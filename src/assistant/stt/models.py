from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str


@dataclass(frozen=True, slots=True)
class TranscribeOptions:
    vad_filter: bool | None = None
    beam_size: int | None = None
    temperature: float | None = None
    no_speech_threshold: float | None = None
    initial_prompt: str | None = None
    hotwords: str | None = None
