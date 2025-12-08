from typing import Optional
import importlib.metadata as im
import sys
import typer
import click

from . import compile_cmd, sim_cmd, run_cmd
from . import error_handler

# ────────────────────────────────────────────────────────────────
# Top-level Typer app
# invoke_without_command=True → running just `cimflow` shows help
# ────────────────────────────────────────────────────────────────
app = typer.Typer(
    help="CIMFlow - compile & simulate SRAM-based digital CIM",
    invoke_without_command=True,
    add_completion=True,   # opt-in later once your CLI stabilises
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)

# Register sub-commands
app.add_typer(compile_cmd.app, name="compile")
app.add_typer(sim_cmd.app,     name="sim")
app.add_typer(run_cmd.app,     name="run")

# ────────────────────────────────────────────────────────────────
# Root callback: global flags (e.g. --version, --debug)
# ────────────────────────────────────────────────────────────────
@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        is_eager=True,           # processed before any sub-command parsing
        help="Show CIMFlow version and exit",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode with full tracebacks and detailed error information",
    ),
):
    """
    Global options processed before any sub-command.
    Typing bare `cimflow` shows this help.
    """
    # Set debug mode and update Typer's pretty exceptions
    error_handler.set_debug_mode(debug)
    if debug:
        # In debug mode: use Typer's comprehensive pretty exceptions
        app.pretty_exceptions_show_locals = True
        app.pretty_exceptions_short = False
    else:
        # In non-debug mode: use our custom user-friendly error handler
        error_handler.install_exception_handler()

    # Store debug flag in context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug

    # Handle --version
    if version:
        typer.echo(f"CIMFlow {im.version('cimflow')}")
        raise typer.Exit()

    # If the user didn't invoke a sub-command, show the help
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def main_with_hints():
    """Main entry point with enhanced error messages."""
    # Allow --debug anywhere in the command line by moving it to the correct position
    # Typer requires global flags before subcommands, so we normalize the position here
    if '--debug' in sys.argv:
        debug_idx = sys.argv.index('--debug')
        # If --debug is not at position 1 (right after the command name), move it there
        if debug_idx != 1:
            sys.argv.pop(debug_idx)
            sys.argv.insert(1, '--debug')

    try:
        app()
    except (click.exceptions.UsageError, SystemExit):
        raise


if __name__ == "__main__":
    main_with_hints()
