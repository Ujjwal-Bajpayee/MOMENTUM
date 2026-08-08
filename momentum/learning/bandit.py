import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Tuple, List, Optional, Dict
from pathlib import Path

CONTEXT_DIM = 12
ACTION_DIM = 8

ACTIONS = [
    "OBSERVE_MORE",
    "RECOMMEND",
    "PREPARE",
    "REQUEST_APPROVAL",
    "SUPERVISED_EXECUTION",
    "AUTONOMOUS_EXECUTION",
    "REDUCE_AUTONOMY",
    "DO_NOT_AUTOMATE",
]

class PolicyNetwork(nn.Module):
    def __init__(self, context_dim: int = CONTEXT_DIM, action_dim: int = ACTION_DIM):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(context_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

class ContextualBandit:
    def __init__(
        self,
        weights_path: Optional[str] = None,
        epsilon: float = 0.15,
        lr: float = 0.001,
    ):
        self.epsilon = epsilon
        self.network = PolicyNetwork()
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        self.weights_path = weights_path
        self.version = 0
        self._reward_history: List[float] = []
        self._loss_history: List[float] = []

        if weights_path and Path(weights_path).exists():
            self._load(weights_path)

    def _extract_context(self, ctx: Dict) -> torch.Tensor:
        features = [
            float(ctx.get("frequency", 0.0)) / 25.0,
            float(ctx.get("average_duration", 0.0)) / 3600.0,
            float(ctx.get("duration_variance", 0.0)) / 3600.0,
            float(ctx.get("repetition_score", 0.0)),
            float(ctx.get("determinism_score", 0.0)),
            float(ctx.get("risk_score", 0.5)),
            float(ctx.get("decision_count", 0.0)) / 10.0,
            float(ctx.get("estimated_savings", 0.0)) / 300.0,
            float(ctx.get("implementation_effort", 0.5)),
            float(ctx.get("historical_success", 0.5)),
            float(ctx.get("user_approval_rate", 0.5)),
            float(ctx.get("workflow_similarity", 0.0)),
        ]
        return torch.tensor(features, dtype=torch.float32)

    def select_action(self, workflow_context: Dict) -> Tuple[int, str, torch.Tensor]:
        context_tensor = self._extract_context(workflow_context)
        if np.random.random() < self.epsilon:
            action_idx = int(np.random.randint(0, ACTION_DIM))
        else:
            with torch.no_grad():
                q_values = self.network(context_tensor)
                action_idx = int(q_values.argmax().item())
        return action_idx, ACTIONS[action_idx], context_tensor

    def get_recommended_action(self, workflow_context: Dict) -> Tuple[str, Dict[str, float]]:
        context_tensor = self._extract_context(workflow_context)
        with torch.no_grad():
            q_values = self.network(context_tensor)
        action_idx = int(q_values.argmax().item())
        q_dict = {ACTIONS[i]: float(q_values[i].item()) for i in range(ACTION_DIM)}
        return ACTIONS[action_idx], q_dict

    def explain_action(self, workflow_context: Dict) -> Dict:
        action, q_dict = self.get_recommended_action(workflow_context)
        context_tensor = self._extract_context(workflow_context)
        features_names = [
            "frequency", "average_duration", "duration_variance", "repetition_score",
            "determinism_score", "risk_score", "decision_count", "estimated_savings",
            "implementation_effort", "historical_success", "user_approval_rate",
            "workflow_similarity"
        ]
        
        feature_vals = context_tensor.numpy().tolist()
        top_features = sorted(zip(features_names, feature_vals), key=lambda x: x[1], reverse=True)[:3]
        
        reason = "Based on high " + ", ".join([f[0].replace('_', ' ') for f in top_features])
        
        return {
            "selected_action": action,
            "q_values": q_dict,
            "top_features": top_features,
            "reason": reason
        }

    def update(
        self,
        context_tensor: torch.Tensor,
        action_idx: int,
        reward: float,
    ) -> float:
        with torch.no_grad():
            current_q = self.network(context_tensor)

        target_q = current_q.clone()
        target_q[action_idx] = torch.tensor(reward, dtype=torch.float32)

        self.optimizer.zero_grad()
        predicted_q = self.network(context_tensor)
        loss = self.loss_fn(predicted_q, target_q.detach())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.network.parameters(), 1.0)
        self.optimizer.step()

        loss_val = float(loss.item())
        self._reward_history.append(reward)
        self._loss_history.append(loss_val)
        self.version += 1

        if self.weights_path:
            self._save(self.weights_path)

        return loss_val

    def decay_epsilon(self, factor: float = 0.995, min_epsilon: float = 0.02):
        self.epsilon = max(min_epsilon, self.epsilon * factor)

    def get_average_reward(self, last_n: int = 20) -> float:
        if not self._reward_history:
            return 0.0
        window = self._reward_history[-last_n:]
        return float(np.mean(window))

    def get_stats(self) -> Dict:
        return {
            "version": self.version,
            "epsilon": self.epsilon,
            "average_reward_last_20": self.get_average_reward(20),
            "average_reward_all": float(np.mean(self._reward_history)) if self._reward_history else 0.0,
            "total_updates": len(self._reward_history),
        }

    def _save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state": self.network.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
                "version": self.version,
                "epsilon": self.epsilon,
                "reward_history": self._reward_history[-200:],
            },
            path,
        )

    def _load(self, path: str):
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        self.network.load_state_dict(checkpoint["model_state"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state"])
        self.version = checkpoint.get("version", 0)
        self.epsilon = checkpoint.get("epsilon", self.epsilon)
        self._reward_history = checkpoint.get("reward_history", [])

_bandit_instance: Optional[ContextualBandit] = None

def get_bandit() -> ContextualBandit:
    global _bandit_instance
    if _bandit_instance is None:
        from momentum.config.settings import settings
        _bandit_instance = ContextualBandit(
            weights_path=str(settings.get_weights_path()),
            epsilon=settings.MOMENTUM_EPSILON,
            lr=settings.MOMENTUM_LEARNING_RATE,
        )
    return _bandit_instance
