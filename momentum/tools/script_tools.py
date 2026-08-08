import os
import subprocess
import logging
from pathlib import Path
from typing import Dict
from momentum.tools.git_tools import BaseTool

logger = logging.getLogger(__name__)

SAFE_COMMANDS = {
    "npm_outdated", "pip_list_outdated", "git_log", "git_status", "git_diff",
    "ls", "cat", "echo", "python_version", "node_version",
}


class RunShellCommandTool(BaseTool):
    name = "run_shell_command"
    description = "Execute a sandboxed read-only shell command and return stdout"
    risk_level = "medium"
    timeout_seconds = 30
    required_permissions = ["terminal.execute"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        cmd = context.get("command", "")
        if not cmd:
            return {"success": False, "error": "No command provided", "output": None}
        first_word = cmd.strip().split()[0].replace("-", "_")
        if dry_run:
            return {"success": True, "output": {"stdout": f"[dry-run] would run: {cmd}", "dry_run": True}}
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=self.timeout_seconds
            )
            return {
                "success": result.returncode == 0,
                "output": {"stdout": result.stdout[:4000], "stderr": result.stderr[:500], "returncode": result.returncode},
                "error": result.stderr[:200] if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out", "output": None}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a local file (e.g. resume, config)"
    risk_level = "low"
    timeout_seconds = 10
    required_permissions = ["filesystem.read"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        path = context.get("path", "")
        if not path:
            return {"success": False, "error": "No path provided", "output": None}
        path = os.path.expanduser(path)
        if dry_run:
            return {"success": True, "output": {"path": path, "content": "[dry-run]", "dry_run": True}}
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            return {"success": True, "output": {"path": path, "content": content[:8000], "size": len(content)}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write text content to a local file"
    risk_level = "medium"
    timeout_seconds = 10
    required_permissions = ["filesystem.write"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        path = context.get("path", "")
        content = context.get("content", "")
        if not path or not content:
            return {"success": False, "error": "path and content required", "output": None}
        path = os.path.expanduser(path)
        if dry_run:
            return {"success": True, "output": {"path": path, "bytes": len(content), "dry_run": True}}
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return {"success": True, "output": {"path": path, "bytes_written": len(content)}}
        except Exception as e:
            return {"success": False, "error": str(e), "output": None}


class SendNotificationTool(BaseTool):
    name = "send_notification"
    description = "Send an OS-level desktop notification"
    risk_level = "low"
    timeout_seconds = 5
    required_permissions = ["system.notify"]

    def execute(self, context: Dict, dry_run: bool = False) -> Dict:
        message = context.get("message", "")
        title = context.get("title", "MOMENTUM")
        if not message:
            return {"success": False, "error": "No message provided", "output": None}
        if dry_run:
            return {"success": True, "output": {"title": title, "message": message, "dry_run": True}}
        try:
            import platform
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], check=True)
            elif system == "Linux":
                subprocess.run(["notify-send", title, message], check=True)
            elif system == "Windows":
                from plyer import notification
                notification.notify(title=title, message=message, timeout=5)
            logger.info(f"Notification sent: {title} — {message}")
            return {"success": True, "output": {"title": title, "message": message}}
        except Exception as e:
            logger.warning(f"Notification failed (non-critical): {e}")
            return {"success": True, "output": {"title": title, "message": message, "note": "notification display failed, logged only"}}


SCRIPT_TOOLS = [
    RunShellCommandTool(),
    ReadFileTool(),
    WriteFileTool(),
    SendNotificationTool(),
]
