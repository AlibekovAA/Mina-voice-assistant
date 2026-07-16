from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WakeDetection:
    keyword: str
