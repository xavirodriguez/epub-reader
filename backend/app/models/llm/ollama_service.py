"""
Servicio de LLM local usando Ollama.
Para detección de speakers y procesamiento de texto.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List
import httpx
from ollama import AsyncClient

from app.core.logger import logger
from app.core.exceptions import LLMException
from app.config import settings


class OllamaService:
    """
    Servicio para comunicación con Ollama.
    Maneja detección de speakers y adaptación dialectal.
    """

    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.client: Optional[AsyncClient] = None
        self.is_ready = False

    async def initialize(self):
        """Inicializar cliente y verificar modelo"""
        try:
            self.client = AsyncClient(host=self.host, timeout=self.timeout)

            # Verificar que el modelo existe
            models = await self.client.list()
            available_models = [m['name'] for m in models.get('models', [])]

            # Ollama models sometimes have :latest tag or similar
            if self.model not in available_models and f"{self.model}:latest" not in available_models:
                logger.warning(
                    f"Model {self.model} not found. "
                    f"Available: {available_models}. "
                    "Attempting to pull..."
                )
                await self.pull_model(self.model)

            self.is_ready = True
            logger.info(f"Ollama service ready with model: {self.model}")

        except Exception as e:
            logger.error(f"Ollama initialization failed: {e}")
            self.is_ready = False

    async def pull_model(self, model_name: str):
        """Descargar modelo desde Ollama registry"""
        logger.info(f"Pulling Ollama model: {model_name}")

        try:
            async for progress in await self.client.pull(model_name, stream=True):
                # Log progreso
                if progress.get('status'):
                    logger.info(f"Pull progress: {progress['status']}")

            logger.info(f"Model {model_name} pulled successfully")

        except Exception as e:
            raise LLMException(f"Failed to pull model {model_name}: {e}")

    async def detect_speakers(self, text: str) -> Dict[str, Any]:
        """
        Analizar texto y detectar narraciones vs diálogos.

        Args:
            text: Texto del capítulo o fragmento

        Returns:
            Dict con segmentos clasificados:
            {
                "segments": [
                    {"speaker": "Narradora", "text": "..."},
                    {"speaker": "Harry", "text": "..."}
                ]
            }
        """
        if not self.is_ready or not self.client:
            raise LLMException("Ollama service not initialized")

        prompt = f"""Analitza aquest text en català i separa'l en segments.
Identifica:
- Text narratiu (descripció, context) → speaker: "Narradora"
- Diàlegs de Harry Potter → speaker: "Harry"
- Altres diàlegs → speaker: "Personatge" (indica quin)

Text:
{text}

Respon NOMÉS con JSON vàlid en aquest format exacte:
{{
  "segments": [
    {{"speaker": "Narradora", "text": "text del segment"}},
    {{"speaker": "Harry", "text": "text del segment"}}
  ]
}}

NO afegeixis explicacions ni text addicional."""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={
                    "temperature": 0.3,  # Baja para consistencia
                    "top_p": 0.9
                }
            )

            # Parse respuesta
            result_text = response.get('response', '{}')
            result = json.loads(result_text)

            # Validar estructura
            if 'segments' not in result:
                raise ValueError("Invalid response format")

            logger.info(f"Detected {len(result['segments'])} segments")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Ollama: {e}")
            # Fallback: todo el texto como narración
            return {
                "segments": [{"speaker": "Narradora", "text": text}]
            }
        except Exception as e:
            logger.error(f"Speaker detection error: {e}")
            raise LLMException(f"Detection failed: {str(e)}")

    async def translate_dialect(
        self,
        text: str,
        target_dialect: str = "valencià"
    ) -> str:
        """
        Adaptar texto entre dialectos catalanes.

        Args:
            text: Texto en catalán estándar
            target_dialect: Dialecto objetivo (valencià, balear, etc)

        Returns:
            Texto adaptado
        """
        if not self.is_ready or not self.client:
            raise LLMException("Ollama service not initialized")

        if target_dialect.lower() not in ["valencià", "valenciano", "valencian"]:
            # Solo soportamos valenciano por ahora
            logger.warning(f"Dialect {target_dialect} not supported, returning original")
            return text

        prompt = f"""Adapta aquest text del català estàndard al valencià.
Mantingues exactament el mateix significat i estructura.

Canvis principals:
- Articles: "el/la" → "lo/la" en alguns casos
- Pronoms: "aquest/aqueix" segons context
- Vocabulari valencià específic

Text original:
{text}

Text adaptat al valencià:"""

        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.2,  # Muy conservador
                }
            )

            adapted_text = response.get('response', '').strip()

            if not adapted_text:
                logger.warning("Empty dialect adaptation, returning original")
                return text

            return adapted_text

        except Exception as e:
            logger.error(f"Dialect translation error: {e}")
            # Fallback: devolver original
            return text

    async def chunk_text_intelligently(
        self,
        text: str,
        max_chunk_size: int = 1000
    ) -> List[str]:
        """
        Dividir texto en chunks inteligentes respetando estructura.

        Args:
            text: Texto completo
            max_chunk_size: Tamaño máximo por chunk

        Returns:
            Lista de chunks
        """
        # Implementación simple primero
        # TODO: Mejorar con LLM para detectar límites naturales

        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def health_check(self) -> bool:
        """Verificar que Ollama responde"""
        if not self.is_ready or not self.client:
            return False

        try:
            response = await self.client.generate(
                model=self.model,
                prompt="Respon només amb: OK",
                options={"num_predict": 5}
            )
            return True
        except Exception:
            return False


# Singleton
ollama_service = OllamaService()
