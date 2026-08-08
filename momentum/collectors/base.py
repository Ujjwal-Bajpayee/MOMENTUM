from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from momentum.models.event import EventCreate

class BaseCollector(ABC):
    name: str = "base"
    interval_seconds: float = 5.0

    def __init__(self):
        self._running = False
        self._last_collected: Optional[datetime] = None

    @abstractmethod
    def collect(self) -> List[EventCreate]:
        pass

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return self._running
