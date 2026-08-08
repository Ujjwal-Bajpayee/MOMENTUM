from momentum.simulation.generator import SyntheticEventGenerator
from momentum.models.event import EventCreate


def test_generator_produces_events():
    gen = SyntheticEventGenerator(seed=42)
    events = gen.generate_days(num_days=1)
    assert len(events) > 50


def test_generator_7_days():
    gen = SyntheticEventGenerator(seed=42)
    events = gen.generate_days(num_days=7)
    assert len(events) > 500


def test_generator_event_types():
    gen = SyntheticEventGenerator(seed=42)
    events = gen.generate_days(num_days=2)
    event_types = {e.event_type for e in events}
    assert "terminal_command" in event_types
    assert "browser_navigation" in event_types
    assert "ci_event" in event_types


def test_generator_ci_chain_embedded():
    gen = SyntheticEventGenerator(seed=42)
    events = gen.generate_days(num_days=3)
    ci_failures = [e for e in events if e.event_type == "ci_event" and e.action == "build_failed"]
    slack_events = [e for e in events if e.event_type == "communication_event"]
    assert len(ci_failures) > 5
    assert len(slack_events) > 0


def test_generator_events_sorted():
    gen = SyntheticEventGenerator(seed=42)
    events = gen.generate_days(num_days=2)
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)


def test_generator_no_labels_in_events():
    gen = SyntheticEventGenerator(seed=42)
    events = gen.generate_days(num_days=1)
    for event in events:
        assert "ci_investigation" not in (event.event_type or "").lower()
        assert "workflow" not in (event.event_type or "").lower()
        meta = event.metadata or {}
        assert "workflow_type" not in meta
        assert "pattern_label" not in meta
