import subprocess
import platform
from datetime import datetime
from typing import List, Optional
from momentum.collectors.base import BaseCollector
from momentum.models.event import EventCreate

class DockerCollector(BaseCollector):
    name = "docker"
    interval_seconds = 15.0

    def __init__(self):
        super().__init__()
        self._last_containers: set = set()

    def _get_running_containers(self) -> List[dict]:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return []
            containers = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 4:
                    containers.append({
                        "id": parts[0],
                        "name": parts[1],
                        "status": parts[2],
                        "image": parts[3],
                    })
            return containers
        except Exception:
            return []

    def collect(self) -> List[EventCreate]:
        events = []
        now = datetime.utcnow()
        containers = self._get_running_containers()
        current_ids = {c["id"] for c in containers}

        started = current_ids - self._last_containers
        stopped = self._last_containers - current_ids

        for container in containers:
            if container["id"] in started:
                events.append(EventCreate(
                    timestamp=now,
                    application="docker",
                    event_type="docker_event",
                    action="container_start",
                    target=container["name"],
                    source="docker_collector",
                    metadata={"image": container["image"]},
                ))

        for cid in stopped:
            events.append(EventCreate(
                timestamp=now,
                application="docker",
                event_type="docker_event",
                action="container_stop",
                target=cid[:12],
                source="docker_collector",
            ))

        self._last_containers = current_ids
        return events
