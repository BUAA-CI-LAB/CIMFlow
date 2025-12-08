from __future__ import annotations

import typer
import time
from pathlib import Path
from ..simulator import driver
from ..config import load_global_paths

app = typer.Typer(
    help="Simulator commands",
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    inst_file: Path = typer.Option(..., "-i", "--inst-file", help="Instruction file", show_default=False),
    output_dir: Path = typer.Option(..., "-o", "--output-dir", help="Simulation output directory", show_default=False),
    config: Path = typer.Option(None, "-cf", "--config", help="Hardware configuration file (auto-resolved from T/B if not provided)", show_default=False),
    config_dir: Path = typer.Option(None, "-cd", "--config-dir", help="Directory containing hardware configs (overrides tool_paths.json)", show_default=False),
    t: int = typer.Option(None, "-t", "--mg-size", help="Macro group size (required for auto-resolving config)"),
    b: int = typer.Option(None, "-b", "--bandwidth", help="NoC flit size/bandwidth (required for auto-resolving config)"),
    profile: str = typer.Option("", "-p", "--profile", help="Enable profiling. Use --profile=from-config to load from tool_paths.json, or --profile=<path> for custom config", show_default=False),
    simulator_bin: str = typer.Option(driver.DEFAULT_SIM_BIN, help="cim-simulator executable", show_default=True),
    paths_cfg: Path = typer.Option(None, help="Path to tool_paths.json (default: config/tool_paths.json)", show_default=False),
    log_level: str | None = typer.Option(None, "-l", "--log-level", help="Logging level: TRACE, DEBUG, VERBOSE, INFO (default), WARNING, ERROR. Auto-set to DEBUG with --debug", show_default=False),
):
    """Run simulation on a single instruction file."""
    # If invoked as a subcommand group (no args), show help
    if ctx.invoked_subcommand is not None:
        return

    # Coordinate log_level with --debug flag
    if log_level is None and ctx.obj and ctx.obj.get('debug'):
        log_level = "DEBUG"

    # Determine config path with priority:
    # 1. Explicit --config provided
    # 2. CLI --config-dir + T/B (auto-resolve with CLI config_dir)
    # 3. tool_paths.json config_dir + T/B (auto-resolve with default config_dir)
    # 4. Error if neither is available
    config_path = None

    if config is not None:
        # User provided explicit config
        config_path = Path(config).expanduser().resolve()
        if not config_path.exists():
            typer.secho(f"Error: Config file not found: {config_path}", fg="red", err=True)
            raise typer.Exit(1)
    else:
        # Try auto-resolution
        if t is not None and b is not None:
            from ..config import resolve_config_path

            # Determine which config_dir to use
            effective_config_dir = None
            if config_dir is not None:
                # CLI override
                effective_config_dir = Path(config_dir).expanduser().resolve()
                if not effective_config_dir.exists():
                    typer.secho(f"Error: Config directory not found: {effective_config_dir}", fg="red", err=True)
                    raise typer.Exit(1)
            else:
                # Use from tool_paths.json
                try:
                    paths = load_global_paths(paths_cfg)
                    effective_config_dir = paths.config_dir
                    # Also load simulator_bin if not provided
                    if simulator_bin == driver.DEFAULT_SIM_BIN:
                        simulator_bin = paths.simulator_bin
                except FileNotFoundError as e:
                    typer.secho(f"Error: Cannot load tool_paths.json: {e}", fg="red", err=True)
                    raise typer.Exit(1)

            try:
                config_path = resolve_config_path(effective_config_dir, t, b)
                typer.secho(f"Using auto-resolved config: {config_path.name}", fg="cyan")
            except FileNotFoundError as e:
                typer.secho(f"Error: {e}", fg="red", err=True)
                raise typer.Exit(1)
        else:
            typer.secho(
                "Error: Hardware config required. Either:\n"
                "  → Provide -cf/--config with explicit config file path, OR\n"
                "  → Provide --t and --b (with optional -cd/--config-dir) for auto-resolution",
                fg="red", err=True
            )
            raise typer.Exit(1)

    # Handle profiling configuration using shared utility
    from ..config import resolve_profile_config
    enable_profiling, profiler_cfg_path = resolve_profile_config(
        profile=profile,
        paths_cfg=paths_cfg,
    )

    # Load simulator_bin if not provided
    if simulator_bin == driver.DEFAULT_SIM_BIN:
        try:
            paths = load_global_paths(paths_cfg)
            simulator_bin = paths.simulator_bin
        except FileNotFoundError:
            typer.secho("Warning: Using default simulator binary path", fg="yellow", err=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / f"simulation_{inst_file.stem}.txt"
    typer.secho("=== Simulation started ===", fg="bright_blue")
    start_time = time.perf_counter()
    profiler_output_path = driver.run_simulation(
        inst_file,
        config_path,
        report,
        enable_profiling=enable_profiling,
        profiler_cfg=profiler_cfg_path,
        simulator_bin=simulator_bin,
        log_level=log_level,
    )
    elapsed = time.perf_counter() - start_time
    typer.secho(f"=== Simulation finished in {elapsed:.2f}s ===", fg="green")
    typer.echo(f"Report: {report}")
    if profiler_output_path is not None:
        typer.secho(f"Profiler output: {profiler_output_path}", fg="cyan")
