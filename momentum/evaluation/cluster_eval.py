import numpy as np
from typing import List, Dict, Tuple
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

def evaluate_clusters(
    ground_truth_labels: List[str], 
    cluster_groups: List[List[int]], 
    valid_indices: List[int],
    total_sessions: int
) -> Dict[str, float]:
    """
    Evaluates discovered clusters against ground truth labels.
    """
    if total_sessions == 0:
        return {}

    pred_labels = np.full(total_sessions, -1)
    
    for cluster_id, seq_indices in enumerate(cluster_groups):
        for seq_idx in seq_indices:
            orig_idx = valid_indices[seq_idx]
            pred_labels[orig_idx] = cluster_id
            
    signal_indices = [i for i, label in enumerate(ground_truth_labels) if label != "noise"]
    clustered_signal = sum(1 for i in signal_indices if pred_labels[i] != -1)
    
    coverage = clustered_signal / len(signal_indices) if signal_indices else 0.0
    
    noise_rate = sum(1 for p in pred_labels if p == -1) / total_sessions
    
    ari = adjusted_rand_score(ground_truth_labels, pred_labels)
    nmi = normalized_mutual_info_score(ground_truth_labels, pred_labels)
    
    total_clustered = sum(len(group) for group in cluster_groups)
    majority_sum = 0
    
    for seq_indices in cluster_groups:
        cluster_labels = [ground_truth_labels[valid_indices[i]] for i in seq_indices]
        if not cluster_labels:
            continue
        
        counts = {}
        for l in cluster_labels:
            counts[l] = counts.get(l, 0) + 1
            
        majority_sum += max(counts.values())
        
    purity = majority_sum / total_clustered if total_clustered > 0 else 0.0
    
    return {
        "ari": float(ari),
        "nmi": float(nmi),
        "purity": float(purity),
        "coverage": float(coverage),
        "noise_rate": float(noise_rate),
        "n_clusters": len(cluster_groups)
    }
