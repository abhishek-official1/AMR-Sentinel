"""Validate Colab CSV/JSON outputs. Never import sklearn or unpickle models."""
import io
import json
import zipfile
import numpy as np
import pandas as pd
from src.io_sources import observations_csv, sha256
from src.analytics import tail_history
from src.clean import REGIONS, STATISTICS

MODELS = ('naive', 'linear', 'ridge')
RESULT_FILES = {'backtests.csv', 'model_metrics.csv', 'forecasts.csv', 'model_metadata.json'}


def score_predictions(rows):
    """Three-way comparison on identical cases; baseline-only comparison if no Ridge."""
    if rows.empty:
        return pd.DataFrame(columns=['model', 'mae_pp', 'rmse_pp', 'n', 'comparison'])
    models = list(MODELS) if rows.ridge_pred.notna().any() else ['naive', 'linear']
    shared = rows.dropna(subset=['actual'] + [m + '_pred' for m in models])
    scores = []
    for model in models:
        if shared.empty:
            continue
        err = shared[model + '_pred'] - shared.actual
        scores.append({'model': model, 'mae_pp': float(err.abs().mean()),
                       'rmse_pp': float(np.sqrt((err ** 2).mean())), 'n': len(shared),
                       'comparison': 'matched_three_models' if len(models) == 3 else 'matched_baselines'})
    return pd.DataFrame(scores, columns=['model', 'mae_pp', 'rmse_pp', 'n', 'comparison'])


def load_results(payload, observations, expected_hash=None):
    expected_hash = expected_hash or sha256(observations_csv(observations))
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len({e.filename for e in entries}) != len(entries) or any(e.filename not in RESULT_FILES for e in entries):
                raise ValueError('Unexpected archive entries; use the Colab results ZIP, without models.')
            if sum(e.file_size for e in entries) > 25_000_000:
                raise ValueError('Result archive exceeds 25 MB.')
            metadata = json.loads(archive.read('model_metadata.json'))
            if metadata.get('observations_sha256') != expected_hash:
                raise ValueError('Results dataset does not match the currently imported observations.')
            if set(e.filename for e in entries) != RESULT_FILES:
                raise ValueError('Missing result files in Colab archive.')
            tables = {name: pd.read_csv(io.BytesIO(archive.read(name))) for name in RESULT_FILES if name.endswith('.csv')}
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f'Invalid Colab results bundle: {exc}') from exc
    if metadata.get('schema_version') != 1 or metadata.get('execution_environment') != 'google_colab':
        raise ValueError('Results require the supported Colab metadata contract.')
    if metadata.get('indicator_code') != 'ECOLI_3GC_BSI' or metadata.get('statistic_type') not in STATISTICS:
        raise ValueError('Unrecognized modeling target or statistic.')
    target = observations[(observations.indicator_code == metadata['indicator_code']) &
                          (observations.statistic_type == metadata['statistic_type'])]
    backtests, forecasts = tables['backtests.csv'], tables['forecasts.csv']
    base = ['who_region', 'indicator_code', 'statistic_type', 'target_year', 'record_type']
    diagnostics = [model + suffix for model in MODELS for suffix in ('_raw', '_clipped')]
    contracts = [(backtests, base + ['actual', 'naive_pred', 'linear_pred', 'ridge_pred', 'phase', 'train_end_year'] + diagnostics),
                 (forecasts, base + ['model', 'prediction', 'raw_prediction', 'clipped', 'last_observed_year'])]
    for table, columns in contracts:
        if not set(columns) <= set(table.columns):
            raise ValueError(f'Result columns missing: {sorted(set(columns) - set(table.columns))}')
        if not table.who_region.isin(REGIONS).all():
            raise ValueError('Unknown result region.')
        if not table.indicator_code.eq(metadata['indicator_code']).all() or not table.statistic_type.eq(metadata['statistic_type']).all():
            raise ValueError('Mixed target definitions in results.')
        for column in ['target_year']:
            vals = pd.to_numeric(table[column], errors='raise')
            if vals.isna().any() or (vals % 1 != 0).any():
                raise ValueError('Result years must be integers.')
        for column in ('prediction', 'actual', 'naive_pred', 'linear_pred', 'ridge_pred'):
            if column in table:
                table[column] = pd.to_numeric(table[column], errors='raise')
                if not table[column].dropna().between(0, 100).all():
                    raise ValueError('Result percentage outside [0,100].')
    if backtests.duplicated(['who_region', 'target_year']).any() or forecasts.duplicated(['who_region', 'target_year', 'model']).any():
        raise ValueError('Duplicate result cases.')
    holdout = int(metadata['holdout_year'])
    if target.dropna(subset=['resistance_pct']).empty or holdout != int(target.dropna(subset=['resistance_pct']).year.max()):
        raise ValueError('Final holdout must equal the latest target observation year.')
    expected_cases = set()
    for obs in target.dropna(subset=['resistance_pct']).itertuples():
        prior = tail_history(target[(target.who_region == obs.who_region) & (target.year < obs.year)])
        if len(prior) >= 4 and prior.year.max() == obs.year - 1:
            expected_cases.add((obs.who_region, int(obs.year)))
    supplied_cases = set(zip(backtests.who_region, backtests.target_year.astype(int)))
    if supplied_cases != expected_cases:
        raise ValueError('Backtest cases do not match all eligible chronological observations; missing or ineligible cases found.')
    if not backtests.phase.isin(['validation', 'holdout']).all():
        raise ValueError('Unknown evaluation phase.')
    for row in backtests.itertuples():
        series = target[target.who_region == row.who_region]
        actual = series[series.year == row.target_year].resistance_pct.dropna()
        if len(actual) != 1 or not np.isclose(actual.iloc[0], row.actual):
            raise ValueError('Backtest actual does not match observed WHO value.')
        prior = tail_history(series[series.year < row.target_year])
        if row.train_end_year != row.target_year - 1 or len(prior) < 4 or prior.year.max() != row.target_year - 1:
            raise ValueError('Backtest chronology or history eligibility is invalid.')
        if (row.phase == 'holdout') != (row.target_year == holdout) or row.target_year > holdout:
            raise ValueError('Invalid holdout partition.')
        if row.record_type != 'backtest_prediction':
            raise ValueError('Backtests must be labeled as predictions.')
        for model in MODELS:
            predicted, raw = getattr(row, model + '_pred'), getattr(row, model + '_raw')
            flag = str(getattr(row, model + '_clipped')).lower()
            if flag not in ('true', 'false'):
                raise ValueError('Clipping flags must be boolean.')
            if pd.isna(predicted):
                if model != 'ridge' or not pd.isna(raw) or flag != 'false':
                    raise ValueError('Only unavailable Ridge may have a missing backtest prediction.')
                continue
            if not np.isfinite(raw) or not np.isclose(np.clip(raw, 0, 100), predicted) or (flag == 'true') != (raw < 0 or raw > 100):
                raise ValueError('Backtest bounding diagnostics do not match.')
    for row in forecasts.itertuples():
        series = target[target.who_region == row.who_region].dropna(subset=['resistance_pct'])
        if series.empty or len(tail_history(series)) < 4:
            raise ValueError('Forecast history is ineligible.')
        if row.last_observed_year != series.year.max() or row.target_year != row.last_observed_year + 1:
            raise ValueError('Forecast must be one year after the last observation.')
        if row.model not in MODELS or row.record_type != 'experimental_forecast':
            raise ValueError('Unrecognized forecast model or record type.')
        if not np.isfinite(row.raw_prediction) or not np.isclose(np.clip(row.raw_prediction, 0, 100), row.prediction):
            raise ValueError('Forecast bounding diagnostics do not match.')
        if str(row.clipped).lower() not in ('true', 'false'):
            raise ValueError('Forecast clipping flags must be boolean.')
        is_clipped = str(row.clipped).lower() == 'true'
        if is_clipped != (row.raw_prediction < 0 or row.raw_prediction > 100):
            raise ValueError('Forecast clipping flag does not match raw prediction.')
    # Recompute scores locally using arithmetic, never trust uploaded metric claims.
    scores = score_predictions(backtests[backtests.phase == 'holdout'])
    provided = tables['model_metrics.csv']
    if not set(scores.columns) <= set(provided.columns) or len(provided) != len(scores):
        raise ValueError('Metric file schema or number of models does not match held-out cases.')
    if len(scores):
        a, b = scores.sort_values('model'), provided.sort_values('model')
        if a.model.tolist() != b.model.tolist() or not np.allclose(a[['mae_pp', 'rmse_pp', 'n']], b[['mae_pp', 'rmse_pp', 'n']]):
            raise ValueError('Uploaded metrics disagree with matched holdout errors.')
    return {'metadata': metadata, 'backtests': backtests, 'forecasts': forecasts, 'metrics': scores}


def save_results(root, payload, observations):
    """Persist only verified plain-data outputs; never extract arbitrary ZIP paths."""
    verified = load_results(payload, observations)
    output = root / 'results'
    output.mkdir(exist_ok=True, parents=True)
    for name in ('backtests', 'forecasts', 'metrics'):
        filename = 'model_metrics.csv' if name == 'metrics' else name + '.csv'
        verified[name].to_csv(output / filename, index=False)
    (output / 'model_metadata.json').write_text(json.dumps(verified['metadata'], indent=2), encoding='utf-8')
    return verified


def load_saved_results(root, observations):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in RESULT_FILES:
            archive.writestr(name, (root / 'results' / name).read_bytes())
    return load_results(buffer.getvalue(), observations)


def main():
    import argparse
    from pathlib import Path
    from src.io_sources import load_saved
    parser = argparse.ArgumentParser(description='Validate Colab results and save CSV/JSON; no model fitting.')
    parser.add_argument('--input', required=True, help='Returned amr_colab_results.zip')
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    root = Path(args.root)
    observations, _, _ = load_saved(root)
    save_results(root, Path(args.input).read_bytes(), observations)
    print('Verified Colab results saved. No predictive model was loaded or trained.')


if __name__ == '__main__':
    main()
