from fastapi import APIRouter
from datetime import datetime
from momentum.daemon.state import daemon_state
from momentum.database.event_store import count_events
from momentum.sessions.sessionizer import count_sessions
from momentum.learning.bandit import get_bandit

router = APIRouter()


@router.get("/health")
def health():
    bandit = get_bandit()
    state = daemon_state.get()
    day_num, day_total = daemon_state.get_day_progress()
    return {
        "status": state.get("status", "stopped"),
        "pid": state.get("pid"),
        "started_at": state.get("started_at"),
        "observation_day": day_num,
        "observation_total_days": day_total,
        "observation_complete": daemon_state.is_observation_complete(),
        "events_collected": count_events(),
        "sessions_identified": count_sessions(),
        "policy_version": bandit.version,
        "policy_epsilon": bandit.epsilon,
        "server_time": datetime.utcnow().isoformat(),
    }
