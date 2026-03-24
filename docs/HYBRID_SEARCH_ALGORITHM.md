# Hybrid Search Algorithm

Reference documentation for the hybrid search implementation in FSS-Mini-RAG.
Source: `mini_rag/search.py` (class `CodeSearcher`)

---

## Overview

The search uses a **two-retriever hybrid** approach: semantic (vector) search and BM25 (keyword) search run **independently** against the full index, then results are merged using **Reciprocal Rank Fusion (RRF)**. Post-fusion, results pass through re-ranking, diversity filtering, and chunk consolidation.

```
Query
  |
  v
[Query Expansion] ---- optional LLM-based synonym expansion
  |
  +---> [Semantic Search]  (LanceDB vector similarity, top_k*3)
  |           |
  +---> [BM25 Search]      (BM25Okapi full index, top_k*3)
  |           |
  v           v
  +-----+-----+
        |
  [RRF Fusion]  ---- merge by rank, not score
        |
  [Smart Re-rank] ---- boost by file importance, recency, chunk type
        |
  [Diversity Filter] ---- max 2 per file, type diversity, dedup
        |
  [Chunk Consolidation] ---- merge adjacent chunks from same file
        |
        v
    Final Results
```

---

## Stage 1: Query Expansion (optional)

**Source:** `mini_rag/query_expander.py` (class `QueryExpander`)

When enabled (`config.search.expand_queries = true`), the query is sent to a small LLM (default: `qwen3:1.7b`) which adds synonym/related terms.

- Example: `"authentication"` -> `"authentication login user verification credentials"`
- Adds ~100ms latency
- Results are cached per-query to avoid repeated API calls
- Disabled by default in CLI, configurable in config.yaml

---

## Stage 2a: Semantic Search (Vector Similarity)

**Source:** `search.py:477-501`

Uses LanceDB's built-in vector search against pre-computed embeddings.

1. The query (or expanded query) is embedded using the same model that built the index
2. LanceDB returns `top_k * 3` nearest neighbors by vector distance
3. Distance is converted to a similarity score: **`score = 1 / (1 + distance)`**
   - This maps L2 distance to a 0-1 range where 1 = identical
4. Skipped entirely if embedder mode is `"unavailable"` or `"hash"` (falls back to BM25-only)

---

## Stage 2b: BM25 Keyword Search

**Source:** `search.py:244-270` (index build), `search.py:355-386` (search)

Uses `rank_bm25.BM25Okapi` over the full chunk corpus.

### Index Construction (`_build_bm25_index`)
- All chunks are loaded from LanceDB into memory
- Each chunk's searchable text = `content + name + chunk_type`
- Text is tokenized with code-aware splitting (see below)

### Code-Aware Tokenization (`_tokenize_for_bm25`)

**Source:** `search.py:25-58`

Splits on:
- Whitespace
- Non-alphanumeric characters (dots, slashes, etc.)
- `snake_case` boundaries: `get_auth_token` -> `[get_auth_token, get, auth, token]`
- `camelCase` boundaries: `getAuthToken` -> `[getauthtoken, get, auth, token]`

The original compound token is kept alongside split parts so exact matches still work.

### Search Execution (`_search_bm25_full`)
1. Query is tokenized with the same code-aware tokenizer
2. BM25 scores all chunks in the corpus
3. Top `top_k * 3` results by raw BM25 score are taken
4. Scores are normalized: **`normalized = bm25_score / max(all_scores)`**, capped at 1.0
5. Zero-score results are discarded

---

## Stage 3: Reciprocal Rank Fusion (RRF)

**Source:** `search.py:388-420`

RRF merges the two ranked lists using rank position rather than raw scores. This is critical because BM25 scores are unbounded while cosine similarity is 0-1 -- score-based mixing would be unreliable.

### Formula

For each result appearing in one or more lists:

```
RRF_score = sum( 1 / (k + rank + 1) )  for each list containing this result
```

- **k = 60** (standard constant from the original RRF paper by Cormack, Clarke & Buettcher, 2009)
- **rank** is 0-indexed position in each list
- A result appearing in both lists gets scores from both summed

### Example

A result ranked #1 in semantic and #3 in BM25:
```
RRF = 1/(60+0+1) + 1/(60+3+1) = 1/61 + 1/64 = 0.01639 + 0.01563 = 0.03202
```

A result ranked #1 in semantic only:
```
RRF = 1/(60+0+1) = 0.01639
```

### Deduplication
Results are keyed by `(file_path, start_line, end_line)`. When duplicates exist across lists, the result object with the higher original score is kept.

### Output
Results are sorted by RRF score descending. The RRF score replaces the original score on each result object. Typical score range: **0.01 - 0.05**.

---

## Stage 4: Smart Re-ranking

**Source:** `search.py:596-678`

Post-fusion score adjustments. Only applied to results with scores above 50% of the max score (to avoid boosting irrelevant results).

### Boost factors (multiplicative)

| Condition | Boost | Rationale |
|-----------|-------|-----------|
| File matches important patterns (`readme`, `main.`, `__init__`, `config`, `docs/`, etc.) | x1.05 | Core files are usually more relevant |
| File modified in last 7 days | x1.02 | Recently touched code is often what you're looking for |
| File modified in last 30 days | x1.01 | Slightly fresher |
| Chunk type is `function`, `class`, or `method` | x1.10 | Code definitions are more valuable than raw blocks |
| Chunk type is `comment` or `docstring` | x1.05 | Documentation helps understanding |
| Content has 3+ lines with substance | x1.02 | Well-structured content is more useful |

### Penalty factors

| Condition | Penalty | Rationale |
|-----------|---------|-----------|
| Content < 50 characters | x0.90 | Too short to be useful |

---

## Stage 5: Diversity Constraints

**Source:** `search.py:680-722`

Prevents result homogeneity:

- **Max 2 chunks per file** - prevents one large file from dominating
- **Chunk type diversity** - once half the results are filled, limits any single type to max 1/3 of top_k
- **Content deduplication** - hashes first 200 chars of each result, skips duplicates

---

## Stage 6: Chunk Consolidation

**Source:** `search.py:535-594`

Merges adjacent/overlapping chunks from the same file into contiguous passages.

- Groups results by file path
- Sorts by start line within each file
- Merges chunks where the gap between them is <= `gap_threshold + 1` lines (default threshold: 1)
- Merged chunks: content is concatenated, line range is extended, score takes the max
- Names are combined with ` + ` separator when both exist
- Final results re-sorted by score

---

## Default Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `semantic_weight` | 0.7 | Accepted but not used in RRF (rank-based, not score-weighted) |
| `bm25_weight` | 0.3 | Same -- legacy parameter, both retrievers have equal rank contribution |
| `top_k` | 10 | Final result count |
| Retriever fetch | `top_k * 3` | Each retriever fetches 3x to give RRF enough candidates |
| RRF k constant | 60 | Standard from original paper |
| Diversity: max per file | 2 | |
| Consolidation gap | 1 line | |

Note: `semantic_weight` and `bm25_weight` are accepted as parameters but the current RRF implementation treats both retrievers equally. The weights are vestigial from a previous score-mixing approach.

---

## Score Interpretation

RRF scores are small numbers. The display system auto-detects the scale:

| Score Range (RRF) | Label |
|-------------------|-------|
| >= 0.035 | HIGH |
| >= 0.025 | GOOD |
| >= 0.018 | FAIR |
| >= 0.010 | LOW |
| < 0.010 | WEAK |

---

## Key Design Decisions

1. **Independent retrieval, not cascaded** - BM25 searches the full index, not just the vector shortlist. This ensures keyword matches are found even when embeddings are poor.

2. **Rank-based fusion, not score-based** - RRF avoids the calibration problem of mixing scores from different distributions.

3. **Over-fetch then filter** - Each retriever returns 3x candidates. This gives RRF enough overlap to identify results that both methods agree on.

4. **Graceful degradation** - If the embedding provider is unavailable, search falls back to BM25-only automatically.

5. **Code-aware tokenization** - The BM25 tokenizer understands `snake_case` and `camelCase`, keeping compound tokens alongside split parts for both exact and partial matching.
