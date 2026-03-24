# FSS-Mini-RAG Deployment Guide

> **Run semantic search anywhere — from laptops to edge devices**

## Platform Compatibility

| Platform | Status | AI Features | Installation | Notes |
|----------|--------|-------------|--------------|-------|
| **Linux** | Full | Full | `pip install -e .` | Primary platform |
| **Windows** | Full | Full | `install_windows.bat` | Desktop GUI works |
| **macOS** | Full | Full | `pip install -e .` | Works perfectly |
| **Raspberry Pi** | Good | Limited | `pip install -e .` | ARM64, use small models |
| **Docker** | Excellent | Full | Dockerfile | Any platform |

## Desktop Deployment

### Linux / macOS
```bash
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Launch GUI
rag-mini gui

# Or use CLI
rag-mini init
rag-mini search "query"
```

### Windows
```cmd
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .

rag-mini gui
```

Or use the interactive installer: `install_windows.bat`

## Server Deployment

### REST API Server
```bash
rag-mini server --port 7777
```

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt && pip install -e .

EXPOSE 7777
CMD ["rag-mini", "server"]
```

```bash
docker build -t fss-mini-rag .
docker run -it -v $(pwd)/projects:/projects fss-mini-rag

# Server mode
docker run -p 7777:7777 fss-mini-rag
```

### Cloud (AWS/GCP/Azure)
Same as Linux installation. Can serve multiple users via the REST API.

## Edge Device Deployment

### Raspberry Pi
```bash
# Raspberry Pi OS 64-bit
sudo apt update && sudo apt install python3-venv python3-pip python3-tk
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For embeddings, either:
- Install `sentence-transformers` for local ML fallback
- Point to a remote LM Studio instance on your network

**Performance expectations:**
- **Pi 4 (4GB+)**: Good performance, BM25 search works well
- **Pi 5**: Excellent performance

## Configuration by Use Case

### Lightweight (old hardware, limited RAM)
```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  profile: precision

search:
  default_top_k: 5
  expand_queries: false

chunking:
  max_size: 1500
```

### Balanced (laptop, desktop)
```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  profile: precision

search:
  default_top_k: 10
  enable_bm25: true
```

### Full Features (good hardware + LLM server)
```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  profile: conceptual

llm:
  provider: openai
  api_base: http://localhost:1234/v1
  enable_synthesis: true
  enable_thinking: true

search:
  expand_queries: true
  default_top_k: 10
```

### Cloud Hybrid (local search + cloud LLM)
```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1

llm:
  provider: openai
  api_base: https://openrouter.ai/api/v1
  api_key: "your-key"
  synthesis_model: "gpt-4o-mini"
```

## Troubleshooting by Platform

### Linux/macOS
- **Missing tkinter**: `sudo apt install python3-tk` (Ubuntu) or `brew install python-tk` (macOS)
- **Permission denied**: Check file permissions, use venv

### Windows
- **Long path errors**: Enable long paths in Windows settings
- **Tkinter missing**: Reinstall Python with tkinter option checked

### Raspberry Pi
- **Out of memory**: Use BM25 only, reduce chunk sizes
- **Slow indexing**: Expected — use smaller projects or remote embedding server

### Docker
- **No GUI**: Docker containers are headless — use CLI or server mode
- **Volume mounts**: Use `-v` to mount project directories
