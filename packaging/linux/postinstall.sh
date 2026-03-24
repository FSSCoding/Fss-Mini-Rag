#!/bin/bash
# Post-installation script for FSS-Mini-RAG .deb package
# Creates a venv at /opt/fss-mini-rag and installs all dependencies

set -e

INSTALL_DIR="/opt/fss-mini-rag"
VENV_DIR="${INSTALL_DIR}/venv"
BIN_DIR="/usr/local/bin"

echo "Setting up FSS-Mini-RAG..."

# Create venv
python3 -m venv "${VENV_DIR}"

# Install the package and dependencies
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install fss-mini-rag

# Create symlinks for CLI commands
ln -sf "${VENV_DIR}/bin/rag-mini" "${BIN_DIR}/rag-mini"
ln -sf "${VENV_DIR}/bin/rag-mini-gui" "${BIN_DIR}/rag-mini-gui"

# Install desktop entry
if [ -d "/usr/share/applications" ]; then
    cp "${INSTALL_DIR}/share/fss-mini-rag.desktop" "/usr/share/applications/" 2>/dev/null || true
fi

# Install icon
if [ -d "/usr/share/icons/hicolor/256x256/apps" ]; then
    cp "${INSTALL_DIR}/share/fss-mini-rag.png" "/usr/share/icons/hicolor/256x256/apps/" 2>/dev/null || true
    gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true
fi

echo "FSS-Mini-RAG installed successfully!"
echo "  CLI: rag-mini --help"
echo "  GUI: rag-mini-gui"
