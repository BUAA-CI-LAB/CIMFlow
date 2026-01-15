#!/bin/bash
# Demo 1: Quick Start - End-to-End Pipeline
# Duration: ~5 minutes (including explanation)
#
# This demo runs a complete compilation and simulation pipeline
# with a single command. Perfect for getting started quickly.

set -eo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${CIMFLOW_OUTPUT_DIR:-$REPO_ROOT/output}/demo1_quickstart"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
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
echo "║  Demo 1: Quick Start - End-to-End Pipeline                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check model
MODEL="$REPO_ROOT/data/models/resnet18.onnx"
if [ ! -f "$MODEL" ]; then
    echo -e "${YELLOW}Model not found. Downloading...${NC}"
    if [ -f /app/entrypoint.sh ]; then
        /app/entrypoint.sh true
    else
        echo "Please download models first or run in Docker."
        exit 1
    fi
fi

echo -e "${GREEN}${BOLD}The Pipeline Command${NC}"
echo ""
echo "CIMFlow compiles ONNX models to CIM hardware instructions and simulates them."
echo "The 'run pipeline' command does everything in one step:"
echo ""
echo "  ONNX Model -> CG Compilation -> OP Compilation -> Simulation -> Report"
echo ""

pause

echo -e "${GREEN}${BOLD}Running the pipeline...${NC}"
echo ""
echo "Parameters:"
echo "  - Model: ResNet-18"
echo "  - Macro Group Size (T): 8"
echo "  - Macro Group Count (K): 16"
echo "  - NoC Bandwidth (B): 16 flits"
echo "  - Core Count (C): 64"
echo "  - Batch Size: 8"
echo ""
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"
echo -e "${DIM}What's happening:${NC}"
echo -e "${DIM}  - CG stage: Progress bar shows graph partitioning into execution stages${NC}"
echo -e "${DIM}  - OP stage: Progress bar shows per-core instruction generation${NC}"
echo -e "${DIM}  - Simulation: Cycle-accurate execution across all cores${NC}"
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"

run_cmd cimflow run pipeline \
    -m "$MODEL" \
    -o "$OUTPUT_DIR" \
    -t 8 -k 16 -b 16 -c 64 \
    --batch-size 8

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Pipeline completed!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"

pause

# Display results
echo -e "${GREEN}${BOLD}Simulation Results${NC}"
echo ""

REPORT=$(ls -t "$OUTPUT_DIR"/simulation_report_*.txt 2>/dev/null | head -1)
if [ -f "$REPORT" ]; then
    echo "Key metrics from $REPORT:"
    echo ""
    grep -E "latency:|average power:|total energy:|TOPS:|TOPS/W:" "$REPORT" | head -6 | sed 's/^/  /'
    echo ""
    echo -e "${CYAN}Full report: $REPORT${NC}"
else
    echo "Report not found in $OUTPUT_DIR"
fi

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "What just happened:"
echo "  1. CG Compilation: Parsed ONNX, created compute graph, partitioned for CIM"
echo "  2. OP Compilation: Generated ISA instructions for each core"
echo "  3. Simulator: Cycle-accurate simulation of CIM hardware execution"
echo ""
echo "Next: Run './tutorial/demo2_stages.sh' to see each stage in detail"
