import os
import sys
import time
import signal
import logging
import threading
from pathlib import Path
from momentum.config.settings import settings
from momentum.database.base import init_db
from momentum.daemon.state import daemon_state
from momentum.collectors.collector_manager import CollectorManager
from momentum.sessions.session_manager import session_manager

logger = logging.getLogger(__name__)


class MomentumDaemon:
    def __init__(self):
        self._running = False
        self._collector_manager = CollectorManager()
        self._stop_event = threading.Event()

    def start(self):
        init_db()
        daemon_state.set_running(os.getpid())
        logger.info(f"MOMENTUM daemon starting (PID={os.getpid()})")
        self._running = True

        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._handle_signal)
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, self._handle_signal)

        self._collector_manager.start()

        sessionize_thread = threading.Thread(
            target=self._periodic_sessionize,
            daemon=True,
            name="sessionizer",
        )
        sessionize_thread.start()

        import uvicorn
        from momentum.api.main import create_app
        app = create_app()
        uvicorn.run(
            app,
            host=settings.MOMENTUM_API_HOST,
            port=settings.MOMENTUM_API_PORT,
            log_level=settings.MOMENTUM_LOG_LEVEL.lower(),
        )

    def _periodic_sessionize(self):
        while not self._stop_event.wait(timeout=300):
            try:
                session_manager.run_sessionization()
            except Exception as e:
                logger.error(f"Sessionization error: {e}")

    def _handle_signal(self, signum, frame):
        logger.info(f"Received signal {signum} — shutting down")
        self._shutdown()

    def _shutdown(self):
        self._running = False
        self._stop_event.set()
        self._collector_manager.stop()
        daemon_state.set_stopped()
        logger.info("MOMENTUM daemon stopped")
        sys.exit(0)


def run_daemon():
    logging.basicConfig(
        level=getattr(logging, settings.MOMENTUM_LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    daemon = MomentumDaemon()
    daemon.start()


if __name__ == "__main__":
    run_daemon()
