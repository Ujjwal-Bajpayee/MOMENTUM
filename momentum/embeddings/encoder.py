from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import pickle
from pathlib import Path

class SequenceEncoder:
    def __init__(self, model_type: str = "tfidf"):
        self.model_type = model_type
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._fitted = False
        self._dim = 128

    def _sequence_to_text(self, sequence: List[dict]) -> str:
        tokens = []
        for step in sequence:
            event_type = step.get("event_type", "unknown")
            application = step.get("application", "unknown").replace(" ", "_")
            action = step.get("action", "").replace(" ", "_")[:30]
            target = step.get("target", "").replace(" ", "_")[:30]
            token = f"{event_type}_{application}"
            if action:
                token += f"_{action}"
            if target:
                token += f"_{target}"
            tokens.append(token)
        return " ".join(tokens)

    def fit(self, sequences: List[List[dict]]):
        texts = [self._sequence_to_text(s) for s in sequences]
        self._vectorizer = TfidfVectorizer(
            max_features=self._dim,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self._vectorizer.fit(texts)
        self._fitted = True

    def encode(self, sequence: List[dict]) -> np.ndarray:
        text = self._sequence_to_text(sequence)
        if not self._fitted or self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                max_features=self._dim,
                ngram_range=(1, 2),
                min_df=1,
            )
            self._vectorizer.fit([text])
            self._fitted = True
        vec = self._vectorizer.transform([text]).toarray().astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec[0]

    def encode_batch(self, sequences: List[List[dict]]) -> np.ndarray:
        texts = [self._sequence_to_text(s) for s in sequences]
        if not self._fitted or self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                max_features=self._dim,
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )
            self._vectorizer.fit(texts)
            self._fitted = True
        matrix = self._vectorizer.transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def encode_text(self, text: str) -> np.ndarray:
        return self.encode([{"event_type": t, "application": t} for t in text.split()])

    def get_dim(self) -> int:
        return self._dim

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump({"vectorizer": self._vectorizer, "fitted": self._fitted}, f)

    def load(self, path: str):
        if Path(path).exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._vectorizer = data["vectorizer"]
            self._fitted = data["fitted"]

_encoder_instance: Optional[SequenceEncoder] = None

def get_encoder() -> SequenceEncoder:
    global _encoder_instance
    if _encoder_instance is None:
        from momentum.config.settings import settings
        _encoder_instance = SequenceEncoder(model_type=settings.MOMENTUM_EMBEDDING_MODEL)
    return _encoder_instance
