#!/bin/bash
# Build AppImage for FSS-Mini-RAG
# Creates a portable Linux binary that includes Python and all dependencies.
#
# Requires: wget (for downloading appimagetool and Python AppImage)
# Usage: bash packaging/linux/build-appimage.sh [version]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERSION="${1:-$(cd "${PROJECT_ROOT}" && python3 -c "import mini_rag; print(mini_rag.__version__)")}"
BUILD_DIR="${PROJECT_ROOT}/build/appimage"
OUTPUT_DIR="${PROJECT_ROOT}/dist"
PYTHON_VERSION="3.11"
ARCH="x86_64"

echo "Building AppImage for FSS-Mini-RAG v${VERSION}..."

# Clean and create build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/AppDir" "${OUTPUT_DIR}"

cd "${BUILD_DIR}"

# Download appimagetool if not present
if ! command -v appimagetool &>/dev/null; then
    echo "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage" \
        -O appimagetool
    chmod +x appimagetool
    APPIMAGETOOL="./appimagetool"
else
    APPIMAGETOOL="appimagetool"
fi

# Download Python AppImage base
echo "Downloading Python ${PYTHON_VERSION} base..."
wget -q "https://github.com/niess/python-appimage/releases/download/python3.11/python3.11.14-cp311-cp311-manylinux_2_28_${ARCH}.AppImage" \
    -O python.AppImage
chmod +x python.AppImage

# Extract the Python AppImage
echo "Extracting Python base..."
./python.AppImage --appimage-extract
mv squashfs-root/* AppDir/
rm -rf squashfs-root

# Install FSS-Mini-RAG and dependencies into the AppImage
echo "Installing FSS-Mini-RAG and dependencies..."
PYTHON_BIN="$(ls AppDir/usr/bin/python3.* | head -1)"
"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install -r "${PROJECT_ROOT}/requirements.txt"
"${PYTHON_BIN}" -m pip install "${PROJECT_ROOT}"

# Create AppRun entry point
cat > AppDir/AppRun << 'APPRUN_EOF'
#!/bin/bash
SELF="$(readlink -f "$0")"
APPDIR="$(dirname "${SELF}")"
export PATH="${APPDIR}/usr/bin:${PATH}"
export PYTHONPATH="${APPDIR}/usr/lib/python3.11/site-packages:${PYTHONPATH}"
export LD_LIBRARY_PATH="${APPDIR}/usr/lib:${LD_LIBRARY_PATH}"
export PYTHONDONTWRITEBYTECODE=1

# Detect if launched as GUI or CLI
if [ "$1" = "--cli" ] || [ "$1" = "search" ] || [ "$1" = "init" ] || \
   [ "$1" = "research" ] || [ "$1" = "scrape" ] || [ "$1" = "status" ]; then
    exec "${APPDIR}/usr/bin/python3" -m mini_rag.cli "$@"
else
    # Default: launch GUI if no args, CLI if args provided
    if [ $# -eq 0 ]; then
        exec "${APPDIR}/usr/bin/python3" -m mini_rag.gui "$@"
    else
        exec "${APPDIR}/usr/bin/python3" -m mini_rag.cli "$@"
    fi
fi
APPRUN_EOF
chmod +x AppDir/AppRun

# Copy desktop file and icon
cp "${SCRIPT_DIR}/fss-mini-rag.desktop" AppDir/
cp "${PROJECT_ROOT}/assets/Fss_Mini_Rag.png" AppDir/fss-mini-rag.png

# Also place icon in standard location for desktop integration
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps/
cp "${PROJECT_ROOT}/assets/Fss_Mini_Rag.png" AppDir/usr/share/icons/hicolor/256x256/apps/fss-mini-rag.png

# Build the AppImage
echo "Packaging AppImage..."
ARCH="${ARCH}" "${APPIMAGETOOL}" AppDir "${OUTPUT_DIR}/FSS-Mini-RAG-${VERSION}-${ARCH}.AppImage"

echo ""
echo "Built: ${OUTPUT_DIR}/FSS-Mini-RAG-${VERSION}-${ARCH}.AppImage"
echo ""
echo "Usage:"
echo "  chmod +x FSS-Mini-RAG-${VERSION}-${ARCH}.AppImage"
echo "  ./FSS-Mini-RAG-${VERSION}-${ARCH}.AppImage              # Launch GUI"
echo "  ./FSS-Mini-RAG-${VERSION}-${ARCH}.AppImage search 'query' # CLI mode"
