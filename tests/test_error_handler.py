"""Tests for error_handler module - user-friendly error formatting."""

import subprocess
import pytest
from pydantic import BaseModel, ValidationError

from cimflow.cli.error_handler import (
    format_user_friendly_error,
    set_debug_mode,
    is_debug_mode,
    _format_file_not_found_error,
    _format_subprocess_error,
    _format_validation_error,
    _format_permission_error,
    _format_generic_error,
)


class TestDebugMode:
    """Tests for debug mode flag."""

    def test_default_debug_mode_off(self):
        """Debug mode should be off by default."""
        set_debug_mode(False)  # Reset
        assert is_debug_mode() is False

    def test_can_enable_debug_mode(self):
        """Should be able to enable debug mode."""
        set_debug_mode(True)
        assert is_debug_mode() is True
        set_debug_mode(False)  # Reset

    def test_can_disable_debug_mode(self):
        """Should be able to disable debug mode."""
        set_debug_mode(True)
        set_debug_mode(False)
        assert is_debug_mode() is False


class TestFormatFileNotFoundError:
    """Tests for FileNotFoundError formatting."""

    def test_onnx_file_suggestion(self):
        """Should provide ONNX-specific suggestions."""
        exc = FileNotFoundError("model.onnx")
        exc.filename = "model.onnx"

        msg = _format_file_not_found_error(exc)

        assert "model.onnx" in msg
        assert "model file path" in msg

    def test_json_file_suggestion(self):
        """Should provide JSON-specific suggestions."""
        exc = FileNotFoundError("config.json")
        exc.filename = "config.json"

        msg = _format_file_not_found_error(exc)

        assert "config.json" in msg
        assert "configuration file" in msg

    def test_tool_paths_suggestion(self):
        """Should provide tool_paths.json specific help."""
        exc = FileNotFoundError("tool_paths.json")
        exc.filename = "config/tool_paths.json"

        msg = _format_file_not_found_error(exc)

        assert "tool_paths.json" in msg
        assert "cp config_templates" in msg

    def test_generic_file_suggestion(self):
        """Should provide generic suggestion for other files."""
        exc = FileNotFoundError("somefile.txt")
        exc.filename = "somefile.txt"

        msg = _format_file_not_found_error(exc)

        assert "Verify the file path" in msg

    def test_debug_hint_included(self):
        """Should include hint about --debug flag."""
        exc = FileNotFoundError("test.txt")
        exc.filename = "test.txt"

        msg = _format_file_not_found_error(exc)

        assert "--debug" in msg


class TestFormatSubprocessError:
    """Tests for subprocess error formatting."""

    def test_basic_subprocess_error(self):
        """Should format basic subprocess error."""
        exc = subprocess.CalledProcessError(1, ["some-command", "arg"])

        msg = _format_subprocess_error(exc)

        assert "some-command" in msg
        assert "Exit code: 1" in msg

    def test_memory_overflow_detection(self):
        """Should detect memory overflow errors."""
        exc = subprocess.CalledProcessError(1, ["compiler"])
        exc.stderr = b"ERROR: Memory address overflow detected"

        msg = _format_subprocess_error(exc)

        assert "Memory" in msg
        assert "batch size" in msg.lower() or "memory" in msg.lower()

    def test_file_not_found_detection(self):
        """Should detect file not found errors in output."""
        exc = subprocess.CalledProcessError(1, ["simulator"])
        exc.stderr = b"Error: No such file or directory: /path/to/file"

        msg = _format_subprocess_error(exc)

        assert "Missing file" in msg or "file" in msg.lower()

    def test_config_error_detection(self):
        """Should detect configuration errors."""
        exc = subprocess.CalledProcessError(1, ["tool"])
        exc.stderr = b"Config error: invalid parameter"

        msg = _format_subprocess_error(exc)

        assert "config" in msg.lower()

    def test_compiler_specific_suggestions(self):
        """Should provide compiler-specific suggestions."""
        exc = subprocess.CalledProcessError(1, ["cim-compiler", "network"])
        exc.stderr = None
        exc.stdout = None

        msg = _format_subprocess_error(exc)

        assert "compiler" in msg.lower()

    def test_simulator_specific_suggestions(self):
        """Should provide simulator-specific suggestions."""
        exc = subprocess.CalledProcessError(1, ["cim-simulator"])
        exc.stderr = None
        exc.stdout = None

        msg = _format_subprocess_error(exc)

        assert "simulator" in msg.lower()

    def test_truncates_long_output(self):
        """Should truncate very long error output."""
        exc = subprocess.CalledProcessError(1, ["cmd"])
        exc.stderr = b"\n".join([f"Line {i}".encode() for i in range(100)])

        msg = _format_subprocess_error(exc)

        # Should not include all 100 lines
        assert msg.count("Line") < 20


class TestFormatValidationError:
    """Tests for Pydantic ValidationError formatting."""

    def test_formats_validation_errors(self):
        """Should format Pydantic validation errors nicely."""
        class TestModel(BaseModel):
            required_field: str
            number_field: int

        try:
            TestModel(required_field=None, number_field="not a number")
        except ValidationError as exc:
            msg = _format_validation_error(exc)

            assert "Configuration validation failed" in msg
            assert "Field:" in msg
            assert "--debug" in msg

    def test_shows_field_path(self):
        """Should show the field path in error."""
        class Inner(BaseModel):
            value: int

        class Outer(BaseModel):
            inner: Inner

        try:
            Outer(inner={"value": "not int"})
        except ValidationError as exc:
            msg = _format_validation_error(exc)

            assert "inner" in msg or "value" in msg


class TestFormatPermissionError:
    """Tests for PermissionError formatting."""

    def test_formats_permission_error(self):
        """Should format permission errors with suggestions."""
        exc = PermissionError("Permission denied: /path/to/file")

        msg = _format_permission_error(exc)

        assert "Permission denied" in msg
        assert "write permissions" in msg
        assert "--debug" in msg


class TestFormatGenericError:
    """Tests for generic error formatting."""

    def test_formats_generic_error(self):
        """Should format unknown errors."""
        exc = RuntimeError("Something went wrong")

        msg = _format_generic_error(exc)

        assert "RuntimeError" in msg
        assert "Something went wrong" in msg
        assert "--debug" in msg


class TestFormatUserFriendlyError:
    """Tests for the main error dispatch function."""

    def test_dispatches_file_not_found(self):
        """Should dispatch FileNotFoundError correctly."""
        exc = FileNotFoundError("test.txt")
        exc.filename = "test.txt"

        msg = format_user_friendly_error(FileNotFoundError, exc)

        assert "File not found" in msg

    def test_dispatches_subprocess_error(self):
        """Should dispatch CalledProcessError correctly."""
        exc = subprocess.CalledProcessError(1, ["cmd"])

        msg = format_user_friendly_error(subprocess.CalledProcessError, exc)

        assert "Command failed" in msg

    def test_dispatches_permission_error(self):
        """Should dispatch PermissionError correctly."""
        exc = PermissionError("denied")

        msg = format_user_friendly_error(PermissionError, exc)

        assert "Permission denied" in msg

    def test_returns_none_for_typer_exit(self):
        """Should return None for expected exits."""
        import typer

        exc = typer.Exit(0)
        msg = format_user_friendly_error(typer.Exit, exc)

        assert msg is None

    def test_returns_none_for_keyboard_interrupt(self):
        """Should return None for keyboard interrupt."""
        exc = KeyboardInterrupt()
        msg = format_user_friendly_error(KeyboardInterrupt, exc)

        assert msg is None

    def test_handles_unknown_errors(self):
        """Should handle unknown error types."""
        exc = ZeroDivisionError("division by zero")

        msg = format_user_friendly_error(ZeroDivisionError, exc)

        assert "ZeroDivisionError" in msg
