from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MOMENTUM_DB: str = str(Path.home() / ".momentum" / "momentum.db")
    MOMENTUM_DATA_DIR: str = str(Path.home() / ".momentum")
    MOMENTUM_OBSERVATION_DAYS: int = 7
    MOMENTUM_SIMULATION_MODE: bool = False
    MOMENTUM_LLM_PROVIDER: str = "ollama"
    MOMENTUM_LLM_MODEL: str = "deepseek-r1:8b"
    MOMENTUM_EMBEDDING_MODEL: str = "tfidf"
    MOMENTUM_LOG_LEVEL: str = "INFO"
    MOMENTUM_API_HOST: str = "127.0.0.1"
    MOMENTUM_API_PORT: int = 8000
    MOMENTUM_MIN_CONFIDENCE: float = 0.65
    MOMENTUM_MIN_AUTOMATION_SCORE: float = 55.0
    MOMENTUM_EPSILON: float = 0.15
    MOMENTUM_LEARNING_RATE: float = 0.001
    MOMENTUM_REPLAY_THRESHOLD: float = 0.75
    MOMENTUM_MAX_CONSECUTIVE_FAILURES: int = 3
    MOMENTUM_WEIGHTS_FILE: str = str(Path.home() / ".momentum" / "policy_weights.pt")
    MOMENTUM_PRIVACY_CONFIG: str = str(Path.home() / ".momentum" / "privacy.json")

    def get_data_dir(self) -> Path:
        p = Path(self.MOMENTUM_DATA_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_db_path(self) -> Path:
        return Path(self.MOMENTUM_DB)

    def get_weights_path(self) -> Path:
        return Path(self.MOMENTUM_WEIGHTS_FILE)

    def get_pid_file(self) -> Path:
        return self.get_data_dir() / "daemon.pid"

    def get_state_file(self) -> Path:
        return self.get_data_dir() / "daemon_state.json"

settings = Settings()
