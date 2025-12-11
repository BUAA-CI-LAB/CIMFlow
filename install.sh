#!/bin/bash
# This script installs the cimflow project and its dependencies,
# including initializing, updating, and potentially installing submodules.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SHALLOW_CLONE=false
REPAIR_MODE=false
RESUME_MODE=false
MAX_RETRIES=3
RETRY_DELAY=5
PROGRESS_FILE="${SCRIPT_DIR}/.install_progress"

# Track installation status
INSTALL_ERRORS=0
CRITICAL_ERRORS=0

# Parse command line arguments
show_help() {
    echo "Usage: ./install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --shallow     Use shallow clones for submodules (faster, less disk space)"
    echo "  --repair      Fix broken/dirty submodules (discards local changes)"
    echo "  --resume      Resume from last completed step"
    echo "  --clean       Remove progress file and start fresh"
    echo "  --uninstall   Remove installed packages and build artifacts"
    echo "  --uninstall --force  Also remove submodule source code"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./install.sh                    # Normal installation"
    echo "  ./install.sh --shallow          # Fast install with shallow clones"
    echo "  ./install.sh --resume           # Continue after interruption"
    echo "  ./install.sh --resume --repair  # Resume and fix broken submodules"
    echo "  ./install.sh --clean --shallow  # Fresh shallow install"
    echo "  ./install.sh --uninstall        # Remove installation"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --shallow)
            SHALLOW_CLONE=true
            shift
            ;;
        --repair)
            REPAIR_MODE=true
            shift
            ;;
        --resume)
            RESUME_MODE=true
            shift
            ;;
        --clean)
            rm -f "$PROGRESS_FILE"
            echo -e "${GREEN}Cleaned progress file. Starting fresh.${NC}"
            shift
            ;;
        --uninstall)
            # Check if --force is also specified
            FORCE_UNINSTALL=false
            if [[ "${2:-}" == "--force" ]] || [[ "${2:-}" == "-f" ]]; then
                FORCE_UNINSTALL=true
            fi

            if [ "$FORCE_UNINSTALL" = true ]; then
                echo -e "${CYAN}Force uninstalling CIMFlow (removing everything)...${NC}"
            else
                echo -e "${CYAN}Uninstalling CIMFlow...${NC}"
            fi

            # Uninstall Python packages
            echo -e "${CYAN}Removing Python packages...${NC}"
            pip uninstall -y cimflow 2>/dev/null && echo -e "${GREEN}  ✓ Removed cimflow${NC}" || echo -e "${YELLOW}  cimflow not installed${NC}"
            pip uninstall -y cim-compiler 2>/dev/null && echo -e "${GREEN}  ✓ Removed cim-compiler${NC}" || echo -e "${YELLOW}  cim-compiler not installed${NC}"

            # Remove config directory
            if [ -d "config" ]; then
                echo -e "${CYAN}Removing config directory...${NC}"
                rm -rf config
                echo -e "${GREEN}  ✓ Removed config/${NC}"
            fi

            # Remove progress file
            rm -f "$PROGRESS_FILE"

            # Remove build artifacts in submodules
            echo -e "${CYAN}Removing build artifacts...${NC}"
            if [ -d "modules" ] && compgen -G "modules/*/" > /dev/null 2>&1; then
                for submodule_dir in modules/*/; do
                    if [ -d "${submodule_dir}build" ]; then
                        rm -rf "${submodule_dir}build"
                        echo -e "${GREEN}  ✓ Removed ${submodule_dir}build${NC}"
                    fi
                    # Also remove llvm-project build directory if it exists
                    if [ -d "${submodule_dir}thirdparty/llvm-project/build" ]; then
                        rm -rf "${submodule_dir}thirdparty/llvm-project/build"
                        echo -e "${GREEN}  ✓ Removed ${submodule_dir}thirdparty/llvm-project/build${NC}"
                    fi
                done
            fi

            # Force mode: also remove submodule source code
            if [ "$FORCE_UNINSTALL" = true ]; then
                echo -e "${CYAN}Removing submodules...${NC}"
                git submodule deinit -f --all 2>/dev/null || true
                if [ -d "modules" ] && compgen -G "modules/*/" > /dev/null 2>&1; then
                    for submodule_dir in modules/*/; do
                        if [ -d "$submodule_dir" ]; then
                            rm -rf "$submodule_dir"
                            echo -e "${GREEN}  ✓ Removed $submodule_dir${NC}"
                        fi
                    done
                fi

                # Also remove git's cached submodule objects
                if [ -d ".git/modules" ]; then
                    rm -rf .git/modules
                    echo -e "${GREEN}  ✓ Removed .git/modules cache${NC}"
                fi

                echo ""
                echo -e "${GREEN}✓ Force uninstall completed. Run ./install.sh to reinstall.${NC}"
            else
                echo ""
                echo -e "${GREEN}✓ Uninstall completed.${NC}"
                echo -e "${YELLOW}Submodule source code preserved. Use --uninstall --force to remove everything.${NC}"
            fi
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Progress tracking functions
mark_step_complete() {
    local step="$1"
    echo "$step" >> "$PROGRESS_FILE"
}

is_step_complete() {
    local step="$1"
    [ -f "$PROGRESS_FILE" ] && grep -qxF "$step" "$PROGRESS_FILE"
}

# Check if a submodule is healthy
check_submodule_health() {
    local path="$1"

    # Check if directory exists
    if [ ! -d "$path" ]; then
        echo "missing"
        return
    fi

    # Check if .git exists (file for submodules, dir for regular repos)
    if [ ! -e "$path/.git" ]; then
        echo "no-git"
        return
    fi

    # Check if HEAD is valid
    if ! (cd "$path" && git rev-parse HEAD >/dev/null 2>&1); then
        echo "corrupt"
        return
    fi

    # Check submodule status
    local status_char
    status_char=$(git submodule status "$path" 2>/dev/null | cut -c1)
    case "$status_char" in
        "-") echo "not-initialized"; return ;;
        "+") echo "wrong-commit"; return ;;
        "U") echo "conflict"; return ;;
    esac

    # Check if submodule has uncommitted changes (dirty)
    local porcelain_status
    porcelain_status=$(git status --porcelain "$path" 2>/dev/null)
    if [[ "$porcelain_status" == "M "* ]] || [[ "$porcelain_status" == " M"* ]]; then
        echo "dirty"
        return
    fi

    echo "healthy"
}

# Repair a broken submodule
repair_submodule() {
    local path="$1"
    local health="$2"
    local name
    name="$(basename "$path")"

    echo -e "${YELLOW}Repairing $name (status: $health)...${NC}"

    case "$health" in
        missing|no-git|corrupt|not-initialized)
            # Complete re-initialization needed
            echo -e "${CYAN}  Removing and re-initializing...${NC}"
            rm -rf "$path"
            git submodule update --init --progress "$path"
            ;;
        wrong-commit)
            # Just update to correct commit
            echo -e "${CYAN}  Updating to correct commit...${NC}"
            git submodule update --init "$path"
            ;;
        dirty)
            # Discard local changes and restore to clean state
            echo -e "${CYAN}  Discarding local changes...${NC}"
            git submodule update --force "$path"
            ;;
        conflict)
            # Deinit and reinit
            echo -e "${CYAN}  Resolving conflict...${NC}"
            git submodule deinit -f "$path"
            git submodule update --init "$path"
            ;;
    esac

    echo -e "${GREEN}  ✓ Repaired $name${NC}"
}

# Cleanup on interrupt
cleanup() {
    printf "\r\033[K"
    echo -e "\n${YELLOW}Installation interrupted. Run './install.sh --resume' to continue.${NC}"
    exit 130
}
trap cleanup INT TERM

# Retry a command with exponential backoff
retry_command() {
    local cmd="$1"
    local description="$2"
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        # Only show attempt number on retries, not on first try
        if [ $attempt -eq 1 ]; then
            echo -e "${CYAN}$description...${NC}"
        else
            echo -e "${CYAN}$description (retry $attempt/$MAX_RETRIES)...${NC}"
        fi

        if eval "$cmd"; then
            return 0
        fi

        if [ $attempt -lt $MAX_RETRIES ]; then
            local wait_time=$((RETRY_DELAY * attempt))
            echo -e "${YELLOW}Failed. Retrying in ${wait_time}s...${NC}"
            sleep $wait_time
        fi
        ((attempt++))
    done

    echo -e "${RED}Failed after $MAX_RETRIES attempts.${NC}"
    return 1
}

# Initialize submodule with progress and retry
init_submodule_robust() {
    local path="$1"
    local name
    name="$(basename "$path")"
    local depth_flag=""

    if [ "$SHALLOW_CLONE" = true ]; then
        depth_flag="--depth 1"
    fi

    # Check health first
    local health
    health=$(check_submodule_health "$path")

    if [ "$health" = "healthy" ]; then
        echo -e "${GREEN}✓ $name is healthy${NC}"
        return 0
    fi

    # Auto-repair broken submodules only in repair mode
    if [ "$health" != "missing" ]; then
        if [ "$REPAIR_MODE" = true ]; then
            repair_submodule "$path" "$health"
            return $?
        else
            # Not in repair mode, warn user about broken state
            echo -e "${YELLOW}⚠ $name appears broken (status: $health)${NC}"
            echo -e "${YELLOW}  Run with --repair to fix, or delete and retry${NC}"
        fi
    fi

    # Initialize with retry
    local cmd="git submodule update --init --progress $depth_flag \"$path\""
    retry_command "$cmd" "Initializing $name"
}

# Check dependencies
echo -e "${CYAN}Checking dependencies...${NC}"
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Python is not installed or not in PATH${NC}"
    exit 1
fi

if ! command -v pip >/dev/null 2>&1; then
    echo -e "${RED}ERROR: pip is not installed or not in PATH${NC}"
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo -e "${RED}ERROR: git is not installed or not in PATH${NC}"
    exit 1
fi

echo -e "${GREEN}All required dependencies found.${NC}"

# Step 1: Initialize top-level submodules
if ! is_step_complete "submodules_init"; then
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Step 1/4: Initializing submodules...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

    git submodule init

    # Initialize each top-level submodule with health check
    # Get submodule paths from .gitmodules (not from directory listing, as dirs may not exist yet)
    _step1_errors=0
    while IFS= read -r submodule_path; do
        if [ -n "$submodule_path" ]; then
            init_submodule_robust "$submodule_path" || {
                echo -e "${RED}ERROR: Failed to initialize $submodule_path${NC}"
                ((CRITICAL_ERRORS++))
                ((_step1_errors++))
            }
        fi
    done < <(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}')

    # Only mark complete if no errors in this step
    if [ "$_step1_errors" -eq 0 ]; then
        mark_step_complete "submodules_init"
        echo -e "${GREEN}✓ Top-level submodules initialized${NC}"
    else
        echo -e "${RED}✗ Top-level submodule initialization had errors${NC}"
    fi
else
    echo -e "${GREEN}✓ Skipping submodule init (already complete)${NC}"
fi

# Step 2: Initialize nested submodules (like llvm-project)
# Check if we need to run this step
run_nested_init=false
if ! is_step_complete "nested_submodules"; then
    run_nested_init=true
elif [ "$RESUME_MODE" = true ] || [ "$REPAIR_MODE" = true ]; then
    # In resume/repair mode, verify nested submodules are actually healthy
    if [ -d "modules" ] && compgen -G "modules/*/" > /dev/null 2>&1; then
    for submodule_dir in modules/*/; do
        if [ -f "${submodule_dir}.gitmodules" ]; then
            # Check if any nested submodule is uninitialized or at wrong commit
            if (cd "$submodule_dir" && git submodule status --recursive 2>/dev/null | grep -qE '^[-+]'); then
                echo -e "${YELLOW}⚠ Found incomplete nested submodules, will re-run initialization${NC}"
                run_nested_init=true
                break
            fi
            # Also check for partially cloned repos (e.g., llvm-project missing mlir/)
            while IFS= read -r nested_path; do
                nested_full="${submodule_dir}${nested_path}"
                if [ -d "$nested_full" ] && [ -e "$nested_full/.git" ]; then
                    # For llvm-project, check if mlir directory exists (required for build)
                    if [[ "$nested_path" == *"llvm-project"* ]] && [ ! -d "$nested_full/mlir" ]; then
                        echo -e "${YELLOW}⚠ llvm-project is incomplete (missing mlir/), will re-clone${NC}"
                        run_nested_init=true
                        break 2
                    fi
                    # Check if repo is actually complete by verifying HEAD
                    if ! (cd "$nested_full" && git rev-parse HEAD >/dev/null 2>&1 && [ -n "$(ls -A)" ]); then
                        echo -e "${YELLOW}⚠ Found partially cloned submodule: $nested_path${NC}"
                        run_nested_init=true
                        break 2
                    fi
                fi
            done < <(cd "$submodule_dir" && git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}')
        fi
    done
    fi
fi

if [ "$run_nested_init" = true ]; then
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Step 2/4: Initializing nested submodules...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}⚠ This step may take 10-30 minutes for large repos like llvm-project.${NC}"
    echo -e "${YELLOW}  Press Ctrl+C to cancel (use --resume to continue later).${NC}"

    _step2_errors=0

    if [ "$SHALLOW_CLONE" = true ]; then
        echo -e "${YELLOW}  Using shallow clones for faster downloads.${NC}"
    fi
    echo

    for submodule_dir in modules/*/; do
        if [ -d "$submodule_dir/.git" ] || [ -f "$submodule_dir/.git" ]; then
            submodule_name="$(basename "$submodule_dir")"

            # Check if there are any nested submodules
            if [ -f "${submodule_dir}.gitmodules" ]; then
                # Count nested submodules
                nested_count=$(git config --file "${submodule_dir}.gitmodules" --get-regexp '^submodule\..*\.path$' 2>/dev/null | wc -l)
                if [ "$nested_count" -gt 0 ]; then
                    echo -e "${CYAN}Initializing $nested_count nested submodule(s) in $submodule_name...${NC}"
                fi

                # In repair mode, check and fix broken nested submodules
                if [ "$REPAIR_MODE" = true ]; then
                    while IFS= read -r nested_path; do
                        nested_full="${submodule_dir}${nested_path}"
                        _needs_reclone=false
                        _reason=""

                        if [ -d "$nested_full" ]; then
                            if [ ! -e "$nested_full/.git" ]; then
                                # Directory exists but no .git - incomplete clone
                                _needs_reclone=true
                                _reason="missing .git"
                            elif ! (cd "$nested_full" && git rev-parse HEAD >/dev/null 2>&1); then
                                # .git exists but HEAD is invalid
                                _needs_reclone=true
                                _reason="corrupt HEAD"
                            elif [[ "$nested_path" == *"llvm-project"* ]] && [ ! -d "$nested_full/mlir" ]; then
                                # llvm-project specific: check for mlir directory
                                _needs_reclone=true
                                _reason="missing mlir/"
                            fi
                        fi

                        if [ "$_needs_reclone" = true ]; then
                            echo -e "${YELLOW}  Removing incomplete submodule: $nested_path ($_reason)${NC}"
                            rm -rf "$nested_full"
                        fi
                    done < <(cd "$submodule_dir" && git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}')
                fi

                # In repair mode, use --force to re-checkout partially cloned submodules
                _force_flag=""
                if [ "$REPAIR_MODE" = true ]; then
                    _force_flag="--force"
                fi

                # Initialize each nested submodule separately to control depth per-submodule
                while IFS= read -r nested_path; do
                    nested_name="$(basename "$nested_path")"
                    nested_full="${submodule_dir}${nested_path}"

                    # Build command arguments array
                    _git_args=(submodule update --init --recursive --progress)
                    if [ -n "$_force_flag" ]; then
                        _git_args+=("$_force_flag")
                    fi

                    # Determine depth flag for this submodule
                    _shallow_msg=""
                    if [ "$SHALLOW_CLONE" = true ]; then
                        # User requested shallow clone for all
                        _git_args+=(--depth 1)
                    elif [[ "$nested_path" == *"llvm-project"* ]]; then
                        # Always shallow clone llvm-project (2GB+ full clone)
                        _git_args+=(--depth 1)
                        _shallow_msg=" (shallow clone, 2GB+ otherwise)"
                    fi

                    _git_args+=("$nested_path")

                    echo -e "${CYAN}Initializing $nested_name...${_shallow_msg}${NC}"
                    _attempt=1
                    _success=false

                    while [ $_attempt -le $MAX_RETRIES ]; do
                        if [ $_attempt -gt 1 ]; then
                            echo -e "${CYAN}Initializing $nested_name (retry $_attempt/$MAX_RETRIES)...${NC}"
                        fi

                        pushd "$submodule_dir" > /dev/null

                        if GIT_PROGRESS_DELAY=0 git "${_git_args[@]}"; then
                            _success=true
                        fi

                        popd > /dev/null
                        if [ "$_success" = true ]; then
                            break
                        fi

                        if [ $_attempt -lt $MAX_RETRIES ]; then
                            _wait_time=$((RETRY_DELAY * _attempt))
                            echo -e "${YELLOW}Failed. Retrying in ${_wait_time}s...${NC}"
                            sleep $_wait_time
                        fi
                        ((_attempt++))
                    done

                    if [ "$_success" = false ]; then
                        echo -e "${RED}ERROR: Failed to initialize $nested_name in $submodule_name${NC}"
                        echo -e "${YELLOW}  Try running: ./install.sh --resume${NC}"
                        ((CRITICAL_ERRORS++))
                        ((_step2_errors++))
                    else
                        echo -e "${GREEN}  ✓ $nested_name initialized${NC}"
                    fi
                done < <(cd "$submodule_dir" && git config --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}')
            fi
        fi
    done

    # Only mark complete if no errors in this step
    if [ "$_step2_errors" -eq 0 ]; then
        mark_step_complete "nested_submodules"
        echo -e "${GREEN}✓ Nested submodules initialized${NC}"
    else
        echo -e "${RED}✗ Nested submodule initialization had errors${NC}"
    fi
else
    echo -e "${GREEN}✓ Skipping nested submodule init (already complete)${NC}"
fi

# Step 3: Build and install submodules
if ! is_step_complete "submodules_build"; then
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Step 3/4: Building and installing submodules...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

    _step3_errors=0

    # Iterate over all directories in 'modules/' and execute 'install.sh' if it exists.
    for submodule_dir in modules/*/; do
        if [ -d "$submodule_dir" ]; then
            submodule_name="$(basename "$submodule_dir")"
            step_name="build_${submodule_name}"

            if is_step_complete "$step_name"; then
                echo -e "${GREEN}✓ Skipping $submodule_name (already built)${NC}"
                continue
            fi

            echo -e "${YELLOW}Building: $submodule_name${NC}"

            install_script="${submodule_dir}install.sh"
            script_install="${submodule_dir}script/install.sh"
            installed=false

            if [ -f "$install_script" ]; then
                echo -e "${CYAN}  Running install.sh...${NC}"
                if (cd "$submodule_dir" && bash install.sh); then
                    installed=true
                else
                    echo -e "${RED}  Failed to install $submodule_name via install.sh${NC}"
                    echo -e "${YELLOW}  Try running: ./install.sh --resume (to continue with other modules)${NC}"
                    ((INSTALL_ERRORS++))
                    ((_step3_errors++))
                fi
            elif [ -f "$script_install" ]; then
                echo -e "${CYAN}  Running script/install.sh...${NC}"
                if (cd "${submodule_dir}script" && bash install.sh); then
                    installed=true
                else
                    echo -e "${RED}  Failed to install $submodule_name via script/install.sh${NC}"
                    ((INSTALL_ERRORS++))
                    ((_step3_errors++))
                fi
            elif [ -f "${submodule_dir}setup.py" ] || [ -f "${submodule_dir}pyproject.toml" ]; then
                echo -e "${CYAN}  Running pip install...${NC}"
                if (cd "$submodule_dir" && pip install -v -e .); then
                    installed=true
                else
                    echo -e "${RED}  Failed to install $submodule_name via pip${NC}"
                    ((INSTALL_ERRORS++))
                    ((_step3_errors++))
                fi
            else
                echo -e "${YELLOW}  No installation script found, skipping.${NC}"
                installed=true  # Mark as done since there's nothing to do
            fi

            if [ "$installed" = true ]; then
                mark_step_complete "$step_name"
                echo -e "${GREEN}  ✓ Successfully installed $submodule_name${NC}"
            fi
        fi
    done

    # Only mark complete if no errors in this step
    if [ "$_step3_errors" -eq 0 ]; then
        mark_step_complete "submodules_build"
    else
        echo -e "${YELLOW}Some submodule builds failed. Run --resume to retry.${NC}"
    fi
else
    echo -e "${GREEN}✓ Skipping submodule builds (already complete)${NC}"
fi

# Step 4: Install the main project
if ! is_step_complete "cimflow_install"; then
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Step 4/4: Installing cimflow...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

    if ! pip install -v -e .; then
        echo -e "${RED}ERROR: Failed to install cimflow${NC}"
        ((CRITICAL_ERRORS++))
    else
        mark_step_complete "cimflow_install"
    fi
else
    echo -e "${GREEN}✓ Skipping cimflow install (already complete)${NC}"
fi

# Set up configuration directory
echo -e "${CYAN}Setting up configuration...${NC}"
if [ ! -d "config" ]; then
    mkdir -p config
    echo -e "${GREEN}Created config directory.${NC}"
fi

# Copy tool_paths.json template if it doesn't exist
if [ ! -f "config/tool_paths.json" ]; then
    if [ -f "config_templates/tool_paths_internal.json" ]; then
        cp config_templates/tool_paths_internal.json config/tool_paths.json
        echo -e "${GREEN}Created config/tool_paths.json from internal template.${NC}"
    elif [ -f "config_templates/tool_paths.json" ]; then
        cp config_templates/tool_paths.json config/tool_paths.json
        echo -e "${GREEN}Created config/tool_paths.json from template.${NC}"
        echo -e "${YELLOW}⚠ IMPORTANT: Edit config/tool_paths.json to set your actual paths!${NC}"
        echo -e "${YELLOW}   → config_dir: Directory containing hardware config files${NC}"
        echo -e "${YELLOW}   → profiler_cfg: Path to profiler configuration${NC}"
        echo -e "${YELLOW}   → compiler_bin: CIM compiler executable (default: cim-compiler)${NC}"
        echo -e "${YELLOW}   → simulator_bin: Path to cim-simulator${NC}"
    else
        echo -e "${RED}ERROR: config_templates/tool_paths.json not found${NC}"
        ((INSTALL_ERRORS++))
    fi
else
    echo -e "${GREEN}config/tool_paths.json already exists.${NC}"
fi

echo -e "${CYAN}Installing cimflow CLI completion...${NC}"
if command -v cimflow >/dev/null 2>&1; then
    # More robust shell detection
    if [ -n "${SHELL:-}" ]; then
        shell_name="${SHELL##*/}"
    elif [ -n "${0:-}" ]; then
        shell_name="${0##*/}"
        shell_name="${shell_name#-}"  # Remove leading dash from login shells
    else
        shell_name="unknown"
    fi

    case "$shell_name" in
        bash|zsh|fish|pwsh|powershell)
            if cimflow --install-completion "$shell_name"; then
                echo -e "${GREEN}Installed completion for $shell_name.${NC}"
            else
                echo -e "${YELLOW}Unable to install completion automatically for $shell_name.${NC}"
            fi
            ;;
        *)
            echo -e "${YELLOW}Shell '$shell_name' not supported for automatic completion installation.${NC}"
            echo -e "${YELLOW}Run 'cimflow --show-completion' and configure your shell manually.${NC}"
            ;;
    esac
else
    echo -e "${YELLOW}cimflow command not found in PATH; skipping completion install.${NC}"
fi

# Summary
echo
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
if [ "$CRITICAL_ERRORS" -gt 0 ]; then
    echo -e "${RED}Installation failed with critical errors.${NC}"
    echo -e "${YELLOW}To resume from where you left off, run:${NC}"
    echo -e "${YELLOW}  ./install.sh --resume${NC}"
    echo -e "${YELLOW}To repair broken submodules and retry, run:${NC}"
    echo -e "${YELLOW}  ./install.sh --repair --resume${NC}"
    exit 1
elif [ "$INSTALL_ERRORS" -gt 0 ]; then
    echo -e "${YELLOW}Installation completed with $INSTALL_ERRORS non-critical error(s).${NC}"
    echo -e "${YELLOW}Some submodules may not be fully functional.${NC}"
    # Clean up progress file on partial success
    rm -f "$PROGRESS_FILE"
    exit 0
else
    echo -e "${GREEN}✓ Installation completed successfully!${NC}"
    # Clean up progress file on success
    rm -f "$PROGRESS_FILE"
    exit 0
fi
