"""
Utilidades para procesamiento de audio.
"""
import numpy as np
import wave
from pathlib import Path
from typing import Union


def create_wav_file(
    audio_data: np.ndarray,
    output_path: Union[str, Path],
    sample_rate: int = 24000,
    channels: int = 1
):
    """
    Crear archivo WAV desde numpy array.

    Args:
        audio_data: Array numpy int16
        output_path: Ruta de salida
        sample_rate: Frecuencia de muestreo
        channels: Número de canales (1=mono)
    """
    output_path = Path(output_path)

    # Asegurar que es int16
    if audio_data.dtype != np.int16:
        audio_data = audio_data.astype(np.int16)

    # Crear WAV
    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 2 bytes = 16 bits
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())


def pcm_to_numpy(pcm_bytes: bytes) -> np.ndarray:
    """
    Convertir bytes PCM int16 a numpy array.

    Args:
        pcm_bytes: Bytes en formato PCM int16

    Returns:
        Numpy array int16
    """
    return np.frombuffer(pcm_bytes, dtype=np.int16)


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """
    Normalizar nivel de audio.

    Args:
        audio: Array de audio
        target_db: Nivel objetivo en dB

        Returns:
        Audio normalizado
    """
    # Calcular RMS actual
    rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

    if rms == 0:
        return audio

    # Convertir target_db a amplitud
    target_amplitude = 10 ** (target_db / 20)

    # Calcular factor de escala
    scale = target_amplitude / rms

    # Aplicar y clip
    normalized = audio.astype(np.float32) * scale
    normalized = np.clip(normalized, -32768, 32767)

    return normalized.astype(np.int16)
