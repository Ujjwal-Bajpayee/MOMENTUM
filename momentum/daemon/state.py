import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from momentum.config.settings import settings


class DaemonState:
    def __init__(self):
        self._path = settings.get_state_file()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self, state: dict):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def set_running(self, pid: int):
        state = self._load()
        state["status"] = "running"
        state["pid"] = pid
        state["started_at"] = datetime.utcnow().isoformat()
        state["observation_start"] = state.get("observation_start") or datetime.utcnow().isoformat()
        self._save(state)

    def set_stopped(self):
        state = self._load()
        state["status"] = "stopped"
        state["stopped_at"] = datetime.utcnow().isoformat()
        state.pop("pid", None)
        self._save(state)

    def set_paused(self):
        state = self._load()
        state["status"] = "paused"
        self._save(state)

    def set_resumed(self):
        state = self._load()
        state["status"] = "running"
        self._save(state)

    def get(self) -> dict:
        return self._load()

    def get_status(self) -> str:
        return self._load().get("status", "stopped")

    def get_observation_start(self) -> Optional[datetime]:
        state = self._load()
        ts = state.get("observation_start")
        if ts:
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                pass
        return None

    def is_observation_complete(self) -> bool:
        obs_start = self.get_observation_start()
        if not obs_start:
            return False
        days = settings.MOMENTUM_OBSERVATION_DAYS
        return (datetime.utcnow() - obs_start).days >= days

    def get_day_progress(self) -> tuple:
        obs_start = self.get_observation_start()
        if not obs_start:
            return 0, settings.MOMENTUM_OBSERVATION_DAYS
        elapsed = (datetime.utcnow() - obs_start).days + 1
        total = settings.MOMENTUM_OBSERVATION_DAYS
        return min(elapsed, total), total


daemon_state = DaemonState()
