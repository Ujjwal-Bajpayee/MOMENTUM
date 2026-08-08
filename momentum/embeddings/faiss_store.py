import numpy as np
import faiss
from typing import List, Tuple, Optional
from pathlib import Path
import pickle

class FAISSStore:
    def __init__(self, dim: int = 128):
        self.dim = dim
        self._index: Optional[faiss.IndexFlatIP] = None
        self._ids: List[str] = []
        self._metadata: List[dict] = []

    def _ensure_index(self):
        if self._index is None:
            self._index = faiss.IndexFlatIP(self.dim)

    def add(self, embedding: np.ndarray, doc_id: str, metadata: Optional[dict] = None):
        self._ensure_index()
        vec = embedding.astype(np.float32).reshape(1, -1)
        if vec.shape[1] != self.dim:
            padded = np.zeros((1, self.dim), dtype=np.float32)
            copy_len = min(vec.shape[1], self.dim)
            padded[0, :copy_len] = vec[0, :copy_len]
            vec = padded
        self._index.add(vec)
        self._ids.append(doc_id)
        self._metadata.append(metadata or {})

    def add_batch(self, embeddings: np.ndarray, doc_ids: List[str], metadata: Optional[List[dict]] = None):
        self._ensure_index()
        batch = embeddings.astype(np.float32)
        if batch.shape[1] != self.dim:
            padded = np.zeros((batch.shape[0], self.dim), dtype=np.float32)
            copy_len = min(batch.shape[1], self.dim)
            padded[:, :copy_len] = batch[:, :copy_len]
            batch = padded
        self._index.add(batch)
        self._ids.extend(doc_ids)
        if metadata:
            self._metadata.extend(metadata)
        else:
            self._metadata.extend([{}] * len(doc_ids))

    def search(self, query: np.ndarray, k: int = 5) -> List[Tuple[str, float, dict]]:
        if self._index is None or self._index.ntotal == 0:
            return []
        vec = query.astype(np.float32).reshape(1, -1)
        if vec.shape[1] != self.dim:
            padded = np.zeros((1, self.dim), dtype=np.float32)
            copy_len = min(vec.shape[1], self.dim)
            padded[0, :copy_len] = vec[0, :copy_len]
            vec = padded
        actual_k = min(k, self._index.ntotal)
        distances, indices = self._index.search(vec, actual_k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self._ids):
                results.append((self._ids[idx], float(dist), self._metadata[idx]))
        return results

    def size(self) -> int:
        if self._index is None:
            return 0
        return self._index.ntotal

    def save(self, path: str):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(p) + ".faiss")
        with open(str(p) + ".meta", "wb") as f:
            pickle.dump({"ids": self._ids, "metadata": self._metadata, "dim": self.dim}, f)

    def load(self, path: str):
        p = Path(path)
        faiss_path = str(p) + ".faiss"
        meta_path = str(p) + ".meta"
        if Path(faiss_path).exists() and Path(meta_path).exists():
            self._index = faiss.read_index(faiss_path)
            with open(meta_path, "rb") as f:
                data = pickle.load(f)
            self._ids = data["ids"]
            self._metadata = data["metadata"]
            self.dim = data["dim"]

    def reset(self):
        self._index = None
        self._ids = []
        self._metadata = []
