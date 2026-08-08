import json
import logging
from datetime import datetime
from typing import Optional
from momentum.learning.bandit import get_bandit
from momentum.learning.reward import calculate_reward, calculate_confidence_delta, calculate_time_saved
from momentum.models.outcome import OutcomeRecord
from momentum.models.automation import AutomationRecord
from momentum.database.base import get_db

logger = logging.getLogger(__name__)


def build_workflow_context(automation: AutomationRecord, workflow_data: Optional[dict] = None) -> dict:
    plan = automation.get_plan()
    wf = workflow_data or {}
    return {
        "frequency": wf.get("frequency", 5.0),
        "average_duration": wf.get("average_duration", 300.0),
        "duration_variance": wf.get("duration_variance", 60.0),
        "repetition_score": wf.get("repetition_score", 0.5),
        "determinism_score": wf.get("determinism_score", 0.6),
        "risk_score": wf.get("risk_score", 0.3),
        "decision_count": float(len(wf.get("decision_points", []))),
        "estimated_savings": wf.get("estimated_weekly_minutes", 60.0),
        "implementation_effort": 0.4,
        "historical_success": (
            automation.success_count / max(automation.execution_count, 1)
        ),
        "user_approval_rate": 1.0 if automation.execution_count == 0 else (
            automation.success_count / max(automation.execution_count, 1)
        ),
        "workflow_similarity": 0.5,
    }


def process_outcome(outcome: OutcomeRecord, automation: AutomationRecord, workflow_data: Optional[dict] = None) -> float:
    bandit = get_bandit()

    workflow_context = build_workflow_context(automation, workflow_data)
    action_idx, action_name, context_tensor = bandit.select_action(workflow_context)

    reward = calculate_reward(
        success=outcome.success,
        time_saved=outcome.time_saved,
        human_intervention=outcome.human_intervention,
        user_feedback=outcome.user_feedback,
        execution_time=outcome.execution_time,
        confidence_before=outcome.confidence_before,
        risk_score=workflow_data.get("risk_score", 0.3) if workflow_data else 0.3,
        consecutive_failures=automation.consecutive_failures,
    )

    loss = bandit.update(context_tensor, action_idx, reward)
    bandit.decay_epsilon()

    conf_delta = calculate_confidence_delta(
        success=outcome.success,
        reward=reward,
        evidence_count=automation.execution_count,
        human_intervention=outcome.human_intervention,
        consecutive_failures=automation.consecutive_failures,
    )

    new_confidence = float(max(0.05, min(0.98, automation.confidence + conf_delta)))

    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation.id).first()
        if auto:
            auto.confidence = new_confidence
            auto.execution_count += 1
            if outcome.success:
                auto.success_count += 1
                auto.consecutive_failures = 0
                auto.total_time_saved += outcome.time_saved
            else:
                auto.failure_count += 1
                auto.consecutive_failures += 1
                from momentum.config.settings import settings
                if auto.consecutive_failures >= settings.MOMENTUM_MAX_CONSECUTIVE_FAILURES:
                    auto.status = "paused"
                    logger.warning(f"Automation {auto.id} auto-paused after {auto.consecutive_failures} consecutive failures")
            auto.last_executed_at = datetime.utcnow()

        out = db.query(OutcomeRecord).filter(OutcomeRecord.id == outcome.id).first()
        if out:
            out.reward = reward
            out.confidence_after = new_confidence
            out.policy_version = str(bandit.version)

    logger.info(f"Outcome processed: success={outcome.success} reward={reward:.3f} conf_delta={conf_delta:+.3f} loss={loss:.4f}")
    return reward


def run_learning_from_history() -> dict:
    bandit = get_bandit()

    with get_db() as db:
        outcomes = (
            db.query(OutcomeRecord)
            .order_by(OutcomeRecord.timestamp)
            .all()
        )

    if not outcomes:
        return {"message": "No outcomes to learn from", "updates": 0}

    updates = 0
    total_reward = 0.0

    for outcome in outcomes:
        with get_db() as db:
            auto = db.query(AutomationRecord).filter(AutomationRecord.id == outcome.automation_id).first()
            if not auto:
                continue

        ctx = build_workflow_context(auto)
        _, _, context_tensor = bandit.select_action(ctx)
        action_idx = 3 if outcome.success else 6

        loss = bandit.update(context_tensor, action_idx, outcome.reward)
        total_reward += outcome.reward
        updates += 1

    bandit.decay_epsilon(factor=0.99)

    stats = bandit.get_stats()
    return {
        "updates": updates,
        "average_reward": total_reward / max(updates, 1),
        "bandit_version": stats["version"],
        "epsilon": stats["epsilon"],
        "average_reward_last_20": stats["average_reward_last_20"],
    }
