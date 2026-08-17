from dataclasses import dataclass
import re
import unicodedata

import requests


@dataclass
class RecentForm:
    player: str
    market: str
    values: list[float]

    @property
    def last_five(self) -> list[float]:
        return self.values[-5:]

    @property
    def last_five_average(self) -> float | None:
        return sum(self.last_five) / len(self.last_five) if self.last_five else None

    @property
    def season_average(self) -> float | None:
        return sum(self.values) / len(self.values) if self.values else None

    def hit_rate(self, line: float, side: str, last: int | None = None) -> float | None:
        sample = self.values[-last:] if last else self.values
        if not sample:
            return None
        wins = sum(value > line if side.lower() == "over" else value < line for value in sample)
        return wins / len(sample)


class MLBRecentFormProvider:
    """Public MLB Stats API game logs. Recent hit rates are descriptive, not projections."""

    BASE = "https://statsapi.mlb.com/api/v1"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @staticmethod
    def _normal(name: str) -> str:
        value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
        return re.sub(r"[^a-z0-9]", "", value)

    def _player_ids(self, season: int) -> dict[str, int]:
        response = requests.get(f"{self.BASE}/sports/1/players", params={"season": season}, timeout=self.timeout)
        response.raise_for_status()
        return {self._normal(person["fullName"]): int(person["id"]) for person in response.json().get("people", [])}

    @staticmethod
    def _outs(innings: str | float | int | None) -> float:
        if innings is None:
            return 0.0
        whole, _, remainder = str(innings).partition(".")
        return float(int(whole) * 3 + int((remainder or "0")[:1]))

    def forms(self, requests_: list[tuple[str, str]], season: int) -> dict[tuple[str, str], RecentForm]:
        try:
            ids = self._player_ids(season)
        except (requests.RequestException, TypeError, ValueError):
            return {}
        output: dict[tuple[str, str], RecentForm] = {}
        for player, market in sorted(set(requests_)):
            player_id = ids.get(self._normal(player))
            if not player_id:
                continue
            pitching = market.startswith("pitcher_")
            params = {"stats": "gameLog", "group": "pitching" if pitching else "hitting",
                      "season": season, "gameType": "R"}
            try:
                response = requests.get(f"{self.BASE}/people/{player_id}/stats", params=params, timeout=self.timeout)
                response.raise_for_status()
                splits = [split for block in response.json().get("stats", []) for split in block.get("splits", [])]
                splits.sort(key=lambda split: split.get("date", ""))
                values = []
                for split in splits:
                    stat = split.get("stat", {})
                    if market == "pitcher_strikeouts": value = stat.get("strikeOuts")
                    elif market == "pitcher_outs": value = self._outs(stat.get("inningsPitched"))
                    elif market == "batter_hits": value = stat.get("hits")
                    elif market == "batter_total_bases": value = stat.get("totalBases")
                    else: value = None
                    if value is not None:
                        values.append(float(value))
                output[(player, market)] = RecentForm(player, market, values)
            except (requests.RequestException, TypeError, ValueError):
                continue
        return output
