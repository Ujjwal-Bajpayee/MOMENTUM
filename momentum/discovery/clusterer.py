import numpy as np
from typing import List, Tuple, Optional, Dict
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize
from momentum.embeddings.encoder import get_encoder
from momentum.models.session import SessionRecord
from momentum.discovery.sequence_extractor import extract_sequence


def cluster_sessions(
    sessions: List[SessionRecord],
    eps: float = 0.35,
    min_samples: int = 3,
) -> Tuple[List[List[dict]], List[List[int]], np.ndarray]:
    sequences = []
    valid_indices = []

    for i, session in enumerate(sessions):
        seq = extract_sequence(session, min_length=3)
        if seq is not None:
            sequences.append(seq)
            valid_indices.append(i)

    if len(sequences) < min_samples:
        return sequences, [], np.array([])

    encoder = get_encoder()
    encoder.fit(sequences)
    embeddings = encoder.encode_batch(sequences)

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
    cluster_sequences = [[sequences[i] for i in group] for group in cluster_groups]

    return sequences, cluster_groups, embeddings


def get_cluster_embedding(
    embeddings: np.ndarray,
    indices: List[int],
) -> np.ndarray:
    if not indices:
        return np.zeros(embeddings.shape[1], dtype=np.float32)
    cluster_vecs = embeddings[indices]
    centroid = cluster_vecs.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm
    return centroid.astype(np.float32)


compute_cluster_embedding = get_cluster_embedding


def compute_cluster_coherence(
    embeddings: np.ndarray,
    indices: List[int],
) -> float:
    if len(indices) < 2:
        return 1.0
    vecs = embeddings[indices]
    sim_matrix = vecs @ vecs.T
    n = len(indices)
    off_diag = (sim_matrix.sum() - n) / max(n * (n - 1), 1)
    return float(np.clip(off_diag, 0.0, 1.0))
