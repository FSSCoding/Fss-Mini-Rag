# RAG System — Embedding Modes

This RAG system can operate with different embedding providers:

## Mode 1: OpenAI-Compatible Endpoint (Recommended)

Uses any OpenAI-compatible embedding server (LM Studio, vLLM, OpenAI, etc.)

```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  model: auto    # auto-detects best embedding model
  profile: precision  # or conceptual
```

**Setup:**
1. Start LM Studio with an embedding model loaded (e.g. MiniLM L6 v2)
2. Or start vLLM with an embedding model
3. The system auto-detects the model via `GET /v1/models`

## Mode 2: ML Fallback (Optional)

If `sentence-transformers` is installed, it serves as a fallback when no API endpoint is available:

```bash
pip install sentence-transformers torch
```

The system will automatically fall back to local ML models if the primary endpoint is unavailable.

## Mode 3: BM25 Only

If no embedding provider is available at all, semantic search is disabled and BM25 keyword search runs solo. This is honest degradation — no fake embeddings, just keyword matching.

## Standard Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

- **Size**: ~123MB total (LanceDB 36MB + PyArrow 43MB + PyLance 44MB)
- **Timing**: 2-3 minutes fast internet, 5-10 minutes slow internet

## Configuration

Edit `.mini-rag/config.yaml`:

```yaml
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
  model: auto
  profile: precision
```

## Status Check

```bash
rag-mini info
rag-mini status
```

## Automatic Behaviour

1. **Try OpenAI-compatible endpoint first** — fastest and most flexible
2. **Fall back to ML models** — if endpoint unavailable and sentence-transformers installed
3. **BM25 only** — if no embedding provider available (keyword search still works)

The system automatically detects what's available and uses the best option.
