from assistant.core.exceptions import AssistantError


class SttError(AssistantError):
    pass


class SttNotReadyError(SttError):
    pass
