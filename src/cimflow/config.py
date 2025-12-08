from __future__ import annotations
import json
import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import typer

# Default location for user-specific configuration within the project
# This file is ignored by git (see .gitignore).
DEFAULT_GLOBAL_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "tool_paths.json"
)


def expand_path(path_str: str, base_dir: Path | None = None) -> Path:
    """Expand a path string to handle ~ and relative paths.

    Parameters
    ----------
    path_str : str
        Path string that may contain ~ or be relative
    base_dir : Path, optional
        Base directory to resolve relative paths from. If None, uses CWD.

    Returns
    -------
    Path
        Absolute Path object with ~ expanded and resolved
    """
    # Handle ~ expansion first
    expanded = os.path.expanduser(path_str)
    path = Path(expanded)

    # Resolve all paths; relative paths are resolved with base_dir if provided, otherwise from CWD
    if base_dir is not None and not path.is_absolute():
        resolved = (base_dir / path).resolve()
    else:
        # Absolute paths or relative paths without base_dir are resolved from CWD
        resolved = path.resolve()

    return resolved


def resolve_config_path(config_dir: Path, t: int, b: int) -> Path:
    """Resolve hardware config path based on T and B parameters.

    Config files follow the naming pattern: config-mg{T}-b{B}.json
    where T maps to macro group (mg) parameter.

    Parameters
    ----------
    config_dir : Path
        Directory containing hardware config files
    t : int
        T parameter (corresponds to macro group 'mg')
    b : int
        B parameter (banks)

    Returns
    -------
    Path
        Resolved config file path

    Raises
    ------
    FileNotFoundError
        If the config file doesn't exist, with helpful error showing available configs
    """
    config_name = f"config-mg{t}-b{b}.json"
    config_path = config_dir / config_name

    if not config_path.exists():
        # Provide helpful error with available configs
        available = sorted(config_dir.glob("config-mg*-b*.json"))
        if available:
            available_names = [p.name for p in available]
            available_list = "\n".join(f"  - {name}" for name in available_names)
            raise FileNotFoundError(
                f"Hardware config not found: {config_path}\n"
                f"\nAvailable configs in {config_dir}:\n{available_list}\n"
                f"\nTip: Check your T and B parameters, or use -cf/--config to specify a custom config file."
            )
        else:
            raise FileNotFoundError(
                f"Hardware config not found: {config_path}\n"
                f"No config files found in directory: {config_dir}"
            )

    return config_path


def validate_hardware_params(t: int, b: int, config_path: Path) -> bool:
    """Validate that T/B parameters match hardware config file.

    This validation should be called BEFORE compilation to fail fast
    if parameters don't match, avoiding wasted compilation time.

    Parameters
    ----------
    t : int
        Macro group size (T) parameter
    b : int
        NoC bandwidth (B) parameter
    config_path : Path
        Path to hardware configuration JSON file

    Returns
    -------
    bool
        True if parameters match

    Raises
    ------
    typer.Exit
        If parameters don't match with user-friendly error message
    """
    config_path = Path(config_path)

    if not config_path.exists():
        typer.secho(f"Error: Config file not found: {config_path}", fg="red", err=True)
        raise typer.Exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        typer.secho(f"Error: Invalid JSON in config file: {config_path}", fg="red", err=True)
        typer.secho(f"       {e}", fg="red", err=True)
        raise typer.Exit(1)

    # Extract T and B from config (simulator format)
    config_t = None
    config_b = None

    try:
        chip_config = config.get("chip_config")
        if chip_config:
            core_config = chip_config.get("core_config", {})
            cim_unit_config = core_config.get("cim_unit_config", {})
            config_t = cim_unit_config.get("macro_group_size")

            network_config = chip_config.get("network_config", {})
            config_b = network_config.get("bus_width_byte")
    except (AttributeError, TypeError) as e:
        typer.secho(f"Error: Invalid config structure in {config_path}", fg="red", err=True)
        typer.secho(f"       {e}", fg="red", err=True)
        raise typer.Exit(1)

    if config_t is None:
        typer.secho(
            f"Error: Config file {config_path.name} missing macro group size field.\n"
            f"       Expected: chip_config.core_config.cim_unit_config.macro_group_size",
            fg="red", err=True
        )
        raise typer.Exit(1)

    if config_b is None:
        typer.secho(
            f"Error: Config file {config_path.name} missing NoC bandwidth field.\n"
            f"       Expected: chip_config.network_config.bus_width_byte",
            fg="red", err=True
        )
        raise typer.Exit(1)

    # Validate T parameter
    if t != config_t:
        typer.secho(
            f"Error: Hardware parameter mismatch (T):\n"
            f"       CLI parameter T = {t}\n"
            f"       Config file T (macro_group_size) = {config_t}\n"
            f"       Config file: {config_path.name}\n"
            f"\n"
            f"       Either use -t {config_t} or use a config with T={t}",
            fg="red", err=True
        )
        raise typer.Exit(1)

    # Validate B parameter
    if b != config_b:
        typer.secho(
            f"Error: Hardware parameter mismatch (B):\n"
            f"       CLI parameter B = {b}\n"
            f"       Config file B (bus_width_byte) = {config_b}\n"
            f"       Config file: {config_path.name}\n"
            f"\n"
            f"       Either use -b {config_b} or use a config with B={b}",
            fg="red", err=True
        )
        raise typer.Exit(1)

    return True


def validate_profiler_config(config_path: Path) -> bool:
    """Validate that a profiler config file is valid JSON.

    Parameters
    ----------
    config_path : Path
        Path to profiler config file

    Returns
    -------
    bool
        True if valid

    Raises
    ------
    typer.Exit
        If validation fails with user-friendly error message
    """
    try:
        with open(config_path, 'r') as f:
            json.load(f)
        return True
    except json.JSONDecodeError as e:
        typer.secho(f"Error: Invalid JSON in profiler config: {config_path}", fg="red", err=True)
        typer.secho(f"       {e}", fg="red", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error: Cannot read profiler config: {config_path}", fg="red", err=True)
        typer.secho(f"       {e}", fg="red", err=True)
        raise typer.Exit(1)


def resolve_profile_config(
    profile: str,
    paths_cfg: Path | None = None,
) -> tuple[bool, Path | None]:
    """Resolve profiling configuration from profile argument.

    Parameters
    ----------
    profile : str
        Profile configuration:
        - "" (empty): No profiling
        - "from-config": Load from tool_paths.json
        - "<path>": Custom profiler config path (absolute or relative to CWD)
    paths_cfg : Path | None, optional
        Path to tool_paths.json (if loading from config)

    Returns
    -------
    tuple[bool, Path | None]
        (enable_profiling, profiler_cfg_path)

    Raises
    ------
    typer.Exit
        If profile resolution fails with user-friendly error message
    """
    if not profile:
        # Empty string means no profiling
        return (False, None)

    # Non-empty string means profiling is enabled
    enable_profiling = True
    profiler_cfg_path = None

    if profile == "from-config":
        # Load from tool_paths.json
        try:
            paths = load_global_paths(paths_cfg)
            profiler_cfg_path = paths.profiler_cfg
            if profiler_cfg_path is None:
                typer.secho("Error: profiler_cfg not specified in tool_paths.json", fg="red", err=True)
                typer.secho("       Either add profiler_cfg to tool_paths.json or use --profile=<path>", fg="yellow", err=True)
                raise typer.Exit(1)
        except FileNotFoundError as e:
            typer.secho(f"Error: Cannot load tool_paths.json: {e}", fg="red", err=True)
            raise typer.Exit(1)
    else:
        # Custom path provided - try to resolve it intelligently
        profile_path = Path(profile).expanduser()

        if profile_path.is_absolute():
            # Absolute path provided
            if profile_path.exists():
                profiler_cfg_path = profile_path.resolve()
            else:
                typer.secho(f"Error: Profiler config not found: {profile_path}", fg="red", err=True)
                raise typer.Exit(1)
        else:
            # Relative path - resolve relative to current working directory
            cwd_path = Path.cwd() / profile_path

            if cwd_path.exists():
                profiler_cfg_path = cwd_path.resolve()
            else:
                typer.secho(f"Error: Profiler config not found: {profile_path}", fg="red", err=True)
                typer.secho(f"       Searched at: {cwd_path}", fg="yellow", err=True)
                typer.secho("       Use an absolute path or a path relative to current directory", fg="yellow", err=True)
                raise typer.Exit(1)

    # Validate the profiler config is valid JSON
    if profiler_cfg_path is not None:
        validate_profiler_config(profiler_cfg_path)

    return (enable_profiling, profiler_cfg_path)


def resolve_or_use_config(
    explicit_config: Path | None,
    config_dir_override: Path | None,
    global_paths: "GlobalPaths",
    t: int | None = None,
    b: int | None = None,
) -> Path:
    """Resolve hardware config with fallback chain and user-friendly error handling.

    Resolution priority:
    1. Explicit --config path (if provided)
    2. Auto-resolve from T/B in --config-dir override (if provided)
    3. Auto-resolve from T/B in default config_dir from tool_paths.json

    Parameters
    ----------
    explicit_config : Path | None
        Explicit config path from --config flag
    config_dir_override : Path | None
        Config directory override from --config-dir flag
    global_paths : GlobalPaths
        Global paths loaded from tool_paths.json
    t : int | None
        Macro group size (required for auto-resolution)
    b : int | None
        NoC bandwidth (required for auto-resolution)

    Returns
    -------
    Path
        Resolved config path

    Raises
    ------
    typer.Exit
        If config resolution fails with user-friendly error message
    """
    if explicit_config is not None:
        # Use explicit config path
        config_path = Path(explicit_config).expanduser().resolve()
        if not config_path.exists():
            typer.secho(f"Error: Config file not found: {config_path}", fg="red", err=True)
            raise typer.Exit(1)
        return config_path
    else:
        # Auto-resolve from T/B parameters
        if t is None or b is None:
            typer.secho(
                "Error: T and B parameters are required for config auto-resolution.\n"
                "   Use --config to specify config explicitly, or provide -t and -b flags.",
                fg="red", err=True
            )
            raise typer.Exit(1)

        # Determine which config_dir to use
        if config_dir_override is not None:
            # CLI override
            effective_config_dir = Path(config_dir_override).expanduser().resolve()
            if not effective_config_dir.exists():
                typer.secho(f"Error: Config directory not found: {effective_config_dir}", fg="red", err=True)
                raise typer.Exit(1)
        else:
            # Use from tool_paths.json
            effective_config_dir = global_paths.config_dir

        try:
            config_path = resolve_config_path(effective_config_dir, t, b)
            typer.secho(f"Using auto-resolved config: {config_path.name}", fg="cyan")
            return config_path
        except FileNotFoundError as e:
            typer.secho(f"Error: {e}", fg="red", err=True)
            raise typer.Exit(1)


class GlobalPaths(BaseModel):
    """Global configuration paths for CIMFlow tools."""
    config_dir: Path = Field(..., description="Directory containing hardware config files")
    profiler_cfg: Path | None = Field(None, description="Path to profiler config (optional)")
    compiler_bin: str = Field("cim-compiler", description="Compiler binary path or name")
    simulator_bin: str = Field("cim-simulator", description="Simulator binary name or path (default: cim-simulator from PATH)")

    @field_validator('config_dir')
    @classmethod
    def validate_config_dir_exists(cls, v: Path) -> Path:
        """Validate that config_dir exists."""
        if not v.exists():
            raise ValueError(f"Required path does not exist: {v}")
        return v

    @field_validator('profiler_cfg')
    @classmethod
    def validate_profiler_cfg_if_provided(cls, v: Path | None) -> Path | None:
        """Validate profiler config path if provided."""
        if v is not None and not v.exists():
            raise ValueError(f"Profiler config path does not exist: {v}")
        return v


def load_global_paths(cfg_path: Path | str | None = None) -> GlobalPaths:
    """Load runtime paths from ``tool_paths.json``.

    Parameters
    ----------
    cfg_path:
        Optional path to ``tool_paths.json``. If omitted, ``config/tool_paths.json`` in the
        project root is used. Can be a Path object or string path.

    Raises
    ------
    FileNotFoundError:
        If the config file doesn't exist
    """

    path = cfg_path or DEFAULT_GLOBAL_CONFIG_PATH

    # Convert to string first if it's a Path, then expand user and resolve
    if isinstance(path, (Path, str)):
        path = Path(os.path.expanduser(str(path))).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = json.loads(path.read_text())

    # Get config file's directory as base for relative paths
    config_dir = path.parent

    # Expand paths for Path fields (~ and relative paths)
    # Relative paths are resolved relative to the config file's location
    path_fields = ['config_dir', 'profiler_cfg']
    for field in path_fields:
        if field in data and data[field] is not None:
            data[field] = expand_path(data[field], base_dir=config_dir)

    # For executable fields, expand if they look like paths (cross-platform)
    exe_fields = ['compiler_bin', 'simulator_bin']
    for field in exe_fields:
        if field in data:
            value = data[field]
            # Check if it's a path (contains separators or starts with ~ or .)
            is_path = (
                os.path.sep in value or
                '/' in value or  # Unix-style
                '\\' in value or  # Windows-style
                value.startswith('~') or
                value.startswith('./') or
                value.startswith('.\\') or
                Path(value).is_absolute()
            )
            if is_path:
                data[field] = str(expand_path(value, base_dir=config_dir))

    return GlobalPaths.model_validate(data)
