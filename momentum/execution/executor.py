import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
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
    stdout_captured = ""
    stderr_captured = ""

    is_python_code = plan.get("type") == "python" and "code" in plan

    if is_python_code:
        code_str = plan["code"]
        if not dry_run:
            try:
                answer = input(f"\n  [MOMENTUM] This automation executes raw Python code. Run it? (y/N): ").strip().lower()
                if answer not in ("y", "yes"):
                    execution_success = False
                    failure_reason = "User declined raw code execution"
                else:
                    import subprocess
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
                        tf.write(code_str)
                        tmp_path = tf.name
                    
                    try:
                        result = subprocess.run(
                            ["python", tmp_path],
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        stdout_captured = result.stdout
                        stderr_captured = result.stderr
                        if result.returncode != 0:
                            execution_success = False
                            failure_reason = f"Script exited with {result.returncode}"
                    except Exception as e:
                        execution_success = False
                        failure_reason = str(e)
                    finally:
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
            except (EOFError, KeyboardInterrupt):
                execution_success = False
                failure_reason = "User aborted"
        else:
            stdout_captured = "(Dry run - code not executed)"
        
        actions_executed.append({
            "tool": "python_script",
            "success": execution_success,
            "stdout": stdout_captured,
            "stderr": stderr_captured,
            "dry_run": dry_run
        })
    else:
        execution_success = False
        failure_reason = "Legacy tool-based automations are no longer supported. Please regenerate this automation."
        logger.warning(failure_reason)

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
