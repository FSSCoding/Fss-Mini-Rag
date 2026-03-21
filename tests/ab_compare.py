#!/usr/bin/env python3
"""A/B search comparison tool.

Runs a query against 3 mini-rag indexes (MiniLM, Nomic, Granite) plus
Fss-Rag gold standard, showing top-3 results from each side by side.

Usage:
    python tests/ab_compare.py kg "your query"     # knowledge-graph collection
    python tests/ab_compare.py code "your query"    # fss-mini-rag codebase
    python tests/ab_compare.py kg                   # interactive mode
    python tests/ab_compare.py code                 # interactive mode
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mini_rag.ollama_embeddings import OllamaEmbedder
from mini_rag.search import CodeSearcher


COLLECTIONS = {
    "kg": {
        "name": "Knowledge Graph",
        "fss_rag_collection": "knowledge-graph",
        "indexes": {
            "MiniLM (384d)": {
                "path": "/tmp/kg-index-minilm",
                "model": "text-embedding-all-minilm-l6-v2-embedding",
            },
            "Nomic (768d)": {
                "path": "/tmp/kg-index-nomic",
                "model": "text-embedding-nomic-embed-text-v1.5@q4_k_m",
            },
            "Granite (384d)": {
                "path": "/tmp/kg-index-granite",
                "model": "text-embedding-granite-embedding-107m-multilingual",
            },
        },
    },
    "code": {
        "name": "FSS-Mini-RAG Codebase",
        "fss_rag_collection": "fss-mini-rag",
        "indexes": {
            "MiniLM (384d)": {
                "path": "/tmp/minirag-index-minilm",
                "model": "text-embedding-all-minilm-l6-v2-embedding",
            },
            "Nomic (768d)": {
                "path": "/tmp/minirag-index-nomic",
                "model": "text-embedding-nomic-embed-text-v1.5@q4_k_m",
            },
            "Granite (384d)": {
                "path": "/tmp/minirag-index-granite",
                "model": "text-embedding-granite-embedding-107m-multilingual",
            },
        },
    },
}


def search_mini_rag(query, index_info, top_k=3):
    path = Path(index_info["path"])
    if not (path / ".mini-rag").exists():
        return []
    emb = OllamaEmbedder(model_name=index_info["model"])
    searcher = CodeSearcher(path, embedder=emb)
    return searcher.search(query, top_k=top_k)


def search_fss_rag(query, collection, top_k=3):
    try:
        result = subprocess.run(
            ["rag", collection, query, "--topk", str(top_k), "--simple"],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(error: {e})"


def format_result(result, idx):
    name = result.name or "-"
    file = Path(result.file_path).name
    score = result.score
    content_preview = result.content[:120].replace("\n", " ").strip()
    return (
        f"  #{idx} [{score:.4f}] {file}: {name[:45]}\n"
        f"     {content_preview}..."
    )


def parse_fss_rag_results(output):
    """Extract file and score from fss-rag simple output."""
    results = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Lines like: "1. (0.770) content..."
        if line and line[0].isdigit() and "(" in line:
            try:
                score_start = line.index("(") + 1
                score_end = line.index(")")
                score = float(line[score_start:score_end])
                content = line[score_end + 1:].strip()[:120]
                results.append((score, content))
            except (ValueError, IndexError):
                continue
    return results


def run_comparison(query, collection_key):
    coll = COLLECTIONS[collection_key]
    print(f"\n{'='*75}")
    print(f"QUERY: {query}")
    print(f"COLLECTION: {coll['name']}")
    print(f"{'='*75}")

    # Mini-rag models
    for model_name, info in coll["indexes"].items():
        print(f"\n--- {model_name} ---")
        results = search_mini_rag(query, info)
        if results:
            for i, r in enumerate(results[:3], 1):
                print(format_result(r, i))
        else:
            print("  (no results)")

    # Fss-Rag
    print(f"\n--- Fss-Rag ({coll['fss_rag_collection']}) ---")
    fss_output = search_fss_rag(query, coll["fss_rag_collection"])
    fss_results = parse_fss_rag_results(fss_output)
    if fss_results:
        for i, (score, content) in enumerate(fss_results[:3], 1):
            print(f"  #{i} [{score:.4f}] {content}...")
    elif fss_output:
        for line in fss_output.split("\n")[:10]:
            print(f"  {line}")
    else:
        print("  (no output)")

    print(f"\n{'='*75}")


def main():
    # Parse collection arg
    if len(sys.argv) < 2 or sys.argv[1] not in COLLECTIONS:
        print("Usage: python tests/ab_compare.py <kg|code> [query]")
        print("  kg   = Knowledge Graph collection")
        print("  code = FSS-Mini-RAG codebase")
        sys.exit(1)

    collection_key = sys.argv[1]
    coll = COLLECTIONS[collection_key]

    if len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        run_comparison(query, collection_key)
    else:
        print(f"A/B Search Comparison - {coll['name']}")
        print("Models: MiniLM | Nomic | Granite | Fss-Rag")
        print("Type 'quit' to exit\n")

        while True:
            try:
                query = input("Query> ").strip()
                if not query or query.lower() in ("quit", "exit", "q"):
                    break
                run_comparison(query, collection_key)
            except (KeyboardInterrupt, EOFError):
                break

        print("\nDone.")


if __name__ == "__main__":
    main()
