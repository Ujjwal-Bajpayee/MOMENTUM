from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


TOOL_TO_PERMISSION = {
    "git_status": ["filesystem.read"],
    "git_log": ["filesystem.read"],
    "git_diff": ["filesystem.read"],
    "search_repository": ["filesystem.read"],
    "run_tests": ["terminal.execute", "filesystem.read"],
    "get_github_pull_request": ["github.read"],
    "get_github_commit": ["github.read"],
    "get_github_ci": ["github.read"],
    "search_documentation": ["browser.read"],
    "search_local_history": ["filesystem.read"],
    "find_code_owner": ["github.read", "filesystem.read"],
    "classify_ci_failure": ["github.read"],
    "create_draft_issue": ["github.read"],
    "create_draft_message": ["communication.draft"],
    "generate_release_notes": ["github.read"],
    "summarize_incident": ["github.read", "browser.read"],
}

CI_INVESTIGATION_TOOLS = [
    "classify_ci_failure",
    "get_github_ci",
    "git_log",
    "get_github_commit",
    "find_code_owner",
    "create_draft_message",
]

PR_REVIEW_TOOLS = [
    "get_github_pull_request",
    "git_diff",
    "search_repository",
    "find_code_owner",
    "create_draft_message",
]

RELEASE_NOTES_TOOLS = [
    "git_log",
    "get_github_pull_request",
    "get_github_ci",
    "generate_release_notes",
]

INCIDENT_TOOLS = [
    "get_github_ci",
    "classify_ci_failure",
    "search_local_history",
    "summarize_incident",
    "create_draft_message",
]

TRIGGER_TO_TOOLS = {
    "ci_build_failed": CI_INVESTIGATION_TOOLS,
    "ci_event:build_failed": CI_INVESTIGATION_TOOLS,
    "pull_request_created": PR_REVIEW_TOOLS,
    "github_event:pr": PR_REVIEW_TOOLS,
    "git_push": RELEASE_NOTES_TOOLS,
    "incident_detected": INCIDENT_TOOLS,
    "incident_event:": INCIDENT_TOOLS,
}


def select_tools_for_workflow(trigger: str, steps: List[Dict]) -> List[str]:
    for key, tools in TRIGGER_TO_TOOLS.items():
        if key in trigger.lower():
            return tools

    event_types = [s.get("event_type", "") for s in steps]
    if "ci_event" in event_types or "browser_navigation" in event_types:
        if "communication_event" in event_types:
            return CI_INVESTIGATION_TOOLS
    if "github_event" in event_types or "pr_event" in event_types:
        return PR_REVIEW_TOOLS

    return CI_INVESTIGATION_TOOLS


@dataclass
class AutomationPlan:
    automation_id: str
    workflow_id: str
    opportunity_id: str
    name: str
    trigger: Dict
    conditions: List[str]
    tools: List[str]
    steps: List[Dict]
    permissions: List[str]
    timeout_seconds: int = 300
    failure_conditions: List[str] = field(default_factory=list)
    rollback_steps: List[Dict] = field(default_factory=list)
    dry_run_capable: bool = True

    def to_dict(self) -> Dict:
        return {
            "automation_id": self.automation_id,
            "workflow_id": self.workflow_id,
            "opportunity_id": self.opportunity_id,
            "name": self.name,
            "trigger": self.trigger,
            "conditions": self.conditions,
            "tools": self.tools,
            "steps": self.steps,
            "permissions": self.permissions,
            "timeout_seconds": self.timeout_seconds,
            "failure_conditions": self.failure_conditions,
            "rollback_steps": self.rollback_steps,
            "dry_run_capable": self.dry_run_capable,
        }
