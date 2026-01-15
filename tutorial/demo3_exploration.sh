#!/bin/bash
# Demo 3: Design Space Exploration
# Duration: ~8 minutes (including explanation)
#
# This demo shows how to use batch processing to explore different
# hardware configurations and compilation parameters.
#
# Exploration matrix:
#   - Bandwidth (B): 8 vs 16 flits
#   - Batch Size: 1 vs 8 samples

set -eo pipefail

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$REPO_ROOT/output/demo3_exploration"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Extract metric from report
# Report format: "  - latency:            2.73229 ms"
# Field 1: "-", Field 2: "latency:", Field 3: value
get_metric() {
    local report="$1"
    local pattern="$2"
    grep "$pattern" "$report" 2>/dev/null | awk '{print $3}' | head -1
}

echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Demo 3: Design Space Exploration                              ║"
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

echo -e "${GREEN}${BOLD}Batch Processing${NC}"
echo ""
echo "Instead of running one configuration at a time, we can define"
echo "multiple runs in a JSON config file and execute them all at once."
echo ""
echo "This is useful for:"
echo "  - Design space exploration"
echo "  - Performance comparison studies"
echo "  - Reproducible experiments"
echo ""

pause

# Show the batch config
echo -e "${GREEN}${BOLD}Exploration Configuration${NC}"
echo ""
echo "We'll explore a 2x2 matrix:"
echo ""
echo "                    Batch Size = 1    Batch Size = 8"
echo "                   ┌───────────────┬───────────────┐"
echo "  Bandwidth = 8    │    Run 1      │    Run 2      │"
echo "                   ├───────────────┼───────────────┤"
echo "  Bandwidth = 16   │    Run 3      │    Run 4      │"
echo "                   └───────────────┴───────────────┘"
echo ""
echo "Config file: $SCRIPT_DIR/exploration.json"
echo ""

# Show config file
echo -e "${CYAN}${BOLD}\$ cat $SCRIPT_DIR/exploration.json${NC}"
echo ""
cat "$SCRIPT_DIR/exploration.json" | head -40
echo ""

pause

echo -e "${GREEN}${BOLD}Running Batch Exploration${NC}"
echo ""
echo "The 'run from-file' command processes all configurations:"
echo ""
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"
echo -e "${DIM}What to observe: Each configuration runs the full CG + OP + Simulation${NC}"
echo -e "${DIM}pipeline. Larger batch sizes increase compilation time (more instructions${NC}"
echo -e "${DIM}generated). Lower bandwidth increases simulation time (communication overhead).${NC}"
echo -e "${DIM}────────────────────────────────────────────────────────────────────${NC}"

run_cmd cimflow run from-file "$SCRIPT_DIR/exploration.json"

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Batch Processing Complete!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"

pause

# Collect and display results
echo -e "${GREEN}${BOLD}Results Comparison${NC}"
echo ""

# Find the timestamped output directory (batch runs create a subdirectory)
RUN_DIR=$(ls -td "$OUTPUT_DIR"/*/ 2>/dev/null | head -1)
if [ -z "$RUN_DIR" ]; then
    RUN_DIR="$OUTPUT_DIR"
fi

# Find all reports in the run directory
REPORTS=$(ls "$RUN_DIR"/simulation_report_*.txt 2>/dev/null)

if [ -n "$REPORTS" ]; then
    # Print table header
    printf "${BOLD}%-12s %-12s %-15s %-15s %-12s${NC}\n" \
        "Bandwidth" "Batch Size" "Latency (ms)" "TOPS" "TOPS/W"
    printf "%-12s %-12s %-15s %-15s %-12s\n" \
        "---------" "----------" "------------" "----" "------"

    # Print each configuration result by matching filename patterns
    for B in 8 16; do
        for BS in 1 8; do
            # Match pattern: *_B{B}_*_batch{BS}.txt
            REPORT=$(ls "$RUN_DIR"/simulation_report_*_B${B}_*_batch${BS}.txt 2>/dev/null | head -1)

            if [ -f "$REPORT" ]; then
                LATENCY=$(get_metric "$REPORT" "latency:")
                TOPS=$(get_metric "$REPORT" "TOPS:")
                TOPSW=$(get_metric "$REPORT" "TOPS/W:")
                printf "%-12s %-12s %-15s %-15s %-12s\n" \
                    "B=$B" "$BS" "${LATENCY:-N/A}" "${TOPS:-N/A}" "${TOPSW:-N/A}"
            else
                printf "%-12s %-12s %-15s %-15s %-12s\n" \
                    "B=$B" "$BS" "N/A" "N/A" "N/A"
            fi
        done
    done

    echo ""
else
    echo "No reports found in $RUN_DIR"
    echo ""
    echo "Directory structure:"
    ls -la "$OUTPUT_DIR" 2>/dev/null || echo "Directory not found"
fi

pause

# Analysis
echo -e "${GREEN}${BOLD}Analysis${NC}"
echo ""
echo "Key observations:"
echo ""
echo -e "  1. ${BOLD}Bandwidth effect:${NC}"
echo "     Higher bandwidth (B=16) reduces communication latency"
echo "     More benefit for communication-bound layers"
echo ""
echo -e "  2. ${BOLD}Batch size effect:${NC}"
echo "     Larger batches improve throughput (TOPS)"
echo "     Better utilization of CIM array parallelism"
echo "     But increases total latency per batch"
echo ""
echo -e "  3. ${BOLD}Efficiency (TOPS/W):${NC}"
echo "     Balance between performance and power"
echo "     Optimal point depends on application requirements"
echo ""

pause

# Wrap up
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}Tutorial Complete!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "You've learned:"
echo "  - Demo 0: Setup and verification"
echo "  - Demo 1: Quick end-to-end pipeline (cimflow run pipeline)"
echo "  - Demo 2: Step-by-step compilation stages"
echo "  - Demo 3: Batch processing for design exploration"
echo ""
echo "To run your own experiments, modify exploration.json or create"
echo "your own batch configuration file."
echo ""
echo "For more information:"
echo "  - cimflow --help"
echo "  - cim-compiler --help"
echo "  - https://github.com/BUAA-CI-LAB/CIMFlow"
echo ""
