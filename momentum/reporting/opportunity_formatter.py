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

def format_opportunity_explanation(explain_dict: dict):
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Group

    table = Table(box=None, expand=False, show_header=True)
    table.add_column("Feature", style="dim")
    table.add_column("Raw Value", justify="right")
    table.add_column("Score (0-1)", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Contribution", style="cyan", justify="right")

    features = explain_dict.get("features", {})
    for feat_name, feat_data in features.items():
        raw = feat_data.get("raw", 0)
        score = feat_data.get("score", 0)
        weight = feat_data.get("weight", 0)
        contrib = score * weight * 100
        table.add_row(
            feat_name.replace("_", " ").title(),
            f"{raw:.2f}",
            f"{score:.2f}",
            f"{weight:.2f}",
            f"+{contrib:.1f}"
        )

    score_val = explain_dict.get("score", 0)
    recommended = explain_dict.get("recommended", False)
    reason = explain_dict.get("rejection_reason", "None")

    summary_color = "green" if recommended else "red"
    summary_text = f"[{summary_color}]Final Score: {score_val:.1f}/100"
    if not recommended:
        summary_text += f"\nRejected: {reason}"
    else:
        summary_text += "\nRecommended for Automation"

    group = Group(table, "\n", summary_text)
    return Panel(group, title="Recommendation Explanation", border_style=summary_color)
