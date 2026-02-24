"""Test that all Airflow DAGs parse without errors.

These tests validate DAG structure without requiring a running Airflow instance.
They import DAG files and check basic properties.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

DAGS_DIR = Path(__file__).parent.parent / "airflow" / "dags"

# Mock airflow modules so tests run without airflow installed
airflow_mock = MagicMock()
sys.modules.setdefault("airflow", airflow_mock)
sys.modules.setdefault("airflow.operators", MagicMock())
sys.modules.setdefault("airflow.operators.bash", MagicMock())


# Make DAG context manager work with mocked airflow
class MockDAG:
    def __init__(self, **kwargs):
        self.dag_id = kwargs.get("dag_id", "unknown")
        self.default_args = kwargs.get("default_args", {})
        self.description = kwargs.get("description", "")
        self.schedule = kwargs.get("schedule")
        self.catchup = kwargs.get("catchup", True)
        self.tags = kwargs.get("tags", [])
        self.tasks = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


airflow_mock.DAG = MockDAG


def _load_dag_module(dag_file: Path):
    """Load a DAG file as a module."""
    # Ensure dag_helpers is importable
    if "dag_helpers" not in sys.modules:
        helpers_path = DAGS_DIR / "dag_helpers.py"
        spec = importlib.util.spec_from_file_location("dag_helpers", helpers_path)
        helpers_module = importlib.util.module_from_spec(spec)
        sys.modules["dag_helpers"] = helpers_module
        spec.loader.exec_module(helpers_module)

    spec = importlib.util.spec_from_file_location(dag_file.stem, dag_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DAG_FILES = sorted(DAGS_DIR.glob("dag_*.py"))
DAG_FILES = [f for f in DAG_FILES if f.name != "dag_helpers.py"]


@pytest.mark.parametrize("dag_file", DAG_FILES, ids=lambda f: f.stem)
def test_dag_parses_without_error(dag_file: Path):
    """Each DAG file should import without raising exceptions."""
    module = _load_dag_module(dag_file)
    assert module is not None


def test_dag_helpers_importable():
    """dag_helpers module should be importable."""
    helpers_path = DAGS_DIR / "dag_helpers.py"
    spec = importlib.util.spec_from_file_location("dag_helpers_test", helpers_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "DEFAULT_ARGS")
    assert hasattr(module, "extract_cmd")
    assert hasattr(module, "process_cmd")
    assert hasattr(module, "bulk_cmd")


def test_dag_helpers_commands():
    """dag_helpers should generate correct commands."""
    helpers_path = DAGS_DIR / "dag_helpers.py"
    spec = importlib.util.spec_from_file_location("dag_helpers_cmd", helpers_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert "camara_deputados" in module.extract_cmd("camara_deputados")
    assert "processing.run camara" in module.process_cmd("camara")
    assert "cnpj_downloader" in module.bulk_cmd("cnpj_downloader")


def test_all_expected_dags_exist():
    """All 7 source DAGs should exist."""
    expected = {
        "dag_camara.py",
        "dag_senado.py",
        "dag_tse.py",
        "dag_transparencia.py",
        "dag_cnpj.py",
        "dag_querido_diario.py",
        "dag_cnj.py",
    }
    actual = {f.name for f in DAG_FILES}
    assert expected == actual, f"Missing DAGs: {expected - actual}, Extra: {actual - expected}"
