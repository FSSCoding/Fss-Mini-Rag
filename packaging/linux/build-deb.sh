#!/bin/bash
# Build .deb package for FSS-Mini-RAG using fpm
# Requires: gem install fpm
#
# Usage: bash packaging/linux/build-deb.sh [version]
# Example: bash packaging/linux/build-deb.sh 2.3.0

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERSION="${1:-$(python3 -c "import mini_rag; print(mini_rag.__version__)")}"
OUTPUT_DIR="${PROJECT_ROOT}/dist"

echo "Building .deb package for FSS-Mini-RAG v${VERSION}..."

# Ensure dist directory exists
mkdir -p "${OUTPUT_DIR}"

# Build the wheel first
cd "${PROJECT_ROOT}"
python3 -m build --wheel

# Build .deb using fpm
fpm \
    -s python \
    -t deb \
    --name fss-mini-rag \
    --version "${VERSION}" \
    --description "Self-contained research and code search system" \
    --url "https://github.com/FSSCoding/Fss-Mini-Rag" \
    --maintainer "Brett Fox <brett@foxsoftwaresolutions.com.au>" \
    --license MIT \
    --depends python3 \
    --depends python3-tk \
    --depends python3-venv \
    --depends python3-pip \
    --after-install "${SCRIPT_DIR}/postinstall.sh" \
    --category science \
    --package "${OUTPUT_DIR}/fss-mini-rag_${VERSION}_amd64.deb" \
    setup.py

echo "Built: ${OUTPUT_DIR}/fss-mini-rag_${VERSION}_amd64.deb"
echo ""
echo "Install with:"
echo "  sudo dpkg -i ${OUTPUT_DIR}/fss-mini-rag_${VERSION}_amd64.deb"
echo "  sudo apt-get install -f  # Fix any missing dependencies"
