from __future__ import annotations

import sounddevice as sd

from assistant.audio.exceptions import AudioPlaybackError
from assistant.audio.models import AudioData


class AudioPlayer:
    def play(
        self,
        audio: AudioData,
        device: int | None = None,
    ) -> None:
        try:
            sd.play(
                data=audio.samples,
                samplerate=audio.sample_rate,
                device=device,
            )

            sd.wait()

        except sd.PortAudioError as error:
            raise AudioPlaybackError("Failed to play audio.") from error
