from sqlalchemy import String, Float, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from momentum.database.base import Base
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import uuid
import json


class SessionRecord(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_start_time", "start_time"),
        Index("ix_sessions_repository", "repository"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    applications_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repository: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_sequence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dominant_context: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    developer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def get_applications(self) -> List[str]:
        if self.applications_json:
            return json.loads(self.applications_json)
        return []

    def get_event_sequence(self) -> List[dict]:
        if self.event_sequence_json:
            return json.loads(self.event_sequence_json)
        return []


class SessionCreate(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    applications: List[str] = Field(default_factory=list)
    repository: Optional[str] = None
    event_count: int = 0
    event_sequence: List[dict] = Field(default_factory=list)
    dominant_context: Optional[str] = None
    developer_id: Optional[str] = None


class SessionSchema(BaseModel):
    model_config = {"from_attributes": True}

    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    repository: Optional[str] = None
    event_count: int = 0
    dominant_context: Optional[str] = None
    developer_id: Optional[str] = None
