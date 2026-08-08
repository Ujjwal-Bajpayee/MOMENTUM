import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from momentum.tools.registry import get_registry
from momentum.permissions.registry import get_permission_registry
from momentum.models.automation import AutomationRecord
from momentum.models.outcome import OutcomeRecord
from momentum.database.base import get_db
from momentum.policy.policy import should_require_approval

logger = logging.getLogger(__name__)

def _validate_execution_preconditions(automation: AutomationRecord) -> Tuple[bool, str]:
    if automation.status == "paused":
        return False, "Automation is paused"
    if automation.status != "active":
        return False, f"Automation status is '{automation.status}'"

    perm_registry = get_permission_registry()
    missing = perm_registry.missing_permissions(automation.get_permissions())
    if missing:
        for perm in missing:
            if not perm_registry.is_dangerous(perm):
                perm_registry.grant(perm, automation.id)
            else:
                return False, f"Missing dangerous permission(s): {missing}"

    return True, "OK"

def execute_automation(
    automation: AutomationRecord,
    trigger_context: Optional[Dict] = None,
    dry_run: bool = False,
) -> OutcomeRecord:
    registry = get_registry()
    valid, reason = _validate_execution_preconditions(automation)
    if not valid:
        return _create_failed_outcome(automation, reason, trigger_context)

    plan = automation.get_plan()

    context = trigger_context or {
        "repository": "repo_alpha",
        "developer_id": "dev_01",
        "simulation": True,
        "trigger_event": plan.get("trigger", {}).get("type", "manual") if isinstance(plan.get("trigger"), dict) else "manual",
    }

    actions_executed = []
    start_time = time.time()
    execution_success = True
    failure_reason = None

    raw_steps = plan.get("steps", [])
    if raw_steps and isinstance(raw_steps[0], dict) and "tool" in raw_steps[0]:
        steps_to_run = raw_steps
    else:
        steps_to_run = [
            {"tool": t, "params": {}, "description": t, "requires_confirmation": False, "critical": False}
            for t in plan.get("tools", automation.get_tools())
        ]

    for step in steps_to_run:
        tool_name = step.get("tool", "")
        params = step.get("params", {})
        step_context = {**context, **params}

        if step.get("requires_confirmation") and not dry_run:
            try:
                answer = input(f"\n  [MOMENTUM] Confirm step: {step.get('description', tool_name)} (y/N): ").strip().lower()
                if answer not in ("y", "yes"):
                    execution_success = False
                    failure_reason = f"User declined step: {tool_name}"
                    actions_executed.append({
                        "tool": tool_name,
                        "success": False,
                        "execution_time_ms": 0,
                        "dry_run": dry_run,
                        "skipped": True,
                        "reason": "user_declined",
                    })
                    break
            except (EOFError, KeyboardInterrupt):
                pass

        tool_start = time.time()
        result = registry.execute_tool(tool_name, step_context, dry_run=dry_run)
        tool_elapsed = time.time() - tool_start

        actions_executed.append({
            "tool": tool_name,
            "success": result.get("success", False),
            "execution_time_ms": tool_elapsed * 1000,
            "dry_run": dry_run,
            "description": step.get("description", ""),
        })

        output = result.get("output", {})
        if isinstance(output, dict):
            context.update({k: v for k, v in output.items() if k not in ("dry_run",)})

        if not result.get("success", True):
            execution_success = False
            failure_reason = result.get("error", f"Tool {tool_name} failed")
            logger.warning(f"Tool {tool_name} failed: {failure_reason}")
            if step.get("critical", False):
                break

    elapsed = time.time() - start_time

    from momentum.learning.reward import calculate_time_saved
    time_saved = calculate_time_saved(elapsed, plan.get("estimated_manual_duration", plan.get("estimated_time_saved_minutes", 5) * 60))

    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation.id).first()
        confidence_before = auto.confidence if auto else automation.confidence
        autonomy_before = auto.autonomy_level if auto else automation.autonomy_level

    outcome = OutcomeRecord(
        automation_id=automation.id,
        timestamp=datetime.utcnow(),
        trigger=plan.get("trigger", {}).get("type", "manual") if isinstance(plan.get("trigger"), dict) else "manual",
        context_json=json.dumps({k: str(v) for k, v in context.items()}),
        actions_json=json.dumps(actions_executed),
        execution_time=elapsed,
        success=execution_success,
        failure_reason=failure_reason,
        human_intervention=False,
        time_saved=time_saved,
        confidence_before=confidence_before,
        autonomy_before=autonomy_before,
        confidence_after=confidence_before,
        autonomy_after=autonomy_before,
    )

    with get_db() as db:
        db.add(outcome)
        db.flush()

    logger.info(
        f"Automation {automation.id} executed: success={execution_success} "
        f"time={elapsed:.2f}s steps={len(actions_executed)} dry_run={dry_run}"
    )
    return outcome

def _create_failed_outcome(
    automation: AutomationRecord,
    reason: str,
    context: Optional[Dict],
) -> OutcomeRecord:
    outcome = OutcomeRecord(
        automation_id=automation.id,
        timestamp=datetime.utcnow(),
        trigger="manual",
        context_json=json.dumps(context or {}),
        actions_json=json.dumps([]),
        execution_time=0.0,
        success=False,
        failure_reason=reason,
        human_intervention=False,
        time_saved=0.0,
        confidence_before=automation.confidence,
        autonomy_before=automation.autonomy_level,
        confidence_after=automation.confidence,
        autonomy_after=automation.autonomy_level,
    )
    with get_db() as db:
        db.add(outcome)
    return outcome
