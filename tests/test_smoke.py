"""Smoke tests to verify basic package functionality."""

from importlib.metadata import version


def test_import_cimflow():
    """Verify cimflow package can be imported."""
    import cimflow
    assert cimflow is not None


def test_import_cli():
    """Verify CLI module can be imported."""
    from cimflow.cli import main
    assert main is not None


def test_version():
    """Verify version is accessible."""
    v = version("cimflow")
    assert v == "0.1.0"
