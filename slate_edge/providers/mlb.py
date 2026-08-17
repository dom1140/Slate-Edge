from __future__ import annotations

from datetime import date, datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import requests

from slate_edge.domain import Game, Pitcher, Team
from slate_edge.providers.base import ScheduleProvider


class MLBStatsProvider(ScheduleProvider):
    """Public MLB Stats API adapter. No key required; availability is not guaranteed by SLA."""

    BASE = "https://statsapi.mlb.com/api/v1"

    def __init__(self, timeout: int = 12):
        self.timeout = timeout

    @staticmethod
    def _abbr(name: str) -> str:
        special = {"Arizona Diamondbacks": "ARI", "Athletics": "ATH", "Chicago White Sox": "CWS",
                   "Kansas City Royals": "KC", "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
                   "New York Mets": "NYM", "New York Yankees": "NYY", "San Diego Padres": "SD",
                   "San Francisco Giants": "SF", "Tampa Bay Rays": "TB", "Washington Nationals": "WSH"}
        return special.get(name, "".join(p[0] for p in name.split()[-2:]).upper())

    def games(self, slate_date: date) -> list[Game]:
        params = {"sportId": 1, "date": slate_date.isoformat(), "hydrate": "probablePitcher,venue,linescore"}
        response = requests.get(f"{self.BASE}/schedule", params=params, timeout=self.timeout)
        response.raise_for_status()
        result: list[Game] = []
        for date_block in response.json().get("dates", []):
            for item in date_block.get("games", []):
                teams = item["teams"]
                away_data, home_data = teams["away"], teams["home"]
                away_name, home_name = away_data["team"]["name"], home_data["team"]["name"]
                venue = item.get("venue", {})
                result.append(Game(
                    id=str(item["gamePk"]), sport="MLB",
                    start_time=datetime.fromisoformat(item["gameDate"].replace("Z", "+00:00")),
                    away=Team(away_data["team"]["id"], away_name, self._abbr(away_name)),
                    home=Team(home_data["team"]["id"], home_name, self._abbr(home_name)),
                    venue=venue.get("name", "TBD"), status=item.get("status", {}).get("detailedState", "Scheduled"),
                    away_pitcher=self._pitcher(away_data), home_pitcher=self._pitcher(home_data), raw=item,
                ))
        return result

    @staticmethod
    def _pitcher(team_data: dict) -> Pitcher:
        p = team_data.get("probablePitcher") or {}
        return Pitcher(p.get("id"), p.get("fullName", "TBD"), bool(p))


class MLBLineupProvider:
    """Reads official game feeds. Batting orders generally appear when clubs submit them."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def enrich(self, games: list[Game]) -> list[Game]:
        def enrich_game(game: Game) -> None:
            try:
                url = f"https://statsapi.mlb.com/api/v1.1/game/{game.id}/feed/live"
                data = requests.get(url, timeout=self.timeout).json()
                box = data.get("liveData", {}).get("boxscore", {}).get("teams", {})
                away_order = box.get("away", {}).get("battingOrder") or []
                home_order = box.get("home", {}).get("battingOrder") or []
                game.away_lineup_status = "CONFIRMED" if len(away_order) >= 9 else "PROJECTED"
                game.home_lineup_status = "CONFIRMED" if len(home_order) >= 9 else "PROJECTED"
                if away_order or home_order:
                    game.lineup_note = "Official batting order posted" if len(away_order) >= 9 and len(home_order) >= 9 else "One lineup posted; monitoring the other"
            except (requests.RequestException, ValueError):
                game.lineup_note = "Lineup feed temporarily unavailable"
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(games)))) as pool:
            list(pool.map(enrich_game, games))
        return games
