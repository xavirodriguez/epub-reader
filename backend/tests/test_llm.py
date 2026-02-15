import pytest
from app.models.llm.text_processor import TextProcessor

@pytest.mark.asyncio
async def test_text_processor_chapter(mock_all_services):
    _, mock_ollama, _ = mock_all_services
    processor = TextProcessor()

    result = await processor.process_chapter_text("Texto de prueba")

    assert "processed_segments" in result
    assert result["metadata"]["speakers_detected"] is True
    mock_ollama.detect_speakers.assert_called_once()

@pytest.mark.asyncio
async def test_dialect_adaptation(mock_all_services):
    _, mock_ollama, _ = mock_all_services
    processor = TextProcessor()

    result = await processor.process_chapter_text("Bon dia", dialect="valencià")

    assert result["dialect"] == "valencià"
    # Verify it called translate_dialect for the segment
    assert mock_ollama.translate_dialect.called
