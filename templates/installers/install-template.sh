#!/bin/bash
# Reusable one-line installer template for Python CLI tools
# Copy this file and customize the marked sections

set -e

# CUSTOMIZE: Your package details
PACKAGE_NAME="your-package-name"
CLI_COMMAND="your-cli-command"
GITHUB_REPO="YOUR-USERNAME/YOUR-REPO"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}🚀 ${PACKAGE_NAME} Installer${NC}"
    echo "=================================================="
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if package is already installed and working
check_existing_installation() {
    if command_exists "$CLI_COMMAND"; then
        print_info "Found existing $CLI_COMMAND installation"
        if $CLI_COMMAND --version >/dev/null 2>&1 || $CLI_COMMAND --help >/dev/null 2>&1; then
            print_success "$PACKAGE_NAME is already installed and working!"
            print_info "Run '$CLI_COMMAND --help' to get started"
            exit 0
        else
            print_warning "Existing installation appears broken, proceeding with reinstallation"
        fi
    fi
}

# Install with uv (fastest method)
install_with_uv() {
    print_info "Attempting installation with uv (fastest method)..."
    
    if ! command_exists uv; then
        print_info "Installing uv package manager..."
        if curl -LsSf https://astral.sh/uv/install.sh | sh; then
            export PATH="$HOME/.cargo/bin:$PATH"
            print_success "uv installed successfully"
        else
            print_warning "Failed to install uv, trying next method..."
            return 1
        fi
    fi
    
    if uv tool install "$PACKAGE_NAME"; then
        print_success "Installed $PACKAGE_NAME with uv"
        print_info "uv tools are typically available in ~/.local/bin"
        return 0
    else
        print_warning "uv installation failed, trying next method..."
        return 1
    fi
}

# Install with pipx (isolated environment)
install_with_pipx() {
    print_info "Attempting installation with pipx (isolated environment)..."
    
    if ! command_exists pipx; then
        print_info "Installing pipx..."
        if command_exists pip3; then
            pip3 install --user pipx
        elif command_exists pip; then
            pip install --user pipx
        else
            print_warning "No pip found, trying next method..."
            return 1
        fi
        
        # Add pipx to PATH
        export PATH="$HOME/.local/bin:$PATH"
        
        if command_exists pipx; then
            pipx ensurepath
            print_success "pipx installed successfully"
        else
            print_warning "pipx installation failed, trying next method..."
            return 1
        fi
    fi
    
    if pipx install "$PACKAGE_NAME"; then
        print_success "Installed $PACKAGE_NAME with pipx"
        return 0
    else
        print_warning "pipx installation failed, trying next method..."
        return 1
    fi
}

# Install with pip (fallback method)
install_with_pip() {
    print_info "Attempting installation with pip (user install)..."
    
    local pip_cmd=""
    if command_exists pip3; then
        pip_cmd="pip3"
    elif command_exists pip; then
        pip_cmd="pip"
    else
        print_error "No pip found. Please install Python and pip first."
        return 1
    fi
    
    if $pip_cmd install --user "$PACKAGE_NAME"; then
        print_success "Installed $PACKAGE_NAME with pip"
        print_info "Make sure ~/.local/bin is in your PATH"
        return 0
    else
        print_error "pip installation failed"
        return 1
    fi
}

# Add to PATH if needed
setup_path() {
    local paths_to_check=(
        "$HOME/.cargo/bin"      # uv
        "$HOME/.local/bin"      # pipx, pip --user
    )
    
    local paths_added=0
    for path_dir in "${paths_to_check[@]}"; do
        if [[ -d "$path_dir" ]] && [[ ":$PATH:" != *":$path_dir:"* ]]; then
            export PATH="$path_dir:$PATH"
            paths_added=1
        fi
    done
    
    if [[ $paths_added -eq 1 ]]; then
        print_info "Added tool directories to PATH for this session"
    fi
}

# Verify installation
verify_installation() {
    setup_path
    
    if command_exists "$CLI_COMMAND"; then
        print_success "Installation successful!"
        print_info "Testing $CLI_COMMAND..."
        
        if $CLI_COMMAND --version >/dev/null 2>&1 || $CLI_COMMAND --help >/dev/null 2>&1; then
            print_success "$CLI_COMMAND is working correctly!"
            print_info ""
            print_info "🎉 $PACKAGE_NAME is now installed!"
            print_info "Run '$CLI_COMMAND --help' to get started"
            
            # CUSTOMIZE: Add usage examples specific to your tool
            print_info ""
            print_info "Quick start examples:"
            print_info "  $CLI_COMMAND --help        # Show help"
            print_info "  $CLI_COMMAND init          # Initialize (if applicable)"
            print_info "  $CLI_COMMAND status        # Check status (if applicable)"
            
            return 0
        else
            print_warning "$CLI_COMMAND installed but not working properly"
            return 1
        fi
    else
        print_error "Installation completed but $CLI_COMMAND not found in PATH"
        print_info "You may need to restart your terminal or run:"
        print_info "  export PATH=\"\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH\""
        return 1
    fi
}

# Main installation function
main() {
    print_header
    print_info "This script will install $PACKAGE_NAME using the best available method"
    print_info "Trying: uv (fastest) → pipx (isolated) → pip (fallback)"
    echo ""
    
    check_existing_installation
    
    # Try installation methods in order of preference
    if install_with_uv || install_with_pipx || install_with_pip; then
        echo ""
        verify_installation
    else
        echo ""
        print_error "All installation methods failed!"
        print_info ""
        print_info "Manual installation options:"
        print_info "1. Install Python 3.8+ and pip, then run:"
        print_info "   pip install --user $PACKAGE_NAME"
        print_info ""
        print_info "2. Visit our GitHub for more options:"
        print_info "   https://github.com/$GITHUB_REPO"
        exit 1
    fi
}

# Run the installer
main "$@"