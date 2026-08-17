from __future__ import annotations

from datetime import date, datetime, timezone
import requests

from slate_edge.domain import Game, OddsQuote
from slate_edge.providers.base import OddsProvider


class TheOddsAPIProvider(OddsProvider):
    BASE = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str, regions: str = "us", timeout: int = 12):
        self.api_key, self.regions, self.timeout = api_key, regions, timeout

    def quotes(self, slate_date: date, games: list[Game]) -> list[OddsQuote]:
        params = {"apiKey": self.api_key, "regions": self.regions, "markets": "h2h", "oddsFormat": "american", "dateFormat": "iso"}
        response = requests.get(f"{self.BASE}/sports/baseball_mlb/odds", params=params, timeout=self.timeout)
        response.raise_for_status()
        fetched = datetime.now(timezone.utc)
        lookup = {(g.away.name.lower(), g.home.name.lower()): g.id for g in games}
        quotes: list[OddsQuote] = []
        for event in response.json():
            game_id = lookup.get((event.get("away_team", "").lower(), event.get("home_team", "").lower()))
            if not game_id:
                continue
            for book in event.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    updated = datetime.fromisoformat(market.get("last_update", fetched.isoformat()).replace("Z", "+00:00"))
                    for outcome in market.get("outcomes", []):
                        quotes.append(OddsQuote(game_id, book.get("title", book["key"]), "moneyline", outcome["name"], int(outcome["price"]), updated))
        return quotes


class DemoOddsProvider(OddsProvider):
    """Clearly labeled deterministic quotes so a keyless deployment remains explorable."""

    def quotes(self, slate_date: date, games: list[Game]) -> list[OddsQuote]:
        now = datetime.now(timezone.utc)
        quotes = []
        for idx, game in enumerate(games):
            home = [-135, -112, 105, -155, 120][idx % 5]
            away = 115 if home < 0 else -125
            quotes += [OddsQuote(game.id, "Demo market", "moneyline", game.home.name, home, now),
                       OddsQuote(game.id, "Demo market", "moneyline", game.away.name, away, now)]
        return quotes

