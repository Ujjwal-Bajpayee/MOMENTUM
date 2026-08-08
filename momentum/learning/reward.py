import numpy as np
from typing import Optional


def calculate_reward(
    success: bool,
    time_saved: float,
    human_intervention: bool,
    user_feedback: Optional[str],
    execution_time: float,
    confidence_before: float,
    risk_score: float,
    consecutive_failures: int,
) -> float:
    if success:
        base = 1.0
        time_bonus = float(np.clip(time_saved / 600.0, 0.0, 2.0))
        intervention_penalty = -0.5 if human_intervention else 0.0
        feedback_bonus = (
            0.5 if user_feedback == "positive"
            else (-0.4 if user_feedback == "negative" else 0.0)
        )
        risk_bonus = (1.0 - risk_score) * 0.3
        speed_bonus = 0.2 if execution_time < 30.0 else 0.0

        reward = base + time_bonus + intervention_penalty + feedback_bonus + risk_bonus + speed_bonus
        return float(np.clip(reward, 0.05, 5.0))

    base = -1.0
    intervention_penalty = -0.3 if human_intervention else 0.0
    risk_penalty = -float(risk_score) * 0.5
    consecutive_penalty = -0.25 * float(min(consecutive_failures, 5))
    feedback_penalty = -0.5 if user_feedback == "negative" else 0.0
    high_conf_penalty = -0.3 if confidence_before > 0.85 else 0.0

    reward = base + intervention_penalty + risk_penalty + consecutive_penalty + feedback_penalty + high_conf_penalty
    return float(np.clip(reward, -5.0, -0.05))


def calculate_confidence_delta(
    success: bool,
    reward: float,
    evidence_count: int,
    human_intervention: bool,
    consecutive_failures: int,
) -> float:
    if success and not human_intervention:
        base_delta = 0.04
        evidence_factor = min(evidence_count / 500.0, 0.03)
        return base_delta + evidence_factor

    if success and human_intervention:
        return 0.005

    base_penalty = -0.08
    consecutive_factor = -0.02 * min(consecutive_failures, 5)
    return float(np.clip(base_penalty + consecutive_factor, -0.30, 0.0))


def calculate_time_saved(
    automation_execution_time: float,
    estimated_manual_duration: float,
) -> float:
    saved = estimated_manual_duration - automation_execution_time
    return float(max(saved, 0.0))
