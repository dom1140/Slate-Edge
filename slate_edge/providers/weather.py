from __future__ import annotations

from datetime import datetime, timezone
import requests
from slate_edge.domain import Game, Weather


MLB_VENUES = {
    "Angel Stadium": (33.8003, -117.8827), "Busch Stadium": (38.6226, -90.1928),
    "Chase Field": (33.4453, -112.0667), "Citi Field": (40.7571, -73.8458),
    "Citizens Bank Park": (39.9061, -75.1665), "Comerica Park": (42.3390, -83.0485),
    "Coors Field": (39.7559, -104.9942), "Dodger Stadium": (34.0739, -118.2400),
    "Fenway Park": (42.3467, -71.0972), "Globe Life Field": (32.7473, -97.0847),
    "Great American Ball Park": (39.0979, -84.5082), "Kauffman Stadium": (39.0517, -94.4803),
    "Nationals Park": (38.8730, -77.0074), "Oracle Park": (37.7786, -122.3893),
    "Oriole Park at Camden Yards": (39.2840, -76.6217), "Petco Park": (32.7076, -117.1570),
    "PNC Park": (40.4469, -80.0057), "Progressive Field": (41.4962, -81.6852),
    "Rate Field": (41.8300, -87.6338), "Rogers Centre": (43.6414, -79.3894),
    "Target Field": (44.9817, -93.2776), "T-Mobile Park": (47.5914, -122.3325),
    "Truist Park": (33.8908, -84.4678), "Wrigley Field": (41.9484, -87.6553),
    "Yankee Stadium": (40.8296, -73.9262),
}


class OpenMeteoProvider:
    def enrich(self, games: list[Game]) -> list[Game]:
        for game in games:
            coords = MLB_VENUES.get(game.venue)
            if not coords:
                continue
            try:
                params = {"latitude": coords[0], "longitude": coords[1], "hourly": "temperature_2m,precipitation_probability,wind_speed_10m", "temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "timezone": "UTC", "forecast_days": 3}
                data = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10).json()["hourly"]
                target = game.start_time.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
                idx = min(range(len(data["time"])), key=lambda i: abs(datetime.fromisoformat(data["time"][i]).replace(tzinfo=timezone.utc).timestamp() - game.start_time.timestamp()))
                game.weather = Weather(data["temperature_2m"][idx], data["wind_speed_10m"][idx], data["precipitation_probability"][idx], "Forecast", datetime.now(timezone.utc))
            except (requests.RequestException, KeyError, ValueError):
                pass
        return games

