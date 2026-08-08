import numpy as np
from typing import List, Dict, Any, Tuple
from momentum.models.session import SessionRecord
from momentum.discovery.clusterer import get_encoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from momentum.discovery.sequence_extractor import extract_sequence

class SequenceEncoderNgram:
    def __init__(self, ngram_range=(1, 3)):
        self._vectorizer = TfidfVectorizer(
            max_features=128,
            ngram_range=ngram_range,
            min_df=1,
            sublinear_tf=True,
        )
        self._fitted = False

    def _sequence_to_text(self, sequence: List[dict]) -> str:
        tokens = []
        for step in sequence:
            event_type = step.get("event_type", "unknown")
            action = step.get("action", "")
            token = f"{event_type}"
            if action:
                token += f"_{action}"
            tokens.append(token)
        return " ".join(tokens)

    def encode_batch(self, sequences: List[List[dict]]) -> np.ndarray:
        texts = [self._sequence_to_text(s) for s in sequences]
        if not self._fitted:
            self._vectorizer.fit(texts)
            self._fitted = True
        matrix = self._vectorizer.transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

def run_clustering_pipeline(
    sessions: List[SessionRecord],
    encoder_type: str = "tfidf_unigram",
    eps: float = 0.35,
    min_samples: int = 3
) -> Tuple[List[List[int]], List[int]]:
    
    sequences = []
    valid_indices = []

    for i, session in enumerate(sessions):
        seq = extract_sequence(session, min_length=3)
        if seq is not None:
            sequences.append(seq)
            valid_indices.append(i)

    if len(sequences) < min_samples:
        return [], valid_indices

    if encoder_type == "tfidf_unigram":
                                   
        encoder = get_encoder()
        encoder.fit(sequences)
        embeddings = encoder.encode_batch(sequences)
    elif encoder_type == "tfidf_ngram":
                                  
        encoder = SequenceEncoderNgram(ngram_range=(1, 3))
        embeddings = encoder.encode_batch(sequences)
    else:
        raise ValueError(f"Unknown encoder_type: {encoder_type}")

    similarity_matrix = embeddings @ embeddings.T
    distance_matrix = np.clip(1.0 - similarity_matrix, 0.0, 2.0).astype(np.float64)

    dbscan = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric="precomputed",
        algorithm="brute",
    )
    labels = dbscan.fit_predict(distance_matrix)

    cluster_map: Dict[int, List[int]] = {}
    for seq_idx, label in enumerate(labels):
        if label == -1:
            continue
        if label not in cluster_map:
            cluster_map[label] = []
        cluster_map[label].append(seq_idx)

    cluster_groups = [indices for indices in cluster_map.values() if len(indices) >= min_samples]
    
    return cluster_groups, valid_indices
