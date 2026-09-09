
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app
from services.config import Settings

REPO = Path(__file__).resolve().parent.parent


def build_client(**overrides) -> TestClient:
    """App on the MOCK provider regardless of any local .env."""
    settings = Settings(
        provider="mock",
        recordings_dir=REPO / "recordings",
        **overrides,
    )
    return TestClient(create_app(settings))


@pytest.fixture
def client() -> TestClient:
    return build_client()