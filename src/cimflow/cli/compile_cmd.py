import typer
import time
from pathlib import Path
from ..compiler import driver
from ..config import load_global_paths
import shutil

app = typer.Typer(
    help="Compiler front-end",
    context_settings={"help_option_names": ["-h", "--help"]},
)

@app.command(name="cg")
def cg(
    ctx: typer.Context,
    model_path: Path = typer.Option(..., "-m", "--model-path", help="Path to the ONNX model", show_default=False),
    output_dir: Path = typer.Option(..., "-o", "--output-dir", help="Directory for generated instructions", show_default=False),
    compiler_bin: str = typer.Option("cim-compiler", help="Compiler executable", show_default=True),
    paths_cfg: Path = typer.Option(None, help="Path to tool_paths.json (default: config/tool_paths.json)", show_default=False),
    t: int = typer.Option(8, "-t", "--mg-size", help="Macro group size"),
    k: int = typer.Option(16, "-k", "--mg-num", help="Macro group number"),
    b: int = typer.Option(16, "-b", "--bandwidth", help="NoC flit size (bandwidth)"),
    c: int = typer.Option(64, "-c", "--core-num", help="Core number"),
    batch_size: int = typer.Option(8, help="Batch size"),
    strategy: str = typer.Option("dp", help="Partition strategy"),
    visualize: bool = typer.Option(False, help="Visualize partition result"),
    log_level: str = typer.Option(None, "-l", "--log-level", help="Logging level: TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR. Auto-set to DEBUG with --debug", show_default=False),
):
    """Compile at computation graph level."""
    # Only consult tool_paths.json if default compiler isn't on PATH
    if compiler_bin == "cim-compiler" and shutil.which("cim-compiler") is None:
        try:
            paths = load_global_paths(paths_cfg)
            compiler_bin = paths.compiler_bin
        except FileNotFoundError:
            typer.secho("Error: cim-compiler not found on PATH and config/tool_paths.json is missing", fg="red", err=True)
            typer.secho("  → Install cim-compiler so it's on PATH, OR", fg="yellow")
            typer.secho("  → Pass --compiler-bin with the full path, OR", fg="yellow")
            typer.secho("  → Create config/tool_paths.json and set compiler_bin", fg="yellow")
            raise typer.Exit(1)

    # Coordinate log_level with --debug flag
    if log_level is None and ctx.obj and ctx.obj.get('debug'):
        log_level = "DEBUG"

    typer.secho("=== CG compilation started ===", fg="bright_blue")
    start_time = time.perf_counter()
    output_file = driver.compile_cg_level(
        model_path=model_path,
        output_dir=output_dir,
        compiler_bin=compiler_bin,
        t=t,
        k=k,
        b=b,
        c=c,
        batch_size=batch_size,
        strategy=strategy,
        visualize=visualize,
        log_level=log_level,
    )
    elapsed = time.perf_counter() - start_time
    typer.secho(f"=== CG compilation finished in {elapsed:.2f}s ===", fg="green")
    typer.echo(f"Generated instructions: {output_file}")

@app.command(name="op")
def op(
    ctx: typer.Context,
    instruction_file: Path = typer.Option(..., "-i", "--instruction-file", help="Instruction file", show_default=False),
    output_dir: Path = typer.Option(..., "-o", "--output-dir", help="Where compiled results go", show_default=False),
    config: Path = typer.Option(None, "-cf", "--config", help="Hardware configuration file (auto-resolved from T/B if not provided)", show_default=False),
    config_dir: Path = typer.Option(None, "-cd", "--config-dir", help="Directory containing hardware configs (overrides tool_paths.json)", show_default=False),
    t: int = typer.Option(None, "-t", "--mg-size", help="Macro group size (required for auto-resolving config)"),
    b: int = typer.Option(None, "-b", "--bandwidth", help="NoC flit size/bandwidth (required for auto-resolving config)"),
    compiler_bin: str = typer.Option("cim-compiler", help="Compiler executable", show_default=True),
    paths_cfg: Path = typer.Option(None, help="Path to tool_paths.json (default: config/tool_paths.json)", show_default=False),
    log_level: str = typer.Option(None, "-l", "--log-level", help="Logging level: TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR. Auto-set to DEBUG with --debug", show_default=False),
):
    """Compile at operator level."""
    # Determine if we need tool_paths.json
    # Only required when: 1) config needs auto-resolution from default config_dir,
    # or 2) compiler_bin is default AND not found on PATH.
    paths = None
    need_paths_for_config = (config is None) and (config_dir is None)
    need_paths_for_compiler = (compiler_bin == "cim-compiler") and (shutil.which("cim-compiler") is None)

    if need_paths_for_config or need_paths_for_compiler:
        try:
            paths = load_global_paths(paths_cfg)
        except FileNotFoundError:
            if need_paths_for_config:
                typer.secho("Error: Cannot auto-resolve config without config/tool_paths.json", fg="red", err=True)
                typer.secho("  → Provide -cf/--config explicitly, OR", fg="yellow")
                typer.secho("  → Provide -cd/--config-dir with -t and -b, OR", fg="yellow")
                typer.secho("  → Create config/tool_paths.json (cp config_templates/tool_paths.json config/tool_paths.json)", fg="yellow")
                raise typer.Exit(1)
            if need_paths_for_compiler:
                typer.secho("Error: cim-compiler not found on PATH and config/tool_paths.json is missing", fg="red", err=True)
                typer.secho("  → Install cim-compiler so it's on PATH, OR", fg="yellow")
                typer.secho("  → Pass --compiler-bin with the full path, OR", fg="yellow")
                typer.secho("  → Create config/tool_paths.json and set compiler_bin", fg="yellow")
                raise typer.Exit(1)

    # Resolve config path
    if config is not None:
        # Explicit config provided - use it directly
        config_path = Path(config).expanduser().resolve()
        if not config_path.exists():
            typer.secho(f"Error: Config file not found: {config_path}", fg="red", err=True)
            raise typer.Exit(1)
    else:
        # Auto-resolve from T/B (requires global_paths)
        from ..config import resolve_or_use_config
        config_path = resolve_or_use_config(
            explicit_config=None,
            config_dir_override=Path(config_dir) if config_dir else None,
            global_paths=paths,
            t=t,
            b=b,
        )

    # Update compiler_bin from tool_paths.json if using default
    if compiler_bin == "cim-compiler" and paths is not None:
        compiler_bin = paths.compiler_bin

    # Coordinate log_level with --debug flag
    if log_level is None and ctx.obj and ctx.obj.get('debug'):
        log_level = "DEBUG"

    typer.secho("=== OP compilation started ===", fg="bright_blue")
    start_time = time.perf_counter()
    isa_file = driver.compile_op_level(
        instruction_file=instruction_file,
        config_path=config_path,
        output_dir=output_dir,
        compiler_bin=compiler_bin,
        log_level=log_level,
    )
    elapsed = time.perf_counter() - start_time
    typer.secho(f"=== OP compilation finished in {elapsed:.2f}s ===", fg="green")
    typer.echo(f"ISA file: {isa_file}")
