from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import quote

from gigachat.models import Function

from assistant.constants import OPEN_METEO_FORECAST_URL, OPEN_METEO_GEOCODE_URL, WEATHER_CODES
from assistant.tools.http import HttpError, get_json
from assistant.tools.specs import make_function, string_param


@dataclass(frozen=True, slots=True)
class _GeoLocation:
    name: str
    latitude: float
    longitude: float


class WeatherTool:
    name: ClassVar[str] = "get_weather"

    def __init__(self, *, default_city: str) -> None:
        self._default_city = default_city

    @property
    def specification(self) -> Function:
        return make_function(
            name=self.name,
            description="Возвращает текущую погоду в указанном городе.",
            properties={
                "city": string_param("Название города на русском или английском"),
            },
            examples=[
                ("Какая погода в Москве", {"city": "Москва"}),
                ("Погода сейчас", {"city": self._default_city}),
            ],
            return_parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "temperature_c": {"type": "number"},
                    "condition": {"type": "string"},
                    "wind_kmh": {"type": "number"},
                    "error": {"type": "string"},
                },
            },
        )

    def execute(self, arguments: Mapping[str, object]) -> dict[str, object]:
        city = str(arguments.get("city") or self._default_city).strip()
        if not city:
            return {"error": "Не указан город"}

        try:
            location = _geocode(city)
            if location is None:
                return {"error": f"Город не найден: {city}"}

            forecast = get_json(
                f"{OPEN_METEO_FORECAST_URL}?latitude={location.latitude}"
                f"&longitude={location.longitude}"
                f"&current=temperature_2m,weather_code,wind_speed_10m"
                f"&timezone=auto"
            )
        except HttpError as error:
            return {"error": str(error)}

        current = forecast.get("current")
        if not isinstance(current, dict):
            return {"error": "Не удалось получить текущую погоду"}

        code_raw = current.get("weather_code", -1)
        code = int(code_raw) if isinstance(code_raw, (int, float)) else -1
        return {
            "city": location.name,
            "temperature_c": current.get("temperature_2m"),
            "condition": WEATHER_CODES.get(code, "неизвестные условия"),
            "wind_kmh": current.get("wind_speed_10m"),
        }


def _geocode(city: str) -> _GeoLocation | None:
    data = get_json(f"{OPEN_METEO_GEOCODE_URL}?name={quote(city)}&count=1&language=ru&format=json")
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None

    first = results[0]
    if not isinstance(first, dict):
        return None

    latitude = first.get("latitude")
    longitude = first.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return None

    name = first.get("name", city)
    return _GeoLocation(
        name=str(name) if name is not None else city,
        latitude=float(latitude),
        longitude=float(longitude),
    )
