"""Raw byte preservation, explicit mapping and content-addressed handoff."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
from src.clean import KEY, normalize_and_validate
from src.analytics import quality_report


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_export(name, payload):
    suffix = Path(name).suffix.lower()
    if suffix == '.csv':
        header = next(csv.reader(io.StringIO(payload.decode('utf-8-sig'))), [])
        if len(header) != len(set(header)):
            raise ValueError('Duplicate source column names are ambiguous.')
        return pd.read_csv(io.BytesIO(payload), encoding='utf-8-sig')
    if suffix == '.xlsx':
        try:
            header = pd.read_excel(io.BytesIO(payload), header=None, nrows=1).iloc[0].dropna().tolist()
            if len(header) != len(set(header)):
                raise ValueError('Duplicate source column names are ambiguous.')
            return pd.read_excel(io.BytesIO(payload))
        except (zipfile.BadZipFile, IndexError, OSError) as exc:
            raise ValueError(f'Cannot read XLSX export: {exc}') from exc
    raise ValueError('Only UTF-8 comma-separated CSV or XLSX is supported. Export or convert explicitly.')


def import_files(items):
    tables, files, manifest = [], {}, {'manifest_version': 1, 'files': []}
    for name, payload, config in items:
        name = Path(name).name
        if name in files and files[name] != payload:
            raise ValueError('Conflicting input filenames; rename files before importing.')
        raw = read_export(name, payload)
        d = normalize_and_validate(raw, config, name)
        d['source_sha256'] = sha256(payload)
        tables.append(d)
        files[name] = payload
        manifest['files'].append({'filename': name, 'sha256': sha256(payload),
                                  'original_columns': list(raw.columns), 'adapter': config})
    if not tables:
        raise ValueError('Select at least one authentic WHO file.')
    d = pd.concat(tables, ignore_index=True).drop_duplicates()
    if d.duplicated(KEY).any():
        raise ValueError('Conflicting duplicate rows across files; do not mix revisions or source definitions.')
    # A target cannot change source or methodology between years.
    for _, g in d.groupby(['who_region', 'indicator_code', 'statistic_type']):
        for col in ('source_id', 'source_revision', 'definition_note', 'source_url'):
            if g[col].nunique() > 1:
                raise ValueError(f'Source/definition change in {col}; import as a separate study.')
    return d.sort_values(KEY).reset_index(drop=True), manifest, files


def observations_csv(d):
    return d.sort_values(KEY).to_csv(index=False, lineterminator='\n').encode('utf-8')


def data_dictionary():
    return '''# Normalized data dictionary

Rows are observed annual WHO regional statistics, never projections.
year: integer observation year. who_region: AFR/AMR/EMR/EUR/SEAR/WPR.
indicator_code: ECOLI_3GC_BSI or MRSA_BSI. infection_type: Bloodstream infection.
pathogen: canonical organism. resistance_pct: percentage in [0,100], null stays null.
statistic_type: who_unadjusted_regional_median or separately labeled derived_country_median.
source_id, source_url, source_file, source_downloaded_at, source_revision,
source_sha256: trace input and release. definition_note: exact metric meaning.
country_count: nullable reporting-country count; country_count_known: bool.
numerator_resistant, denominator_tested: nullable compatible infection counts.
sample_size_known: both compatible count fields supplied; no count eligibility claim.
coverage_note: source limitations. record_type: observed.

Transformations: explicitly mapped fields, documented WHO region aliases,
declared fraction-to-percent scaling only, exact redundant duplicates dropped,
conflicting duplicates rejected. Nulls never become zero. No interpolation.
Derived medians need >=5 countries and documented mapping/selection, and never
reproduce WHO's count-based eligibility without the required infection counts.
Unknown country/testing counts do not demonstrate WHO eligibility thresholds.

Source: WHO GLASS https://worldhealthorg.shinyapps.io/glass-dashboard/
Primary definition: https://data.who.int/indicators/i/918081E/745F475
Secondary definition: https://data.who.int/indicators/i/918081E/5DD9606
'''


def write_processed(root, d, manifest, raw_files):
    raw_dir, processed = root / 'data/raw', root / 'data/processed'
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite an untouched raw input with different bytes.
    for name, payload in raw_files.items():
        target = raw_dir / name
        if target.exists() and target.read_bytes() != payload:
            raise ValueError(f'Raw file already exists with different bytes: {name}')
    for name, payload in raw_files.items():
        (raw_dir / name).write_bytes(payload)
    (root / 'data/source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    d.to_parquet(processed / 'regional_resistance.parquet', index=False)
    (processed / 'regional_resistance.csv').write_bytes(observations_csv(d))
    quality_report(d).to_csv(processed / 'data_quality.csv', index=False)
    (processed / 'data_dictionary.md').write_text(data_dictionary(), encoding='utf-8')


def input_bundle(d, manifest):
    payload = observations_csv(d)
    contract = {'schema_version': 1, 'observations_sha256': sha256(payload),
                'manifest': manifest, 'note': 'WHO observations only; run modeling in Google Colab.'}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('observations.csv', payload)
        archive.writestr('input_metadata.json', json.dumps(contract, indent=2))
    return output.getvalue()


def load_saved(root):
    """Rebuild normalized rows from hash-verified untouched source files."""
    manifest = json.loads((root / 'data/source_manifest.json').read_text(encoding='utf-8'))
    items = []
    for entry in manifest['files']:
        name = entry['filename']
        if Path(name).name != name:
            raise ValueError('Invalid source filename in manifest.')
        payload = (root / 'data/raw' / name).read_bytes()
        if sha256(payload) != entry['sha256']:
            raise ValueError(f'Raw checksum changed: {name}. Re-import explicitly.')
        items.append((name, payload, entry['adapter']))
    return import_files(items)
