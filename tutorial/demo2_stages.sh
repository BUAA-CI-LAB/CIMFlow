#!/bin/bash
# Demo 2: Step-by-Step Compilation Stages
# Duration: ~12 minutes (including explanation)
#
# This demo breaks down the CIMFlow pipeline into individual stages,
# showing the intermediate representations at each step.
#
# Stages:
#   1. CG Compilation: ONNX -> Compute Graph Instructions
#   2. OP Compilation: CG Instructions -> ISA Instructions (JSON)
#   3. Format Conversion: JSON -> Assembly (human-readable)
#   4. Simulation: ISA -> Performance Report

set -eo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${CIMFLOW_OUTPUT_DIR:-$REPO_ROOT/output}/demo2_stages"

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

# Helper to show file preview
show_preview() {
    local file="$1"
    local lines="${2:-15}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────${NC}"
    head -n "$lines" "$file"
    echo -e "${DIM}... (truncated)${NC}"
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────${NC}"
}

echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Demo 2: Step-by-Step Compilation Stages                       ║"
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

# Create output directories
mkdir -p "$OUTPUT_DIR"/{cg,op,sim}

echo -e "${GREEN}${BOLD}Overview${NC}"
echo ""
echo "We'll compile ResNet-18 through each stage:"
echo ""
echo "  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐"
echo "  │  ONNX Model │ -> │ CG Compile  │ -> │ OP Compile  │ -> │  Simulate   │"
echo "  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘"
echo "                           │                  │                  │"
echo "                           v                  v                  v"
echo "                     CG Instructions    ISA (JSON/ASM)    Performance"
echo ""

pause

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: CG Compilation
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Stage 1: CG-Level Compilation${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "CG (Compute Graph) compilation:"
echo "  - Parses the ONNX model"
echo "  - Analyzes layer dependencies"
echo "  - Partitions computation into stages across cores"
echo "  - Generates high-level operation schedule"
echo ""
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"
echo -e "${DIM}What's happening: The progress bar shows dynamic programming solving${NC}"
echo -e "${DIM}the optimal graph-to-stage mapping. Each 'prefix' represents a subgraph.${NC}"
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"

run_cmd cimflow compile cg \
    -m "$MODEL" \
    -o "$OUTPUT_DIR/cg" \
    -l VERBOSE

pause

# Show CG output
echo -e "${GREEN}${BOLD}CG Output: Compute Graph Instructions${NC}"
CG_FILE=$(ls "$OUTPUT_DIR"/cg/instructions_*.json 2>/dev/null | head -1)
if [ -f "$CG_FILE" ]; then
    echo ""
    echo "File: $(basename "$CG_FILE")"
    show_preview "$CG_FILE" 20

    # Count operations
    OP_COUNT=$(grep -c '"op":' "$CG_FILE" 2>/dev/null || echo "?")
    echo ""
    echo "This file contains $OP_COUNT high-level CIM operations (read/compute/write)."
fi

pause

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: OP Compilation
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Stage 2: OP-Level Compilation${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "OP (Operation) compilation:"
echo "  - Takes CG instructions as input"
echo "  - Generates ISA instructions for each core"
echo "  - Handles memory allocation and data movement"
echo "  - Optimizes instruction scheduling"
echo ""
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"
echo -e "${DIM}What's happening: Each core gets its own instruction sequence. The${NC}"
echo -e "${DIM}compiler handles SRAM tiling, weight loading, and synchronization.${NC}"
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"

run_cmd cimflow compile op \
    -i "$CG_FILE" \
    -o "$OUTPUT_DIR/op" \
    -t 8 -b 16 \
    -l VERBOSE

pause

# Show OP output
echo -e "${GREEN}${BOLD}OP Output: ISA Instructions (JSON format)${NC}"
ISA_FILE=$(ls "$OUTPUT_DIR"/op/isa_instructions_*.json 2>/dev/null | head -1)
if [ -f "$ISA_FILE" ]; then
    echo ""
    echo "File: $(basename "$ISA_FILE")"
    show_preview "$ISA_FILE" 20

    # Count instructions
    INST_COUNT=$(grep -c '"opcode":' "$ISA_FILE" 2>/dev/null || echo "?")
    echo ""
    echo "This file contains $INST_COUNT ISA instructions across all cores."
fi

pause

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2.5: Format Conversion (JSON -> ASM)
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Bonus: Convert to Human-Readable Assembly${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "The JSON format is machine-readable but verbose."
echo "We can convert to assembly format for easier inspection:"
echo ""

ASM_FILE="$OUTPUT_DIR/op/isa_instructions.asm"

run_cmd cim-compiler convert \
    --src-type json \
    --dst-type asm \
    --src-file "$ISA_FILE" \
    --dst-file "$ASM_FILE"

pause

echo -e "${GREEN}${BOLD}Assembly Output${NC}"
if [ -f "$ASM_FILE" ]; then
    echo ""
    echo "File: $(basename "$ASM_FILE")"
    show_preview "$ASM_FILE" 25
    echo ""
    echo "Each line is one instruction: OPCODE operands..."
    echo "Much easier to read than JSON!"
fi

pause

# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3: Simulation
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Stage 3: Cycle-Accurate Simulation${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "The SystemC simulator:"
echo "  - Executes ISA instructions cycle-by-cycle"
echo "  - Models CIM array computation"
echo "  - Simulates NoC communication"
echo "  - Tracks power and energy consumption"
echo ""
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"
echo -e "${DIM}What's happening: The simulator models all 64 cores in parallel,${NC}"
echo -e "${DIM}tracking data movement through the NoC and CIM array operations.${NC}"
echo -e "${DIM}Power is estimated from a calibrated energy model.${NC}"
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"

run_cmd cimflow sim \
    -i "$ISA_FILE" \
    -o "$OUTPUT_DIR/sim" \
    -t 8 -b 16 \
    -l VERBOSE

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Simulation Results${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"

# Derive report filename from ISA filename: isa_instructions_*.json -> simulation_isa_instructions_*.txt
ISA_BASENAME=$(basename "$ISA_FILE" .json)
REPORT="$OUTPUT_DIR/sim/simulation_${ISA_BASENAME}.txt"
if [ -f "$REPORT" ]; then
    echo ""
    echo "Key metrics:"
    echo ""
    grep -E "latency:|average power:|total energy:|TOPS:|TOPS/W:" "$REPORT" | head -6 | sed 's/^/  /'
else
    echo ""
    echo "Report not found: $REPORT"
fi

pause

# Summary
echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Summary: Output Files${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
tree "$OUTPUT_DIR" 2>/dev/null || ls -la "$OUTPUT_DIR"/*
echo ""
echo "Key files:"
echo "  - cg/instructions_*.json     : High-level compute graph operations"
echo "  - op/isa_instructions_*.json : Low-level ISA (JSON format)"
echo "  - op/isa_instructions.asm    : Low-level ISA (Assembly format)"
echo "  - sim/simulation_*.txt       : Performance metrics"
echo ""
echo "Next: Run './tutorial/demo3_exploration.sh' to explore the design space"
