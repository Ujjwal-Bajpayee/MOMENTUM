from fastapi import APIRouter, HTTPException
from momentum.discovery.workflow_builder import get_all_workflows, get_workflow_by_id

router = APIRouter()


@router.get("/workflows")
def list_workflows():
    workflows = get_all_workflows()
    return [
        {
            "id": w.id,
            "name": w.name,
            "trigger": w.trigger,
            "frequency": w.frequency,
            "automation_score": w.automation_score,
            "confidence": w.confidence,
            "determinism_score": w.determinism_score,
            "risk_score": w.risk_score,
            "estimated_weekly_minutes": w.estimated_weekly_minutes,
            "status": w.status,
            "session_count": len(w.get_session_ids()),
        }
        for w in workflows
    ]


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    workflow = get_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": workflow.id,
        "name": workflow.name,
        "trigger": workflow.trigger,
        "goal": workflow.goal,
        "steps": workflow.get_steps(),
        "applications": workflow.get_applications(),
        "evidence": workflow.get_evidence(),
        "frequency": workflow.frequency,
        "automation_score": workflow.automation_score,
        "confidence": workflow.confidence,
        "determinism_score": workflow.determinism_score,
        "risk_score": workflow.risk_score,
        "decision_points": workflow.get_decision_points(),
        "estimated_weekly_minutes": workflow.estimated_weekly_minutes,
        "estimated_annual_minutes": workflow.estimated_annual_minutes,
        "status": workflow.status,
    }
