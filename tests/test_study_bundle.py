"""Synthetic ZIP safety tests; no training, networking or real source claims."""
import io
import zipfile
import pytest
from src.study import validate_project_bundle


def test_rejects_arbitrary_archive_paths():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('../source_manifest.json', '{}')
    with pytest.raises(ValueError, match='archive'):
        validate_project_bundle(buffer.getvalue())


def test_requires_complete_study_not_just_forecasts():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('results/forecasts.csv', 'model,prediction\nnaive,10\n')
    with pytest.raises(ValueError, match='manifest'):
        validate_project_bundle(buffer.getvalue())


def test_reproducible_study_and_results_import_together():
    import json
    import pandas as pd
    from src.io_sources import import_files, observations_csv, sha256
    from src.results import score_predictions
    config = {'columns': {'year': 'year', 'who_region': 'who_region', 'resistance_pct': 'resistance_pct'},
              'percentage_scale': 'percent', 'indicator_code': 'ECOLI_3GC_BSI',
              'statistic_type': 'who_unadjusted_regional_median', 'source_id': 'S1',
              'source_url': 'https://worldhealthorg.shinyapps.io/glass-dashboard/',
              'source_revision': '2025-09-25', 'source_downloaded_at': '2026-10-29T12:00:00+00:00',
              'definition_note': 'SYNTHETIC TEST ONLY', 'filters': {'fixture': True}}
    raw = pd.DataFrame({'year': range(2019,2024), 'who_region': ['AFR']*5, 'resistance_pct': [10.,11.,12.,13.,14.]}).to_csv(index=False).encode()
    data, manifest, _ = import_files([('synthetic.csv', raw, config)])
    base = {'who_region': 'AFR', 'indicator_code': 'ECOLI_3GC_BSI', 'statistic_type': 'who_unadjusted_regional_median'}
    row = {**base, 'target_year': 2023, 'actual': 14., 'train_end_year': 2022, 'phase': 'holdout', 'record_type': 'backtest_prediction'}
    for model in ('naive','linear','ridge'):
        row.update({model+'_pred': 13., model+'_raw': 13., model+'_clipped': False})
    backtests = pd.DataFrame([row])
    forecasts = pd.DataFrame([{**base, 'target_year': 2024, 'last_observed_year': 2023,
                               'model': 'naive', 'prediction': 14., 'raw_prediction': 14.,
                               'clipped': False, 'record_type': 'experimental_forecast'}])
    metadata = {'schema_version': 1, 'execution_environment': 'google_colab',
                'indicator_code': 'ECOLI_3GC_BSI', 'statistic_type': 'who_unadjusted_regional_median',
                'holdout_year': 2023, 'observations_sha256': sha256(observations_csv(data))}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('data/source_manifest.json', json.dumps(manifest))
        archive.writestr('data/raw/synthetic.csv', raw)
        archive.writestr('data/processed/regional_resistance.csv', observations_csv(data))
        archive.writestr('results/backtests.csv', backtests.to_csv(index=False))
        archive.writestr('results/forecasts.csv', forecasts.to_csv(index=False))
        archive.writestr('results/model_metrics.csv', score_predictions(backtests).to_csv(index=False))
        archive.writestr('results/model_metadata.json', json.dumps(metadata))
    imported, _, raw_files, result, _ = validate_project_bundle(buffer.getvalue())
    assert len(imported) == 5
    assert raw_files['synthetic.csv'] == raw
    # Hand calculation: each synthetic holdout prediction is 13 against actual 14.
    assert result['metrics'].mae_pp.tolist() == [1.,1.,1.]
