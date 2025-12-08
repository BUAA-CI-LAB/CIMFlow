#!/bin/bash
# run_example.sh - Download example models and run CIMFlow examples
#
# Usage:
#   ./run_example.sh              # Run examples (models must be downloaded)
#   ./run_example.sh --download   # Download models only
#   ./run_example.sh --all        # Download models and run examples
#   ./run_example.sh --verbose    # Run with verbose output

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
MODELS_DIR="$REPO_ROOT/data/models"
RELEASE_URL="https://github.com/BUAA-CI-LAB/CIMFlow-Compiler/releases/download/v0.1.0"
MODELS_ZIP="example-models.zip"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
DOWNLOAD=false
RUN_EXAMPLES=true
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --download)
            DOWNLOAD=true
            RUN_EXAMPLES=false
            shift
            ;;
        --all)
            DOWNLOAD=true
            RUN_EXAMPLES=true
            shift
            ;;
        --verbose|-v)
            VERBOSE="-l VERBOSE"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --download    Download models only"
            echo "  --all         Download models and run examples"
            echo "  --verbose     Run with verbose output"
            echo "  --help        Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

download_models() {
    echo -e "${CYAN}=== Downloading example models ===${NC}"

    DATA_DIR="$REPO_ROOT/data"
    mkdir -p "$DATA_DIR"

    # Check if models already exist
    if ls "$MODELS_DIR"/*.onnx 1> /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Models already exist in $MODELS_DIR"
        echo -e "  ${YELLOW}To re-download, remove the directory first${NC}"
        return
    fi

    echo -e "  Downloading $MODELS_ZIP..."
    cd "$DATA_DIR"
    if curl -fsSL -o "$MODELS_ZIP" "$RELEASE_URL/$MODELS_ZIP"; then
        echo -e "  Extracting..."
        unzip -q "$MODELS_ZIP"
        rm "$MODELS_ZIP"
        echo -e "  ${GREEN}✓${NC} Models extracted to $MODELS_DIR"
        echo ""
        echo "  Available models:"
        ls -1 "$MODELS_DIR"/*.onnx 2>/dev/null | xargs -n1 basename | while read model; do
            echo -e "    - $model"
        done
    else
        echo -e "  ${RED}✗${NC} Failed to download models"
        echo -e "  ${YELLOW}Download manually from: $RELEASE_URL/$MODELS_ZIP${NC}"
        exit 1
    fi

    cd "$SCRIPT_DIR"
    echo ""
}

check_models() {
    if ! ls "$MODELS_DIR"/*.onnx 1> /dev/null 2>&1; then
        echo -e "${YELLOW}Models not found in $MODELS_DIR${NC}"
        echo -e "Run with --download or --all to download models first"
        exit 1
    fi
}

run_examples() {
    echo -e "${CYAN}=== Running CIMFlow examples ===${NC}"
    echo ""

    # Check if cimflow is available
    if ! command -v cimflow &> /dev/null; then
        echo -e "${RED}Error: cimflow not found. Run ./install.sh first.${NC}"
        exit 1
    fi

    # Check models exist
    check_models

    # Run batch
    echo -e "Running batch configuration..."
    cd "$SCRIPT_DIR"
    cimflow run from-file batch.json $VERBOSE

    echo ""
    echo -e "${GREEN}=== Examples completed ===${NC}"
    echo -e "Results saved to: ${CYAN}$REPO_ROOT/output/examples/${NC}"
}

# Main
if [ "$DOWNLOAD" = true ]; then
    download_models
fi

if [ "$RUN_EXAMPLES" = true ]; then
    run_examples
fi
