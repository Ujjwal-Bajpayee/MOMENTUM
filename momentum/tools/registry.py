from typing import Dict, Optional, List
from momentum.tools.git_tools import BaseTool, ALL_TOOLS


def _load_all_tools() -> List[BaseTool]:
    tools = list(ALL_TOOLS)
    try:
        from momentum.tools.browser_tools import BROWSER_TOOLS
        tools.extend(BROWSER_TOOLS)
    except Exception:
        pass
    try:
        from momentum.tools.script_tools import SCRIPT_TOOLS
        tools.extend(SCRIPT_TOOLS)
    except Exception:
        pass
    try:
        from momentum.tools.llm_tools import LLM_TOOLS
        tools.extend(LLM_TOOLS)
    except Exception:
        pass
    return tools


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        for tool in _load_all_tools():
            self._tools[tool.name] = tool

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level,
                "required_permissions": t.required_permissions,
                "timeout_seconds": t.timeout_seconds,
            }
            for t in self._tools.values()
        ]

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_schema_for_llm(self) -> str:
        lines = ["Available tools (name | description | risk):"]
        for t in self._tools.values():
            lines.append(f"  - {t.name}: {t.description} [risk={t.risk_level}]")
        return "\n".join(lines)

    def execute_tool(self, name: str, context: Dict, dry_run: bool = False) -> Dict:
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found in registry", "output": None}
        try:
            return tool.execute(context, dry_run=dry_run)
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}


_registry_instance: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance

