#!/bin/bash
# FSS-Mini-RAG Installation Script
# Interactive installer that sets up Python environment and dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print colored output
print_header() {
    echo -e "\n${CYAN}${BOLD}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    print_header "Checking Python Installation"
    
    # Check for python3 first, then python
    local python_cmd=""
    if command_exists python3; then
        python_cmd="python3"
    elif command_exists python; then
        python_cmd="python"
    else
        print_error "Python not found!"
        echo -e "${YELLOW}Please install Python 3.8+ from:${NC}"
        echo "  • https://python.org/downloads"
        echo "  • Or use your system package manager:"
        echo "    - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "    - macOS: brew install python"
        echo "    - Windows: Download from python.org"
        echo ""
        echo -e "${CYAN}After installing Python, run this script again.${NC}"
        exit 1
    fi
    
    # Check Python version
    local python_version=$($python_cmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    local major=$(echo $python_version | cut -d. -f1)
    local minor=$(echo $python_version | cut -d. -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        print_error "Python $python_version found, but 3.8+ required"
        echo "Please upgrade Python to 3.8 or higher."
        exit 1
    fi
    
    print_success "Found Python $python_version ($python_cmd)"
    export PYTHON_CMD="$python_cmd"
}

# Check if virtual environment exists
check_venv() {
    if [ -d "$SCRIPT_DIR/.venv" ]; then
        print_info "Virtual environment already exists at $SCRIPT_DIR/.venv"
        echo -n "Recreate it? (y/N): "
        read -r recreate
        if [[ $recreate =~ ^[Yy]$ ]]; then
            print_info "Removing existing virtual environment..."
            rm -rf "$SCRIPT_DIR/.venv"
            return 1  # Needs creation
        else
            return 0  # Use existing
        fi
    else
        return 1  # Needs creation
    fi
}

# Create virtual environment
create_venv() {
    print_header "Creating Python Virtual Environment"
    
    if ! check_venv; then
        print_info "Creating virtual environment at $SCRIPT_DIR/.venv"
        $PYTHON_CMD -m venv "$SCRIPT_DIR/.venv"
        
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment"
            echo "This might be because python3-venv is not installed."
            echo "Try: sudo apt install python3-venv (Ubuntu/Debian)"
            exit 1
        fi
        
        print_success "Virtual environment created"
    else
        print_success "Using existing virtual environment"
    fi
    
    # Activate virtual environment
    source "$SCRIPT_DIR/.venv/bin/activate"
    print_success "Virtual environment activated"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
}

# Check Ollama installation
check_ollama() {
    print_header "Checking Ollama (AI Model Server)"
    
    if command_exists ollama; then
        print_success "Ollama is installed"
        
        # Check if Ollama is running
        if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
            print_success "Ollama server is running"
            return 0
        else
            print_warning "Ollama is installed but not running"
            echo -n "Start Ollama now? (Y/n): "
            read -r start_ollama
            if [[ ! $start_ollama =~ ^[Nn]$ ]]; then
                print_info "Starting Ollama server..."
                ollama serve &
                sleep 3
                if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
                    print_success "Ollama server started"
                    return 0
                else
                    print_warning "Failed to start Ollama automatically"
                    echo "Please start Ollama manually: ollama serve"
                    return 1
                fi
            else
                return 1
            fi
        fi
    else
        print_warning "Ollama not found"
        echo ""
        echo -e "${CYAN}Ollama provides the best embedding quality and performance.${NC}"
        echo -e "${YELLOW}To install Ollama:${NC}"
        echo "  1. Visit: https://ollama.ai/download"
        echo "  2. Download and install for your system"
        echo "  3. Run: ollama serve"
        echo "  4. Re-run this installer"
        echo ""
        echo -e "${BLUE}Alternative: Use ML fallback (requires more disk space)${NC}"
        echo ""
        echo -n "Continue without Ollama? (y/N): "
        read -r continue_without
        if [[ $continue_without =~ ^[Yy]$ ]]; then
            return 1
        else
            print_info "Install Ollama first, then re-run this script"
            exit 0
        fi
    fi
}

# Setup Ollama model based on configuration
setup_ollama_model() {
    # Skip if custom config says to skip
    if [ "$CUSTOM_OLLAMA_MODEL" = "skip" ]; then
        print_info "Skipping Ollama model setup (custom configuration)"
        return 1
    fi
    
    print_header "Ollama Model Setup"
    
    print_info "Checking available Ollama models..."
    
    # Get list of installed models
    local available_models=$(ollama list 2>/dev/null | grep -v "NAME" | awk '{print $1}' | grep -v "^$")
    
    if echo "$available_models" | grep -q "nomic-embed-text"; then
        print_success "nomic-embed-text model already installed"
        local model_info=$(ollama list | grep "nomic-embed-text")
        echo -e "${BLUE}• $model_info${NC}"
        return 0
    fi
    
    if [ -n "$available_models" ]; then
        print_info "Other Ollama models found:"
        echo "$available_models" | sed 's/^/  • /'
        echo ""
    fi
    
    # For custom installations, we already asked. For auto installations, ask now
    local should_download="$CUSTOM_OLLAMA_MODEL"
    if [ -z "$should_download" ] || [ "$should_download" = "auto" ]; then
        echo -e "${CYAN}Model: nomic-embed-text (~270MB)${NC}"
        echo "  • Purpose: High-quality semantic embeddings"
        echo "  • Alternative: System will use ML/hash fallbacks"
        echo ""
        echo -n "Download model? [y/N]: "
        read -r download_model
        should_download=$([ "$download_model" = "y" ] && echo "download" || echo "skip")
    fi
    
    if [ "$should_download" != "download" ]; then
        print_info "Skipping model download"
        echo "  Install later: ollama pull nomic-embed-text"
        return 1
    fi
    
    # Test connectivity and download
    print_info "Testing Ollama connection..."
    if ! curl -s --connect-timeout 5 http://localhost:11434/api/version >/dev/null; then
        print_error "Cannot connect to Ollama server"
        echo "  Ensure Ollama is running: ollama serve"
        echo "  Then install manually: ollama pull nomic-embed-text"
        return 1
    fi
    
    print_info "Downloading nomic-embed-text..."
    echo -e "${BLUE}  Press Ctrl+C to cancel if needed${NC}"
    
    if ollama pull nomic-embed-text; then
        print_success "Model ready"
        return 0
    else
        print_warning "Download failed - will use fallback embeddings"
        return 1
    fi
}

# Get installation preferences with smart defaults
get_installation_preferences() {
    print_header "Installation Configuration"
    
    echo -e "${CYAN}FSS-Mini-RAG can run with different embedding backends:${NC}"
    echo ""
    echo -e "${GREEN}• Ollama${NC} (recommended) - Best quality, local AI server"
    echo -e "${YELLOW}• ML Fallback${NC} - Offline transformers, larger but always works"  
    echo -e "${BLUE}• Hash-based${NC} - Lightweight fallback, basic similarity"
    echo ""
    
    # Smart recommendation based on detected setup
    local recommended=""
    if [ "$ollama_available" = true ]; then
        recommended="light (Ollama detected)"
        echo -e "${GREEN}✓ Ollama detected - light installation recommended${NC}"
    else
        recommended="full (no Ollama)"
        echo -e "${YELLOW}⚠ No Ollama - full installation recommended for better quality${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}Installation options:${NC}"
    echo -e "${GREEN}L) Light${NC} - Ollama + basic deps (~50MB)"
    echo -e "${YELLOW}F) Full${NC}  - Light + ML fallback (~2-3GB)"
    echo -e "${BLUE}C) Custom${NC} - Configure individual components"
    echo ""
    
    while true; do
        echo -n "Choose [L/F/C] or Enter for recommended ($recommended): "
        read -r choice
        
        # Default to recommendation if empty
        if [ -z "$choice" ]; then
            if [ "$ollama_available" = true ]; then
                choice="L"
            else
                choice="F"  
            fi
        fi
        
        case "${choice^^}" in
            L)
                export INSTALL_TYPE="light"
                echo -e "${GREEN}Selected: Light installation${NC}"
                break
                ;;
            F)
                export INSTALL_TYPE="full"
                echo -e "${YELLOW}Selected: Full installation${NC}"
                break
                ;;
            C)
                configure_custom_installation
                break
                ;;
            *)
                print_warning "Please choose L, F, C, or press Enter for default"
                ;;
        esac
    done
}

# Custom installation configuration
configure_custom_installation() {
    print_header "Custom Installation Configuration"
    
    echo -e "${CYAN}Configure each component individually:${NC}"
    echo ""
    
    # Base dependencies (always required)
    echo -e "${GREEN}✓ Base dependencies${NC} (lancedb, pandas, numpy, etc.) - Required"
    
    # Ollama model
    local ollama_model="skip"
    if [ "$ollama_available" = true ]; then
        echo ""
        echo -e "${BOLD}Ollama embedding model:${NC}"
        echo "  • nomic-embed-text (~270MB) - Best quality embeddings"
        echo -n "Download Ollama model? [y/N]: "
        read -r download_ollama
        if [[ $download_ollama =~ ^[Yy]$ ]]; then
            ollama_model="download"
        fi
    fi
    
    # ML dependencies
    echo ""
    echo -e "${BOLD}ML fallback system:${NC}"
    echo "  • PyTorch + transformers (~2-3GB) - Works without Ollama"
    echo "  • Useful for: Offline use, server deployments, CI/CD"
    echo -n "Include ML dependencies? [y/N]: "
    read -r include_ml
    
    # Pre-download models
    local predownload_ml="skip"
    if [[ $include_ml =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BOLD}Pre-download ML models:${NC}"
        echo "  • sentence-transformers model (~80MB)"
        echo "  • Skip: Models download automatically when first used"
        echo -n "Pre-download now? [y/N]: "
        read -r predownload
        if [[ $predownload =~ ^[Yy]$ ]]; then
            predownload_ml="download"
        fi
    fi
    
    # Set configuration
    if [[ $include_ml =~ ^[Yy]$ ]]; then
        export INSTALL_TYPE="full"
    else
        export INSTALL_TYPE="light"
    fi
    export CUSTOM_OLLAMA_MODEL="$ollama_model"
    export CUSTOM_ML_PREDOWNLOAD="$predownload_ml"
    
    echo ""
    echo -e "${GREEN}Custom configuration set:${NC}"
    echo "  • Base deps: ✓"
    echo "  • Ollama model: $ollama_model"
    echo "  • ML deps: $([ "$INSTALL_TYPE" = "full" ] && echo "✓" || echo "skip")"
    echo "  • ML predownload: $predownload_ml"
}

# Install dependencies with progress
install_dependencies() {
    print_header "Installing Python Dependencies"
    
    if [ "$INSTALL_TYPE" = "light" ]; then
        print_info "Installing core dependencies (~50MB)..."
        echo -e "${BLUE}  Installing: lancedb, pandas, numpy, PyYAML, etc.${NC}"
        
        if pip install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
            print_success "Dependencies installed"
        else
            print_error "Failed to install dependencies"
            echo "Try: pip install -r requirements.txt"
            exit 1
        fi
    else
        print_info "Installing full dependencies (~2-3GB)..."
        echo -e "${YELLOW}  This includes PyTorch and transformers - will take several minutes${NC}"
        echo -e "${BLUE}  Progress will be shown...${NC}"
        
        if pip install -r "$SCRIPT_DIR/requirements-full.txt"; then
            print_success "All dependencies installed"
        else
            print_error "Failed to install dependencies"
            echo "Try: pip install -r requirements-full.txt"
            exit 1
        fi
    fi
    
    print_info "Verifying installation..."
    if python3 -c "import lancedb, pandas, numpy" 2>/dev/null; then
        print_success "Core packages verified"
    else
        print_error "Package verification failed"
        exit 1
    fi
}

# Setup ML models based on configuration  
setup_ml_models() {
    if [ "$INSTALL_TYPE" != "full" ]; then
        return 0
    fi
    
    # Check if we should pre-download
    local should_predownload="$CUSTOM_ML_PREDOWNLOAD"
    if [ -z "$should_predownload" ] || [ "$should_predownload" = "auto" ]; then
        print_header "ML Model Pre-download"
        echo -e "${CYAN}Pre-download ML models for offline use?${NC}"
        echo ""
        echo -e "${BLUE}Model: sentence-transformers/all-MiniLM-L6-v2 (~80MB)${NC}"
        echo "  • Purpose: Offline fallback when Ollama unavailable"
        echo "  • If skipped: Auto-downloads when first needed"
        echo ""
        echo -n "Pre-download now? [y/N]: "
        read -r download_ml
        should_predownload=$([ "$download_ml" = "y" ] && echo "download" || echo "skip")
    fi
    
    if [ "$should_predownload" != "download" ]; then
        print_info "Skipping ML model pre-download"
        echo "  Models will download automatically when first used"
        return 0
    fi
    
    print_info "Pre-downloading ML model..."
    echo -e "${BLUE}  This ensures offline availability${NC}"
    
    # Create a simple progress indicator
    python3 -c "
import sys
import threading
import time

# Progress spinner
def spinner():
    chars = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while not spinner.stop:
        for char in chars:
            if spinner.stop:
                break
            sys.stdout.write(f'\r  {char} Downloading model...')
            sys.stdout.flush()
            time.sleep(0.1)

try:
    spinner.stop = False
    spinner_thread = threading.Thread(target=spinner)
    spinner_thread.start()
    
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    spinner.stop = True
    spinner_thread.join()
    print('\r✅ ML model ready for offline use                ')
    
except Exception as e:
    spinner.stop = True
    spinner_thread.join()
    print(f'\r❌ Download failed: {e}                ')
    sys.exit(1)
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "ML models ready"
    else
        print_warning "Pre-download failed"
        echo "  Models will auto-download when first needed"
    fi
}

# Test installation
test_installation() {
    print_header "Testing Installation"
    
    print_info "Testing basic functionality..."
    
    # Test import
    if python3 -c "from mini_rag import CodeEmbedder, ProjectIndexer, CodeSearcher; print('✅ Import successful')" 2>/dev/null; then
        print_success "Python imports working"
    else
        print_error "Import test failed"
        return 1
    fi
    
    # Test embedding system
    if python3 -c "
from mini_rag import CodeEmbedder
embedder = CodeEmbedder()
info = embedder.get_embedding_info()
print(f'✅ Embedding system: {info[\"method\"]}')
    " 2>/dev/null; then
        print_success "Embedding system working"
    else
        print_warning "Embedding test failed, but system should still work"
    fi
    
    return 0
}

# Show completion message
show_completion() {
    print_header "Installation Complete!"
    
    echo -e "${GREEN}${BOLD}FSS-Mini-RAG is now installed!${NC}"
    echo ""
    echo -e "${CYAN}Quick Start Options:${NC}"
    echo ""
    echo -e "${GREEN}🎯 TUI (Beginner-Friendly):${NC}"
    echo "     ./rag-tui"
    echo "     # Interactive interface with guided setup"
    echo ""
    echo -e "${BLUE}💻 CLI (Advanced):${NC}"
    echo "     ./rag-mini index /path/to/project"
    echo "     ./rag-mini search /path/to/project \"query\""
    echo "     ./rag-mini status /path/to/project"
    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    echo "  • README.md - Complete technical documentation"
    echo "  • docs/GETTING_STARTED.md - Step-by-step guide"
    echo "  • examples/ - Usage examples and sample configs"
    echo ""
    
    if [ "$INSTALL_TYPE" = "light" ] && ! command_exists ollama; then
        echo -e "${YELLOW}Note: You chose light installation but Ollama isn't running.${NC}"
        echo "The system will use hash-based embeddings (lower quality)."
        echo "For best results, install Ollama from https://ollama.ai/download"
        echo ""
    fi
    
    # Ask if they want to run a test
    echo -n "Would you like to run a quick test now? (Y/n): "
    read -r run_test
    if [[ ! $run_test =~ ^[Nn]$ ]]; then
        run_quick_test
    fi
}

# Run quick test
run_quick_test() {
    print_header "Quick Test"
    
    print_info "Testing on this project directory..."
    echo "This will index the FSS-Mini-RAG system itself as a test."
    echo ""
    
    # Index this project
    if ./rag-mini index "$SCRIPT_DIR"; then
        print_success "Indexing completed"
        
        # Try a search
        echo ""
        print_info "Testing search functionality..."
        ./rag-mini search "$SCRIPT_DIR" "embedding system" --limit 3
        
        echo ""
        print_success "Test completed successfully!"
        echo -e "${CYAN}You can now use FSS-Mini-RAG on your own projects.${NC}"
    else
        print_error "Test failed"
        echo "Check the error messages above for troubleshooting."
    fi
}

# Main installation flow
main() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════╗"
    echo "║        FSS-Mini-RAG Installer        ║"
    echo "║   Fast Semantic Search for Code      ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${BLUE}Adaptive installation process:${NC}"
    echo "  • Python environment setup"
    echo "  • Smart configuration based on your system"  
    echo "  • Optional AI model downloads (with consent)"
    echo "  • Testing and verification"
    echo ""
    echo -e "${CYAN}Note: You'll be asked before downloading any models${NC}"
    echo ""
    
    echo -n "Begin installation? [Y/n]: "
    read -r continue_install
    if [[ $continue_install =~ ^[Nn]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    # Run installation steps
    check_python
    create_venv
    
    # Check Ollama availability
    ollama_available=false
    if check_ollama; then
        ollama_available=true
    fi
    
    # Get installation preferences with smart recommendations
    get_installation_preferences
    
    # Install dependencies
    install_dependencies
    
    # Setup models based on configuration
    if [ "$ollama_available" = true ]; then
        setup_ollama_model
    fi
    setup_ml_models
    
    if test_installation; then
        show_completion
    else
        print_error "Installation test failed"
        echo "Please check error messages and try again."
        exit 1
    fi
}

# Run main function
main "$@"