from datetime import datetime
from typing import Optional, List
from momentum.database.base import get_db
from momentum.models.event import EventRecord, EventCreate
import json


def store_event(event: EventCreate) -> str:
    with get_db() as db:
        record = EventRecord(
            timestamp=event.timestamp,
            application=event.application,
            event_type=event.event_type,
            action=event.action,
            target=event.target,
            metadata_json=json.dumps(event.metadata) if event.metadata else None,
            duration=event.duration,
            source=event.source,
            session_id=event.session_id,
            privacy_level=event.privacy_level,
        )
        db.add(record)
        db.flush()
        return record.id


def store_events_bulk(events: List[EventCreate]) -> int:
    with get_db() as db:
        records = [
            EventRecord(
                timestamp=e.timestamp,
                application=e.application,
                event_type=e.event_type,
                action=e.action,
                target=e.target,
                metadata_json=json.dumps(e.metadata) if e.metadata else None,
                duration=e.duration,
                source=e.source,
                session_id=e.session_id,
                privacy_level=e.privacy_level,
            )
            for e in events
        ]
        db.bulk_save_objects(records)
        return len(records)


def get_events(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    event_type: Optional[str] = None,
    application: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 2000,
    offset: int = 0,
) -> List[EventRecord]:
    with get_db() as db:
        q = db.query(EventRecord)
        if start_time:
            q = q.filter(EventRecord.timestamp >= start_time)
        if end_time:
            q = q.filter(EventRecord.timestamp <= end_time)
        if event_type:
            q = q.filter(EventRecord.event_type == event_type)
        if application:
            q = q.filter(EventRecord.application == application)
        if session_id:
            q = q.filter(EventRecord.session_id == session_id)
        return q.order_by(EventRecord.timestamp).offset(offset).limit(limit).all()


def count_events(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> int:
    with get_db() as db:
        q = db.query(EventRecord)
        if start_time:
            q = q.filter(EventRecord.timestamp >= start_time)
        if end_time:
            q = q.filter(EventRecord.timestamp <= end_time)
        return q.count()


def get_events_for_session(session_id: str) -> List[EventRecord]:
    with get_db() as db:
        return (
            db.query(EventRecord)
            .filter(EventRecord.session_id == session_id)
            .order_by(EventRecord.timestamp)
            .all()
        )


def delete_all_events() -> int:
    with get_db() as db:
        count = db.query(EventRecord).count()
        db.query(EventRecord).delete()
        return count
