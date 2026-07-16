import threading
import time

from assistant.audio.manager import AudioManager
from assistant.audio.models import AudioFormat
from assistant.audio.utterance import UtteranceCapture
from assistant.brain import AssistantBrain, BrainError
from assistant.config import SttConfig, UtteranceConfig, WakeConfig
from assistant.constants import SPEECH_POST_WAKE_READ_TIMEOUT_SECONDS
from assistant.logger import Logger
from assistant.overlay import AvatarOverlay
from assistant.prompts import BRAIN_FAILURE, NOT_HEARD
from assistant.stt import SpeechToText, TranscribeOptions
from assistant.tts import TextToSpeech
from assistant.tts.exceptions import TtsError
from assistant.wake import WakeDetection, WakeWordDetector

_LOG = Logger.get(__name__)


class VoicePipeline:
    def __init__(
        self,
        *,
        audio: AudioManager,
        stt: SpeechToText,
        tts: TextToSpeech,
        wake: WakeWordDetector,
        brain: AssistantBrain,
        overlay: AvatarOverlay,
        wake_config: WakeConfig,
        utterance_config: UtteranceConfig,
        stt_config: SttConfig,
    ) -> None:
        self._audio = audio
        self._stt = stt
        self._tts = tts
        self._wake = wake
        self._brain = brain
        self._overlay = overlay
        self._wake_config = wake_config
        self._utterance = UtteranceCapture(utterance_config)
        self._command_options = TranscribeOptions(
            vad_filter=stt_config.vad_filter,
            beam_size=stt_config.beam_size,
            temperature=stt_config.temperature,
            no_speech_threshold=stt_config.no_speech_threshold,
        )

    def run(self, stop_event: threading.Event) -> None:
        audio_format = self._audio.format
        self._audio.start_capture()
        _LOG.info("Listening for wake word %r", self._wake_config.keyword)

        try:
            while not stop_event.is_set():
                chunk = self._audio.read_chunk(timeout=0.1)
                if chunk is None:
                    continue

                detection = self._wake.feed(chunk)
                if stop_event.is_set():
                    break

                if detection is None:
                    continue

                self._handle_detection(detection, audio_format, stop_event)
                if stop_event.is_set():
                    break

                self._wake.reset()
                _LOG.debug("Resumed wake listening")
        finally:
            self._overlay.hide()
            self._audio.stop_capture()
            self._wake.reset()

    def _handle_detection(
        self,
        detection: WakeDetection,
        audio_format: AudioFormat,
        stop_event: threading.Event,
    ) -> None:
        _LOG.info("Wake word detected: %r", detection.keyword)
        self._overlay.show()
        try:
            self._prune_post_wake(stop_event)
            if stop_event.is_set():
                return

            utterance = self._utterance.capture(
                audio_format=audio_format,
                read_audio=self._audio.read_chunk,
                stop_event=stop_event,
            )
            if stop_event.is_set():
                return

            if utterance is None or utterance.samples.size == 0:
                _LOG.warning("No speech captured after wake word")
                self._speak(NOT_HEARD, stop_event)
                return

            transcript = self._stt.transcribe(utterance, self._command_options)
            if stop_event.is_set():
                return

            if not transcript.text:
                _LOG.warning("Empty transcript")
                self._speak(NOT_HEARD, stop_event)
                return

            _LOG.info("Heard: %s", transcript.text)
            try:
                reply = self._brain.reply(transcript.text)
            except BrainError:
                _LOG.exception("Brain request failed")
                reply = BRAIN_FAILURE
            self._speak(reply, stop_event)
            if self._brain.shutdown_requested:
                _LOG.warning("Shutdown requested by assistant")
                stop_event.set()
        finally:
            self._overlay.hide()

    def _speak(self, text: str, stop_event: threading.Event) -> None:
        _LOG.info("Reply: %s", text)
        if stop_event.is_set():
            return

        try:
            speech = self._tts.synthesize(text)
        except TtsError as error:
            _LOG.warning("Speech synthesis failed: %s", error)
            return

        if stop_event.is_set():
            return

        self._audio.play(speech, on_level=self._overlay.set_level)

    def _prune_post_wake(self, stop_event: threading.Event) -> None:
        deadline = time.monotonic() + self._wake_config.post_wake_prune_seconds
        while not stop_event.is_set() and time.monotonic() < deadline:
            self._audio.read_chunk(timeout=SPEECH_POST_WAKE_READ_TIMEOUT_SECONDS)
