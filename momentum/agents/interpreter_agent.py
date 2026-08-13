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

def _parse_json_response(text: str, default_fallback: Dict) -> Dict:
    import json
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.rstrip("`").strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    try:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            extracted = text[start_idx:end_idx+1]
            return json.loads(extracted)
    except json.JSONDecodeError:
        pass
        
    logger.warning("Failed to parse LLM JSON response. Using fallback.")
    return default_fallback

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
    
    fallback = {
        "goal": "Unknown goal",
        "automation_explanation": "Failed to generate explanation.",
        "risk_explanation": "Unknown risks.",
        "confidence_explanation": "Unknown confidence."
    }
    
    data = _parse_json_response(response.content, fallback)
    data["model"] = settings.MOMENTUM_LLM_MODEL
    return data

def generate_automation_plan(
    workflow: WorkflowRecord,
    user_context: Dict,
) -> Dict:
    from typing import TypedDict, List
    from langgraph.graph import StateGraph, END
    from langchain.schema import HumanMessage, SystemMessage
    from momentum.config.settings import settings
    import ast

    class AgentState(TypedDict):
        workflow_text: str
        errors: List[str]
        iterations: int
        generated_code: str
        final_plan: Dict

    llm = _get_llm()

    def generate_node(state: AgentState):
        prompt = state["workflow_text"]
        if state["errors"]:
            prompt += "\n\nThe previous code had the following syntax errors. Please fix them:\n"
            prompt += "\n".join(state["errors"])
            prompt += "\n\nRespond with the updated JSON plan containing the fixed Python script."
        
        response = llm.invoke([
            SystemMessage(content="You are an automation engineer. Generate a practical Python script. Respond in JSON only."),
            HumanMessage(content=prompt),
        ])

        fallback = {
            "name": "Fallback Plan",
            "description": "Failed to parse generated plan.",
            "trigger": {"type": "manual"},
            "type": "python",
            "code": "print('Fallback empty script executed.')\n",
            "estimated_time_saved_minutes": 0,
            "risks": ["parsing_failure"]
        }
        
        plan = _parse_json_response(response.content, fallback)
        return {
            "generated_code": plan.get("code", ""),
            "final_plan": plan,
            "iterations": state["iterations"] + 1,
            "errors": []
        }

    def validate_node(state: AgentState):
        code = state["generated_code"]
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"SyntaxError on line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(f"Error parsing code: {str(e)}")
        
        return {"errors": errors}

    def format_node(state: AgentState):
        plan = state["final_plan"]
        plan["generated_by"] = "langgraph"
        plan["model"] = settings.MOMENTUM_LLM_MODEL
        plan["iterations"] = state["iterations"]
        return {"final_plan": plan}

    def should_continue(state: AgentState):
        if len(state["errors"]) > 0 and state["iterations"] < 3:
            return "generate"
        return "format"

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("generate", generate_node)
    graph_builder.add_node("validate", validate_node)
    graph_builder.add_node("format", format_node)

    graph_builder.set_entry_point("generate")
    graph_builder.add_edge("generate", "validate")
    graph_builder.add_conditional_edges("validate", should_continue, {
        "generate": "generate",
        "format": "format"
    })
    graph_builder.add_edge("format", END)

    app = graph_builder.compile()

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

Write an executable, self-contained Python script that automates this workflow.
The script should be robust and handle potential errors.

Generate a JSON automation plan with the following schema:
{{
  "name": "short descriptive name",
  "description": "one sentence description",
  "trigger": {{ "type": "manual" }},
  "type": "python",
  "code": "import os\\n\\nprint('Hello world!')\\n",
  "estimated_time_saved_minutes": 5,
  "risks": ["list any risks of running this code"]
}}

Rules:
- The `code` field MUST contain a valid Python script as a string. Use \\n for newlines.
- Do not use markdown backticks inside the `code` string.
- Respond in JSON only."""

    initial_state = {
        "workflow_text": prompt,
        "errors": [],
        "iterations": 0,
        "generated_code": "",
        "final_plan": {}
    }

    result = app.invoke(initial_state)
    return result["final_plan"]

def interpret_opportunity(opportunity: OpportunityRecord, workflow: WorkflowRecord) -> str:
    from langchain.schema import HumanMessage
    llm = _get_llm()
    prompt = (
        f"Explain in 2-3 sentences why '{workflow.name}' (score: {opportunity.automation_score:.0f}/100, "
        f"confidence: {opportunity.confidence:.0%}) is a strong automation candidate."
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()
