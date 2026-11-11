"""All observations in this module are SYNTHETIC TEST FIXTURES, never WHO data."""
import pandas as pd
import pytest

from src.clean import normalize_and_validate
from src.analytics import annual_changes, summarize, quality_report


@pytest.fixture
def raw():
    return pd.DataFrame({'Year': [2019, 2020, 2021, 2022], 'Region': ['Africa'] * 4,
                         'Value': [10., 12., 14., 16.]})


@pytest.fixture
def config():
    return {'columns': {'year': 'Year', 'who_region': 'Region', 'resistance_pct': 'Value'},
            'percentage_scale': 'percent', 'indicator_code': 'ECOLI_3GC_BSI',
            'statistic_type': 'who_unadjusted_regional_median', 'source_id': 'S1',
            'source_url': 'https://worldhealthorg.shinyapps.io/glass-dashboard/',
            'source_revision': '2025-09-25', 'source_downloaded_at': '2026-10-29T12:00:00+00:00',
            'definition_note': 'Synthetic test only', 'filters': {'infection': 'Bloodstream infection'}}


def test_normalizes_and_preserves_unknown_counts(raw, config):
    d = normalize_and_validate(raw, config, 'test.csv')
    assert set(d.who_region) == {'AFR'}
    assert not d.country_count_known.any()
    assert not d.sample_size_known.any()
    assert d.resistance_pct.tolist() == [10, 12, 14, 16]


@pytest.mark.parametrize('value', [-1, 101, float('inf'), 'not a number'])
def test_rejects_invalid_percent(raw, config, value):
    raw['Value'] = raw['Value'].astype(object)
    raw.loc[0, 'Value'] = value
    with pytest.raises(ValueError):
        normalize_and_validate(raw, config, 'test.csv')


def test_requires_explicit_scale(raw, config):
    config.pop('percentage_scale')
    with pytest.raises(ValueError, match='scale'):
        normalize_and_validate(raw, config, 'test.csv')


def test_fraction_scale(raw, config):
    config['percentage_scale'] = 'fraction'
    raw['Value'] /= 100
    assert normalize_and_validate(raw, config, 'test.csv').resistance_pct.iloc[0] == 10


def test_duplicate_conflict_rejected(raw, config):
    extra = raw.iloc[[0]].copy()
    extra['Value'] = 99
    with pytest.raises(ValueError, match='Conflicting duplicate'):
        normalize_and_validate(pd.concat([raw, extra]), config, 'test.csv')


def test_exact_duplicates_collapsed(raw, config):
    assert len(normalize_and_validate(pd.concat([raw, raw]), config, 'test.csv')) == 4


def test_unknown_region_rejected(raw, config):
    raw.loc[0, 'Region'] = 'Atlantis'
    with pytest.raises(ValueError, match='region'):
        normalize_and_validate(raw, config, 'test.csv')


def test_missing_year_breaks_change_and_forecast(raw, config):
    d = normalize_and_validate(raw.drop(index=2), config, 'test.csv')
    assert pd.isna(annual_changes(d).iloc[-1].annual_change_pp)
    s = summarize(d)
    assert not s['forecast_eligible']
    assert s['direction'] == 'Insufficient data'
    assert s['missing_years'] == '2021'


def test_slope_and_quality(raw, config):
    d = normalize_and_validate(raw, config, 'test.csv')
    s = summarize(d)
    assert s['slope_pp_per_year'] == pytest.approx(2)
    assert s['direction'] == 'Increasing'
    assert s['forecast_eligible']
    q = quality_report(d)
    assert len(q) == 6
    assert q.loc[q.who_region == 'WPR', 'status'].iloc[0] == 'Data unavailable'


def test_definition_and_metadata_required(raw, config):
    config['statistic_type'] = 'adjusted_estimate'
    with pytest.raises(ValueError, match='statistic'):
        normalize_and_validate(raw, config, 'test.csv')


def test_invalid_count_rejected(raw, config):
    raw['Count'] = [-1, 4, 5, 6]
    config['columns']['country_count'] = 'Count'
    with pytest.raises(ValueError, match='count'):
        normalize_and_validate(raw, config, 'test.csv')


def test_mapping_cannot_overwrite_indicator_definitions(raw, config):
    raw['Metric'] = 'unverified metric'
    config['columns']['indicator_code'] = 'Metric'
    with pytest.raises(ValueError, match='Unsupported mapped'):
        normalize_and_validate(raw, config, 'test.csv')
