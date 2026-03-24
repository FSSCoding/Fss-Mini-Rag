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

1. **Your query** goes to a small, fast LLM via your configured endpoint
2. **LLM adds related terms** that people might use when writing about the topic
3. **Both semantic and keyword search** use the expanded query
4. **You get much better results** without changing anything

## Configuration

### Via GUI

Open the desktop GUI (`rag-mini gui`), go to Preferences, and configure your LLM endpoint. Query expansion uses the same LLM endpoint as synthesis.

### Via Config File

Edit `.mini-rag/config.yaml`:

```yaml
search:
  expand_queries: false         # Enable automatic query expansion

llm:
  max_expansion_terms: 8        # How many terms to add
  expansion_model: auto         # Which model to use
  api_base: http://localhost:1234/v1  # LLM server endpoint
```

## When Is It Enabled?

- **CLI commands**: Disabled by default (for speed)
- **Configurable**: Can be enabled/disabled in config.yaml
- **Per-query**: Use `--synthesize` flag for individual queries

## Performance

- **Speed**: ~100ms on most systems (depends on your hardware and model)
- **Caching**: Repeated queries are instant
- **Model Selection**: Automatically uses fastest available model

## Examples

**Code Search:**
```
"error handling" -> "error handling exception try catch fault tolerance recovery"
```

**Documentation Search:**
```
"installation" -> "installation setup install deploy configuration getting started"
```

**Any Content:**
```
"budget planning" -> "budget planning financial forecast cost analysis spending plan"
```

## Troubleshooting

**Query expansion not working?**
1. Check your LLM endpoint is running (LM Studio, vLLM, etc.)
2. Verify `expand_queries: true` in config
3. Check logs with `--verbose` flag

**Too slow?**
1. Disable in config: `expand_queries: false`
2. Or use a faster/smaller model in your LLM server

**Poor expansions?**
1. Try a different model in your LLM server
2. Reduce terms: `max_expansion_terms: 5`

## Technical Details

The QueryExpander class:
- Uses temperature 0.1 for consistent results
- Limits expansions to prevent very long queries
- Handles model selection automatically
- Includes smart caching to avoid repeated calls

Enable it when you want better results, disable when you want maximum speed.
