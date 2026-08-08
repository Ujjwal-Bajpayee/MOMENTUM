import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

DEFAULT_EXCLUDED_APPS = [
    "1password",
    "lastpass",
    "keepass",
    "bitwarden",
    "dashlane",
    "keychain",
    "banking",
    "paypal",
    "wallet",
    "signal",
    "whatsapp",
    "telegram",
    "messages",
    "credential",
    "vault",
    "passkey",
]

DEFAULT_EXCLUDED_DOMAINS = [
    "bank",
    "paypal",
    "crypto",
    "wallet",
    "password",
    "login",
    "auth",
    "oauth",
    "saml",
    "sso",
]

SENSITIVE_PATTERNS = [
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "credential",
    "auth",
    "bearer",
    "basic ",
]

@dataclass
class PrivacyConfig:
    excluded_applications: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_APPS))
    excluded_domains: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_DOMAINS))
    collect_window_titles: bool = True
    collect_terminal_commands: bool = True
    collect_file_paths: bool = True
    collect_browser_urls: bool = True
    collect_git_commands: bool = True
    observation_paused: bool = False
    redact_sensitive_patterns: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "PrivacyConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

def load_privacy_config(config_path: str) -> PrivacyConfig:
    p = Path(config_path)
    if p.exists():
        with open(p) as f:
            data = json.load(f)
        return PrivacyConfig.from_dict(data)
    return PrivacyConfig()

def save_privacy_config(config: PrivacyConfig, config_path: str):
    p = Path(config_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(config.to_dict(), f, indent=2)
