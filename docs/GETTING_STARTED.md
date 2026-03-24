# Getting Started with FSS-Mini-RAG

> **Get from zero to searching in 2 minutes**
> *Everything you need to know to start finding code by meaning, not just keywords*

## Installation

### Option 1: Install from Source (Recommended)

**Linux/macOS:**
```bash
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

**Windows:**
```cmd
git clone https://github.com/FSSCoding/Fss-Mini-Rag.git
cd Fss-Mini-Rag
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

**What this does:**
- Creates an isolated Python environment
- Installs all dependencies (LanceDB, PyArrow, Rich, etc.)
- Makes `rag-mini` command available in the virtual environment

**Time needed:** 2-5 minutes (depends on internet speed for downloading dependencies)

---

### Option 2: Windows Interactive Installer

```cmd
install_windows.bat
```

**Time needed:** 5-10 minutes

---

## Choose Your Interface

FSS-Mini-RAG has two interfaces:

**Desktop GUI** (recommended for beginners):
```bash
rag-mini gui
```
Tkinter desktop app with dark/light theme, search, indexing, web research, and LLM synthesis — all in one window.

**Command Line** (for power users):
```bash
rag-mini <command> [options]
```
Direct commands when you know what you want.

---

## First Search

### Step 1: Index Your Project

```bash
# Index current directory
rag-mini init

# Or index a specific path
rag-mini init --path ~/my-project

# Force a complete re-index
rag-mini init --path ~/my-project --force
```

**What indexing does:**
- Finds all text files in your project
- Breaks them into smart "chunks" (functions, classes, logical sections)
- Creates searchable embeddings that understand meaning
- Stores everything in a fast vector database (LanceDB)
- Creates a `.mini-rag/` directory with your search index

**Time needed:** 10-60 seconds depending on project size

### Step 2: Search by Meaning

**Natural language queries:**
```bash
rag-mini search "user authentication logic"
rag-mini search "error handling for database connections"
rag-mini search "how to validate input data"
```

**Code concepts:**
```bash
# Finds login functions, auth middleware, session handling
rag-mini search "login functionality"

# Finds try/catch blocks, error handlers, retry logic
rag-mini search "exception handling"

# Finds validation functions, input sanitization, data checking
rag-mini search "data validation"
```

**What you get:**
- Ranked results by relevance (not just keyword matching)
- File paths and line numbers for easy navigation
- Context around each match so you understand what it does
- Smart filtering to avoid noise and duplicates

### Step 3: Get AI-Synthesised Answers

Add `--synthesize` to have an LLM read the search results and explain them:

```bash
rag-mini search "authentication logic" --synthesize
```

This requires an LLM endpoint (LM Studio, vLLM, or OpenAI-compatible). Without one, search still works — you just don't get the AI summary.

---

## Web Research

FSS-Mini-RAG can search the web, scrape pages, and index the content locally:

```bash
# Scrape a URL and make it searchable
rag-mini scrape https://docs.python.org/3/library/json.html --index

# Search the web and scrape results
rag-mini search-web "quantum gravity holographic mass" --engine brave

# Full pipeline: search, scrape, index (one command)
rag-mini research "proton structure quantum chromodynamics" --engine tavily

# Deep research: iterative cycles with LLM analysis and time budget
rag-mini research "quantum vacuum fluctuations" --deep --time 1h
```

See the [Web Search & Research Guide](WEB_SEARCH_AND_RESEARCH.md) for full details.

---

## Check Your Setup

```bash
rag-mini status
```

**What you'll see:**
- How many files were processed
- Total chunks created for searching
- Embedding provider and model in use
- Configuration file location
- Index health and last update time

---

## Configuration (Optional)

Your project gets a `.mini-rag/config.yaml` file:

```yaml
embedding:
  provider: openai              # openai or ml
  base_url: http://localhost:1234/v1
  model: auto                   # auto-detects best available
  profile: precision            # precision or conceptual

chunking:
  max_size: 2000                # characters per chunk
  min_size: 150

search:
  default_top_k: 10
  enable_bm25: true
```

**When to customise:**
- Searches aren't finding what you expect — adjust chunking settings
- You want AI synthesis — configure an LLM endpoint (see [LLM Providers](LLM_PROVIDERS.md))
- System is slow — try smaller embedding models or reduce chunk sizes
- Getting too many/few results — adjust `default_top_k` or similarity threshold

---

## Troubleshooting

### "Project not indexed"
```bash
rag-mini init
```

### "No embedding provider available"
You need an OpenAI-compatible embedding server running. Recommended: [LM Studio](https://lmstudio.ai/) with MiniLM L6 v2 loaded. Without one, BM25 keyword search still works.

### "Virtual environment not found"

**Manual method (100% reliable):**
```bash
# Linux/macOS
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install .
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install .
.venv\Scripts\activate.bat
```

> **Timing**: Fast internet 2-3 minutes total, slow internet 5-10 minutes due to large dependencies (LanceDB 36MB, PyArrow 43MB, PyLance 44MB).

### Getting weird results
```bash
# Check what got indexed
rag-mini status

# Try more specific queries
rag-mini search "specific function name"

# Force re-index if needed
rag-mini init --force
```

---

## Next Steps

### Learn More
- **[Beginner's Glossary](BEGINNER_GLOSSARY.md)** — All the terms explained simply
- **[Visual Diagrams](DIAGRAMS.md)** — See how everything works

### Advanced Features
- **[Web Search & Research](WEB_SEARCH_AND_RESEARCH.md)** — Web scraping and deep research
- **[Query Expansion](QUERY_EXPANSION.md)** — Make searches smarter with AI
- **[LLM Providers](LLM_PROVIDERS.md)** — Use different AI models
- **[CPU Deployment](CPU_DEPLOYMENT.md)** — Optimise for older computers

### Go Deeper
- **[Technical Guide](TECHNICAL_GUIDE.md)** — How the system actually works
- **[Hybrid Search Algorithm](HYBRID_SEARCH_ALGORITHM.md)** — RRF fusion details

---

The best way to learn is to index a project you know well and try searching for things you know are in there. You'll quickly see how much better meaning-based search is than traditional keyword search.
