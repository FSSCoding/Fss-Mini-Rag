# Web Search and Research Guide

> **Turn the web into a searchable knowledge base**
> *Search, scrape, index, and explore — from one command*

## Quick Start

```bash
# Scrape a URL and make it searchable
rag-mini scrape https://arxiv.org/pdf/2405.07987 --index

# Search the web and scrape results
rag-mini search-web "quantum gravity holographic mass" --engine brave

# Full pipeline: search → scrape → index (one command)
rag-mini research "proton structure quantum chromodynamics" --engine tavily

# Deep research: iterative cycles with LLM analysis
rag-mini research "quantum vacuum fluctuations" --deep --time 1h
```

---

## Three Commands

### `rag-mini scrape` — Fetch specific URLs

Scrape one or more URLs and save as clean, searchable markdown.

```bash
# Single URL
rag-mini scrape https://docs.python.org/3/library/json.html

# Multiple URLs
rag-mini scrape https://site1.com https://site2.com https://site3.com

# Follow links one level deep
rag-mini scrape https://arxiv.org/abs/2405.07987 --depth 1

# Scrape and auto-index for immediate searching
rag-mini scrape https://arxiv.org/pdf/2405.07987 --index

# Custom session name
rag-mini scrape https://example.com --name my-research
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--path` | `-p` | Project path (default: current directory) |
| `--depth` | `-d` | Follow links N levels deep (default: 0) |
| `--max-pages` | `-m` | Maximum pages to scrape |
| `--timeout` | | Per-request timeout in seconds |
| `--index` | `-i` | Auto-run indexing after scraping |
| `--name` | `-n` | Session name (default: auto from URL) |

### `rag-mini search-web` — Search and scrape

Search the web using DuckDuckGo, Tavily, or Brave, then scrape the top results.

```bash
# Default engine (DuckDuckGo, no API key needed)
rag-mini search-web "python web scraping tutorial"

# Use Tavily (better results, needs API key)
rag-mini search-web "quantum gravity" --engine tavily

# Use Brave (good results, needs API key)
rag-mini search-web "Nassim Haramein" --engine brave --max-results 10

# Search, scrape, and index in one go
rag-mini search-web "proton charge radius" --engine tavily --index
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--engine` | `-e` | Search engine: `duckduckgo`, `tavily`, `brave` |
| `--max-results` | `-r` | Number of search results to scrape |
| `--depth` | `-d` | Follow links from results |
| `--max-pages` | `-m` | Total page limit |
| `--index` | `-i` | Auto-index after scraping |
| `--name` | `-n` | Session name |

### `rag-mini research` — Full pipeline

The power command. Searches the web, scrapes results, indexes everything, and makes it searchable — all in one step.

```bash
# Single-round research
rag-mini research "quantum vacuum fluctuations"

# With specific engine
rag-mini research "Nassim Haramein holographic mass" --engine tavily

# Deep research: iterative analysis with LLM
rag-mini research "proton structure" --deep --rounds 5

# Time-budgeted deep research
rag-mini research "quantum gravity" --deep --time 2h

# Analyze existing corpus only (no web search)
rag-mini research "my topic" --analyze
```

**Options:**

| Flag | Description |
|------|-------------|
| `--engine` | Search engine: `duckduckgo`, `tavily`, `brave` |
| `--max-pages` | Total page limit |
| `--deep` | Enable iterative deep research with LLM analysis |
| `--time` | Time budget for deep research (e.g. `30m`, `1h`, `100h`) |
| `--rounds` | Maximum research cycles for `--deep` |
| `--analyze` | Analyze existing corpus only — no web search |

**Session management:**

| Flag | Description |
|------|-------------|
| `--list` | List all research sessions |
| `--open NAME` | Open session folder in file manager |
| `--delete NAME` | Delete a research session |

```bash
# List all sessions
rag-mini research --list

# Open a session folder
rag-mini research --open 2026-03-23-quantum-gravity

# Delete a session
rag-mini research --delete 2026-03-23-old-research
```

---

## Deep Research

Deep research runs iterative cycles where an LLM analyzes your corpus, identifies gaps, generates targeted search queries, and builds a comprehensive knowledge base over time.

### How it works

```
Round 1:
  ANALYZE  → LLM reads corpus, identifies what's covered and what's missing
  SEARCH   → LLM generates targeted queries to fill gaps
  SCRAPE   → Fetch and extract content from search results

Round 2:
  ANALYZE  → LLM re-evaluates with new content, finds remaining gaps
  SEARCH   → New queries targeting unfilled gaps
  SCRAPE   → More content added to corpus
  PRUNE    → Remove duplicates, detect corroborated findings

Round N:
  ...repeats until confidence is HIGH, time expires, or rounds exhausted...

Final:
  REPORT   → Comprehensive stats, gap assessment, confidence evaluation
```

### Agent phases

| Phase | What happens |
|-------|-------------|
| **ANALYZE** | Index the session, search the collection, LLM evaluates coverage and identifies gaps |
| **SEARCH** | LLM generates follow-up queries from identified gaps |
| **SCRAPE** | Fetch search results, extract content, save to `sources/` |
| **PRUNE** | Fuzzy deduplication, cross-source consistency checking |
| **REPORT** | Generate session stats, confidence assessment, gap report |

### Time budgets

Set a time limit and the engine will manage its own schedule:

```bash
# Run for 30 minutes
rag-mini research "topic" --deep --time 30m

# Run for 2 hours
rag-mini research "topic" --deep --time 2h

# Run for a full work day
rag-mini research "topic" --deep --time 8h
```

The engine tracks how long each round takes and starts a final roundup before the deadline. It never overshoots — if you set 1 hour, it finishes within 1 hour.

### Analyze mode

Point deep research at an existing corpus without doing any web search:

```bash
rag-mini research "my research topic" --analyze
```

This indexes whatever is already in the session directory, runs LLM analysis to identify what's covered and what's missing, and saves a gap report. Useful for evaluating material you already have before deciding whether to search for more.

---

## Session directories

Each research run creates a session directory under `mini-research/`:

```
mini-research/
  2026-03-23-quantum-gravity/
    sources/           ← Downloaded web pages and PDFs
    notes/             ← Your own files (add anything here)
    agent-notes/       ← AI-generated analysis and reports
    session.json       ← Session metadata
    metrics.json       ← Detailed analytics
```

### Three buckets

| Directory | Contents | Rules |
|-----------|----------|-------|
| `sources/` | Scraped web pages, PDFs | Never modified by the agent except dedup removal |
| `notes/` | Your own files | Bring your own documents — the agent reads but never touches |
| `agent-notes/` | AI analysis, gap reports, session reports | Generated by the research engine |

These buckets are never mixed. Source integrity is maintained — the agent writes its own observations separately from downloaded material.

### What gets generated

After a deep research session, `agent-notes/` contains:

- `analysis-round-1.md` — Per-round gap analysis (covered topics, gaps, queries)
- `analysis-round-2.md` — ...
- `corpus-assessment.md` — Full prose assessment of the corpus
- `research-report.md` — Comprehensive stats and findings

### Session metadata

`session.json` tracks:
- Query, engine, status
- URLs visited (for deduplication)
- Pages scraped, pages pruned
- Current research phase
- Time elapsed

`metrics.json` tracks (deep research only):
- Per-file registry with character/word/token counts
- Per-round snapshots with timing and stats
- LLM call counts, token usage, failure rates
- Scrape success rates by domain
- Corpus growth curve
- Confidence trend across rounds

---

## Search engines

### DuckDuckGo (default)

No API key required. Works out of the box.

```bash
rag-mini search-web "python tutorial"
```

Uses the `duckduckgo-search` package with a direct HTML scraping fallback. Rate limited to 10 queries/minute. Note: DuckDuckGo can be aggressive with CAPTCHAs from some IPs.

### Tavily

Excellent result quality for research topics. Requires an API key.

1. Sign up at [tavily.com](https://tavily.com)
2. Add your key to `.env`:
   ```
   TAVILY_API_KEY=tvly-your-key-here
   ```
3. Use it:
   ```bash
   rag-mini search-web "quantum gravity" --engine tavily
   ```

Rate limited to 30 queries/minute with automatic retry on rate limit errors.

### Brave

Good general-purpose search. Requires an API key.

1. Sign up at [brave.com/search/api](https://brave.com/search/api/)
2. Add your key to `.env`:
   ```
   BRAVE_API_KEY=BSA-your-key-here
   ```
3. Use it:
   ```bash
   rag-mini search-web "proton structure" --engine brave
   ```

Rate limited to 15 queries/minute with automatic retry on 429 errors.

### API keys in `.env`

Create a `.env` file in your project root (it's already in `.gitignore`):

```bash
# FSS-Mini-RAG API Keys
# This file is in .gitignore — never committed

# Tavily Search API
TAVILY_API_KEY=tvly-your-key-here

# Brave Search API
BRAVE_API_KEY=BSA-your-key-here
```

Keys can also be set in the YAML config under `search_engine:`.

---

## Content extractors

The scraper automatically uses the best extractor for each URL:

| Extractor | Domains | What it extracts |
|-----------|---------|-----------------|
| **ArxivExtractor** | arxiv.org | Paper title, authors, abstract, subjects, date, PDF link |
| **GitHubExtractor** | github.com | README content, repo description, topics |
| **PDFExtractor** | Any `.pdf` URL or `application/pdf` | Full text extraction via pymupdf |
| **GenericExtractor** | Everything else | Main content area, headings, code blocks, tables, links |

### PDF support

PDF extraction is built-in (not optional). Research papers from arXiv, journals, and other sources are automatically detected and converted to clean markdown.

```bash
# Direct PDF URL — automatically extracted
rag-mini scrape https://arxiv.org/pdf/2405.07987

# arXiv abstract page — extracts metadata + links to PDF
rag-mini scrape https://arxiv.org/abs/2405.07987
```

### Output format

Every scraped page is saved as markdown with BOBAI-compatible frontmatter:

```markdown
---
profile: scraped
generator: "fss-mini-rag-scraper"
title: "Paper Title"
source_url: "https://..."
scraped_at: "2026-03-23T09:15:00"
word_count: 2450
source_type: "arxiv"
content_quality: 1.0
---

# Paper Title

[clean markdown content]

---
*Source: [url](url) — scraped 2026-03-23*
```

---

## Rate limiting

All API calls are rate-limited and retry on transient errors. This runs unattended for hours without hitting rate limits or crashing on temporary failures.

| Service | Rate limit | Retry | Backoff |
|---------|-----------|-------|---------|
| DuckDuckGo | 10/min | 2 retries | 5s → 30s |
| Tavily | 30/min | 3 retries | 2s → 30s |
| Brave | 15/min | 3 retries | 2s → 30s |
| LLM | 30/min | 2 retries | 1s → 15s |
| Web scraper | From config `delay_between_requests` | 2 retries | 2s → 20s |

Rate limiters are shared across the entire session — if deep research fires 5 Brave queries in one round, they're automatically spaced to stay within limits. `Retry-After` headers from APIs are respected.

### robots.txt

Web scraping respects `robots.txt` by default. Sites that disallow scraping are skipped with a log message. This can be configured:

```yaml
web_scraper:
  respect_robots: true   # Honour robots.txt (default)
  delay_between_requests: 1.0  # Seconds between requests
```

---

## Configuration

All settings are in `.mini-rag/config.yaml`. The web scraper adds these sections:

### Web scraper settings

```yaml
web_scraper:
  enabled: true
  output_dir: mini-research    # Session output directory
  max_pages: 20                # Per session page limit
  max_depth: 1                 # Link following depth
  timeout: 15                  # Per-request timeout seconds
  min_content_length: 200      # Skip pages with less content
  respect_robots: true         # Honour robots.txt
  delay_between_requests: 1.0  # Rate limiting (seconds)
```

### Search engine settings

```yaml
search_engine:
  engine: duckduckgo    # Default engine: duckduckgo, tavily, brave
  max_results: 10       # Results per search
  # tavily_api_key: null  # Or set in .env
  # brave_api_key: null   # Or set in .env
```

### Deep research settings

```yaml
deep_research:
  enabled: false
  max_rounds: 5                 # Maximum research cycles
  max_time_minutes: 60          # Time budget (0 = unlimited)
  max_total_pages: 100          # Hard cap across all rounds
  checkpoint_interval: 1        # Save state every N rounds
  prune_threshold: 0.3          # Similarity threshold for dedup
  roundup_buffer_minutes: 5     # Start final roundup before deadline
```

---

## Metrics and analytics

Deep research sessions produce detailed metrics in `metrics.json`:

### File registry

Every file tracked with: path, URL, title, character count, word count, token estimate, source type, round added, relevance score, pruning status.

### Per-round snapshots

Each round records: duration, time per phase, pages attempted vs scraped, characters/tokens added, queries used, confidence level, LLM calls/failures/tokens, scrape success by domain.

### Decision intelligence

The engine uses metrics to make smarter decisions:

- **Stalling detection** — if the last 2 rounds added minimal new content, the research topic may be exhausted
- **Domain skipping** — domains that consistently fail (403s, timeouts) are automatically skipped in future rounds
- **Growth tracking** — cumulative token curve shows if research is productive or plateauing
- **Confidence trend** — tracks LOW → MEDIUM → HIGH progression across rounds

### Example metrics output

```
Rounds: 3
Time: 4.2 min
Sources: 8 (1 pruned)
Tokens: ~45,000
LLM calls: 3 (0 failed)
Scrape rate: 45%
Failing domains: journals.aps.org
Growth: 12000 → 18000 → 5000 tokens/round
Confidence: MEDIUM
Trend: LOW → LOW → MEDIUM
```

---

## Typical workflows

### Research a new topic

```bash
# Start with a broad search
rag-mini research "quantum vacuum fluctuations proton structure" --engine tavily

# Results are indexed — search immediately
rag-mini search "proton radius"

# Want more depth? Run deep research
rag-mini research "quantum vacuum fluctuations proton structure" --deep --rounds 5
```

### Build a knowledge base overnight

```bash
# Set a time budget and walk away
rag-mini research "holographic principle black hole information" --deep --time 8h --engine brave
```

### Scrape specific sources

```bash
# Scrape a collection of known URLs
rag-mini scrape \
  https://arxiv.org/abs/2405.07987 \
  https://arxiv.org/pdf/2301.12345 \
  https://github.com/user/repo \
  --index --name arxiv-papers
```

### Analyze existing material

```bash
# Put your documents in the session's notes/ folder
cp my-papers/*.pdf mini-research/2026-03-23-my-topic/notes/

# Analyze what you have and find gaps
rag-mini research "my topic" --analyze
```

### Manage sessions

```bash
# See all research sessions
rag-mini research --list

# Open a session folder to browse files
rag-mini research --open 2026-03-23-quantum-gravity

# Clean up old sessions
rag-mini research --delete 2026-03-23-old-stuff
```

---

## Troubleshooting

### No search results (DuckDuckGo)

DuckDuckGo can be aggressive with CAPTCHAs from some IPs. Solutions:
- Use `--engine tavily` or `--engine brave` (API-based, more reliable)
- Wait and try again later
- The HTML fallback triggers automatically when the package fails

### SSL errors

If you see `CERTIFICATE_VERIFY_FAILED`, the scraper auto-detects system CA bundles. If that fails:
```bash
# Set in .env
REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

### 403 errors on academic sites

Many journal sites (aps.org, nature.com, sciencedirect.com) block automated access. The scraper handles this gracefully — it logs the failure, the metrics track failing domains, and deep research automatically skips domains that consistently fail.

For academic content, arXiv works well (both abstract pages and PDFs).

### LLM not responding

Deep research needs an LLM for gap analysis. Check:
- Is your LLM endpoint running? (configured in `.mini-rag/config.yaml` under `embedding.base_url` or `llm.api_base`)
- The engine degrades gracefully — without LLM, it falls back to using the original query for each round

### Rate limit errors

All API calls include automatic retry with exponential backoff. If you're still hitting limits:
- Reduce `search_engine.max_results` in config
- Increase `web_scraper.delay_between_requests`
- Use `--rounds` to limit deep research cycles
