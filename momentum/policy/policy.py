from typing import Dict, Tuple
from momentum.learning.bandit import ACTIONS

AUTONOMY_LEVELS = {
    0: "observation",
    1: "recommendation",
    2: "automation_preparation",
    3: "supervised_execution",
    4: "autonomous_execution",
    5: "adaptive_autonomous_execution",
}

ACTION_TO_AUTONOMY: Dict[str, int] = {
    "OBSERVE_MORE": 0,
    "RECOMMEND": 1,
    "PREPARE": 2,
    "REQUEST_APPROVAL": 2,
    "SUPERVISED_EXECUTION": 3,
    "AUTONOMOUS_EXECUTION": 4,
    "REDUCE_AUTONOMY": 1,
    "DO_NOT_AUTOMATE": 0,
}

HIGH_RISK_THRESHOLD = 0.65

def compute_autonomy_level(
    current_level: int,
    success: bool,
    risk_score: float,
    confidence: float,
    consecutive_failures: int,
    execution_count: int,
    success_count: int,
) -> int:
    if risk_score >= HIGH_RISK_THRESHOLD:
        return min(current_level, 3)

    if not success:
        new_level = max(0, current_level - 1)
        if consecutive_failures >= 3:
            new_level = max(0, current_level - 2)
        return new_level

    success_rate = success_count / max(execution_count, 1)
    if confidence >= 0.85 and success_rate >= 0.90 and execution_count >= 5:
        return min(current_level + 1, 5)
    if confidence >= 0.75 and success_rate >= 0.80 and execution_count >= 3:
        return min(current_level + 1, 4)

    return current_level

def action_name_to_autonomy(action_name: str) -> int:
    return ACTION_TO_AUTONOMY.get(action_name, 3)

def get_autonomy_description(level: int) -> str:
    return AUTONOMY_LEVELS.get(level, "unknown")

def should_require_approval(autonomy_level: int, risk_score: float) -> bool:
    if risk_score >= HIGH_RISK_THRESHOLD:
        return True
    return autonomy_level < 4

def get_policy_summary(
    autonomy_level: int,
    confidence: float,
    risk_score: float,
    execution_count: int,
    success_count: int,
) -> Dict:
    success_rate = success_count / max(execution_count, 1)
    return {
        "autonomy_level": autonomy_level,
        "autonomy_description": get_autonomy_description(autonomy_level),
        "confidence": confidence,
        "risk_score": risk_score,
        "execution_count": execution_count,
        "success_count": success_count,
        "success_rate": success_rate,
        "requires_approval": should_require_approval(autonomy_level, risk_score),
        "can_increase_autonomy": confidence >= 0.75 and success_rate >= 0.80,
    }
