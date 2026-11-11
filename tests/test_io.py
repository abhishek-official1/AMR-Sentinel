"""All input bytes are synthetic, isolated pipeline contract tests."""
import json
import io
import zipfile
import pytest
from src.io_sources import read_export, import_files, input_bundle, sha256


def test_duplicate_headers_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        read_export('test.csv', b'year,year,value\n2020,2020,10\n')


def test_unsupported_export_rejected():
    with pytest.raises(ValueError, match='CSV or XLSX'):
        read_export('test.json', b'{}')


def test_corrupt_xlsx_rejected():
    with pytest.raises(ValueError):
        read_export('test.xlsx', b'not an excel file')


def test_bundle_identity():
    import pandas as pd
    frame = pd.DataFrame({'year': [2020,2022], 'who_region': ['AFR','AFR'],
                          'indicator_code': ['ECOLI_3GC_BSI']*2,
                          'statistic_type': ['who_unadjusted_regional_median']*2,
                          'resistance_pct': [10.,20.]})
    with zipfile.ZipFile(io.BytesIO(input_bundle(frame, {'files': []}))) as z:
        meta = json.loads(z.read('input_metadata.json'))
        assert sha256(z.read('observations.csv')) == meta['observations_sha256']
