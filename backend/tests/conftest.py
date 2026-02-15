import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Mock missing heavy modules BEFORE importing app
mock_tts_mod = MagicMock()
sys.modules["TTS"] = mock_tts_mod
sys.modules["TTS.api"] = mock_tts_mod
sys.modules["bark"] = MagicMock()
sys.modules["bark.generation"] = MagicMock()

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app as fastapi_app
import app.models.tts.tts_manager
import app.models.llm.ollama_service
import app.core.cache

@pytest.fixture
def client():
    return TestClient(fastapi_app)

@pytest.fixture(autouse=True)
def mock_all_services(monkeypatch):
    """Mock heavy services for all tests"""
    # Create mocks
    mock_tts = AsyncMock()
    mock_tts.initialized = True
    mock_tts.generate_speech.return_value = (b"mock_audio_data", "mock_engine")
    mock_tts.list_all_voices.return_value = {"mock_engine": {"voices": {"v1": {}}}}
    mock_tts.health_check.return_value = {"mock_engine": True}
    mock_tts.initialize.return_value = None
    mock_tts.shutdown.return_value = None

    mock_ollama = AsyncMock()
    mock_ollama.is_ready = True
    mock_ollama.detect_speakers.return_value = {
        "segments": [{"speaker": "Narradora", "text": "Test"}]
    }
    mock_ollama.translate_dialect.return_value = "Test adaptat"
    mock_ollama.chunk_text_intelligently.return_value = ["Test chunk"]
    mock_ollama.health_check.return_value = True
    mock_ollama.initialize.return_value = None

    mock_cache = AsyncMock()
    mock_cache.enabled = True
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.connect.return_value = None
    mock_cache.disconnect.return_value = None

    # Apply patches to the modules where the instances are defined
    # AND where they are imported
    for target in ["app.models.tts.tts_manager.tts_manager", "app.api.routes.tts.tts_manager", "app.api.routes.health.tts_manager", "app.workers.tasks.tts_manager"]:
        monkeypatch.setattr(target, mock_tts)

    for target in ["app.models.llm.ollama_service.ollama_service", "app.models.llm.text_processor.ollama_service", "app.api.routes.health.ollama_service"]:
        monkeypatch.setattr(target, mock_ollama)

    for target in ["app.core.cache.cache_manager", "app.api.routes.health.cache_manager"]:
        monkeypatch.setattr(target, mock_cache)

    return mock_tts, mock_ollama, mock_cache
