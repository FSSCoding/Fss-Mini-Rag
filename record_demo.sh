#!/bin/bash
# Script to record the FSS-Mini-RAG demo as an animated GIF

set -e

echo "🎬 FSS-Mini-RAG Demo Recording Script"
echo "====================================="
echo

# Check if required tools are available
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ $1 is required but not installed."
        echo "   Install with: $2"
        exit 1
    fi
}

echo "🔧 Checking required tools..."
check_tool "asciinema" "pip install asciinema"
echo "✅ asciinema found"

# Optional: Check for gif conversion tools
if command -v "agg" &> /dev/null; then
    echo "✅ agg found (for gif conversion)"
    CONVERTER="agg"
elif command -v "svg-term" &> /dev/null; then
    echo "✅ svg-term found (for gif conversion)"
    CONVERTER="svg-term"
else
    echo "⚠️  No gif converter found. You can:"
    echo "   - Install agg: cargo install --git https://github.com/asciinema/agg"
    echo "   - Or use online converter at: https://dstein64.github.io/gifcast/"
    CONVERTER="none"
fi

echo

# Set up recording environment
export TERM=xterm-256color
export COLUMNS=80
export LINES=24

# Create recording directory
mkdir -p recordings
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RECORDING_FILE="recordings/fss-mini-rag-demo-${TIMESTAMP}.cast"
GIF_FILE="recordings/fss-mini-rag-demo-${TIMESTAMP}.gif"

echo "🎥 Starting recording..."
echo "   Output: $RECORDING_FILE"
echo

# Record the demo
asciinema rec "$RECORDING_FILE" \
    --title "FSS-Mini-RAG Demo" \
    --command "python3 create_demo_script.py" \
    --cols 80 \
    --rows 24

echo
echo "✅ Recording complete: $RECORDING_FILE"

# Convert to GIF if converter is available
if [ "$CONVERTER" = "agg" ]; then
    echo "🎨 Converting to GIF with agg..."
    agg "$RECORDING_FILE" "$GIF_FILE" \
        --font-size 14 \
        --line-height 1.2 \
        --cols 80 \
        --rows 24 \
        --theme monokai
    
    echo "✅ GIF created: $GIF_FILE"
    
    # Optimize GIF size
    if command -v "gifsicle" &> /dev/null; then
        echo "🗜️  Optimizing GIF size..."
        gifsicle -O3 --lossy=80 -o "${GIF_FILE}.optimized" "$GIF_FILE"
        mv "${GIF_FILE}.optimized" "$GIF_FILE"
        echo "✅ GIF optimized"
    fi
    
elif [ "$CONVERTER" = "svg-term" ]; then
    echo "🎨 Converting to SVG with svg-term..."
    svg-term --cast "$RECORDING_FILE" --out "${RECORDING_FILE%.cast}.svg" \
        --window --width 80 --height 24
    echo "✅ SVG created: ${RECORDING_FILE%.cast}.svg"
    echo "💡 Convert SVG to GIF online at: https://cloudconvert.com/svg-to-gif"
fi

echo
echo "🎉 Demo recording complete!"
echo
echo "📁 Files created:"
echo "   📼 Recording: $RECORDING_FILE"
if [ "$CONVERTER" != "none" ] && [ -f "$GIF_FILE" ]; then
    echo "   🎞️  GIF: $GIF_FILE"
fi
echo
echo "📋 Next steps:"
echo "   1. Review the recording: asciinema play $RECORDING_FILE"
if [ "$CONVERTER" = "none" ]; then
    echo "   2. Convert to GIF online: https://dstein64.github.io/gifcast/"
fi
echo "   3. Add to README.md after the mermaid diagram"
echo "   4. Optimize for web (target: <2MB for fast loading)"
echo
echo "🚀 Perfect demo for showcasing FSS-Mini-RAG!"