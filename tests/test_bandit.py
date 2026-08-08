import torch
from momentum.learning.bandit import ContextualBandit, ACTIONS, ACTION_DIM, CONTEXT_DIM
from momentum.learning.reward import calculate_reward, calculate_confidence_delta


def test_bandit_initialization():
    bandit = ContextualBandit(epsilon=0.15, lr=0.001)
    assert bandit.epsilon == 0.15
    assert bandit.version == 0


def test_bandit_select_action():
    bandit = ContextualBandit(epsilon=0.0)
    ctx = {
        "frequency": 10.0,
        "average_duration": 300.0,
        "duration_variance": 30.0,
        "repetition_score": 0.8,
        "determinism_score": 0.7,
        "risk_score": 0.2,
        "decision_count": 2.0,
        "estimated_savings": 120.0,
        "implementation_effort": 0.4,
        "historical_success": 0.9,
        "user_approval_rate": 1.0,
        "workflow_similarity": 0.5,
    }
    action_idx, action_name, context_tensor = bandit.select_action(ctx)
    assert 0 <= action_idx < ACTION_DIM
    assert action_name in ACTIONS
    assert context_tensor.shape == (CONTEXT_DIM,)


def test_bandit_update():
    bandit = ContextualBandit(epsilon=0.0)
    ctx = {k: 0.5 for k in [
        "frequency", "average_duration", "duration_variance",
        "repetition_score", "determinism_score", "risk_score",
        "decision_count", "estimated_savings", "implementation_effort",
        "historical_success", "user_approval_rate", "workflow_similarity",
    ]}
    _, _, tensor = bandit.select_action(ctx)
    loss = bandit.update(tensor, 0, 1.0)
    assert loss >= 0.0
    assert bandit.version == 1


def test_bandit_epsilon_decay():
    bandit = ContextualBandit(epsilon=0.5)
    bandit.decay_epsilon(factor=0.9, min_epsilon=0.02)
    assert abs(bandit.epsilon - 0.45) < 0.001


def test_reward_success():
    reward = calculate_reward(
        success=True,
        time_saved=300.0,
        human_intervention=False,
        user_feedback="positive",
        execution_time=15.0,
        confidence_before=0.8,
        risk_score=0.2,
        consecutive_failures=0,
    )
    assert reward > 1.0


def test_reward_failure():
    reward = calculate_reward(
        success=False,
        time_saved=0.0,
        human_intervention=True,
        user_feedback="negative",
        execution_time=0.0,
        confidence_before=0.9,
        risk_score=0.5,
        consecutive_failures=3,
    )
    assert reward < 0.0


def test_confidence_delta_success():
    delta = calculate_confidence_delta(
        success=True,
        reward=1.5,
        evidence_count=50,
        human_intervention=False,
        consecutive_failures=0,
    )
    assert delta > 0.0


def test_confidence_delta_failure():
    delta = calculate_confidence_delta(
        success=False,
        reward=-1.0,
        evidence_count=5,
        human_intervention=True,
        consecutive_failures=2,
    )
    assert delta < 0.0
