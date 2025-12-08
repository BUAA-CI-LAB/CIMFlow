"""SystemC simulator helpers."""

from __future__ import annotations
import os
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

# Default simulator binary - uses PATH lookup via shutil.which()
DEFAULT_SIM_BIN = "cim-simulator"

# Valid log levels for the simulator
VALID_LOG_LEVELS = {"TRACE", "DEBUG", "VERBOSE", "INFO", "WARNING", "ERROR"}


def run_simulation(
    inst_file: Path,
    config_path: Path,
    report: Path,
    enable_profiling: bool = False,
    profiler_cfg: Path | None = None,
    output_format: str = "text",
    list_cores: bool = False,
    simulator_bin: str = DEFAULT_SIM_BIN,
    log_level: str | None = None,
) -> Path | None:
    """Run the SystemC simulator on a single instruction file.

    Parameters
    ----------
    inst_file : Path
        Path to the ISA instructions file
    config_path : Path
        Path to the hardware configuration file
    report : Path
        Path where simulation report will be written
    enable_profiling : bool, optional
        Enable profiling (default: False). If True and profiler_cfg is None,
        uses default config/profiler_config.json relative to simulator binary
    profiler_cfg : Path, optional
        Path to custom profiler config file. If provided, enables profiling
        with this custom configuration (ignoring enable_profiling parameter).
        Note: If json_file in the config is a relative path, it will be resolved
        relative to the profiler config file's directory.
    output_format : {"text", "json"}, optional
        Output format (default: "text")
    list_cores : bool, optional
        Report energy for each core individually (default: False)
    simulator_bin : str, optional
        Path or name of the simulator binary (default: "cim-simulator")
    log_level : str, optional
        Logging level: TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR
        If not specified, the simulator uses its default (INFO)

    Returns
    -------
    Path | None
        Path to the profiler output JSON file if profiling was enabled, None otherwise

    Raises
    ------
    subprocess.CalledProcessError
        If the simulator binary fails
    """

    # Validate log_level if provided (None or empty string means use simulator default)
    if log_level:
        if log_level.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log_level '{log_level}'. "
                f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
            )

    inst_file = inst_file.resolve()
    config_path = config_path.resolve()
    report = Path(report).expanduser().resolve()

    report.parent.mkdir(parents=True, exist_ok=True)

    # Build command with new interface
    cmd = [
        simulator_bin,
        str(config_path),
        str(inst_file),
        "-o", str(report),
        "--format", output_format,
    ]

    # Handle profiling: only add --profile flag if explicitly enabled or profiler_cfg provided
    temp_profiler_cfg = None
    profiler_output_path = None
    try:
        if profiler_cfg is not None:
            # Custom profiler config provided - read and modify paths to be absolute
            profiler_cfg = profiler_cfg.resolve()

            # Read the profiler config
            with open(profiler_cfg, 'r') as f:
                profiler_data = json.load(f)

            # Make json_file path absolute if it's relative
            if 'json_file' in profiler_data and profiler_data['json_file']:
                json_file_path = Path(profiler_data['json_file'])
                if not json_file_path.is_absolute():
                    # Make it absolute relative to the profiler config file's directory
                    config_dir = profiler_cfg.parent
                    json_file_path = (config_dir / json_file_path).resolve()
                    profiler_data['json_file'] = str(json_file_path)
                else:
                    json_file_path = json_file_path.resolve()

                # Ensure parent directory exists for the profiler output
                json_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Track profiler output path for return
                profiler_output_path = json_file_path

            # Write modified config to a temp file
            temp_profiler_cfg = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(profiler_data, temp_profiler_cfg, indent=2)
            temp_profiler_cfg.close()

            cmd.extend(["--profile", temp_profiler_cfg.name])
        elif enable_profiling:
            # Enable profiling with default config
            cmd.append("--profile")

        # Add list-cores flag if requested
        if list_cores:
            cmd.append("-l")

        # Determine working directory based on simulator_bin type
        # If it's just a command name (no path separator), resolve via PATH
        if '/' not in simulator_bin and '\\' not in simulator_bin:
            # Command name only - find it in PATH
            resolved_bin = shutil.which(simulator_bin)
            if resolved_bin is None:
                # If not in PATH, try resolving as relative path
                simulator_bin_path = Path(simulator_bin).resolve()
            else:
                # Use resolve() to follow symlinks to actual binary location
                simulator_bin_path = Path(resolved_bin).resolve()
        else:
            # Path provided - resolve directly
            simulator_bin_path = Path(simulator_bin).resolve()

        run_dir = simulator_bin_path.parent

        # Set simulator log level via environment variable
        # The simulator expects: TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR
        env = None
        if log_level:
            env = os.environ.copy()
            env['CIMSIM_LOG_LEVEL'] = log_level.upper()

        subprocess.run(cmd, check=True, cwd=run_dir, env=env)
    finally:
        # Clean up temp profiler config if created
        if temp_profiler_cfg is not None:
            try:
                Path(temp_profiler_cfg.name).unlink(missing_ok=True)
            except OSError:
                # Ignore OS-level errors during deletion (permission issues, etc.)
                pass

    return profiler_output_path
