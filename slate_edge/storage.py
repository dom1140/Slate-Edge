from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


class BetStore:
    def __init__(self, path: str = "slate_edge.db"):
        self.path = path
        self._init()

    def connect(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY, placed_at TEXT NOT NULL, sport TEXT NOT NULL, event TEXT NOT NULL,
                selection TEXT NOT NULL, market TEXT NOT NULL, sportsbook TEXT NOT NULL, odds INTEGER NOT NULL,
                stake REAL NOT NULL, result TEXT NOT NULL DEFAULT 'OPEN', payout REAL NOT NULL DEFAULT 0,
                closing_odds INTEGER, model_probability REAL, edge REAL, notes TEXT DEFAULT '')""")

    def add(self, **bet):
        fields = ["placed_at", "sport", "event", "selection", "market", "sportsbook", "odds", "stake", "model_probability", "edge", "notes"]
        values = [bet.get(k) for k in fields]
        with self.connect() as db:
            db.execute(f"INSERT INTO bets ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", values)

    def settle(self, bet_id: int, result: str, payout: float, closing_odds: int | None):
        with self.connect() as db:
            db.execute("UPDATE bets SET result=?, payout=?, closing_odds=? WHERE id=?", (result, payout, closing_odds, bet_id))

    def frame(self) -> pd.DataFrame:
        with self.connect() as db:
            return pd.read_sql_query("SELECT * FROM bets ORDER BY placed_at DESC", db)


def clv_percent(placed: int, closing: int | None) -> float | None:
    if closing is None:
        return None
    from slate_edge.engine import implied_probability
    return (implied_probability(closing) / implied_probability(placed) - 1) * 100

