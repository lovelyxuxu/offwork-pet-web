"""Local publishing and SQLite storage; no visitor-facing write interface."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import tempfile
from urllib.parse import urlsplit
import zipfile

from packaging.version import Version
from PIL import Image

IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")
CAPABILITIES = {
    'input.pointer-look/v1': '鼠标跟随',
    'input.stroke/v1': '抚摸互动',
    'behavior.autonomy/v1': '自主活动',
    'desktop.explore/v1': '桌面探索',
    'desktop.toys/v1': '桌面小球',
    'render.gifts/v1': '搭子礼物',
    'focus.events/v1': '专注陪伴',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def safe_name(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError('包标识或版本包含不支持的字符')
    return value


def archive_path(value):
    if not isinstance(value, str) or '\\' in value or ':' in value or '\x00' in value:
        raise ValueError('角色包资源路径不合法')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('角色包资源路径不合法')
    return path.as_posix()


class Catalog:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'catalog.sqlite3'
        with closing(self.connect()) as db, db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS characters (
                    id TEXT PRIMARY KEY, current_version TEXT NOT NULL,
                    published_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    visible INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS versions (
                    character_id TEXT NOT NULL, version TEXT NOT NULL,
                    sha256 TEXT NOT NULL, size INTEGER NOT NULL,
                    metadata TEXT NOT NULL, published_at TEXT NOT NULL,
                    PRIMARY KEY(character_id, version)
                );
                CREATE TABLE IF NOT EXISTS releases (
                    version TEXT PRIMARY KEY, metadata TEXT NOT NULL,
                    published_at TEXT NOT NULL
                );
            ''')

    def connect(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def characters(self, query='', tag=''):
        # User input never becomes SQL or a filesystem path.
        with closing(self.connect()) as db:
            rows = db.execute('''SELECT v.* FROM characters c JOIN versions v
                ON c.id=v.character_id AND c.current_version=v.version
                WHERE c.visible=1 ORDER BY c.id''').fetchall()
        items = [self.serialize(row) for row in rows]
        needle = query.strip().casefold()
        return [item for item in items
                if (not needle or needle in ' '.join([
                    item['name'], item['description'], item['author'],
                    *item['tags']]).casefold())
                and (not tag or tag in item['tags'])]

    def character(self, identifier, version=None):
        with closing(self.connect()) as db:
            if version:
                row = db.execute('''SELECT v.* FROM versions v JOIN characters c
                    ON c.id=v.character_id WHERE c.visible=1
                    AND v.character_id=? AND v.version=?''', (identifier, version)).fetchone()
            else:
                row = db.execute('''SELECT v.* FROM characters c JOIN versions v
                    ON c.id=v.character_id AND c.current_version=v.version
                    WHERE c.visible=1 AND c.id=?''', (identifier,)).fetchone()
        return self.serialize(row) if row else None

    def serialize(self, row):
        item = json.loads(row['metadata'])
        base = f"/media/{item['id']}/{item['version']}"
        item.update(size=row['size'], sha256=row['sha256'], published_at=row['published_at'],
                    thumbnail_url=base + '/thumbnail.png', preview_url=base + '/preview.webp',
                    download_url=f"/api/catalog/characters/{item['id']}/download?version={item['version']}")
        for action in item['actions']:
            action['preview_url'] = base + '/' + action['file']
        return item

    def versions(self, identifier):
        if not self.character(identifier):
            return []
        with closing(self.connect()) as db:
            rows = db.execute('SELECT * FROM versions WHERE character_id=?', (identifier,)).fetchall()
        return [self.serialize(row) for row in sorted(rows, key=lambda row: Version(row['version']), reverse=True)]

    def releases(self):
        with closing(self.connect()) as db:
            rows = db.execute('SELECT metadata FROM releases').fetchall()
        return sorted([json.loads(row[0]) for row in rows], key=lambda row: Version(row['version']), reverse=True)

    def import_release(self, path):
        document = json.loads(Path(path).read_text(encoding='utf-8'))
        release = document['release']
        Version(release['version'])
        url = urlsplit(release['url'])
        if url.scheme not in ('http', 'https') or not url.netloc:
            raise ValueError('下载地址必须是 HTTP(S) 地址')
        # Display-only snapshot of the publisher's feed. The signed feed itself
        # stays on the desktop update service; this site never re-signs it.
        value = {key: release[key] for key in ['version', 'url', 'size', 'sha256', 'publishedAt', 'notes']}
        value['channel'] = 'preview' if Version(value['version']).is_prerelease else 'stable'
        with closing(self.connect()) as db, db:
            db.execute('INSERT OR REPLACE INTO releases VALUES (?,?,?)',
                       (value['version'], json.dumps(value, ensure_ascii=False), value['publishedAt']))
        return value

    def set_visible(self, identifier, visible):
        with closing(self.connect()) as db, db:
            result = db.execute('UPDATE characters SET visible=? WHERE id=?', (int(visible), identifier))
            if not result.rowcount:
                raise ValueError('角色不存在')

    def import_pack(self, source):
        source = Path(source).resolve()
        if source.stat().st_size > 256 * 1024 * 1024:
            raise ValueError('角色包过大')
        with source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) > 4096 or sum(entry.file_size for entry in entries) > 256 * 1024 * 1024:
                raise ValueError('角色包超出文件数或解压大小限制')
            names = set()
            for entry in entries:
                # On Windows zipfile normalizes backslashes in .filename;
                # inspect the original archive name before trusting it.
                name = archive_path(entry.orig_filename)
                if name in names or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise ValueError('角色包存在重复路径、符号链接或加密文件')
                names.add(name)
            manifest = self.read_json(archive, 'manifest.json')
            if manifest.get('formatVersion') != 1:
                raise ValueError('不支持的角色包格式版本')
            identifier, version = safe_name(manifest['id']), safe_name(manifest['version'])
            Version(version)
            with closing(self.connect()) as db:
                previous = db.execute('SELECT sha256 FROM versions WHERE character_id=? AND version=?',
                                      (identifier, version)).fetchone()
            if previous and previous[0] != digest:
                raise ValueError('同一角色版本已经发布了不同内容，请增加版本号')
            behavior = self.read_json(archive, archive_path(manifest['behavior']))
            canvas = manifest['canvas']
            width, height = canvas['width'], canvas['height']
            if not all(isinstance(n, int) and 0 < n <= 4096 for n in (width, height)) or width * height * 4 > 32 * 1024 * 1024:
                raise ValueError('角色画布尺寸超出限制')
            animations = behavior['animations']
            initial = behavior['states'][behavior['initialState']]['animation']
            with tempfile.TemporaryDirectory(prefix='pack-', dir=self.root) as temporary:
                staging = Path(temporary)
                image_cache = {}
                def get_image(name):
                    name = archive_path(name)
                    if name not in image_cache:
                        if len(image_cache) >= 64:
                            image_cache.clear()
                        with Image.open(io.BytesIO(archive.read(name))) as original:
                            if original.width * original.height * 4 > 32 * 1024 * 1024:
                                raise ValueError('素材图片解码尺寸超出限制')
                            image_cache[name] = original.convert('RGBA')
                    return image_cache[name]
                thumb = get_image(manifest['thumbnail']).copy()
                thumb.thumbnail((512, 512))
                thumb.save(staging / 'thumbnail.png')

                def make_preview(animation_id, target):
                    definition = animations[animation_id]
                    frames, durations = [], []
                    if not definition['frames'] or len(definition['frames']) > 256:
                        raise ValueError('预览动画为空或超过 256 帧')
                    for frame in definition['frames']:
                        picture = get_image(frame['file'])
                        if 'rect' in frame:
                            x, y, w, h = frame['rect']
                            if min(x, y) < 0 or min(w, h) <= 0 or x + w > picture.width or y + h > picture.height:
                                raise ValueError('动画帧区域超出图片范围')
                            picture = picture.crop((x, y, x + w, y + h))
                        picture = picture.copy()
                        layer = Image.new('RGBA', (width, height))
                        rect = frame.get('drawRect', [0, 0, width, height])
                        x, y, w, h = rect
                        if not all(isinstance(n, int) for n in rect) or min(w, h) <= 0 or max(w, h) > 4096:
                            raise ValueError('动画绘制区域不合法')
                        layer.alpha_composite(picture.resize((w, h)), (x, y))
                        layer.thumbnail((384, 384))
                        frames.append(layer)
                        durations.append(max(40, min(10000, int(frame['durationMs']))))
                    frames[0].save(target, format='WEBP', save_all=True,
                                   append_images=frames[1:], duration=durations, loop=0, lossless=True)

                make_preview(initial, staging / 'preview.webp')
                actions = []
                for menu in sorted(behavior.get('menu', []), key=lambda entry: entry.get('order', 0))[:12]:
                    invoke = menu.get('invoke', {})
                    if invoke.get('type') != 'action':
                        continue
                    action = behavior['actions'][invoke['id']]
                    file = f'action-{len(actions)}.webp'
                    make_preview(action['animation'], staging / file)
                    actions.append({'id': str(menu['id']), 'label': str(menu['label']), 'file': file})
                requires = manifest.get('requires', [])
                tags = [label for capability, label in CAPABILITIES.items() if capability in requires]
                if behavior.get('interactions'):
                    tags.append('远程互动')
                metadata = {'id': identifier, 'version': version, 'name': str(manifest['displayName']),
                            'description': str(manifest.get('description', '')), 'author': str(manifest.get('author', '未署名')),
                            'credits': manifest.get('credits', []), 'requires': requires,
                            'format_version': manifest['formatVersion'], 'tags': tags, 'actions': actions,
                            'interactions': [{'id': item['id'], 'label': item['label']} for item in behavior.get('interactions', [])]}
                media = self.root / 'media' / identifier / version
                pack = self.root / 'packs' / identifier / version / 'character.petpack'
                if not media.exists():
                    media.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(staging, media)
                if not pack.exists():
                    pack.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, pack)
                timestamp = now()
                with closing(self.connect()) as db, db:
                    db.execute('INSERT OR IGNORE INTO versions VALUES (?,?,?,?,?,?)',
                               (identifier, version, digest, source.stat().st_size, json.dumps(metadata, ensure_ascii=False), timestamp))
                    current = db.execute('SELECT current_version FROM characters WHERE id=?', (identifier,)).fetchone()
                    if not current:
                        db.execute('INSERT INTO characters VALUES (?,?,?,?,1)', (identifier, version, timestamp, timestamp))
                    elif Version(version) > Version(current[0]):
                        db.execute('UPDATE characters SET current_version=?, updated_at=? WHERE id=?', (version, timestamp, identifier))
        return self.character(identifier, version)

    @staticmethod
    def read_json(archive, path):
        if archive.getinfo(path).file_size > 4 * 1024 * 1024:
            raise ValueError('角色包声明文件过大')
        return json.loads(archive.read(path))
