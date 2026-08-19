import importlib
import sys


def reload_shared_config():
    """Reload shared config so env-dependent defaults are recalculated."""
    if "shared.config" in sys.modules:
        return importlib.reload(sys.modules["shared.config"])

    import shared.config  # pylint: disable=import-outside-toplevel

    return shared.config


def test_jwt_secret_prefers_jwt_secret(monkeypatch, tmp_path):
    # Unit tests must use only the values set below, not the developer's
    # gitignored .env file from the repository root.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JWT_SECRET", "primary-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "legacy-secret")

    config_module = reload_shared_config()

    assert config_module.settings.JWT_SECRET == "primary-secret"


def test_jwt_secret_falls_back_to_legacy_key(monkeypatch, tmp_path):
    # Keep the local deployment secrets out of this fallback test.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "legacy-secret")

    config_module = reload_shared_config()

    assert config_module.settings.JWT_SECRET == "legacy-secret"
