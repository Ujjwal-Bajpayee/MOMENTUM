import random
import math
from datetime import datetime, timedelta
from typing import List, Optional
from momentum.models.event import EventCreate


DEVELOPERS = [f"dev_{i:02d}" for i in range(1, 11)]
REPOSITORIES = ["repo_alpha", "repo_beta", "repo_gamma", "repo_delta", "repo_epsilon"]
TEAMS = {
    "frontend": ["dev_01", "dev_02", "dev_03"],
    "backend": ["dev_04", "dev_05", "dev_06", "dev_07"],
    "devops": ["dev_08", "dev_09", "dev_10"],
}

CI_TARGETS = [f"ci.company.com", f"ci.company.com/builds", f"ci.company.com/logs"]
GITHUB_TARGETS = ["github.com/org/repo/commit", "github.com/org/repo/blame", "github.com/org/repo/pulls"]
DOC_TARGETS = ["docs.company.com", "confluence.company.com", "stackoverflow.com"]
SLACK_TARGET = "slack.company.com"

TERMINAL_COMMANDS = [
    "git_log_--oneline_-10",
    "git_status",
    "git_diff_HEAD",
    "git_show",
    "pytest_tests/",
    "npm_test",
    "docker_ps",
    "kubectl_get_pods",
    "grep_-r_error",
    "tail_-f_logs/app.log",
    "git_pull_origin_main",
    "git_checkout_-b_fix/issue",
]

EDITOR_ACTIONS = ["open_file", "edit_file", "save_file", "close_file", "search_in_file"]
PR_TEMPLATES = [
    "fix: resolve race condition in worker queue",
    "feat: add pagination to API endpoints",
    "chore: update node dependencies",
    "fix: correct timeout handling in retries",
    "feat: implement webhook signature validation",
    "refactor: extract common DB utilities",
    "fix: resolve memory leak in connection pool",
    "docs: update API documentation",
]


def _ts(base: datetime, delta_seconds: float) -> datetime:
    return base + timedelta(seconds=delta_seconds)


def _work_hour_offset(day_base: datetime, rng: random.Random) -> float:
    hour = rng.uniform(8.5, 17.5)
    minute_jitter = rng.uniform(-30, 30)
    return hour * 3600 + minute_jitter * 60


class SyntheticEventGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.start_date: Optional[datetime] = None

    def generate_days(self, num_days: int, start_date: Optional[datetime] = None) -> List[EventCreate]:
        self.start_date = start_date or (datetime.utcnow() - timedelta(days=num_days))
        all_events = []
        for day_offset in range(num_days):
            day_base = self.start_date + timedelta(days=day_offset)
            day_base = day_base.replace(hour=0, minute=0, second=0, microsecond=0)
            all_events.extend(self._generate_day(day_base))
        all_events.sort(key=lambda e: e.timestamp)
        return all_events

    def _generate_day(self, day_base: datetime) -> List[EventCreate]:
        events = []
        events.extend(self._generate_normal_developer_activity(day_base))
        events.extend(self._generate_ci_events_and_chains(day_base))
        events.extend(self._generate_pr_activity(day_base))
        events.extend(self._generate_documentation_searches(day_base))
        events.extend(self._generate_docker_activity(day_base))
        events.extend(self._generate_git_commits(day_base))
        events.extend(self._generate_linkedin_job_search(day_base))
        events.extend(self._generate_email_triage(day_base))
        events.extend(self._generate_standup_prep(day_base))
        events.extend(self._generate_jira_ticket_creation(day_base))
        events.extend(self._generate_dependency_update_check(day_base))
        events.extend(self._generate_meeting_prep(day_base))
        if self.rng.random() < 0.4:
            events.extend(self._generate_incident(day_base))
        return events


    def _generate_normal_developer_activity(self, day_base: datetime) -> List[EventCreate]:
        events = []
        for dev in DEVELOPERS:
            work_start = _work_hour_offset(day_base, self.rng)
            n_sessions = self.rng.randint(3, 7)
            t = work_start
            for _ in range(n_sessions):
                repo = self.rng.choice(REPOSITORIES)
                session_duration = self.rng.uniform(600, 3600)
                n_events = int(session_duration / 120)
                for j in range(n_events):
                    t += self.rng.uniform(30, 240)
                    event_type = self.rng.choice(["terminal_command", "editor_event", "browser_navigation"])
                    if event_type == "terminal_command":
                        events.append(EventCreate(
                            timestamp=_ts(day_base, t),
                            application="terminal",
                            event_type="terminal_command",
                            action=self.rng.choice(TERMINAL_COMMANDS),
                            source="simulation",
                            metadata={"developer_id": dev, "repo": repo},
                        ))
                    elif event_type == "editor_event":
                        events.append(EventCreate(
                            timestamp=_ts(day_base, t),
                            application="vscode",
                            event_type="editor_event",
                            action=self.rng.choice(EDITOR_ACTIONS),
                            target=f"src/{repo}/module.py",
                            source="simulation",
                            metadata={"developer_id": dev, "repo": repo},
                        ))
                    else:
                        target = self.rng.choice(DOC_TARGETS + GITHUB_TARGETS)
                        events.append(EventCreate(
                            timestamp=_ts(day_base, t),
                            application="browser",
                            event_type="browser_navigation",
                            action="navigate",
                            target=target,
                            source="simulation",
                            metadata={"developer_id": dev},
                        ))
                t += self.rng.uniform(300, 1200)
        return events

    def _generate_ci_events_and_chains(self, day_base: datetime) -> List[EventCreate]:
        events = []
        n_ci = self.rng.randint(35, 50)
        for _ in range(n_ci):
            repo = self.rng.choice(REPOSITORIES)
            build_id = self.rng.randint(1000, 9999)
            is_failure = self.rng.random() < 0.38
            status = "build_failed" if is_failure else "build_passed"
            ci_ts = _ts(day_base, self.rng.uniform(9 * 3600, 17 * 3600))

            events.append(EventCreate(
                timestamp=ci_ts,
                application="ci-system",
                event_type="ci_event",
                action=status,
                target=f"build_{build_id}",
                source="simulation",
                metadata={"repo": repo, "build_id": build_id},
            ))

            if is_failure and self.rng.random() < 0.72:
                dev = self.rng.choice(DEVELOPERS)
                events.extend(self._generate_ci_investigation_chain(dev, repo, build_id, ci_ts))

        return events

    def _generate_ci_investigation_chain(
        self, dev: str, repo: str, build_id: int, failure_ts: datetime
    ) -> List[EventCreate]:
        events = []
        t = failure_ts + timedelta(seconds=self.rng.uniform(45, 150))

        events.append(EventCreate(
            timestamp=t,
            application="browser",
            event_type="browser_navigation",
            action="navigate",
            target="ci.company.com",
            source="simulation",
            metadata={"developer_id": dev, "repo": repo, "build_id": build_id},
        ))
        t += timedelta(seconds=self.rng.uniform(15, 45))

        events.append(EventCreate(
            timestamp=t,
            application="browser",
            event_type="browser_navigation",
            action="navigate",
            target="ci.company.com/builds",
            source="simulation",
            metadata={"developer_id": dev, "build_id": build_id},
        ))
        t += timedelta(seconds=self.rng.uniform(30, 90))

        events.append(EventCreate(
            timestamp=t,
            application="browser",
            event_type="browser_navigation",
            action="navigate",
            target="ci.company.com/logs",
            source="simulation",
            metadata={"developer_id": dev, "build_id": build_id},
        ))
        t += timedelta(seconds=self.rng.uniform(60, 180))

        events.append(EventCreate(
            timestamp=t,
            application="terminal",
            event_type="terminal_command",
            action="git_log_--oneline_-10",
            source="simulation",
            metadata={"developer_id": dev, "repo": repo},
        ))
        t += timedelta(seconds=self.rng.uniform(10, 30))

        commit_hash = "".join(self.rng.choices("abcdef0123456789", k=7))
        events.append(EventCreate(
            timestamp=t,
            application="browser",
            event_type="browser_navigation",
            action="navigate",
            target="github.com/org/repo/commit",
            source="simulation",
            metadata={"developer_id": dev, "commit_hash": commit_hash, "repo": repo},
        ))
        t += timedelta(seconds=self.rng.uniform(30, 90))

        events.append(EventCreate(
            timestamp=t,
            application="terminal",
            event_type="git_command",
            action="git_show",
            source="simulation",
            metadata={"developer_id": dev, "commit_hash": commit_hash},
        ))
        t += timedelta(seconds=self.rng.uniform(15, 40))

        events.append(EventCreate(
            timestamp=t,
            application="browser",
            event_type="browser_navigation",
            action="navigate",
            target="github.com/org/repo/blame",
            source="simulation",
            metadata={"developer_id": dev, "repo": repo},
        ))
        t += timedelta(seconds=self.rng.uniform(20, 60))

        events.append(EventCreate(
            timestamp=t,
            application="slack",
            event_type="communication_event",
            action="send_notification",
            target="engineering-alerts",
            source="simulation",
            metadata={"developer_id": dev, "repo": repo, "build_id": build_id},
        ))
        return events

    def _generate_pr_activity(self, day_base: datetime) -> List[EventCreate]:
        events = []
        n_prs = self.rng.randint(18, 25)
        for _ in range(n_prs):
            dev = self.rng.choice(DEVELOPERS)
            repo = self.rng.choice(REPOSITORIES)
            t = _ts(day_base, self.rng.uniform(9 * 3600, 17 * 3600))
            msg = self.rng.choice(PR_TEMPLATES)
            events.append(EventCreate(
                timestamp=t,
                application="github",
                event_type="pr_event",
                action="pr_created",
                target=f"github.com/{repo}/pulls",
                source="simulation",
                metadata={"developer_id": dev, "repo": repo, "title": msg},
            ))
            review_delay = self.rng.uniform(1800, 7200)
            reviewer = self.rng.choice([d for d in DEVELOPERS if d != dev])
            events.append(EventCreate(
                timestamp=t + timedelta(seconds=review_delay),
                application="browser",
                event_type="github_event",
                action="pr_review",
                target=f"github.com/{repo}/pulls",
                source="simulation",
                metadata={"developer_id": reviewer, "repo": repo},
            ))
        return events

    def _generate_documentation_searches(self, day_base: datetime) -> List[EventCreate]:
        events = []
        for _ in range(self.rng.randint(12, 18)):
            dev = self.rng.choice(DEVELOPERS)
            t = _ts(day_base, self.rng.uniform(9 * 3600, 17 * 3600))
            events.append(EventCreate(
                timestamp=t,
                application="browser",
                event_type="browser_navigation",
                action="navigate",
                target=self.rng.choice(DOC_TARGETS),
                source="simulation",
                metadata={"developer_id": dev, "query": self.rng.choice(["CI failure", "pytest fixtures", "docker compose", "kubernetes ingress"])},
            ))
        return events

    def _generate_docker_activity(self, day_base: datetime) -> List[EventCreate]:
        events = []
        for _ in range(self.rng.randint(8, 15)):
            dev = self.rng.choice(DEVELOPERS)
            t = _ts(day_base, self.rng.uniform(9 * 3600, 17 * 3600))
            action = self.rng.choice(["container_start", "container_stop", "image_build", "compose_up"])
            events.append(EventCreate(
                timestamp=t,
                application="docker",
                event_type="docker_event",
                action=action,
                target=self.rng.choice(REPOSITORIES),
                source="simulation",
                metadata={"developer_id": dev},
            ))
        return events

    def _generate_git_commits(self, day_base: datetime) -> List[EventCreate]:
        events = []
        for _ in range(self.rng.randint(25, 35)):
            dev = self.rng.choice(DEVELOPERS)
            repo = self.rng.choice(REPOSITORIES)
            t = _ts(day_base, self.rng.uniform(9 * 3600, 17 * 3600))
            events.append(EventCreate(
                timestamp=t,
                application="git",
                event_type="git_command",
                action="git_commit",
                target=repo,
                source="simulation",
                metadata={"developer_id": dev, "repo": repo, "message": self.rng.choice(PR_TEMPLATES)},
            ))
        return events

    def _generate_incident(self, day_base: datetime) -> List[EventCreate]:
        events = []
        dev = self.rng.choice(DEVELOPERS)
        repo = self.rng.choice(REPOSITORIES)
        t = _ts(day_base, self.rng.uniform(10 * 3600, 16 * 3600))

        events.append(EventCreate(
            timestamp=t,
            application="alerting",
            event_type="incident_event",
            action="incident_detected",
            target=repo,
            source="simulation",
            metadata={"developer_id": dev, "severity": self.rng.choice(["low", "medium"])},
        ))

        for offset, (app, etype, action, target) in enumerate([
            ("browser", "browser_navigation", "navigate", "status.company.com"),
            ("terminal", "terminal_command", "git_log_--oneline_-20", ""),
            ("browser", "browser_navigation", "navigate", "github.com/org/repo/commit"),
            ("slack", "communication_event", "send_notification", "incidents"),
        ]):
            events.append(EventCreate(
                timestamp=t + timedelta(seconds=self.rng.uniform(60, 300) * (offset + 1)),
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "repo": repo},
            ))
        return events

    def _generate_linkedin_job_search(self, day_base: datetime) -> List[EventCreate]:
        events = []
        if self.rng.random() > 0.7:
            return events
        dev = self.rng.choice(DEVELOPERS)
        t = _ts(day_base, self.rng.uniform(8 * 3600, 9.5 * 3600))
        sequence = [
            ("browser", "browser_navigation", "navigate", "linkedin.com"),
            ("browser", "browser_navigation", "navigate", "linkedin.com/jobs"),
            ("browser", "browser_navigation", "navigate", "linkedin.com/jobs/search?keywords=software+engineer&f_WT=2"),
            ("browser", "browser_navigation", "navigate", "linkedin.com/jobs/view/12345"),
            ("browser", "form_interaction", "fill_field", "linkedin.com/jobs/apply"),
            ("browser", "form_interaction", "fill_field", "linkedin.com/jobs/apply/resume"),
            ("browser", "form_interaction", "submit_form", "linkedin.com/jobs/apply/submit"),
            ("browser", "browser_navigation", "navigate", "linkedin.com/jobs/view/67890"),
            ("browser", "form_interaction", "fill_field", "linkedin.com/jobs/apply"),
            ("browser", "form_interaction", "submit_form", "linkedin.com/jobs/apply/submit"),
        ]
        for app, etype, action, target in sequence:
            t += timedelta(seconds=self.rng.uniform(20, 90))
            events.append(EventCreate(
                timestamp=t,
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "workflow": "job_application"},
            ))
        return events

    def _generate_email_triage(self, day_base: datetime) -> List[EventCreate]:
        events = []
        if self.rng.random() > 0.8:
            return events
        dev = self.rng.choice(DEVELOPERS)
        t = _ts(day_base, self.rng.uniform(8.5 * 3600, 9 * 3600))
        sequence = [
            ("browser", "browser_navigation", "navigate", "mail.google.com"),
            ("browser", "browser_navigation", "navigate", "mail.google.com/inbox"),
            ("browser", "form_interaction", "click_label", "mail.google.com/label"),
            ("browser", "form_interaction", "archive_email", "mail.google.com/archive"),
            ("browser", "form_interaction", "click_email", "mail.google.com/email/1"),
            ("browser", "form_interaction", "reply_email", "mail.google.com/reply"),
            ("browser", "form_interaction", "archive_email", "mail.google.com/archive"),
            ("browser", "form_interaction", "click_email", "mail.google.com/email/2"),
            ("browser", "form_interaction", "label_email", "mail.google.com/label"),
        ]
        for app, etype, action, target in sequence:
            t += timedelta(seconds=self.rng.uniform(15, 60))
            events.append(EventCreate(
                timestamp=t,
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "workflow": "email_triage"},
            ))
        return events

    def _generate_standup_prep(self, day_base: datetime) -> List[EventCreate]:
        events = []
        if self.rng.random() > 0.85:
            return events
        dev = self.rng.choice(DEVELOPERS)
        t = _ts(day_base, self.rng.uniform(9 * 3600, 9.5 * 3600))
        sequence = [
            ("terminal", "terminal_command", "git_log_--oneline_-5", ""),
            ("browser", "browser_navigation", "navigate", "ci.company.com"),
            ("browser", "browser_navigation", "navigate", "github.com/org/repo/pulls"),
            ("slack", "communication_event", "compose_message", "standup-channel"),
            ("slack", "communication_event", "send_message", "standup-channel"),
        ]
        for app, etype, action, target in sequence:
            t += timedelta(seconds=self.rng.uniform(20, 60))
            events.append(EventCreate(
                timestamp=t,
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "workflow": "standup_prep"},
            ))
        return events

    def _generate_jira_ticket_creation(self, day_base: datetime) -> List[EventCreate]:
        events = []
        if self.rng.random() > 0.6:
            return events
        dev = self.rng.choice(DEVELOPERS)
        t = _ts(day_base, self.rng.uniform(10 * 3600, 14 * 3600))
        sequence = [
            ("browser", "browser_navigation", "navigate", "jira.company.com"),
            ("browser", "browser_navigation", "navigate", "jira.company.com/board"),
            ("browser", "form_interaction", "click_button", "jira.company.com/create"),
            ("browser", "form_interaction", "fill_field", "jira.company.com/create/title"),
            ("browser", "form_interaction", "fill_field", "jira.company.com/create/description"),
            ("browser", "form_interaction", "select_option", "jira.company.com/create/assignee"),
            ("browser", "form_interaction", "submit_form", "jira.company.com/create/submit"),
        ]
        for app, etype, action, target in sequence:
            t += timedelta(seconds=self.rng.uniform(15, 45))
            events.append(EventCreate(
                timestamp=t,
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "workflow": "jira_ticket"},
            ))
        return events

    def _generate_dependency_update_check(self, day_base: datetime) -> List[EventCreate]:
        events = []
        if self.rng.random() > 0.5:
            return events
        dev = self.rng.choice(DEVELOPERS)
        t = _ts(day_base, self.rng.uniform(11 * 3600, 15 * 3600))
        sequence = [
            ("terminal", "terminal_command", "npm_outdated", ""),
            ("browser", "browser_navigation", "navigate", "npmjs.com/package/react"),
            ("browser", "browser_navigation", "navigate", "github.com/facebook/react/releases"),
            ("terminal", "terminal_command", "npm_install_react@latest", ""),
            ("terminal", "terminal_command", "npm_test", ""),
        ]
        for app, etype, action, target in sequence:
            t += timedelta(seconds=self.rng.uniform(30, 120))
            events.append(EventCreate(
                timestamp=t,
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "workflow": "dependency_update"},
            ))
        return events

    def _generate_meeting_prep(self, day_base: datetime) -> List[EventCreate]:
        events = []
        if self.rng.random() > 0.5:
            return events
        dev = self.rng.choice(DEVELOPERS)
        t = _ts(day_base, self.rng.uniform(9.5 * 3600, 13 * 3600))
        sequence = [
            ("browser", "browser_navigation", "navigate", "calendar.google.com"),
            ("browser", "browser_navigation", "navigate", "notion.so/meeting-notes"),
            ("browser", "browser_navigation", "navigate", "github.com/org/repo/pulls"),
            ("browser", "form_interaction", "fill_field", "notion.so/new-page"),
            ("browser", "form_interaction", "fill_field", "notion.so/agenda"),
        ]
        for app, etype, action, target in sequence:
            t += timedelta(seconds=self.rng.uniform(20, 80))
            events.append(EventCreate(
                timestamp=t,
                application=app,
                event_type=etype,
                action=action,
                target=target,
                source="simulation",
                metadata={"developer_id": dev, "workflow": "meeting_prep"},
            ))
        return events


def create_generator(seed: int = 42) -> SyntheticEventGenerator:
    return SyntheticEventGenerator(seed=seed)

