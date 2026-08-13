import logging
from datetime import datetime
from typing import List, Optional, Tuple
from momentum.sessions.sessionizer import get_sessions
from momentum.discovery.clusterer import cluster_sessions
from momentum.discovery.workflow_builder import (
    build_workflow_from_cluster,
    save_workflows,
    get_all_workflows,
)
from momentum.discovery.opportunity_engine import (
    score_all_workflows,
    save_opportunities,
    get_all_opportunities,
)
from momentum.models.workflow import WorkflowRecord
from momentum.models.opportunity import OpportunityRecord

logger = logging.getLogger(__name__)

class DiscoveryEngine:
    def __init__(self, min_cluster_size: int = 3, eps: float = 0.35):
        self.min_cluster_size = min_cluster_size
        self.eps = eps

    def run(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        progress_callback=None,
    ) -> Tuple[List[WorkflowRecord], List[OpportunityRecord]]:
        from momentum.database.base import get_db
        from momentum.models.workflow import WorkflowRecord as WFModel
        from momentum.models.opportunity import OpportunityRecord as OppModel
        from momentum.discovery.opportunity_engine import deduplicate_workflows

        if progress_callback:
            progress_callback("Loading sessions...")

        sessions = get_sessions(start_time=start_time, end_time=end_time, limit=10000)
        if not sessions:
            logger.warning("No sessions found for discovery")
            return [], []

        if progress_callback:
            progress_callback(f"Auto-tuning DBSCAN eps for {len(sessions)} sessions...")

        eps_candidates = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
        best_eps = self.eps
        best_score = -1.0
        best_result = None

        from momentum.discovery.clusterer import compute_cluster_coherence

        for candidate_eps in eps_candidates:
            result = cluster_sessions(
                sessions,
                eps=candidate_eps,
                min_samples=self.min_cluster_size,
            )
            candidate_groups = result[1]
            candidate_embeddings = result[2]
            
            if not candidate_groups:
                score = -1.0
            else:
                coherences = []
                for group in candidate_groups:
                    coh = compute_cluster_coherence(candidate_embeddings, group)
                    coherences.append(coh)
                # Maximize average coherence * sqrt(number of clusters)
                # This balances tight clusters with finding multiple distinct workflows
                score = (sum(coherences) / len(coherences)) * (len(candidate_groups) ** 0.5)

            if score > best_score:
                best_score = score
                best_eps = candidate_eps
                best_result = result

        if best_result is None or not best_result[1]:
            logger.info("No clusters found — try more data or lower eps threshold")
            return [], []

        if progress_callback:
            progress_callback(f"Selected eps={best_eps} with score={best_score:.2f}. Found {len(best_result[1])} pattern clusters — building workflows...")

        all_sequences, cluster_groups, embeddings, valid_indices = best_result

        valid_sessions = [sessions[i] for i in valid_indices]

        raw_workflows = []
        for cluster_id, seq_indices in enumerate(cluster_groups):
            workflow = build_workflow_from_cluster(
                valid_sessions, seq_indices, embeddings, cluster_id
            )
            if workflow is not None:
                raw_workflows.append(workflow)

        workflows = deduplicate_workflows(raw_workflows)

        with get_db() as db:
            db.query(OppModel).delete()
            db.query(WFModel).delete()

        if workflows:
            save_workflows(workflows)
            logger.info(f"Saved {len(workflows)} deduplicated workflows")
        else:
            logger.info("No qualifying workflows built from clusters")
            return [], []

        if progress_callback:
            progress_callback(f"Scoring {len(workflows)} workflows for automation potential...")

        opportunities = score_all_workflows(workflows)

        if opportunities:
            save_opportunities(opportunities)
            logger.info(f"Saved {len(opportunities)} opportunities")

        return workflows, opportunities

    def get_results(self) -> Tuple[List[WorkflowRecord], List[OpportunityRecord]]:
        return get_all_workflows(), get_all_opportunities()

discovery_engine = DiscoveryEngine()
