import pytest
from momentum.evaluation.cluster_eval import evaluate_clusters

def test_evaluate_clusters_perfect():
                                    
    labels = ["A", "A", "B", "B", "noise"]
    valid_indices = [0, 1, 2, 3, 4]
    cluster_groups = [[0, 1], [2, 3]]
    
    metrics = evaluate_clusters(labels, cluster_groups, valid_indices, 5)
    
    assert metrics["purity"] == 1.0
    assert metrics["coverage"] == 1.0                                 
    assert metrics["noise_rate"] == 0.2                      
    assert metrics["n_clusters"] == 2
    assert metrics["ari"] > 0.99
    
def test_evaluate_clusters_imperfect():
                                 
    labels = ["A", "B", "C", "C", "C"]
    valid_indices = [0, 1, 2, 3, 4]
    cluster_groups = [[0, 1], [2, 3, 4]]
    
    metrics = evaluate_clusters(labels, cluster_groups, valid_indices, 5)
    
    assert metrics["purity"] == 0.8
    assert metrics["coverage"] == 1.0
    assert metrics["noise_rate"] == 0.0
    assert metrics["n_clusters"] == 2
    
def test_evaluate_clusters_empty():
    metrics = evaluate_clusters([], [], [], 0)
    assert metrics == {}
