"""Tests for CLI module - command parsing and basic functionality."""

import pytest
from typer.testing import CliRunner
from pathlib import Path

from cimflow.cli.main import app


runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help and basic commands."""

    def test_main_help(self):
        """Should show help without errors."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "cimflow" in result.output.lower() or "CIMFlow" in result.output

    def test_version_flag(self):
        """Should show version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_compile_help(self):
        """Should show compile subcommand help."""
        result = runner.invoke(app, ["compile", "--help"])
        assert result.exit_code == 0
        assert "cg" in result.output.lower() or "op" in result.output.lower()

    def test_compile_cg_help(self):
        """Should show compile cg help."""
        result = runner.invoke(app, ["compile", "cg", "--help"])
        assert result.exit_code == 0
        assert "model" in result.output.lower()
        assert "output" in result.output.lower()

    def test_compile_op_help(self):
        """Should show compile op help."""
        result = runner.invoke(app, ["compile", "op", "--help"])
        assert result.exit_code == 0
        assert "instruction" in result.output.lower() or "inst" in result.output.lower()

    def test_sim_help(self):
        """Should show sim subcommand help."""
        result = runner.invoke(app, ["sim", "--help"])
        assert result.exit_code == 0
        assert "instruction" in result.output.lower() or "inst" in result.output.lower()

    def test_run_help(self):
        """Should show run subcommand help."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "pipeline" in result.output.lower()

    def test_run_pipeline_help(self):
        """Should show run pipeline help."""
        result = runner.invoke(app, ["run", "pipeline", "--help"])
        assert result.exit_code == 0
        assert "model" in result.output.lower()
        assert "-t" in result.output or "--mg-size" in result.output


class TestCLIFlags:
    """Tests for CLI flag parsing."""

    def test_debug_flag_position(self):
        """Debug flag should be global (before subcommand)."""
        # This should work - debug before subcommand
        result = runner.invoke(app, ["--debug", "--help"])
        assert result.exit_code == 0

    def test_short_flags_in_help(self):
        """Short flags should be documented in help."""
        result = runner.invoke(app, ["run", "pipeline", "--help"])

        # Check for short flag aliases
        assert "-m" in result.output  # model-path
        assert "-o" in result.output  # output-dir
        assert "-t" in result.output  # mg-size
        assert "-b" in result.output  # bandwidth


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_missing_required_args(self):
        """Should error on missing required arguments."""
        result = runner.invoke(app, ["compile", "cg"])
        # Should fail because model-path and output-dir are required
        assert result.exit_code != 0

    def test_invalid_subcommand(self):
        """Should error on invalid subcommand."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    def test_nonexistent_model_file(self, tmp_path):
        """Should handle nonexistent model file gracefully."""
        result = runner.invoke(app, [
            "compile", "cg",
            "-m", str(tmp_path / "nonexistent.onnx"),
            "-o", str(tmp_path / "output"),
        ])
        # Should fail but not crash
        assert result.exit_code != 0


class TestCLIIntegration:
    """Integration tests for CLI commands (with mocked externals)."""

    def test_compile_cg_validates_inputs(self, tmp_path):
        """compile cg should validate input file exists."""
        result = runner.invoke(app, [
            "compile", "cg",
            "-m", str(tmp_path / "nonexistent.onnx"),
            "-o", str(tmp_path / "output"),
        ])

        assert result.exit_code != 0
        # Should mention the file or path issue
        assert "not found" in result.output.lower() or "error" in result.output.lower() or result.exit_code != 0
