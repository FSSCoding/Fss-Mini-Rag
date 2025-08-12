# RAG System - Hybrid Mode Setup

This RAG system can operate in three modes:

## 🚀 **Mode 1: Ollama Only (Recommended - Lightweight)**
```bash
pip install -r requirements-light.txt
# Requires: ollama serve running with nomic-embed-text model
```
- **Size**: ~426MB total  
- **Performance**: Fastest (leverages Ollama)
- **Network**: Uses local Ollama server

## 🔄 **Mode 2: Hybrid (Best of Both Worlds)** 
```bash
pip install -r requirements-full.txt  
# Works with OR without Ollama
```
- **Size**: ~3GB total (includes ML fallback)
- **Resilience**: Automatic fallback if Ollama unavailable
- **Performance**: Ollama speed when available, ML fallback when needed

## 🛡️ **Mode 3: ML Only (Maximum Compatibility)**
```bash
pip install -r requirements-full.txt
# Disable Ollama fallback in config
```
- **Size**: ~3GB total
- **Compatibility**: Works anywhere, no external dependencies
- **Use case**: Offline environments, embedded systems

## 🔧 **Configuration**

Edit `.claude-rag/config.json` in your project:
```json
{
  "embedding": {
    "provider": "hybrid",           // "hybrid", "ollama", "fallback"  
    "model": "nomic-embed-text:latest",
    "base_url": "http://localhost:11434",
    "enable_fallback": true         // Set to false to disable ML fallback
  }
}
```

## 📊 **Status Check**
```python
from claude_rag.ollama_embeddings import OllamaEmbedder

embedder = OllamaEmbedder()
status = embedder.get_status()
print(f"Mode: {status['mode']}")
print(f"Ollama: {'✅' if status['ollama_available'] else '❌'}")
print(f"ML Fallback: {'✅' if status['fallback_available'] else '❌'}")
```

## 🎯 **Automatic Behavior**
1. **Try Ollama first** - fastest and most efficient
2. **Fall back to ML** - if Ollama unavailable and ML dependencies installed  
3. **Use hash fallback** - deterministic embeddings as last resort

The system automatically detects what's available and uses the best option!