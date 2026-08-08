import threading
import time
import logging
from typing import List, Type
from datetime import datetime
from momentum.collectors.base import BaseCollector
from momentum.collectors.process_collector import ProcessCollector
from momentum.collectors.git_collector import GitCollector
from momentum.collectors.terminal_collector import TerminalCollector
from momentum.collectors.browser_collector import BrowserCollector
from momentum.collectors.docker_collector import DockerCollector
from momentum.database.event_store import store_events_bulk
from momentum.privacy.manager import privacy_manager
from momentum.models.event import EventCreate

logger = logging.getLogger(__name__)

class CollectorManager:
    def __init__(self):
        self._collectors: List[BaseCollector] = [
            ProcessCollector(),
            GitCollector(),
            TerminalCollector(),
            BrowserCollector(),
            DockerCollector(),
        ]
        self._threads: List[threading.Thread] = []
        self._running = False
        self._total_collected = 0

    def _run_collector(self, collector: BaseCollector):
        while self._running and collector.is_running():
            try:
                pfilter = privacy_manager.get_filter()
                if not pfilter.should_collect():
                    time.sleep(collector.interval_seconds)
                    continue

                raw_events = collector.collect()
                filtered = []
                for evt in raw_events:
                    if not pfilter.is_application_allowed(evt.application):
                        continue
                    evt.target = pfilter.filter_target(evt.target, evt.event_type)
                    evt.action = pfilter.filter_action(evt.action)
                    evt.metadata = pfilter.filter_metadata(evt.metadata)
                    filtered.append(evt)

                if filtered:
                    count = store_events_bulk(filtered)
                    self._total_collected += count

            except Exception as e:
                logger.error(f"Collector {collector.name} error: {e}")

            time.sleep(collector.interval_seconds)

    def start(self):
        self._running = True
        for collector in self._collectors:
            collector.start()
            t = threading.Thread(
                target=self._run_collector,
                args=(collector,),
                daemon=True,
                name=f"collector-{collector.name}",
            )
            t.start()
            self._threads.append(t)
        logger.info(f"Started {len(self._collectors)} collectors")

    def stop(self):
        self._running = False
        for collector in self._collectors:
            collector.stop()
        logger.info("All collectors stopped")

    def get_total_collected(self) -> int:
        return self._total_collected

    def get_collector_names(self) -> List[str]:
        return [c.name for c in self._collectors]
