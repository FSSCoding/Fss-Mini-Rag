# 🛠️ Troubleshooting Guide - Common Issues & Solutions

*Having problems? You're not alone! Here are solutions to the most common issues beginners encounter.*

---

## 🚀 Installation & Setup Issues

### ❌ "Command not found: ollama"
**Problem:** The system can't find Ollama  
**Solution:** 
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
# Or on Mac: brew install ollama
# Start Ollama
ollama serve
```
**Alternative:** Use the system without Ollama - it will automatically fall back to other embedding methods.

### ❌ "Permission denied" when running scripts
**Problem:** Script files aren't executable  
**Solution:**
```bash
chmod +x rag-mini.py rag-tui.py install_mini_rag.sh
# Or run with python directly:
python3 rag-mini.py --help
```

### ❌ "Module not found" or import errors
**Problem:** Python dependencies not installed  
**Solution:**
```bash
# Install dependencies
pip3 install -r requirements.txt
# If that fails, try:
pip3 install --user -r requirements.txt
```

### ❌ Installation script fails
**Problem:** `./install_mini_rag.sh` doesn't work  
**Solution:**
```bash
# Make it executable first
chmod +x install_mini_rag.sh
# Then run
./install_mini_rag.sh
# Or install manually:
pip3 install -r requirements.txt
python3 -c "import mini_rag; print('✅ Installation successful')"
```

---

## 🔍 Search & Results Issues

### ❌ "No results found" for everything
**Problem:** Search isn't finding anything  
**Diagnosis & Solutions:**

1. **Check if project is indexed:**
   ```bash
   ./rag-mini status /path/to/project
   # If not indexed:
   ./rag-mini index /path/to/project
   ```

2. **Lower similarity threshold:**
   - Edit config file, change `similarity_threshold: 0.05`
   - Or try: `./rag-mini search /path/to/project "query" --threshold 0.05`

3. **Try broader search terms:**
   - Instead of: "getUserById" 
   - Try: "user function" or "get user"

4. **Enable query expansion:**
   - Edit config: `expand_queries: true`
   - Or use TUI which enables it automatically

### ❌ Search results are irrelevant/weird
**Problem:** Getting results that don't match your search  
**Solutions:**

1. **Increase similarity threshold:**
   ```yaml
   search:
     similarity_threshold: 0.3  # Higher = more picky
   ```

2. **Use more specific terms:**
   - Instead of: "function"
   - Try: "login function" or "authentication method"

3. **Check BM25 setting:**
   ```yaml
   search:
     enable_bm25: true  # Helps find exact word matches
   ```

### ❌ Search is too slow
**Problem:** Takes too long to get results  
**Solutions:**

1. **Disable query expansion:**
   ```yaml
   search:
     expand_queries: false
   ```

2. **Reduce result limit:**
   ```yaml
   search:
     default_limit: 5  # Instead of 10
   ```

3. **Use faster embedding method:**
   ```yaml
   embedding:
     preferred_method: hash  # Fastest but lower quality
   ```

4. **Smaller batch size:**
   ```yaml
   embedding:
     batch_size: 16  # Instead of 32
   ```

---

## 🤖 AI/LLM Issues

### ❌ "LLM synthesis unavailable" 
**Problem:** AI explanations aren't working  
**Solutions:**

1. **Check Ollama is running:**
   ```bash
   # In one terminal:
   ollama serve
   # In another:
   ollama list  # Should show installed models
   ```

2. **Install a model:**
   ```bash
   ollama pull qwen3:0.6b    # Fast, small model
   # Or: ollama pull llama3.2  # Larger but better
   ```

3. **Test connection:**
   ```bash
   curl http://localhost:11434/api/tags
   # Should return JSON with model list
   ```

### ❌ AI gives weird/wrong answers
**Problem:** LLM responses don't make sense  
**Solutions:**

1. **Lower temperature:**
   ```yaml
   llm:
     synthesis_temperature: 0.1  # More factual, less creative
   ```

2. **Try different model:**
   ```bash
   ollama pull qwen3:4b     # Recommended: excellent quality
   ollama pull qwen3:1.7b   # Still very good, faster
   ollama pull qwen3:0.6b   # Surprisingly good for CPU-only
   ```

3. **Use synthesis mode instead of exploration:**
   ```bash
   ./rag-mini search /path "query" --synthesize
   # Instead of: ./rag-mini explore /path
   ```

---

## 💾 Memory & Performance Issues

### ❌ "Out of memory" or computer freezes during indexing
**Problem:** System runs out of RAM  
**Solutions:**

1. **Reduce batch size:**
   ```yaml
   embedding:
     batch_size: 8  # Much smaller batches
   ```

2. **Lower streaming threshold:**
   ```yaml
   streaming:
     threshold_bytes: 512000  # 512KB instead of 1MB
   ```

3. **Index smaller projects first:**
   ```bash
   # Exclude large directories
   ./rag-mini index /path/to/project --exclude "node_modules/**,dist/**"
   ```

4. **Use hash embeddings:**
   ```yaml
   embedding:
     preferred_method: hash  # Much less memory
   ```

### ❌ Indexing is extremely slow
**Problem:** Taking forever to index project  
**Solutions:**

1. **Exclude unnecessary files:**
   ```yaml
   files:
     exclude_patterns:
       - "node_modules/**"
       - ".git/**" 
       - "*.log"
       - "build/**"
       - "*.min.js"  # Minified files
   ```

2. **Increase minimum file size:**
   ```yaml
   files:
     min_file_size: 200  # Skip tiny files
   ```

3. **Use simpler chunking:**
   ```yaml
   chunking:
     strategy: fixed  # Faster than semantic
   ```

4. **More workers (if you have good CPU):**
   ```bash
   ./rag-mini index /path/to/project --workers 8
   ```

---

## ⚙️ Configuration Issues

### ❌ "Invalid configuration" errors
**Problem:** Config file has errors  
**Solutions:**

1. **Check YAML syntax:**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

2. **Copy from working example:**
   ```bash
   cp examples/config.yaml .mini-rag/config.yaml
   ```

3. **Reset to defaults:**
   ```bash
   rm .mini-rag/config.yaml
   # System will recreate with defaults
   ```

### ❌ Changes to config aren't taking effect
**Problem:** Modified settings don't work  
**Solutions:**

1. **Restart TUI/CLI:**
   - Configuration is loaded at startup
   - Exit and restart the interface

2. **Check config location:**
   ```bash
   # Project-specific config:
   /path/to/project/.mini-rag/config.yaml
   # Global config:
   ~/.mini-rag/config.yaml
   ```

3. **Force re-index after config changes:**
   ```bash
   ./rag-mini index /path/to/project --force
   ```

---

## 🖥️ Interface Issues

### ❌ TUI looks broken/garbled
**Problem:** Text interface isn't displaying correctly  
**Solutions:**

1. **Try different terminal:**
   ```bash
   # Instead of basic terminal, try:
   # - iTerm2 (Mac)
   # - Windows Terminal (Windows)  
   # - GNOME Terminal (Linux)
   ```

2. **Use CLI directly:**
   ```bash
   ./rag-mini --help  # Skip TUI entirely
   ```

3. **Check terminal size:**
   ```bash
   # Make terminal window larger (TUI needs space)
   # At least 80x24 characters
   ```

### ❌ "Keyboard interrupt" or TUI crashes
**Problem:** Interface stops responding  
**Solutions:**

1. **Use Ctrl+C to exit cleanly:**
   - Don't force-quit if possible

2. **Check for conflicting processes:**
   ```bash
   ps aux | grep rag-tui
   # Kill any stuck processes
   ```

3. **Use CLI as fallback:**
   ```bash
   ./rag-mini search /path/to/project "your query"
   ```

---

## 📁 File & Path Issues

### ❌ "Project not found" or "Permission denied"
**Problem:** Can't access project directory  
**Solutions:**

1. **Check path exists:**
   ```bash
   ls -la /path/to/project
   ```

2. **Check permissions:**
   ```bash
   # Make sure you can read the directory
   chmod -R +r /path/to/project
   ```

3. **Use absolute paths:**
   ```bash
   # Instead of: ./rag-mini index ../my-project
   # Use: ./rag-mini index /full/path/to/my-project
   ```

### ❌ "No files found to index"
**Problem:** System doesn't see any files  
**Solutions:**

1. **Check include patterns:**
   ```yaml
   files:
     include_patterns:
       - "**/*.py"     # Only Python files
       - "**/*.js"     # Add JavaScript
       - "**/*.md"     # Add Markdown
   ```

2. **Check exclude patterns:**
   ```yaml
   files:
     exclude_patterns: []  # Remove all exclusions temporarily
   ```

3. **Lower minimum file size:**
   ```yaml
   files:
     min_file_size: 10  # Instead of 50
   ```

---

## 🔍 Quick Diagnostic Commands

**Check system status:**
```bash
./rag-mini status /path/to/project
```

**Test embeddings:**
```bash
python3 -c "from mini_rag.ollama_embeddings import OllamaEmbedder; e=OllamaEmbedder(); print(e.get_embedding_info())"
```

**Verify installation:**
```bash
python3 -c "import mini_rag; print('✅ RAG system installed')"
```

**Test Ollama connection:**
```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

**Check disk space:**
```bash
df -h .mini-rag/  # Make sure you have space for index
```

---

## 🆘 When All Else Fails

1. **Start fresh:**
   ```bash
   rm -rf .mini-rag/
   ./rag-mini index /path/to/project
   ```

2. **Use minimal config:**
   ```yaml
   # Simplest possible config:
   chunking:
     strategy: fixed
   embedding:  
     preferred_method: auto
   search:
     expand_queries: false
   ```

3. **Try a tiny test project:**
   ```bash
   mkdir test-project
   echo "def hello(): print('world')" > test-project/test.py
   ./rag-mini index test-project
   ./rag-mini search test-project "hello function"
   ```

4. **Get help:**
   - Check the main README.md
   - Look at examples/ directory
   - Try the basic_usage.py example

---

## 💡 Prevention Tips

**For beginners:**
- Start with default settings
- Use the TUI interface first
- Test with small projects initially
- Keep Ollama running in background

**For better results:**
- Be specific in search queries
- Use the glossary to understand terms
- Experiment with config settings on test projects first
- Use synthesis mode for quick answers, exploration for learning

**Remember:** This is a learning tool! Don't be afraid to experiment and try different settings. The worst thing that can happen is you delete the `.mini-rag` directory and start over. 🚀