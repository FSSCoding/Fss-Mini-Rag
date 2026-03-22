"""Model discovery service.

Queries embedding and LLM endpoints for available models.
Used by preferences dialog to populate model dropdowns.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def discover_models(base_url: str) -> Dict[str, List[str]]:
    """Discover available models from an OpenAI-compatible endpoint.

    Returns:
        Dict with "embedding" and "llm" lists of model IDs.
    """
    try:
        from mini_rag.ollama_embeddings import OllamaEmbedder

        emb = OllamaEmbedder(base_url=base_url)
        return emb.discover_models()
    except Exception as e:
        logger.debug(f"Model discovery failed for {base_url}: {e}")
        return {"embedding": [], "llm": []}
