import random
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Tuple
from momentum.models.session import SessionRecord
from momentum.models.event import EventCreate

WORKFLOW_TYPES = [
    "ci_failure",
    "pr_review",
    "standup_prep",
    "dependency_update",
    "email_triage",
    "noise"
]

class BenchmarkGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.repos = ["frontend-web", "backend-api", "ml-pipeline", "infrastructure"]

    def generate_dataset(self, num_sessions: int = 100) -> Tuple[List[SessionRecord], List[str]]:
        sessions = []
        labels = []
        base_time = datetime(2026, 8, 1, 9, 0, 0)
        
        for i in range(num_sessions):
            workflow_type = self.rng.choice(WORKFLOW_TYPES)
            s_id = str(uuid.UUID(int=self.rng.getrandbits(128)))
            dev_id = f"dev_{self.rng.randint(1, 10):02d}"
            t = base_time + timedelta(hours=self.rng.uniform(0, 100))
            
            s = SessionRecord(session_id=s_id, start_time=t, developer_id=dev_id)
            repo = self.rng.choice(self.repos)
            
            events = getattr(self, f"_gen_{workflow_type}")(t, repo)
            
            if workflow_type != "noise" and len(events) > 3 and self.rng.random() < 0.2:
                idx = self.rng.randint(1, len(events) - 2)
                events.pop(idx)
                
            if workflow_type != "noise" and len(events) > 3 and self.rng.random() < 0.2:
                idx = self.rng.randint(1, len(events) - 2)
                events[idx], events[idx+1] = events[idx+1], events[idx]
                
            if self.rng.random() < 0.3:
                events.insert(self.rng.randint(0, len(events)), self._random_noise_event(t))
                
            event_dicts = [e.model_dump() for e in events]
            s.event_sequence_json = json.dumps(event_dicts, default=str)
            s.event_count = len(event_dicts)
            s.repository = repo
            s.end_time = events[-1].timestamp if events else t
            if events:
                s.duration = (s.end_time - t).total_seconds()
            
            sessions.append(s)
            labels.append(workflow_type)
            
        return sessions, labels

    def _random_noise_event(self, t: datetime) -> EventCreate:
        apps = ["Spotify", "Slack", "Chrome", "Terminal", "VSCode"]
        app = self.rng.choice(apps)
        return EventCreate(
            timestamp=t,
            event_type="app_focused",
            application=app,
            title="Random window",
            action="view",
            target="window"
        )
        
    def _gen_ci_failure(self, t: datetime, repo: str) -> List[EventCreate]:
        return [
            EventCreate(timestamp=t, event_type="notification_clicked", application="Slack", title="CI failed", action="click", target="slack_msg"),
            EventCreate(timestamp=t+timedelta(seconds=5), event_type="app_focused", application="Chrome", title="GitHub Actions", action="view", target="ci_log"),
            EventCreate(timestamp=t+timedelta(seconds=15), event_type="app_focused", application="Terminal", title="Terminal", action="run", target="git checkout"),
            EventCreate(timestamp=t+timedelta(seconds=20), event_type="app_focused", application="Terminal", title="Terminal", action="run", target="git pull"),
            EventCreate(timestamp=t+timedelta(seconds=30), event_type="app_focused", application="VSCode", title="Editor", action="view", target="code_file"),
        ]

    def _gen_pr_review(self, t: datetime, repo: str) -> List[EventCreate]:
        return [
            EventCreate(timestamp=t, event_type="notification_clicked", application="Email", title="PR review requested", action="click", target="email"),
            EventCreate(timestamp=t+timedelta(seconds=10), event_type="app_focused", application="Chrome", title="GitHub PR", action="view", target="pr_page"),
            EventCreate(timestamp=t+timedelta(seconds=45), event_type="app_focused", application="Chrome", title="GitHub PR", action="click", target="files_changed"),
            EventCreate(timestamp=t+timedelta(seconds=120), event_type="app_focused", application="Chrome", title="GitHub PR", action="submit", target="pr_comment"),
        ]

    def _gen_standup_prep(self, t: datetime, repo: str) -> List[EventCreate]:
        return [
            EventCreate(timestamp=t, event_type="app_focused", application="Terminal", title="Terminal", action="run", target="git log --author"),
            EventCreate(timestamp=t+timedelta(seconds=10), event_type="app_focused", application="Chrome", title="Jira", action="view", target="board"),
            EventCreate(timestamp=t+timedelta(seconds=30), event_type="app_focused", application="Notion", title="Standup Notes", action="edit", target="notes"),
        ]

    def _gen_dependency_update(self, t: datetime, repo: str) -> List[EventCreate]:
        return [
            EventCreate(timestamp=t, event_type="app_focused", application="Terminal", title="Terminal", action="run", target="npm outdated"),
            EventCreate(timestamp=t+timedelta(seconds=15), event_type="app_focused", application="Terminal", title="Terminal", action="run", target="npm update"),
            EventCreate(timestamp=t+timedelta(seconds=30), event_type="app_focused", application="Terminal", title="Terminal", action="run", target="npm test"),
            EventCreate(timestamp=t+timedelta(seconds=45), event_type="app_focused", application="Terminal", title="Terminal", action="run", target="git commit -m 'chore: update deps'"),
        ]

    def _gen_email_triage(self, t: datetime, repo: str) -> List[EventCreate]:
        return [
            EventCreate(timestamp=t, event_type="app_focused", application="Chrome", title="Gmail", action="view", target="inbox"),
            EventCreate(timestamp=t+timedelta(seconds=10), event_type="app_focused", application="Chrome", title="Gmail", action="click", target="archive"),
            EventCreate(timestamp=t+timedelta(seconds=15), event_type="app_focused", application="Chrome", title="Gmail", action="click", target="archive"),
            EventCreate(timestamp=t+timedelta(seconds=25), event_type="app_focused", application="Chrome", title="Gmail", action="click", target="reply"),
        ]

    def _gen_noise(self, t: datetime, repo: str) -> List[EventCreate]:
        events = []
        for _ in range(self.rng.randint(2, 6)):
            events.append(self._random_noise_event(t))
            t += timedelta(seconds=self.rng.randint(5, 60))
        return events
