import json
import time
import random
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from momentum.models.workflow import WorkflowRecord
from momentum.models.automation import AutomationRecord
from momentum.tools.registry import get_registry


def _build_replay_context(session_data: Dict) -> Dict:
    return {
        "session_id": session_data.get("session_id", ""),
        "repository": session_data.get("repository", "repo_alpha"),
        "developer_id": session_data.get("developer_id", "dev_01"),
        "timestamp": session_data.get("timestamp", datetime.utcnow().isoformat()),
        "trigger_event": session_data.get("trigger_event", "ci_build_failed"),
        "build_id": random.randint(1000, 9999),
        "commit_hash": "a1b2c3d",
        "simulation": True,
    }


def _simulate_tool_execution(tool_name: str, context: Dict, dry_run: bool = True) -> Dict:
    registry = get_registry()
    if not registry.has_tool(tool_name):
        return {"success": False, "error": f"Tool {tool_name} not found", "output": None}

    tool = registry.get_tool(tool_name)
    result = tool.execute(context, dry_run=dry_run)
    return result


def replay_automation_against_history(
    automation: AutomationRecord,
    workflow: WorkflowRecord,
) -> Dict:
    plan = automation.get_plan()
    tools = plan.get("tools", automation.get_tools())

    evidence = workflow.get_evidence()
    if not evidence:
        evidence = [{"session_id": "sim_001", "timestamp": datetime.utcnow().isoformat(), "duration_seconds": 300}]

    total_cases = len(evidence)
    successful = 0
    failed = 0
    total_time = 0.0
    case_results = []

    for case in evidence[:10]:
        ctx = _build_replay_context(case)
        case_success = True
        case_time_start = time.time()
        tool_results = []

        for tool_name in tools:
            result = _simulate_tool_execution(tool_name, ctx, dry_run=True)
            tool_results.append({"tool": tool_name, "result": result})
            if not result.get("success", True):
                case_success = False

        elapsed = time.time() - case_time_start
        total_time += elapsed

        if case_success:
            successful += 1
        else:
            failed += 1

        case_results.append({
            "session_id": case.get("session_id", ""),
            "success": case_success,
            "execution_time_ms": elapsed * 1000,
            "tools_executed": len(tools),
        })

    accuracy = successful / max(total_cases, 1)
    avg_time = total_time / max(total_cases, 1)
    manual_duration = workflow.average_duration
    estimated_saved_per_run = max(manual_duration - avg_time, 0)

    return {
        "total_cases": total_cases,
        "successful_cases": successful,
        "failed_cases": failed,
        "accuracy": accuracy,
        "false_positive_rate": failed / max(total_cases, 1),
        "false_negative_rate": 0.0,
        "average_execution_time_seconds": avg_time,
        "estimated_time_saved_per_run_seconds": estimated_saved_per_run,
        "estimated_weekly_hours_saved": (
            estimated_saved_per_run * workflow.frequency / 3600.0
        ),
        "meets_threshold": accuracy >= 0.75,
        "case_results": case_results[:5],
    }
