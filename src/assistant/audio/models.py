from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from assistant.constants.audio import AUDIO_DEFAULT_CHANNELS, STT_SAMPLE_RATE
from assistant.core.exceptions import AudioError


@dataclass(frozen=True, slots=True)
class AudioFormat:
    sample_rate: int = STT_SAMPLE_RATE
    channels: int = AUDIO_DEFAULT_CHANNELS

    def validate(self) -> None:
        if self.sample_rate <= 0:
            raise AudioError(f"Invalid sample_rate: {self.sample_rate}")

        if self.channels < 1:
            raise AudioError(f"Invalid channels: {self.channels}")


@dataclass(frozen=True, slots=True)
class AudioData:
    samples: NDArray[np.float32]
    format: AudioFormat
