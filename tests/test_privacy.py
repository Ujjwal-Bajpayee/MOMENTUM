from momentum.privacy.config import PrivacyConfig
from momentum.privacy.filter import PrivacyFilter

def test_default_config():
    config = PrivacyConfig()
    assert not config.observation_paused
    assert config.collect_terminal_commands
    assert len(config.excluded_applications) > 0

def test_application_exclusion():
    config = PrivacyConfig()
    pfilter = PrivacyFilter(config)
    assert not pfilter.is_application_allowed("1password")
    assert not pfilter.is_application_allowed("LastPass")
    assert pfilter.is_application_allowed("vscode")
    assert pfilter.is_application_allowed("terminal")

def test_redact_api_key():
    config = PrivacyConfig()
    pfilter = PrivacyFilter(config)
    text = "running with OPENAI_API_KEY=sk-abcdef123456789012345678901234567890"
    result = pfilter.redact_sensitive(text)
    assert "sk-" not in result or "[REDACTED]" in result

def test_redact_github_token():
    config = PrivacyConfig()
    pfilter = PrivacyFilter(config)
    text = "export GH_TOKEN=ghp_" + "a" * 36
    result = pfilter.redact_sensitive(text)
    assert "ghp_" not in result

def test_paused_filter_blocks_collection():
    config = PrivacyConfig()
    config.observation_paused = True
    pfilter = PrivacyFilter(config)
    assert not pfilter.should_collect()

def test_metadata_filtering():
    config = PrivacyConfig()
    pfilter = PrivacyFilter(config)
    metadata = {
        "title": "My Page",
        "password": "super_secret",
        "repo": "my-repo",
        "token": "abc123",
    }
    filtered = pfilter.filter_metadata(metadata)
    assert "password" not in filtered
    assert "token" not in filtered
    assert filtered.get("title") == "My Page"
    assert filtered.get("repo") == "my-repo"
