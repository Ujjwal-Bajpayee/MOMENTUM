import json
import numpy as np
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from momentum.embeddings.faiss_store import FAISSStore
from momentum.models.workflow import WorkflowRecord
from momentum.database.base import get_db
from momentum.config.settings import settings


class WorkflowMemory:
    def __init__(self):
        self._store = FAISSStore(dim=128)
        self._index_path = str(settings.get_data_dir() / "workflow_index")
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self._store.load(self._index_path)
            self._loaded = True

    def index_workflow(self, workflow: WorkflowRecord):
        self._ensure_loaded()
        if not workflow.embedding_json:
            return
        embedding = np.array(json.loads(workflow.embedding_json), dtype=np.float32)
        metadata = {
            "name": workflow.name,
            "automation_score": workflow.automation_score,
            "confidence": workflow.confidence,
            "status": workflow.status,
        }
        self._store.add(embedding, workflow.id, metadata)
        self._store.save(self._index_path)

    def index_all_workflows(self, workflows: List[WorkflowRecord]):
        self._ensure_loaded()
        valid = [(w, json.loads(w.embedding_json)) for w in workflows if w.embedding_json]
        if not valid:
            return
        embeddings = np.array([e for _, e in valid], dtype=np.float32)
        ids = [w.id for w, _ in valid]
        metadata = [
            {"name": w.name, "automation_score": w.automation_score, "status": w.status}
            for w, _ in valid
        ]
        self._store.add_batch(embeddings, ids, metadata)
        self._store.save(self._index_path)

    def find_similar(
        self,
        embedding: np.ndarray,
        k: int = 5,
        exclude_id: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict]]:
        self._ensure_loaded()
        results = self._store.search(embedding, k=k + 1)
        return [
            (doc_id, score, meta)
            for doc_id, score, meta in results
            if doc_id != exclude_id
        ][:k]

    def find_similar_to_workflow(
        self, workflow: WorkflowRecord, k: int = 5
    ) -> List[Tuple[str, float, Dict]]:
        if not workflow.embedding_json:
            return []
        embedding = np.array(json.loads(workflow.embedding_json), dtype=np.float32)
        return self.find_similar(embedding, k=k, exclude_id=workflow.id)

    def size(self) -> int:
        self._ensure_loaded()
        return self._store.size()

    def reset(self):
        self._store.reset()
        self._loaded = False


workflow_memory = WorkflowMemory()
