#!/usr/bin/env python3
"""
Script para descargar todos los modelos necesarios.
"""
import asyncio
import sys
from pathlib import Path

# Añadir parent al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logger import logger
from app.models.llm.ollama_service import ollama_service
from TTS.api import TTS


async def download_ollama_models():
    """Descargar modelos de Ollama"""
    logger.info("Downloading Ollama models...")

    try:
        await ollama_service.initialize()

        models_to_pull = ["llama3.2", "mistral"]

        for model in models_to_pull:
            try:
                logger.info(f"Pulling {model}...")
                await ollama_service.pull_model(model)
            except Exception as e:
                logger.error(f"Failed to pull {model}: {e}")

        logger.info("✓ Ollama models ready")

    except Exception as e:
        logger.error(f"Ollama setup failed: {e}")


def download_coqui_models():
    """Descargar modelos de Coqui TTS"""
    logger.info("Downloading Coqui TTS models...")

    try:
        # Esto descargará el modelo automáticamente
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        logger.info("✓ Coqui models ready")

    except Exception as e:
        logger.error(f"Coqui download failed: {e}")


async def main():
    """Main function"""
    logger.info("=== Model Download Script ===")

    # Create voices directory if not exists
    voices_dir = Path(__file__).parent.parent / "voices"
    voices_dir.mkdir(exist_ok=True)

    # Ollama
    await download_ollama_models()

    # Coqui
    download_coqui_models()

    # Create placeholder for reference audios if they don't exist
    for voice in ["narradora", "harry"]:
        wav_file = voices_dir / f"{voice}.wav"
        if not wav_file.exists():
            logger.info(f"Creating placeholder for {voice}.wav (User should replace this for cloning)")
            # Create a 1-second empty wav file as placeholder
            import numpy as np
            from app.utils.audio import create_wav_file
            silence = np.zeros(24000, dtype=np.int16)
            create_wav_file(silence, wav_file, sample_rate=24000)

    logger.info("=== Download Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
