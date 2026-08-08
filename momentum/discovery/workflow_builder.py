import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import Counter
from momentum.models.workflow import WorkflowRecord
from momentum.models.session import SessionRecord
from momentum.discovery.sequence_extractor import (
    extract_sequence,
    find_common_subsequence,
    sequence_to_token_list,
)
from momentum.discovery.pattern_miner import compute_pattern_stats
from momentum.discovery.clusterer import compute_cluster_embedding, compute_cluster_coherence
from momentum.database.base import get_db
import uuid


def _infer_workflow_name(sequences: List[List[dict]], stats: Dict) -> str:
    all_targets = []
    all_actions = []
    all_types = []
    all_apps = []
    for seq in sequences:
        for step in seq:
            t = str(step.get("target", "")).lower()
            a = str(step.get("action", "")).lower()
            e = str(step.get("event_type", "")).lower()
            ap = str(step.get("application", "")).lower()
            if t:
                all_targets.append(t)
            if a:
                all_actions.append(a)
            if e:
                all_types.append(e)
            if ap:
                all_apps.append(ap)

    target_blob = " ".join(all_targets)
    action_blob = " ".join(all_actions)
    meta_blob = " ".join(str(s.get("metadata", "")) for seq in sequences for s in seq).lower()

    has_form = "form_interaction" in all_types
    has_submit = "submit" in action_blob or "submit_form" in action_blob
    has_fill = "fill" in action_blob

    if "linkedin.com" in target_blob and (has_form or "apply" in target_blob):
        return "LinkedIn Job Application"
    if ("indeed.com" in target_blob or "glassdoor.com" in target_blob) and has_form:
        return "Job Application Loop"
    if "job_application" in meta_blob or "job_search" in meta_blob:
        return "Job Application Loop"

    if ("mail.google.com" in target_blob or "outlook" in target_blob or "email_triage" in meta_blob):
        return "Email Triage"

    if "standup" in target_blob or "standup_prep" in meta_blob or (
        "standup" in action_blob
    ):
        return "Daily Standup Prep"

    if "jira" in target_blob or "jira_ticket" in meta_blob:
        return "Jira Ticket Creation"

    if ("notion.so" in target_blob or "meeting_prep" in meta_blob) and "calendar" in target_blob:
        return "Meeting Prep"

    if "dependency_update" in meta_blob or (
        "npm_outdated" in action_blob or "pip_list" in action_blob
    ):
        return "Dependency Update Check"

    if "calendar.google.com" in target_blob:
        return "Calendar and Planning"

    top_apps = stats.get("top_applications", [])
    top_types = stats.get("top_event_types", [])

    type_signatures = [
        (({"ci_event"}, {"browser_navigation", "terminal_command"}), "CI Failure Investigation"),
        (({"incident_event"}, {"browser_navigation", "communication_event"}), "Incident Response"),
        (({"github_event", "pr_event"}, {"browser_navigation"}), "Pull Request Review"),
        (({"github_event"}, {"git_command", "terminal_command"}), "Release Preparation"),
        (({"docker_event"}, {"terminal_command"}), "Service Deployment Check"),
        (({"git_command", "editor_event"}, {"terminal_command"}), "Development Iteration"),
        (({"browser_navigation", "terminal_command"}, {"git_command"}), "Code Review and Commit"),
        (({"browser_navigation"}, {"communication_event"}), "Issue Triage and Notification"),
    ]

    type_set = set(all_types)
    for (required, secondary), name in type_signatures:
        if required.issubset(type_set) or (required & type_set and secondary & type_set):
            return name

    app_name_map = {
        "linkedin": "LinkedIn", "gmail": "Gmail", "slack": "Slack",
        "ci": "CI Pipeline", "github": "GitHub", "docker": "Docker",
        "jira": "Jira", "notion": "Notion", "terminal": "Terminal",
    }
    parts = []
    for app in top_apps[:2]:
        for key, label in app_name_map.items():
            if key in app.lower():
                parts.append(label)
                break
    if parts:
        return " + ".join(parts) + " Workflow"

    if top_types:
        primary = top_types[0].replace("_", " ").title()
        return f"Recurring {primary} Workflow"
    return "Developer Workflow"


def _infer_trigger(common_seq: List[dict]) -> str:
    if not common_seq:
        return "periodic"
    first = common_seq[0]
    event_type = first.get("event_type", "")
    action = first.get("action", "")
    target = str(first.get("target", "")).lower()

    if event_type == "ci_event":
        return "ci_build_failed"
    if event_type == "github_event" and "pr" in action:
        return "pull_request_created"
    if event_type == "incident_event":
        return "incident_detected"
    if event_type == "terminal_command" and "git_push" in action:
        return "git_push"
    if "linkedin" in target:
        return "scheduled:morning"
    if "mail.google.com" in target or "outlook" in target:
        return "scheduled:morning"
    if "jira" in target:
        return "on_demand"
    if "calendar" in target:
        return "scheduled:pre_meeting"
    return f"{event_type}:{action[:30]}" if action else event_type


def _infer_goal(name: str, common_seq: List[dict]) -> str:
    event_types = set(s.get("event_type", "") for s in common_seq)
    targets = " ".join(str(s.get("target", "")).lower() for s in common_seq)

    goal_map = {
        "LinkedIn Job Application": "Search for relevant jobs on LinkedIn and submit Easy Apply applications automatically",
        "Job Application Loop": "Search for jobs matching your criteria and submit applications efficiently",
        "Email Triage": "Process the inbox — archive, label, and respond to emails in a structured pass",
        "Daily Standup Prep": "Collect git log, CI status, and open PRs then compose and send the standup message",
        "Jira Ticket Creation": "Create and configure a new Jira ticket with the appropriate fields and assignee",
        "Meeting Prep": "Gather agenda, check calendar, and open relevant documents before a meeting",
        "Dependency Update Check": "Identify outdated dependencies, review changelogs, and run tests after upgrading",
        "CI Failure Investigation": "Investigate a CI build failure, identify the responsible change, and notify the team",
        "Incident Response": "Triage an incident, gather context from logs and commits, and notify stakeholders",
        "Pull Request Review": "Review a pull request — inspect the diff, check CI, and draft feedback",
        "Release Preparation": "Gather merged PRs and generate release notes for a deployment",
    }

    if name in goal_map:
        return goal_map[name]

    has_communication = "communication_event" in event_types
    has_ci = "ci_event" in event_types
    has_git = "git_command" in event_types or "git_event" in event_types
    has_browser = "browser_navigation" in event_types

    if has_ci and has_communication:
        return "Investigate a CI build failure and notify the team"
    if has_git and has_browser:
        return "Review recent code changes and gather context for decision making"
    if has_communication:
        return "Gather context and communicate status to the team"
    return f"Complete the {name.lower()} task efficiently"




def _compute_decision_points(sequences: List[List[dict]]) -> List[str]:
    if not sequences:
        return []
    all_event_types = Counter()
    for seq in sequences:
        for step in seq:
            all_event_types[step.get("event_type", "")] += 1

    decision_indicators = {
        "communication_event": "Deciding who to notify",
        "github_event": "Selecting the relevant PR or commit",
        "browser_navigation": "Choosing which URL to inspect",
        "terminal_command": "Selecting diagnostic command",
        "ci_event": "Evaluating CI failure severity",
    }

    decisions = []
    for event_type, label in decision_indicators.items():
        if event_type in all_event_types:
            decisions.append(label)
    return decisions[:4]


def _compute_risk_score(
    sequences: List[List[dict]],
    applications: List[str],
    decision_points: List[str],
) -> float:
    has_write = any(
        "push" in str(s) or "delete" in str(s) or "deploy" in str(s)
        for seq in sequences for s in seq
    )
    has_communication = any(
        s.get("event_type") == "communication_event" for seq in sequences for s in seq
    )
    decision_count = len(decision_points)

    risk = 0.15
    if has_write:
        risk += 0.3
    if has_communication:
        risk += 0.15
    risk += min(decision_count * 0.05, 0.25)
    return min(risk, 0.9)


def build_workflow_from_cluster(
    sessions: List[SessionRecord],
    cluster_indices: List[int],
    embeddings: np.ndarray,
    cluster_id: int,
) -> Optional[WorkflowRecord]:
    cluster_sessions = [sessions[i] for i in cluster_indices]
    sequences = [extract_sequence(s) for s in cluster_sessions]
    sequences = [s for s in sequences if s is not None]

    if len(sequences) < 2:
        return None

    common_seq = find_common_subsequence(sequences)
    if not common_seq:
        return None

    stats = compute_pattern_stats(sequences)
    name = _infer_workflow_name(sequences, stats)

    durations = [s.duration or 0.0 for s in cluster_sessions if s.duration]
    avg_dur = float(np.mean(durations)) if durations else 120.0
    med_dur = float(np.median(durations)) if durations else 120.0
    var_dur = float(np.var(durations)) if len(durations) > 1 else 0.0

    timestamps = sorted([s.start_time for s in cluster_sessions if s.start_time])
    first_seen = timestamps[0] if timestamps else None
    last_seen = timestamps[-1] if timestamps else None

    if first_seen and last_seen:
        total_days = max((last_seen - first_seen).total_seconds() / 86400, 1.0)
        frequency = len(sequences) / total_days * 7
    else:
        frequency = float(len(sequences))

    all_apps = []
    all_repos = []
    for s in cluster_sessions:
        all_apps.extend(s.get_applications())
        if s.repository:
            all_repos.append(s.repository)

    unique_apps = list(set(all_apps))
    unique_repos = list(set(all_repos))

    coherence = compute_cluster_coherence(embeddings, cluster_indices)
    centroid = compute_cluster_embedding(embeddings, cluster_indices)

    decision_points = _compute_decision_points(sequences)
    risk_score = _compute_risk_score(sequences, unique_apps, decision_points)

    seq_lengths = [len(s) for s in sequences]
    length_variance = float(np.var(seq_lengths)) if len(seq_lengths) > 1 else 0.0
    determinism_score = max(0.0, 1.0 - (length_variance / max(np.mean(seq_lengths) ** 2, 1.0)))

    session_ids = [s.session_id for s in cluster_sessions]

    evidence = []
    for i, session in enumerate(cluster_sessions[:5]):
        evidence.append({
            "session_id": session.session_id,
            "timestamp": session.start_time.isoformat() if session.start_time else "",
            "duration_seconds": session.duration or 0,
            "event_count": session.event_count,
            "applications": session.get_applications(),
        })

    trigger = _infer_trigger(common_seq)
    goal = _infer_goal(name, common_seq)

    weekly_minutes = frequency * avg_dur / 60.0
    annual_minutes = weekly_minutes * 52

    return WorkflowRecord(
        id=str(uuid.uuid4()),
        name=name,
        trigger=trigger,
        goal=goal,
        steps_json=json.dumps(common_seq),
        frequency=frequency,
        first_seen=first_seen,
        last_seen=last_seen,
        average_duration=avg_dur,
        median_duration=med_dur,
        duration_variance=var_dur,
        applications_json=json.dumps(unique_apps),
        repositories_json=json.dumps(unique_repos),
        decision_points_json=json.dumps(decision_points),
        success_rate=1.0,
        repetition_score=float(min(len(sequences) / 20.0, 1.0)),
        determinism_score=float(np.clip(determinism_score, 0.0, 1.0)),
        risk_score=risk_score,
        automation_score=0.0,
        confidence=float(np.clip(coherence * 0.6 + min(len(sequences) / 30.0, 0.4), 0.0, 1.0)),
        estimated_weekly_minutes=weekly_minutes,
        estimated_annual_minutes=annual_minutes,
        evidence_json=json.dumps(evidence),
        status="discovered",
        session_ids_json=json.dumps(session_ids),
        embedding_json=json.dumps(centroid.tolist()),
        cluster_id=cluster_id,
    )


def save_workflows(workflows: List[WorkflowRecord]) -> int:
    with get_db() as db:
        for w in workflows:
            existing = db.query(WorkflowRecord).filter(WorkflowRecord.id == w.id).first()
            if not existing:
                db.add(w)
        return len(workflows)


def get_all_workflows() -> List[WorkflowRecord]:
    with get_db() as db:
        return db.query(WorkflowRecord).order_by(WorkflowRecord.automation_score.desc()).all()


def get_workflow_by_id(workflow_id: str) -> Optional[WorkflowRecord]:
    with get_db() as db:
        return db.query(WorkflowRecord).filter(WorkflowRecord.id == workflow_id).first()
