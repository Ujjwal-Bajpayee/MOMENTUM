import pytest
from datetime import datetime, timedelta
from momentum.simulation.generator import create_generator
from momentum.database.event_store import store_events_bulk
from momentum.sessions.session_manager import session_manager
from momentum.discovery.discovery_engine import discovery_engine
from momentum.database.base import get_db
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord

def test_e2e_discovery_pipeline(tmp_db):
    """
    Test the full end-to-end pipeline:
    1. Generate synthetic events
    2. Store them in the database
    3. Sessionize the events
    4. Discover workflows and opportunities
    """
    generator = create_generator(seed=42)
    start_date = datetime.utcnow() - timedelta(days=7)
    events = generator.generate_days(num_days=7, start_date=start_date)
    
    assert len(events) > 100, "Should generate a substantial number of events"
    
    stored = store_events_bulk(events)
    assert stored == len(events), "All events should be stored"
    
    sessions_created = session_manager.run_sessionization(
        start_time=start_date,
        end_time=datetime.utcnow(),
    )
    assert sessions_created > 10, "Should create several sessions"
    
    workflows, opportunities = discovery_engine.run(
        start_time=start_date,
        end_time=datetime.utcnow(),
    )
    
    assert len(workflows) > 0, "Should discover at least one workflow"
    assert len(opportunities) > 0, "Should score and identify at least one opportunity"
    
    with get_db() as db:
        saved_wfs = db.query(WorkflowRecord).all()
        saved_opps = db.query(OpportunityRecord).all()
        assert len(saved_wfs) == len(workflows)
        assert len(saved_opps) == len(opportunities)