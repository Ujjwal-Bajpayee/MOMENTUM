from fastapi import APIRouter, HTTPException
from typing import Optional
from momentum.database.base import get_db
from momentum.models.automation import AutomationRecord
from momentum.models.outcome import OutcomeRecord
from momentum.execution.executor import execute_automation
from momentum.execution.outcome_recorder import record_and_learn, get_outcomes_for_automation

router = APIRouter()

@router.get("/automations")
def list_automations():
    with get_db() as db:
        automations = db.query(AutomationRecord).all()
        result = [
            {
                "id": a.id,
                "name": a.name,
                "opportunity_id": a.opportunity_id,
                "workflow_id": a.workflow_id,
                "confidence": a.confidence,
                "autonomy_level": a.autonomy_level,
                "status": a.status,
                "execution_count": a.execution_count,
                "success_count": a.success_count,
                "failure_count": a.failure_count,
                "total_time_saved": a.total_time_saved,
                "last_executed_at": a.last_executed_at.isoformat() if a.last_executed_at else None,
            }
            for a in automations
        ]
    return result

@router.post("/automations/{automation_id}/run")
def run_automation(automation_id: str, dry_run: bool = False):
    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation_id).first()
        if not auto:
            raise HTTPException(status_code=404, detail="Automation not found")

    outcome = execute_automation(auto, dry_run=dry_run)
    learn_result = record_and_learn(outcome, auto)

    return {
        "automation_id": automation_id,
        "success": outcome.success,
        "execution_time": outcome.execution_time,
        "time_saved": outcome.time_saved,
        "dry_run": dry_run,
        "reward": learn_result["reward"],
        "confidence_after": learn_result["confidence_after"],
        "autonomy_after": learn_result["autonomy_after"],
    }

@router.post("/automations/{automation_id}/pause")
def pause_automation(automation_id: str):
    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation_id).first()
        if not auto:
            raise HTTPException(status_code=404, detail="Automation not found")
        auto.status = "paused"
    return {"status": "paused", "automation_id": automation_id}

@router.post("/automations/{automation_id}/resume")
def resume_automation(automation_id: str):
    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation_id).first()
        if not auto:
            raise HTTPException(status_code=404, detail="Automation not found")
        auto.status = "active"
    return {"status": "active", "automation_id": automation_id}

@router.get("/automations/{automation_id}/outcomes")
def get_automation_outcomes(automation_id: str):
    outcomes = get_outcomes_for_automation(automation_id)
    return [
        {
            "id": o.id,
            "timestamp": o.timestamp.isoformat(),
            "success": o.success,
            "execution_time": o.execution_time,
            "time_saved": o.time_saved,
            "reward": o.reward,
            "failure_reason": o.failure_reason,
            "human_intervention": o.human_intervention,
            "confidence_before": o.confidence_before,
            "confidence_after": o.confidence_after,
            "autonomy_before": o.autonomy_before,
            "autonomy_after": o.autonomy_after,
        }
        for o in outcomes
    ]
