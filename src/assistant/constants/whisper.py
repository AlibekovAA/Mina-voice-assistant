from enum import StrEnum
from typing import Final


class WhisperDevice(StrEnum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


class WhisperComputeType(StrEnum):
    AUTO = "auto"
    FLOAT16 = "float16"
    INT8 = "int8"


WHISPER_DEFAULT_MODEL: Final[str] = "small"
WHISPER_DEFAULT_LANGUAGE: Final[str] = "ru"
WHISPER_DEFAULT_DEVICE: Final[WhisperDevice] = WhisperDevice.AUTO
WHISPER_DEFAULT_COMPUTE_TYPE: Final[WhisperComputeType] = WhisperComputeType.AUTO
WHISPER_DEFAULT_BEAM_SIZE: Final[int] = 8
WHISPER_DEFAULT_VAD_FILTER: Final[bool] = True
WHISPER_DEFAULT_TEMPERATURE: Final[float] = 0.0
WHISPER_DEFAULT_NO_SPEECH: Final[float] = 0.5
WHISPER_DEFAULT_CPU_THREADS: Final[int] = 0
WHISPER_COMPRESSION_RATIO_THRESHOLD: Final[float] = 2.4
WHISPER_LOG_PROB_THRESHOLD: Final[float] = -0.8
WHISPER_CUDA_COMPUTE_TYPE: Final[WhisperComputeType] = WhisperComputeType.FLOAT16
WHISPER_CPU_COMPUTE_TYPE: Final[WhisperComputeType] = WhisperComputeType.INT8

__all__ = (
    "WHISPER_COMPRESSION_RATIO_THRESHOLD",
    "WHISPER_CPU_COMPUTE_TYPE",
    "WHISPER_CUDA_COMPUTE_TYPE",
    "WHISPER_DEFAULT_BEAM_SIZE",
    "WHISPER_DEFAULT_COMPUTE_TYPE",
    "WHISPER_DEFAULT_CPU_THREADS",
    "WHISPER_DEFAULT_DEVICE",
    "WHISPER_DEFAULT_LANGUAGE",
    "WHISPER_DEFAULT_MODEL",
    "WHISPER_DEFAULT_NO_SPEECH",
    "WHISPER_DEFAULT_TEMPERATURE",
    "WHISPER_DEFAULT_VAD_FILTER",
    "WHISPER_LOG_PROB_THRESHOLD",
    "WhisperComputeType",
    "WhisperDevice",
)
