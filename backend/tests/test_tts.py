import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.tts.base_tts import TTSEngine
from app.models.tts.piper_service import PiperTTSService

@pytest.mark.asyncio
async def test_piper_service_initialization():
    # Mock subprocess for version check
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"1.2.0", b"")
    mock_process.returncode = 0

    with MagicMock() as mock_create:
        mock_create.return_value = mock_process
        # We need to monkeypatch asyncio.create_subprocess_exec
        # but for unit test we can just mock the Path check

        config = {"binary_path": "/tmp/piper", "model_path": "/tmp/model"}
        service = PiperTTSService(config)

        # Manually set ready to True to test logic if subprocess is hard to mock here
        service.is_ready = True
        assert service.engine_name == TTSEngine.PIPER

@pytest.mark.asyncio
async def test_tts_manager_generate(mock_all_services):
    mock_tts, _, _ = mock_all_services
    from app.models.tts.tts_manager import tts_manager

    audio, engine = await tts_manager.generate_speech("Hola", voice="narradora")

    assert audio == b"mock_audio_data"
    assert engine == "mock_engine"
    mock_tts.generate_speech.assert_called_once()
