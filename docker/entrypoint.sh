#!/bin/bash
# CIMFlow Tutorial Entrypoint Script
# Downloads example models on first run from CIMFlow-Compiler release
#
# Can be run from any directory - paths are resolved automatically.

set -e

# Resolve script and repo paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect environment: Docker uses /app/cimflow, otherwise use relative path from script
if [ -d "/app/cimflow" ]; then
    REPO_ROOT="/app/cimflow"
else
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

MODELS_DIR="$REPO_ROOT/data/models"
RELEASE_URL="https://github.com/BUAA-CI-LAB/CIMFlow-Compiler/releases/download/v0.1.0"
MODELS_ZIP="example-models.zip"

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

# Download models if not present
if [ ! -f "$MODELS_DIR/resnet18.onnx" ]; then
    echo -e "${CYAN}Downloading example models...${NC}"
    mkdir -p "$MODELS_DIR"

    # Download models zip from release
    if curl -fsSL -o /tmp/"$MODELS_ZIP" "$RELEASE_URL/$MODELS_ZIP" 2>/dev/null; then
        # Verify it's a valid zip file before extracting (using unzip -t, no file utility needed)
        if unzip -t /tmp/"$MODELS_ZIP" >/dev/null 2>&1; then
            unzip -q /tmp/"$MODELS_ZIP" -d "$(dirname "$MODELS_DIR")"
            rm -f /tmp/"$MODELS_ZIP"
            echo -e "${GREEN}Models downloaded to $MODELS_DIR${NC}"
            echo ""
            echo "Available models:"
            for model in "$MODELS_DIR"/*.onnx; do
                [ -f "$model" ] && echo "  - $(basename "$model")"
            done
            echo ""
        else
            echo "Warning: Downloaded file is not a valid zip archive"
            rm -f /tmp/"$MODELS_ZIP"
        fi
    else
        echo "Warning: Could not download models from release."
        echo "You can manually download from: $RELEASE_URL/$MODELS_ZIP"
        echo "Or provide your own ONNX models in $MODELS_DIR"
        echo ""
    fi
else
    echo -e "${GREEN}Models already present in $MODELS_DIR${NC}"
fi

# Show quick start help if running interactively with no arguments
if [ $# -eq 0 ] || [ "$1" = "/bin/bash" ]; then
    echo -e "${CYAN}=== CIMFlow Tutorial ===${NC}"
    echo ""
    echo "Quick start commands:"
    echo "  cimflow --version              # Check installation"
    echo "  cimflow --help                 # Show help"
    echo ""
    echo "Run a demo (can be run from any directory):"
    echo "  $REPO_ROOT/tutorial/demo0_setup.sh             # Setup verification"
    echo "  $REPO_ROOT/tutorial/demo1_quickstart.sh        # Quick end-to-end pipeline"
    echo "  $REPO_ROOT/tutorial/demo2_stages.sh            # Step-by-step compilation"
    echo "  $REPO_ROOT/tutorial/demo3_exploration.sh       # Design space exploration"
    echo ""
    echo "Manual run:"
    echo "  cimflow run pipeline -m $MODELS_DIR/resnet18.onnx -o $REPO_ROOT/output/test -t 8 -b 16"
    echo ""
fi

# Execute the command passed to docker run
exec "$@"
