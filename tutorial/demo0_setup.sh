#!/bin/bash
# Demo 0: Setup and Verification
# Duration: ~3 minutes
#
# This demo verifies the CIMFlow installation and shows basic usage.
# Run this first to ensure everything is working.

set -eo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# Helper to display and run commands
run_cmd() {
    echo ""
    echo -e "${CYAN}${BOLD}\$ $@${NC}"
    echo ""
    "$@"
}

# Helper to pause for presenter
pause() {
    echo ""
    echo -e "${YELLOW}[Press Enter to continue...]${NC}"
    read -r
}

echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Demo 0: Setup and Verification                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Version check
echo -e "${GREEN}${BOLD}Step 1: Check CIMFlow version${NC}"
run_cmd cimflow --version

pause

# Step 2: Show help
echo -e "${GREEN}${BOLD}Step 2: Explore available commands${NC}"
run_cmd cimflow --help

pause

# Step 3: Show run subcommands
echo -e "${GREEN}${BOLD}Step 3: Pipeline execution options${NC}"
run_cmd cimflow run --help

pause

# Step 4: Show compile subcommands
echo -e "${GREEN}${BOLD}Step 4: Compilation stages${NC}"
run_cmd cimflow compile --help

pause

# Step 5: Check compiler and simulator
echo -e "${GREEN}${BOLD}Step 5: Check CIM Compiler and Simulator${NC}"
run_cmd cim-compiler --version
run_cmd cim-simulator --version

pause

# Step 6: Shell completion
echo -e "${GREEN}${BOLD}Step 6: Install shell auto-completion${NC}"
run_cmd cimflow --install-completion
echo ""
echo "Tab completion installed. Run 'source ~/.bashrc' to activate."
echo ""

pause

# Step 7: Verify models
echo -e "${GREEN}${BOLD}Step 7: Check example models${NC}"
MODELS_DIR="$REPO_ROOT/data/models"
if [ -d "$MODELS_DIR" ] && ls "$MODELS_DIR"/*.onnx >/dev/null 2>&1; then
    echo ""
    echo "Available models in $MODELS_DIR:"
    ls -lh "$MODELS_DIR"/*.onnx 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
else
    echo ""
    echo -e "${YELLOW}Models not found. They will be downloaded on first run.${NC}"
fi

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Setup complete! Ready for demos.${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Next: Run './tutorial/demo1_quickstart.sh' for a quick end-to-end pipeline"
