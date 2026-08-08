import torch
import numpy as np
from typing import Dict, List, Tuple
from momentum.learning.bandit import get_bandit, ACTIONS, ACTION_DIM

def simulate_environment(num_steps: int = 1000) -> Tuple[Dict, Dict, Dict]:
    bandit = get_bandit()
                         
    orig_epsilon = bandit.epsilon
    bandit.epsilon = 0.1                
    
    policies = ["contextual_bandit", "always_recommend", "fixed_threshold"]
    metrics = {p: {"rewards": [], "recommend_count": 0, "success_count": 0, "unsafe_count": 0} for p in policies}
    
    for _ in range(num_steps):
                                    
        ctx = {
            "frequency": np.random.uniform(0, 50),
            "average_duration": np.random.uniform(10, 3600),
            "duration_variance": np.random.uniform(0, 1000),
            "repetition_score": np.random.uniform(0, 1),
            "determinism_score": np.random.uniform(0, 1),
            "risk_score": np.random.uniform(0, 1),
            "decision_count": np.random.randint(0, 20),
            "estimated_savings": np.random.uniform(0, 600),
            "implementation_effort": np.random.uniform(0, 1),
            "historical_success": np.random.uniform(0, 1),
            "user_approval_rate": np.random.uniform(0, 1),
            "workflow_similarity": np.random.uniform(0, 1),
        }
        
        true_success_prob = (
            0.4 * ctx["determinism_score"] +
            0.3 * (1.0 - ctx["risk_score"]) +
            0.3 * ctx["repetition_score"]
        )
        is_success = np.random.random() < true_success_prob
        is_unsafe = ctx["risk_score"] > 0.7 and is_success is False
        
        cb_action_idx, cb_action_str, cb_tensor = bandit.select_action(ctx)
        
        def evaluate_action(action_str: str) -> float:
            if action_str == "RECOMMEND":
                if is_unsafe:
                    return -10.0
                elif is_success:
                    return 5.0
                else:
                    return -1.0
            elif action_str == "DO_NOT_AUTOMATE":
                return 0.0
            else:
                return -0.1                                          
                
        cb_reward = evaluate_action(cb_action_str)
        bandit.update(cb_tensor, cb_action_idx, cb_reward)
        
        metrics["contextual_bandit"]["rewards"].append(cb_reward)
        if cb_action_str == "RECOMMEND":
            metrics["contextual_bandit"]["recommend_count"] += 1
            if is_success:
                metrics["contextual_bandit"]["success_count"] += 1
            if is_unsafe:
                metrics["contextual_bandit"]["unsafe_count"] += 1
                
        ar_reward = evaluate_action("RECOMMEND")
        metrics["always_recommend"]["rewards"].append(ar_reward)
        metrics["always_recommend"]["recommend_count"] += 1
        if is_success:
            metrics["always_recommend"]["success_count"] += 1
        if is_unsafe:
            metrics["always_recommend"]["unsafe_count"] += 1
            
        score = (ctx["frequency"]/50 + ctx["repetition_score"] + ctx["determinism_score"] + (1-ctx["risk_score"])) / 4
        ft_action = "RECOMMEND" if score > 0.6 else "DO_NOT_AUTOMATE"
        ft_reward = evaluate_action(ft_action)
        metrics["fixed_threshold"]["rewards"].append(ft_reward)
        if ft_action == "RECOMMEND":
            metrics["fixed_threshold"]["recommend_count"] += 1
            if is_success:
                metrics["fixed_threshold"]["success_count"] += 1
            if is_unsafe:
                metrics["fixed_threshold"]["unsafe_count"] += 1

    bandit.epsilon = orig_epsilon
    
    summary = {}
    for p in policies:
        recs = max(metrics[p]["recommend_count"], 1)
        summary[p] = {
            "cumulative_reward": sum(metrics[p]["rewards"]),
            "recommendation_precision": metrics[p]["success_count"] / recs,
            "success_rate": metrics[p]["success_count"] / num_steps,
            "unsafe_action_rate": metrics[p]["unsafe_count"] / num_steps
        }
        
    return summary
