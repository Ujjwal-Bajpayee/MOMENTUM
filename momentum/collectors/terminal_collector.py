import os
import platform
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from momentum.collectors.base import BaseCollector
from momentum.models.event import EventCreate


class TerminalCollector(BaseCollector):
    name = "terminal"
    interval_seconds = 5.0

    def __init__(self):
        super().__init__()
        self._last_history_size = 0
        self._history_file = self._find_history_file()

    def _find_history_file(self) -> Optional[Path]:
        home = Path.home()
        candidates = [
            home / ".zsh_history",
            home / ".bash_history",
            home / ".local" / "share" / "fish" / "fish_history",
            home / "AppData" / "Roaming" / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def _read_new_commands(self) -> List[str]:
        if not self._history_file or not self._history_file.exists():
            return []
        try:
            content = self._history_file.read_text(errors="ignore")
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            clean_lines = []
            for line in lines:
                if line.startswith(":") and ";" in line:
                    line = line.split(";", 1)[1]
                if line.startswith("#"):
                    continue
                clean_lines.append(line)

            current_size = len(clean_lines)
            if current_size > self._last_history_size:
                new_commands = clean_lines[self._last_history_size:]
                self._last_history_size = current_size
                return new_commands[-10:]
            self._last_history_size = current_size
            return []
        except Exception:
            return []

    def _classify_command(self, cmd: str) -> str:
        cmd_lower = cmd.lower()
        if cmd_lower.startswith("git "):
            return "git_command"
        if cmd_lower.startswith("docker "):
            return "docker_event"
        return "terminal_command"

    def collect(self) -> List[EventCreate]:
        events = []
        now = datetime.utcnow()
        new_commands = self._read_new_commands()

        for cmd in new_commands:
            safe_cmd = cmd[:256]
            event_type = self._classify_command(safe_cmd)
            events.append(EventCreate(
                timestamp=now,
                application="terminal",
                event_type=event_type,
                action=safe_cmd,
                source="terminal_collector",
                metadata={"shell": self._history_file.suffix if self._history_file else "unknown"},
            ))

        return events
