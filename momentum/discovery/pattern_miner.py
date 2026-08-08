from typing import List, Dict, Tuple, Set
from collections import Counter
from momentum.discovery.sequence_extractor import compute_sequence_ngrams, sequence_to_token_list


def mine_frequent_patterns(
    sequences: List[List[dict]],
    min_support: int = 3,
    ngram_sizes: List[int] = [2, 3, 4, 5],
) -> List[Tuple[tuple, int]]:
    all_ngrams: Counter = Counter()
    for seq in sequences:
        for n in ngram_sizes:
            if len(seq) >= n:
                ngrams = compute_sequence_ngrams(seq, n)
                all_ngrams.update(ngrams)

    frequent = [(ngram, count) for ngram, count in all_ngrams.items() if count >= min_support]
    frequent.sort(key=lambda x: x[1], reverse=True)
    return frequent


def compute_sequence_similarity(seq_a: List[dict], seq_b: List[dict]) -> float:
    if not seq_a or not seq_b:
        return 0.0
    tokens_a = set(sequence_to_token_list(seq_a))
    tokens_b = set(sequence_to_token_list(seq_b))
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


def find_pattern_groups(
    sequences: List[List[dict]],
    session_ids: List[str],
    similarity_threshold: float = 0.35,
) -> List[List[int]]:
    n = len(sequences)
    if n == 0:
        return []

    groups: List[List[int]] = []
    assigned = set()

    for i in range(n):
        if i in assigned:
            continue
        group = [i]
        for j in range(i + 1, n):
            if j in assigned:
                continue
            sim = compute_sequence_similarity(sequences[i], sequences[j])
            if sim >= similarity_threshold:
                group.append(j)
        if len(group) >= 2:
            for idx in group:
                assigned.add(idx)
            groups.append(group)

    return groups


def compute_pattern_stats(
    group_sequences: List[List[dict]],
) -> Dict:
    if not group_sequences:
        return {}

    lengths = [len(s) for s in group_sequences]
    all_apps = []
    all_event_types = []
    for seq in group_sequences:
        for step in seq:
            all_apps.append(step.get("application", ""))
            all_event_types.append(step.get("event_type", ""))

    app_counts = Counter(all_apps)
    type_counts = Counter(all_event_types)

    return {
        "count": len(group_sequences),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "top_applications": [a for a, _ in app_counts.most_common(5)],
        "top_event_types": [t for t, _ in type_counts.most_common(5)],
        "application_diversity": len(set(all_apps)),
    }
