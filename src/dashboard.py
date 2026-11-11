"""Plain-data study service for the React dashboard. No model inference or fitting."""
import io
import json
import threading
import zipfile
from pathlib import Path
import pandas as pd
from src.analytics import annual_changes, quality_report
from src.clean import REGIONS, INDICATORS
from src.io_sources import import_files, load_saved, observations_csv, sha256
from src.results import load_saved_results, score_predictions
from src.study import validate_project_bundle


def records(frame):
    """JSON-safe pandas records: nullable counts and NaN become JSON null."""
    return json.loads(frame.to_json(orient='records', date_format='iso'))


def folder_bundle(folder):
    """Package only data-contract files from an existing Colab export, in memory."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for directory in ('data', 'results'):
            base = folder / directory
            for path in base.rglob('*'):
                if path.is_file():
                    archive.writestr(path.relative_to(folder).as_posix(), path.read_bytes())
    return output.getvalue()


class StudyService:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.RLock()
        self.data = pd.DataFrame()
        self.manifest = {'files': []}
        self.results = None
        self.tables = {}
        self.error = None
        self.report_folder = None
        self.load_default()

    def load_default(self):
        try:
            manifest_path = self.root / 'data/source_manifest.json'
            if manifest_path.exists() and json.loads(manifest_path.read_text(encoding='utf-8')).get('files'):
                self.data, self.manifest, _ = load_saved(self.root)
                if (self.root / 'results/model_metadata.json').exists():
                    self.results = load_saved_results(self.root, self.data)
            else:
                folder = self.root / 'notebooks/amr_project_bundle'
                if (folder / 'data/source_manifest.json').exists():
                    self.import_bundle(folder_bundle(folder), folder=folder)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            self.data, self.results = pd.DataFrame(), None
            self.error = str(exc)

    def import_bundle(self, payload, folder=None):
        data, manifest, _, results, _ = validate_project_bundle(payload)
        extras = {}
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for key, name in {
                'national': 'data/processed/national_observations.csv',
                'coverage': 'data/processed/country_coverage_all_years.csv',
                'composition': 'data/processed/reporting_country_composition.csv',
            }.items():
                if name in archive.namelist():
                    extras[key] = pd.read_csv(io.BytesIO(archive.read(name)))
            validation = json.loads(archive.read('data/processed/input_validation.json')) if 'data/processed/input_validation.json' in archive.namelist() else {}
        # Commit only after the entire dataset/result contract has passed.
        with self.lock:
            self.data, self.manifest, self.results, self.tables = data, manifest, results, extras
            self.validation = validation
            self.report_folder, self.error = folder, None
        return self.snapshot()

    def import_observations(self, name, payload, mapping):
        data, manifest, _ = import_files([(name, payload, mapping)])
        with self.lock:
            self.data, self.manifest, self.results = data, manifest, None
            self.tables, self.validation, self.report_folder, self.error = {}, {}, None, None
        return self.snapshot()

    def snapshot(self):
        with self.lock:
            if self.data.empty:
                return {'status': 'empty', 'error': self.error, 'observations': [], 'metrics': [],
                        'forecasts': [], 'backtests': [], 'quality': [], 'national': [], 'coverage': [],
                        'regions': REGIONS, 'indicators': INDICATORS, 'metadata': {}, 'manifest': self.manifest,
                        'validation': {}, 'summary': {}, 'report_available': False}
            data = annual_changes(self.data)
            valid = data.dropna(subset=['resistance_pct'])
            national = self.tables.get('national', pd.DataFrame())
            metadata = self.results['metadata'] if self.results else {}
            return {
                'status': 'ready', 'error': None, 'regions': REGIONS, 'indicators': INDICATORS,
                'observations': records(data), 'quality': records(quality_report(data)),
                'national': records(national), 'coverage': records(self.tables.get('coverage', pd.DataFrame())),
                'forecasts': records(self.results['forecasts']) if self.results else [],
                'backtests': records(self.results['backtests']) if self.results else [],
                'metrics': records(self.results['metrics']) if self.results else [],
                'validation_metrics': records(score_predictions(self.results['backtests'].query("phase == 'validation'"))) if self.results else [],
                'metadata': metadata, 'manifest': self.manifest, 'validation': getattr(self, 'validation', {}),
                'summary': {'first_year': int(valid.year.min()) if not valid.empty else None, 'last_year': int(valid.year.max()) if not valid.empty else None,
                            'national_observations': len(national) if not national.empty else None,
                            'reporting_countries': int(national.country_code.nunique()) if 'country_code' in national else None,
                            'regional_observations': len(data),
                            'observations_sha256': sha256(observations_csv(self.data))},
                'report_available': self.report_folder is not None and (self.report_folder / 'reports/analysis_report.html').exists(),
            }

    def export(self, name):
        with self.lock:
            if self.data.empty:
                raise ValueError('Real dataset required — analysis unavailable.')
            tables = {'observations': annual_changes(self.data), 'quality': quality_report(self.data), **self.tables}
            if self.results:
                tables.update({k: self.results[k] for k in ('forecasts', 'backtests', 'metrics')})
            if name not in tables:
                raise KeyError(name)
            return tables[name].to_csv(index=False).encode('utf-8')
