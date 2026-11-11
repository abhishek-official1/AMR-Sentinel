"""Synthetic contract examples only; no fitting or real findings."""
import io
import json
import zipfile
import pandas as pd
import pytest
from src.results import load_results, score_predictions


def test_metrics_use_matched_cases():
    rows = pd.DataFrame({'who_region': ['AFR','AMR'], 'target_year': [2023,2023],
                         'actual': [10,20], 'naive_pred': [12,18],
                         'linear_pred': [11,19], 'ridge_pred': [None,21]})
    metrics = score_predictions(rows)
    assert set(metrics.n) == {1}
    assert metrics.loc[metrics.model == 'naive', 'mae_pp'].iloc[0] == 2
    assert metrics.loc[metrics.model == 'ridge', 'rmse_pp'].iloc[0] == 1


def test_no_results_without_matching_data():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('model_metadata.json', json.dumps({'observations_sha256': 'wrong'}))
    with pytest.raises(ValueError, match='dataset'):
        load_results(buffer.getvalue(), pd.DataFrame(), expected_hash='right')


def test_rejects_archive_paths():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('../forecasts.csv', 'malicious')
    with pytest.raises(ValueError, match='archive'):
        load_results(buffer.getvalue(), pd.DataFrame(), expected_hash='right')


@pytest.fixture
def synthetic_result_contract():
    """Handwritten predictions, not fitted models; isolated SYNTHETIC test data."""
    from src.io_sources import observations_csv, sha256
    d = pd.DataFrame({'year': list(range(2019,2024)), 'who_region': ['AFR'] * 5,
                      'indicator_code': ['ECOLI_3GC_BSI'] * 5,
                      'statistic_type': ['who_unadjusted_regional_median'] * 5,
                      'resistance_pct': [10.,11.,12.,13.,14.]})
    base = {'who_region': 'AFR', 'indicator_code': 'ECOLI_3GC_BSI',
            'statistic_type': 'who_unadjusted_regional_median'}
    row = {**base, 'target_year': 2023, 'actual': 14., 'train_end_year': 2022,
           'phase': 'holdout', 'record_type': 'backtest_prediction'}
    for model in ('naive', 'linear', 'ridge'):
        row.update({model + '_pred': 13., model + '_raw': 13., model + '_clipped': False})
    backtests = pd.DataFrame([row])
    forecasts = pd.DataFrame([{**base, 'target_year': 2024, 'last_observed_year': 2023,
                               'model': 'naive', 'prediction': 14., 'raw_prediction': 14.,
                               'clipped': False, 'record_type': 'experimental_forecast',
                               'label': 'Synthetic test only'}])
    meta = {'schema_version': 1, 'execution_environment': 'google_colab',
            'indicator_code': 'ECOLI_3GC_BSI', 'statistic_type': 'who_unadjusted_regional_median',
            'holdout_year': 2023, 'observations_sha256': sha256(observations_csv(d))}
    return d, backtests, forecasts, meta


def result_zip(backtests, forecasts, metadata):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('backtests.csv', backtests.to_csv(index=False))
        archive.writestr('forecasts.csv', forecasts.to_csv(index=False))
        archive.writestr('model_metrics.csv', score_predictions(backtests).to_csv(index=False))
        archive.writestr('model_metadata.json', json.dumps(metadata))
    return buffer.getvalue()


def test_valid_bundle_round_trip(synthetic_result_contract):
    d, b, f, meta = synthetic_result_contract
    result = load_results(result_zip(b, f, meta), d)
    assert result['metrics'].n.tolist() == [1,1,1]
    assert result['forecasts'].prediction.tolist() == [14.]


@pytest.mark.parametrize('field,value', [('actual', 99), ('train_end_year', 2023),
                                         ('naive_raw', 101), ('naive_clipped', True)])
def test_invalid_backtest_rejected(synthetic_result_contract, field, value):
    d, b, f, meta = synthetic_result_contract
    b.loc[0, field] = value
    with pytest.raises(ValueError):
        load_results(result_zip(b, f, meta), d)


def test_sparse_forecast_rejected(synthetic_result_contract):
    d, b, f, meta = synthetic_result_contract
    f.loc[0, 'target_year'] = 2026
    with pytest.raises(ValueError, match='one year'):
        load_results(result_zip(b, f, meta), d)


def test_backtest_rejects_stale_history(synthetic_result_contract):
    from src.io_sources import observations_csv, sha256
    d, b, f, meta = synthetic_result_contract
    d.loc[:3, 'year'] = [2010,2011,2012,2013]
    meta['observations_sha256'] = sha256(observations_csv(d))
    with pytest.raises(ValueError, match='chronology|eligible'):
        load_results(result_zip(b, f.iloc[:0], meta), d)


def test_holdout_must_match_latest_year(synthetic_result_contract):
    d, b, f, meta = synthetic_result_contract
    meta['holdout_year'] = 2022
    b.loc[0, 'phase'] = 'validation'
    with pytest.raises(ValueError, match='holdout'):
        load_results(result_zip(b, f, meta), d)


def test_omitted_eligible_cases_rejected(synthetic_result_contract):
    d, b, f, meta = synthetic_result_contract
    with pytest.raises(ValueError, match='eligible'):
        load_results(result_zip(b.iloc[:0], f, meta), d)


def test_app_reviews_returned_synthetic_results(synthetic_result_contract):
    """Test-only handwritten result bundle; never train an estimator here."""
    from pathlib import Path
    from src.dashboard import StudyService
    from src.io_sources import observations_csv, sha256
    d, b, f, meta = synthetic_result_contract
    d['source_revision'] = '2025-09-25'
    d['source_downloaded_at'] = '2026-10-29T12:00:00+00:00'
    d['country_count'] = pd.NA
    meta['observations_sha256'] = sha256(observations_csv(d))
    service = StudyService(Path('tests/fixtures/no-project'))
    service.data = d
    service.results = load_results(result_zip(b, f, meta), d)
    snapshot = service.snapshot()
    assert snapshot['status'] == 'ready'
    assert snapshot['metrics'][0]['n'] == 1
    assert len(snapshot['forecasts']) == 1
