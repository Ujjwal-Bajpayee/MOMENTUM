import psutil
import platform
from datetime import datetime
from typing import List, Optional
from momentum.collectors.base import BaseCollector
from momentum.models.event import EventCreate

class ProcessCollector(BaseCollector):
    name = "process"
    interval_seconds = 5.0

    def __init__(self):
        super().__init__()
        self._prev_pids: set = set()
        self._prev_foreground: Optional[str] = None

    def _get_foreground_app(self) -> Optional[str]:
        system = platform.system()
        if system == "Windows":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                proc = psutil.Process(pid.value)
                return proc.name()
            except Exception:
                return None
        elif system == "Darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'],
                    capture_output=True, text=True, timeout=2
                )
                return result.stdout.strip() or None
            except Exception:
                return None
        return None

    def _get_running_procs(self) -> set:
        try:
            return {p.pid for p in psutil.process_iter(['pid'])}
        except Exception:
            return set()

    def collect(self) -> List[EventCreate]:
        events = []
        now = datetime.utcnow()

        current_pids = self._get_running_procs()
        opened = current_pids - self._prev_pids
        closed = self._prev_pids - current_pids

        for pid in list(opened)[:5]:
            try:
                proc = psutil.Process(pid)
                name = proc.name()
                events.append(EventCreate(
                    timestamp=now,
                    application=name,
                    event_type="application_open",
                    action="open",
                    source="process_collector",
                    metadata={"pid": pid},
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self._prev_pids = current_pids

        foreground = self._get_foreground_app()
        if foreground and foreground != self._prev_foreground:
            events.append(EventCreate(
                timestamp=now,
                application=foreground,
                event_type="window_change",
                action="focus",
                source="process_collector",
            ))
            self._prev_foreground = foreground

        idle_seconds = self._get_idle_seconds()
        if idle_seconds and idle_seconds > 120:
            events.append(EventCreate(
                timestamp=now,
                application="system",
                event_type="idle",
                duration=idle_seconds,
                source="process_collector",
            ))

        return events

    def _get_idle_seconds(self) -> Optional[float]:
        try:
            system = platform.system()
            if system == "Windows":
                import ctypes
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
                lii = LASTINPUTINFO()
                lii.cbSize = ctypes.sizeof(lii)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return millis / 1000.0
        except Exception:
            pass
        return None
