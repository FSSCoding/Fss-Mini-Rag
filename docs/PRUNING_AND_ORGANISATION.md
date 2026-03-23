# Pruning and Organisation System

> **How the deep research engine manages, deduplicates, and cross-references its corpus**

## How It Works

The pruning system uses the **same vector embeddings already in the LanceDB index** to compute document similarity. No additional GPU calls, no separate embedding step — it reads the vectors that were created when the content was indexed.

### The Pipeline

```
Source files indexed → LanceDB has chunk embeddings
                            ↓
Pruner reads embeddings → averages chunks per file → file-level vectors
                            ↓
Cosine similarity matrix → NxN pairwise comparison (numpy, microseconds)
                            ↓
Threshold classification:
  >= 0.95  →  DUPLICATE (remove newer copy)
  0.80-0.95  →  BORDERLINE (ask LLM to confirm)
  0.60-0.80  →  CORROBORATION (flag as supporting evidence)
  < 0.60  →  UNRELATED (ignore)
```

### Why Vectors, Not Text

The original implementation used CPU-based trigram Jaccard similarity on raw text. This had serious problems:

| Approach | "Haramein" vs "Haramein's" | Same topic, different wording | Speed at 100 files |
|----------|--------------------------|------------------------------|-------------------|
| Trigram Jaccard | 0.85 (miss) | 0.25 (miss) | ~5s |
| Keyword overlap | exact match only | 0.13 (miss) | ~2s |
| **Cosine on indexed vectors** | **0.95+ (correct)** | **0.60-0.80 (correct)** | **<0.1s** |

The embeddings understand semantic meaning. Two papers about proton radius measurements written in completely different words score 0.73 cosine similarity. Trigrams saw them as 0.25 (unrelated).

## Real-World Test: Holographic Mass Research Session

A 2-round deep research session on "proton radius holographic mass" produced 6 source files:

| File | Words | Source |
|------|-------|--------|
| Proton Radius Prediction | 1,529 | spacefed.com |
| Holographic Model Part II | 2,812 | spacefed.com |
| Holographic Model Part III | 4,171 | spacefed.com |
| CODATA Proton Charge Radius | 2,142 | spacefed.com |
| Review History (prh) | 667 | prh.sdiarticle3.com |
| Quantum Gravity Q&A | 1,165 | physics.stackexchange.com |

### Full Similarity Matrix

Cosine similarity computed from averaged chunk embeddings (already in LanceDB):

```
                          CODATA   PRH    QG-QA   Holo-II  Holo-III  Proton-R
CODATA History            1.000   0.491   0.613   0.718    0.779     0.861
PRH Review                0.491   1.000   0.600   0.479    0.448     0.611
QG StackExchange          0.613   0.600   1.000   0.824    0.745     0.731
Holographic Model II      0.718   0.479   0.824   1.000    0.898     0.763
Holographic Model III     0.779   0.448   0.745   0.898    1.000     0.748
Proton Radius Prediction  0.861   0.611   0.731   0.763    0.748     1.000
```

### What The Pruner Found

From 15 pairwise comparisons (6 files):

- **0 duplicates** — no files scored >= 0.95 (all genuinely different documents)
- **3 borderline pairs** (0.80-0.95):
  - CODATA ↔ Proton Radius Prediction (0.861) — both about measurement history
  - QG Q&A ↔ Holographic Model II (0.824) — both discuss Haramein's approach
  - Holographic Model II ↔ III (0.898) — parts of the same paper series
- **9 corroborations** (0.60-0.80):
  - Every other pair of physics documents was detected as topically related
- **3 below threshold** (<0.60):
  - All involving PRH Review (0.448-0.491) — it's a review submission log, not a physics paper

### What This Means

The 0.898 between Holographic Model II and III is correct — they're sequential parts of the same paper series. They share extensive theoretical framework but have different content (Part II covers quantum gravity, Part III covers the electron). The pruner correctly classified this as borderline, not duplicate.

The CODATA ↔ Proton Radius Prediction pair at 0.861 makes sense — both discuss measurement history and specific numerical values, but from different angles (CODATA focuses on the standards process, Prediction focuses on Haramein's calculation).

The PRH Review at 0.448-0.491 with most documents is correct — it's metadata about a journal submission, semantically distant from the physics content.

## Bug Found and Fixed

### Cross-Session Name Collision

The initial pruner matched files by filename stem (e.g., `quantum-gravity-and-the-holographic-mass`). This caused collisions — a file named `quantum-gravity-and-the-holographic-mass.md` matched 30 chunks across multiple research sessions instead of the 6 chunks from its own session.

**Fix:** Match by full relative path first (`mini-research/2026-03-23-session/sources/filename.md`), fall back to stem match only when path match fails.

**Impact:** Before the fix, the pruner found 1 corroboration. After: 12 corroborations — every significant relationship detected.

## Thresholds

| Range | Classification | Action |
|-------|---------------|--------|
| >= 0.95 | **DUPLICATE** | Remove newer copy, keep original (sorted by file modification time) |
| 0.80-0.95 | **BORDERLINE** | Ask LLM to classify as DUPLICATE/RELATED/UNRELATED. Without LLM, conservatively classify as corroboration |
| 0.60-0.80 | **CORROBORATION** | Flag as supporting evidence. Same info in multiple sources strengthens confidence |
| < 0.60 | **UNRELATED** | Ignore — different topics |

These thresholds were calibrated against real research data:
- 0.898 (Holographic Model II ↔ III) = correctly borderline, not duplicate
- 0.861 (CODATA ↔ Proton Radius) = correctly borderline
- 0.600 (PRH ↔ QG Q&A) = correctly at the corroboration boundary
- 0.448-0.491 (PRH ↔ most docs) = correctly below threshold

## Fallback: Text-Based Similarity

When the LanceDB index isn't available (e.g., content hasn't been indexed yet), the pruner falls back to:

1. **Trigram Jaccard** on first 2000 characters (normalized, lowercased, punctuation stripped)
2. Threshold: >= 0.90 = duplicate, >= 0.60 = corroboration
3. No LLM borderline checking in fallback mode

This is less accurate (misses topical relationships) but handles the case where pruning runs before indexing.

## File Ordering

When a duplicate is confirmed, the pruner keeps the **older** file and removes the **newer** one:

- Files sorted by modification time (oldest first)
- The first file in the sorted order is treated as the original
- Only the newer copy is deleted

This prevents the original source from being removed if the same content was scraped from a mirror site in a later round.

## Integration With Deep Research

The pruner runs every other round during deep research (and always on the last round):

```
Round 1: ANALYZE → SEARCH → SCRAPE
Round 2: ANALYZE → SEARCH → SCRAPE → PRUNE    ← here
Round 3: ANALYZE → SEARCH → SCRAPE
Round 4: ANALYZE → SEARCH → SCRAPE → PRUNE    ← here
Round 5: ANALYZE → SEARCH → SCRAPE → PRUNE    ← final round, always prune
```

### What Gets Tracked

Every pruning action is recorded in `metrics.json`:

- Files marked as pruned in the file registry (with `duplicate_of` reference)
- Per-round `pages_pruned` count
- Corroborations listed in the research report

### What The Pruner Never Does

- **Never deletes a source file that isn't a true duplicate** — corroborations and borderline cases are flagged, not removed
- **Never modifies source content** — source files in `sources/` are read-only except for duplicate removal
- **Never touches `notes/`** — user files are completely off-limits
- **Writes findings to `agent-notes/`** — corroboration reports go in the agent's space

## Performance

| Corpus Size | Pairs | Vector Matrix | Total Prune Time |
|------------|-------|---------------|-----------------|
| 6 files | 15 | < 0.01s | < 0.1s |
| 20 files | 190 | < 0.01s | < 0.5s |
| 50 files | 1,225 | < 0.05s | ~1s |
| 100 files | 4,950 | < 0.1s | ~2s (without LLM calls) |

The vector comparison is numpy dot products — essentially free. The cost is in LLM calls for borderline cases (0.80-0.95 range). At 100 files with ~5% borderline rate, that's ~250 potential LLM calls, mitigated by only checking pairs above the borderline threshold.

## Configuration

```yaml
deep_research:
  prune_threshold: 0.3   # Not currently used (thresholds are hardcoded)
```

Current thresholds are class constants on `CorpusPruner`:
- `DUPLICATE_THRESHOLD = 0.95`
- `BORDERLINE_THRESHOLD = 0.80`
- `CORROBORATION_THRESHOLD = 0.60`

These can be made configurable if tuning is needed, but the current values are calibrated against real research data and shouldn't need adjustment for most use cases.
