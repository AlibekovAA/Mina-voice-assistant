import signal
import threading
import types

from assistant.audio.manager import AudioManager
from assistant.brain import AssistantBrain, GigaChatBrain
from assistant.config import load_config
from assistant.core.exceptions import AssistantError
from assistant.core.pipeline import VoicePipeline
from assistant.logger import Logger
from assistant.overlay import AvatarOverlay, TkAvatarOverlay
from assistant.stt import SpeechToText, WhisperStt
from assistant.tools import ToolRegistry
from assistant.tts import EdgeTts, TextToSpeech
from assistant.wake import WakeWordDetector, WhisperWakeWord

_LOG = Logger.get(__name__)


class Application:
    def __init__(self) -> None:
        Logger.configure()

        self._config = load_config()
        self._stop_event = threading.Event()
        self._interrupt_count = 0
        self._audio = AudioManager(self._config.audio)
        self._stt: SpeechToText = WhisperStt(self._config.stt)
        self._tts: TextToSpeech = EdgeTts(self._config.tts)
        self._wake: WakeWordDetector = WhisperWakeWord(
            self._config.wake,
            self._stt,
            stop_event=self._stop_event,
        )
        self._tools = ToolRegistry.default(
            default_city=self._config.tools.default_city,
            default_timezone=self._config.tools.default_timezone,
        )
        self._brain: AssistantBrain = GigaChatBrain(self._config.gigachat, self._tools)
        self._overlay: AvatarOverlay = TkAvatarOverlay()
        self._pipeline = VoicePipeline(
            audio=self._audio,
            stt=self._stt,
            tts=self._tts,
            wake=self._wake,
            brain=self._brain,
            overlay=self._overlay,
            wake_config=self._config.wake,
            utterance_config=self._config.utterance,
            stt_config=self._config.stt,
        )

    def run(self) -> None:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_signal)
        pipeline_thread: threading.Thread | None = None

        try:
            self._initialize()
            pipeline_thread = threading.Thread(
                target=self._run_pipeline,
                name="voice-pipeline",
                daemon=False,
            )
            pipeline_thread.start()
            self._overlay.run()
        except AssistantError:
            _LOG.exception("Application terminated due to an error")
            raise
        except KeyboardInterrupt:
            self._stop_event.set()
            _LOG.warning("Application interrupted")
        finally:
            signal.signal(signal.SIGINT, previous_handler)
            self._stop_event.set()
            self._overlay.shutdown()
            if pipeline_thread is not None:
                pipeline_thread.join(timeout=10.0)
                if pipeline_thread.is_alive():
                    _LOG.warning("Voice pipeline thread is still alive")
            self._shutdown()

    def _handle_signal(self, _signum: int, _frame: types.FrameType | None) -> None:
        self._interrupt_count += 1
        self._stop_event.set()
        self._overlay.shutdown()

        if self._interrupt_count == 1:
            _LOG.warning("Stop requested")
            raise KeyboardInterrupt

        _LOG.error("Force exit")
        raise SystemExit(130)

    def _initialize(self) -> None:
        _LOG.info("Initializing application")
        self._audio.initialize()
        self._stt.initialize()
        self._tts.initialize()
        self._wake.initialize()
        self._brain.initialize()
        self._overlay.initialize()

    def _run_pipeline(self) -> None:
        if not self._overlay.wait_until_ready():
            _LOG.error("Avatar overlay failed to start")
            self._stop_event.set()
            self._overlay.shutdown()
            return

        try:
            _LOG.info("%s v%s started", self._config.app_name, self._config.app_version)
            _LOG.info(
                "STT ready (model=%s, language=%s)",
                self._config.stt.model,
                self._config.stt.language,
            )
            self._pipeline.run(self._stop_event)
        finally:
            self._overlay.shutdown()

    def _shutdown(self) -> None:
        self._stop_event.set()
        self._audio.shutdown()
        self._wake.shutdown()
        self._brain.shutdown()
        self._tts.shutdown()
        self._stt.shutdown()
        _LOG.info("Application stopped")
