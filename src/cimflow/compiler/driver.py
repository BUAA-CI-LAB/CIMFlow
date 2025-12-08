"""Helper routines to invoke the integrated CIM compiler."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..config import validate_hardware_params


def compile_cg_level(
    *,
    model_path: Path,
    output_dir: Path,
    compiler_bin: str = "cim-compiler",
    t: int = 8,
    k: int = 16,
    b: int = 16,
    c: int = 64,
    batch_size: int = 8,
    strategy: str = "dp",
    visualize: bool = False,
    log_level: str | None = None,
) -> Path:
    """Invoke the computation graph level compiler.

    Parameters
    ----------
    model_path : Path
        Path to the ONNX model file
    output_dir : Path
        Directory to store compilation outputs
    compiler_bin : str, optional
        Path or name of the compiler binary (default: "cim-compiler")
    t : int, optional
        Size of the macro group (default: 8)
    k : int, optional
        Number of macro groups (default: 16)
    b : int, optional
        NoC communication bandwidth (default: 16)
    c : int, optional
        Number of cores (default: 64)
    batch_size : int, optional
        Batch size for compilation (default: 8)
    strategy : str, optional
        Partitioning strategy (default: "dp")
    visualize : bool, optional
        Whether to generate visualization (default: False)
    log_level : str, optional
        Logging level for the compiler (TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR)

    Returns
    -------
    Path
        Path to the generated instructions JSON file

    Raises
    ------
    subprocess.CalledProcessError
        If the compiler command fails
    """
    model_path = Path(model_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()

    # Validate input files exist
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [compiler_bin]

    if log_level:
        cmd.extend(["--log-level", log_level])

    cmd.extend([
        "cg-level",
        "-m", str(model_path),
        "-o", str(output_dir),
        "-T", str(t),
        "-K", str(k),
        "-B", str(b),
        "-C", str(c),
        "--batch-size", str(batch_size),
        "--strategy", strategy,
    ])

    if visualize:
        cmd.append("--visualize")

    subprocess.run(cmd, check=True)

    model_name = model_path.stem
    instructions = output_dir / (
        f"instructions_{model_name}_{strategy}_T{t}_K{k}_B{b}_C{c}_batch{batch_size}.json"
    )

    if not instructions.exists():
        raise FileNotFoundError(
            f"Expected CG instructions file not found: {instructions}\n"
            f"Check compiler output in {output_dir}"
        )

    return instructions


def compile_op_level(
    *,
    instruction_file: Path,
    config_path: Path,
    output_dir: Path,
    compiler_bin: str = "cim-compiler",
    log_level: str | None = None,
) -> Path:
    """Invoke the operator level compiler.

    Parameters
    ----------
    instruction_file : Path
        Path to the CG-level instructions JSON file
    config_path : Path
        Path to the hardware configuration file
    output_dir : Path
        Directory to store ISA compilation outputs
    compiler_bin : str, optional
        Path or name of the compiler binary (default: "cim-compiler")
    log_level : str, optional
        Logging level for the compiler (TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR)

    Returns
    -------
    Path
        Path to the generated ISA instructions file

    Raises
    ------
    subprocess.CalledProcessError
        If the compiler command fails
    """
    instruction_file = Path(instruction_file).expanduser().resolve()
    config_path = Path(config_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()

    # Validate input files exist
    if not instruction_file.exists():
        raise FileNotFoundError(f"Instruction file not found: {instruction_file}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [compiler_bin]
    if log_level:
        cmd.extend(["--log-level", log_level])

    cmd.extend([
        "op-level",
        "-i", str(instruction_file),
        "-c", str(config_path),
        "-o", str(output_dir),
    ])

    subprocess.run(cmd, check=True)

    # Remove temporary per-core results to keep the run directory clean
    each_core_dir = output_dir / "each_core"
    if each_core_dir.is_dir():
        shutil.rmtree(each_core_dir)

    isa_file = output_dir / ("isa_" + instruction_file.name)

    if not isa_file.exists():
        raise FileNotFoundError(
            f"Expected ISA file not found: {isa_file}\n"
            f"Check compiler output in {output_dir}"
        )

    return isa_file


def compile_network(
    *,
    model_path: Path,
    output_dir: Path,
    config_path: Path,
    compiler_bin: str = "cim-compiler",
    t: int = 8,
    k: int = 16,
    b: int = 16,
    c: int = 64,
    batch_size: int = 8,
    strategy: str = "dp",
    visualize: bool = False,
    keep_ir: bool = False,
    log_level: str | None = None,
) -> Path:
    """Invoke the full network compiler (CG + OP compilation with validation).

    Parameters
    ----------
    model_path : Path
        Path to the ONNX model file
    output_dir : Path
        Directory to store compilation outputs
    config_path : Path
        Path to the hardware configuration file
    compiler_bin : str, optional
        Path or name of the compiler binary (default: "cim-compiler")
    t : int, optional
        Size of the macro group (default: 8)
    k : int, optional
        Number of macro groups (default: 16)
    b : int, optional
        NoC communication bandwidth (default: 16)
    c : int, optional
        Number of cores (default: 64)
    batch_size : int, optional
        Batch size for compilation (default: 8)
    strategy : str, optional
        Partitioning strategy (default: "dp")
    visualize : bool, optional
        Whether to generate visualization (default: False)
    keep_ir : bool, optional
        Whether to keep all intermediate IR files (default: False)
    log_level : str, optional
        Logging level for the compiler (TRACE, DEBUG, VERBOSE, INFO, WARNING, ERROR)

    Returns
    -------
    Path
        Path to the generated ISA instructions file

    Raises
    ------
    subprocess.CalledProcessError
        If the compiler command fails
    """
    model_path = Path(model_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    config_path = Path(config_path).expanduser().resolve()

    # Validate input files exist
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Validate T/B parameters match config BEFORE compilation
    # This fails fast to avoid wasting time on CG compilation if params don't match
    validate_hardware_params(t, b, config_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [compiler_bin]

    if log_level:
        cmd.extend(["--log-level", log_level])

    cmd.extend([
        "network",
        "-m", str(model_path),
        "-o", str(output_dir),
        "-c", str(config_path),
        "-T", str(t),
        "-K", str(k),
        "-B", str(b),
        "-C", str(c),
        "--batch-size", str(batch_size),
        "--strategy", strategy,
    ])

    if visualize:
        cmd.append("--visualize")

    if keep_ir:
        cmd.append("--keep-cg-ir")

    subprocess.run(cmd, check=True)

    model_name = model_path.stem
    isa_file = output_dir / f"isa_instructions_{model_name}_{strategy}_T{t}_K{k}_B{b}_C{c}_batch{batch_size}.json"

    if not isa_file.exists():
        raise FileNotFoundError(
            f"Expected ISA file not found: {isa_file}\n"
            f"Check compiler output in {output_dir}"
        )

    return isa_file
