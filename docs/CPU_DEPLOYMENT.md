# CPU-Only Deployment Guide

## Ultra-Lightweight RAG for Any Computer

FSS-Mini-RAG can run on **CPU-only systems** with small local models. Perfect for laptops, older computers, or systems without GPUs.

## Quick Setup (CPU-Optimised)

### 1. Install FSS-Mini-RAG
```bash
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Set Up an Embedding Server

For CPU-only systems, [LM Studio](https://lmstudio.ai/) is recommended:
1. Download and install LM Studio
2. Load a small embedding model (e.g. MiniLM L6 v2 — 274MB)
3. Start the local server (default port 1234)

For LLM synthesis, load a small chat model (e.g. Qwen 0.6B or 1.7B).

### 3. Verify Setup
```bash
rag-mini info
rag-mini init
rag-mini search "test query"
```

## Performance Expectations

### Small Models on CPU:
- **Embedding (MiniLM)**: ~21 files/sec indexing
- **Query Expansion**: ~200-500ms per query
- **LLM Synthesis**: ~1-3 seconds depending on model size
- **Memory Usage**: ~1GB RAM total
- **Quality**: Excellent for RAG tasks

### Model Size Comparison:
| Model | Size | CPU Speed | Quality |
|-------|------|-----------|---------|
| Qwen 0.6B | 522MB | Fast | Excellent |
| Qwen 1.7B | 1.4GB | Medium | Excellent |
| Qwen 4B | 2.5GB | Slow | Excellent |

## CPU-Optimised Configuration

Edit `.mini-rag/config.yaml`:

```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  profile: precision            # MiniLM — fast and accurate

llm:
  provider: openai
  api_base: http://localhost:1234/v1
  synthesis_temperature: 0.2
  enable_synthesis: false       # Enable per-query with --synthesize

search:
  expand_queries: false         # Disable for speed
  default_top_k: 8
```

## System Requirements

### Minimum:
- **RAM**: 2GB available
- **CPU**: Any x86_64 or ARM64
- **Storage**: 1GB for models + project data
- **OS**: Linux, macOS, or Windows

### Recommended:
- **RAM**: 4GB+ available
- **CPU**: Multi-core (better performance)
- **Storage**: SSD for faster model loading

## Performance Tips

### For Maximum Speed:
1. **Disable query expansion** by default
2. **Use smaller result limits** (8 instead of 10)
3. **Use SSD storage** for model files
4. **Use MiniLM** for embeddings (faster than Nomic)

### For Maximum Quality:
1. **Enable query expansion** for important searches
2. **Use synthesis** for important queries (`--synthesize`)
3. **Use a larger LLM** (1.7B or 4B) in your server

## Example Usage

```bash
# Fast search (no expansion, no synthesis)
rag-mini search "authentication"

# Thorough search with AI synthesis
rag-mini search "error handling" --synthesize

# Desktop GUI (all features available)
rag-mini gui

# Web research
rag-mini research "topic" --engine duckduckgo
```

## Deployment Examples

### Raspberry Pi
```bash
# Install on Raspberry Pi OS (64-bit)
sudo apt update && sudo apt install python3-venv python3-pip
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For embeddings on Pi, use the ML fallback (`pip install sentence-transformers`) or point to a remote LM Studio instance on your network.

### Docker (CPU-Only)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt && pip install -e .

EXPOSE 7777
CMD ["rag-mini", "server"]
```

This makes FSS-Mini-RAG accessible on any hardware — no GPU required.
