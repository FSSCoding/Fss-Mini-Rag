# Getting Started with FSS-Mini-RAG

## Step 1: Installation

Choose your installation based on what you want:

### Option A: Ollama Only (Recommended)
```bash
# Install Ollama first
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the embedding model  
ollama pull nomic-embed-text

# Install Python dependencies
pip install -r requirements.txt
```

### Option B: Full ML Stack
```bash  
# Install everything including PyTorch
pip install -r requirements-full.txt
```

## Step 2: Test Installation

```bash
# Index this RAG system itself
./rag-mini index ~/my-project

# Search for something 
./rag-mini search ~/my-project "chunker function"

# Check what got indexed
./rag-mini status ~/my-project
```

## Step 3: Index Your First Project

```bash
# Index any project directory
./rag-mini index /path/to/your/project

# The system creates .mini-rag/ directory with:
# - config.json (settings)
# - manifest.json (file tracking)  
# - database.lance/ (vector database)
```

## Step 4: Search Your Code

```bash
# Basic semantic search
./rag-mini search /path/to/project "user login logic"

# Enhanced search with smart features  
./rag-mini-enhanced search /path/to/project "authentication"

# Find similar patterns
./rag-mini-enhanced similar /path/to/project "def validate_input"
```

## Step 5: Customize Configuration

Edit `project/.mini-rag/config.json`:

```json
{
  "chunking": {
    "max_size": 3000,
    "strategy": "semantic"  
  },
  "files": {
    "min_file_size": 100
  }
}
```

Then re-index to apply changes:
```bash
./rag-mini index /path/to/project --force
```

## Common Use Cases

### Find Functions by Name
```bash
./rag-mini search /project "function named connect_to_database" 
```

### Find Code Patterns  
```bash
./rag-mini search /project "error handling try catch"
./rag-mini search /project "database query with parameters"
```

### Find Configuration
```bash  
./rag-mini search /project "database connection settings"
./rag-mini search /project "environment variables"
```

### Find Documentation
```bash
./rag-mini search /project "how to deploy" 
./rag-mini search /project "API documentation"
```

## Python API Usage

```python
from mini_rag import ProjectIndexer, CodeSearcher, CodeEmbedder
from pathlib import Path

# Initialize
project_path = Path("/path/to/your/project")
embedder = CodeEmbedder()
indexer = ProjectIndexer(project_path, embedder)
searcher = CodeSearcher(project_path, embedder)

# Index the project
print("Indexing project...")
result = indexer.index_project()
print(f"Indexed {result['files_processed']} files, {result['chunks_created']} chunks")

# Search
print("\nSearching for authentication code...")
results = searcher.search("user authentication logic", limit=5)

for i, result in enumerate(results, 1):
    print(f"\n{i}. {result.file_path}")
    print(f"   Score: {result.score:.3f}")
    print(f"   Type: {result.chunk_type}")
    print(f"   Content: {result.content[:100]}...")
```

## Advanced Features

### Auto-optimization
```bash
# Get optimization suggestions
./rag-mini-enhanced analyze /path/to/project

# This analyzes your codebase and suggests:
# - Better chunk sizes for your language mix
# - Streaming settings for large files
# - File filtering optimizations
```

### File Watching
```python  
from mini_rag import FileWatcher

# Watch for file changes and auto-update index
watcher = FileWatcher(project_path, indexer)
watcher.start_watching()

# Now any file changes automatically update the index
```

### Custom Chunking
```python
from mini_rag import CodeChunker

chunker = CodeChunker()

# Chunk a Python file
with open("example.py") as f:
    content = f.read()

chunks = chunker.chunk_text(content, "python", "example.py")
for chunk in chunks:
    print(f"Type: {chunk.chunk_type}")
    print(f"Content: {chunk.content}")
```

## Tips and Best Practices

### For Better Search Results
- Use descriptive phrases: "function that validates email addresses" 
- Try different phrasings if first search doesn't work
- Search for concepts, not just exact variable names

### For Better Indexing
- Exclude build directories: `node_modules/`, `build/`, `dist/`
- Include documentation files - they often contain valuable context
- Use semantic chunking strategy for most projects

### For Configuration  
- Start with default settings
- Use `analyze` command to get optimization suggestions
- Increase chunk size for larger functions/classes
- Decrease chunk size for more granular search

### For Troubleshooting
- Check `./rag-mini status` to see what was indexed
- Look at `.mini-rag/manifest.json` for file details
- Run with `--force` to completely rebuild index
- Check logs in `.mini-rag/` directory for errors

## What's Next?

1. Try the test suite to understand how components work:
   ```bash
   python -m pytest tests/ -v
   ```

2. Look at the examples in `examples/` directory

3. Read the main README.md for complete technical details

4. Customize the system for your specific project needs