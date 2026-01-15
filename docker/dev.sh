#!/bin/bash
# Start CIMFlow development container
#
# Usage:
#   ./docker/dev.sh              # Start or attach to persistent container
#   ./docker/dev.sh --fresh      # Start fresh ephemeral container
#   ./docker/dev.sh --build      # Rebuild image first
#   ./docker/dev.sh <cmd>        # Run a command and exit
#
# Inside the container:
#   - Type 'exit' or press Ctrl+D to stop and exit
#   - Press Ctrl+P, Ctrl+Q to detach (container keeps running)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="ghcr.io/buaa-ci-lab/cimflow-tutorial:dev-base"
LOCAL_IMAGE="cimflow-dev-base"
CONTAINER_NAME="cimflow-dev"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
BUILD=false
FRESH=false
REMOVE=false
NO_CACHE=false
CMD_ARGS=()  # Use array to preserve argument boundaries

while [[ $# -gt 0 ]]; do
    case $1 in
        --build|-b)
            BUILD=true
            shift
            ;;
        --no-cache)
            BUILD=true
            NO_CACHE=true
            shift
            ;;
        --fresh|-f)
            FRESH=true
            shift
            ;;
        --rm|--remove)
            REMOVE=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./docker/dev.sh [OPTIONS] [COMMAND]"
            echo ""
            echo "Options:"
            echo "  --build, -b    Rebuild the dev image before starting"
            echo "  --no-cache     Rebuild image from scratch (no Docker layer cache)"
            echo "  --fresh, -f    Start fresh ephemeral container (uses --rm)"
            echo "  --rm, --remove Remove existing persistent container and exit"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./docker/dev.sh              # Start or attach to persistent container"
            echo "  ./docker/dev.sh --fresh      # Start fresh container (lost on exit)"
            echo "  ./docker/dev.sh --build      # Rebuild image, then start"
            echo "  ./docker/dev.sh --no-cache   # Full rebuild without cache"
            echo "  ./docker/dev.sh cimflow -V   # Run command and exit"
            echo "  ./docker/dev.sh --rm         # Remove persistent container"
            echo ""
            echo "Inside the container:"
            echo "  exit        - Stop and exit container"
            echo "  Ctrl+D      - Same as exit"
            echo "  Ctrl+P,Q    - Detach (container keeps running, reattach with ./docker/dev.sh)"
            exit 0
            ;;
        *)
            CMD_ARGS=("$@")  # Store all remaining args as array
            break
            ;;
    esac
done

cd "$REPO_ROOT"

# Handle --rm flag
if [ "$REMOVE" = true ]; then
    if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
        echo -e "${CYAN}Removing container '$CONTAINER_NAME'...${NC}"
        docker rm -f "$CONTAINER_NAME"
        echo -e "${GREEN}Container removed.${NC}"
    else
        echo -e "${YELLOW}Container '$CONTAINER_NAME' does not exist.${NC}"
    fi
    exit 0
fi

# Build if requested
if [ "$BUILD" = true ]; then
    if [ "$NO_CACHE" = true ]; then
        echo -e "${CYAN}Building dev image (no cache)...${NC}"
        docker build --no-cache -f docker/Dockerfile.dev-base -t "$LOCAL_IMAGE" .
    else
        echo -e "${CYAN}Building dev image...${NC}"
        docker build -f docker/Dockerfile.dev-base -t "$LOCAL_IMAGE" .
    fi
    IMAGE_NAME="$LOCAL_IMAGE"
fi

# Check if image exists (try local first, then remote)
if docker image inspect "$LOCAL_IMAGE" >/dev/null 2>&1; then
    IMAGE_NAME="$LOCAL_IMAGE"
elif ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo -e "${YELLOW}Image not found locally. Pulling from registry...${NC}"
    if ! docker pull "$IMAGE_NAME" 2>/dev/null; then
        echo -e "${YELLOW}Remote image not available. Building locally...${NC}"
        docker build -f docker/Dockerfile.dev-base -t "$LOCAL_IMAGE" .
        IMAGE_NAME="$LOCAL_IMAGE"
    fi
fi

echo -e "${CYAN}CIMFlow Development Container${NC}"
echo -e "${GREEN}Source:${NC} $REPO_ROOT"
echo -e "${GREEN}Image:${NC}  $IMAGE_NAME"
echo ""

# Run command mode (always ephemeral)
if [ ${#CMD_ARGS[@]} -gt 0 ]; then
    docker run --rm \
        -v "$REPO_ROOT":/app/cimflow \
        -v "$REPO_ROOT/output":/app/output \
        -w /app/cimflow \
        "$IMAGE_NAME" \
        "${CMD_ARGS[@]}"  # Properly quoted array expansion
    exit 0
fi

# Fresh ephemeral container mode
if [ "$FRESH" = true ]; then
    echo -e "${YELLOW}Starting fresh container (will be removed on exit)...${NC}"
    echo -e "${YELLOW}Tip: Ctrl+P,Q to detach, 'exit' to stop${NC}"
    echo ""
    docker run -it --rm \
        -v "$REPO_ROOT":/app/cimflow \
        -v "$REPO_ROOT/output":/app/output \
        -w /app/cimflow \
        "$IMAGE_NAME"
    exit 0
fi

# Persistent container mode (default)
# Check container state
CONTAINER_EXISTS=$(docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1 && echo "yes" || echo "no")
CONTAINER_RUNNING=$(docker container inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || echo "false")

if [ "$CONTAINER_EXISTS" = "yes" ]; then
    if [ "$CONTAINER_RUNNING" = "true" ]; then
        # Container is running - attach to it
        echo -e "${GREEN}Attaching to running container '$CONTAINER_NAME'...${NC}"
        echo -e "${YELLOW}Tip: Ctrl+P,Q to detach, 'exit' to stop${NC}"
        echo ""
        docker attach "$CONTAINER_NAME"
    else
        # Container exists but stopped - start and attach
        echo -e "${GREEN}Starting stopped container '$CONTAINER_NAME'...${NC}"
        echo -e "${YELLOW}Tip: Ctrl+P,Q to detach, 'exit' to stop${NC}"
        echo ""
        docker start -ai "$CONTAINER_NAME"
    fi
else
    # Container doesn't exist - create it
    echo -e "${GREEN}Creating persistent container '$CONTAINER_NAME'...${NC}"
    echo -e "${YELLOW}Tip: Ctrl+P,Q to detach, 'exit' to stop${NC}"
    echo -e "${YELLOW}      Use './docker/dev.sh --rm' to remove container${NC}"
    echo ""
    docker run -it \
        --name "$CONTAINER_NAME" \
        -v "$REPO_ROOT":/app/cimflow \
        -v "$REPO_ROOT/output":/app/output \
        -w /app/cimflow \
        "$IMAGE_NAME"
fi
