#!/usr/bin/env python3
"""
Script para probar todos los engines TTS.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.tts.tts_manager import tts_manager
from app.core.logger import logger


async def test_engine(engine_name: str):
    """Probar un engine específico"""
    logger.info(f"\n=== Testing {engine_name} ===")

    try:
        test_text = "Hola, això és una prova de text a veu."

        audio_bytes, source = await tts_manager.generate_speech(
            text=test_text,
            voice="narradora",
            language="ca",
            engine=engine_name,
            use_cache=False
        )

        logger.info(f"✓ {engine_name} OK - Generated {len(audio_bytes)} bytes")
        return True

    except Exception as e:
        logger.error(f"✗ {engine_name} FAILED: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("=== TTS Engines Test ===")

    # Inicializar manager
    await tts_manager.initialize()

    # Probar cada engine
    results = {}

    for engine in ["piper", "coqui", "bark"]:
        results[engine] = await test_engine(engine)

    # Resumen
    logger.info("\n=== Test Results ===")
    for engine, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{engine}: {status}")

    # Health check general
    health = await tts_manager.health_check()
    logger.info(f"\nHealth check: {health}")


if __name__ == "__main__":
    asyncio.run(main())
