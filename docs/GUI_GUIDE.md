# FSS-Mini-RAG Desktop GUI Guide

> **Note:** The original Text User Interface (rag-tui) has been replaced by a full desktop GUI application.

## Quick Start

```bash
rag-mini gui
```

That's it. The desktop GUI launches with a dark-themed Tkinter window.

## Interface Overview

The GUI uses a **two-tab layout** built on Sun Valley theme (dark/light toggle available):

### Tab 1: Search & Index

The primary interface for working with local collections:

- **Collection Panel** — browse and select indexed projects
- **Search Bar** — enter natural language queries with synthesis toggle
- **Results Table** — ranked results with score labels (HIGH/GOOD/FAIR/LOW)
- **Content Panel** — full content display with RenderedMarkdown widget
- **Status Bar** — connection status, indexing progress, timing info

**Key actions:**
- Index a project directory
- Search with semantic + BM25 hybrid search
- Toggle LLM synthesis for AI-generated summaries
- View full chunk content with syntax highlighting

### Tab 2: Web Research

The web research interface for scraping and deep research:

- **Web search** — search DuckDuckGo, Tavily, or Brave
- **URL scraping** — fetch and extract content from URLs
- **Deep research** — iterative research cycles with time budgets
- **Session management** — browse and manage research sessions

## Features

### RenderedMarkdown Widget
Rich text rendering with:
- Stripped markdown syntax for clean display
- Embedded code blocks as syntax-highlighted widgets
- Tables rendered as Treeview widgets
- Clickable links
- Collapsible thinking blocks (for LLM reasoning)

### LLM Streaming
Live token rendering via Server-Sent Events (SSE). Watch the LLM generate responses in real-time with thinking blocks that can be expanded/collapsed.

### Preferences Dialog
Configure endpoints and behaviour:
- Embedding endpoint URL and model
- LLM endpoint URL and model
- Presets for LM Studio, BobAI, and custom endpoints
- Test Connection button to verify endpoints

### Keyboard Shortcuts
- **Ctrl+F** — focus search bar
- **Ctrl+I** — index current collection
- **Ctrl+Q** — quit
- **Ctrl+T** — toggle theme (dark/light)

## Configuration

The GUI reads from the same `.mini-rag/config.yaml` as the CLI. Changes made in the Preferences dialog are saved to `~/.config/fss-mini-rag/gui_config.json`.

## Architecture

The GUI uses a modular component architecture:

```
mini_rag/gui/
  app.py                    — main application window
  config_store.py           — GUI-specific settings persistence
  tooltip.py                — tooltip widget
  components/
    search_bar.py           — search input with options
    results_table.py        — ranked results display
    content_panel.py        — content viewer with RenderedMarkdown
    collection_panel.py     — project/collection browser
    status_bar.py           — status and progress display
    rendered_markdown.py    — rich markdown rendering widget
    research_tab.py         — web research tab
  dialogs/
    about.py                — about dialog
    preferences.py          — endpoint configuration
  services/
    research.py             — web research service layer
    streaming.py            — SSE streaming for LLM responses
```

Components communicate via an **EventBus** for decoupled messaging.

## CLI Alternative

Everything the GUI does is also available from the command line:

```bash
rag-mini init                              # Index current directory
rag-mini search "query" --synthesize       # Search with LLM synthesis
rag-mini scrape https://example.com        # Scrape a URL
rag-mini research "topic" --deep --time 1h # Deep research
rag-mini status                            # System status
```

See the [main README](../README.md) for the full CLI command reference.
