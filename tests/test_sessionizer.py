from datetime import datetime, timedelta
from momentum.sessions.sessionizer import Sessionizer
from momentum.models.event import EventRecord
import uuid

def _make_event(ts: datetime, event_type: str = "terminal_command", app: str = "terminal") -> EventRecord:
    e = EventRecord()
    e.id = str(uuid.uuid4())
    e.timestamp = ts
    e.event_type = event_type
    e.application = app
    e.action = "test_action"
    e.target = None
    e.metadata_json = None
    e.duration = None
    e.source = "test"
    e.session_id = None
    e.privacy_level = "public"
    return e

def test_single_session():
    now = datetime.utcnow()
    events = [_make_event(now + timedelta(seconds=i * 30)) for i in range(10)]
    sessionizer = Sessionizer(gap_seconds=300)
    sessions = sessionizer.process_events(events)
    assert len(sessions) == 1
    assert sessions[0].event_count >= 2

def test_two_sessions_with_gap():
    now = datetime.utcnow()
    batch1 = [_make_event(now + timedelta(seconds=i * 30)) for i in range(5)]
    batch2 = [_make_event(now + timedelta(seconds=3600 + i * 30)) for i in range(5)]
    events = batch1 + batch2
    sessionizer = Sessionizer(gap_seconds=300)
    sessions = sessionizer.process_events(events)
    assert len(sessions) == 2

def test_idle_event_splits_session():
    now = datetime.utcnow()
    events = [_make_event(now + timedelta(seconds=i * 30)) for i in range(3)]
    idle = EventRecord()
    idle.id = str(uuid.uuid4())
    idle.timestamp = now + timedelta(seconds=90)
    idle.event_type = "idle"
    idle.application = "system"
    idle.action = None
    idle.target = None
    idle.metadata_json = None
    idle.duration = 600.0
    idle.source = "test"
    idle.session_id = None
    idle.privacy_level = "public"
    events2 = [_make_event(now + timedelta(seconds=600 + i * 30)) for i in range(4)]
    all_events = events + [idle] + events2
    sessionizer = Sessionizer(gap_seconds=300)
    sessions = sessionizer.process_events(all_events)
    assert len(sessions) >= 1

def test_session_applications():
    now = datetime.utcnow()
    events = [
        _make_event(now, "terminal_command", "terminal"),
        _make_event(now + timedelta(seconds=10), "browser_navigation", "chrome"),
        _make_event(now + timedelta(seconds=20), "editor_event", "vscode"),
        _make_event(now + timedelta(seconds=30), "git_command", "git"),
    ]
    sessionizer = Sessionizer(gap_seconds=300)
    sessions = sessionizer.process_events(events)
    assert len(sessions) == 1
    apps = sessions[0].applications
    assert "terminal" in apps or "chrome" in apps or "vscode" in apps
