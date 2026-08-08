import platform
from datetime import datetime
from typing import List, Optional
from momentum.collectors.base import BaseCollector
from momentum.models.event import EventCreate

class BrowserCollector(BaseCollector):
    name = "browser"
    interval_seconds = 5.0

    def __init__(self):
        super().__init__()
        self._last_url: Optional[str] = None
        self._last_title: Optional[str] = None

    def _get_browser_window_title(self) -> Optional[str]:
        system = platform.system()
        if system == "Windows":
            try:
                import ctypes
                BROWSERS = ["chrome", "firefox", "edge", "brave", "opera", "safari"]
                import psutil
                for proc in psutil.process_iter(["pid", "name"]):
                    if any(b in proc.info["name"].lower() for b in BROWSERS):
                        hwnd_title = []

                        def enum_windows_callback(hwnd, _):
                            import ctypes
                            pid = ctypes.c_ulong()
                            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            if pid.value == proc.info["pid"]:
                                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                                if length > 0:
                                    buf = ctypes.create_unicode_buffer(length + 1)
                                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                                    hwnd_title.append(buf.value)
                            return True

                        ctypes.windll.user32.EnumWindows(
                            ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(enum_windows_callback),
                            0
                        )
                        if hwnd_title:
                            return hwnd_title[0]
            except Exception:
                pass
        return None

    def _extract_domain(self, title: str) -> Optional[str]:
        import re
        patterns = [
            r"(?:https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        return None

    def collect(self) -> List[EventCreate]:
        events = []
        title = self._get_browser_window_title()

        if title and title != self._last_title:
            domain = self._extract_domain(title)
            events.append(EventCreate(
                timestamp=datetime.utcnow(),
                application="browser",
                event_type="browser_navigation",
                action="navigate",
                target=domain or title[:128],
                source="browser_collector",
                metadata={"title": title[:256]},
            ))
            self._last_title = title

        return events
