from datetime import datetime
from momentum.models.event import EventCreate, EventRecord
from momentum.database.event_store import store_event, get_events, count_events, store_events_bulk

def test_store_single_event():
    event = EventCreate(
        timestamp=datetime.utcnow(),
        application="test_app",
        event_type="terminal_command",
        action="git status",
        source="test",
    )
    event_id = store_event(event)
    assert event_id is not None
    assert len(event_id) > 0

def test_store_bulk_events():
    events = [
        EventCreate(
            timestamp=datetime.utcnow(),
            application=f"app_{i}",
            event_type="terminal_command",
            action=f"cmd_{i}",
            source="test",
        )
        for i in range(5)
    ]
    count = store_events_bulk(events)
    assert count == 5

def test_get_events_filter_by_type():
    events = get_events(event_type="terminal_command", limit=100)
    assert all(e.event_type == "terminal_command" for e in events)

def test_count_events():
    count = count_events()
    assert count >= 6

def test_event_metadata():
    event = EventCreate(
        timestamp=datetime.utcnow(),
        application="browser",
        event_type="browser_navigation",
        action="navigate",
        target="github.com",
        metadata={"title": "GitHub - PR Review", "commit": "abc123"},
        source="test",
    )
    store_event(event)
    events = get_events(event_type="browser_navigation", limit=10)
    assert any(e.application == "browser" for e in events)
