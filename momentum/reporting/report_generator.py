from datetime import datetime
from typing import List, Optional
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord
from momentum.database.base import get_db
from momentum.database.event_store import count_events
from momentum.sessions.sessionizer import count_sessions
from momentum.discovery.workflow_builder import get_all_workflows
from momentum.discovery.opportunity_engine import get_all_opportunities


def generate_report(
    observation_start: Optional[datetime] = None,
    observation_end: Optional[datetime] = None,
) -> str:
    now = datetime.utcnow()
    start = observation_start or now
    end = observation_end or now

    total_events = count_events()
    total_sessions = count_sessions()
    workflows = get_all_workflows()
    opportunities = get_all_opportunities()

    days_str = f"{(end - start).days} days" if start != end else "Active"

    lines = [
        "═" * 60,
        "  MOMENTUM — 7 DAY OBSERVATION REPORT",
        "═" * 60,
        "",
        f"  Observation period:",
        f"    Start  : {start.strftime('%Y-%m-%d %H:%M UTC')}",
        f"    End    : {end.strftime('%Y-%m-%d %H:%M UTC')}",
        f"    Duration: {days_str}",
        "",
        f"  Events observed    : {total_events:,}",
        f"  Sessions identified: {total_sessions:,}",
        f"  Recurring workflows: {len(workflows)}",
        f"  Automation candidates: {len(opportunities)}",
        "",
        "═" * 60,
        "  AUTOMATION OPPORTUNITIES",
        "═" * 60,
        "",
    ]

    if not opportunities:
        lines.append("  No automation opportunities found yet.")
        lines.append("  Run `python -m momentum simulate --days 7` to generate data.")
    else:
        for i, opp in enumerate(opportunities, 1):
            weekly_hours = opp.estimated_weekly_minutes / 60.0
            annual_hours = opp.estimated_annual_minutes / 60.0
            lines += [
                f"  {i}. {opp.name}",
                f"     Confidence  : {opp.confidence:.0%}",
                f"     Frequency   : {opp.frequency:.1f}x/week",
                f"     Time cost   : {weekly_hours:.1f} hours/week ({annual_hours:.0f} hours/year)",
                f"     Risk        : {opp.risk_level}",
                f"     Score       : {opp.automation_score:.0f}/100",
                f"     ID          : {opp.id}",
                "",
            ]

    lines += [
        "═" * 60,
        "  Use `python -m momentum inspect <id>` to see full details.",
        "  Use `python -m momentum approve <id>` to activate an automation.",
        "═" * 60,
    ]

    return "\n".join(lines)


def format_workflow_for_inspect(
    workflow: WorkflowRecord,
    opportunity: Optional[OpportunityRecord] = None,
) -> str:
    steps = workflow.get_steps()
    evidence = workflow.get_evidence()
    apps = ", ".join(workflow.get_applications()[:5]) or "various"
    decisions = workflow.get_decision_points()
    weekly_hours = workflow.estimated_weekly_minutes / 60.0
    annual_hours = workflow.estimated_annual_minutes / 60.0

    replay = opportunity.get_replay_results() if opportunity else {}

    lines = [
        "═" * 60,
        f"  WORKFLOW INSPECTION",
        "═" * 60,
        "",
        f"  Name        : {workflow.name}",
        f"  ID          : {workflow.id}",
        f"  Status      : {workflow.status}",
        f"  Trigger     : {workflow.trigger or 'unknown'}",
        f"  Goal        : {workflow.goal or 'Not yet inferred'}",
        "",
        "  ── OBSERVATIONS ──────────────────────────────────",
        f"  First seen  : {workflow.first_seen.strftime('%Y-%m-%d') if workflow.first_seen else 'unknown'}",
        f"  Last seen   : {workflow.last_seen.strftime('%Y-%m-%d') if workflow.last_seen else 'unknown'}",
        f"  Frequency   : {workflow.frequency:.1f}x per week",
        f"  Avg duration: {workflow.average_duration:.0f}s ({workflow.average_duration/60:.1f} min)",
        f"  Variance    : ±{(workflow.duration_variance**0.5):.0f}s",
        f"  Evidence    : {len(evidence)} observed sessions",
        f"  Applications: {apps}",
        "",
        "  ── TIME COST ─────────────────────────────────────",
        f"  Weekly cost : {weekly_hours:.1f} hours/week",
        f"  Annual cost : {annual_hours:.0f} hours/year",
        "",
        "  ── SCORES ────────────────────────────────────────",
        f"  Automation  : {workflow.automation_score:.0f}/100",
        f"  Confidence  : {workflow.confidence:.0%}",
        f"  Determinism : {workflow.determinism_score:.0%}",
        f"  Repetition  : {workflow.repetition_score:.0%}",
        f"  Risk score  : {workflow.risk_score:.0%}",
        "",
        "  ── OBSERVED STEPS ────────────────────────────────",
    ]

    for i, step in enumerate(steps[:10], 1):
        evt = step.get("event_type", "").replace("_", " ")
        app = step.get("application", "")
        action = step.get("action", "")
        desc = f"  {i:2}. [{evt}] on {app}"
        if action:
            desc += f" — {action[:50]}"
        lines.append(desc)

    if decisions:
        lines += [
            "",
            "  ── DECISION POINTS ───────────────────────────────",
        ]
        for d in decisions:
            lines.append(f"  • {d}")

    if opportunity:
        lines += [
            "",
            "  ── WHY I THINK THIS IS AUTOMATABLE ──────────────",
        ]
        reasoning = opportunity.reasoning or "Score and confidence support automation."
        for chunk in [reasoning[i:i+70] for i in range(0, len(reasoning), 70)]:
            lines.append(f"  {chunk}")

        lines += [
            "",
            "  ── PROPOSED AUTOMATION ───────────────────────────",
        ]
        proposed = opportunity.proposed_automation or ""
        for line in proposed.splitlines():
            lines.append(f"  {line}")

        perms = opportunity.get_required_permissions()
        if perms:
            lines += [
                "",
                "  ── REQUIRED PERMISSIONS ──────────────────────────",
            ]
            for perm in perms:
                lines.append(f"  • {perm}")

        if replay:
            lines += [
                "",
                "  ── HISTORICAL REPLAY RESULTS ─────────────────────",
                f"  Cases tested : {replay.get('total_cases', 0)}",
                f"  Successful   : {replay.get('successful_cases', 0)}",
                f"  Accuracy     : {replay.get('accuracy', 0):.0%}",
                f"  Avg exec time: {replay.get('average_execution_time_seconds', 0):.1f}s",
                f"  Meets threshold: {'✓ Yes' if replay.get('meets_threshold') else '✗ No'}",
            ]

    lines += [
        "",
        "═" * 60,
    ]
    return "\n".join(lines)
