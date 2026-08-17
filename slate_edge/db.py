from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).with_name("slate_edge.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sport TEXT NOT NULL,
    event_date TEXT,
    event TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds REAL NOT NULL,
    stake REAL NOT NULL,
    model_prob REAL,
    market_fair_prob REAL,
    edge_pp REAL,
    ev_roi REAL,
    closing_odds REAL,
    result TEXT DEFAULT 'OPEN',
    profit REAL DEFAULT 0,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS bankroll_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    amount REAL NOT NULL,
    reason TEXT
);
"""

def conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL;")
    return c

def init_db(starting_bankroll: float = 1000.0):
    with conn() as c:
        c.executescript(SCHEMA)
        n = c.execute("SELECT COUNT(*) FROM bankroll_log").fetchone()[0]
        if n == 0:
            c.execute(
                "INSERT INTO bankroll_log(amount, reason) VALUES(?, ?)",
                (starting_bankroll, "Starting bankroll"),
            )

def get_bankroll() -> float:
    with conn() as c:
        deposits = c.execute("SELECT COALESCE(SUM(amount),0) FROM bankroll_log").fetchone()[0]
        pnl = c.execute("SELECT COALESCE(SUM(profit),0) FROM bets WHERE result != 'OPEN'").fetchone()[0]
        return float(deposits + pnl)

def add_bankroll_adjustment(amount: float, reason: str):
    with conn() as c:
        c.execute("INSERT INTO bankroll_log(amount, reason) VALUES(?,?)", (amount, reason))

def add_bet(row: dict):
    cols = [
        "sport","event_date","event","market","selection","odds","stake",
        "model_prob","market_fair_prob","edge_pp","ev_roi","notes"
    ]
    vals = [row.get(k) for k in cols]
    with conn() as c:
        c.execute(
            f"INSERT INTO bets({','.join(cols)}) VALUES({','.join(['?']*len(cols))})",
            vals
        )

def bets_df() -> pd.DataFrame:
    with conn() as c:
        return pd.read_sql_query("SELECT * FROM bets ORDER BY id DESC", c)

def settle_bet(bet_id: int, result: str, closing_odds=None):
    with conn() as c:
        row = c.execute("SELECT odds, stake FROM bets WHERE id=?", (bet_id,)).fetchone()
        if not row:
            raise ValueError("Bet not found.")
        odds, stake = row
        if result == "WIN":
            profit = stake * (100/abs(odds) if odds < 0 else odds/100)
        elif result == "LOSS":
            profit = -stake
        elif result == "PUSH":
            profit = 0.0
        else:
            raise ValueError("Result must be WIN, LOSS, or PUSH.")
        c.execute(
            "UPDATE bets SET result=?, profit=?, closing_odds=COALESCE(?,closing_odds) WHERE id=?",
            (result, profit, closing_odds, bet_id)
        )

def analytics():
    df = bets_df()
    settled = df[df["result"] != "OPEN"].copy() if not df.empty else df
    if settled.empty:
        return {
            "bets": 0, "wins": 0, "losses": 0, "pushes": 0,
            "profit": 0.0, "staked": 0.0, "roi": 0.0, "win_rate": 0.0
        }
    staked = settled["stake"].sum()
    profit = settled["profit"].sum()
    wins = int((settled["result"]=="WIN").sum())
    losses = int((settled["result"]=="LOSS").sum())
    pushes = int((settled["result"]=="PUSH").sum())
    decisions = wins + losses
    return {
        "bets": len(settled),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "profit": float(profit),
        "staked": float(staked),
        "roi": float(profit/staked) if staked else 0.0,
        "win_rate": float(wins/decisions) if decisions else 0.0,
    }
