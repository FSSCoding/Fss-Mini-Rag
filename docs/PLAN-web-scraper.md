# PLAN: Web Scraper & Research Engine Integration

**Status:** Planning — awaiting approval to build
**Version target:** v2.2.0 (core), v2.2.x (extras), v2.3.0 (deep research)
**Date:** 2026-03-23
**Ref spec:** Obsidian `SPEC-Mini-RAG-Web-Scraper-Integration.md`

---

## Vision

Mini RAG becomes a research tool. Users can search the web, scrape content, convert it to clean markdown, index it, and explore it — all from one CLI. The deep research mode runs unattended: search, scrape, index, reason, search again, building a corpus over hours.

This is not a high-performance scraper. It's a slow, thorough, respectful research engine that a user starts before work and comes home to a curated knowledge base.

---

## Architecture

### Layer stack

```
CLI commands
  scrape          — fetch URLs, extract, save
  search-web      — search engine + scrape results
  research        — full pipeline: search → scrape → index → explore
  research --deep — iterative: search → scrape → index → reason → repeat
     |
ResearchSession              ← session state, iteration, decision-making
     |
MiniWebScraper               ← fetch, extract, convert
  /        |          \
Fetcher   Extractors   Search Engines
```

### Fetcher — two tiers

| Tier | Tech | When |
|------|------|------|
| **1 (default)** | `requests` + lightweight JS response handling | Always available. Handles static HTML. Detects/closes simple JS blockers (confirmation dialogs, cookie walls). No full JS rendering. |
| **2 (optional)** | Playwright headless | Install on demand: `rag-mini research --install-browser`. Used when Tier 1 fails or for known JS-heavy domains. Pre-configured with sensible defaults so it works for anyone out of the box. |

If Tier 2 is not installed and a page requires it, show a clear message:
"This page requires browser rendering. Install with: rag-mini research --install-browser"

No Selenium. No requests-html. No cloudscraper. Two clean tiers.

### Search engines

| Engine | API key | Status |
|--------|---------|--------|
| **DuckDuckGo** | None | Default. `duckduckgo-search` package + direct HTML scraping fallback. |
| **Tavily** | Required | Planned. User has working integration in fss-webscraper. |
| **Brave** | Required | Planned. User has working integration in fss-webscraper + fss-link. |

All engines implement the same interface:
```python
class SearchEngine(Protocol):
    def search(self, query: str, max_results: int) -> List[WebSearchResult]
```

Config selects the engine. Factory instantiates it.

### Content extractors

| Extractor | Handles | Priority |
|-----------|---------|----------|
| **ArxivExtractor** | arxiv.org — paper abstracts, metadata, PDF links | v2.2.0 |
| **GitHubExtractor** | github.com — READMEs, code, repo metadata | v2.2.0 |
| **PDFExtractor** | Any PDF (content-type or URL) via pymupdf | v2.2.0 |
| **GenericExtractor** | Everything else — bs4 strip nav/footer/scripts | v2.2.0 |
| **Additional domains** | Research sites, wikis, documentation | v2.2.x |

Extractor selection:
1. Check URL against domain extractors (`can_handle(url, content_type)`)
2. Check content-type for PDF → PDFExtractor
3. Fall back to GenericExtractor

### PDF handling

**Not optional.** `pymupdf` (~15MB) is a default dependency. Extracts text with layout from research papers, converts to clean markdown.

User has a superior PDF parser that may become an installable extra later. The pymupdf default is the baseline.

### Output — session directories

```
{project}/mini-research/
  2026-03-23-quantum-gravity/
    session.json                    ← query, URLs visited, status, timestamps
    quantum-gravity-holographic.md  ← scraped content as markdown
    arxiv-2405-07987.md
    proton-charge-radius.md
  2026-03-24-floquet-states/
    session.json
    ...
```

**Why `mini-research/`:** Can't use `research/` (would collide with user folders). Can't use `.mini-rag/research/` (indexer excludes `.mini-rag/`). `mini-research/` is distinctive, unlikely to collide, and the indexer picks it up automatically.

**Session metadata (`session.json`):**
```json
{
  "query": "quantum vacuum fluctuations proton structure",
  "created": "2026-03-23T09:00:00",
  "status": "complete",
  "engine": "duckduckgo",
  "urls_visited": ["https://..."],
  "pages_scraped": 8,
  "rounds": 1,
  "deep_research": false
}
```

**User management:**
- List sessions: `rag-mini research --list`
- Open folder: `rag-mini research --open <session-name>`
- Delete session: `rag-mini research --delete <session-name>`
- Continue/extend: `rag-mini research --continue <session-name> "additional query"`
- GUI shows sessions as browsable collections

### Markdown output format

Each scraped page saved with BOBAI-compatible frontmatter:
```markdown
---
profile: scraped
generator: "fss-mini-rag-scraper"
title: "Paper Title"
source_url: "https://..."
scraped_at: "2026-03-23T09:15:00"
word_count: 2450
content_quality: 1.0
---

# Paper Title

[clean markdown content]

---
*Source: [url](url) — scraped 2026-03-23*
```

Filename: `slugified-title.md` (within session directory).

### Config additions

```python
@dataclass
class WebScraperConfig:
    enabled: bool = True
    output_dir: str = "mini-research"       # Relative to project path
    max_pages: int = 20                     # Per session hard limit
    max_depth: int = 1                      # Link following depth
    timeout: int = 15                       # Per-request seconds
    min_content_length: int = 200           # Skip thin pages
    respect_robots: bool = True             # Honour robots.txt
    delay_between_requests: float = 1.0     # Rate limiting
    user_agent: str = "FSS-Mini-RAG-Research/2.2"

@dataclass
class SearchEngineConfig:
    engine: str = "duckduckgo"              # "duckduckgo", "tavily", "brave"
    max_results: int = 10
    tavily_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None

@dataclass
class DeepResearchConfig:
    enabled: bool = False
    max_rounds: int = 5                     # Maximum search→scrape→reason cycles
    max_time_minutes: int = 60              # Time budget (0 = unlimited, use max_rounds)
    max_total_pages: int = 100              # Hard cap across all rounds
    checkpoint_interval: int = 1            # Save state every N rounds
    prune_threshold: float = 0.3            # Similarity threshold for fuzzy dedup
    roundup_buffer_minutes: int = 5         # Start final roundup this many minutes before deadline
```

All wired into `RAGConfig` alongside existing config sections.

### Compliance

- `respect_robots: bool = True` — parse and honour robots.txt by default
- Rate limiting via `delay_between_requests` — minimum 1 second between requests
- Identifiable user agent string
- Max pages hard cap prevents runaway crawls
- Deep research has its own `max_total_pages` cap

---

## CLI commands

### `rag-mini scrape`
```
rag-mini scrape URL [URL...] [OPTIONS]
  --depth N          Follow links N levels (default: 0)
  --max-pages N      Page limit (default: 20)
  --output DIR       Override output directory
  --timeout N        Per-request seconds (default: 15)
  --index            Auto-index after scraping
  --name NAME        Session name (default: auto from date + query/URL)
```

### `rag-mini search-web`
```
rag-mini search-web QUERY [OPTIONS]
  --engine ENGINE    Search engine: duckduckgo|tavily|brave
  --max-results N    Search results to scrape (default: 5)
  --depth N          Follow links from results (default: 0)
  --max-pages N      Total page limit (default: 20)
  --index            Auto-index after scraping
  --name NAME        Session name
```

### `rag-mini research`
```
rag-mini research QUERY [OPTIONS]
  Full pipeline: search → scrape → index → explore

  --deep             Enable deep research (iterative, long-running)
  --max-rounds N     Deep research iteration limit (default: 5)
  --engine ENGINE    Search engine
  --max-pages N      Total page limit
  --list             List existing research sessions
  --open NAME        Open session folder in file manager
  --delete NAME      Delete a research session
  --continue NAME    Add to existing session with new query
  --install-browser  Install Playwright for JS-heavy sites
```

### `rag-mini research --deep` (v2.3.0)

Long-running unattended research with time budget and agent phases.

**Time budget:** User sets max duration (e.g. `--time 1h`, `--time 100h`). The agent
tracks elapsed time per round. When remaining time drops below one round's estimated
duration, it triggers the final roundup — review, prune, organize, report. Never
overshoots the timer. If someone sets 1 hour, it finishes in under 1 hour.

**Three-bucket session directory:**
```
{session}/
  sources/       ← downloaded web pages, PDFs (NEVER modified by agent except dedup)
  notes/         ← user's own files they bring to the session
  agent-notes/   ← AI-generated analysis, gap reports, summaries, session docs
  session.json   ← metadata, timing, stats
```
These buckets must never be mixed. Source integrity is paramount.

**Agent phases (explicit state machine):**

| Phase | What happens |
|-------|-------------|
| **ANALYZE** | Index the session folder. Search the collection. Understand content deeply. Identify gaps. Write analysis to `agent-notes/`. Can start here with existing folder (no web search needed). |
| **SEARCH** | Use identified gaps to generate web search queries via LLM. Execute searches. |
| **SCRAPE** | Fetch and extract content from search results. Save to `sources/`. Deduplicate against existing sources (fuzzy matching, not just character comparison). |
| **PRUNE** | Evaluate sources for consistency. Same info in 3+ sources = stronger evidence (keep all, note corroboration). True duplicates removed. Low-relevance content flagged but NOT deleted. |
| **REPORT** | Generate session report: searches performed, pages found/pulled/pruned, token counts (chars/4), gaps remaining, confidence assessment. Save to `agent-notes/`. |

**Cycle:** ANALYZE → SEARCH → SCRAPE → ANALYZE → PRUNE → REPORT → (repeat or finish)

The ANALYZE phase can run standalone — user points at an existing folder, agent indexes
it, evaluates what's there, identifies gaps. Web search is a separate trigger that kicks
in when the user opts for it or `--deep` is active.

**Pruning subsystem:**
- Fuzzy deduplication (semantic similarity, not just character matching)
- Cross-source consistency checking (corroboration = evidence strength)
- Never deletes sources unless truly duplicate content
- Inconsistencies flagged in agent-notes, not silently resolved

**Session report on completion:**
- Total searches, pages found, pages scraped, pages pruned
- Token count estimate (chars/4)
- Gaps remaining vs gaps filled
- Confidence assessment per topic area
- Time spent per phase

---

## New files

| File | Purpose |
|------|---------|
| `mini_rag/web_scraper.py` | MiniWebScraper, Fetcher, session management |
| `mini_rag/extractors.py` | ContentExtractor protocol, ArxivExtractor, GitHubExtractor, PDFExtractor, GenericExtractor |
| `mini_rag/search_engines.py` | SearchEngine protocol, DuckDuckGoSearch, TavilySearch, BraveSearch |
| `mini_rag/research_session.py` | ResearchSession state machine, deep research loop |

## Modified files

| File | Change |
|------|--------|
| `mini_rag/config.py` | Add WebScraperConfig, SearchEngineConfig, DeepResearchConfig to RAGConfig |
| `mini_rag/cli.py` | Add `scrape`, `search-web`, `research` commands. Extract reusable `index_project()` |
| `requirements.txt` | Add `beautifulsoup4`, `duckduckgo-search`, `pymupdf` |
| `pyproject.toml` | Bump to 2.2.0, add deps, add `[web]` optional extra for Playwright |

## Unchanged

Indexer, search, explorer, embeddings, chunker, synthesizer, server, watcher — all untouched. The scraper is purely additive. Indexer picks up `mini-research/` markdown automatically.

---

## Dependencies

### Required (added to default install)
```
beautifulsoup4      # HTML parsing, ~300KB
duckduckgo-search   # Web search, no API key, ~50KB
pymupdf             # PDF extraction, ~15MB
```

### Optional extras
```
# pip install fss-mini-rag[browser]
playwright          # JS rendering, install-on-demand ~50MB
```

---

## Build phases

### v2.2.0 — Core research pipeline

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| 1 | Config: `WebScraperConfig`, `SearchEngineConfig` in config.py | — |
| 2 | `extractors.py`: GenericExtractor (bs4), PDFExtractor (pymupdf) | — |
| 3 | `web_scraper.py`: Fetcher (requests tier-1), session directory management | Phase 2 |
| 4 | `search_engines.py`: DuckDuckGoSearch + HTML fallback | — |
| 5 | CLI: `scrape` command | Phase 3 |
| 6 | CLI: `search-web` command | Phase 3, 4 |
| 7 | Extract reusable `index_project()` from cli.py | — |
| 8 | CLI: `research` command (single-round pipeline) | Phase 5-7 |
| 9 | Domain extractors: ArxivExtractor, GitHubExtractor | Phase 2 |

### v2.2.x — Capability expansion

| Phase | Deliverable |
|-------|-------------|
| 10 | Playwright tier-2 fetcher + `--install-browser` |
| ~~11~~ | ~~Tavily + Brave search engines~~ — **DONE** (shipped in phases 1-4) |
| 12 | Lightweight JS response handling (blocker detection, cookie walls) |
| 13 | Additional domain extractors |
| 14 | Session management CLI: `--list`, `--open`, `--delete`, `--continue` |

### v2.3.0 — Deep research engine

Three-bucket directory structure, agent phase state machine, time-budgeted research.

| Phase | Deliverable |
|-------|-------------|
| 15 | Three-bucket session directory: `sources/`, `notes/`, `agent-notes/` |
| 16 | Agent phase state machine: ANALYZE → SEARCH → SCRAPE → PRUNE → REPORT |
| 17 | Time budget tracking: elapsed time per round, deadline-aware roundup |
| 18 | ANALYZE phase: index folder, search collection, understand content, find gaps |
| 19 | LLM gap analysis + follow-up query generation (uses built-in LLM) |
| 20 | SCRAPE phase with fuzzy dedup against existing sources |
| 21 | PRUNE phase: cross-source consistency, corroboration detection, duplicate removal |
| 22 | REPORT phase: session stats, token counts (chars/4), gaps remaining, confidence |
| 23 | `research --deep` command with `--time` flag |
| 24 | `research --analyze` — start from existing folder without web search |

---

## Open decisions

1. **GUI integration** — How does the GUI show/manage research sessions? Needs scoping once the CLI pipeline works.
2. **User data directory** — GUI may need a central user data directory for sessions that aren't project-specific. Not yet determined where this lives.
3. **Domain extractor priority** — Which research sites beyond arXiv and GitHub get custom extractors in v2.2.0?
4. **Setup wizard** — Install scripts should ask about optional deps (browser, API keys). Design TBD.
5. **User's superior PDF parser** — What is it and when does it get integrated as an extra?
6. **Fuzzy dedup patterns** — User has existing tools for this. Need to review and port.
7. **LLM prompt design** — Gap analysis and self-assessment prompts need careful crafting to keep agent on-workflow.
