# FSS-Mini-RAG Deployment Guide

> **Run semantic search anywhere - from smartphones to edge devices**  
> *Complete guide to deploying FSS-Mini-RAG on every platform imaginable*

## Platform Compatibility Matrix

| Platform | Status | AI Features | Installation | Notes |
|----------|--------|-------------|--------------|-------|
| **Linux** | ✅ Full | ✅ Full | `./install_mini_rag.sh` | Primary platform |
| **Windows** | ✅ Full | ✅ Full | `install_windows.bat` | Desktop shortcuts |
| **macOS** | ✅ Full | ✅ Full | `./install_mini_rag.sh` | Works perfectly |
| **Raspberry Pi** | ✅ Excellent | ✅ AI ready | `./install_mini_rag.sh` | ARM64 optimized |
| **Android (Termux)** | ✅ Good | 🟡 Limited | Manual install | Terminal interface |
| **iOS (a-Shell)** | 🟡 Limited | ❌ Text only | Manual install | Sandbox limitations |
| **Docker** | ✅ Excellent | ✅ Full | Dockerfile | Any platform |

## Desktop & Server Deployment

### 🐧 **Linux** (Primary Platform)
```bash
# Full installation with AI features
./install_mini_rag.sh

# What you get:
# ✅ Desktop shortcuts (.desktop files)
# ✅ Application menu integration  
# ✅ Full AI model downloads
# ✅ Complete terminal interface
```

### 🪟 **Windows** (Fully Supported)
```cmd
# Full installation with desktop integration
install_windows.bat

# What you get:
# ✅ Desktop shortcuts (.lnk files)
# ✅ Start Menu entries
# ✅ Full AI model downloads  
# ✅ Beautiful terminal interface
```

### 🍎 **macOS** (Excellent Support)
```bash
# Same as Linux - works perfectly
./install_mini_rag.sh

# Additional macOS optimizations:
brew install python3           # If needed
brew install ollama           # For AI features
```

**macOS-specific features:**
- Automatic path detection for common project locations
- Integration with Spotlight search locations
- Support for `.app` bundle creation (advanced)

## Edge Device Deployment

### 🥧 **Raspberry Pi** (Recommended Edge Platform)

**Perfect for:**
- Home lab semantic search server
- Portable development environment  
- IoT project documentation search
- Offline code search station

**Installation:**
```bash
# On Raspberry Pi OS (64-bit recommended)
sudo apt update && sudo apt upgrade
./install_mini_rag.sh

# The installer automatically detects ARM and optimizes:
# ✅ Suggests lightweight models (qwen3:0.6b)
# ✅ Reduces memory usage
# ✅ Enables efficient chunking
```

**Raspberry Pi optimized config:**
```yaml
# Automatically generated for Pi
embedding:
  preferred_method: ollama
  ollama_model: nomic-embed-text  # 270MB - perfect for Pi

llm:
  synthesis_model: qwen3:0.6b     # 500MB - fast on Pi 4+
  context_window: 4096            # Conservative memory use
  cpu_optimized: true

chunking:
  max_size: 1500                  # Smaller chunks for efficiency
```

**Performance expectations:**
- **Pi 4 (4GB)**: Excellent performance, full AI features
- **Pi 4 (2GB)**: Good performance, text-only or small models
- **Pi 5**: Outstanding performance, handles large models
- **Pi Zero**: Text-only search (hash-based embeddings)

### 🔧 **Other Edge Devices**

**NVIDIA Jetson Series:**
- Overkill performance for this use case
- Can run largest models with GPU acceleration
- Perfect for AI-heavy development workstations

**Intel NUC / Mini PCs:**
- Excellent performance
- Full desktop experience
- Can serve multiple users simultaneously

**Orange Pi / Rock Pi:**
- Similar to Raspberry Pi
- Same installation process
- May need manual Ollama compilation

## Mobile Deployment

### 📱 **Android (Recommended: Termux)**

**Installation in Termux:**
```bash
# Install Termux from F-Droid (not Play Store)
# In Termux:
pkg update && pkg upgrade
pkg install python python-pip git
pip install --upgrade pip

# Clone and install FSS-Mini-RAG
git clone https://github.com/your-repo/fss-mini-rag
cd fss-mini-rag

# Install dependencies (5-15 minutes due to compilation)
python -m pip install -r requirements.txt  # Large downloads + ARM compilation
python -m pip install .                    # ~1 minute

# Quick start
python -m mini_rag index /storage/emulated/0/Documents/myproject
python -m mini_rag search /storage/emulated/0/Documents/myproject "your query"
```

**Android-optimized config:**
```yaml
# config-android.yaml
embedding:
  preferred_method: hash    # No heavy models needed
  
chunking:
  max_size: 800            # Small chunks for mobile
  
files:
  min_file_size: 20        # Include more small files
  
llm:
  enable_synthesis: false  # Text-only for speed
```

**What works on Android:**
- ✅ Full text search and indexing
- ✅ Terminal interface (`rag-tui`)
- ✅ Project indexing from phone storage
- ✅ Search your phone's code projects
- ❌ Heavy AI models (use cloud providers instead)

**Android use cases:**
- Search your mobile development projects
- Index documentation on your phone
- Quick code reference while traveling
- Offline search of downloaded repositories

### 🍎 **iOS (Limited but Possible)**

**Option 1: a-Shell (Free)**
```bash
# Install a-Shell from App Store
# In a-Shell:
pip install requests pathlib

# Limited installation (core features only)
# Files must be in app sandbox
```

**Option 2: iSH (Alpine Linux)**
```bash
# Install iSH from App Store  
# In iSH terminal:
apk add python3 py3-pip git
pip install -r requirements-light.txt

# Basic functionality only
```

**iOS limitations:**
- Sandbox restricts file access
- No full AI model support
- Terminal interface only
- Limited to app-accessible files

## Specialized Deployment Scenarios

### 🐳 **Docker Deployment**

**For any platform with Docker:**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Expose ports for server mode
EXPOSE 7777

# Default to TUI interface
CMD ["python", "-m", "mini_rag.cli"]
```

**Usage:**
```bash
# Build and run
docker build -t fss-mini-rag .
docker run -it -v $(pwd)/projects:/projects fss-mini-rag

# Server mode for web access
docker run -p 7777:7777 fss-mini-rag python -m mini_rag server
```

### ☁️ **Cloud Deployment**

**AWS/GCP/Azure VM:**
- Same as Linux installation
- Can serve multiple users
- Perfect for team environments

**GitHub Codespaces:**
```bash
# Works in any Codespace
./install_mini_rag.sh
# Perfect for searching your workspace
```

**Replit/CodeSandbox:**
- Limited by platform restrictions
- Basic functionality available

### 🏠 **Home Lab Integration**

**Home Assistant Add-on:**
- Package as Home Assistant add-on
- Search home automation configs
- Voice integration possible

**NAS Integration:**
- Install on Synology/QNAP
- Search all stored documents
- Family code documentation

**Router with USB:**
- Install on OpenWrt routers with USB storage
- Search network documentation
- Configuration management

## Configuration by Use Case

### 🪶 **Ultra-Lightweight (Old hardware, mobile)**
```yaml
# Minimal resource usage
embedding:
  preferred_method: hash
chunking:
  max_size: 800
  strategy: fixed
llm:
  enable_synthesis: false
```

### ⚖️ **Balanced (Raspberry Pi, older laptops)**
```yaml
# Good performance with AI features
embedding:
  preferred_method: ollama
  ollama_model: nomic-embed-text
llm:
  synthesis_model: qwen3:0.6b
  context_window: 4096
```

### 🚀 **Performance (Modern hardware)**
```yaml
# Full features and performance
embedding:
  preferred_method: ollama
  ollama_model: nomic-embed-text
llm:
  synthesis_model: qwen3:1.7b
  context_window: 16384
  enable_thinking: true
```

### ☁️ **Cloud-Hybrid (Mobile + Cloud AI)**
```yaml
# Local search, cloud intelligence
embedding:
  preferred_method: hash
llm:
  provider: openai
  api_key: your_api_key
  synthesis_model: gpt-4
```

## Troubleshooting by Platform

### **Raspberry Pi Issues**
- **Out of memory**: Reduce context window, use smaller models
- **Slow indexing**: Use hash-based embeddings
- **Model download fails**: Check internet, use smaller models

### **Android/Termux Issues**  
- **Permission denied**: Use `termux-setup-storage`
- **Package install fails**: Update packages first
- **Can't access files**: Use `/storage/emulated/0/` paths

### **iOS Issues**
- **Limited functionality**: Expected due to iOS restrictions
- **Can't install packages**: Use lighter requirements file
- **File access denied**: Files must be in app sandbox

### **Edge Device Issues**
- **ARM compatibility**: Ensure using ARM64 Python packages
- **Limited RAM**: Use hash embeddings, reduce chunk sizes
- **No internet**: Skip AI model downloads, use text-only

## Advanced Edge Deployments

### **IoT Integration**
- Index sensor logs and configurations
- Search device documentation
- Troubleshoot IoT deployments

### **Offline Development**
- Complete development environment on edge device
- No internet required after setup
- Perfect for remote locations

### **Educational Use**
- Raspberry Pi computer labs
- Student project search
- Coding bootcamp environments

### **Enterprise Edge**
- Factory floor documentation search
- Field service technical reference
- Remote site troubleshooting

---

## Quick Start by Platform

### Desktop Users
```bash
# Linux/macOS
./install_mini_rag.sh

# Windows  
install_windows.bat
```

### Edge/Mobile Users
```bash
# Raspberry Pi
./install_mini_rag.sh

# Android (Termux) - 5-15 minutes due to ARM compilation
pkg install python git && python -m pip install -r requirements.txt && python -m pip install .

# Any Docker platform
docker run -it fss-mini-rag
```

**💡 Pro tip**: Start with your current platform, then expand to edge devices as needed. The system scales from smartphones to servers seamlessly!