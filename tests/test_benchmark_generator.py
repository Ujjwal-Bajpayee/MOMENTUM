import pytest
from momentum.evaluation.benchmark_generator import BenchmarkGenerator, WORKFLOW_TYPES

def test_benchmark_generator_determinism():
    gen1 = BenchmarkGenerator(seed=42)
    sessions1, labels1 = gen1.generate_dataset(num_sessions=10)
    
    gen2 = BenchmarkGenerator(seed=42)
    sessions2, labels2 = gen2.generate_dataset(num_sessions=10)
    
    assert labels1 == labels2
    assert len(sessions1) == len(sessions2)
    
    for s1, s2 in zip(sessions1, sessions2):
        assert s1.session_id == s2.session_id
        assert s1.start_time == s2.start_time
        assert s1.event_sequence_json == s2.event_sequence_json

def test_benchmark_generator_labels_and_data():
    gen = BenchmarkGenerator(seed=123)
    sessions, labels = gen.generate_dataset(num_sessions=50)
    
    assert len(sessions) == 50
    assert len(labels) == 50
    
    for s, l in zip(sessions, labels):
        assert l in WORKFLOW_TYPES
                                                                
        assert l not in s.event_sequence_json
        
        assert s.session_id is not None
        assert s.start_time is not None
        assert s.event_sequence_json is not None
