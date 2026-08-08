import pytest
from momentum.database.base import init_db, reset_engine, get_db
from momentum.config.settings import settings
import tempfile
import os

@pytest.fixture(scope="session", autouse=True)
def tmp_db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("momentum_test")
    db_path = str(tmp / "test.db")
    settings.MOMENTUM_DB = db_path
    settings.MOMENTUM_DATA_DIR = str(tmp)
    settings.MOMENTUM_WEIGHTS_FILE = str(tmp / "test_weights.pt")
    settings.MOMENTUM_PRIVACY_CONFIG = str(tmp / "privacy.json")
    reset_engine()
    init_db()
    yield db_path
    reset_engine()
