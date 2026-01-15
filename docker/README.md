# CIMFlow Docker Images

This directory contains Docker configurations for CIMFlow development and tutorials.

## Images

| Image | Purpose | Download |
|-------|---------|----------|
| `cimflow-tutorial:latest` | Pre-built, ready-to-run tutorial | ~3GB |
| `cimflow-tutorial:dev-base` | Development base with dependencies | ~1GB |

## Quick Start

### For Tutorials (Pre-built)

```bash
# Pull and run
docker pull ghcr.io/buaa-ci-lab/cimflow-tutorial:latest
docker run -it --rm -v $(pwd)/output:/app/output ghcr.io/buaa-ci-lab/cimflow-tutorial:latest

# Run demos
./tutorial/demo1_quickstart.sh
```

### For Development

**Easiest way** - use the helper script:

```bash
# Start or attach to persistent container (recommended)
./docker/dev.sh

# First time inside container: install everything (~30-45 min)
./install.sh --shallow

# Subsequent sessions: just run dev.sh again - everything is preserved
./docker/dev.sh
```

**Container management:**
```bash
./docker/dev.sh              # Start or reattach to persistent container
./docker/dev.sh --fresh      # Start fresh ephemeral container (lost on exit)
./docker/dev.sh --build      # Rebuild image first, then start
./docker/dev.sh --rm         # Remove the persistent container
./docker/dev.sh cimflow -V   # Run a command and exit
```

**Exiting the container:**
- Type `exit` or press `Ctrl+D` - stops the container
- Press `Ctrl+P`, then `Ctrl+Q` - detaches (container keeps running, reattach with `./docker/dev.sh`)

**Manual approach:**

```bash
# Pull pre-built dev image
docker pull ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base

# Or build locally
docker build -f docker/Dockerfile.dev-base -t cimflow-dev-base .

# Start container
docker run -it --rm \
  -v $(pwd):/app/cimflow \
  -v $(pwd)/output:/app/output \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base
```

## Development Workflow

### Why Develop in Docker?

- **Consistent environment** - matches CI/production exactly
- **No dependency conflicts** - isolated from host system
- **Easy onboarding** - new developers just pull the image
- **Path consistency** - build artifacts work across sessions

### First-Time Setup

```bash
cd /path/to/cimflow

# Clean any existing host builds (optional, but recommended)
rm -rf modules/CIMFlow-Compiler-Private/thirdparty/llvm-project/build
rm -rf modules/CIMFlow-Compiler-Private/build
rm -rf modules/CIMFlow-Simulator-Private/build

# Start container
docker run -it --rm \
  -v $(pwd):/app/cimflow \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base

# Build everything (one-time, ~30-45 min)
./install.sh --shallow
```

### Daily Development

```bash
# Start container (builds are cached on host via mount)
docker run -it --rm \
  -v $(pwd):/app/cimflow \
  -v $(pwd)/output:/app/output \
  ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base

# Everything is ready - start working
cimflow --version
cimflow run pipeline -m data/models/resnet18.onnx -o /app/output/test -t 8 -b 16
```

### With VS Code

Use the [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension:

1. Open the `cimflow` folder in VS Code
2. Click "Reopen in Container" (or Cmd/Ctrl+Shift+P → "Reopen in Container")
3. VS Code will use the dev-base image automatically

To enable this, create `.devcontainer/devcontainer.json`:
```json
{
  "name": "CIMFlow Dev",
  "image": "ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base",
  "workspaceFolder": "/app/cimflow",
  "workspaceMount": "source=${localWorkspaceFolder},target=/app/cimflow,type=bind",
  "postCreateCommand": "./install.sh --shallow --resume"
}
```

## File Descriptions

| File | Description |
|------|-------------|
| `dev.sh` | Helper script to start development container |
| `Dockerfile.tutorial` | Multi-stage build for pre-built tutorial image |
| `Dockerfile.dev-base` | Base image with all dependencies |
| `entrypoint.sh` | Downloads models on first run |
| `.dockerignore` | Excludes unnecessary files from build context |

## Building Images Locally

```bash
# Build dev-base
docker build -f docker/Dockerfile.dev-base -t cimflow-dev-base .

# Build full tutorial image (requires public repos accessible)
docker build -f docker/Dockerfile.tutorial -t cimflow-tutorial .
```

## Troubleshooting

### Git "dubious ownership" error
This is handled automatically in dev-base. If you see it, the image may be outdated:
```bash
docker pull ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base
```

### CMake path mismatch errors
This happens if you previously built on host. Clean the build directories:
```bash
rm -rf modules/CIMFlow-Compiler-Private/thirdparty/llvm-project/build
rm -rf modules/CIMFlow-Compiler-Private/build
rm -rf modules/CIMFlow-Simulator-Private/build
```

### Slow file access on macOS/Windows
Docker volume mounts are slower on non-Linux. Consider using:
- Docker's built-in caching: `-v $(pwd):/app/cimflow:cached`
- Or keep build artifacts in a Docker volume instead of bind mount
