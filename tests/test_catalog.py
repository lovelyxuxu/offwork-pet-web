import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from portal.app import create_app


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.app = create_app(self.root / 'data')
        self.catalog = self.app.state.catalog
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def pack(self, version='1.0.0', description='会变成云的小伙伴', extra=None, menu=True):
        output = self.root / f'test-{version}.petpack'
        image = io.BytesIO()
        Image.new('RGBA', (12, 12), '#758953').save(image, format='PNG')
        manifest = {'formatVersion': 1, 'id': 'cloud.friend', 'version': version,
                    'displayName': '云朵', 'description': description, 'author': '创作者',
                    'canvas': {'width': 12, 'height': 12}, 'thumbnail': 'assets/cloud.png',
                    'behavior': 'behavior.json', 'requires': ['input.pointer-look/v1'],
                    'credits': [{'author': '创作者', 'license': 'test license'}]}
        behavior = {'initialState': 'cloud', 'states': {'cloud': {'animation': 'float'}},
                    'animations': {'float': {'frames': [{'file': 'assets/cloud.png', 'durationMs': 150}]}},
                    'actions': {'become_rain': {'animation': 'float'}},
                    'menu': [{'id': 'rain', 'label': '变成一场雨', 'invoke': {'type': 'action', 'id': 'become_rain'}}] if menu else [],
                    'interactions': []}
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('behavior.json', json.dumps(behavior))
            archive.writestr('assets/cloud.png', image.getvalue())
            if extra:
                # zipfile normally normalizes Windows separators on write;
                # preserve an untrusted archive's exact path for this fixture.
                entry = zipfile.ZipInfo('untrusted')
                entry.filename = entry.orig_filename = extra
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    archive.writestr(entry, 'unexpected')
        return output

    def test_arbitrary_states_actions_and_download_match_source(self):
        pack = self.pack()
        item = self.catalog.import_pack(pack)
        self.assertEqual(item['actions'][0]['label'], '变成一场雨')
        self.assertIn('鼠标跟随', item['tags'])
        response = self.client.get(item['download_url'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, pack.read_bytes())
        self.assertEqual(hashlib.sha256(response.content).hexdigest(), item['sha256'])
        preview = self.client.get(item['preview_url'])
        self.assertEqual(preview.headers['content-type'], 'image/webp')
        self.assertEqual(self.client.get(item['actions'][0]['preview_url']).status_code, 200)

    def test_zero_menu_actions_is_valid(self):
        self.assertEqual(self.catalog.import_pack(self.pack(menu=False))['actions'], [])

    def test_latest_is_semantic_version_not_import_order(self):
        self.catalog.import_pack(self.pack('1.10.0'))
        self.catalog.import_pack(self.pack('1.2.0'))
        self.assertEqual(self.catalog.character('cloud.friend')['version'], '1.10.0')
        self.assertEqual([item['version'] for item in self.catalog.versions('cloud.friend')], ['1.10.0', '1.2.0'])
        self.assertEqual(self.client.get('/api/catalog/characters/cloud.friend/download?version=1.2.0').status_code, 200)

    def test_same_version_cannot_replace_different_bytes(self):
        original = self.pack()
        self.catalog.import_pack(original)
        first_hash = self.catalog.character('cloud.friend')['sha256']
        with self.assertRaisesRegex(ValueError, '增加版本号'):
            self.catalog.import_pack(self.pack(description='different'))
        self.assertEqual(self.catalog.character('cloud.friend')['sha256'], first_hash)

    def test_hidden_character_is_unavailable_at_all_public_endpoints(self):
        item = self.catalog.import_pack(self.pack())
        self.catalog.set_visible(item['id'], False)
        self.assertEqual(self.client.get('/api/catalog/characters').json()['total'], 0)
        for path in [item['preview_url'], item['download_url'], '/api/catalog/characters/cloud.friend', '/api/catalog/characters/cloud.friend/versions']:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.catalog.set_visible(item['id'], True)
        self.assertEqual(len(self.catalog.characters()), 1)

    def test_archive_traversal_and_duplicate_names_rejected(self):
        for extra in ['../escape.txt', 'C:/escape.txt', 'assets\\escape.txt', 'assets/cloud.png']:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.catalog.import_pack(self.pack(extra=extra))
        self.assertEqual(self.catalog.characters(), [])
        self.assertFalse((self.root / 'escape.txt').exists())

    def test_search_handles_unicode_and_sql_characters(self):
        self.catalog.import_pack(self.pack())
        self.assertEqual(self.client.get('/api/catalog/characters', params={'q':'创作者'}).json()['total'], 1)
        self.assertEqual(self.client.get('/api/catalog/characters', params={'q':"' OR 1=1 --"}).json()['total'], 0)
        self.assertEqual(self.client.get('/api/catalog/characters', params={'tag':'鼠标跟随'}).json()['total'], 1)
        self.assertEqual(self.client.get('/api/catalog/characters', params={'tag':'不存在'}).json()['total'], 0)

    def test_database_survives_new_application_instance(self):
        self.catalog.import_pack(self.pack())
        with TestClient(create_app(self.root / 'data')) as second:
            self.assertEqual(second.get('/api/catalog/characters').json()['total'], 1)

    def test_deep_links_and_public_write_routes(self):
        for path in ['/', '/characters', '/characters/cloud.friend', '/download', '/guide']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/html', response.headers['content-type'])
            self.assertIn("script-src 'self'", response.headers['content-security-policy'])
        self.assertEqual(self.client.post('/api/catalog/characters', json={}).status_code, 405)
        self.assertEqual(self.client.get('/api/catalog/not-present').status_code, 404)
        self.assertEqual(self.client.get('/media/../catalog.sqlite3').status_code, 404)

    def test_dialogue_catalog_is_character_bound_readonly_and_download_matches(self):
        from unittest.mock import patch
        from portal.dialogues import dialogue_items, public
        self.catalog.import_pack(self.pack())
        source = Path(__file__).resolve().parents[1] / 'static/dialogue-packs/gugagaga-daily.petdialogue'
        data = json.loads(source.read_text(encoding='utf-8'))
        data['characterId'] = 'cloud.friend'
        directory = self.root / 'dialogues'
        directory.mkdir()
        path = directory / 'sample.petdialogue'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        actual_loader = dialogue_items
        with patch('portal.app.dialogue_items', side_effect=lambda _, catalog: actual_loader(directory, catalog)):
            response = self.client.get('/api/catalog/characters/cloud.friend/dialogues')
            self.assertEqual(response.status_code, 200)
            item = response.json()['items'][0]
            self.assertEqual((item['sceneCount'], item['lineCount']), (30, 360))
            self.assertNotIn('_path', item)
            downloaded = self.client.get(item['download_url'])
            self.assertEqual(downloaded.content, path.read_bytes())
            self.assertEqual(hashlib.sha256(downloaded.content).hexdigest(), item['sha256'])
            self.assertIn('.petdialogue', downloaded.headers['content-disposition'])
            self.assertEqual(self.client.post('/api/catalog/dialogues', json={}).status_code, 405)
            self.assertEqual(self.client.get('/api/catalog/characters/unknown/dialogues').status_code, 404)
            self.catalog.set_visible('cloud.friend', False)
            self.assertEqual(self.client.get('/api/catalog/dialogues').json()['items'], [])
            self.assertEqual(self.client.get(item['download_url']).status_code, 404)
        self.assertEqual(self.client.get('/dialogues').status_code, 200)

    def test_release_metadata_and_url_validation(self):
        path = self.root / 'latest.json'
        value = {'version': '0.6.0-preview.2', 'url':'https://example.com/release.zip',
                 'size': 20, 'sha256':'a' * 64, 'publishedAt':'2026-10-23T00:00:00Z', 'notes':'新增互动\n改进体验'}
        path.write_text(json.dumps({'release': value}), encoding='utf-8')
        self.catalog.import_release(path)
        releases = self.client.get('/api/catalog/releases').json()['items']
        self.assertEqual(releases[0]['channel'], 'preview')
        self.assertEqual(releases[0]['notes'], value['notes'])
        value['url'] = 'javascript:alert(1)'
        path.write_text(json.dumps({'release': value}), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.catalog.import_release(path)


if __name__ == '__main__':
    unittest.main()
