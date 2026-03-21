"""
Embedding module with OpenAI-compatible endpoint support.

Priority chain:
1. OpenAI-compatible endpoint (LM Studio, vLLM, OpenAI, any proxy)
2. Ollama (legacy, via config)
3. Local ML models (sentence-transformers, if installed)
4. Hash-based deterministic fallback (always available)
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import numpy as np
import requests

logger = logging.getLogger(__name__)

# Try to import fallback ML dependencies
FALLBACK_AVAILABLE = False
try:
    import torch
    from sentence_transformers import SentenceTransformer
    from transformers import AutoModel, AutoTokenizer

    FALLBACK_AVAILABLE = True
    logger.debug("ML fallback dependencies available")
except ImportError:
    logger.debug("ML fallback not available - Ollama only mode")


class OllamaEmbedder:
    """Embedding provider with OpenAI-compatible endpoint support.

    Supports LM Studio, vLLM, OpenAI, Ollama, and any OpenAI-compatible
    embedding API. Falls back to local ML models or hash embeddings.
    """

    def __init__(
        self,
        model_name: str = "auto",
        base_url: str = "http://localhost:1234/v1",
        enable_fallback: bool = True,
        provider: str = "openai",
        api_key: Optional[str] = None,
        embedding_dim: int = 768,
    ):
        """
        Initialize the embedder.

        Args:
            model_name: Model name for the embedding API
            base_url: Base URL for API (LM Studio: localhost:1234/v1,
                      Ollama: localhost:11434, OpenAI: api.openai.com/v1)
            enable_fallback: Whether to use ML/hash fallback if API fails
            provider: "openai" (OpenAI-compatible), "ollama", "ml", "hash"
            api_key: API key (required for OpenAI, optional for local)
            embedding_dim: Expected embedding dimension
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.embedding_dim = embedding_dim
        self.enable_fallback = enable_fallback and FALLBACK_AVAILABLE
        self.provider = provider
        self.api_key = api_key

        # State tracking
        self.ollama_available = False
        self.fallback_embedder = None
        self.mode = "unknown"  # "openai", "ollama", "fallback", or "hash"

        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize embedding providers in priority order."""
        if self.provider == "hash":
            self.mode = "hash"
            logger.info("Using hash-based embeddings (configured)")
            return

        if self.provider == "ml":
            if self._try_ml_fallback():
                return
            self.mode = "hash"
            return

        # Try the configured provider (openai-compatible or ollama)
        if self.provider == "ollama":
            try:
                self._verify_ollama_connection()
                self.ollama_available = True
                self.mode = "ollama"
                logger.info(f"Ollama embeddings active: {self.model_name}")
                return
            except Exception as e:
                logger.debug(f"Ollama not available: {e}")
        else:
            # OpenAI-compatible endpoint (LM Studio, vLLM, OpenAI, etc.)
            try:
                self._verify_openai_connection()
                self.mode = "openai"
                logger.info(f"OpenAI-compatible embeddings active: {self.model_name} at {self.base_url}")
                return
            except Exception as e:
                logger.debug(f"OpenAI-compatible endpoint not available: {e}")

        # Fallback chain
        if self._try_ml_fallback():
            return

        self.mode = "hash"
        logger.info("Using hash-based embeddings (all providers unavailable)")

    def _try_ml_fallback(self) -> bool:
        """Attempt to initialize ML fallback. Returns True if successful."""
        if not self.enable_fallback:
            return False
        try:
            self._initialize_fallback_embedder()
            self.mode = "fallback"
            model_type = getattr(self.fallback_embedder, 'model_type', 'transformer')
            logger.info(f"ML fallback active: {model_type}")
            return True
        except Exception as e:
            logger.warning(f"ML fallback failed: {e}")
            return False

    def discover_models(self) -> Dict[str, List[str]]:
        """Discover available models from the endpoint.

        Queries GET /v1/models (OpenAI-compatible) or GET /api/tags (Ollama)
        and classifies models as embedding or llm based on naming patterns.

        Returns:
            Dict with "embedding" and "llm" lists of model IDs.
        """
        embedding_models = []
        llm_models = []

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            if self.provider == "ollama":
                response = requests.get(
                    f"{self.base_url}/api/tags", headers=headers, timeout=5
                )
                response.raise_for_status()
                models = [m["name"] for m in response.json().get("models", [])]
            else:
                response = requests.get(
                    f"{self.base_url}/models", headers=headers, timeout=5
                )
                response.raise_for_status()
                models = [m["id"] for m in response.json().get("data", [])]

            # Classify models
            embedding_patterns = ("embed", "embedding", "bge-", "e5-", "gte-")
            for model in models:
                model_lower = model.lower()
                if any(p in model_lower for p in embedding_patterns):
                    embedding_models.append(model)
                else:
                    llm_models.append(model)

        except Exception as e:
            logger.debug(f"Model discovery failed: {e}")

        return {"embedding": embedding_models, "llm": llm_models}

    def _auto_select_embedding_model(self) -> Optional[str]:
        """Auto-detect the best embedding model from the endpoint."""
        discovered = self.discover_models()
        embedding_models = discovered["embedding"]

        if not embedding_models:
            return None

        # Prefer MiniLM (fast, high precision), then nomic, then others
        for preferred in ("minilm", "nomic", "bge", "e5", "gte"):
            for model in embedding_models:
                if preferred in model.lower():
                    return model

        return embedding_models[0]

    def _verify_openai_connection(self):
        """Verify OpenAI-compatible endpoint is reachable and find embedding model."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # If model is "auto", discover available models
        if self.model_name == "auto":
            detected = self._auto_select_embedding_model()
            if detected:
                self.model_name = detected
                logger.info(f"Auto-detected embedding model: {self.model_name}")
            else:
                raise ValueError(
                    f"No embedding models found at {self.base_url}. "
                    f"Load an embedding model (e.g. nomic-embed-text) in your server."
                )

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={"model": self.model_name, "input": "test"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                emb = data["data"][0].get("embedding", [])
                if emb:
                    self.embedding_dim = len(emb)
                    return
            raise ValueError("Invalid embedding response format")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to embedding endpoint at {self.base_url}. "
                f"Ensure your embedding server is running."
            )
        except requests.exceptions.Timeout:
            raise ConnectionError(f"Embedding endpoint at {self.base_url} timed out.")

    def _verify_ollama_connection(self):
        """Verify Ollama server is running and model is available."""
        try:
            # Check server status
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            print("🔌 Ollama Service Unavailable")
            print("   Ollama provides AI embeddings that make semantic search possible")
            print("   Start Ollama: ollama serve")
            print("   Install models: ollama pull nomic-embed-text")
            print()
            raise ConnectionError("Ollama service not running. Start with: ollama serve")
        except requests.exceptions.Timeout:
            print("⏱️ Ollama Service Timeout")
            print("   Ollama is taking too long to respond")
            print("   Check if Ollama is overloaded: ollama ps")
            print("   Restart if needed: killall ollama && ollama serve")
            print()
            raise ConnectionError("Ollama service timeout")

        # Check if our model is available
        models = response.json().get("models", [])
        model_names = [model["name"] for model in models]

        if self.model_name not in model_names:
            print(f"📦 Model '{self.model_name}' Not Found")
            print("   Embedding models convert text into searchable vectors")
            print(f"   Download model: ollama pull {self.model_name}")
            if model_names:
                print(f"   Available models: {', '.join(model_names[:3])}")
            print()
            # Try to pull the model
            self._pull_model()

    def _initialize_fallback_embedder(self):
        """Initialize the ML fallback embedder."""
        if not FALLBACK_AVAILABLE:
            raise RuntimeError("ML dependencies not available for fallback")

        # Try lightweight models first for better compatibility
        fallback_models = [
            (
                "sentence-transformers/all-MiniLM-L6-v2",
                384,
                self._init_sentence_transformer,
            ),
            ("microsoft/codebert-base", 768, self._init_transformer_model),
            ("microsoft/unixcoder-base", 768, self._init_transformer_model),
        ]

        for model_name, dim, init_func in fallback_models:
            try:
                init_func(model_name)
                self.embedding_dim = dim
                logger.info(f"Loaded fallback model: {model_name}")
                return
            except Exception as e:
                logger.debug(f"Failed to load {model_name}: {e}")
                continue

        raise RuntimeError("Could not initialize any fallback embedding model")

    def _init_sentence_transformer(self, model_name: str):
        """Initialize sentence-transformers model."""
        self.fallback_embedder = SentenceTransformer(model_name)
        self.fallback_embedder.model_type = "sentence_transformer"

    def _init_transformer_model(self, model_name: str):
        """Initialize transformer model."""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).to(device)
        model.eval()

        # Create a simple wrapper

        class TransformerWrapper:

            def __init__(self, model, tokenizer, device):
                self.model = model
                self.tokenizer = tokenizer
                self.device = device
                self.model_type = "transformer"

        self.fallback_embedder = TransformerWrapper(model, tokenizer, device)

    def _pull_model(self):
        """Pull the embedding model if not available."""
        logger.info(f"Pulling model {self.model_name}...")
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name},
                timeout=300,  # 5 minutes for model download
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled {self.model_name}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to pull model {self.model_name}: {e}")

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding using the best available provider."""
        if self.mode == "openai":
            return self._get_openai_embedding(text)
        elif self.mode == "ollama" and self.ollama_available:
            return self._get_ollama_embedding(text)
        elif self.mode == "fallback" and self.fallback_embedder:
            return self._get_fallback_embedding(text)
        else:
            return self._hash_embedding(text)

    def _get_openai_embedding(self, text: str) -> np.ndarray:
        """Get embedding from OpenAI-compatible endpoint."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json={"model": self.model_name, "input": text},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]
            return np.array(embedding, dtype=np.float32)

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI-compatible API failed: {e}")
            if self.enable_fallback and self.fallback_embedder:
                return self._get_fallback_embedding(text)
            return self._hash_embedding(text)
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Invalid response from embedding API: {e}")
            return self._hash_embedding(text)

    def _get_ollama_embedding(self, text: str) -> np.ndarray:
        """Get embedding from Ollama API."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            embedding = result.get("embedding", [])

            if not embedding:
                raise ValueError("No embedding returned from Ollama")

            return np.array(embedding, dtype=np.float32)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            # Degrade gracefully - try fallback if available
            if self.mode == "ollama" and self.enable_fallback and self.fallback_embedder:
                logger.info("Falling back to ML embeddings due to Ollama failure")
                self.mode = "fallback"  # Switch mode temporarily
                return self._get_fallback_embedding(text)
            return self._hash_embedding(text)
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid response from Ollama: {e}")
            return self._hash_embedding(text)

    def _get_fallback_embedding(self, text: str) -> np.ndarray:
        """Get embedding from ML fallback."""
        try:
            if self.fallback_embedder.model_type == "sentence_transformer":
                embedding = self.fallback_embedder.encode([text], convert_to_numpy=True)[0]
                return embedding.astype(np.float32)

            elif self.fallback_embedder.model_type == "transformer":
                # Tokenize and generate embedding
                inputs = self.fallback_embedder.tokenizer(
                    text,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.fallback_embedder.device)

                with torch.no_grad():
                    outputs = self.fallback_embedder.model(**inputs)

                    # Use pooler output if available, otherwise mean pooling
                    if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
                        embedding = outputs.pooler_output[0]
                    else:
                        # Mean pooling over sequence length
                        attention_mask = inputs["attention_mask"]
                        token_embeddings = outputs.last_hidden_state[0]

                        # Mask and average
                        input_mask_expanded = (
                            attention_mask.unsqueeze(-1)
                            .expand(token_embeddings.size())
                            .float()
                        )
                        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 0)
                        sum_mask = torch.clamp(input_mask_expanded.sum(0), min=1e-9)
                        embedding = sum_embeddings / sum_mask

                return embedding.cpu().numpy().astype(np.float32)

            else:
                raise ValueError(
                    f"Unknown fallback model type: {self.fallback_embedder.model_type}"
                )

        except Exception as e:
            logger.error(f"Fallback embedding failed: {e}")
            return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> np.ndarray:
        """Generate deterministic hash-based embedding as fallback."""
        import hashlib

        # Create deterministic hash
        hash_obj = hashlib.sha256(text.encode("utf-8"))
        hash_bytes = hash_obj.digest()

        # Convert to numbers and normalize
        hash_nums = np.frombuffer(hash_bytes, dtype=np.uint8)

        # Expand to target dimension using repetition
        while len(hash_nums) < self.embedding_dim:
            hash_nums = np.concatenate([hash_nums, hash_nums])

        # Take exactly the dimension we need
        embedding = hash_nums[: self.embedding_dim].astype(np.float32)

        # Normalize to [-1, 1] range
        embedding = (embedding / 127.5) - 1.0

        logger.debug(f"Using hash fallback embedding for text: {text[:50]}...")
        return embedding

    def embed_code(self, code: Union[str, List[str]], language: str = "python") -> np.ndarray:
        """
        Generate embeddings for code snippet(s).

        Args:
            code: Single code string or list of code strings
            language: Programming language (used for context)

        Returns:
            Embedding vector(s) as numpy array
        """
        if isinstance(code, str):
            code = [code]
            single_input = True
        else:
            single_input = False

        # Preprocess code for better embeddings
        processed_code = [self._preprocess_code(c, language) for c in code]

        # Generate embeddings
        embeddings = []
        for text in processed_code:
            embedding = self._get_embedding(text)
            embeddings.append(embedding)

        embeddings = np.array(embeddings, dtype=np.float32)

        if single_input:
            return embeddings[0]
        return embeddings

    def _preprocess_code(self, code: str, language: str = "python") -> str:
        """
        Preprocess code for better embedding quality.
        Add language context and clean up formatting.
        """
        # Remove leading/trailing whitespace
        code = code.strip()

        # Normalize whitespace but preserve structure
        lines = code.split("\n")
        processed_lines = []

        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            # Keep non-empty lines
            if line:
                processed_lines.append(line)

        cleaned_code = "\n".join(processed_lines)

        # Add language context for better embeddings
        if language and cleaned_code:
            return f"```{language}\n{cleaned_code}\n```"
        return cleaned_code

    @lru_cache(maxsize=1000)
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query with caching.
        Queries are often repeated, so we cache them.
        """
        # Enhance query for code search
        enhanced_query = f"Search for code related to: {query}"
        return self._get_embedding(enhanced_query)

    def batch_embed_files(self, file_contents: List[dict], max_workers: int = 4) -> List[dict]:
        """
        Embed multiple files efficiently using concurrent requests to Ollama.

        Args:
            file_contents: List of dicts with 'content' and optionally 'language' keys
            max_workers: Maximum number of concurrent Ollama requests

        Returns:
            List of dicts with added 'embedding' key (preserves original order)
        """
        if not file_contents:
            return []

        # For small batches, use sequential processing to avoid overhead
        if len(file_contents) <= 2:
            return self._batch_embed_sequential(file_contents)

        # For very large batches, use chunked processing to prevent memory issues
        if len(file_contents) > 500:  # Process in chunks to manage memory
            return self._batch_embed_chunked(file_contents, max_workers)

        return self._batch_embed_concurrent(file_contents, max_workers)

    def _batch_embed_sequential(self, file_contents: List[dict]) -> List[dict]:
        """Sequential processing for small batches."""
        results = []
        for file_dict in file_contents:
            content = file_dict["content"]
            language = file_dict.get("language", "python")
            embedding = self.embed_code(content, language)

            result = file_dict.copy()
            result["embedding"] = embedding
            results.append(result)

        return results

    def _batch_embed_concurrent(
        self, file_contents: List[dict], max_workers: int
    ) -> List[dict]:
        """Concurrent processing for larger batches."""

        def embed_single(item_with_index):
            index, file_dict = item_with_index
            content = file_dict["content"]
            language = file_dict.get("language", "python")

            try:
                embedding = self.embed_code(content, language)
                result = file_dict.copy()
                result["embedding"] = embedding
                return index, result
            except Exception as e:
                logger.error(f"Failed to embed content at index {index}: {e}")
                # Return with hash fallback
                result = file_dict.copy()
                result["embedding"] = self._hash_embedding(content)
                return index, result

        # Create indexed items to preserve order
        indexed_items = list(enumerate(file_contents))

        # Process concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            indexed_results = list(executor.map(embed_single, indexed_items))

        # Sort by original index and extract results
        indexed_results.sort(key=lambda x: x[0])
        return [result for _, result in indexed_results]

    def _batch_embed_chunked(
        self, file_contents: List[dict], max_workers: int, chunk_size: int = 200
    ) -> List[dict]:
        """
        Process very large batches in smaller chunks to prevent memory issues.
        This is important for beginners who might try to index huge projects.
        """
        results = []
        total_chunks = len(file_contents)

        # Process in chunks
        for i in range(0, len(file_contents), chunk_size):
            chunk = file_contents[i : i + chunk_size]

            # Log progress for large operations
            if total_chunks > chunk_size:
                chunk_num = i // chunk_size + 1
                total_chunk_count = (total_chunks + chunk_size - 1) // chunk_size
                logger.info(
                    f"Processing chunk {chunk_num}/{total_chunk_count} ({len(chunk)} files)"
                )

            # Process this chunk using concurrent method
            chunk_results = self._batch_embed_concurrent(chunk, max_workers)
            results.extend(chunk_results)

            # Brief pause between chunks to prevent overwhelming the system
            if i + chunk_size < len(file_contents):

                time.sleep(0.1)  # 100ms pause between chunks

        return results

    def get_embedding_dim(self) -> int:
        """Return the dimension of embeddings produced by this model."""
        return self.embedding_dim

    def get_mode(self) -> str:
        """Return current embedding mode: 'openai', 'ollama', 'fallback', or 'hash'."""
        return self.mode

    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the embedding system."""
        return {
            "mode": self.mode,
            "provider": self.provider,
            "model": self.model_name,
            "base_url": self.base_url,
            "ollama_available": self.ollama_available,
            "fallback_available": FALLBACK_AVAILABLE and self.enable_fallback,
            "fallback_model": (
                getattr(self.fallback_embedder, "model_type", None)
                if self.fallback_embedder
                else None
            ),
            "embedding_dim": self.embedding_dim,
        }

    def get_embedding_info(self) -> Dict[str, str]:
        """Get human-readable embedding system information."""
        mode = self.mode
        if mode == "openai":
            return {"method": f"OpenAI-compatible ({self.model_name} at {self.base_url})", "status": "working"}
        if mode == "ollama":
            return {"method": f"Ollama ({self.model_name})", "status": "working"}
        # Treat legacy/alternate naming uniformly
        if mode in ("fallback", "ml"):
            return {
                "method": f"ML Fallback ({status['fallback_model']})",
                "status": "working",
            }
        if mode == "hash":
            return {"method": "Hash-based (basic similarity)", "status": "working"}
        return {"method": "Unknown", "status": "error"}

    def warmup(self):
        """Warm up the embedding system with a dummy request."""
        dummy_code = "def hello(): pass"
        _ = self.embed_code(dummy_code)
        logger.info(f"Hybrid embedder ready - Mode: {self.mode}")
        return self.get_status()


# Convenience function for quick embedding


def embed_code(
    code: Union[str, List[str]], model_name: str = "nomic-embed-text:latest"
) -> np.ndarray:
    """
    Quick function to embed code without managing embedder instance.

    Args:
        code: Code string(s) to embed
        model_name: Ollama model name to use

    Returns:
        Embedding vector(s)
    """
    embedder = OllamaEmbedder(model_name=model_name)
    return embedder.embed_code(code)


# Compatibility alias for drop-in replacement
CodeEmbedder = OllamaEmbedder
