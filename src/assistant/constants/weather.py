from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

WEATHER_DEFAULT_CITY: Final[str] = "Москва"
WEATHER_DEFAULT_TIMEZONE: Final[str] = "Europe/Moscow"

OPEN_METEO_GEOCODE_URL: Final[str] = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL: Final[str] = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES: Final[Mapping[int, str]] = MappingProxyType(
    {
        0: "ясно",
        1: "преимущественно ясно",
        2: "переменная облачность",
        3: "пасмурно",
        45: "туман",
        48: "изморозь",
        51: "лёгкая морось",
        53: "морось",
        55: "сильная морось",
        61: "небольшой дождь",
        63: "дождь",
        65: "сильный дождь",
        71: "небольшой снег",
        73: "снег",
        75: "сильный снег",
        80: "ливень",
        81: "сильный ливень",
        82: "очень сильный ливень",
        95: "гроза",
        96: "гроза с градом",
        99: "гроза с сильным градом",
    }
)

__all__ = (
    "OPEN_METEO_FORECAST_URL",
    "OPEN_METEO_GEOCODE_URL",
    "WEATHER_CODES",
    "WEATHER_DEFAULT_CITY",
    "WEATHER_DEFAULT_TIMEZONE",
)
