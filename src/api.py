"""Local React dashboard API and static server. All predictive work stays in Colab."""
import argparse
import base64
import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.dashboard import StudyService

ROOT = Path(__file__).resolve().parents[1]


def create_app(root=ROOT):
    root = Path(root)
    service = StudyService(root)
    app = FastAPI(title='AMR Sentinel', docs_url='/api/docs', redoc_url=None)
    app.state.study = service

    @app.get('/api/study')
    def study():
        return service.snapshot()

    async def bounded_body(request, limit=50_000_000):
        chunks, total = [], 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit:
                raise HTTPException(413, 'Import exceeds 50 MB. Use the plain-data Colab study bundle.')
            chunks.append(chunk)
        return b''.join(chunks)

    @app.post('/api/import/study')
    async def import_study(request: Request):
        try:
            return service.import_bundle(await bounded_body(request))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post('/api/import/observations')
    async def import_observations(request: Request):
        try:
            body = json.loads(await bounded_body(request))
            name = body['filename']
            if not isinstance(name, str) or Path(name).name != name:
                raise ValueError('Invalid source filename.')
            payload = base64.b64decode(body['content_base64'], validate=True)
            return service.import_observations(name, payload, body['mapping'])
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/api/export/{name}')
    def export(name: str):
        try:
            content = service.export(name)
            return Response(content, media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="amr_{name}.csv"'})
        except KeyError as exc:
            raise HTTPException(404, 'Unknown or unavailable export.') from exc
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get('/api/notebook')
    def notebook():
        path = root / 'notebooks/AMR_Sentinel_Public.ipynb'
        if not path.exists():
            raise HTTPException(404, 'Colab notebook is unavailable.')
        return FileResponse(path, filename=path.name, media_type='application/x-ipynb+json')

    @app.get('/api/report')
    def report():
        folder = service.report_folder
        if folder is None or not (folder / 'reports/analysis_report.html').exists():
            raise HTTPException(404, 'Report is available in the original Colab bundle.')
        return FileResponse(folder / 'reports/analysis_report.html', filename='AMR_Sentinel_Analysis.html', media_type='text/html')

    dist = root / 'frontend/dist'
    if dist.is_dir():
        app.mount('/', StaticFiles(directory=dist, html=True), name='react')
    else:
        @app.get('/')
        def not_built():
            return JSONResponse({'message': 'Build the React interface first: cd frontend; npm install; npm run build'}, status_code=503)
    return app


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port, access_log=False)


if __name__ == '__main__':
    main()
