# RAG System - Hybrid Mode Setup

This RAG system can operate in three modes:

## 🚀 **Mode 1: Standard Installation (Recommended)**
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt  # 2-8 minutes
.venv/bin/python -m pip install .                    # ~1 minute
source .venv/bin/activate
```
- **Size**: ~123MB total (LanceDB 36MB + PyArrow 43MB + PyLance 44MB)  
- **Performance**: Excellent hybrid embedding system
- **Timing**: 2-3 minutes fast internet, 5-10 minutes slow internet

## 🔄 **Mode 2: Light Installation (Alternative)** 
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-light.txt  # If available
.venv/bin/python -m pip install .
source .venv/bin/activate
```
- **Size**: ~426MB total (includes basic dependencies only)
- **Requires**: Ollama server running locally
- **Use case**: Minimal installations, edge devices

## 🛡️ **Mode 3: Full Installation (Maximum Features)**
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-full.txt  # If available
.venv/bin/python -m pip install .
source .venv/bin/activate
```
- **Size**: ~3GB total (includes all ML fallbacks)
- **Compatibility**: Works anywhere, all features enabled  
- **Use case**: Offline environments, complete feature set

## 🔧 **Configuration**

Edit `.mini-rag/config.json` in your project:
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
from mini_rag.ollama_embeddings import OllamaEmbedder

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