import pytest
from datetime import datetime
import json
from momentum.models.session import SessionRecord
from momentum.discovery.clusterer import cluster_sessions

def test_cluster_sessions_index_mapping():
                       
    sessions = []
    
    s0 = SessionRecord(session_id="s0", start_time=datetime.now())
    s0.event_sequence_json = json.dumps([{"event_type": "app_focused", "application": "app1"}])
    sessions.append(s0)

    s1 = SessionRecord(session_id="s1", start_time=datetime.now())
    s1.event_sequence_json = json.dumps([{"event_type": "app_focused", "application": "app2"} for _ in range(3)])
    sessions.append(s1)

    s2 = SessionRecord(session_id="s2", start_time=datetime.now())
    s2.event_sequence_json = json.dumps([{"event_type": "app_focused", "application": "app1"}])
    sessions.append(s2)

    s3 = SessionRecord(session_id="s3", start_time=datetime.now())
    s3.event_sequence_json = json.dumps([{"event_type": "app_focused", "application": "app2"} for _ in range(3)])
    sessions.append(s3)

    s4 = SessionRecord(session_id="s4", start_time=datetime.now())
    s4.event_sequence_json = json.dumps([{"event_type": "app_focused", "application": "app2"} for _ in range(3)])
    sessions.append(s4)

    sequences, cluster_groups, embeddings, valid_indices = cluster_sessions(
        sessions, eps=0.5, min_samples=2
    )

    assert valid_indices == [1, 3, 4]

    assert len(sequences) == 3

    if cluster_groups:
        group = cluster_groups[0]
                                                  
        assert set(group) == {0, 1, 2}
        
        mapped = [valid_indices[i] for i in group]
        assert set(mapped) == {1, 3, 4}
