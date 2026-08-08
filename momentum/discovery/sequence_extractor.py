from typing import List, Dict, Tuple, Optional
from momentum.models.session import SessionRecord
import re


def extract_sequence(session: SessionRecord, min_length: int = 3) -> Optional[List[dict]]:
    seq = session.get_event_sequence()
    if len(seq) < min_length:
        return None

    filtered = []
    for step in seq:
        event_type = step.get("event_type", "")
        if event_type == "idle":
            continue
        filtered.append({
            "event_type": event_type,
            "application": step.get("application", "unknown"),
            "action": _normalize_action(step.get("action", "")),
            "target": _normalize_target(step.get("target", "")),
        })

    if len(filtered) < min_length:
        return None

    return filtered


def _normalize_action(action: str) -> str:
    if not action:
        return ""
    action = action.lower().strip()
    if action.startswith("git "):
        parts = action.split()
        return "git_" + parts[1] if len(parts) > 1 else "git"
    for keyword in ["docker", "npm", "pytest", "python", "curl", "ssh", "kubectl"]:
        if action.startswith(keyword):
            return keyword
    return action[:40].replace(" ", "_")


def _normalize_target(target: str) -> str:
    if not target:
        return ""
    target = target.lower()
    target = re.sub(r"/\d+", "/{id}", target)
    target = re.sub(r"[a-f0-9]{7,40}", "{hash}", target)
    target = re.sub(r"\b\d{4,}\b", "{num}", target)
    return target[:50]


def sequence_to_token_list(sequence: List[dict]) -> List[str]:
    tokens = []
    for step in sequence:
        tok = f"{step['event_type']}::{step['application']}"
        if step.get("action"):
            tok += f"::{step['action']}"
        tokens.append(tok)
    return tokens


def compute_sequence_ngrams(sequence: List[dict], n: int = 3) -> List[Tuple]:
    tokens = sequence_to_token_list(sequence)
    ngrams = []
    for i in range(len(tokens) - n + 1):
        ngrams.append(tuple(tokens[i:i + n]))
    return ngrams


def find_common_subsequence(sequences: List[List[dict]], threshold: float = 0.5) -> List[dict]:
    if not sequences:
        return []
    if len(sequences) == 1:
        return sequences[0]

    token_lists = [sequence_to_token_list(s) for s in sequences]
    all_tokens = []
    for tl in token_lists:
        all_tokens.extend(tl)

    token_counts: Dict[str, int] = {}
    for tok in all_tokens:
        token_counts[tok] = token_counts.get(tok, 0) + 1

    min_count = max(1, int(len(sequences) * threshold))
    common_tokens = {t for t, c in token_counts.items() if c >= min_count}

    representative = max(sequences, key=len)
    common_steps = []
    for step in representative:
        tok = f"{step['event_type']}::{step['application']}"
        if tok in common_tokens or any(t.startswith(f"{step['event_type']}::{step['application']}") for t in common_tokens):
            common_steps.append(step)

    return common_steps if len(common_steps) >= 2 else representative[:5]
