"""Read plain-data Colab study bundles; never execute code or load fitted models."""
import argparse
import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from src.io_sources import import_files, observations_csv, sha256, write_processed
from src.results import load_results, save_results, RESULT_FILES


def validate_project_bundle(payload):
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)) or any('\\' in n or PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('Invalid study archive paths or duplicate entries.')
            if sum(e.file_size for e in entries) > 200_000_000:
                raise ValueError('Study archive exceeds 200 MB uncompressed.')
            if 'data/source_manifest.json' not in names:
                raise ValueError('Study source manifest is missing.')
            manifest = json.loads(archive.read('data/source_manifest.json'))
            if not isinstance(manifest.get('files'), list) or not manifest['files']:
                raise ValueError('Study manifest has no source inputs.')
            items, raw_files = [], {}
            for entry in manifest['files']:
                name = entry['filename']
                if Path(name).name != name or '/' in name or '\\' in name:
                    raise ValueError('Invalid source filename in study manifest.')
                content = archive.read('data/raw/' + name)
                if sha256(content) != entry['sha256']:
                    raise ValueError('Study source checksum mismatch.')
                items.append((name, content, entry['adapter']))
                raw_files[name] = content
            for entry in manifest.get('upstream_sources', []):
                name = entry['filename']
                if Path(name).name != name or '/' in name or '\\' in name:
                    raise ValueError('Invalid upstream source filename.')
                content = archive.read('data/raw/' + name)
                if sha256(content) != entry['sha256']:
                    raise ValueError('Upstream WHO source checksum mismatch.')
                raw_files[name] = content
            data, regenerated, _ = import_files(items)
            if regenerated['files'] != manifest['files']:
                raise ValueError('Study source adapter/header metadata does not match raw inputs.')
            if archive.read('data/processed/regional_resistance.csv') != observations_csv(data):
                raise ValueError('Study processed observations do not match reproducible source transforms.')
            result_buffer = io.BytesIO()
            with zipfile.ZipFile(result_buffer, 'w', zipfile.ZIP_DEFLATED) as results:
                for name in RESULT_FILES:
                    results.writestr(name, archive.read('results/' + name))
            result_payload = result_buffer.getvalue()
            verified = load_results(result_payload, data)
    except (zipfile.BadZipFile, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Invalid study bundle: {exc}') from exc
    return data, manifest, raw_files, verified, result_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='amr_project_bundle.zip downloaded from Colab')
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    data, manifest, raw_files, _, results = validate_project_bundle(Path(args.input).read_bytes())
    root = Path(args.root)
    write_processed(root, data, manifest, raw_files)
    save_results(root, results, data)
    print(f'Imported {len(data)} observations and verified Colab results. No predictive fitting or model loading.')


if __name__ == '__main__':
    main()
