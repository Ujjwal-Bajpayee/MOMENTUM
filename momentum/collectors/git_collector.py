import subprocess
import os
import re
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from momentum.collectors.base import BaseCollector
from momentum.models.event import EventCreate

class GitCollector(BaseCollector):
    name = "git"
    interval_seconds = 10.0

    def __init__(self):
        super().__init__()
        self._last_git_log_hash: Optional[str] = None
        self._watch_dirs: List[Path] = []
        self._discover_git_repos()

    def _discover_git_repos(self):
        home = Path.home()
        candidates = [home / "Documents", home / "Projects", home / "code", home / "dev", home / "workspace"]
        for candidate in candidates:
            if candidate.exists():
                for p in candidate.iterdir():
                    if p.is_dir() and (p / ".git").exists():
                        self._watch_dirs.append(p)

    def _run_git(self, args: List[str], cwd: Path) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def collect(self) -> List[EventCreate]:
        events = []
        now = datetime.utcnow()

        for repo_dir in self._watch_dirs:
            log = self._run_git(["log", "--oneline", "-1", "--format=%H %s"], repo_dir)
            if log and log != self._last_git_log_hash:
                self._last_git_log_hash = log
                parts = log.split(" ", 1)
                commit_hash = parts[0] if parts else ""
                commit_msg = parts[1] if len(parts) > 1 else ""

                branch = self._run_git(["branch", "--show-current"], repo_dir)
                events.append(EventCreate(
                    timestamp=now,
                    application="git",
                    event_type="git_command",
                    action="commit",
                    target=repo_dir.name,
                    source="git_collector",
                    metadata={
                        "repo": repo_dir.name,
                        "branch": branch or "unknown",
                        "commit_hash": commit_hash[:8],
                        "message": commit_msg[:120],
                    },
                ))

        return events
