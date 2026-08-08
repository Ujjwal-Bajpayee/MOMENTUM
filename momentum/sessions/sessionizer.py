from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from momentum.models.event import EventRecord
from momentum.models.session import SessionRecord, SessionCreate
from momentum.database.base import get_db
import json
import uuid

SESSION_GAP_SECONDS = 300
MIN_SESSION_EVENTS = 2

@dataclass
class ActiveSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    events: List[EventRecord] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    repository: Optional[str] = None
    developer_id: Optional[str] = None

    def add_event(self, event: EventRecord):
        self.events.append(event)
        self.end_time = event.timestamp
        if event.application not in self.applications:
            self.applications.append(event.application)
        repo = self._extract_repo(event)
        if repo and not self.repository:
            self.repository = repo

    def _extract_repo(self, event: EventRecord) -> Optional[str]:
        meta = event.get_metadata()
        return meta.get("repo") or meta.get("repository")

    @property
    def duration(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def event_count(self) -> int:
        return len(self.events)

    def get_dominant_context(self) -> str:
        if not self.applications:
            return "unknown"
        app_counts: Dict[str, int] = {}
        for app in self.applications:
            app_counts[app] = app_counts.get(app, 0) + 1
        return max(app_counts, key=app_counts.get)

    def get_event_sequence(self) -> List[dict]:
        return [
            {
                "event_type": e.event_type,
                "application": e.application,
                "action": e.action or "",
                "target": e.target or "",
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.events
        ]

class Sessionizer:
    def __init__(self, gap_seconds: float = SESSION_GAP_SECONDS):
        self.gap_seconds = gap_seconds
        self._active_sessions: Dict[str, ActiveSession] = {}

    def process_events(self, events: List[EventRecord]) -> List[SessionCreate]:
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        sessions: List[ActiveSession] = []
        current: Optional[ActiveSession] = None

        for event in sorted_events:
            if event.event_type == "idle" and (event.duration or 0) > self.gap_seconds:
                if current and current.event_count >= MIN_SESSION_EVENTS:
                    sessions.append(current)
                current = None
                continue

            if current is None:
                current = ActiveSession(
                    start_time=event.timestamp,
                    developer_id=event.get_metadata().get("developer_id"),
                )
                current.add_event(event)
            else:
                gap = (event.timestamp - current.end_time).total_seconds()
                if gap > self.gap_seconds:
                    if current.event_count >= MIN_SESSION_EVENTS:
                        sessions.append(current)
                    current = ActiveSession(
                        start_time=event.timestamp,
                        developer_id=event.get_metadata().get("developer_id"),
                    )
                current.add_event(event)

        if current and current.event_count >= MIN_SESSION_EVENTS:
            sessions.append(current)

        return [self._to_session_create(s) for s in sessions]

    def _to_session_create(self, s: ActiveSession) -> SessionCreate:
        return SessionCreate(
            session_id=s.session_id,
            start_time=s.start_time,
            end_time=s.end_time,
            duration=s.duration,
            applications=list(set(s.applications)),
            repository=s.repository,
            event_count=s.event_count,
            event_sequence=s.get_event_sequence(),
            dominant_context=s.get_dominant_context(),
            developer_id=s.developer_id,
        )

def save_sessions(sessions: List[SessionCreate]) -> int:
    with get_db() as db:
        records = [
            SessionRecord(
                session_id=s.session_id,
                start_time=s.start_time,
                end_time=s.end_time,
                duration=s.duration,
                applications_json=json.dumps(s.applications),
                repository=s.repository,
                event_count=s.event_count,
                event_sequence_json=json.dumps(s.event_sequence),
                dominant_context=s.dominant_context,
                developer_id=s.developer_id,
            )
            for s in sessions
        ]
        db.bulk_save_objects(records)
        return len(records)

def get_sessions(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 500,
) -> List[SessionRecord]:
    with get_db() as db:
        q = db.query(SessionRecord)
        if start_time:
            q = q.filter(SessionRecord.start_time >= start_time)
        if end_time:
            q = q.filter(SessionRecord.start_time <= end_time)
        return q.order_by(SessionRecord.start_time).limit(limit).all()

def count_sessions() -> int:
    with get_db() as db:
        return db.query(SessionRecord).count()
