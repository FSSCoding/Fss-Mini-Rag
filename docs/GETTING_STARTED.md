# Getting Started with FSS-Mini-RAG

> **Get from zero to searching in 2 minutes**  
> *Everything you need to know to start finding code by meaning, not just keywords*

## Installation (Choose Your Adventure)

### 🎯 **Option 1: Full Installation (Recommended)**
*Gets you everything working reliably with desktop shortcuts and AI features*

**Linux/macOS:**
```bash
./install_mini_rag.sh
```

**Windows:**
```cmd
install_windows.bat
```

**What this does:**
- Sets up Python environment automatically
- Installs all dependencies 
- Downloads AI models (with your permission)
- Creates desktop shortcuts and application menu entries
- Tests everything works
- Gives you an interactive tutorial

**Time needed:** 5-10 minutes (depending on AI model downloads)

---

### 🚀 **Option 2: Copy & Try (Experimental)**
*Just copy the folder and run - may work, may need manual setup*

**Linux/macOS:**
```bash
# Copy folder anywhere and try running
./rag-mini index ~/my-project
# Auto-setup attempts to create virtual environment
# Falls back with clear instructions if it fails
```

**Windows:**
```cmd
# Copy folder anywhere and try running  
rag.bat index C:\my-project
# Auto-setup attempts to create virtual environment
# Shows helpful error messages if manual install needed
```

**Time needed:** 30 seconds if it works, 10 minutes if you need manual setup

---

## First Search (The Fun Part!)

### Step 1: Choose Your Interface

**For Learning and Exploration:**
```bash
# Linux/macOS
./rag-tui

# Windows  
rag.bat
```
*Interactive menus, shows you CLI commands as you learn*

**For Quick Commands:**
```bash
# Linux/macOS
./rag-mini <command> <project-path>

# Windows
rag.bat <command> <project-path>
```
*Direct commands when you know what you want*

### Step 2: Index Your First Project

**Interactive Way (Recommended for First Time):**
```bash
# Linux/macOS
./rag-tui
# Then: Select Project Directory → Index Project

# Windows
rag.bat  
# Then: Select Project Directory → Index Project
```

**Direct Commands:**
```bash
# Linux/macOS
./rag-mini index ~/my-project

# Windows  
rag.bat index C:\my-project
```

**What indexing does:**
- Finds all text files in your project
- Breaks them into smart "chunks" (functions, classes, logical sections)
- Creates searchable embeddings that understand meaning
- Stores everything in a fast vector database
- Creates a `.mini-rag/` directory with your search index

**Time needed:** 10-60 seconds depending on project size

### Step 3: Search by Meaning

**Natural language queries:**
```bash
# Linux/macOS
./rag-mini search ~/my-project "user authentication logic"
./rag-mini search ~/my-project "error handling for database connections"
./rag-mini search ~/my-project "how to validate input data"

# Windows
rag.bat search C:\my-project "user authentication logic"  
rag.bat search C:\my-project "error handling for database connections"
rag.bat search C:\my-project "how to validate input data"
```

**Code concepts:**
```bash
# Finds login functions, auth middleware, session handling
./rag-mini search ~/my-project "login functionality"

# Finds try/catch blocks, error handlers, retry logic  
./rag-mini search ~/my-project "exception handling"

# Finds validation functions, input sanitization, data checking
./rag-mini search ~/my-project "data validation"
```

**What you get:**
- Ranked results by relevance (not just keyword matching)
- File paths and line numbers for easy navigation
- Context around each match so you understand what it does
- Smart filtering to avoid noise and duplicates

## Two Powerful Modes

FSS-Mini-RAG has two different ways to get answers, optimized for different needs:

### 🚀 **Synthesis Mode** - Fast Answers
```bash
# Linux/macOS
./rag-mini search ~/project "authentication logic" --synthesize

# Windows  
rag.bat search C:\project "authentication logic" --synthesize
```

**Perfect for:**
- Quick code discovery
- Finding specific functions or patterns
- Getting fast, consistent answers

**What you get:**
- Lightning-fast responses (no thinking overhead)
- Reliable, factual information about your code
- Clear explanations of what code does and how it works

### 🧠 **Exploration Mode** - Deep Understanding
```bash  
# Linux/macOS
./rag-mini explore ~/project

# Windows
rag.bat explore C:\project
```

**Perfect for:**
- Learning new codebases
- Debugging complex issues  
- Understanding architectural decisions

**What you get:**
- Interactive conversation with AI that remembers context
- Deep reasoning with full "thinking" process shown
- Follow-up questions and detailed explanations
- Memory of your previous questions in the session

**Example exploration session:**
```
🧠 Exploration Mode - Ask anything about your project

You: How does authentication work in this codebase?

AI: Let me analyze the authentication system...

💭 Thinking: I can see several authentication-related files. Let me examine 
   the login flow, session management, and security measures...

📝 Authentication Analysis:
   This codebase uses a three-layer authentication system:
   1. Login validation in auth.py handles username/password checking
   2. Session management in sessions.py maintains user state  
   3. Middleware in auth_middleware.py protects routes

You: What security concerns should I be aware of?

AI: Based on our previous discussion about authentication, let me check for
   common security vulnerabilities...
```

## Check Your Setup

**See what got indexed:**
```bash
# Linux/macOS  
./rag-mini status ~/my-project

# Windows
rag.bat status C:\my-project
```

**What you'll see:**
- How many files were processed
- Total chunks created for searching
- Embedding method being used (Ollama, ML models, or hash-based)
- Configuration file location
- Index health and last update time

## Configuration (Optional)

Your project gets a `.mini-rag/config.yaml` file with helpful comments:

```yaml
# Context window configuration (critical for AI features)
# 💡 Sizing guide: 2K=1 question, 4K=1-2 questions, 8K=manageable, 16K=most users
#               32K=large codebases, 64K+=power users only  
# ⚠️  Larger contexts use exponentially more CPU/memory - only increase if needed
context_window: 16384           # Context size in tokens

# AI model preferences (edit to change priority)
model_rankings:
  - "qwen3:1.7b"    # Excellent for RAG (1.4GB, recommended)
  - "qwen3:0.6b"    # Lightweight and fast (~500MB)  
  - "qwen3:4b"      # Higher quality but slower (~2.5GB)
```

**When to customize:**
- Your searches aren't finding what you expect → adjust chunking settings
- You want AI features → install Ollama and download models
- System is slow → try smaller models or reduce context window
- Getting too many/few results → adjust similarity threshold

## Troubleshooting

### "Project not indexed" 
**Problem:** You're trying to search before indexing
```bash
# Run indexing first
./rag-mini index ~/my-project    # Linux/macOS
rag.bat index C:\my-project      # Windows
```

### "No Ollama models available"
**Problem:** AI features need models downloaded
```bash
# Install Ollama first
curl -fsSL https://ollama.ai/install.sh | sh    # Linux/macOS
# Or download from https://ollama.com            # Windows

# Start Ollama server
ollama serve

# Download a model
ollama pull qwen3:1.7b
```

### "Virtual environment not found" 
**Problem:** Auto-setup didn't work, need manual installation

**Option A: Use installer scripts**
```bash
./install_mini_rag.sh          # Linux/macOS  
install_windows.bat            # Windows
```

**Option B: Manual method (100% reliable)**
```bash
# Linux/macOS
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt  # 2-8 minutes
.venv/bin/python -m pip install .                    # ~1 minute  
source .venv/bin/activate

# Windows  
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt  
.venv\Scripts\python -m pip install .
.venv\Scripts\activate.bat
```

> **⏱️ Timing**: Fast internet 2-3 minutes total, slow internet 5-10 minutes due to large dependencies (LanceDB 36MB, PyArrow 43MB, PyLance 44MB).

### Getting weird results
**Solution:** Try different search terms or check what got indexed
```bash
# See what files were processed
./rag-mini status ~/my-project

# Try more specific queries
./rag-mini search ~/my-project "specific function name"
```

## Next Steps

### Learn More
- **[Beginner's Glossary](BEGINNER_GLOSSARY.md)** - All the terms explained simply
- **[TUI Guide](TUI_GUIDE.md)** - Master the interactive interface
- **[Visual Diagrams](DIAGRAMS.md)** - See how everything works

### Advanced Features
- **[Query Expansion](QUERY_EXPANSION.md)** - Make searches smarter with AI
- **[LLM Providers](LLM_PROVIDERS.md)** - Use different AI models  
- **[CPU Deployment](CPU_DEPLOYMENT.md)** - Optimize for older computers

### Customize Everything
- **[Technical Guide](TECHNICAL_GUIDE.md)** - How the system actually works
- **[Configuration Examples](../examples/)** - Pre-made configs for different needs

---

**🎉 That's it!** You now have a semantic search system that understands your code by meaning, not just keywords. Start with simple searches and work your way up to the advanced AI features as you get comfortable.

**💡 Pro tip:** The best way to learn is to index a project you know well and try searching for things you know are in there. You'll quickly see how much better meaning-based search is than traditional keyword search.