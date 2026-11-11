"""Read-only real-result integration checks; no model training."""
from pathlib import Path
import asyncio
import json
import pytest
from types import SimpleNamespace
from src.api import create_app

ROOT = Path(__file__).resolve().parents[1]
FULL_EXPORT = ROOT / 'notebooks/amr_project_bundle/data/source_manifest.json'


class TestClient:
    """Minimal ASGI harness: no extra HTTP client dependency or server needed."""
    __test__ = False

    def __init__(self, app):
        self.app = app

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def request(self, method, path, content=b'', headers=None):
        async def run():
            sent, received = [], False
            async def receive():
                nonlocal received
                if received:
                    return {'type': 'http.disconnect'}
                received = True
                return {'type': 'http.request', 'body': content, 'more_body': False}
            async def send(message):
                sent.append(message)
            scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
                     'method': method, 'path': path, 'raw_path': path.encode(), 'query_string': b'',
                     'root_path': '', 'scheme': 'http', 'server': ('testserver', 80),
                     'client': ('127.0.0.1', 1234),
                     'headers': [(k.lower().encode(), v.encode()) for k,v in (headers or {}).items()]}
            await self.app(scope, receive, send)
            start = next(m for m in sent if m['type'] == 'http.response.start')
            payload = b''.join(m.get('body', b'') for m in sent if m['type'] == 'http.response.body')
            return SimpleNamespace(status_code=start['status'], text=payload.decode(errors='replace'),
                                   json=lambda: json.loads(payload))
        return asyncio.run(run())

    def get(self, path):
        return self.request('GET', path)

    def post(self, path, content, headers):
        return self.request('POST', path, content, headers)


@pytest.mark.skipif(not FULL_EXPORT.exists(), reason='Optional Colab study export is not included in the repository')
def test_actual_colab_study_is_available():
    with TestClient(create_app(ROOT)) as client:
        response = client.get('/api/study')
        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'ready'
        # Source: the checked local Colab export described in reports/MINI_PROJECT_REPORT.md.
        assert len(body['observations']) == 31
        assert body['summary']['national_observations'] == 407
        assert body['summary']['reporting_countries'] == 95
        assert body['metadata']['holdout_year'] == 2022
        # The report records 9.61 pp MAE; the saved score table retains 9.612 pp.
        assert next(m for m in body['metrics'] if m['model'] == 'naive')['mae_pp'] == pytest.approx(9.612)
        assert len(body['quality']) == 6


@pytest.mark.skipif(not FULL_EXPORT.exists(), reason='Optional Colab study export is not included in the repository')
def test_downloads_have_real_observed_and_forecast_labels():
    with TestClient(create_app(ROOT)) as client:
        assert 'observed' in client.get('/api/export/observations').text
        assert 'experimental_forecast' in client.get('/api/export/forecasts').text
        assert client.get('/api/notebook').status_code == 200
        assert client.get('/api/export/not-a-table').status_code == 404


@pytest.mark.skipif(not FULL_EXPORT.exists(), reason='Optional Colab study export is not included in the repository')
def test_bad_import_keeps_current_study():
    with TestClient(create_app(ROOT)) as client:
        response = client.post('/api/import/study', content=b'not a ZIP', headers={'Content-Type': 'application/zip'})
        assert response.status_code == 400
        assert len(client.get('/api/study').json()['observations']) == 31


def test_empty_project_has_honest_no_data_state():
    with TestClient(create_app(ROOT / 'tests/fixtures/no-project')) as client:
        body = client.get('/api/study').json()
        assert body['status'] == 'empty'
        assert body['observations'] == []
        assert body['metrics'] == []


@pytest.mark.skipif(not FULL_EXPORT.exists(), reason='Optional Colab study export is not included in the repository')
def test_complete_import_and_observation_only_replacement():
    import base64
    from src.dashboard import folder_bundle
    folder = ROOT / 'notebooks/amr_project_bundle'
    payload = folder_bundle(folder)
    with TestClient(create_app(ROOT)) as client:
        imported = client.post('/api/import/study', content=payload, headers={'Content-Type': 'application/zip'})
        assert imported.status_code == 200
        assert len(imported.json()['forecasts']) == 15
        manifest = json.loads((folder / 'data/source_manifest.json').read_text(encoding='utf-8'))
        entry = manifest['files'][0]
        body = {'filename': entry['filename'],
                'content_base64': base64.b64encode((folder / 'data/raw' / entry['filename']).read_bytes()).decode(),
                'mapping': entry['adapter']}
        response = client.post('/api/import/observations', content=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        assert response.status_code == 200
        assert len(response.json()['observations']) == 31
        assert response.json()['forecasts'] == []
        assert response.json()['metadata'] == {}
