# FSS-Mini-RAG

> **A lightweight, educational RAG system that actually works**  
> *Built for beginners who want results, and developers who want to understand how RAG really works*

## Demo

![FSS-Mini-RAG Demo](recordings/fss-mini-rag-demo-20250812_161410.gif)

*See it in action: index a project and search semantically in seconds*

## How It Works

```mermaid
graph LR
    Files[📁 Your Code] --> Index[🔍 Index]
    Index --> Chunks[✂️ Smart Chunks]
    Chunks --> Embeddings[🧠 Semantic Vectors]
    Embeddings --> Database[(💾 Vector DB)]
    
    Query[❓ user auth] --> Search[🎯 Hybrid Search]
    Database --> Search
    Search --> Results[📋 Ranked Results]
    
    style Files fill:#e3f2fd
    style Results fill:#e8f5e8
    style Database fill:#fff3e0
```

## What This Is

FSS-Mini-RAG is a distilled, lightweight implementation of a production-quality RAG (Retrieval Augmented Generation) search system. Born from 2 years of building, refining, and tuning RAG systems - from enterprise-scale solutions handling 14,000 queries/second to lightweight implementations that anyone can install and understand.

**The Problem This Solves**: Most RAG implementations are either too simple (poor results) or too complex (impossible to understand and modify). This bridges that gap.

## Two Powerful Modes

FSS-Mini-RAG offers **two distinct experiences** optimized for different use cases:

### 🚀 **Synthesis Mode** - Fast & Consistent
```bash
./rag-mini search ~/project "authentication logic" --synthesize
```
- **Perfect for**: Quick answers, code discovery, fast lookups
- **Speed**: Lightning fast responses (no thinking overhead)
- **Quality**: Consistent, reliable results

### 🧠 **Exploration Mode** - Deep & Interactive  
```bash
./rag-mini explore ~/project
> How does authentication work in this codebase?
> Why is the login function slow?
> What security concerns should I be aware of?
```
- **Perfect for**: Learning codebases, debugging, detailed analysis
- **Features**: Thinking-enabled LLM, conversation memory, follow-up questions
- **Quality**: Deep reasoning with full context awareness

## Quick Start (2 Minutes)

```bash
# 1. Install everything
./install_mini_rag.sh

# 2. Choose your interface
./rag-tui                         # Friendly interface for beginners
# OR choose your mode:
./rag-mini index ~/my-project     # Index your project first
./rag-mini search ~/my-project "query" --synthesize  # Fast synthesis
./rag-mini explore ~/my-project   # Interactive exploration
```

That's it. No external dependencies, no configuration required, no PhD in computer science needed.

## What Makes This Different

### For Beginners
- **Just works** - Zero configuration required
- **Multiple interfaces** - TUI for learning, CLI for speed
- **Educational** - Shows you CLI commands as you use the TUI
- **Solid results** - Finds code by meaning, not just keywords

### For Developers
- **Hackable** - Clean, documented code you can actually modify
- **Configurable** - YAML config for everything, or change the code directly
- **Multiple embedding options** - Ollama, ML models, or hash-based
- **Production patterns** - Streaming, batching, error handling, monitoring

### For Learning
- **Complete technical documentation** - How chunking, embedding, and search actually work
- **Educational tests** - See the system in action with real examples
- **No magic** - Every decision explained, every component documented

## Usage Examples

### Find Code by Concept
```bash
./rag-mini search ~/project "user authentication"
# Finds: login functions, auth middleware, session handling, password validation
```

### Natural Language Queries  
```bash
./rag-mini search ~/project "error handling for database connections"
# Finds: try/catch blocks, connection pool error handlers, retry logic
```

### Development Workflow
```bash
./rag-mini index ~/new-project              # Index once
./rag-mini search ~/new-project "API endpoints"   # Search as needed
./rag-mini status ~/new-project            # Check index health
```

![FSS-Mini-RAG Search Demo](recordings/fss-mini-rag-demo-20250812_160725.gif)

*Advanced usage: semantic search with synthesis and exploration modes*

## Installation Options

### Recommended: Full Installation
```bash
./install_mini_rag.sh
# Handles Python setup, dependencies, optional AI models
```

### Experimental: Copy & Run (May Not Work)
```bash
# Copy folder anywhere and try to run directly
./rag-mini index ~/my-project
# Auto-setup will attempt to create environment
# Falls back with clear instructions if it fails
```

### Manual Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Note**: The experimental copy & run feature is provided for convenience but may fail on some systems. If you encounter issues, use the full installer for reliable setup.

## System Requirements

- **Python 3.8+** (installer checks and guides setup)
- **Optional: Ollama** (for best search quality - installer helps set up)
- **Fallback: Works without external dependencies** (uses built-in embeddings)

## Project Philosophy

This implementation prioritizes:

1. **Educational Value** - You can understand and modify every part
2. **Practical Results** - Actually finds relevant code, not just keyword matches  
3. **Zero Friction** - Works out of the box, configurable when needed
4. **Real-world Patterns** - Production techniques in beginner-friendly code

## What's Inside

- **Hybrid embedding system** - Ollama → ML → Hash fallbacks
- **Smart chunking** - Language-aware code parsing 
- **Vector + keyword search** - Best of both worlds
- **Streaming architecture** - Handles large codebases efficiently
- **Multiple interfaces** - TUI, CLI, Python API, server mode

## Next Steps

- **New users**: Run `./rag-mini` for guided experience
- **Developers**: Read [`TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md) for implementation details
- **Contributors**: See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Visual Diagrams](docs/DIAGRAMS.md)** - 📊 System flow charts and architecture diagrams
- **[TUI Guide](docs/TUI_GUIDE.md)** - Complete walkthrough of the friendly interface  
- **[Technical Guide](docs/TECHNICAL_GUIDE.md)** - How the system actually works
- **[Configuration Guide](docs/CONFIGURATION.md)** - Customizing for your needs
- **[Development Guide](docs/DEVELOPMENT.md)** - Extending and modifying the code

## License

MIT - Use it, learn from it, build on it.

---

*Built by someone who got frustrated with RAG implementations that were either too simple to be useful or too complex to understand. This is the system I wish I'd found when I started.*