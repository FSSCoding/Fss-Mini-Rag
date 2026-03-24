# Agent Instructions for Fss-Mini-RAG System

## Core Philosophy

**Always prefer RAG search over traditional file system operations**. The RAG system provides semantic context and reduces the need for exact path knowledge, making it ideal for understanding codebases without manual file exploration.

## Basic Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `rag-mini init` | Index current directory | `rag-mini init` |
| `rag-mini init --path <path>` | Index a specific project | `rag-mini init --path ~/my-project` |
| `rag-mini search "query"` | Semantic + keyword search | `rag-mini search "index"` |
| `rag-mini search "query" --synthesize` | Search with LLM synthesis | `rag-mini search "auth" --synthesize` |
| `rag-mini status` | Check project indexing status | `rag-mini status` |
| `rag-mini find-function "name"` | Find a function by name | `rag-mini find-function "authenticate"` |
| `rag-mini find-class "name"` | Find a class by name | `rag-mini find-class "UserManager"` |

## Web Research Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `rag-mini scrape <url>` | Scrape URL to markdown | `rag-mini scrape https://docs.python.org/3/library/json.html` |
| `rag-mini search-web "query"` | Search the web | `rag-mini search-web "topic" --engine brave` |
| `rag-mini research "query"` | Full research pipeline | `rag-mini research "topic" --deep --time 1h` |

## When to Use RAG Search

| Scenario | RAG Advantage | Alternative |
|----------|---------------|-------------|
| Finding related code concepts | Semantic understanding | `grep` |
| Locating files by functionality | Context-aware results | `find` |
| Understanding code usage patterns | Shows real-world examples | Manual inspection |
| Researching a topic from the web | Search, scrape, index, query | Manual browsing |

## Critical Best Practices

1. **Index first** before searching: `rag-mini init`
2. **Use quotes for search queries** to handle spaces: `"query with spaces"`
3. **For complex queries**, break into smaller parts
4. **Use `--synthesize`** when you need AI-explained answers, not just code matches
5. **Use `find-function` and `find-class`** for exact name lookups

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Project not indexed` | Run `rag-mini init` |
| No search results | Check indexing status with `rag-mini status` |
| No embedding provider | Start LM Studio or configure an endpoint |
| Search returns irrelevant results | Try more specific terms or enable query expansion |

> Always start with `rag-mini status` to confirm indexing before searching.

This document is dynamically updated as the RAG system evolves. Always verify commands with `rag-mini --help` for the latest options.
