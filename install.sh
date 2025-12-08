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

# Track installation status
INSTALL_ERRORS=0
CRITICAL_ERRORS=0

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

echo -e "${CYAN}Initializing and updating submodules...${NC}"
git submodule init
git submodule update --init

# Initialize nested submodules in each module
for submodule_dir in modules/*/; do
    if [ -d "$submodule_dir/.git" ] || [ -f "$submodule_dir/.git" ]; then
        echo -e "${CYAN}Initializing nested submodules in $submodule_dir...${NC}"
        (cd "$submodule_dir" && git submodule update --init --recursive) || {
            echo -e "${YELLOW}Warning: Some nested submodules in $submodule_dir may not be initialized${NC}"
        }
    fi
done

echo -e "${CYAN}Executing submodule installation scripts...${NC}"
# Iterate over all directories in 'modules/' and execute 'install.sh' if it exists.
for submodule_dir in modules/*/; do
    if [ -d "$submodule_dir" ]; then
        echo -e "${YELLOW}Checking submodule: $submodule_dir${NC}"

        install_script="${submodule_dir}install.sh"
        script_install="${submodule_dir}script/install.sh"

        submodule_name="$(basename "$submodule_dir")"
        installed=false

        if [ -f "$install_script" ]; then
            echo -e "${GREEN}Found install.sh in $submodule_dir. Executing...${NC}"
            if (cd "$submodule_dir" && bash install.sh); then
                installed=true
            else
                echo -e "${RED}Failed to install $submodule_name via install.sh${NC}"
                ((INSTALL_ERRORS++))
            fi
        elif [ -f "$script_install" ]; then
            echo -e "${GREEN}Found script/install.sh in $submodule_dir. Executing...${NC}"
            if (cd "${submodule_dir}script" && bash install.sh); then
                installed=true
            else
                echo -e "${RED}Failed to install $submodule_name via script/install.sh${NC}"
                ((INSTALL_ERRORS++))
            fi
        elif [ -f "${submodule_dir}setup.py" ] || [ -f "${submodule_dir}pyproject.toml" ]; then
            echo -e "${GREEN}Found setup.py or pyproject.toml in $submodule_dir. Executing pip install...${NC}"
            if (cd "$submodule_dir" && pip install -v -e .); then
                installed=true
            else
                echo -e "${RED}Failed to install $submodule_name via pip${NC}"
                ((INSTALL_ERRORS++))
            fi
        else
            echo -e "${YELLOW}No standard installation script found in $submodule_dir.${NC}"
        fi

        if [ "$installed" = true ]; then
            echo -e "${GREEN}✓ Successfully installed $submodule_name${NC}"
        fi
    fi
done

# Install the main project
echo -e "${CYAN}Installing cimflow...${NC}"
if ! pip install -v -e .; then
    echo -e "${RED}ERROR: Failed to install cimflow${NC}"
    ((CRITICAL_ERRORS++))
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
if [ $CRITICAL_ERRORS -gt 0 ]; then
    echo -e "${RED}Installation failed with critical errors.${NC}"
    exit 1
elif [ $INSTALL_ERRORS -gt 0 ]; then
    echo -e "${YELLOW}Installation completed with $INSTALL_ERRORS non-critical error(s).${NC}"
    echo -e "${YELLOW}Some submodules may not be fully functional.${NC}"
    exit 0
else
    echo -e "${GREEN}Installation completed successfully!${NC}"
    exit 0
fi
