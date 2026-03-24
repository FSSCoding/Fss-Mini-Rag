# Chunker & Indexer Evaluation Issues

Tracked from hands-on evaluation session 2026-03-23, indexing a real-world project (124 files, 1683 chunks).

---

## Indexer: Missing File Extensions

The include list in `indexer.py:80-135` is missing common file types found in real projects.

| Extension | Example in fss-open | Size | Status |
|-----------|-------------------|------|--------|
| `.html` | `ARCHITECTURE_OPTIONS.html` (41KB), `routing_analysis.html` (21KB), `web/static/index.html` | 62KB+ total | NOT INDEXED |
| `.sh` | `build.sh`, `install.sh`, `uninstall.sh`, `web/fss-shell.sh` | 4 files | NOT INDEXED |
| `.conf` | `web/mysite.nginx.conf` | 1 file | NOT INDEXED |
| `.service` | `web/fss-open-web.service` | 1 file | NOT INDEXED |
| `.css` | None in this project, but common | — | NOT INDEXED |
| `.sql` | None in this project, but common | — | NOT INDEXED |
| `.env` | Should remain excluded (secrets) | — | N/A |

**Impact:** The entire web deployment layer (nginx, systemd, HTML frontend) and build scripts are invisible to search. Architecture analysis in HTML files is a significant content loss.

**Fix:** Add to `self.include_patterns` in `indexer.py`:
```
*.html, *.htm, *.css, *.sh, *.bash, *.zsh, *.fish,
*.conf, *.cfg, *.service, *.nginx, *.sql, *.graphql,
*.dockerfile, Dockerfile, Makefile, *.mk,
*.env.example, *.proto, *.tf, *.hcl
```

---

## Chunker: Missing Language Mappings

The `language_patterns` dict in `chunker.py:154-187` has no entries for several file types the indexer should support. Files that make it through the indexer but have no language mapping fall through to generic fixed-size splitting with no structure awareness.

| Extension | Suggested Language | Chunking Strategy |
|-----------|--------------------|-------------------|
| `.html`, `.htm` | `html` | Tag-aware: strip nav/footer/script, split on block elements, preserve structure |
| `.sh`, `.bash`, `.zsh`, `.fish` | `shell` | Function-aware: detect `function name()` and `name()` patterns |
| `.conf`, `.cfg`, `.nginx` | `config` | Already has config strategy, just needs mapping |
| `.service` | `config` | INI-like sections, map to config strategy |
| `.css` | `css` | Rule-based: split on selectors/media queries |
| `.sql` | `sql` | Statement-based: split on CREATE/SELECT/INSERT boundaries |

**Impact:** Even when files are included, they get dumb fixed-size splitting instead of structure-aware chunks.

---

## Chunker: Markdown Table Protection

Code blocks are extracted as protected regions before `\n\n` splitting (via `_protect_fenced_blocks`). Tables receive no such protection.

**Problem:** A markdown table preceded or followed by a blank line can be split from its header or broken mid-row.

**Example:**
```markdown
## Comparison

| Feature | Old | New |
|---------|-----|-----|
| Speed   | 10s | 2s  |
| Quality | Low | High|

More text here...
```

The `\n\n` split could separate the `## Comparison` header from the table, or the table from surrounding context.

**Fix:** Add `_protect_tables()` similar to `_protect_fenced_blocks()`. Detect lines starting with `|` that contain `|---|` separator rows, extract the full table block as a protected region. Restore after splitting.

---

## Chunker: Embedding Model Preference Order

**Fixed 2026-03-23.** Granite was second in precision profile preference order. Changed to:

```
precision: minilm > nomic > bge > e5 > gte > granite
```

File: `ollama_embeddings.py:206`

---

## Evaluation Results Summary

### Strong
- Python AST chunking: class headers, method previews, async functions
- `find-function` / `find-class`: exact match at 1.0 score
- Markdown sections: boundaries preserved, code blocks protected
- File overviews: answer "what's in this file" queries
- Search speed: ~20ms hybrid search
- Score distribution: healthy spread across HIGH/GOOD/FAIR
- Diversity filter: no single file dominates results

### Weak
- Missing file types (see above)
- Missing language mappings (see above)
- Table protection absent
- HTML content completely invisible (biggest single content loss)
- Shell scripts not searchable (deployment/build knowledge lost)
- Config files (.conf, .service) not indexed

### Observations
- When actual files are missing, embedded code blocks in docs partially compensate (systemd service found via STATUS.md code block at 0.057)
- Per-language chunk sizes working well (Python 3000 max appropriate)
- Overlap between chunks not explicitly tested but no boundary artefacts observed
- Unclosed fence detection working (8 warnings on malformed docs, graceful fallback)
