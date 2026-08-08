from sqlalchemy import String, Float, DateTime, Text, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from momentum.database.base import Base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
import uuid
import json


class OutcomeRecord(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        Index("ix_outcomes_automation_id", "automation_id"),
        Index("ix_outcomes_timestamp", "timestamp"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    automation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    trigger: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    context_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    human_intervention: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    user_feedback: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    reward: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    policy_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    autonomy_before: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    autonomy_after: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    time_saved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def get_context(self) -> Dict:
        if self.context_json:
            return json.loads(self.context_json)
        return {}

    def get_actions(self) -> List[Dict]:
        if self.actions_json:
            return json.loads(self.actions_json)
        return []


class OutcomeSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    automation_id: str
    timestamp: datetime
    execution_time: float = 0.0
    success: bool = False
    failure_reason: Optional[str] = None
    human_intervention: bool = False
    user_feedback: Optional[str] = None
    reward: float = 0.0
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    autonomy_before: int = 3
    autonomy_after: int = 3
    time_saved: float = 0.0
