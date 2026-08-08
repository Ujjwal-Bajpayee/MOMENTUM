from sqlalchemy import String, Float, DateTime, Text, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from momentum.database.base import Base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
import uuid
import json

class AutomationRecord(Base):
    __tablename__ = "automations"
    __table_args__ = (
        Index("ix_automations_status", "status"),
        Index("ix_automations_opportunity_id", "opportunity_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    opportunity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    trigger_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tools_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    autonomy_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_time_saved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    replay_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def get_plan(self) -> Dict:
        if self.plan_json:
            return json.loads(self.plan_json)
        return {}

    def get_tools(self) -> List[str]:
        if self.tools_json:
            return json.loads(self.tools_json)
        return []

    def get_permissions(self) -> List[str]:
        if self.permissions_json:
            return json.loads(self.permissions_json)
        return []

    def get_trigger(self) -> Dict:
        if self.trigger_json:
            return json.loads(self.trigger_json)
        return {}

    def get_conditions(self) -> List[str]:
        if self.conditions_json:
            return json.loads(self.conditions_json)
        return []

class AutomationSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    opportunity_id: str
    workflow_id: str
    name: str
    autonomy_level: int = 3
    confidence: float = 0.0
    status: str = "active"
    created_at: datetime
    last_executed_at: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_time_saved: float = 0.0
    consecutive_failures: int = 0
    replay_accuracy: float = 0.0
