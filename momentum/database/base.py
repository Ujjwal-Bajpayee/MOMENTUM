from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

class Base(DeclarativeBase):
    pass

_engine = None
_SessionFactory = None

def get_engine():
    global _engine
    if _engine is None:
        from momentum.config.settings import settings
        db_path = Path(settings.MOMENTUM_DB)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine

def reset_engine():
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None

def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory

@contextmanager
def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    from momentum.models import event as _e
    from momentum.models import session as _s
    from momentum.models import workflow as _w
    from momentum.models import opportunity as _o
    from momentum.models import automation as _a
    from momentum.models import outcome as _out
    engine = get_engine()
    Base.metadata.create_all(engine)
