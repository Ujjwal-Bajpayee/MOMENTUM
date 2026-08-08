import re
from typing import Optional
from momentum.privacy.config import PrivacyConfig, SENSITIVE_PATTERNS


_REDACT_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|bearer|credential)[^\s]*\s*[=:]\s*\S+"),
    re.compile(r"(?i)Authorization:\s*\S+\s*\S+"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"github_pat_[a-zA-Z0-9_]{82}"),
    re.compile(r"(?i)-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----[\s\S]+?-----END\s+(RSA\s+)?PRIVATE\s+KEY-----"),
]


class PrivacyFilter:
    def __init__(self, config: PrivacyConfig):
        self.config = config

    def is_application_allowed(self, application: str) -> bool:
        app_lower = application.lower()
        for excluded in self.config.excluded_applications:
            if excluded.lower() in app_lower:
                return False
        return True

    def is_domain_allowed(self, url: Optional[str]) -> bool:
        if not url:
            return True
        url_lower = url.lower()
        for excluded in self.config.excluded_domains:
            if excluded.lower() in url_lower:
                return False
        return True

    def filter_target(self, target: Optional[str], event_type: str) -> Optional[str]:
        if not target:
            return target
        if event_type == "browser_navigation" and not self.config.collect_browser_urls:
            return "[redacted-url]"
        if event_type in ("terminal_command", "git_command") and not self.config.collect_terminal_commands:
            return "[redacted-command]"
        if not self.is_domain_allowed(target):
            return "[redacted-sensitive-domain]"
        return self.redact_sensitive(target)

    def filter_action(self, action: Optional[str]) -> Optional[str]:
        if not action:
            return action
        return self.redact_sensitive(action)

    def redact_sensitive(self, text: str) -> str:
        if not self.config.redact_sensitive_patterns:
            return text
        result = text
        for pattern in _REDACT_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    def should_collect(self) -> bool:
        return not self.config.observation_paused

    def filter_metadata(self, metadata: Optional[dict]) -> Optional[dict]:
        if not metadata:
            return metadata
        cleaned = {}
        for k, v in metadata.items():
            k_lower = k.lower()
            if any(p in k_lower for p in SENSITIVE_PATTERNS):
                continue
            if isinstance(v, str):
                cleaned[k] = self.redact_sensitive(v)
            else:
                cleaned[k] = v
        return cleaned
