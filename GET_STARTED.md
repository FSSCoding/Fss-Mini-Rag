# 🚀 FSS-Mini-RAG: Get Started in 2 Minutes

## Step 1: Install Everything
```bash
./install_mini_rag.sh
```
**That's it!** The installer handles everything automatically:
- Checks Python installation
- Sets up virtual environment  
- Guides you through Ollama setup
- Installs dependencies
- Tests everything works

## Step 2: Use It

### TUI - Interactive Interface (Easiest)
```bash
./rag-tui
```
**Perfect for beginners!** Menu-driven interface that:
- Shows you CLI commands as you use it
- Guides you through setup and configuration
- No need to memorize commands

### Quick Commands (Beginner-Friendly)
```bash
# Index any project
./run_mini_rag.sh index ~/my-project

# Search your code  
./run_mini_rag.sh search ~/my-project "authentication logic"

# Check what's indexed
./run_mini_rag.sh status ~/my-project
```

### Full Commands (More Options)
```bash
# Basic indexing and search
./rag-mini index /path/to/project
./rag-mini search /path/to/project "database connection"

# Enhanced search with smart features
./rag-mini-enhanced search /path/to/project "UserManager"
./rag-mini-enhanced similar /path/to/project "def validate_input"
```

## What You Get

**Semantic Search**: Instead of exact text matching, finds code by meaning:
- Search "user login" → finds authentication functions, session management, password validation
- Search "database queries" → finds SQL, ORM code, connection handling  
- Search "error handling" → finds try/catch blocks, error classes, logging

## Installation Options

The installer offers two choices:

**Light Installation (Recommended)**:
- Uses Ollama for high-quality embeddings
- Requires Ollama installed (installer guides you)
- Small download (~50MB)

**Full Installation**:  
- Includes ML fallback models
- Works without Ollama
- Large download (~2-3GB)

## Troubleshooting

**"Python not found"**: Install Python 3.8+ from python.org
**"Ollama not found"**: Visit https://ollama.ai/download
**"Import errors"**: Re-run `./install_mini_rag.sh`

## Next Steps

- **Technical Details**: Read `README.md`
- **Step-by-Step Guide**: Read `docs/GETTING_STARTED.md`
- **Examples**: Check `examples/` directory
- **Test It**: Run on this project: `./run_mini_rag.sh index .`

---
**Questions?** Everything is documented in the README.md file.