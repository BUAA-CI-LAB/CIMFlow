# CIMFlow Docker Tutorial Guide

This guide provides instructions for running the CIMFlow hands-on tutorial using Docker.

## Overview

CIMFlow is a full-stack compilation and simulation framework for digital Compute-In-Memory (CIM) architectures. This tutorial demonstrates:

1. **Single model compilation and simulation** - Run an ONNX model through the pipeline
2. **Batch processing** - Compare multiple models
3. **Hardware parameter exploration** - Understand CIM architecture trade-offs
4. **Intermediate representation inspection** - Explore compiler outputs

## Prerequisites

- Docker installed ([Install Docker](https://docs.docker.com/get-docker/))
- ~10GB disk space for the Docker image
- Terminal/command line access

## Quick Start

### 1. Pull the Docker Image

```bash
docker pull ghcr.io/buaa-ci-lab/cimflow-tutorial:latest
```

### 2. Start Interactive Session

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:latest
```

### 3. Run a Demo

Inside the container:
```bash
./tutorial/demo1_quickstart.sh
```

## Tutorial Structure (30 minutes)

| Part | Time | Demo Script | Description |
|------|------|-------------|-------------|
| 1 | 3 min | `demo0_setup.sh` | Setup verification |
| 2 | 5 min | `demo1_quickstart.sh` | Quick end-to-end pipeline |
| 3 | 12 min | `demo2_stages.sh` | Step-by-step compilation |
| 4 | 10 min | `demo3_exploration.sh` | Design space exploration |

## Available Commands

### Verify Installation
```bash
cimflow --version
cim-compiler --version
cim-simulator --help
```

### Run Full Pipeline
```bash
cimflow run pipeline \
  -m data/models/resnet18.onnx \
  -o /app/output/test \
  -t 8 -k 16 -b 16 -c 64 \
  --batch-size 8
```

### Batch Processing
```bash
cimflow run from-file tutorial/exploration.json
```

### With Intermediate Files
```bash
cimflow run pipeline \
  -m data/models/resnet18.onnx \
  -o /app/output/debug \
  -t 8 -b 16 \
  --keep-ir
```

## Hardware Parameters

| Parameter | Short | Description | Default | Options |
|-----------|-------|-------------|---------|---------|
| Macro Group Size | `-t` | CIM array parallelism | 8 | 4, 8, 12, 16 |
| Macro Group Number | `-k` | Number of macro groups | 16 | - |
| Bandwidth | `-b` | NoC flit size | 16 | 8, 16 |
| Core Number | `-c` | Processing cores | 64 | - |
| Batch Size | `--batch-size` | Inference batch | 8 | - |

## Output Metrics

After simulation, you'll see:

- **Latency**: End-to-end inference time (ms)
- **Average Power**: Power consumption (mW)
- **Total Energy**: Energy per inference (pJ)
- **TOPS**: Tera operations per second
- **TOPS/W**: Energy efficiency

### Example Output
```
Simulation Result:
  - latency:            2.08837 ms
  - average power:      4420.4895 mW
  - total energy:       9231608896.0073 pJ/it
  - TOPS:               0.5319
  - TOPS/W:             0.1203
```

## Docker Images

| Image | Size | Use Case |
|-------|------|----------|
| `cimflow-tutorial:latest` | ~10GB | Pre-built, ready to use |
| `cimflow-tutorial:dev-base` | ~3.5GB | Build from source |

### Using Dev Base Image

```bash
# Pull dev base
docker pull ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base

# Mount source and build
docker run -it --rm \
  -v /path/to/cimflow:/app/cimflow \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base

# Inside container
cd /app/cimflow
./install.sh --shallow
```

## Troubleshooting

### Models not found
Models are downloaded automatically on first run. If download fails:
```bash
# Manual download
curl -fsSL -o /tmp/models.zip \
  https://github.com/BUAA-CI-LAB/CIMFlow-Compiler/releases/download/v0.1.0/example-models.zip
unzip /tmp/models.zip -d data/
```

### Out of memory
Reduce batch size or use a smaller model:
```bash
cimflow run pipeline -m data/models/mobilenetv2.onnx -o output -t 8 -b 16 --batch-size 4
```

### Permission denied on output
Ensure the output directory is writable:
```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  --user $(id -u):$(id -g) \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:latest
```

## File Structure

```
/app/cimflow/
├── data/models/          # ONNX models (downloaded on first run)
│   ├── resnet18.onnx
│   └── mobilenetv2.onnx
├── tutorial/             # Demo scripts
│   ├── demo0_setup.sh
│   ├── demo1_quickstart.sh
│   ├── demo2_stages.sh
│   └── demo3_exploration.sh
├── config/               # Configuration files
└── modules/              # Compiler and simulator
```

## Resources

- [CIMFlow GitHub](https://github.com/BUAA-CI-LAB/CIMFlow)
- [CIMFlow Documentation](https://github.com/BUAA-CI-LAB/CIMFlow/blob/main/README.md)
- [Report Issues](https://github.com/BUAA-CI-LAB/CIMFlow/issues)

## License

CIMFlow is released under the Apache 2.0 License.
