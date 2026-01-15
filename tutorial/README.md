# CIMFlow Tutorial

Hands-on tutorial materials for CIMFlow, a full-stack compilation and simulation framework for digital Compute-In-Memory (CIM) architectures.

## ASP-DAC 2026 Tutorial

This tutorial is part of **[Tutorial-2: Design Methodologies and Toolchains for Compute-in-Memory](https://www.aspdac.com/aspdac2026/tutorial/#t2)** at ASP-DAC 2026.

- **Date**: Monday, January 19, 2026, 9:00—12:00
- **Location**: Sleeping Beauty 3

The CIMFlow hands-on session demonstrates practical workflows for compilation, simulation, and design space exploration.

## Time Estimates

### Guided Session (~50 min)

For instructor-led tutorials with framework introduction:

| Phase | Time | Content |
|-------|------|---------|
| Introduction | 20 min | CIMFlow framework overview and paper |
| Demo 0: Setup | 3 min | Verify installation, explore CLI |
| Demo 1: Quick Start | 5 min | End-to-end pipeline in one command |
| Demo 2: Stages | 12 min | Step-by-step compilation with IR inspection |
| Demo 3: Exploration | 8 min | Design space exploration with batch processing |
| Q&A | 2 min | Questions and wrap-up |

### Self-Paced (~30 min)

For independent exploration (includes image pulling and reading time):

| Script | Duration | Description |
|--------|----------|-------------|
| `demo0_setup.sh` | ~10 min | Setup, image pull, CLI overview |
| `demo1_quickstart.sh` | ~3 min | Run ResNet-18 through full pipeline |
| `demo2_stages.sh` | ~5 min | Step-by-step compilation stages |
| `demo3_exploration.sh` | ~8 min | Batch processing and comparison |

## Prerequisites

### Option A: Docker (Recommended)
- Docker installed
- CIMFlow tutorial image: `docker pull ghcr.io/buaa-ci-lab/cimflow-tutorial:latest`
- Models are downloaded automatically on first run

### Option B: Local Installation
- CIMFlow installed: `./install.sh`
- Download example models: `./scripts/download_models.sh`

## Quick Start

```bash
# Start interactive container
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:latest

# Inside container, run demos in order:
./tutorial/demo0_setup.sh
./tutorial/demo1_quickstart.sh
./tutorial/demo2_stages.sh
./tutorial/demo3_exploration.sh
```

## Demo Descriptions

### Demo 0: Setup
- Verify `cimflow` and `cim-compiler` installation
- Explore CLI help and available commands
- Setup shell auto-completion (optional)

### Demo 1: Quick Start
- Single `cimflow run pipeline` command
- Shows the simplest way to compile and simulate a model
- Displays performance metrics (latency, power, TOPS, TOPS/W)

### Demo 2: Step-by-Step Stages
- **CG Compilation**: ONNX → Compute Graph instructions
- **OP Compilation**: CG instructions → ISA (JSON format)
- **Format Conversion**: `cim-compiler convert` JSON → Assembly (human-readable)
- **Simulation**: ISA → Performance report
- Inspect intermediate representations at each stage

### Demo 3: Design Space Exploration
- Batch processing with `cimflow run from-file`
- Explore 2×2 matrix: Bandwidth (8, 16) × Batch Size (1, 8)
- Compare results in tabular format
- Discuss parameter effects on performance

## Hardware Parameters

| Parameter | Description | Available Values |
|-----------|-------------|------------------|
| **T** | Macro group size | 8 |
| **K** | Macro group number | 16 |
| **B** | NoC bandwidth (flit size) | 8, 16 |
| **C** | Core number | 64 |
| **batch_size** | Inference batch size | 1, 2, 4, 8, ... |

## Output Metrics

After simulation, you'll see:
- **Latency**: End-to-end inference time (ms)
- **Power**: Average power consumption (mW)
- **Energy**: Total energy per inference (pJ)
- **TOPS**: Tera operations per second (throughput)
- **TOPS/W**: Energy efficiency

## Key Commands

```bash
# Full pipeline (simplest)
cimflow run pipeline -m model.onnx -o output -t 8 -b 16

# Individual stages
cimflow compile cg -m model.onnx -o output/cg
cimflow compile op -i output/cg/instructions.json -o output/op -t 8 -b 16
cimflow sim -i output/op/isa_instructions.json -o output/sim -t 8 -b 16

# Format conversion (JSON ↔ Assembly)
cim-compiler convert --src-type json --dst-type asm --src-file input.json --dst-file output.asm

# Batch processing
cimflow run from-file exploration.json
```

## Files

```
tutorial/
├── demo0_setup.sh        # Setup and verification
├── demo1_quickstart.sh   # Quick end-to-end demo
├── demo2_stages.sh       # Step-by-step compilation
├── demo3_exploration.sh  # Design space exploration
├── exploration.json      # Batch config for demo3
└── README.md             # This file
```

## Resources

- GitHub: https://github.com/BUAA-CI-LAB/CIMFlow
- Paper: [CIMFlow: An Integrated Framework for Systematic Design and Evaluation of Digital CIM Architectures (DAC 2025)](https://doi.org/10.1109/DAC63849.2025.11133270)
- Tutorial: [ASP-DAC 2026 Tutorial-2: Design Methodologies and Toolchains for Compute-in-Memory](https://www.aspdac.com/aspdac2026/tutorial/#t2)
