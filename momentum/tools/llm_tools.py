import logging
from typing import Dict, List, Optional
from momentum.tools.git_tools import BaseTool

logger = logging.getLogger(__name__)

def _get_llm(api_key: str, model: str = "gpt-4o-mini"):
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=api_key, temperature=0.3, max_tokens=800)
    except Exception:
        return None

class LLMFillTextTool(BaseTool):
    name = "llm_fill_text"
    description = "Use an LLM to generate text — cover letters, standup messages, ticket descriptions, emails"
    risk_level = "low"
    timeout_seconds = 30
    required_permissions = ["llm.generate"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        from momentum.config.settings import settings
        import os

        prompt = context.get("prompt", "")
        text_type = context.get("text_type", "message")
        additional_context = context.get("user_context", "")
        api_key = settings.MOMENTUM_LLM_API_KEY or os.environ.get("OPENAI_API_KEY", "")

        if not prompt:
            return {"success": False, "error": "No prompt provided", "output": None}

        if dry_run:
            return {"success": True, "output": {"generated_text": f"[dry-run] Generated {text_type}", "dry_run": True}}

        if not api_key:
            return {"success": False, "error": "API key required for llm_fill_text tool", "output": None}

        try:
            llm = _get_llm(api_key, settings.MOMENTUM_LLM_MODEL)
            if not llm:
                return {"success": False, "error": "LLM client could not be initialized", "output": None}

            from langchain.schema import HumanMessage, SystemMessage
            full_prompt = prompt
            if additional_context:
                full_prompt += f"\n\nAdditional context: {additional_context}"

            response = llm.invoke([
                SystemMessage(content=f"You are a helpful assistant generating a professional {text_type}. Be concise and direct."),
                HumanMessage(content=full_prompt),
            ])
            return {"success": True, "output": {"generated_text": response.content.strip(), "text_type": text_type}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

class LLMClassifyTool(BaseTool):
    name = "llm_classify"
    description = "Use an LLM to classify or score text — job listing relevance, email priority, etc."
    risk_level = "low"
    timeout_seconds = 20
    required_permissions = ["llm.generate"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        from momentum.config.settings import settings
        import os

        text = context.get("text", "")
        options = context.get("options", [])
        classification_task = context.get("task", "classify")
        criteria = context.get("criteria", "")
        api_key = settings.MOMENTUM_LLM_API_KEY or os.environ.get("OPENAI_API_KEY", "")

        if not text:
            return {"success": False, "error": "No text to classify", "output": None}

        if dry_run:
            return {"success": True, "output": {"label": options[0] if options else "relevant", "score": 0.8, "dry_run": True}}

        if not api_key:
            return {"success": False, "error": "API key required for llm_classify tool", "output": None}

        try:
            llm = _get_llm(api_key, settings.MOMENTUM_LLM_MODEL)
            if not llm:
                return {"success": False, "error": "LLM client could not be initialized", "output": None}

            from langchain.schema import HumanMessage, SystemMessage
            import json

            options_str = f"Choose from: {options}" if options else "Return a relevance score 0-1"
            criteria_str = f"Criteria: {criteria}" if criteria else ""

            prompt = f"""Task: {classification_task}
{criteria_str}
{options_str}

Text to classify:
{text[:2000]}

Respond in JSON: { "label": "...", "score": 0.0-1.0, "reasoning": "..."} """

            response = llm.invoke([
                SystemMessage(content="You are a classification assistant. Respond with JSON only."),
                HumanMessage(content=prompt),
            ])

            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            return {"success": True, "output": result}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}

LLM_TOOLS = [
    LLMFillTextTool(),
    LLMClassifyTool(),
]
