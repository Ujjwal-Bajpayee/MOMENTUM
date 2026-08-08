import json
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord
from momentum.database.base import get_db
import uuid


WEIGHT_FREQUENCY = 0.20
WEIGHT_TIME_COST = 0.20
WEIGHT_REPETITION = 0.15
WEIGHT_DETERMINISM = 0.20
WEIGHT_RISK_INVERSE = 0.10
WEIGHT_SAVINGS = 0.15


def _score_frequency(frequency: float) -> float:
    return float(np.clip(frequency / 25.0, 0.0, 1.0))


def _score_time_cost(weekly_minutes: float) -> float:
    return float(np.clip(weekly_minutes / 300.0, 0.0, 1.0))


def _score_repetition(repetition_score: float) -> float:
    return float(np.clip(repetition_score, 0.0, 1.0))


def _score_determinism(determinism_score: float) -> float:
    return float(np.clip(determinism_score, 0.0, 1.0))


def _score_risk_inverse(risk_score: float) -> float:
    return 1.0 - float(np.clip(risk_score, 0.0, 1.0))


def _score_savings(annual_minutes: float) -> float:
    return float(np.clip(annual_minutes / 5000.0, 0.0, 1.0))


def compute_automation_score(workflow: WorkflowRecord) -> float:
    freq_score = _score_frequency(workflow.frequency)
    time_score = _score_time_cost(workflow.estimated_weekly_minutes)
    rep_score = _score_repetition(workflow.repetition_score)
    det_score = _score_determinism(workflow.determinism_score)
    risk_inv = _score_risk_inverse(workflow.risk_score)
    sav_score = _score_savings(workflow.estimated_annual_minutes)

    raw = (
        WEIGHT_FREQUENCY * freq_score
        + WEIGHT_TIME_COST * time_score
        + WEIGHT_REPETITION * rep_score
        + WEIGHT_DETERMINISM * det_score
        + WEIGHT_RISK_INVERSE * risk_inv
        + WEIGHT_SAVINGS * sav_score
    )
    return float(np.clip(raw * 100.0, 0.0, 100.0))


def compute_confidence(
    workflow: WorkflowRecord,
    historical_successes: int = 0,
    total_historical: int = 0,
) -> float:
    base = workflow.confidence

    evidence_count = len(workflow.get_session_ids())
    evidence_boost = min(evidence_count / 50.0, 0.25)

    determinism_boost = workflow.determinism_score * 0.20

    historical_boost = 0.0
    if total_historical > 0:
        historical_boost = (historical_successes / total_historical) * 0.15

    variance_penalty = 0.0
    if workflow.average_duration > 0:
        cv = np.sqrt(workflow.duration_variance) / max(workflow.average_duration, 1.0)
        variance_penalty = min(cv * 0.1, 0.15)

    confidence = base + evidence_boost + determinism_boost + historical_boost - variance_penalty
    return float(np.clip(confidence, 0.05, 0.98))


def _classify_risk(risk_score: float) -> str:
    if risk_score < 0.25:
        return "Low"
    if risk_score < 0.55:
        return "Medium"
    return "High"


def _build_reasoning(workflow: WorkflowRecord, automation_score: float, confidence: float) -> str:
    evidence_count = len(workflow.get_session_ids())
    freq_per_week = round(workflow.frequency, 1)
    time_per_week = round(workflow.estimated_weekly_minutes, 1)
    apps = ", ".join(workflow.get_applications()[:3]) or "multiple applications"

    parts = [
        f"I observed this workflow {evidence_count} times over the observation period.",
        f"It occurs approximately {freq_per_week}x per week and consumes {time_per_week} minutes of developer time weekly.",
        f"The workflow involves {apps}.",
    ]

    if workflow.determinism_score > 0.7:
        parts.append(
            f"The sequence is highly deterministic (score: {workflow.determinism_score:.0%}), suggesting it follows a predictable pattern each time."
        )
    else:
        parts.append(
            f"The sequence shows some variation (determinism: {workflow.determinism_score:.0%}), but a core repeating pattern is clear."
        )

    if workflow.risk_score < 0.3:
        parts.append("The automation carries low risk — it primarily involves read operations and draft creation.")
    elif workflow.risk_score < 0.6:
        parts.append("The automation carries moderate risk — it involves some write operations that require careful validation.")
    else:
        parts.append("The automation carries higher risk and will require explicit permission grants before execution.")

    parts.append(
        f"Automation score: {automation_score:.0f}/100. Confidence: {confidence:.0%}. "
        f"I am {'highly' if confidence > 0.8 else 'moderately'} confident this can be reliably automated."
    )
    return " ".join(parts)


def _build_proposed_automation(workflow: WorkflowRecord) -> str:
    steps = workflow.get_steps()
    trigger = workflow.trigger or "detected event"
    goal = workflow.goal or "complete the workflow"

    lines = [f"When trigger '{trigger}' is detected:"]
    tool_map = {
        "ci_event": "classify_ci_failure",
        "browser_navigation": "get_github_ci",
        "terminal_command": "git_log",
        "git_command": "git_log",
        "github_event": "get_github_pull_request",
        "communication_event": "create_draft_message",
        "pr_event": "get_github_pull_request",
        "incident_event": "summarize_incident",
    }
    seen_tools = set()
    for i, step in enumerate(steps[:8], 1):
        event_type = step.get("event_type", "")
        tool = tool_map.get(event_type, "search_local_history")
        if tool not in seen_tools:
            lines.append(f"  {i}. Execute {tool}(context)")
            seen_tools.add(tool)
    lines.append(f"  Goal: {goal}")
    return "\n".join(lines)


def _infer_permissions(workflow: WorkflowRecord) -> List[str]:
    steps = workflow.get_steps()
    perms = {"github.read", "filesystem.read"}

    for step in steps:
        event_type = step.get("event_type", "")
        action = step.get("action", "")
        if event_type == "communication_event":
            perms.add("communication.draft")
        if "push" in action or "write" in action or "deploy" in action:
            perms.add("filesystem.write")
        if event_type == "github_event" and "write" in action:
            perms.add("github.write")
        if event_type == "terminal_command":
            perms.add("terminal.execute")

    return sorted(perms)


def create_opportunity(workflow: WorkflowRecord) -> OpportunityRecord:
    automation_score = compute_automation_score(workflow)
    confidence = compute_confidence(workflow)
    risk_level = _classify_risk(workflow.risk_score)
    reasoning = _build_reasoning(workflow, automation_score, confidence)
    proposed = _build_proposed_automation(workflow)
    permissions = _infer_permissions(workflow)

    with get_db() as db:
        db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow.id).update(
            {"automation_score": automation_score, "confidence": confidence}
        )

    return OpportunityRecord(
        id=str(uuid.uuid4()),
        workflow_id=workflow.id,
        name=workflow.name,
        automation_score=automation_score,
        confidence=confidence,
        risk_level=risk_level,
        risk_score=workflow.risk_score,
        estimated_weekly_minutes=workflow.estimated_weekly_minutes,
        estimated_annual_minutes=workflow.estimated_annual_minutes,
        frequency=workflow.frequency,
        reasoning=reasoning,
        proposed_automation=proposed,
        required_permissions_json=json.dumps(permissions),
        evidence_json=workflow.evidence_json,
        status="pending",
        created_at=datetime.utcnow(),
    )


def deduplicate_workflows(workflows: List[WorkflowRecord]) -> List[WorkflowRecord]:
    best: Dict[str, WorkflowRecord] = {}
    for wf in workflows:
        key = wf.name.strip().lower()
        if key not in best or wf.confidence > best[key].confidence:
            best[key] = wf
    return list(best.values())


def score_all_workflows(workflows: List[WorkflowRecord]) -> List[OpportunityRecord]:
    from momentum.config.settings import settings
    deduplicated = deduplicate_workflows(workflows)
    opportunities = []
    for workflow in deduplicated:
        score = compute_automation_score(workflow)
        conf = compute_confidence(workflow)
        if score >= settings.MOMENTUM_MIN_AUTOMATION_SCORE and conf >= settings.MOMENTUM_MIN_CONFIDENCE:
            opp = create_opportunity(workflow)
            opportunities.append(opp)

    opportunities.sort(key=lambda o: o.automation_score, reverse=True)
    return opportunities


def save_opportunities(opportunities: List[OpportunityRecord]) -> int:
    with get_db() as db:
        db.bulk_save_objects(opportunities)
        return len(opportunities)


def get_all_opportunities() -> List[OpportunityRecord]:
    with get_db() as db:
        return (
            db.query(OpportunityRecord)
            .filter(OpportunityRecord.status == "pending")
            .order_by(OpportunityRecord.automation_score.desc())
            .all()
        )


def get_opportunity_by_id(opp_id: str) -> Optional[OpportunityRecord]:
    with get_db() as db:
        return db.query(OpportunityRecord).filter(OpportunityRecord.id == opp_id).first()
