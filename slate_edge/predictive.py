from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def _logit(p: float) -> float:
    p = min(.995, max(.005, p))
    return math.log(p / (1 - p))


@dataclass
class ModelContext:
    version: str
    validated: bool
    reason: str
    coefficients: list[float]
    ratings: dict[str, float]
    run_strength: dict[str, float]
    metrics: dict[str, Any]

    def home_probability(self, market_probability: float, home_id: int, away_id: int) -> float:
        home_rating = self.ratings.get(str(home_id), 1500.0)
        away_rating = self.ratings.get(str(away_id), 1500.0)
        home_runs = self.run_strength.get(str(home_id), 0.0)
        away_runs = self.run_strength.get(str(away_id), 0.0)
        features = [1.0, _logit(market_probability), (home_rating - away_rating) / 400.0,
                    (home_runs - away_runs) / 5.0]
        return min(.95, max(.05, _sigmoid(sum(a * b for a, b in zip(self.coefficients, features)))))


def load_model(path: str | Path) -> ModelContext:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return ModelContext("research-baseline", False, "No validated artifact has been trained", [], {}, {}, {})
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    gate = data.get("validation_gate", {})
    return ModelContext(data.get("version", "unknown"), bool(gate.get("passed")),
                        gate.get("reason", "Validation status unavailable"), data.get("coefficients", []),
                        data.get("ratings", {}), data.get("run_strength", {}), data.get("metrics", {}))


def update_current_season(context: ModelContext, season: int, timeout: int = 20) -> ModelContext:
    """Update only latent team state from completed current-season games; coefficients remain frozen."""
    if not context.coefficients:
        return context
    ratings, run_strength = dict(context.ratings), dict(context.run_strength)
    try:
        params = {"sportId": 1, "startDate": f"{season}-03-01", "endDate": date.today().isoformat(),
                  "gameType": "R"}
        payload = requests.get("https://statsapi.mlb.com/api/v1/schedule", params=params, timeout=timeout).json()
        games = [g for block in payload.get("dates", []) for g in block.get("games", [])]
        games.sort(key=lambda g: g.get("gameDate", ""))
        for game in games:
            teams = game.get("teams", {})
            home, away = teams.get("home", {}), teams.get("away", {})
            if not home.get("isWinner") and not away.get("isWinner"):
                continue
            hid, aid = str(home["team"]["id"]), str(away["team"]["id"])
            hr, ar = float(ratings.get(hid, 1500)), float(ratings.get(aid, 1500))
            expected = 1 / (1 + 10 ** (-(hr + 24 - ar) / 400))
            actual = 1.0 if home.get("isWinner") else 0.0
            change = 18 * (actual - expected)
            ratings[hid], ratings[aid] = hr + change, ar - change
            hs, ass = home.get("score"), away.get("score")
            if hs is not None and ass is not None:
                margin = float(hs) - float(ass)
                run_strength[hid] = .92 * float(run_strength.get(hid, 0)) + .08 * margin
                run_strength[aid] = .92 * float(run_strength.get(aid, 0)) - .08 * margin
    except (requests.RequestException, KeyError, TypeError, ValueError):
        pass
    return ModelContext(context.version, context.validated, context.reason, context.coefficients,
                        ratings, run_strength, context.metrics)

