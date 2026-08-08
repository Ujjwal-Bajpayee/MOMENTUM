from fastapi import APIRouter, HTTPException
from datetime import datetime
from momentum.discovery.opportunity_engine import get_all_opportunities, get_opportunity_by_id
from momentum.discovery.workflow_builder import get_workflow_by_id
from momentum.database.base import get_db
from momentum.models.opportunity import OpportunityRecord

router = APIRouter()


@router.get("/opportunities")
def list_opportunities():
    opps = get_all_opportunities()
    return [
        {
            "id": o.id,
            "workflow_id": o.workflow_id,
            "name": o.name,
            "automation_score": o.automation_score,
            "confidence": o.confidence,
            "risk_level": o.risk_level,
            "estimated_weekly_minutes": o.estimated_weekly_minutes,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in opps
    ]


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: str):
    opp = get_opportunity_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {
        "id": opp.id,
        "workflow_id": opp.workflow_id,
        "name": opp.name,
        "automation_score": opp.automation_score,
        "confidence": opp.confidence,
        "risk_level": opp.risk_level,
        "risk_score": opp.risk_score,
        "estimated_weekly_minutes": opp.estimated_weekly_minutes,
        "estimated_annual_minutes": opp.estimated_annual_minutes,
        "frequency": opp.frequency,
        "reasoning": opp.reasoning,
        "proposed_automation": opp.proposed_automation,
        "required_permissions": opp.get_required_permissions(),
        "status": opp.status,
    }


@router.post("/opportunities/{opportunity_id}/approve")
def approve_opportunity(opportunity_id: str):
    with get_db() as db:
        opp = db.query(OpportunityRecord).filter(OpportunityRecord.id == opportunity_id).first()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        opp.status = "approved"
        opp.approved_at = datetime.utcnow()
        opp.action_taken = "approved"
    return {"status": "approved", "opportunity_id": opportunity_id}


@router.post("/opportunities/{opportunity_id}/reject")
def reject_opportunity(opportunity_id: str, reason: str = "user_rejected"):
    with get_db() as db:
        opp = db.query(OpportunityRecord).filter(OpportunityRecord.id == opportunity_id).first()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        opp.status = "rejected"
        opp.rejected_at = datetime.utcnow()
        opp.rejection_reason = reason
        opp.action_taken = "rejected"
    return {"status": "rejected", "opportunity_id": opportunity_id}
