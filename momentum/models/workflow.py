from sqlalchemy import String, Float, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from momentum.database.base import Base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
import uuid
import json

class WorkflowRecord(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_status", "status"),
        Index("ix_workflows_automation_score", "automation_score"),
        Index("ix_workflows_confidence", "confidence"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    trigger: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    frequency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    average_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    median_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_variance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    applications_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repositories_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_points_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    repetition_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    determinism_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    automation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_weekly_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    estimated_annual_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    similar_workflows_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="discovered"
    )
    session_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def get_steps(self) -> List[Dict]:
        if self.steps_json:
            return json.loads(self.steps_json)
        return []

    def get_applications(self) -> List[str]:
        if self.applications_json:
            return json.loads(self.applications_json)
        return []

    def get_evidence(self) -> List[Dict]:
        if self.evidence_json:
            return json.loads(self.evidence_json)
        return []

    def get_session_ids(self) -> List[str]:
        if self.session_ids_json:
            return json.loads(self.session_ids_json)
        return []

    def get_decision_points(self) -> List[str]:
        if self.decision_points_json:
            return json.loads(self.decision_points_json)
        return []

    def get_similar_workflows(self) -> List[str]:
        if self.similar_workflows_json:
            return json.loads(self.similar_workflows_json)
        return []

class WorkflowSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    trigger: Optional[str] = None
    goal: Optional[str] = None
    frequency: float = 0.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    average_duration: float = 0.0
    median_duration: float = 0.0
    duration_variance: float = 0.0
    success_rate: float = 1.0
    repetition_score: float = 0.0
    determinism_score: float = 0.0
    risk_score: float = 0.5
    automation_score: float = 0.0
    confidence: float = 0.0
    estimated_weekly_minutes: float = 0.0
    estimated_annual_minutes: float = 0.0
    status: str = "discovered"
