import json
import logging
from datetime import datetime
from typing import Optional
from momentum.models.outcome import OutcomeRecord
from momentum.models.automation import AutomationRecord
from momentum.learning.trainer import process_outcome
from momentum.policy.policy import compute_autonomy_level
from momentum.database.base import get_db

logger = logging.getLogger(__name__)


def record_and_learn(
    outcome: OutcomeRecord,
    automation: AutomationRecord,
    workflow_data: Optional[dict] = None,
) -> dict:
    reward = process_outcome(outcome, automation, workflow_data)

    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation.id).first()
        if auto:
            new_autonomy = compute_autonomy_level(
                current_level=auto.autonomy_level,
                success=outcome.success,
                risk_score=workflow_data.get("risk_score", 0.3) if workflow_data else 0.3,
                confidence=auto.confidence,
                consecutive_failures=auto.consecutive_failures,
                execution_count=auto.execution_count,
                success_count=auto.success_count,
            )

            out_record = db.query(OutcomeRecord).filter(OutcomeRecord.id == outcome.id).first()
            if out_record:
                out_record.autonomy_after = new_autonomy

            auto.autonomy_level = new_autonomy

    return {
        "reward": reward,
        "success": outcome.success,
        "time_saved": outcome.time_saved,
        "execution_time": outcome.execution_time,
        "confidence_before": outcome.confidence_before,
        "confidence_after": outcome.confidence_after,
        "autonomy_before": outcome.autonomy_before,
        "autonomy_after": outcome.autonomy_after,
    }


def get_outcomes_for_automation(automation_id: str) -> list:
    with get_db() as db:
        return (
            db.query(OutcomeRecord)
            .filter(OutcomeRecord.automation_id == automation_id)
            .order_by(OutcomeRecord.timestamp.desc())
            .limit(50)
            .all()
        )
