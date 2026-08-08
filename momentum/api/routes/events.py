from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
from momentum.database.event_store import get_events, count_events
from momentum.models.event import EventSchema

router = APIRouter()


@router.get("/events", response_model=list)
def list_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
    application: Optional[str] = Query(None),
):
    records = get_events(
        event_type=event_type,
        application=application,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "application": r.application,
            "event_type": r.event_type,
            "action": r.action,
            "target": r.target,
            "source": r.source,
            "session_id": r.session_id,
        }
        for r in records
    ]


@router.get("/events/count")
def event_count():
    return {"count": count_events()}
