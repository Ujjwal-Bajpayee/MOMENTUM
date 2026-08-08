from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from momentum.automation.plan_builder import AutomationPlan, TOOL_TO_PERMISSION, select_tools_for_workflow
from momentum.tools.registry import get_registry


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    missing_permissions: List[str]


def validate_plan(plan: AutomationPlan) -> ValidationResult:
    registry = get_registry()
    errors = []
    warnings = []
    missing_perms = []

    for tool_name in plan.tools:
        if not registry.has_tool(tool_name):
            errors.append(f"Tool '{tool_name}' not found in registry")

    granted_permissions = set(plan.permissions)
    for tool_name in plan.tools:
        required = TOOL_TO_PERMISSION.get(tool_name, [])
        for perm in required:
            if perm not in granted_permissions:
                missing_perms.append(f"{tool_name} requires {perm}")

    if plan.timeout_seconds <= 0:
        errors.append("Timeout must be positive")
    if plan.timeout_seconds > 3600:
        warnings.append("Timeout exceeds 1 hour — consider reducing it")

    if not plan.tools:
        errors.append("Automation plan has no tools")

    if not plan.trigger:
        warnings.append("No trigger defined — automation must be run manually")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        missing_permissions=missing_perms,
    )


def build_automation_plan(
    workflow,
    opportunity,
    automation_id: str,
) -> Tuple[AutomationPlan, ValidationResult]:
    from momentum.automation.plan_builder import select_tools_for_workflow, TOOL_TO_PERMISSION

    trigger_str = workflow.trigger or "manual"
    steps = workflow.get_steps()
    tools = select_tools_for_workflow(trigger_str, steps)

    all_permissions = set()
    for tool in tools:
        for perm in TOOL_TO_PERMISSION.get(tool, []):
            all_permissions.add(perm)

    plan_steps = []
    for i, tool in enumerate(tools, 1):
        plan_steps.append({
            "step": i,
            "tool": tool,
            "description": f"Execute {tool}",
            "inputs": {"context": "workflow_context"},
            "on_failure": "stop",
        })

    trigger_dict = {
        "type": trigger_str,
        "description": f"Triggered when {trigger_str.replace('_', ' ')} is detected",
    }

    conditions = [
        "Automation enabled",
        f"Permission granted: {', '.join(sorted(all_permissions))}",
        "No conflicting automation running",
    ]

    failure_conditions = [
        "Tool returns error",
        "Timeout exceeded",
        "Permission denied",
    ]

    plan = AutomationPlan(
        automation_id=automation_id,
        workflow_id=workflow.id,
        opportunity_id=opportunity.id,
        name=f"Automation: {workflow.name}",
        trigger=trigger_dict,
        conditions=conditions,
        tools=tools,
        steps=plan_steps,
        permissions=sorted(all_permissions),
        timeout_seconds=300,
        failure_conditions=failure_conditions,
        rollback_steps=[],
        dry_run_capable=True,
    )

    result = validate_plan(plan)
    return plan, result
