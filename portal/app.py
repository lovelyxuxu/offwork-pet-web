import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .catalog import Catalog, IDENTIFIER
from .dialogues import dialogue_items, public

ROOT = Path(__file__).resolve().parents[1]


def create_app(data_dir=None):
    catalog = Catalog(data_dir or os.environ.get('OFFWORK_WEB_DATA', ROOT / 'var'))
    app = FastAPI(title='下班搭子 · 角色资源库', docs_url=None, redoc_url=None)
    app.state.catalog = catalog

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith('/api/catalog/'):
            response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.get('/api/catalog/health')
    def health():
        return {'ok': True, 'service': 'offwork-pet-web'}

    @app.get('/api/catalog/characters')
    def characters(q: str = Query('', max_length=200), tag: str = Query('', max_length=60)):
        items = catalog.characters(q, tag)
        return {'items': items, 'total': len(items),
                'tags': sorted({tag for item in catalog.characters() for tag in item['tags']})}

    @app.get('/api/catalog/characters/{identifier}/download')
    def download(identifier: str, version: str | None = None):
        character = catalog.character(identifier, version)
        if not character:
            raise HTTPException(404, '角色或版本不存在')
        path = catalog.root / 'packs' / character['id'] / character['version'] / 'character.petpack'
        if not path.is_file():
            raise HTTPException(404, '角色包文件暂不可用')
        return FileResponse(path, filename=f"{character['id']}-{character['version']}.petpack",
                            media_type='application/octet-stream', headers={'ETag': '"' + character['sha256'] + '"'})

    @app.get('/api/catalog/characters/{identifier}/versions')
    def versions(identifier: str):
        if not catalog.character(identifier):
            raise HTTPException(404, '角色不存在')
        return {'items': catalog.versions(identifier)}

    @app.get('/api/catalog/characters/{identifier}')
    def character(identifier: str):
        result = catalog.character(identifier)
        if not result:
            raise HTTPException(404, '角色不存在')
        return result

    @app.get('/api/catalog/releases')
    def releases():
        return {'items': catalog.releases()}

    @app.get('/api/catalog/dialogues')
    def dialogues():
        return {'items': [public(item) for item in dialogue_items(ROOT / 'static/dialogue-packs', catalog)]}

    @app.get('/api/catalog/characters/{identifier}/dialogues')
    def character_dialogues(identifier: str):
        if not catalog.character(identifier):
            raise HTTPException(404, '角色不存在')
        return {'items': [public(item) for item in dialogue_items(ROOT / 'static/dialogue-packs', catalog)
                          if item['characterId'] == identifier]}

    @app.get('/api/catalog/dialogues/{identifier}/download')
    def dialogue_download(identifier: str):
        item = next((item for item in dialogue_items(ROOT / 'static/dialogue-packs', catalog) if item['id'] == identifier), None)
        if not item:
            raise HTTPException(404, '台词包不存在')
        return FileResponse(item['_path'], filename=f"{item['id']}-{item['version']}.petdialogue",
                            media_type='application/octet-stream', headers={'ETag': '"' + item['sha256'] + '"'})

    @app.get('/media/{identifier}/{version}/{name}')
    def media(identifier: str, version: str, name: str):
        if not all(IDENTIFIER.fullmatch(part) for part in (identifier, version, name)):
            raise HTTPException(404)
        if not catalog.character(identifier, version) or not (name in ('thumbnail.png', 'preview.webp') or re.fullmatch(r'action-\d+\.webp', name)):
            raise HTTPException(404)
        path = catalog.root / 'media' / identifier / version / name
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, headers={'Cache-Control': 'public, max-age=3600'})

    app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

    @app.get('/')
    @app.get('/characters')
    @app.get('/characters/{identifier}')
    @app.get('/download')
    @app.get('/guide')
    @app.get('/dialogues')
    def page(identifier: str | None = None):
        return FileResponse(ROOT / 'static' / 'index.html', headers={'Cache-Control': 'no-cache'})

    return app


app = create_app()
