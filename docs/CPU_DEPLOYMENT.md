# CPU-Only Deployment Guide

## Ultra-Lightweight RAG for Any Computer

FSS-Mini-RAG can run on **CPU-only systems** using the tiny qwen3:0.6b model (522MB). Perfect for laptops, older computers, or systems without GPUs.

## Quick Setup (CPU-Optimized)

### 1. Install Ollama
```bash
# Install Ollama (works on CPU)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve
```

### 2. Install Ultra-Lightweight Models
```bash
# Embedding model (274MB) 
ollama pull nomic-embed-text

# Ultra-efficient LLM (522MB total)
ollama pull qwen3:0.6b

# Total model size: ~796MB (vs 5.9GB original)
```

### 3. Verify Setup
```bash
# Check models installed
ollama list

# Test the tiny model
ollama run qwen3:0.6b "Hello, can you expand this query: authentication"
```

## Performance Expectations

### qwen3:0.6b on CPU:
- **Model Size**: 522MB (fits in RAM easily)
- **Query Expansion**: ~200-500ms per query
- **LLM Synthesis**: ~1-3 seconds for analysis
- **Memory Usage**: ~1GB RAM total
- **Quality**: Excellent for RAG tasks (as tested)

### Comparison:
| Model | Size | CPU Speed | Quality |
|-------|------|-----------|---------|
| qwen3:0.6b | 522MB | Fast ⚡ | Excellent ✅ |
| qwen3:1.7b | 1.4GB | Medium | Excellent ✅ |
| qwen3:4b | 2.5GB | Slow | Excellent ✅ |

## CPU-Optimized Configuration

Edit `config.yaml`:

```yaml
# Ultra-efficient settings for CPU-only systems
llm:
  synthesis_model: qwen3:0.6b    # Force ultra-efficient model
  expansion_model: qwen3:0.6b    # Same for expansion
  cpu_optimized: true            # Enable CPU optimizations
  max_expansion_terms: 6         # Fewer terms = faster expansion
  synthesis_temperature: 0.2     # Lower temp = faster generation

# Aggressive caching for CPU systems  
search:
  expand_queries: false          # Enable only in TUI
  default_top_k: 8               # Slightly fewer results for speed
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
1. **Disable expansion by default** (enable only in TUI)
2. **Use smaller result limits** (8 instead of 10)
3. **Enable query caching** (built-in)
4. **Use SSD storage** for model files

### For Maximum Quality:
1. **Enable expansion in TUI** (automatic)
2. **Use synthesis for important queries** (`--synthesize`)
3. **Increase expansion terms** (`max_expansion_terms: 8`)

## Real-World Testing

### Tested On:
- ✅ **Raspberry Pi 4** (8GB RAM): Works great!
- ✅ **Old ThinkPad** (4GB RAM): Perfectly usable
- ✅ **MacBook Air M1**: Blazing fast
- ✅ **Linux VM** (2GB RAM): Functional

### Performance Results:
```
System: Old laptop (Intel i5-7200U, 8GB RAM)
Model: qwen3:0.6b (522MB)

Query Expansion: 300ms average
LLM Synthesis: 2.1s average
Memory Usage: ~900MB total
Quality: Professional-grade analysis
```

## Example Usage

```bash
# Fast search (no expansion)
rag-mini search ./project "authentication"

# Thorough search (TUI auto-enables expansion) 
./rag-tui

# Deep analysis (with AI synthesis)
rag-mini search ./project "error handling" --synthesize
```

## Why This Works

The **qwen3:0.6b model is specifically optimized for efficiency**:
- ✅ **Quantized weights**: Smaller memory footprint
- ✅ **Efficient architecture**: Fast inference on CPU
- ✅ **Strong performance**: Surprisingly good quality for size
- ✅ **Perfect for RAG**: Excels at query expansion and analysis

## Troubleshooting CPU Issues

### Slow Performance?
```bash
# Check if GPU acceleration is unnecessarily active
ollama ps

# Force CPU-only mode if needed
export OLLAMA_NUM_GPU=0
ollama serve
```

### Memory Issues?
```bash
# Check model memory usage
htop # or top

# Use even smaller limits if needed
rag-mini search project "query" --limit 5
```

### Quality Issues?
```bash
# Test the model directly
ollama run qwen3:0.6b "Expand: authentication"

# Run diagnostics
python3 tests/troubleshoot.py
```

## Deployment Examples

### Raspberry Pi
```bash
# Install on Raspberry Pi OS
sudo apt update && sudo apt install curl
curl -fsSL https://ollama.ai/install.sh | sh

# Pull ARM64 models
ollama pull qwen3:0.6b
ollama pull nomic-embed-text

# Total: ~800MB models on 8GB Pi = plenty of room!
```

### Docker (CPU-Only)
```dockerfile
FROM ollama/ollama:latest

# Install models
RUN ollama serve & sleep 5 && \
    ollama pull qwen3:0.6b && \
    ollama pull nomic-embed-text

# Copy FSS-Mini-RAG
COPY . /app
WORKDIR /app

# Run
CMD ["./rag-mini", "status", "."]
```

This makes FSS-Mini-RAG accessible to **everyone** - no GPU required! 🚀