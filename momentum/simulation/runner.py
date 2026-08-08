import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from momentum.database.base import init_db
from momentum.database.event_store import store_events_bulk, count_events
from momentum.sessions.session_manager import session_manager
from momentum.discovery.discovery_engine import discovery_engine
from momentum.simulation.generator import create_generator
from momentum.learning.trainer import run_learning_from_history
from momentum.learning.bandit import get_bandit

logger = logging.getLogger(__name__)

def run_simulation(
    days: int = 7,
    seed: int = 42,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    def progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    progress("Initializing database...")
    init_db()

    bandit = get_bandit()
    initial_reward = bandit.get_average_reward(20)
    initial_epsilon = bandit.epsilon

    progress(f"Generating {days} days of synthetic developer activity...")
    generator = create_generator(seed=seed)
    start_date = datetime.utcnow() - timedelta(days=days)
    events = generator.generate_days(num_days=days, start_date=start_date)

    progress(f"Storing {len(events)} events...")
    stored = store_events_bulk(events)
    progress(f"Stored {stored} events successfully")

    progress("Sessionizing events into developer work sessions...")
    sessions_created = session_manager.run_sessionization(
        start_time=start_date,
        end_time=datetime.utcnow(),
    )
    total_sessions = session_manager.get_session_count()
    progress(f"Created {sessions_created} sessions ({total_sessions} total)")

    progress("Running workflow discovery pipeline...")
    workflows, opportunities = discovery_engine.run(
        start_time=start_date,
        end_time=datetime.utcnow(),
        progress_callback=progress,
    )

    progress(f"Discovered {len(workflows)} workflows, {len(opportunities)} automation opportunities")

    if opportunities:
        progress("Simulating automation executions for learning benchmark...")
        from momentum.models.automation import AutomationRecord
        from momentum.models.outcome import OutcomeRecord
        from momentum.database.base import get_db
        import json
        import random
        import time

        rng = random.Random(seed)
        sim_executions = 0

        for opp in opportunities[:3]:
            wf_data = None
            from momentum.discovery.workflow_builder import get_workflow_by_id
            wf = get_workflow_by_id(opp.workflow_id)
            if wf:
                wf_data = {
                    "frequency": wf.frequency,
                    "average_duration": wf.average_duration,
                    "duration_variance": wf.duration_variance,
                    "repetition_score": wf.repetition_score,
                    "determinism_score": wf.determinism_score,
                    "risk_score": wf.risk_score,
                    "decision_points": wf.get_decision_points(),
                    "estimated_weekly_minutes": wf.estimated_weekly_minutes,
                }

            import uuid as _uuid
            dummy_opp_id = str(_uuid.uuid4())

            auto = AutomationRecord(
                opportunity_id=dummy_opp_id,
                workflow_id=opp.workflow_id,
                name=f"sim-automation-{opp.workflow_id[:8]}",
                plan_json=json.dumps({"tools": ["classify_ci_failure", "get_github_ci", "git_log", "create_draft_message"], "trigger": {"type": "ci_build_failed"}}),
                tools_json=json.dumps(["classify_ci_failure", "get_github_ci", "git_log", "create_draft_message"]),
                permissions_json=json.dumps(["github.read", "filesystem.read", "communication.draft"]),
                confidence=opp.confidence,
                autonomy_level=3,
                status="active",
                replay_accuracy=rng.uniform(0.75, 0.95),
            )
            with get_db() as db:
                db.add(auto)
                db.flush()
                auto_id = auto.id

            for i in range(8):
                success = rng.random() < (0.75 + i * 0.02)
                time_saved = rng.uniform(180, 600) if success else 0.0

                outcome = OutcomeRecord(
                    automation_id=auto_id,
                    timestamp=datetime.utcnow() - timedelta(hours=rng.uniform(0, 24)),
                    trigger="ci_build_failed",
                    execution_time=rng.uniform(5, 25),
                    success=success,
                    failure_reason=None if success else "Tool execution timeout",
                    human_intervention=not success and rng.random() < 0.3,
                    time_saved=time_saved,
                    confidence_before=opp.confidence,
                    autonomy_before=3,
                    confidence_after=opp.confidence,
                    autonomy_after=3,
                )
                with get_db() as db:
                    db.add(outcome)

                with get_db() as db:
                    auto_record = db.query(AutomationRecord).filter(AutomationRecord.id == auto_id).first()
                    if auto_record:
                        from momentum.learning.trainer import process_outcome
                        process_outcome(outcome, auto_record, wf_data)
                        sim_executions += 1

        progress(f"Simulated {sim_executions} automation executions for learning")

    progress("Running final learning pass over all outcomes...")
    learn_result = run_learning_from_history()

    final_reward = bandit.get_average_reward(20)
    final_epsilon = bandit.epsilon
    bandit_stats = bandit.get_stats()

    total_events = count_events()

    return {
        "days_simulated": days,
        "events_generated": stored,
        "total_events": total_events,
        "sessions_created": sessions_created,
        "total_sessions": total_sessions,
        "workflows_discovered": len(workflows),
        "opportunities_found": len(opportunities),
        "workflow_names": [w.name for w in workflows[:5]],
        "top_opportunity": opportunities[0].name if opportunities else None,
        "learning": {
            "initial_average_reward": initial_reward,
            "final_average_reward": final_reward,
            "initial_epsilon": initial_epsilon,
            "final_epsilon": final_epsilon,
            "policy_updates": bandit_stats["total_updates"],
            "bandit_version": bandit_stats["version"],
        },
    }
