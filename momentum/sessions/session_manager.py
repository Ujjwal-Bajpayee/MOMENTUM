from typing import List, Optional
from datetime import datetime
from momentum.sessions.sessionizer import Sessionizer, save_sessions, get_sessions, count_sessions
from momentum.database.event_store import get_events
from momentum.models.session import SessionRecord
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self._sessionizer = Sessionizer()

    def run_sessionization(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        events = get_events(start_time=start_time, end_time=end_time, limit=50000)
        if not events:
            return 0

        sessions = self._sessionizer.process_events(events)

        existing_ids = set()
        for s in get_sessions(start_time=start_time, end_time=end_time):
            existing_ids.add(s.session_id)

        new_sessions = [s for s in sessions if s.session_id not in existing_ids]
        if new_sessions:
            saved = save_sessions(new_sessions)
            logger.info(f"Sessionized {saved} new sessions from {len(events)} events")
            return saved

        return 0

    def get_all_sessions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[SessionRecord]:
        return get_sessions(start_time=start_time, end_time=end_time)

    def get_session_count(self) -> int:
        return count_sessions()

session_manager = SessionManager()
