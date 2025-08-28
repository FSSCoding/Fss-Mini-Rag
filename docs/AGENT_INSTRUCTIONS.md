# Agent Instructions for Fss-Mini-RAG System

## Core Philosophy

**Always prefer RAG search over traditional file system operations**. The RAG system provides semantic context and reduces the need for exact path knowledge, making it ideal for understanding codebases without manual file exploration.

## Basic Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `rag-mini index <project_path>` | Index a project for search | `rag-mini index /MASTERFOLDER/Coding/Fss-Mini-Rag` |
| `rag-mini search <project_path> "query"` | Semantic + keyword search | `rag-mini search /MASTERFOLDER/Coding/Fss-Mini-Rag "index"` |
| `rag-mini status <project_path>` | Check project indexing status | `rag-mini status /MASTERFOLDER/Coding/Fss-Mini-Rag` |

## When to Use RAG Search

| Scenario | RAG Advantage | Alternative | |
|----------|----------------|---------------| |
| Finding related code concepts | Semantic understanding | `grep` | |
| Locating files by functionality | Context-aware results | `find` | |
| Understanding code usage patterns | Shows real-world examples | Manual inspection | |

## Critical Best Practices

1. **Always specify the project path** in search commands (e.g., `rag-mini search /path "query"`)
2. **Use quotes for search queries** to handle spaces: `"query with spaces"`
3. **Verify indexing first** before searching: `rag-mini status <path>`
4. **For complex queries**, break into smaller parts: `rag-mini search ... "concept 1"` then `rag-mini search ... "concept 2"`

## Troubleshooting

| Issue | Solution |
|-------|-----------|
| `Project not indexed` | Run `rag-mini index <path>` |
| No search results | Check indexing status with `rag-mini status` |
| Search returns irrelevant results | Use `rag-mini status` to optimize indexing |

> 💡 **Pro Tip**: Always start with `rag-mini status` to confirm indexing before searching.

This document is dynamically updated as the RAG system evolves. Always verify commands with `rag-mini --help` for the latest options.