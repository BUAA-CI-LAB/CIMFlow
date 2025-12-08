from __future__ import annotations

import json
import shutil
import time
import typer
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from ..compiler import driver as comp_driver
from ..simulator import driver as sim_driver
from ..config import load_global_paths

app = typer.Typer(
    help="Run compile and simulation pipeline",
    context_settings={"help_option_names": ["-h", "--help"]},
)


class RunConfig(BaseModel):
    """Configuration for a single pipeline run within a batch."""

    model_path: Path
    config_path: Path | None = None  # Per-run explicit config file override
    t: int = 8
    k: int = 16
    b: int = 16
    c: int = 64
    batch_size: int = 8
    strategy: str = "dp"
    visualize: bool = False
    log_level: str | None = None
    profile: str = ""  # Profiling config: "" (disabled), "from-config", or path to custom config


class PipelineConfig(BaseModel):
    """Configuration for batch pipeline runs."""

    paths_cfg: Path | None = None
    output_dir: Path  # Shared by all runs in batch
    keep_ir: bool = False  # Shared by all runs in batch
    run_name: str = "batch"  # Name for batch output folder
    runs: list[RunConfig]  # Individual run configurations

def _run_single_pipeline(
    ctx: typer.Context,
    model_path: Path,
    output_dir: Path,
    t: int,
    k: int,
    b: int,
    c: int,
    batch_size: int,
    strategy: str,
    visualize: bool,
    keep_ir: bool,
    config: Path | None,
    config_dir: Path | None,
    profile: str,
    paths_cfg: Path | None,
    log_level: str | None,
) -> dict:
    """Internal helper to run a single pipeline and return run info.

    This function contains the actual pipeline logic and returns a dict
    with run information. Used by both the CLI command and batch processing.
    """
    # Coordinate log_level with --debug flag
    if log_level is None and ctx.obj and ctx.obj.get('debug'):
        log_level = "DEBUG"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir).expanduser().resolve()

    # Conditional output structure based on keep_ir flag
    if keep_ir:
        # Create timestamped folder for debugging with all artifacts
        run_dir = output_dir / f"{ts}_{model_path.stem}"
        run_dir.mkdir(parents=True, exist_ok=True)
        report_path_template = None  # Will use default in run_dir
    else:
        # Output directly to output_dir with timestamped report filename
        run_dir = output_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        model_name = model_path.stem
        # Report will be named with timestamp for easy identification
        report_path_template = f"simulation_report_{ts}_{model_name}"

    run_start = time.perf_counter()

    # Load global paths (required for all stages)
    try:
        paths = load_global_paths(paths_cfg)
    except FileNotFoundError:
        typer.secho("Error: Pipeline command requires config/tool_paths.json", fg="red", err=True)
        typer.secho("   → Run: cp config_templates/tool_paths.json config/tool_paths.json", fg="yellow")
        typer.secho("   → Then edit config/tool_paths.json with your actual paths", fg="yellow")
        raise typer.Exit(1)

    # Determine config path with priority:
    # Resolve config path using shared utility
    # Priority: 1. CLI --config, 2. CLI --config-dir + T/B, 3. tool_paths.json config_dir + T/B
    from ..config import resolve_or_use_config
    config_path = resolve_or_use_config(
        explicit_config=Path(config) if config else None,
        config_dir_override=Path(config_dir) if config_dir else None,
        global_paths=paths,
        t=t,
        b=b,
    )

    typer.secho("=== Compilation started ===", fg="bright_blue")
    stage_start = time.perf_counter()
    isa_file = comp_driver.compile_network(
        model_path=model_path,
        output_dir=run_dir,
        config_path=config_path,
        compiler_bin=paths.compiler_bin,
        t=t,
        k=k,
        b=b,
        c=c,
        batch_size=batch_size,
        strategy=strategy,
        visualize=visualize,
        keep_ir=keep_ir,
        log_level=log_level,
    )
    compile_time = time.perf_counter() - stage_start
    typer.secho(f"=== Compilation finished in {compile_time:.2f}s ===", fg="green")

    typer.secho("=== Simulation started ===", fg="bright_blue")
    stage_start = time.perf_counter()

    # Determine report path based on keep_ir flag
    if report_path_template:
        # Custom timestamped report name for direct output
        report = run_dir / f"{report_path_template}_{strategy}_T{t}_K{k}_B{b}_C{c}_batch{batch_size}.txt"
    else:
        # Default report name in timestamped folder
        report = run_dir / f"simulation_{isa_file.stem}.txt"

    # Handle profiling configuration using shared utility
    from ..config import resolve_profile_config
    enable_profiling, profiler_cfg_path = resolve_profile_config(
        profile=profile,
        paths_cfg=paths_cfg,
    )

    profiler_output_path = sim_driver.run_simulation(
        inst_file=isa_file,
        config_path=config_path,
        report=report,
        enable_profiling=enable_profiling,
        profiler_cfg=profiler_cfg_path,
        simulator_bin=paths.simulator_bin,
        log_level=log_level,
    )
    sim_time = time.perf_counter() - stage_start
    typer.secho(f"=== Simulation finished in {sim_time:.2f}s ===", fg="green")

    # Move profiler output to run_dir if profiling was enabled
    profiler_output_in_run_dir = None
    if profiler_output_path is not None and profiler_output_path.exists():
        # Create a consistent name following the same convention as other output files
        model_name = model_path.stem
        if keep_ir:
            # In keep_ir mode, folder has timestamp, so filename doesn't need it
            profiler_filename = f"profiling_{model_name}_{strategy}_T{t}_K{k}_B{b}_C{c}_batch{batch_size}.json"
        else:
            # Without keep_ir, no timestamped folder, so add timestamp to filename
            profiler_filename = f"profiling_{ts}_{model_name}_{strategy}_T{t}_K{k}_B{b}_C{c}_batch{batch_size}.json"
        profiler_dest = run_dir / profiler_filename

        # Move the profiler output to the run directory
        shutil.move(str(profiler_output_path), str(profiler_dest))
        profiler_output_in_run_dir = profiler_dest
        typer.secho(f"✓ Profiler output saved to {profiler_dest.name}", fg="cyan")

    # Clean up ISA file if not keeping intermediate files
    if not keep_ir:
        if isa_file.exists():
            isa_file.unlink()

    run_time = time.perf_counter() - run_start
    typer.secho(f"=== Pipeline finished in {run_time:.2f}s ===", fg="bright_green")

    # Build run info dict (always, for batch runs)
    info = {
        "model": str(model_path),
        "timestamp": ts,
        "strategy": strategy,
        "params": {"t": t, "k": k, "b": b, "c": c, "batch_size": batch_size},
        "files": {
            "report": report.name,
        },
        "stage_times": {
            "compilation": round(compile_time, 2),
            "simulation": round(sim_time, 2),
            "total": round(run_time, 2),
        },
    }

    # Add profiler output to info if it was copied to run_dir
    if profiler_output_in_run_dir is not None:
        info["files"]["profiling"] = profiler_output_in_run_dir.name

    # Only create run_info.json file when keeping intermediate files
    if keep_ir:
        # Add ISA file to info when keeping IR
        info["files"]["isa"] = isa_file.name

        # Add CG IR file to info if preserved
        # Use exact filename pattern (matches compiler's naming convention)
        model_name = model_path.stem
        expected_cg_ir = run_dir / f"instructions_{model_name}_{strategy}_T{t}_K{k}_B{b}_C{c}_batch{batch_size}.json"
        if expected_cg_ir.exists():
            info["files"]["cg_ir"] = expected_cg_ir.name
        else:
            typer.secho(f"⚠ Warning: Expected CG IR file not found: {expected_cg_ir.name}", fg="yellow")

        (run_dir / "run_info.json").write_text(json.dumps(info, indent=2))

    # Return info for batch processing
    return info


@app.command()
def pipeline(
    ctx: typer.Context,
    model_path: Path = typer.Option(..., "-m", "--model-path", help="Path to the ONNX model", show_default=False),
    output_dir: Path = typer.Option(..., "-o", "--output-dir", help="Base output directory", show_default=False),
    t: int = typer.Option(8, "-t", "--mg-size", help="Macro group size"),
    k: int = typer.Option(16, "-k", "--mg-num", help="Macro group number"),
    b: int = typer.Option(16, "-b", "--bandwidth", help="NoC flit size (bandwidth)"),
    c: int = typer.Option(64, "-c", "--core-num", help="Core number"),
    batch_size: int = typer.Option(8, help="Batch size"),
    strategy: str = typer.Option("dp", help="Partition strategy"),
    visualize: bool = typer.Option(False, help="Visualize partition result"),
    keep_ir: bool = typer.Option(False, help="Keep all intermediate IR files for debugging"),
    config: Path | None = typer.Option(None, "-cf", "--config", help="Hardware configuration file (auto-resolved from T/B by default)", show_default=False),
    config_dir: Path | None = typer.Option(None, "-cd", "--config-dir", help="Directory containing hardware configs (overrides tool_paths.json)", show_default=False),
    profile: str = typer.Option("", "-p", "--profile", help="Enable profiling. Use --profile=from-config to load from tool_paths.json, or --profile=<path> for custom config", show_default=False),
    paths_cfg: Path | None = typer.Option(None, help="Path to tool_paths.json (default: config/tool_paths.json)", show_default=False),
    log_level: str | None = typer.Option(None, "-l", "--log-level", help="Logging level: TRACE, DEBUG, VERBOSE, INFO (default), WARNING, ERROR. Controls both compiler and simulator logging. Auto-set to DEBUG with --debug", show_default=False),
) -> None:
    """Run full pipeline: compile (CG + OP) → simulate."""
    _run_single_pipeline(
        ctx=ctx,
        model_path=model_path,
        output_dir=output_dir,
        t=t,
        k=k,
        b=b,
        c=c,
        batch_size=batch_size,
        strategy=strategy,
        visualize=visualize,
        keep_ir=keep_ir,
        config=config,
        config_dir=config_dir,
        profile=profile,
        paths_cfg=paths_cfg,
        log_level=log_level,
    )


@app.command()
def from_file(
    ctx: typer.Context,
    cfg: Path = typer.Argument(..., help="JSON configuration file"),
):
    """Run one or more pipelines defined in a JSON file."""
    # Resolve the pipeline config file from CWD and get its directory
    cfg = Path(cfg).expanduser().resolve()
    config_dir = cfg.parent

    data = json.loads(cfg.read_text())

    # Parse config with batch-level settings
    conf = PipelineConfig.model_validate(data)

    # Validate non-empty runs
    if not conf.runs:
        typer.secho("Error: No pipeline runs defined in config file", fg="red", err=True)
        raise typer.Exit(1)

    # Resolve batch-level paths relative to config directory
    if conf.paths_cfg and not Path(conf.paths_cfg).is_absolute():
        conf.paths_cfg = (config_dir / conf.paths_cfg).resolve()

    output_dir = Path(conf.output_dir)
    if not output_dir.is_absolute():
        output_dir = (config_dir / output_dir).resolve()

    # Determine output structure based on keep_ir and number of runs
    batch_run_infos = []

    if len(conf.runs) > 1 and not conf.keep_ir:
        # Batch without keep_ir: unified folder
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_output_dir = output_dir / f"{ts}_{conf.run_name}"
        batch_output_dir.mkdir(parents=True, exist_ok=True)
        actual_output_dir = batch_output_dir
        base_output_for_info = batch_output_dir
    elif len(conf.runs) > 1 and conf.keep_ir:
        # Batch with keep_ir: separate folders, track base for run_info
        actual_output_dir = output_dir
        base_output_for_info = output_dir
    else:
        # Single run
        actual_output_dir = output_dir
        base_output_for_info = None

    # Run each pipeline
    for run_conf in conf.runs:
        # Resolve per-run paths relative to config directory
        model_path = Path(run_conf.model_path)
        if not model_path.is_absolute():
            model_path = (config_dir / model_path).resolve()

        config_path = None
        if run_conf.config_path:
            config_path = Path(run_conf.config_path)
            if not config_path.is_absolute():
                config_path = (config_dir / config_path).resolve()

        # Resolve profile path relative to config directory if it's a relative file path
        # Don't resolve if it's: empty (no profiling), "from-config" (special value), or absolute
        profile_path = run_conf.profile
        if profile_path and profile_path != "from-config":
            profile_path_obj = Path(profile_path)
            if not profile_path_obj.is_absolute():
                # Make it absolute relative to the config file's directory
                profile_path = str((config_dir / profile_path_obj).resolve())

        # Run pipeline and capture run info
        run_info = _run_single_pipeline(
            ctx=ctx,
            model_path=model_path,
            output_dir=actual_output_dir,
            t=run_conf.t,
            k=run_conf.k,
            b=run_conf.b,
            c=run_conf.c,
            batch_size=run_conf.batch_size,
            strategy=run_conf.strategy,
            visualize=run_conf.visualize,
            keep_ir=conf.keep_ir,  # Use batch-level keep_ir
            config=config_path,
            config_dir=None,
            profile=profile_path,
            paths_cfg=conf.paths_cfg,
            log_level=run_conf.log_level,
        )

        # Collect run info for batch summary
        if len(conf.runs) > 1 and run_info:
            batch_run_infos.append(run_info)

    # Write consolidated run_info.json for batch runs
    if len(conf.runs) > 1 and batch_run_infos and base_output_for_info:
        (base_output_for_info / "run_info.json").write_text(json.dumps(batch_run_infos, indent=2))
        typer.secho(f"✓ Batch summary written to {base_output_for_info / 'run_info.json'}", fg="green")
