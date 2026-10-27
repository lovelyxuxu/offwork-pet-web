"""Read-only publisher-supplied character dialogue catalog."""
import hashlib
import json
from pathlib import Path
import re

IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')


def dialogue_items(directory, catalog):
    visible = {item['id'] for item in catalog.characters()}
    result = []
    for path in sorted(Path(directory).glob('*.petdialogue')):
        if path.is_symlink() or path.stat().st_size > 1024 * 1024:
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if (data.get('format') != 'offwork-pet.dialogue/v1' or data.get('medium') != 'text'
                    or data.get('characterId') not in visible or not IDENTIFIER.fullmatch(data.get('id', ''))):
                continue
            scenes = [{'id': scene['id'], 'label': scene['label'], 'lines': scene['lines']} for scene in data['scenes']]
            result.append({'id': data['id'], 'characterId': data['characterId'], 'version': data['version'],
                           'name': data['displayName'], 'description': data['description'], 'medium': 'text',
                           'scenes': scenes, 'sceneCount': len(scenes), 'lineCount': sum(len(scene['lines']) for scene in scenes),
                           'size': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'download_url': f"/api/catalog/dialogues/{data['id']}/download", '_path': path})
        except (ValueError, KeyError, TypeError, OSError):
            continue
    return result


def public(item):
    return {key: value for key, value in item.items() if key != '_path'}
