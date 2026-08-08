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
            progress_callback(f"Clustering {len(sessions)} sessions...")

        all_sequences, cluster_groups, embeddings, valid_indices = cluster_sessions(
            sessions,
            eps=self.eps,
            min_samples=self.min_cluster_size,
        )

        if not cluster_groups:
            logger.info("No clusters found — try more data or lower eps threshold")
            return [], []

        if progress_callback:
            progress_callback(f"Found {len(cluster_groups)} pattern clusters — building workflows...")

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
