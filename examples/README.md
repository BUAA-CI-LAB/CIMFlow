# CIMFlow Examples

This directory contains example configurations for running CIMFlow.

## Prerequisites

1. Install CIMFlow by running `./install.sh` from the repository root
2. Download example ONNX models (see below)

## Downloading Models

Example ONNX models are available from the [CIMFlow-Compiler Releases](https://github.com/BUAA-CI-LAB/CIMFlow-Compiler/releases).

**Quick download using the provided script:**

```bash
./run_example.sh --download
```

This downloads and extracts models to `data/models/`.

**Manual download:**

```bash
mkdir -p data
cd data
curl -fsSL -o example-models.zip https://github.com/BUAA-CI-LAB/CIMFlow-Compiler/releases/download/v0.1.0/example-models.zip
unzip example-models.zip
rm example-models.zip
# Models are now in data/models/
```

## Running Examples

**Download models and run examples:**

```bash
./run_example.sh --all
```

**Run examples only (models must be downloaded first):**

```bash
./run_example.sh
```

**Run with verbose output:**

```bash
./run_example.sh --verbose
```

**Or run manually:**

```bash
cimflow run from-file examples/batch.json
```

## Example Configuration

The `batch.json` file defines batch runs with different models and parameters. See the file for details.

## Output

Results are saved to `output/examples/` including:
- Simulation reports with cycle counts and performance metrics
- Energy estimates

Use `--keep-ir` to preserve intermediate compilation artifacts for debugging.
