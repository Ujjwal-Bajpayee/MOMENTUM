import os
import json
import logging
from typing import Optional, Dict, List
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)

def _get_llm():
    from momentum.config.settings import settings
    from langchain_community.chat_models import ChatOllama
    return ChatOllama(
        model=settings.MOMENTUM_LLM_MODEL,
        temperature=0.3,
    )

def interpret_workflow(workflow: WorkflowRecord) -> Dict:
    from langchain.schema import HumanMessage, SystemMessage
    from momentum.config.settings import settings

    llm = _get_llm()
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
- automation_explanation: why this is worth automating (2-3 sentences)
- risk_explanation: what risks exist
- confidence_explanation: why the confidence score makes sense

Keep each field under 100 words. Respond in JSON only."""

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

def generate_automation_plan(
    workflow: WorkflowRecord,
    user_context: Dict,
) -> Dict:
    from langchain.schema import HumanMessage, SystemMessage
    from momentum.tools.registry import get_registry
    from momentum.config.settings import settings

    registry = get_registry()
    tool_schema = registry.get_schema_for_llm()

    steps_text = "\n".join(
        f"  {i+1}. {s.get('event_type','unknown')}: {s.get('application','?')} -> {s.get('action','')[:60]}"
        for i, s in enumerate(workflow.get_steps()[:15])
    )

    context_text = "\n".join(
        f"  - {k}: {v}" for k, v in user_context.items() if k != "workflow_type"
    )

    prompt = f"""You observed a developer doing the following sequence {len(workflow.get_session_ids())} times:

{steps_text}

Workflow stats:
  - Frequency: {workflow.frequency:.1f}x per week (per developer)
  - Avg duration: {workflow.average_duration/60:.1f} minutes
  - Applications: {', '.join(workflow.get_applications()[:6])}
  - Goal: {workflow.goal or 'unknown'}

User provided context:
{context_text}

{tool_schema}

Generate a JSON automation plan using ONLY tools from the list above:
{ 
  "name": "short descriptive name",
  "description": "one sentence description",
  "trigger": { "type": "scheduled|event|manual", "cron": "0 9 * * 1-5"} ,
  "steps": [
    { 
      "tool": "tool_name",
      "params": { "key": "value"} ,
      "description": "what this step does",
      "requires_confirmation": false,
      "critical": false
    } 
  ],
  "estimated_time_saved_minutes": 0,
  "risks": ["risk1"],
  "permissions_needed": ["browser.read"]
} 

Rules:
- Only use tools from the Available tools list
- requires_confirmation=true for steps that write, submit, or send anything
- critical=true if failure should abort the automation
- 4-8 steps maximum
- Respond in JSON only"""

    llm = _get_llm()

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

def interpret_opportunity(opportunity: OpportunityRecord, workflow: WorkflowRecord) -> str:
    from langchain.schema import HumanMessage
    llm = _get_llm()
    prompt = (
        f"Explain in 2-3 sentences why '{workflow.name}' (score: {opportunity.automation_score:.0f}/100, "
        f"confidence: {opportunity.confidence:.0%}) is a strong automation candidate."
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()
