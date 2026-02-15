"""
Sistema de caché con Redis.
Incluye decoradores para cachear funciones automáticamente.
"""
import hashlib
import json
import redis.asyncio as aioredis
from typing import Optional, Any, Callable
from functools import wraps
from app.config import settings
from app.core.logger import logger


class CacheManager:
    """Gestor de caché Redis con soporte async"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.enabled = settings.TTS_CACHE_ENABLED

    async def connect(self):
        """Conectar a Redis"""
        if not self.enabled:
            logger.info("Cache disabled")
            return

        try:
            self.redis = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                encoding="utf-8",
                decode_responses=False  # Mantener bytes para audio
            )
            await self.redis.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False

    async def disconnect(self):
        """Desconectar de Redis"""
        if self.redis:
            await self.redis.close()

    def _generate_key(self, prefix: str, **kwargs) -> str:
        """
        Genera clave única basada en parámetros.

        Args:
            prefix: Prefijo de la clave (ej: "tts", "llm")
            **kwargs: Parámetros para generar hash

        Returns:
            Clave única
        """
        # Ordenar parámetros para consistencia
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        hash_value = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{hash_value}"

    async def get(self, key: str) -> Optional[bytes]:
        """
        Obtener valor del caché.

        Args:
            key: Clave

        Returns:
            Valor (bytes) o None
        """
        if not self.enabled or not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Guardar valor en caché.

        Args:
            key: Clave
            value: Valor (bytes)
            ttl: Tiempo de vida en segundos

        Returns:
            True si exitoso
        """
        if not self.enabled or not self.redis:
            return False

        try:
            ttl = ttl or settings.CACHE_TTL
            await self.redis.setex(key, ttl, value)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Eliminar clave del caché"""
        if not self.enabled or not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Eliminar claves que coincidan con patrón.

        Args:
            pattern: Patrón (ej: "tts:*")

        Returns:
            Número de claves eliminadas
        """
        if not self.enabled or not self.redis:
            return 0

        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    deleted += await self.redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"Cleared {deleted} keys matching '{pattern}'")
            return deleted
        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")
            return 0


# Singleton global
cache_manager = CacheManager()


def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorador para cachear resultados de funciones async.

    Uso:
        @cached(prefix="tts", ttl=7200)
        async def generate_audio(text: str, voice: str):
            ...

    Args:
        prefix: Prefijo para clave de caché
        ttl: Tiempo de vida personalizado
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generar clave basada en argumentos
            cache_key = cache_manager._generate_key(
                prefix=prefix,
                func=func.__name__,
                args=args,
                kwargs=kwargs
            )

            # Intentar obtener de caché
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Ejecutar función
            result = await func(*args, **kwargs)

            # Guardar en caché si es bytes
            if isinstance(result, bytes):
                await cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator
