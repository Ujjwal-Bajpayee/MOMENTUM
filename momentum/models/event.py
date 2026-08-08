from sqlalchemy import String, Float, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from momentum.database.base import Base
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid
import json

EVENT_TYPES = [
    "application_open",
    "application_close",
    "window_change",
    "terminal_command",
    "git_command",
    "github_event",
    "ci_event",
    "browser_navigation",
    "editor_event",
    "docker_event",
    "postman_event",
    "jupyter_event",
    "idle",
    "file_activity",
    "communication_event",
    "pr_event",
    "incident_event",
]

class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_timestamp", "timestamp"),
        Index("ix_events_session_id", "session_id"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_application", "application"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    application: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    target: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="collector"
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    privacy_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="public"
    )

    def get_metadata(self) -> dict:
        if self.metadata_json:
            return json.loads(self.metadata_json)
        return {}

class EventCreate(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    application: str
    event_type: str
    action: Optional[str] = None
    target: Optional[str] = None
    metadata: Optional[dict] = None
    duration: Optional[float] = None
    source: str = "collector"
    session_id: Optional[str] = None
    privacy_level: str = "public"

class EventSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    timestamp: datetime
    application: str
    event_type: str
    action: Optional[str] = None
    target: Optional[str] = None
    duration: Optional[float] = None
    source: str
    session_id: Optional[str] = None
    privacy_level: str
