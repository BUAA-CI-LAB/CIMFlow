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

## Docker

CIMFlow provides Docker images for both tutorials and development:

| Image | Purpose | Download |
|-------|---------|----------|
| `cimflow-tutorial:latest` | Pre-built with models and demos | ~3GB |
| `cimflow-tutorial:dev-base` | Development base with dependencies | ~1GB |

```bash
# Try the interactive tutorial
docker run -it --rm ghcr.io/buaa-ci-lab/cimflow-tutorial:latest

# Or start a development environment
./docker/dev.sh
```

See [docker/README.md](docker/README.md) for detailed instructions.

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 22.04 (other Linux distributions may work but are untested)
- **Disk Space**: 15GB or more available
- **Python 3.11 or later** is required.

We recommend using Conda for Python environment management:

```bash
conda create -n cimflow python=3.11
conda activate cimflow
```

> **Note:** If you don't have Conda installed, see the [Miniconda installation guide](https://docs.conda.io/en/latest/miniconda.html).

Alternatively, you can use venv:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### System Dependencies

Install the required system packages (Ubuntu 22.04):

```bash
# Build tools
sudo apt install build-essential cmake ninja-build ccache

# Clang toolchain (for LLVM/MLIR build)
sudo apt install clang lld

# Java Development Kit (for ANTLR parser)
sudo apt install openjdk-11-jdk

# Required libraries
sudo apt install libeigen3-dev libunwind-dev
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/BUAA-CI-LAB/CIMFlow.git
cd CIMFlow
```

### 2. Run Installation Script

With your virtual environment activated, run the installation script:

```bash
./install.sh
```

This script will:
1.  Initialize and update submodules (`CIMFlow-Compiler`, `CIMFlow-Simulator`).
2.  Build the compiler (LLVM/MLIR) and simulator (SystemC).
3.  Install the Python package and CLI tools.
4.  Generate the default configuration in `config/tool_paths.json`.

> **Tip:** Run `./install.sh --help` for additional options (resume, repair, uninstall, etc.).

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

## Tutorial

CIMFlow includes interactive tutorials to help you get started. Run them in Docker or after local installation:

```bash
# Demo 0: Setup verification
./tutorial/demo0_setup.sh

# Demo 1: Quick end-to-end pipeline
./tutorial/demo1_quickstart.sh

# Demo 2: Step-by-step compilation stages
./tutorial/demo2_stages.sh

# Demo 3: Design space exploration
./tutorial/demo3_exploration.sh
```

The tutorials cover:
- **Demo 0**: Verify installation and explore CLI commands
- **Demo 1**: Run a complete compile-simulate pipeline on ResNet-18
- **Demo 2**: Understand each compilation stage (CG, OP, Simulation)
- **Demo 3**: Batch processing for hardware design exploration

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
