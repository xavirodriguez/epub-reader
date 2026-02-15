import pytest

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_tts_generate_endpoint(client):
    payload = {
        "text": "Hola mundo",
        "voice": "narradora",
        "language": "ca"
    }
    response = client.post("/api/tts/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "audio_data" in data
    assert data["source"] == "mock_engine"

def test_text_process_endpoint(client):
    payload = {
        "text": "Harry dijo: Hola.",
        "detect_speakers": True,
        "dialect": "català"
    }
    response = client.post("/api/text/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "processed_segments" in data
    assert len(data["processed_segments"]) > 0
