"""Descriptive statistics only; this module trains no forecasting model."""
import numpy as np
import pandas as pd
from src.clean import KEY, REGIONS


def single_definition(d):
    for col in ('indicator_code', 'statistic_type'):
        if d[col].nunique() > 1:
            raise ValueError(f'Select a single {col} before calculating a series.')


def tail_history(d):
    d = d.dropna(subset=['resistance_pct']).sort_values('year')
    if d.empty:
        return d
    breaks = d.year.diff().ne(1)
    return d.loc[breaks.cumsum() == breaks.cumsum().iloc[-1]]


def annual_changes(d):
    d = d.sort_values(KEY).copy()
    groups = d.groupby(['who_region', 'indicator_code', 'statistic_type'])
    d['annual_change_pp'] = groups.resistance_pct.diff().where(groups.year.diff().eq(1))
    return d


def summarize(d):
    single_definition(d)
    if d.who_region.nunique() > 1:
        raise ValueError('Select one WHO region.')
    valid = d.dropna(subset=['resistance_pct']).sort_values('year')
    tail = tail_history(valid)
    years = valid.year.astype(int).tolist()
    missing = sorted(set(range(min(years), max(years) + 1)) - set(years)) if years else []
    slope = None
    direction = 'Insufficient data'
    if len(tail) >= 3:
        x = tail.year.to_numpy(dtype=float)
        y = tail.resistance_pct.to_numpy(dtype=float)
        x = x - x.mean()
        slope = float(np.dot(x, y - y.mean()) / np.dot(x, x))
        direction = 'Increasing' if slope >= 1 else 'Decreasing' if slope <= -1 else 'Inconclusive/near-flat'
    return {'n_observations': len(valid), 'last_year': max(years) if years else None,
            'missing_years': ', '.join(map(str, missing)), 'consecutive_years': len(tail),
            'years_used': ', '.join(tail.year.astype(str)), 'slope_pp_per_year': slope,
            'direction': direction, 'forecast_eligible': len(tail) >= 4,
            'eligibility_reason': 'Eligible for exploratory baselines; Ridge eligibility decided in Colab'
            if len(tail) >= 4 else 'Insufficient data to forecast: require 4 consecutive observed years ending at last observation',
            'status': 'Observed' if years else 'Data unavailable',
            'unknown_country_counts': int(valid.country_count.isna().sum()) if 'country_count' in valid else len(valid)}


def quality_report(d):
    rows = []
    for (indicator, statistic), g in d.groupby(['indicator_code', 'statistic_type']):
        for region in REGIONS:
            s = g[g.who_region == region]
            rows.append({'who_region': region, 'indicator_code': indicator, 'statistic_type': statistic,
                         **summarize(s)})
    return pd.DataFrame(rows)
