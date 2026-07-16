from assistant.core.exceptions import AssistantError


class WakeError(AssistantError):
    pass


class WakeNotReadyError(WakeError):
    pass
