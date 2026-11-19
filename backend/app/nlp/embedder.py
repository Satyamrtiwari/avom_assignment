import re
import logging
from typing import Sequence
import numpy as np

logger = logging.getLogger("resumeranker.embedder")


class Embedder:
    """
    Embedding generation engine using fastembed ONNX runtime (fallback: sentence-transformers).
    Generates 384-dimensional dense semantic vectors with document chunking and mean-pooling.
    Optimized for low-memory cloud runtimes (e.g., Render free tier <512MB).
    """

    _instance = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.embedding_dim = 384
        self._backend = "fastembed"

        try:
            from fastembed import TextEmbedding
            fn = model_name
            if not fn.startswith("sentence-transformers/") and "/" not in fn:
                fn = f"sentence-transformers/{fn}"
            logger.info(f"Loading fastembed ONNX model '{fn}'...")
            self.model = TextEmbedding(model_name=fn)
            self._backend = "fastembed"
            logger.info(f"fastembed model '{fn}' loaded successfully (dim={self.embedding_dim}).")
        except Exception as e:
            logger.warning(f"fastembed unavailable ({e}); falling back to SentenceTransformer.")
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model '{model_name}'...")
            self.model = SentenceTransformer(model_name)
            self._backend = "sentence_transformers"
            logger.info(f"SentenceTransformer '{model_name}' loaded successfully (dim={self.embedding_dim}).")

    @classmethod
    def get_instance(cls, model_name: str = "all-MiniLM-L6-v2") -> "Embedder":
        """Singleton accessor to prevent reloading the model multiple times."""
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def _chunk_text(self, text: str, max_words: int = 150) -> list[str]:
        """
        Split document text into cohesive semantic chunks fitting model token boundaries.
        Splits by paragraphs and groups them up to `max_words`.
        """
        if not text or not text.strip():
            return []

        # Split by double newlines or single newlines
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: list[str] = []
        current_words: list[str] = []

        for p in paragraphs:
            p_words = p.split()
            if len(current_words) + len(p_words) <= max_words:
                current_words.extend(p_words)
            else:
                if current_words:
                    chunks.append(" ".join(current_words))
                    current_words = []

                if len(p_words) > max_words:
                    # Break long paragraph by sentences
                    sentences = re.split(r"(?<=[.!?])\s+", p)
                    sub_words: list[str] = []
                    for s in sentences:
                        s_words = s.split()
                        if len(sub_words) + len(s_words) <= max_words:
                            sub_words.extend(s_words)
                        else:
                            if sub_words:
                                chunks.append(" ".join(sub_words))
                            sub_words = s_words
                    if sub_words:
                        current_words = sub_words
                else:
                    current_words = p_words

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks if chunks else [text[:500]]

    def _encode(self, chunks: list[str]) -> np.ndarray:
        """Vectorized inference helper across backends."""
        if not chunks:
            return np.empty((0, self.embedding_dim), dtype=np.float32)
        if self._backend == "fastembed":
            vecs = list(self.model.embed(chunks))
            return np.array(vecs, dtype=np.float32)
        else:
            return self.model.encode(chunks, convert_to_numpy=True)

    def embed(self, text: str) -> list[float]:
        """
        Generate a 384-dimensional semantic embedding for a single text.
        For texts longer than token limit, chunks and mean-pools vectors.
        """
        if not text or not text.strip():
            return [0.0] * self.embedding_dim

        chunks = self._chunk_text(text)
        chunk_vectors = self._encode(chunks)
        if len(chunks) == 1:
            vec = chunk_vectors[0]
        else:
            vec = np.mean(chunk_vectors, axis=0)

        # Normalize vector for cosine distance
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm

        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Efficient batch embedding for multiple documents.
        Processes all chunks in a single vectorized forward pass.
        """
        if not texts:
            return []

        all_chunks: list[str] = []
        doc_chunk_map: list[int] = []  # maps chunk index -> doc index

        for doc_idx, text in enumerate(texts):
            chunks = self._chunk_text(text)
            if not chunks:
                chunks = [""]
            for c in chunks:
                all_chunks.append(c)
                doc_chunk_map.append(doc_idx)

        # Batch encode all chunks together
        all_vectors = self._encode(all_chunks)

        # Re-aggregate per document with mean-pooling
        doc_vectors: list[list[np.ndarray]] = [[] for _ in texts]
        for chunk_vec, doc_idx in zip(all_vectors, doc_chunk_map):
            doc_vectors[doc_idx].append(chunk_vec)

        results: list[list[float]] = []
        for vectors in doc_vectors:
            if not vectors:
                results.append([0.0] * self.embedding_dim)
                continue
            mean_vec = np.mean(vectors, axis=0)
            norm = np.linalg.norm(mean_vec)
            if norm > 1e-9:
                mean_vec = mean_vec / norm
            results.append(mean_vec.tolist())

        return results

    def similarity(self, emb_a: Sequence[float] | None, emb_b: Sequence[float] | None) -> float:
        """
        Compute cosine similarity between two normalized embeddings.
        Returns float clamped between 0.0 and 1.0.
        """
        if emb_a is None or emb_b is None:
            return 0.0

        a = np.array(emb_a, dtype=np.float32)
        b = np.array(emb_b, dtype=np.float32)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0

        cos_sim = np.dot(a, b) / (norm_a * norm_b)
        # Clamp to [0.0, 1.0]
        return float(max(0.0, min(1.0, cos_sim)))

