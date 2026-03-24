# FSS-Mini-RAG: The Project Story

## Origins — The Lightweight Sibling (August 12, 2025)

FSS-Mini-RAG was born in a single day. On August 12, 2025, Brett Fox committed 22 times in what was clearly a planned sprint — the project went from zero to a working semantic code search system in under 24 hours. The initial commit message set the tone: *"Initial release: FSS-Mini-RAG - Lightweight semantic code search system."*

But Mini RAG didn't appear in a vacuum. It was the lightweight extraction of something much larger.

Brett had been building **FSS-RAG** — a sprawling, industrial-strength retrieval-augmented generation system that grew to 38,000+ indexed chunks across 57 collections, with multi-index search (semantic, BM25, B-Tree, AST), knowledge graphs, query archetype learning, and parsers for every document format imaginable. That system is documented in a 110-page manifesto. It's the backbone of Brett's entire AI infrastructure.

Mini RAG was the answer to a simpler question: *what if someone just has files and wants AI to understand them?*

The initial architecture was modest by FSS-RAG standards:
- Python chunker with function/class/markdown awareness
- Ollama embeddings (localhost, no API keys)
- LanceDB vector storage
- BM25 keyword search
- LLM synthesis via Ollama
- CLI interface (`rag-mini search`, `rag-mini index`)
- A simple terminal TUI for interactive exploration

The day-one burst also included LLM safeguards, query expansion, CPU deployment support, and beginner-friendly documentation. The whole system was designed to be educational — comments explained *why*, not just *what*.

---

## The First Sprint — Polishing for Public (August 12–September 7, 2025)

The first month saw 67 commits across three intense periods:

**August 12–16 (50 commits):** The core sprint. LLM synthesis, query expansion, smart ranking, Windows compatibility, streaming tokens, context window configuration, auto-update system, GitHub Actions CI. Three different contributors touched the code (FSSCoding, BobAi agents, fss-code-server). This was a full-stack push to make the system installable and usable.

**August 26–September 3 (6 commits):** Cleanup and hardening. Unicode emoji fixes for Windows CI, code quality improvements, security hardening (command injection fix), model resolution improvements.

**September 6–7 (11 commits):** The installation saga. Five commits in one day trying to fix `pip install` in externally-managed Python environments. Virtual environment activation, global command wrappers, path detection. The last commits were PyPI launch preparation and distribution packaging.

Then silence.

---

## The Stagnation — 6.5 Months of Nothing (September 2025 – March 2026)

From September 7, 2025 to March 21, 2026 — **zero commits**. The project sat frozen with:

- An installation flow that barely worked
- Ollama-only embeddings (no OpenAI-compatible endpoints)
- BM25 search that was trapped inside the vector search shortlist (only scored chunks already returned by semantic search — defeating the entire purpose of hybrid search)
- A chunker using line counts instead of character counts, producing wildly inconsistent chunk sizes
- Hash embeddings (SHA-256 vectors) shipped as a feature despite being mathematically worse than random
- No GUI
- No web scraping
- Broken installer scripts with hardcoded paths
- Stale documentation referencing deleted files

The system worked in the narrowest sense — you could index a folder and search it from the terminal. But it was fragile, limited to Ollama users, and the search quality was mediocre because the hybrid search architecture was fundamentally flawed.

There were better systems out there. And honestly, nobody wanted to use this one. The few people who encountered it didn't know how to use it — a terminal-only tool is a hard sell for anyone who isn't already comfortable in a shell. The installation barely worked, the search quality wasn't competitive, and there was no compelling reason to choose Mini RAG over established alternatives.

The stagnation wasn't laziness — it was pragmatism. Brett had been building the larger FSS-RAG ecosystem for his own needs, and that system was going well. The big RAG system had everything: multi-index search, knowledge graphs, query learning, parsers for every format. Mini RAG was a side project born from the idea that someone else might benefit from a lighter version. When nobody did, the honest reaction was: *to hell with it — what do I actually need?* And what he needed was the big system. So that's where the work went.

---

## The Catalyst — Jason (March 2026)

The revival started with a person, not a technical decision.

In late 2025, Brett met Jason — a philosopher and independent researcher studying quantum biology, consciousness, and "true nature" physics. Jason works on a Windows laptop with an RTX 4050 (6GB VRAM), runs LM Studio for local LLMs, and uses Obsidian for knowledge management. He's not a developer. His pain point: web search integration is fragile, LangChain/Node.js error loops, and no clean way to scrape research, index it locally, and query it with AI.

Jason became the first test case — and the forcing function. As Brett's Obsidian vault documents:

> *"If it works for a non-developer researching fringe physics on a 6GB VRAM laptop, it works for anyone."*

The vision crystallised: Mini RAG needed to become a **self-contained research tool** — scrape the web, index content, search semantically, and ask questions, all running locally with no cloud dependencies. A single installable package that bridges the gap between "I have files" and "AI understands them."

---

## The Revival — 54 Commits in 3 Days (March 21–23, 2026)

On March 21, 2026, the project restarted with the kind of intensity that characterised its birth. 54 commits in 3 days — nearly matching the entire first month's 67.

### Day 1 — March 21: The Overhaul (24 commits)

The first day was demolition and reconstruction:

1. **Cleanup:** Removed noise files, fixed lsof typo that had been silently breaking port cleanup, pinned dependency versions, fixed all stale references to deleted files.

2. **Chunker rewrite:** Switched from line-based to character-based sizing. Paragraph-based markdown splitting. Section boundary preservation. File overview chunks (one per file listing all functions/classes).

3. **Search architecture rebuild:** The fundamental flaw — BM25 trapped in the vector shortlist — was fixed by adopting the pattern from FSS-RAG: independent dual-pipeline search (semantic and BM25 run against the full index separately) with Reciprocal Rank Fusion (RRF) to merge results. The formula: `score = sum(weight * 1/(k + rank))` across methods, k=60.

4. **Embedding system modernisation:** Replaced Ollama-only embeddings with OpenAI-compatible endpoints. Auto-detection of embedding and LLM models from running servers. LM Studio and vLLM work out of the box. MiniLM L6 v2 set as default.

5. **Hash embeddings removed:** The SHA-256 embedding mode — which produced vectors with zero semantic similarity — was deleted. A/B benchmarking confirmed MiniLM at 100% precision vs hash at near-random.

6. **Test suite:** 35 unit tests added. Synthetic test corpus created. End-to-end benchmarks with Jaccard scoring.

7. **README rewritten** to describe the system as it actually existed, not the aspirational version from August.

### Day 2 — March 22: GUI and Public Release (10 commits)

The desktop GUI arrived — a Tkinter application with Sun Valley dark theme:

- Modular component architecture: SearchBar, ResultsTable, ContentPanel, CollectionPanel, StatusBar
- EventBus for decoupled communication between components
- Cancellable indexing with live progress reporting
- LLM synthesis wired through configurable endpoints
- Preferences dialog with endpoint presets (LM Studio, BobAI)
- Dark/light theme toggle

The critical bug that nearly derailed everything: the `ProjectIndexer.__init__` body was silently detached by an indentation error, causing 2443 files to be indexed (no exclude patterns applied) instead of ~115. Fixed in a commit titled "CRITICAL FIX: Restore ProjectIndexer.__init__ body."

### Day 3 — March 23: Features, Research Engine, and Polish (20 commits)

The final day was feature-dense:

1. **Weighted RRF fusion** and algorithm documentation
2. **Complete GUI overhaul** — modular architecture with all features working
3. **BobAI custom endpoint support** — after two rounds of the endpoint being broken and Brett's fury at untested claims
4. **GUI integration tests** — verifying endpoint routing actually works
5. **Web scraper foundation** — extractors (HTML, PDF, arXiv, GitHub), search engines (DuckDuckGo with HTML fallback, Tavily, Brave), session management with 3-bucket directory structure (sources/, notes/, agent-notes/)
6. **Deep research engine** — iterative ANALYZE→SEARCH→SCRAPE→PRUNE→REPORT cycles with time budgeting, corpus pruning via trigram fuzzy dedup, LLM gap analysis, and comprehensive research reports
7. **GUI polish** — 12 items from issue tracking implemented
8. **Rate limiting and retry infrastructure** for all API calls
9. **RenderedMarkdown widget** — rich text rendering with stripped markdown syntax, embedded code blocks as syntax-highlighted widgets, tables as Treeview widgets, clickable links, collapsible thinking blocks
10. **LLM streaming** with live token rendering via SSE
11. **Web Research tab** — full ttk.Notebook integration with search, scrape, deep research, session management

---

## What FSS-Mini-RAG Is Now (v2.3.0)

A **self-contained local research system** with 19,380 lines of code across the core modules, GUI, and test suite.

### Core Engine (~10,400 lines)

| Module | Lines | Purpose |
|--------|-------|---------|
| `search.py` | 1,130 | Independent BM25 + semantic search with RRF fusion |
| `chunker.py` | 1,429 | Code-aware chunking with function/class/markdown/config parsers |
| `indexer.py` | 1,155 | Cancellable project indexing with progress, manifest tracking |
| `ollama_embeddings.py` | 777 | OpenAI-compatible embedding provider with auto-detection |
| `llm_synthesizer.py` | 1,133 | LLM synthesis with streaming SSE support |
| `cli.py` | 1,316 | Full CLI: index, search, info, gui, research |
| `config.py` | 668 | Dataclass config with YAML persistence |
| `deep_research.py` | 1,438 | Iterative deep research with time budgets and pruning |
| `extractors.py` | 696 | HTML/PDF/arXiv/GitHub content extraction |
| `web_scraper.py` | 396 | Rate-limited web fetcher with robots.txt compliance |
| `search_engines.py` | 285 | DuckDuckGo/Tavily/Brave search with unified interface |

### Desktop GUI (~1,500 lines)

Two-tab layout: **Search & Index** (semantic search, collections, LLM synthesis) and **Web Research** (web search, scraping, deep research, session management). Both use the RenderedMarkdown widget for rich content display. LLM streaming with live token rendering and collapsible thinking blocks.

### Test Suite (~4,000 lines)

Unit tests for chunker, search, LLM synthesis, GUI integration, and end-to-end benchmarks.

---

## What Can Be Done With It

### For Researchers (the Jason use case)
1. Point it at a folder of PDFs, papers, notes → index
2. Ask questions in natural language → get synthesised answers with source citations
3. Search the web for a topic → scrape pages → index locally → search and ask
4. Run deep research: set a topic and time budget → autonomous search/scrape/analyse cycles → comprehensive research report

### For Developers
1. Index a codebase → semantic search across functions, classes, modules
2. "How does authentication work?" → finds relevant code across all files
3. "Find all error handling patterns" → hybrid search catches both semantic and keyword matches
4. Ask mode synthesises answers from search results using local LLM

### For Anyone
- No cloud. No API keys required. Runs on LM Studio + local models.
- Works on 6GB VRAM laptops (MiniLM embeddings + Qwen 9B)
- Desktop GUI — no terminal knowledge needed
- Web research built in — search, scrape, read, index

---

## The Numbers

| Metric | Value |
|--------|-------|
| First commit | August 12, 2025 |
| Total commits | 121 |
| Total function changes tracked | 2,992 |
| Functions in codebase | 609 |
| Contributors | 1 human (Brett Fox), AI agents |
| Days with 20+ commits | 4 (Aug 12, Aug 15, Mar 21, Mar 23) |
| Longest gap | 195 days (Sep 7, 2025 → Mar 21, 2026) |
| Lines of code (core) | ~10,400 |
| Lines of code (GUI) | ~1,500 |
| Lines of code (tests) | ~4,000 |
| Hottest file | `search.py` (16 function-level changes) |
| Most fragile zone | `config.py` (14 changes, 2 authors) |

---

## The Bigger Picture — Why This Exists

Mini RAG isn't a standalone invention. The GUI, the web scraper, the deep research engine — these are all capabilities that Brett built as separate tools over the past two years. Each existed independently because that's how you develop tools properly: heavy dependencies stay isolated, tight coupling gets worked out in its own space, and each tool matures at its own pace without dragging others down.

### The Lineage

Mini RAG's March 2026 features trace back to five separate systems:

| Source | What It Contributed | Scale |
|--------|-------------------|-------|
| **FSS-RAG** (`Fss-Rag`) | Search architecture — independent BM25 + semantic pipelines, RRF fusion, query characteristic analysis. The two-tier hybrid search (intra-collection fusion + cross-collection universal search) was simplified into Mini RAG's single-collection dual-pipeline design. | 38,000+ chunks, 57 collections, Qdrant + SQLite FTS |
| **fss-webscraper** | Web scraping patterns — rate limiting, robots.txt compliance, domain-aware crawling, Playwright auto-escalation, content extraction strategies. Mini RAG's `MiniWebScraper` is a stripped-down single-tier version (requests only, no Playwright, no background queues). | 18,000+ indexed chunks, 6-15x performance over standard |
| **fss-research** | Deep research model — multi-phase orchestration (plan → gather → analyse → iterate → synthesise → validate), LLM-driven gap analysis, iterative search cycles, structured reports. Mini RAG's `DeepResearchEngine` follows the same phase loop in a simpler form. | Full CLI tool with interactive plan review |
| **FSS Parsers** (`parsers/`) | Document extraction patterns — PDF via pymupdf, HTML via BeautifulSoup, arXiv and GitHub domain-specific extractors. The parser suite has 10 TypeScript parsers and Python legacy parsers; Mini RAG carries simplified Python-only versions of the core extractors. | 10 TypeScript + 9 Python parsers, BOBAI frontmatter standard |
| **FSS-RAG embedding system** | OpenAI-compatible endpoint pattern — auto-detection of models via `/v1/models`, embedding profiles (precision vs conceptual), manifest-based model tracking. Mini RAG's `OllamaEmbedder` adopted this pattern wholesale. | Multi-provider: vLLM, LM Studio, OpenAI, custom |

The desktop GUI is original to Mini RAG — Tkinter with Sun Valley theme, built from scratch during the March revival. The EventBus architecture, component modularity, and RenderedMarkdown widget have no direct ancestor in the FSS ecosystem (the other tools are CLI-first or use web frontends).

It's only now — with those upstream tools proven and stable — that it makes sense to consolidate the best of them into a single package. The web scraper works. The research engine works. The RAG search works. Merging them isn't an experiment; it's a packaging exercise.

But the core goal remains restraint. Too many features make tools complex and hard to use. The whole point of Mini RAG is to take the best functionality from a much larger ecosystem and package it into something a normal person can pick up and use. Not a developer. Not someone who knows what a vector database is. Just someone with files, questions, and maybe an OpenAI key.

The vision: a quick download-and-install that just works. Index a folder, a large PDF, a handful of research papers. Get AI-synthesised answers from your own corpus. Use a local model on a laptop, or plug in an OpenAI key and get the full capabilities of the latest models. Changing endpoints is a configuration toggle. Increasing chunk sizes is a configuration toggle. The system bends to fit what you have.

At the edges, it has limits. The core search code and LanceDB storage would start to strain under massive collections — tens of thousands of documents would need a proper vector database, more sophisticated retrieval, and the kind of infrastructure the big FSS-RAG system provides. But most people don't need massive RAG collections. They need *clean* ones. And that's where Mini RAG's self-management comes in.

Corpus pruning, session management, deduplication, relevance scoring, stale content removal — the system is built to maintain itself. The goal is a self-contained knowledge assistant that manages its own health so the user doesn't have to think about it. That internal self-management is designed to grow over time as features enable it, but the principle is already baked in.

The difference between Mini RAG and everything else out there is philosophy. It's managed the way Brett manages file systems: structured, constrained, but flexible if you bend a little to fit into the system. That trade-off — a small amount of structure in exchange for a system that works reliably and maintains itself — is the bet.

---

## The Arc

Mini RAG's story is a common pattern in solo developer projects: intense creation, premature distribution attempt, stagnation when nobody wanted to use a terminal-only tool with mediocre search quality, then revival when a real user with real needs provided the forcing function.

The stagnation wasn't abandonment — it was the honest conclusion that the tool wasn't needed yet. The larger ecosystem needed building first. The individual components needed to mature. And the motivation to package something for others needed a reason beyond "it would be nice."

What makes the revival different is that it's not speculative. The March 2026 sprint rebuilt the search architecture, rewrote the embedding system, added a desktop GUI, built a web research engine with deep research capabilities, and added LLM streaming with rich rendering. In three days, the codebase went from 67 commits of struggling-to-install to 121 commits of a functional research tool. But every one of those features was already proven elsewhere. This was assembly, not invention.

The hope is simple: that this tool gives people a sample of what the larger ecosystem can provide. If someone downloads Mini RAG, indexes their research folder, and gets useful answers — that's the job done. And if it sparks interest in what a more capable system could do, the larger ecosystem is there.

The first test case remains Jason — a philosopher with 6GB of VRAM and questions about quantum vacuum fluctuations. If Mini RAG can help him search, scrape, index, and reason about fringe physics research running entirely on his local machine, it's done its job.
