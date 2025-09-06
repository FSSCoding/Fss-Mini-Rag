#!/usr/bin/env bash
# FSS-Mini-RAG Installation Script for Linux/macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/fsscoding/fss-mini-rag/main/install.sh | bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PACKAGE_NAME="fss-mini-rag"
COMMAND_NAME="rag-mini"

print_header() {
    echo -e "${CYAN}"
    echo "████████╗██╗   ██╗██████╗ "
    echo "██╔══██║██║   ██║██╔══██╗"
    echo "██████╔╝██║   ██║██████╔╝"
    echo "██╔══██╗██║   ██║██╔══██╗"
    echo "██║  ██║╚██████╔╝██║  ██║"
    echo "╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${BLUE}FSS-Mini-RAG Installation Script${NC}"
    echo -e "${YELLOW}Educational RAG that actually works!${NC}"
    echo
}

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_system() {
    log "Checking system requirements..."
    
    # Check if we're on a supported platform
    case "$(uname -s)" in
        Darwin*) PLATFORM="macOS" ;;
        Linux*)  PLATFORM="Linux" ;;
        *) error "Unsupported platform: $(uname -s). This script supports Linux and macOS only." ;;
    esac
    
    log "Platform: $PLATFORM"
    
    # Check if Python 3.8+ is available
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed. Please install Python 3.8 or later."
    fi
    
    # Check Python version
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    required_version="3.8"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
        error "Python ${python_version} detected, but Python ${required_version}+ is required."
    fi
    
    log "Python ${python_version} detected ✓"
}

install_uv() {
    if command -v uv &> /dev/null; then
        log "uv is already installed ✓"
        return
    fi
    
    log "Installing uv (fast Python package manager)..."
    
    # Install uv using the official installer
    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        warn "Neither curl nor wget available. Falling back to pip installation method."
        return 1
    fi
    
    # Add uv to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    if command -v uv &> /dev/null; then
        log "uv installed successfully ✓"
        return 0
    else
        warn "uv installation may not be in PATH. Falling back to pip method."
        return 1
    fi
}

install_with_uv() {
    log "Installing ${PACKAGE_NAME} with uv..."
    
    # Install using uv tool install
    if uv tool install "$PACKAGE_NAME"; then
        log "${PACKAGE_NAME} installed successfully with uv ✓"
        return 0
    else
        warn "uv installation failed. Falling back to pip method."
        return 1
    fi
}

install_with_pipx() {
    if ! command -v pipx &> /dev/null; then
        log "Installing pipx..."
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
        
        # Add pipx to PATH for current session
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    if command -v pipx &> /dev/null; then
        log "Installing ${PACKAGE_NAME} with pipx..."
        if pipx install "$PACKAGE_NAME"; then
            log "${PACKAGE_NAME} installed successfully with pipx ✓"
            return 0
        else
            warn "pipx installation failed. Falling back to pip method."
            return 1
        fi
    else
        warn "pipx not available. Falling back to pip method."
        return 1
    fi
}

install_with_pip() {
    log "Installing ${PACKAGE_NAME} with pip (system-wide)..."
    
    # Try pip install with --user first
    if python3 -m pip install --user "$PACKAGE_NAME"; then
        log "${PACKAGE_NAME} installed successfully with pip --user ✓"
        
        # Ensure ~/.local/bin is in PATH
        local_bin="$HOME/.local/bin"
        if [[ ":$PATH:" != *":$local_bin:"* ]]; then
            warn "Adding $local_bin to PATH..."
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
            if [ -f "$HOME/.zshrc" ]; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
            fi
            export PATH="$local_bin:$PATH"
        fi
        
        return 0
    else
        error "Failed to install ${PACKAGE_NAME} with pip. Please check your Python setup."
    fi
}

verify_installation() {
    log "Verifying installation..."
    
    # Check if command is available
    if command -v "$COMMAND_NAME" &> /dev/null; then
        log "${COMMAND_NAME} command is available ✓"
        
        # Test the command
        if $COMMAND_NAME --help &> /dev/null; then
            log "Installation verified successfully! ✅"
            return 0
        else
            warn "Command exists but may have issues."
            return 1
        fi
    else
        warn "${COMMAND_NAME} command not found in PATH."
        warn "You may need to restart your terminal or run: source ~/.bashrc"
        return 1
    fi
}

print_usage() {
    echo
    echo -e "${GREEN}🎉 Installation complete!${NC}"
    echo
    echo -e "${BLUE}Quick Start:${NC}"
    echo -e "  ${CYAN}# Initialize your project${NC}"
    echo -e "  ${COMMAND_NAME} init"
    echo
    echo -e "  ${CYAN}# Search your codebase${NC}"
    echo -e "  ${COMMAND_NAME} search \"authentication logic\""
    echo
    echo -e "  ${CYAN}# Get help${NC}"
    echo -e "  ${COMMAND_NAME} --help"
    echo
    echo -e "${BLUE}Documentation:${NC} https://github.com/FSSCoding/Fss-Mini-Rag"
    echo
    
    if ! command -v "$COMMAND_NAME" &> /dev/null; then
        echo -e "${YELLOW}Note: If the command is not found, restart your terminal or run:${NC}"
        echo -e "  source ~/.bashrc"
        echo
    fi
}

main() {
    print_header
    
    # Check system requirements
    check_system
    
    # Try installation methods in order of preference
    if install_uv && install_with_uv; then
        log "Installation method: uv ✨"
    elif install_with_pipx; then
        log "Installation method: pipx 📦"
    else
        install_with_pip
        log "Installation method: pip 🐍"
    fi
    
    # Verify installation
    if verify_installation; then
        print_usage
    else
        warn "Installation completed but verification failed. The tool may still work."
        print_usage
    fi
}

# Run the main function
main "$@"