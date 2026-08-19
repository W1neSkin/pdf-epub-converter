import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import storage  # noqa: E402


def test_cloudinary_storage_uses_credentials_loaded_from_combined_url(monkeypatch):
    """CLOUDINARY_URL credentials must not be replaced with empty variables."""
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)

    url_config = SimpleNamespace(
        cloud_name="test-cloud",
        api_key="test-key",
        api_secret="test-secret",
    )

    def fake_config(**values):
        if not values:
            return url_config
        return SimpleNamespace(**values)

    monkeypatch.setattr(storage.cloudinary, "config", fake_config)

    cloudinary_storage = storage.CloudinaryStorage()

    assert cloudinary_storage.enabled is True
