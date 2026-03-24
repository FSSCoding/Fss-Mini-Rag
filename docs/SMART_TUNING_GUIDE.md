# FSS-Mini-RAG Smart Tuning Guide

## Performance Tuning

### Search Enhancement
```bash
# Enhanced search with query intelligence
rag-mini search "MyClass"     # Detects class names
rag-mini search "login()"     # Detects function calls
rag-mini search "user auth"   # Natural language
```

### Language-Specific Optimisations

**Automatic tuning based on your project:**
- **Python projects**: AST-based function/class chunking
- **Documentation**: Paragraph-based splitting with header hierarchy
- **Config files**: Smaller chunks, skip huge JSONs
- **Mixed projects**: Adaptive strategies per file type

## Configuration

Edit `.mini-rag/config.yaml`:

```yaml
chunking:
  max_size: 2000              # Characters per chunk (adjust per project)
  min_size: 150               # Skip tiny chunks

embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  profile: precision          # precision (MiniLM) or conceptual (Nomic)

search:
  default_top_k: 10
  enable_bm25: true
  expand_queries: false       # Enable for broader searches
```

### Project-Specific Tuning
```bash
# Force reindex with new settings
rag-mini init --force

# Test search quality
rag-mini search "your test query"

# Check index stats
rag-mini stats
```

## Tuning by Project Type

### Small Projects (< 100 files)
- Default settings work well
- Consider smaller chunk sizes for granular search

### Large Projects (> 1000 files)
- Exclude build directories and dependencies
- Increase chunk sizes for broader context
- Use the `precision` embedding profile for speed

### Code-Heavy Projects
- AST-based chunking is automatic for Python
- The code-aware BM25 tokenizer handles `snake_case` and `CamelCase` splitting

### Documentation-Heavy Projects
- Paragraph-based markdown splitting preserves structure
- Header hierarchy is maintained in chunks
- File overview chunks help with "what's in this file" queries

## Performance Impact

- **Better search relevance** from language-aware chunks
- **Faster indexing** from smart file filtering
- **Improved context** from function/header-level chunks
- **Enhanced queries** from automatic query expansion (when enabled)
