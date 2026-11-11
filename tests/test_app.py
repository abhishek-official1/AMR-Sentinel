"""The user-run Colab notebook stays readable and never executes in these tests."""
import ast
from pathlib import Path
import nbformat

NOTEBOOK = Path('notebooks/AMR_Sentinel_Public.ipynb')


def test_public_notebook_format_syntax_and_no_saved_outputs():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    code = [cell for cell in notebook.cells if cell.cell_type == 'code']
    assert 'google.colab' in code[0].source
    assert 'RuntimeError' in code[0].source
    for cell in code:
        tree = ast.parse(cell.source)
        assert cell.outputs == []
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                if any(isinstance(t, ast.Name) and (t.id.endswith('_source') or t.id == 'worker_prelude') for t in node.targets):
                    ast.parse(node.value.value)
