from __future__ import annotations

import sounddevice as sd

from assistant.audio.exceptions import AudioRecordingError
from assistant.audio.models import AudioData


class AudioRecorder:
    def record(
        self,
        duration: float,
        sample_rate: int,
        channels: int = 1,
        device: int | None = None,
    ) -> AudioData:
        try:
            samples = sd.rec(
                frames=int(duration * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                device=device,
                dtype="float32",
            )

            sd.wait()

        except sd.PortAudioError as error:
            raise AudioRecordingError("Failed to record audio.") from error

        return AudioData(
            samples=samples,
            sample_rate=sample_rate,
        )
