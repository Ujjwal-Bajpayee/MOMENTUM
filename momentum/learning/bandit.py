import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Tuple, List, Optional, Dict
from pathlib import Path
from collections import deque
import random

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

class ReplayBuffer:
    def __init__(self, capacity: int = 1000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, context: torch.Tensor, action: int, reward: float):
        self.buffer.append((context, action, reward))
        
    def sample(self, batch_size: int) -> List[Tuple[torch.Tensor, int, float]]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def get_all(self) -> List[Tuple[torch.Tensor, int, float]]:
        return list(self.buffer)
    
    def __len__(self) -> int:
        return len(self.buffer)

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
        batch_size: int = 16,
    ):
        self.epsilon = epsilon
        self.batch_size = batch_size
        self.network = PolicyNetwork()
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        self.weights_path = weights_path
        self.version = 0
        self._reward_history: List[float] = []
        self._loss_history: List[float] = []
        self.replay_buffer = ReplayBuffer(capacity=1000)

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
        
        context_tensor.requires_grad_(True)
        q_values = self.network(context_tensor)
        action_idx = int(q_values.argmax().item())
        
        q_values[action_idx].backward()
        saliency = (context_tensor.grad * context_tensor).detach().numpy()
        
        features_names = [
            "frequency", "average_duration", "duration_variance", "repetition_score",
            "determinism_score", "risk_score", "decision_count", "estimated_savings",
            "implementation_effort", "historical_success", "user_approval_rate",
            "workflow_similarity"
        ]
        
        impacts = np.abs(saliency)
        top_indices = impacts.argsort()[-3:][::-1]
        
        top_features = []
        for idx in top_indices:
            val = float(saliency[idx])
            top_features.append((features_names[idx], val))
            
        reason = "Based on " + ", ".join([f"{'high' if v > 0 else 'low'} {n.replace('_', ' ')}" for n, v in top_features])
        
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
        self.replay_buffer.push(context_tensor, action_idx, reward)
        
        batch = self.replay_buffer.sample(self.batch_size)
        
        contexts = torch.stack([b[0] for b in batch])
        actions = torch.tensor([b[1] for b in batch], dtype=torch.long)
        rewards = torch.tensor([b[2] for b in batch], dtype=torch.float32)
        
        self.optimizer.zero_grad()
        predicted_q = self.network(contexts)
        
        target_q = predicted_q.clone().detach()
        for i, a in enumerate(actions):
            target_q[i, a] = rewards[i]
            
        loss = self.loss_fn(predicted_q, target_q)
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
