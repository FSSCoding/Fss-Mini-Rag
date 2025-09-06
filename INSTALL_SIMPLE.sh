#!/bin/bash
# Ultra-simple FSS-Mini-RAG setup that just works
set -e

echo "🚀 FSS-Mini-RAG Simple Setup"

# Create symlink for global access
if [ ! -f /usr/local/bin/rag-mini ]; then
    sudo ln -sf "$(pwd)/rag-mini" /usr/local/bin/rag-mini
    echo "✅ Global rag-mini command created"
fi

# Just make sure we have the basic requirements
python3 -m pip install --user click rich lancedb pandas numpy pyarrow watchdog requests PyYAML rank-bm25 psutil

echo "✅ Done! Try: rag-mini --help"