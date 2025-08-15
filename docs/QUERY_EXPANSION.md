# Query Expansion Guide

## What Is Query Expansion?

Query expansion automatically adds related terms to your search to find more relevant results.

**Example:**
- You search: `"authentication"`
- System expands to: `"authentication login user verification credentials security"`
- Result: 2-3x more relevant matches!

## How It Works

```mermaid
graph LR
    A[User Query] --> B[LLM Expands]
    B --> C[Enhanced Search]
    C --> D[Better Results]
    
    style A fill:#e1f5fe
    style D fill:#e8f5e8
```

1. **Your query** goes to a small, fast LLM (like qwen3:1.7b)
2. **LLM adds related terms** that people might use when writing about the topic
3. **Both semantic and keyword search** use the expanded query
4. **You get much better results** without changing anything

## When Is It Enabled?

- ❌ **CLI commands**: Disabled by default (for speed)
- ✅ **TUI interface**: Auto-enabled (when you have time to explore)
- ⚙️ **Configurable**: Can be enabled/disabled in config.yaml

## Configuration

### Easy Configuration (TUI)

Use the interactive Configuration Manager in the TUI:

1. **Start TUI**: `./rag-tui` or `rag.bat` (Windows)
2. **Select Option 6**: Configuration Manager
3. **Choose Option 2**: Toggle query expansion
4. **Follow prompts**: Get explanation and easy on/off toggle

The TUI will:
- Explain benefits and requirements clearly
- Check if Ollama is available
- Show current status (enabled/disabled)
- Save changes automatically

### Manual Configuration (Advanced)

Edit `config.yaml` directly:

```yaml
# Search behavior settings
search:
  expand_queries: false         # Enable automatic query expansion

# LLM expansion settings  
llm:
  max_expansion_terms: 8        # How many terms to add
  expansion_model: auto         # Which model to use
  ollama_host: localhost:11434  # Ollama server
```

## Performance

- **Speed**: ~100ms on most systems (depends on your hardware)
- **Caching**: Repeated queries are instant
- **Model Selection**: Automatically uses fastest available model

## Examples

**Code Search:**
```
"error handling" → "error handling exception try catch fault tolerance recovery"
```

**Documentation Search:**
```
"installation" → "installation setup install deploy configuration getting started"
```

**Any Content:**
```
"budget planning" → "budget planning financial forecast cost analysis spending plan"
```

## Troubleshooting

**Query expansion not working?**
1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify you have a model installed: `ollama list`
3. Check logs with `--verbose` flag

**Too slow?**
1. Disable in config.yaml: `expand_queries: false`
2. Or use faster model: `expansion_model: "qwen3:0.6b"`

**Poor expansions?**
1. Try different model: `expansion_model: "qwen3:1.7b"`
2. Reduce terms: `max_expansion_terms: 5`

## Technical Details

The QueryExpander class:
- Uses temperature 0.1 for consistent results
- Limits expansions to prevent very long queries
- Handles model selection automatically
- Includes smart caching to avoid repeated calls

Perfect for beginners because it "just works" - enable it when you want better results, disable when you want maximum speed.