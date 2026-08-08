import json
from datetime import datetime
from typing import Optional
from momentum.database.base import get_db
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord
from momentum.models.automation import AutomationRecord


def format_approve_prompt(
    workflow: WorkflowRecord,
    opportunity: OpportunityRecord,
) -> str:
    steps = workflow.get_steps()
    perms = opportunity.get_required_permissions()
    replay = opportunity.get_replay_results()
    proposed = opportunity.proposed_automation or "No automation plan generated yet"

    lines = [
        "═" * 60,
        "  AUTOMATION APPROVAL REQUEST",
        "═" * 60,
        "",
        f"  Workflow    : {workflow.name}",
        f"  Opportunity : {opportunity.id}",
        "",
        "  ── WHY IT WAS DISCOVERED ─────────────────────────",
        f"  {opportunity.reasoning or 'Pattern detected in observation data.'}",
        "",
        "  ── OBSERVED ──────────────────────────────────────",
        f"  {len(workflow.get_session_ids())} sessions  |  "
        f"First: {workflow.first_seen.strftime('%Y-%m-%d') if workflow.first_seen else 'n/a'}  |  "
        f"Last: {workflow.last_seen.strftime('%Y-%m-%d') if workflow.last_seen else 'n/a'}",
        "",
        "  ── ESTIMATED TIME SAVED ──────────────────────────",
        f"  {opportunity.estimated_weekly_minutes / 60:.1f} hours/week",
        f"  {opportunity.estimated_annual_minutes / 60:.0f} hours/year",
        "",
        "  ── CONFIDENCE & RISK ─────────────────────────────",
        f"  Confidence  : {opportunity.confidence:.0%}",
        f"  Risk level  : {opportunity.risk_level}",
        f"  Risk score  : {opportunity.risk_score:.0%}",
        f"  Score       : {opportunity.automation_score:.0f}/100",
        "",
        "  ── PROPOSED ACTIONS ──────────────────────────────",
    ]
    for line in proposed.splitlines():
        lines.append(f"  {line}")

    if perms:
        lines += [
            "",
            "  ── PERMISSIONS REQUIRED ──────────────────────────",
        ]
        for perm in perms:
            lines.append(f"  • {perm}")

    if replay:
        lines += [
            "",
            "  ── HISTORICAL REPLAY ─────────────────────────────",
            f"  Tested: {replay.get('total_cases', 0)} cases  |  "
            f"Accuracy: {replay.get('accuracy', 0):.0%}  |  "
            f"Avg exec: {replay.get('average_execution_time_seconds', 0):.1f}s",
        ]

    lines += [
        "",
        "═" * 60,
    ]
    return "\n".join(lines)
