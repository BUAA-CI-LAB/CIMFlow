#!/bin/bash
# download_models.sh - Download example ONNX models for CIMFlow
#
# Usage:
#   ./scripts/download_models.sh           # Download to data/models/
#   ./scripts/download_models.sh --force   # Re-download even if exists

set -eo pipefail

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
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Download example ONNX models for CIMFlow tutorials and examples."
            echo ""
            echo "Options:"
            echo "  --force, -f   Re-download even if models already exist"
            echo "  --help, -h    Show this help"
            echo ""
            echo "Models are downloaded from:"
            echo "  $RELEASE_URL/$MODELS_ZIP"
            echo ""
            echo "And extracted to:"
            echo "  $MODELS_DIR/"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}=== CIMFlow Model Downloader ===${NC}"
echo ""

DATA_DIR="$REPO_ROOT/data"
mkdir -p "$DATA_DIR"

# Check if models already exist
if ls "$MODELS_DIR"/*.onnx 1> /dev/null 2>&1; then
    if [ "$FORCE" = true ]; then
        echo -e "${YELLOW}Removing existing models (--force)...${NC}"
        rm -rf "$MODELS_DIR"
    else
        echo -e "${GREEN}Models already exist in $MODELS_DIR${NC}"
        echo ""
        echo "Available models:"
        ls -1 "$MODELS_DIR"/*.onnx 2>/dev/null | xargs -n1 basename | while read model; do
            echo "  - $model"
        done
        echo ""
        echo -e "${YELLOW}Use --force to re-download${NC}"
        exit 0
    fi
fi

echo "Downloading $MODELS_ZIP..."
cd "$DATA_DIR"

if curl -fsSL -o "$MODELS_ZIP" "$RELEASE_URL/$MODELS_ZIP"; then
    # Verify it's a valid zip file (using unzip -t, no file utility needed)
    if unzip -t "$MODELS_ZIP" >/dev/null 2>&1; then
        echo "Extracting..."
        unzip -q "$MODELS_ZIP"
        rm "$MODELS_ZIP"
        echo ""
        echo -e "${GREEN}Models downloaded to $MODELS_DIR${NC}"
        echo ""
        echo "Available models:"
        for model in "$MODELS_DIR"/*.onnx; do
            [ -f "$model" ] && echo "  - $(basename "$model")"
        done
    else
        echo -e "${RED}Downloaded file is not a valid zip archive${NC}"
        rm -f "$MODELS_ZIP"
        exit 1
    fi
else
    echo -e "${RED}Failed to download models${NC}"
    echo ""
    echo "Please download manually from:"
    echo "  $RELEASE_URL/$MODELS_ZIP"
    echo ""
    echo "And extract to:"
    echo "  $MODELS_DIR/"
    exit 1
fi
