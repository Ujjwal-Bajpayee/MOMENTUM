from sqlalchemy import String, Float, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from momentum.database.base import Base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
import uuid
import json


class OpportunityRecord(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_status", "status"),
        Index("ix_opportunities_workflow_id", "workflow_id"),
        Index("ix_opportunities_automation_score", "automation_score"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    automation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="medium"
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    estimated_weekly_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    estimated_annual_minutes: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    frequency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_automation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_permissions_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replay_results_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    action_taken: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def get_required_permissions(self) -> List[str]:
        if self.required_permissions_json:
            return json.loads(self.required_permissions_json)
        return []

    def get_evidence(self) -> List[Dict]:
        if self.evidence_json:
            return json.loads(self.evidence_json)
        return []

    def get_replay_results(self) -> Dict:
        if self.replay_results_json:
            return json.loads(self.replay_results_json)
        return {}


class OpportunitySchema(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    workflow_id: str
    name: str
    automation_score: float = 0.0
    confidence: float = 0.0
    risk_level: str = "medium"
    risk_score: float = 0.5
    estimated_weekly_minutes: float = 0.0
    estimated_annual_minutes: float = 0.0
    frequency: float = 0.0
    reasoning: Optional[str] = None
    proposed_automation: Optional[str] = None
    status: str = "pending"
    created_at: datetime
    action_taken: Optional[str] = None
