"""Review the user's latest notebook through pure headers/data checks only."""
import ast
import json
import re
from pathlib import Path
import pandas as pd

NOTEBOOK = Path('notebooks/AMR_Sentinel_Public.ipynb')


def assets():
    notebook = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    values = {}
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        for node in ast.parse(''.join(cell['source'])).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            values[target.id] = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            pass
    if isinstance(values.get('old'), str) and isinstance(values.get('new'), str):
        values['acquisition_source'] = values['acquisition_source'].replace(values['old'], values['new'], 1)
    return notebook, values


def test_actual_who_percentage_header_is_supported():
    if not Path('notebooks/745F475_ALL_LATEST.csv').exists():
        import pytest
        pytest.skip('Optional WHO source CSV is not included in the repository')
    _, values = assets()
    tree = ast.parse(values['acquisition_source'])
    lookup = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pick_column')
    namespace = {'re': re}
    exec(compile(ast.Module(body=[lookup], type_ignores=[]), '<pure header lookup>', 'exec'), namespace)
    loader = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'load_uploaded_national')
    assignment = next(n for n in ast.walk(loader) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'value_col' for t in n.targets))
    candidates = ast.literal_eval(assignment.value.args[1])
    assert namespace['pick_column'](pd.read_csv('notebooks/745F475_ALL_LATEST.csv', nrows=1), candidates) == 'RATE_PER_100_N'


def test_kernel_does_not_import_scientific_packages():
    notebook, _ = assets()
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        for node in ast.parse(''.join(cell['source'])).body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or '']
                assert not any(name.split('.')[0] in ('numpy', 'pandas', 'scipy', 'sklearn') for name in names)


def test_repeated_analysis_uses_a_fresh_work_directory():
    notebook, _ = assets()
    run = next(''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).startswith('ANALYSIS_SUCCEEDED = False'))
    assert 'uuid4().hex' in run
    assert 'exist_ok=False' in run


def test_real_regional_values_reproduce_from_exported_national_rows():
    root = Path('notebooks/amr_project_bundle/data')
    if not (root / 'processed/national_observations.csv').exists():
        import pytest
        pytest.skip('Optional Colab study export is not included in the repository')
    national = pd.read_csv(root / 'processed/national_observations.csv')
    observed = pd.read_csv(root / 'raw/derived_regional_input.csv')
    derived = national.groupby(['who_region', 'year'], as_index=False).agg(resistance_pct=('resistance_pct', 'median'), country_count=('country_code', 'nunique'))
    eligible = derived[derived.country_count >= 5].sort_values(['who_region', 'year']).reset_index(drop=True)
    pd.testing.assert_frame_equal(eligible, observed[eligible.columns].sort_values(['who_region', 'year']).reset_index(drop=True), check_dtype=False)


def test_training_remains_colab_only_and_time_ordered():
    _, values = assets()
    modeling = values['modeling_source']
    assert 'study.year < cutoff' in modeling
    assert 'study.year < target_year' in modeling
    assert 'random_split' not in modeling
    assert 'ColumnTransformer' in modeling and 'Pipeline' in modeling
    assert 'tune_before(holdout_year)' in modeling
