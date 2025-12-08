<h1>
  <img
    src="https://raw.githubusercontent.com/BUAA-CI-LAB/CIMFlow-Docs/refs/heads/main/public/assets/icon.svg"
    height="25"
    alt="CIMFlow logo"
  >
  &nbsp;CIMFlow
</h1>

[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/BUAA-CI-LAB/CIMFlow)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> **CIMFlow** is an integrated framework for systematic design and evaluation of digital compute-in-memory (CIM) architectures.

This repository contains the CIMFlow framework, providing a full-stack solution from neural network compilation to cycle-accurate hardware simulation.

## Key Features

- **End-to-End Flow**: Unifies the entire workflow from high-level DNN model description to detailed performance analysis.
- **Two-Level Compiler**: CG-level optimization for workload partitioning across cores, and OP-level optimization using LLVM/MLIR for efficient code generation.
- **Cycle-Accurate Simulation**: SystemC-based simulator with detailed timing and energy modeling.
- **Flexible Architecture**: Configurable parameters for CIM macro size, memory hierarchy, NoC bandwidth, and core organization.
- **Profiling & Analysis**: Built-in tools for performance profiling and energy estimation.

## Architecture

CIMFlow consists of two main components:

1.  **CIMFlow Compiler**: Transforms high-level neural network models (ONNX) into optimized instruction sequences (ISA) for the target CIM architecture.
2.  **CIMFlow Simulator**: Executes the generated instructions on a cycle-accurate model of the hardware, producing detailed performance and energy reports.

## Prerequisites

Before installing, ensure you have the following system dependencies:

- **Python**: 3.11+
- **Build Tools**: `cmake` (>=3.20), `ninja-build`, `make`, `build-essential`
- **Compiler**: `clang`, `lld`, `ccache`
- **Java**: `openjdk-11-jdk` (for ANTLR parser)
- **Libraries**: `libeigen3-dev`, `libunwind-dev`

## Installation

To install CIMFlow, its dependencies, and handle submodules, run the installation script:

```bash
./install.sh
```

This script will:
1.  Initialize and update submodules (`CIMFlow-Compiler`, `CIMFlow-Simulator`).
2.  Build the compiler (LLVM/MLIR) and simulator (SystemC).
3.  Install the Python package and CLI tools.
4.  Generate the default configuration in `config/tool_paths.json`.

## Configuration

Runtime paths are defined in `config/tool_paths.json`. This file is automatically created during installation.

**Post-installation:** Check `config/tool_paths.json` to ensure it points to the correct directories for your setup.

## Usage

### Quick Start

Run a full pipeline (compile + simulate) using a config file:

```bash
# Copy the template
cp config_templates/batch.json config/batch.json

# Run the batch
cimflow run from-file config/batch.json
```

### Command Line Interface

You can also run individual steps or override parameters via the CLI:

```bash
# Run pipeline with specific model and hardware parameters
cimflow run pipeline -m model.onnx -o output -t 8 -b 16

# Enable profiling
cimflow run pipeline -m model.onnx -o output --profile=from-config

# Enable verbose logging
cimflow run pipeline -m model.onnx -o output -l VERBOSE
```

### Output Structure

- **Default**: Simulation reports are saved in the output directory.
- **Debug (`--keep-ir`)**: Saves all intermediate files (IR, ISA, logs) in timestamped folders.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.

## Citation

If you use CIMFlow in your research, please cite our paper:

```bibtex
@inproceedings{qi2025cimflow,
  title={CIMFlow: An Integrated Framework for Systematic Design and Evaluation of Digital CIM Architectures},
  author={Qi, Yingjie and Yang, Jianlei and Wang, Yiou and Wang, Yikun and Wang, Dayu and Tang, Ling and Duan, Cenlin and He, Xiaolin and Zhao, Weisheng},
  booktitle={2025 62nd ACM/IEEE Design Automation Conference (DAC)},
  pages={1--7},
  year={2025},
  doi={10.1109/DAC63849.2025.11133270}
}
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
