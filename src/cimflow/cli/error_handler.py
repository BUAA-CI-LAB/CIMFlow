"""Custom exception handler for user-friendly error messages."""

from __future__ import annotations

import sys
import subprocess
from typing import Type
import typer
from pydantic import ValidationError


# Global debug flag, set by main.py
_debug_mode = False


def set_debug_mode(enabled: bool):
    """Enable or disable debug mode globally."""
    global _debug_mode
    _debug_mode = enabled


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return _debug_mode


def format_user_friendly_error(exc_type: Type[BaseException], exc_value: BaseException) -> str:
    """Format an exception as a user-friendly error message.

    Parameters
    ----------
    exc_type : Type[BaseException]
        The exception type
    exc_value : BaseException
        The exception instance

    Returns
    -------
    str
        A formatted, user-friendly error message
    """
    if isinstance(exc_value, FileNotFoundError):
        return _format_file_not_found_error(exc_value)
    elif isinstance(exc_value, subprocess.CalledProcessError):
        return _format_subprocess_error(exc_value)
    elif isinstance(exc_value, ValidationError):
        return _format_validation_error(exc_value)
    elif isinstance(exc_value, PermissionError):
        return _format_permission_error(exc_value)
    elif isinstance(exc_value, (typer.Exit, typer.Abort, KeyboardInterrupt)):
        # These are expected exits, don't format them
        return None
    else:
        return _format_generic_error(exc_value)


def _format_file_not_found_error(exc: FileNotFoundError) -> str:
    """Format FileNotFoundError as user-friendly message."""
    # Extract the filename from the exception attribute, fallback to "unknown"
    filename = exc.filename if getattr(exc, "filename", None) else "unknown"

    msg = f"Error: File not found: '{filename}'\n"

    # Provide context-specific suggestions
    if filename.endswith('.onnx'):
        msg += "   → Check that the model file path is correct\n"
        msg += "   → Use an absolute path or a path relative to the current directory\n"
    elif filename.endswith('.json'):
        msg += "   → Check that the configuration file exists\n"
        if 'tool_paths.json' in filename:
            msg += "   → Run: cp config_templates/tool_paths.json config/tool_paths.json\n"
            msg += "   → Then edit config/tool_paths.json with your actual paths\n"
    elif filename.endswith('.py'):
        msg += "   → Check that the compiler script path is correct\n"
        msg += "   → Verify the path in config/tool_paths.json\n"
    else:
        msg += "   → Verify the file path and try again\n"

    msg += "\n   Run with --debug for full error details"
    return msg


def _format_subprocess_error(exc: subprocess.CalledProcessError) -> str:
    """Format subprocess.CalledProcessError as user-friendly message."""
    cmd = exc.cmd[0] if isinstance(exc.cmd, list) and len(exc.cmd) > 0 else str(exc.cmd)

    # Get the error output
    error_output = None
    if exc.stderr:
        error_output = exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode('utf-8', errors='replace')
    elif exc.stdout:
        error_output = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode('utf-8', errors='replace')

    # Detect specific error patterns
    specific_error = None
    suggestions = []

    if error_output:
        error_lower = error_output.lower()

        # Memory overflow errors
        if 'memory address overflow' in error_lower or 'memory overflow' in error_lower:
            specific_error = "Memory address overflow detected"
            suggestions = [
                "The model requires more memory than the configured hardware supports",
                "Try reducing batch size or using a smaller model configuration",
                "Adjust hardware config parameters (T, K, B, C) if possible",
            ]

        # File not found errors
        elif 'no such file' in error_lower or 'cannot find' in error_lower or 'does not exist' in error_lower:
            specific_error = "Missing file or path"
            suggestions = [
                "Check that all input files exist",
                "Verify paths in your configuration files",
            ]

        # Configuration errors
        elif 'config' in error_lower and ('invalid' in error_lower or 'error' in error_lower):
            specific_error = "Configuration error"
            suggestions = [
                "Verify your hardware configuration file",
                "Check that all required config parameters are set correctly",
            ]

        # Compilation errors (syntax, type errors, etc.)
        elif 'syntax error' in error_lower or 'parse error' in error_lower:
            specific_error = "Compilation syntax error"
            suggestions = [
                "Check the input file format",
                "Verify the instruction/model file is valid",
            ]

    # Build the error message
    msg = f"Error: Command failed: {cmd}\n"
    msg += f"   Exit code: {exc.returncode}\n"

    # If no captured output, the error was printed to console in real-time
    if not error_output:
        msg += "\n   ⚠️  Check the error output above in the console\n"

    if specific_error:
        msg += f"\n   Issue: {specific_error}\n"

    # Show relevant error output
    if error_output:
        output_lines = error_output.strip().split('\n')

        # For specific errors, show only the most relevant lines
        if specific_error:
            # Find lines with ERROR, FATAL, or the specific pattern
            relevant_lines = [line for line in output_lines
                            if any(marker in line.upper() for marker in ['ERROR', 'FATAL', 'OVERFLOW', 'FAILED'])]
            if relevant_lines:
                msg += "\n   Error details:\n"
                for line in relevant_lines[:5]:  # Show up to 5 relevant lines
                    msg += f"   │ {line}\n"
            else:
                # Fall back to last few lines
                msg += "\n   Error output (last 5 lines):\n"
                for line in output_lines[-5:]:
                    msg += f"   │ {line}\n"
        else:
            # For generic errors, show last 10 lines
            if len(output_lines) > 10:
                msg += "\n   Error output (last 10 lines):\n"
                for line in output_lines[-10:]:
                    msg += f"   │ {line}\n"
            else:
                msg += "\n   Error output:\n"
                for line in output_lines:
                    msg += f"   │ {line}\n"

    # Add suggestions
    if suggestions:
        msg += "\n   Suggestions:\n"
        for suggestion in suggestions:
            msg += f"   → {suggestion}\n"
    else:
        # Generic suggestions based on command if no specific error detected
        if 'cim-compiler' in cmd or 'compiler' in cmd.lower():
            msg += "\n   → Check that the CIM compiler is built and in your PATH\n"
            msg += "   → Verify compiler_bin in config/tool_paths.json\n"
            msg += "   → Review the error output above for specific issues\n"
        elif 'simulator' in cmd.lower():
            msg += "\n   → Check that the simulator is built and accessible\n"
            msg += "   → Verify simulator_bin in config/tool_paths.json\n"

    msg += "\n   Run with --debug for full error details"
    return msg


def _format_validation_error(exc: ValidationError) -> str:
    """Format Pydantic ValidationError as user-friendly message."""
    msg = "Error: Configuration validation failed\n\n"

    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error['loc'])
        error_msg = error['msg']
        msg += f"   Field: {field}\n"
        msg += f"   Issue: {error_msg}\n\n"

    msg += "   → Check your configuration file for typos or missing fields\n"
    msg += "   → Compare with config_templates/ for the expected format\n"
    msg += "\n   Run with --debug for full error details"
    return msg


def _format_permission_error(exc: PermissionError) -> str:
    """Format PermissionError as user-friendly message."""
    msg = "Error: Permission denied\n"
    msg += f"   {exc}\n\n"
    msg += "   → Check that you have write permissions to the output directory\n"
    msg += "   → Try using a different output directory path\n"
    msg += "\n   Run with --debug for full error details"
    return msg


def _format_generic_error(exc: BaseException) -> str:
    """Format a generic error as user-friendly message."""
    msg = f"Error: {type(exc).__name__}\n"
    msg += f"   {exc}\n"
    msg += "\n   Run with --debug for full error details"
    return msg


def custom_excepthook(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback):
    """Custom exception hook for handling uncaught exceptions.

    Parameters
    ----------
    exc_type : Type[BaseException]
        The exception type
    exc_value : BaseException
        The exception instance
    exc_traceback
        The traceback object
    """
    # Don't handle expected exits
    if isinstance(exc_value, (typer.Exit, typer.Abort, KeyboardInterrupt)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    if is_debug_mode():
        # In debug mode, show full traceback (using default Python formatting)
        # Typer's rich tracebacks are shown via its own mechanisms
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        # In normal mode, show user-friendly error
        friendly_msg = format_user_friendly_error(exc_type, exc_value)
        if friendly_msg:
            typer.secho(friendly_msg, fg="red", err=True)
        else:
            # Fallback to default if we can't format it
            sys.__excepthook__(exc_type, exc_value, exc_traceback)


def install_exception_handler():
    """Install the custom exception handler."""
    sys.excepthook = custom_excepthook