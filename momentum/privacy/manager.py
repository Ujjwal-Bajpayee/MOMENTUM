from momentum.privacy.config import PrivacyConfig, load_privacy_config, save_privacy_config
from momentum.privacy.filter import PrivacyFilter
from momentum.config.settings import settings
from typing import Optional


class PrivacyManager:
    def __init__(self):
        self._config: Optional[PrivacyConfig] = None
        self._filter: Optional[PrivacyFilter] = None

    def _load(self) -> PrivacyConfig:
        if self._config is None:
            self._config = load_privacy_config(settings.MOMENTUM_PRIVACY_CONFIG)
        return self._config

    def get_config(self) -> PrivacyConfig:
        return self._load()

    def get_filter(self) -> PrivacyFilter:
        if self._filter is None:
            self._filter = PrivacyFilter(self._load())
        return self._filter

    def _save(self):
        save_privacy_config(self._config, settings.MOMENTUM_PRIVACY_CONFIG)
        self._filter = PrivacyFilter(self._config)

    def pause(self):
        config = self._load()
        config.observation_paused = True
        self._save()

    def resume(self):
        config = self._load()
        config.observation_paused = False
        self._save()

    def exclude_application(self, app_name: str):
        config = self._load()
        if app_name not in config.excluded_applications:
            config.excluded_applications.append(app_name)
            self._save()

    def include_application(self, app_name: str):
        config = self._load()
        if app_name in config.excluded_applications:
            config.excluded_applications.remove(app_name)
            self._save()

    def is_paused(self) -> bool:
        return self._load().observation_paused

    def reload(self):
        self._config = None
        self._filter = None


privacy_manager = PrivacyManager()
