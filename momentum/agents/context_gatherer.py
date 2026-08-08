import json
import logging
from typing import Dict, List, Optional
from momentum.models.workflow import WorkflowRecord

logger = logging.getLogger(__name__)

WORKFLOW_QUESTIONS = {
    "browser_form": [
        ("site", "What website or app does this workflow happen on?", "e.g. linkedin.com"),
        ("goal", "What is the goal of this workflow?", "e.g. Apply for software engineering jobs"),
        ("filters", "Any filters, criteria, or preferences to apply?", "e.g. Remote only, salary >$100k, Python"),
        ("confirm_each", "Should I confirm with you before each submission?", "yes / no"),
    ],
    "communication": [
        ("platform", "Which communication platform is this on?", "e.g. Slack, Gmail, Outlook"),
        ("goal", "What is the goal of this workflow?", "e.g. Send daily standup updates"),
        ("recipients", "Who are the usual recipients or channels?", "e.g. #engineering channel"),
        ("tone", "What tone should generated messages use?", "e.g. professional, casual, brief"),
    ],
    "development": [
        ("repo", "Which repository or project is this for?", "e.g. ~/projects/myapp"),
        ("goal", "What does this workflow accomplish?", "e.g. Run tests and push to staging"),
        ("branch", "What branch or environment is typically involved?", "e.g. main, staging"),
        ("on_failure", "What should happen if a step fails?", "e.g. stop and notify me"),
    ],
    "job_search": [
        ("site", "Which job site does this happen on?", "e.g. linkedin.com, indeed.com"),
        ("role", "What role or title are you looking for?", "e.g. Senior Python Engineer"),
        ("filters", "What filters? (location, salary, type)", "e.g. Remote, >$120k, Full-time"),
        ("resume_path", "Where is your resume file?", "e.g. ~/Documents/resume.pdf"),
        ("confirm_each", "Confirm before applying to each job?", "yes / no"),
    ],
    "data_entry": [
        ("site", "What site or tool does this workflow use?", "e.g. Jira, Notion, Airtable"),
        ("goal", "What data is being entered or updated?", "e.g. Log daily metrics into Jira"),
        ("source", "Where does the data come from?", "e.g. my terminal output, a CSV file"),
        ("frequency", "How often should this run automatically?", "e.g. daily at 9am, after each git push"),
    ],
    "generic": [
        ("goal", "What is the goal of this workflow?", "Describe what it accomplishes"),
        ("trigger", "When should this automation run?", "e.g. daily at 9am, when I start my computer"),
        ("inputs", "What information or files does it need?", "e.g. my resume, login credentials"),
        ("confirm", "Should I ask for confirmation before taking actions?", "yes / no"),
    ],
}


def _classify_workflow_type(workflow: WorkflowRecord) -> str:
    steps = workflow.get_steps()
    apps = [s.get("application", "") for s in steps]
    event_types = [s.get("event_type", "") for s in steps]
    actions = [s.get("action", "") for s in steps]

    has_browser = "browser" in apps or "browser_navigation" in event_types
    has_form = "form_interaction" in event_types or any("fill" in a or "submit" in a for a in actions)
    has_linkedin = any("linkedin" in str(s) for s in steps)
    has_job = any("job" in str(s) or "apply" in str(s) for s in steps)
    has_communication = "communication_event" in event_types or any(a in apps for a in ["slack", "gmail", "outlook"])
    has_dev = any(a in apps for a in ["terminal", "vscode", "git"])
    has_data_entry = any("jira" in str(s) or "notion" in str(s) or "airtable" in str(s) for s in steps)

    if has_linkedin or has_job:
        return "job_search"
    if has_browser and has_form:
        return "browser_form"
    if has_communication:
        return "communication"
    if has_dev:
        return "development"
    if has_data_entry:
        return "data_entry"
    return "generic"


def gather_context(workflow: WorkflowRecord) -> Dict:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box

    console = Console()
    wf_type = _classify_workflow_type(workflow)
    questions = WORKFLOW_QUESTIONS.get(wf_type, WORKFLOW_QUESTIONS["generic"])

    console.print()
    console.print(Panel.fit(
        f"[bold cyan]MOMENTUM — Context Gathering[/bold cyan]\n"
        f"[dim]I detected a recurring [bold]{wf_type.replace('_', ' ')}[/bold] workflow "
        f"({workflow.frequency:.1f}x/week, ~{workflow.average_duration/60:.0f} min each).\n"
        f"To build a custom automation, I need a few details.[/dim]",
        border_style="cyan",
    ))
    console.print()

    user_context: Dict[str, str] = {"workflow_type": wf_type}

    for key, question, hint in questions:
        console.print(f"  [bold cyan]?[/bold cyan] [bold]{question}[/bold]")
        console.print(f"    [dim]{hint}[/dim]")
        try:
            answer = input("    > ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer:
            user_context[key] = answer
        console.print()

    return user_context


def format_context_for_llm(user_context: Dict) -> str:
    lines = ["User provided context:"]
    for key, value in user_context.items():
        if key != "workflow_type":
            lines.append(f"  - {key}: {value}")
    return "\n".join(lines)
