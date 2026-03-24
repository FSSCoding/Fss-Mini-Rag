# Troubleshooting Guide — Common Issues & Solutions

---

## Installation & Setup Issues

### "Command not found: rag-mini"
**Problem:** The CLI isn't installed or the virtual environment isn't active.
**Solution:**
```bash
# Activate the virtual environment
source .venv/bin/activate

# Or install in development mode
pip install -e .

# Verify
rag-mini --help
```

### "Permission denied" when running scripts
**Problem:** Script files aren't executable.
**Solution:**
```bash
chmod +x rag-mini
# Or run via Python directly:
python3 -m mini_rag.cli --help
```

### "Module not found" or import errors
**Problem:** Python dependencies not installed.
**Solution:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Installation fails
**Problem:** Dependencies won't install.
**Solution:**
```bash
# Proven manual method (100% reliable):
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python3 -c "import mini_rag; print('Installation successful')"
```

### Installation takes too long
**Problem:** pip install seems stuck.
**Expected timing:** 2-5 minutes (depends on internet speed).
**Why:** Large but essential dependencies:
- LanceDB: ~36MB (vector database)
- PyArrow: ~43MB (data processing)
- PyLance: ~44MB (language parsing)
- Total: ~120MB download

**Slow connection fallback:**
```bash
pip install -r requirements.txt --timeout 1000
```

---

## Search & Results Issues

### "No results found" for everything
**Diagnosis & solutions:**

1. **Check if project is indexed:**
   ```bash
   rag-mini status
   # If not indexed:
   rag-mini init
   ```

2. **Try broader search terms:**
   - Instead of: "getUserById"
   - Try: "user function" or "get user"

3. **Enable query expansion:**
   - Edit config: `expand_queries: true`

### Search results are irrelevant
**Solutions:**

1. **Use more specific terms:**
   - Instead of: "function"
   - Try: "login function" or "authentication method"

2. **Check BM25 setting:**
   ```yaml
   search:
     enable_bm25: true  # Helps find exact word matches
   ```

### Search is too slow
**Solutions:**

1. **Disable query expansion:**
   ```yaml
   search:
     expand_queries: false
   ```

2. **Reduce result limit:**
   ```yaml
   search:
     default_top_k: 5
   ```

---

## Embedding & LLM Issues

### "No embedding provider available"
**Problem:** No OpenAI-compatible embedding server is running.
**Solutions:**

1. **Start LM Studio** with an embedding model loaded (e.g. MiniLM L6 v2)
2. **Or use vLLM** with an embedding model
3. **Or use any OpenAI-compatible endpoint** and configure:
   ```yaml
   embedding:
     base_url: http://localhost:1234/v1
   ```

Without an embedding server, BM25 keyword search still works — you just don't get semantic similarity.

### "LLM synthesis unavailable"
**Problem:** No LLM endpoint configured or reachable.
**Solutions:**

1. **Check your LLM server is running** (LM Studio, vLLM, or cloud provider)
2. **Configure the endpoint:**
   ```yaml
   llm:
     provider: openai
     api_base: http://localhost:1234/v1
   ```
3. **Test the connection:**
   ```bash
   rag-mini gui
   # Use Preferences > Test Connection
   ```

### LLM gives poor answers
**Solutions:**

1. **Lower temperature:**
   ```yaml
   llm:
     synthesis_temperature: 0.1  # More factual, less creative
   ```

2. **Try a different/larger model** in your LLM server

3. **Use synthesis mode instead of just search:**
   ```bash
   rag-mini search "query" --synthesize
   ```

---

## Web Research Issues

### Scraping fails or returns empty content
**Solutions:**

1. **Check the URL is accessible:**
   ```bash
   rag-mini scrape https://example.com
   ```

2. **Some sites block scrapers** — try a different source

3. **For PDFs**, ensure pymupdf is installed:
   ```bash
   pip install pymupdf
   ```

### Deep research runs out of time
**Solution:** Increase the time budget:
```bash
rag-mini research "topic" --deep --time 2h
```

### Rate limiting errors
The system has built-in rate limiting and retry logic. If you're hitting API limits:
- Reduce `--max-pages` for web searches
- Use a search engine with higher rate limits (Tavily with API key)

---

## GUI Issues

### GUI won't launch
**Problem:** Tkinter not installed.
**Solution:**
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# macOS (usually included with Python)
# Windows (usually included with Python)
```

### GUI looks wrong or has no theme
**Problem:** Sun Valley theme not loading.
**Solution:**
```bash
pip install sv-ttk
```

### GUI can't connect to endpoints
**Solution:**
1. Open Preferences dialog
2. Set correct embedding and LLM endpoint URLs
3. Click "Test Connection" to verify
4. Use a preset (LM Studio, BobAI) if available

---

## Memory & Performance Issues

### "Out of memory" or computer freezes during indexing
**Solutions:**

1. **Index smaller projects** or exclude large directories
2. **Use the `--force` flag** to rebuild cleanly:
   ```bash
   rag-mini init --force
   ```

### Indexing is extremely slow
**Solutions:**

1. **Check exclude patterns** — make sure node_modules, .git, etc. are excluded
2. **Force re-index:**
   ```bash
   rag-mini init --force
   ```

---

## Configuration Issues

### Changes to config aren't taking effect
**Solutions:**

1. **Restart the CLI/GUI** — config is loaded at startup
2. **Check config location:**
   ```bash
   # Project-specific config:
   .mini-rag/config.yaml
   ```
3. **Force re-index after config changes:**
   ```bash
   rag-mini init --force
   ```

### Reset to defaults
```bash
rm .mini-rag/config.yaml
# System will recreate with defaults on next run
```

---

## Quick Diagnostic Commands

**Check system status:**
```bash
rag-mini status
```

**Show system info:**
```bash
rag-mini info
```

**Verify installation:**
```bash
python3 -c "import mini_rag; print('RAG system installed')"
```

---

## When All Else Fails

1. **Start fresh:**
   ```bash
   rm -rf .mini-rag/
   rag-mini init
   ```

2. **Try a tiny test project:**
   ```bash
   mkdir test-project
   echo "def hello(): print('world')" > test-project/test.py
   cd test-project
   rag-mini init
   rag-mini search "hello function"
   ```

3. **Check the docs:**
   - [Getting Started](GETTING_STARTED.md)
   - [LLM Providers](LLM_PROVIDERS.md)
   - [Web Search & Research](WEB_SEARCH_AND_RESEARCH.md)
