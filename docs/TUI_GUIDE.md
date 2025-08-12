# FSS-Mini-RAG Text User Interface Guide

## Overview

The TUI (Text User Interface) provides a beginner-friendly, menu-driven way to use FSS-Mini-RAG without memorizing command-line syntax. It's designed with a "learn by doing" approach - you use the friendly interface while seeing the CLI commands, naturally building confidence to use the command line directly.

## Quick Start

```bash
./rag-tui
```

That's it! The TUI will guide you through everything.

## Interface Design Philosophy

### Learn by Doing
- **No reading required** - Jump in and start using it
- **CLI commands shown** - See equivalent commands as you work
- **Progressive disclosure** - Basic actions upfront, advanced options available
- **Natural transition** - Build confidence to try CLI commands

### User Flow
1. **Select Project** → Choose directory to search
2. **Index Project** → Process files for search
3. **Search Content** → Find what you need
4. **Explore Results** → See full context and files

## Main Menu Options

### 1. Select Project Directory

**Purpose**: Choose which codebase to work with

**Options**:
- **Enter project path** - Type any directory path
- **Use current directory** - Index where you are now  
- **Browse recent projects** - Pick from previously indexed projects

**What You Learn**:
- Project paths and directory navigation
- How RAG works with specific directories
- CLI equivalent: All commands need a project path

**CLI Commands Shown**:
```bash
# You'll see these patterns throughout
./rag-mini <command> /path/to/your/project
```

### 2. Index Project for Search

**Purpose**: Process files to make them searchable

**What Happens**:
- Scans all files in project directory
- Breaks text into searchable chunks
- Creates embeddings (AI numerical representations)
- Stores in local database (`.claude-rag/` folder)

**Interactive Elements**:
- **Force re-index option** - Completely rebuild if needed
- **Progress feedback** - See files being processed
- **Results summary** - Files processed, chunks created, timing

**What You Learn**:
- Why indexing is necessary (one-time setup per project)
- What gets indexed (code files, documentation, configs)
- How fast the system works
- Storage location (`.claude-rag/` directory)

**CLI Commands Shown**:
```bash
./rag-mini index /path/to/project          # Basic indexing
./rag-mini index /path/to/project --force  # Force complete re-index
```

### 3. Search Project

**Purpose**: Find code using natural language queries

**Interactive Process**:
1. **Enter search query** - Natural language or keywords
2. **Set result limit** - How many matches to show (1-20)
3. **View results** - See full content, not just snippets

**Result Display**:
- **File path** - Relative to project root
- **Relevance score** - How closely it matches your query
- **Line numbers** - Exact location in file
- **Context** - Function/class name if applicable  
- **Full content** - Up to 8 lines of actual code/text
- **Continuation info** - How many more lines exist

**Advanced Tips Shown**:
- Enhanced search with `./rag-mini-enhanced`
- Verbose output with `--verbose` flag
- Context-aware search for related code

**What You Learn**:
- Semantic search vs text search (finds concepts, not just words)
- How to phrase effective queries
- Reading search results and relevance scores
- When to use different search strategies

**CLI Commands Shown**:
```bash
./rag-mini search /path/to/project "authentication logic"
./rag-mini search /path/to/project "user login" --limit 10
./rag-mini-enhanced context /path/to/project "login()"
```

### 4. View Status

**Purpose**: Check system health and project information

**Information Displayed**:

**Project Status**:
- **Indexing status** - Whether project is indexed
- **File count** - How many files are searchable
- **Chunk count** - Total searchable pieces
- **Last update** - When indexing was last run
- **Average chunks per file** - Efficiency metric

**Embedding System Status**:
- **Current method** - Ollama, ML fallback, or hash
- **Quality level** - High, good, or basic
- **Model information** - Which AI model is active

**What You Learn**:
- System architecture (embedding methods)
- Project statistics and health
- When re-indexing might be needed
- Performance characteristics

**CLI Commands Shown**:
```bash
./rag-mini status /path/to/project
```

### 5. Configuration

**Purpose**: View and understand system settings

**Configuration Display**:
- **Current settings** - Chunk size, strategy, file patterns
- **File location** - Where config is stored
- **Setting explanations** - What each option does
- **Quick actions** - View or edit config directly

**Key Settings Explained**:
- **chunking.max_size** - How large each searchable piece is
- **chunking.strategy** - Smart (semantic) vs simple (fixed size)
- **files.exclude_patterns** - Skip certain files/directories
- **embedding.preferred_method** - AI model preference
- **search.default_limit** - How many results to show

**Interactive Options**:
- **[V]iew config** - See full configuration file
- **[E]dit path** - Get command to edit configuration

**What You Learn**:
- How configuration affects search quality
- YAML configuration format
- Which settings to adjust for different projects
- Where to find advanced options

**CLI Commands Shown**:
```bash
cat /path/to/project/.claude-rag/config.yaml   # View config
nano /path/to/project/.claude-rag/config.yaml  # Edit config
```

### 6. CLI Command Reference

**Purpose**: Complete command reference for transitioning to CLI

**Organized by Use Case**:

**Basic Commands**:
- Daily usage patterns
- Essential operations
- Common options

**Enhanced Commands**:
- Advanced search features
- Analysis and optimization
- Pattern finding

**Quick Scripts**:
- Simplified wrappers
- Batch operations
- Development workflow integration

**Options Reference**:
- Flags and their purposes
- When to use each option
- Performance considerations

**What You Learn**:
- Complete CLI capabilities
- How TUI maps to CLI commands
- Advanced features not in TUI
- Integration possibilities

## Educational Features

### Progressive Learning

**Stage 1: TUI Comfort**
- Use menus and prompts
- See immediate results
- Build understanding through doing

**Stage 2: CLI Awareness**  
- Notice commands being shown
- Understand command structure
- See patterns in usage

**Stage 3: CLI Experimentation**
- Try simple commands from TUI
- Compare TUI vs CLI speed
- Explore advanced options

**Stage 4: CLI Proficiency**
- Use CLI for daily tasks
- Script and automate workflows
- Customize for specific needs

### Knowledge Building

**Concepts Learned**:
- **Semantic search** - AI understanding vs text matching
- **Embeddings** - How text becomes searchable numbers
- **Chunking** - Breaking files into meaningful pieces
- **Configuration** - Customizing for different projects
- **Indexing** - One-time setup vs incremental updates

**Skills Developed**:
- **Query crafting** - How to phrase effective searches
- **Result interpretation** - Understanding relevance scores
- **System administration** - Configuration and maintenance
- **Workflow integration** - Using RAG in development process

## Advanced Usage Patterns

### Project Management Workflow

1. **New Project**: Select directory → Index → Configure if needed
2. **Existing Project**: Check status → Search → Re-index if outdated
3. **Multiple Projects**: Use recent projects browser for quick switching

### Search Strategies

**Concept Searches**:
- "user authentication" → finds login, auth, sessions
- "database connection" → finds DB code, connection pools, queries
- "error handling" → finds try/catch, error classes, logging

**Specific Code Searches**:
- "class UserManager" → finds class definitions
- "function authenticate()" → finds specific functions
- "config settings" → finds configuration code

**Pattern Searches**:
- "validation logic" → finds input validation across files
- "API endpoints" → finds route definitions and handlers
- "test cases" → finds unit tests and test data

### Configuration Optimization

**Small Projects** (< 100 files):
- Default settings work well
- Consider smaller chunk sizes for very granular search

**Large Projects** (> 1000 files):
- Exclude build directories and dependencies
- Increase chunk sizes for broader context
- Use semantic chunking for code-heavy projects

**Mixed Content Projects**:
- Balance chunk sizes for code vs documentation
- Configure file patterns to include/exclude specific types
- Use appropriate embedding methods for content type

## Troubleshooting

### Common Issues

**"Project not indexed"**:
- Use "Index project for search" from main menu
- Check if project path is correct
- Look for permission issues

**"No results found"**:
- Try broader search terms
- Check project is actually indexed
- Verify files contain expected content

**"Search results poor quality"**:
- Check embedding system status
- Consider re-indexing with --force
- Review configuration for project type

**"System seems slow"**:
- Check if Ollama is running (best performance)
- Consider ML fallback installation
- Review project size and exclude patterns

### Learning Resources

**Built-in Help**:
- TUI shows CLI commands throughout
- Configuration section explains all options
- Status shows system health

**External Resources**:
- `README.md` - Complete technical documentation
- `examples/config.yaml` - Configuration examples
- `docs/GETTING_STARTED.md` - Step-by-step setup guide

**Community Patterns**:
- Common search queries for different languages
- Project-specific configuration examples  
- Integration with IDEs and editors

## Tips for Success

### Getting Started
1. **Start with a small project** - Learn the basics without complexity
2. **Try different search terms** - Experiment with phrasing
3. **Watch the CLI commands** - Notice patterns and structure
4. **Use the status check** - Understand what's happening

### Building Expertise
1. **Compare TUI vs CLI speed** - See when CLI becomes faster
2. **Experiment with configuration** - Try different settings
3. **Search your own code** - Use familiar projects for learning
4. **Try advanced searches** - Explore enhanced commands

### Transitioning to CLI
1. **Copy commands from TUI** - Start with exact commands shown
2. **Modify gradually** - Change options and see effects
3. **Build shortcuts** - Create aliases for common operations
4. **Integrate with workflow** - Add to development process

The TUI is designed to be your training wheels - use it as long as you need, and transition to CLI when you're ready. There's no pressure to abandon the TUI; it's a fully functional interface that many users prefer permanently.