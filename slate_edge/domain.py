from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Team:
    id: int
    name: str
    abbreviation: str


@dataclass
class Pitcher:
    id: int | None = None
    name: str = "TBD"
    confirmed: bool = False


@dataclass
class Weather:
    temperature_f: float | None = None
    wind_mph: float | None = None
    precipitation_probability: float | None = None
    summary: str = "Unavailable"
    fetched_at: datetime | None = None


@dataclass
class OddsQuote:
    game_id: str
    sportsbook: str
    market: str
    selection: str
    american_odds: int
    fetched_at: datetime
    point: float | None = None
    participant: str | None = None


@dataclass
class Game:
    id: str
    sport: str
    start_time: datetime
    away: Team
    home: Team
    venue: str = "TBD"
    venue_lat: float | None = None
    venue_lon: float | None = None
    status: str = "Scheduled"
    away_pitcher: Pitcher = field(default_factory=Pitcher)
    home_pitcher: Pitcher = field(default_factory=Pitcher)
    away_lineup_status: str = "PROJECTED"
    home_lineup_status: str = "PROJECTED"
    lineup_note: str = "Lineups not yet confirmed"
    injuries: list[str] = field(default_factory=list)
    weather: Weather = field(default_factory=Weather)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    game: Game
    selection: str
    odds: int
    sportsbook: str
    market_probability: float
    model_probability: float
    edge: float
    expected_value: float
    kelly_fraction: float
    stake: float
    grade: str
    confidence: str
    reasons: list[str]
    quote_fetched_at: datetime | None
    simulated: bool = False
