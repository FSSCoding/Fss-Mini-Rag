# FSS-Mini-RAG Enhancement Backlog

## Path Resolution & UX Improvements

### Current State
```bash
rag-mini search /full/absolute/path "query"
```

### Desired State
```bash
cd /my/project
rag-mini "authentication logic"    # Auto-detects current directory, defaults to search
rag-mini . "query"                 # Explicit current directory  
rag-mini ../other "query"          # Relative path resolution
```

### Implementation Requirements
1. **Auto-detect current working directory** when no path specified
2. **Default to search command** when first argument is a query string
3. **Proper path resolution** using `pathlib.Path.resolve()` for all relative paths
4. **Maintain backwards compatibility** with existing explicit command syntax

### Technical Details
- Modify `mini_rag/cli.py` argument parsing
- Add path resolution with `os.path.abspath()` or `pathlib.Path.resolve()`
- Make project_path optional (default to `os.getcwd()`)
- Smart command detection (if first arg doesn't match command, assume search)

### Priority
High - Significant UX improvement for daily usage