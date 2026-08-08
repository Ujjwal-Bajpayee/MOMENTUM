import os
import json
import logging
from typing import Optional, Dict, List
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord
from momentum.config.settings import settings

logger = logging.getLogger(__name__)

_API_KEY_CACHE: Optional[str] = None


def _persist_api_key(key: str):
    from pathlib import Path
    config_path = Path.home() / ".momentum" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass
    config["api_key"] = key
    config_path.write_text(json.dumps(config, indent=2))


def _load_persisted_key() -> Optional[str]:
    from pathlib import Path
    config_path = Path.home() / ".momentum" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get("api_key", "")
        except Exception:
            pass
    return None


def _get_api_key() -> Optional[str]:
    global _API_KEY_CACHE
    if _API_KEY_CACHE:
        return _API_KEY_CACHE

    key = settings.MOMENTUM_LLM_API_KEY
    if key:
        _API_KEY_CACHE = key
        return key

    env_key = os.environ.get("OPENAI_API_KEY", "")
    if env_key:
        _API_KEY_CACHE = env_key
        return env_key

    persisted = _load_persisted_key()
    if persisted:
        _API_KEY_CACHE = persisted
        os.environ["OPENAI_API_KEY"] = persisted
        settings.MOMENTUM_LLM_API_KEY = persisted
        return persisted

    try:
        print("\n[MOMENTUM] No LLM API key found.")
        print("An API key enables custom automation plan generation for any discovered workflow.")
        print("Without it, generic workflows (LinkedIn, email, etc.) cannot be automated.")
        entered = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
        if entered:
            os.environ["OPENAI_API_KEY"] = entered
            settings.MOMENTUM_LLM_API_KEY = entered
            _API_KEY_CACHE = entered
            _persist_api_key(entered)
            return entered
    except (EOFError, KeyboardInterrupt):
        pass

    return None


def _deterministic_interpret(workflow: WorkflowRecord) -> Dict:
    steps = workflow.get_steps()
    apps = workflow.get_applications()
    decision_points = workflow.get_decision_points()

    step_descriptions = []
    for i, step in enumerate(steps[:10], 1):
        event_type = step.get("event_type", "").replace("_", " ")
        app = step.get("application", "unknown")
        action = step.get("action", "")
        desc = f"Step {i}: {event_type} on {app}"
        if action:
            desc += f" ({action[:40]})"
        step_descriptions.append(desc)

    return {
        "name": workflow.name,
        "goal": workflow.goal or f"Complete the {workflow.name.lower()}",
        "trigger": workflow.trigger or "periodic",
        "step_interpretations": step_descriptions,
        "decision_summary": f"This workflow involves {len(decision_points)} decision point(s): {', '.join(decision_points[:3])}",
        "automation_explanation": (
            f"This workflow repeats {workflow.frequency:.1f}x/week with "
            f"{workflow.determinism_score:.0%} determinism. "
            f"Observed {len(workflow.get_session_ids())} times."
        ),
        "risk_explanation": (
            "Low risk — read operations only." if workflow.risk_score < 0.3 else
            "Moderate risk — involves some write operations." if workflow.risk_score < 0.6 else
            "Higher risk — requires careful permission management."
        ),
        "confidence_explanation": (
            f"Confidence of {workflow.confidence:.0%} based on {len(workflow.get_session_ids())} "
            f"observations and {workflow.determinism_score:.0%} sequence consistency."
        ),
        "model": "offline",
    }


def _llm_interpret(workflow: WorkflowRecord, api_key: str) -> Optional[Dict]:
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage

        llm = ChatOpenAI(model=settings.MOMENTUM_LLM_MODEL, api_key=api_key, temperature=0.3, max_tokens=600)

        steps_text = "\n".join(
            f"- {s.get('event_type','')}: {s.get('application','')} {s.get('action','')[:50]}"
            for s in workflow.get_steps()[:10]
        )

        prompt = f"""You are analyzing a recurring workflow discovered by observing raw developer activity.

Workflow: {workflow.name}
Frequency: {workflow.frequency:.1f}x per week
Duration: {workflow.average_duration:.0f} seconds average
Applications: {', '.join(workflow.get_applications()[:5])}
Determinism: {workflow.determinism_score:.0%}
Risk: {workflow.risk_score:.0%}

Observed steps:
{steps_text}

Provide JSON with:
- goal: one sentence describing what this workflow accomplishes
- automation_explanation: why this is worth automating
- risk_explanation: what risks exist
- confidence_explanation: why the confidence score makes sense

Keep each field under 100 words."""

        response = llm.invoke([
            SystemMessage(content="You are a workflow analysis expert. Respond in JSON only."),
            HumanMessage(content=prompt),
        ])

        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        data["model"] = settings.MOMENTUM_LLM_MODEL
        return data

    except Exception as e:
        logger.warning(f"LLM interpret failed: {e}")
        return None


def requires_api_key_for_plan(workflow: WorkflowRecord) -> bool:
    from momentum.automation.plan_builder import TRIGGER_TO_TOOLS
    trigger = workflow.trigger or ""
    for known_trigger in TRIGGER_TO_TOOLS:
        if known_trigger in trigger.lower():
            return False
    return True


def generate_automation_plan(
    workflow: WorkflowRecord,
    user_context: Dict,
    api_key: str,
) -> Optional[Dict]:
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage, SystemMessage
        from momentum.tools.registry import get_registry

        registry = get_registry()
        tool_schema = registry.get_schema_for_llm()

        steps_text = "\n".join(
            f"  {i+1}. {s.get('event_type','unknown')}: {s.get('application','?')} -> {s.get('action','')[:60]}"
            for i, s in enumerate(workflow.get_steps()[:15])
        )

        context_text = "\n".join(
            f"  - {k}: {v}" for k, v in user_context.items() if k != "workflow_type"
        )

        prompt = f"""You observed a developer doing the following sequence {len(workflow.get_session_ids())} times over the observation period:

{steps_text}

Workflow stats:
  - Frequency: {workflow.frequency:.1f}x per week
  - Avg duration: {workflow.average_duration/60:.1f} minutes
  - Applications: {', '.join(workflow.get_applications()[:6])}
  - Goal: {workflow.goal or 'unknown'}

User provided context:
{context_text}

{tool_schema}

Generate a JSON automation plan using ONLY tools from the list above:
{{
  "name": "short descriptive name",
  "description": "one sentence description",
  "trigger": {{"type": "scheduled|event|manual", "cron": "0 9 * * 1-5"}},
  "steps": [
    {{
      "tool": "tool_name",
      "params": {{"key": "value"}},
      "description": "what this step does",
      "requires_confirmation": false,
      "critical": false
    }}
  ],
  "estimated_time_saved_minutes": 0,
  "risks": ["risk1"],
  "permissions_needed": ["browser.read"]
}}

Rules: only use tools from the list, mark requires_confirmation=true for write/submit steps, keep to 4-8 steps."""

        llm = ChatOpenAI(model=settings.MOMENTUM_LLM_MODEL, api_key=api_key, temperature=0.2, max_tokens=1000)

        response = llm.invoke([
            SystemMessage(content="You are an automation engineer. Generate practical plans using only the provided tools. Respond in JSON only."),
            HumanMessage(content=prompt),
        ])

        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rstrip("`").strip()

        plan = json.loads(text)

        valid_tool_names = registry.list_tool_names()
        plan["steps"] = [s for s in plan.get("steps", []) if s.get("tool") in valid_tool_names]
        plan["generated_by"] = "llm"
        plan["model"] = settings.MOMENTUM_LLM_MODEL
        return plan

    except Exception as e:
        logger.error(f"LLM plan generation failed: {e}")
        return None


def generate_automation_plan_offline(workflow: WorkflowRecord, user_context: Dict) -> Dict:
    from momentum.automation.plan_builder import select_tools_for_workflow
    steps = workflow.get_steps()
    tools = select_tools_for_workflow(workflow.trigger or "", steps)
    return {
        "name": f"Automation: {workflow.name}",
        "description": workflow.goal or workflow.name,
        "trigger": {"type": "manual", "event": workflow.trigger or "manual"},
        "steps": [{"tool": t, "params": {}, "description": f"Execute {t}", "requires_confirmation": False, "critical": False} for t in tools],
        "estimated_time_saved_minutes": int(workflow.average_duration / 60),
        "risks": ["Offline mode — heuristic tool selection. Provide an API key for a custom plan."],
        "permissions_needed": [],
        "generated_by": "offline",
    }


def interpret_workflow(workflow: WorkflowRecord) -> Dict:
    api_key = _get_api_key()
    if api_key:
        result = _llm_interpret(workflow, api_key)
        if result:
            return result
    return _deterministic_interpret(workflow)


def interpret_opportunity(opportunity: OpportunityRecord, workflow: WorkflowRecord) -> str:
    api_key = settings.MOMENTUM_LLM_API_KEY or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return opportunity.reasoning or _deterministic_interpret(workflow).get("automation_explanation", "")
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage
        llm = ChatOpenAI(model=settings.MOMENTUM_LLM_MODEL, api_key=api_key, temperature=0.2, max_tokens=300)
        prompt = (
            f"Explain in 2-3 sentences why '{workflow.name}' (score: {opportunity.automation_score:.0f}/100, "
            f"confidence: {opportunity.confidence:.0%}) is a good automation candidate."
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception:
        return opportunity.reasoning or ""
