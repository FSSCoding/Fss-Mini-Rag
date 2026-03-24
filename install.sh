#!/bin/bash
# FSS-Mini-RAG Installer for Linux and macOS
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/FSSCoding/Fss-Mini-Rag/main/install.sh | bash
#
# Or download and run:
#   chmod +x install.sh && ./install.sh

set -e

APP_NAME="FSS-Mini-RAG"
REPO="FSSCoding/Fss-Mini-Rag"
INSTALL_DIR="${HOME}/.local/share/fss-mini-rag"
BIN_DIR="${HOME}/.local/bin"
MIN_PYTHON="3.8"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}$1${NC}"; }
ok()    { echo -e "${GREEN}$1${NC}"; }
warn()  { echo -e "${YELLOW}$1${NC}"; }
error() { echo -e "${RED}$1${NC}" >&2; }

# Find Python 3
find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            if [ -n "$ver" ]; then
                local major minor
                major=$(echo "$ver" | cut -d. -f1)
                minor=$(echo "$ver" | cut -d. -f2)
                if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
                    echo "$cmd"
                    return 0
                fi
            fi
        fi
    done
    return 1
}

# Check for tkinter
check_tkinter() {
    local python="$1"
    "$python" -c "import tkinter" 2>/dev/null
}

echo ""
echo "========================================"
echo "  ${APP_NAME} Installer"
echo "========================================"
echo ""

# Step 1: Find Python
info "Checking Python..."
PYTHON=$(find_python) || {
    error "Python ${MIN_PYTHON}+ not found!"
    echo ""
    echo "Install Python first:"
    if [ "$(uname)" = "Darwin" ]; then
        echo "  brew install python3"
        echo "  # Or download from https://python.org"
    else
        echo "  sudo apt install python3 python3-venv python3-tk  # Debian/Ubuntu"
        echo "  sudo dnf install python3 python3-tkinter          # Fedora"
        echo "  sudo pacman -S python python-tk                    # Arch"
    fi
    exit 1
}

PYTHON_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
ok "Found Python ${PYTHON_VER} (${PYTHON})"

# Step 2: Check tkinter
info "Checking tkinter (needed for GUI)..."
if check_tkinter "$PYTHON"; then
    ok "tkinter available"
else
    warn "tkinter not found — GUI won't work, CLI is fine"
    echo ""
    echo "To install tkinter:"
    if [ "$(uname)" = "Darwin" ]; then
        echo "  brew install python-tk"
    else
        echo "  sudo apt install python3-tk      # Debian/Ubuntu"
        echo "  sudo dnf install python3-tkinter  # Fedora"
        echo "  sudo pacman -S tk                  # Arch"
    fi
    echo ""
    read -rp "Continue without GUI support? [Y/n]: " choice
    if [ "${choice,,}" = "n" ]; then
        echo "Install tkinter first, then run this script again."
        exit 0
    fi
fi

# Step 3: Create install directory and venv
info "Installing to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}" "${BIN_DIR}"

if [ -d "${INSTALL_DIR}/venv" ]; then
    info "Existing installation found, upgrading..."
else
    info "Creating virtual environment..."
    "$PYTHON" -m venv "${INSTALL_DIR}/venv"
fi

# Step 4: Install FSS-Mini-RAG
info "Installing FSS-Mini-RAG (this may take 2-5 minutes)..."
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip --quiet

# Try PyPI first, fall back to GitHub
if "${INSTALL_DIR}/venv/bin/pip" install fss-mini-rag --quiet 2>/dev/null; then
    ok "Installed from PyPI"
else
    info "PyPI not available, installing from GitHub..."
    "${INSTALL_DIR}/venv/bin/pip" install "git+https://github.com/${REPO}.git" --quiet
    ok "Installed from GitHub"
fi

# Step 5: Create symlinks
info "Creating command links..."
ln -sf "${INSTALL_DIR}/venv/bin/rag-mini" "${BIN_DIR}/rag-mini"
ln -sf "${INSTALL_DIR}/venv/bin/rag-mini-gui" "${BIN_DIR}/rag-mini-gui"

# Step 6: Check PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qx "${BIN_DIR}"; then
    warn "${BIN_DIR} is not in your PATH"
    echo ""
    echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"\${HOME}/.local/bin:\${PATH}\""
    echo ""
    echo "Then restart your shell or run:"
    echo "  source ~/.bashrc  # or ~/.zshrc"
fi

# Step 7: Verify
info "Verifying installation..."
if "${BIN_DIR}/rag-mini" --help &>/dev/null; then
    ok "CLI verified"
else
    warn "CLI verification failed — check the output above for errors"
fi

# Step 8: Desktop entry (Linux only)
if [ "$(uname)" = "Linux" ] && [ -d "${HOME}/.local/share/applications" ]; then
    DESKTOP_FILE="${HOME}/.local/share/applications/fss-mini-rag.desktop"
    cat > "${DESKTOP_FILE}" << DESKTOP_EOF
[Desktop Entry]
Name=FSS-Mini-RAG
Comment=Self-contained research and code search system
Exec=${BIN_DIR}/rag-mini-gui
Icon=${INSTALL_DIR}/icon.png
Terminal=false
Type=Application
Categories=Utility;Development;Science;
DESKTOP_EOF

    # Copy icon if available
    if command -v curl &>/dev/null; then
        curl -fsSL "https://raw.githubusercontent.com/${REPO}/main/assets/Fss_Mini_Rag.png" \
            -o "${INSTALL_DIR}/icon.png" 2>/dev/null || true
    fi

    ok "Desktop entry created"
fi

echo ""
echo "========================================"
ok "  ${APP_NAME} installed!"
echo "========================================"
echo ""
echo "  CLI:  rag-mini --help"
echo "  GUI:  rag-mini-gui"
echo ""
echo "  Quick start:"
echo "    cd /path/to/your/project"
echo "    rag-mini init"
echo "    rag-mini search \"your query\""
echo ""
echo "  Uninstall:"
echo "    rm -rf ${INSTALL_DIR} ${BIN_DIR}/rag-mini ${BIN_DIR}/rag-mini-gui"
echo ""
