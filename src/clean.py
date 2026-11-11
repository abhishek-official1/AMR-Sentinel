"""Strict, explicit adapters for regional WHO chart exports."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

REGIONS = {'AFR': 'Africa', 'AMR': 'Americas', 'EMR': 'Eastern Mediterranean',
           'EUR': 'Europe', 'SEAR': 'South-East Asia', 'WPR': 'Western Pacific'}
INDICATORS = {'ECOLI_3GC_BSI': 'Escherichia coli', 'MRSA_BSI': 'Staphylococcus aureus'}
KEY = ['year', 'who_region', 'indicator_code', 'statistic_type']
STATISTICS = ('who_unadjusted_regional_median', 'derived_country_median')


def normalize_and_validate(raw, config, filename):
    """Map named source fields; scale is declared, never guessed from magnitudes."""
    if not isinstance(config, dict):
        raise ValueError('Mapping JSON must contain an object, not a list or scalar.')
    if config.get('percentage_scale') not in ('percent', 'fraction'):
        raise ValueError('percentage_scale must explicitly be percent or fraction; ambiguous scale rejected.')
    required = ['indicator_code', 'statistic_type', 'source_id', 'source_url',
                'source_revision', 'source_downloaded_at', 'definition_note', 'filters']
    for field in required:
        if not config.get(field):
            raise ValueError(f'Missing provenance/definition: {field}')
    if config['indicator_code'] not in INDICATORS:
        raise ValueError('Unrecognized indicator_code; only ECOLI_3GC_BSI and MRSA_BSI are supported.')
    if config['statistic_type'] not in STATISTICS:
        raise ValueError('Unsupported statistic_type: adjusted estimates must remain separate.')
    host = urlparse(config['source_url']).hostname or ''
    if not (host == 'who.int' or host.endswith('.who.int') or host == 'worldhealthorg.shinyapps.io'):
        raise ValueError('source_url must be a cited official WHO source page.')
    try:
        timestamp = datetime.fromisoformat(config['source_downloaded_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('source_downloaded_at requires an ISO-8601 timestamp with timezone.') from None
    if raw.empty:
        raise ValueError('Input has no observation rows.')
    if raw.columns.duplicated().any():
        raise ValueError('Duplicate source column names are ambiguous.')
    mapping = config.get('columns', {})
    allowed = {'year', 'who_region', 'resistance_pct', 'country_count', 'numerator_resistant', 'denominator_tested'}
    if not isinstance(mapping, dict) or set(mapping) - allowed:
        raise ValueError('Unsupported mapped fields. Select a single indicator/statistic in the original WHO export.')
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Each mapped source field must have one meaning.')
    for field in ('year', 'resistance_pct'):
        if field not in mapping:
            raise ValueError(f'Explicit column mapping required: {field}')
    missing = set(mapping.values()) - set(raw.columns)
    if missing:
        raise ValueError(f'Mapped columns missing: {sorted(missing)}. Available: {list(raw.columns)}')
    d = raw[list(mapping.values())].rename(columns={v: k for k, v in mapping.items()}).copy()
    if 'who_region' not in d:
        d['who_region'] = config.get('who_region')
    aliases = {k.casefold(): k for k in REGIONS}
    aliases.update({v.casefold(): k for k, v in REGIONS.items()})
    aliases.update({'south-east asia region': 'SEAR', 'western pacific region': 'WPR',
                    'african region': 'AFR', 'european region': 'EUR',
                    'region of the americas': 'AMR', 'eastern mediterranean region': 'EMR'})
    d['who_region'] = d.who_region.astype(str).str.strip().str.casefold().map(aliases)
    if d.who_region.isna().any():
        raise ValueError('Unrecognized WHO region; country/continent guessing is prohibited.')
    y = pd.to_numeric(d.year, errors='raise')
    if y.isna().any() or (~np.isfinite(y)).any() or (y % 1 != 0).any() or not y.between(1900, datetime.now().year).all():
        raise ValueError('year must contain integer observation years, no future observations.')
    d['year'] = y.astype(int)
    p = pd.to_numeric(d.resistance_pct, errors='raise')
    upper = 1 if config['percentage_scale'] == 'fraction' else 100
    if not p.dropna().between(0, upper).all():
        raise ValueError(f'resistance_pct outside declared scale [0,{upper}].')
    d['resistance_pct'] = p.astype(float) * (100 if upper == 1 else 1)
    for name in ('country_count', 'numerator_resistant', 'denominator_tested'):
        vals = pd.to_numeric(d[name], errors='raise') if name in d else pd.Series(float('nan'), index=d.index)
        if (vals.dropna() < 0).any() or (vals.dropna() % 1 != 0).any() or not np.isfinite(vals.dropna()).all():
            raise ValueError(f'{name}: count must be nonnegative integer or null.')
        d[name] = vals.astype('Int64')
    if (d.denominator_tested.dropna() == 0).any():
        raise ValueError('denominator_tested must be greater than zero when provided.')
    both = d.numerator_resistant.notna() & d.denominator_tested.notna()
    if (d.loc[both, 'numerator_resistant'] > d.loc[both, 'denominator_tested']).any():
        raise ValueError('resistant count exceeds tested count.')
    if config['statistic_type'] == 'derived_country_median':
        if d.country_count.isna().any() or (d.country_count < 5).any():
            raise ValueError('Derived medians require at least 5 verified reporting countries per row.')
        if not config.get('derivation_note') or not config.get('region_mapping_source'):
            raise ValueError('Derived medians require derivation_note and verified region_mapping_source.')
    # WHO chart time-series medians are only eligible with >=5 CTAs when known.
    low = d.country_count.notna() & (d.country_count < 5) & d.resistance_pct.notna()
    if low.any():
        raise ValueError('Regional medians with fewer than 5 contributing countries are ineligible.')
    d['country_count_known'] = d.country_count.notna()
    d['sample_size_known'] = both
    for field in required:
        if field != 'filters':
            d[field] = config[field]
    d['infection_type'] = 'Bloodstream infection'
    d['pathogen'] = INDICATORS[config['indicator_code']]
    d['source_file'] = Path(filename).name
    d['coverage_note'] = config.get('coverage_note', 'Unknown counts do not establish WHO count-based eligibility.')
    d['record_type'] = 'observed'
    d = d.drop_duplicates()
    if d.duplicated(KEY).any():
        raise ValueError('Conflicting duplicate series/year rows. Resolve source ambiguity before importing.')
    return d.sort_values(KEY).reset_index(drop=True)


def main():
    from src.io_sources import import_files, write_processed
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', nargs='+', required=True, help='Untouched WHO regional CSV/XLSX files')
    parser.add_argument('--mapping', required=True, help='Explicit adapter JSON, applied to all supplied files')
    parser.add_argument('--root', default='.', help='Project output directory')
    args = parser.parse_args()
    config = json.loads(Path(args.mapping).read_text(encoding='utf-8'))
    data, manifest, raw_files = import_files([(Path(p).name, Path(p).read_bytes(), config) for p in args.input])
    write_processed(Path(args.root), data, manifest, raw_files)
    print(f'Imported {len(data)} rows. No predictive models were trained.')


if __name__ == '__main__':
    main()
