"""Train and validate SlateEdge's market-aware MLB model using historical closing snapshots.

This script is designed for a manual GitHub Actions run. It consumes paid historical
API credits, saves normalized observations, and writes a versioned artifact only after
a strictly later season is evaluated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import time
from statistics import median

import numpy as np
import requests

API = "https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/odds"
MLB = "https://statsapi.mlb.com/api/v1/schedule"


def implied(odds: int) -> float:
    return abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)


def decimal(odds: int) -> float:
    return 1 + (100 / abs(odds) if odds < 0 else odds / 100)


def logit(p: float) -> float:
    p = min(.995, max(.005, p)); return math.log(p / (1 - p))


def date_range(year: int):
    current, end = datetime(year, 3, 20, tzinfo=timezone.utc), datetime(year, 10, 2, tzinfo=timezone.utc)
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_results(year: int) -> list[dict]:
    params = {"sportId": 1, "startDate": f"{year}-03-20", "endDate": f"{year}-10-02", "gameType": "R"}
    response = requests.get(MLB, params=params, timeout=45); response.raise_for_status()
    games = []
    for block in response.json().get("dates", []):
        for g in block.get("games", []):
            home, away = g["teams"]["home"], g["teams"]["away"]
            if home.get("score") is None or away.get("score") is None:
                continue
            games.append({"id": str(g["gamePk"]), "start": g["gameDate"], "home": home["team"]["name"],
                          "away": away["team"]["name"], "home_id": home["team"]["id"], "away_id": away["team"]["id"],
                          "home_score": home["score"], "away_score": away["score"]})
    return games


MAX_QUOTE_AGE_MINUTES = 360
MIN_BOOKS = 3


def quote_from_event(event: dict, snapshot: datetime | None = None) -> dict | None:
    """Build a robust consensus and executable prices from fresh, non-outlier books."""
    pairs = []
    for book in event.get("bookmakers", []):
        updated_raw = book.get("last_update")
        if snapshot and updated_raw:
            updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
            if updated > snapshot or snapshot - updated > timedelta(minutes=MAX_QUOTE_AGE_MINUTES):
                continue
        for market in book.get("markets", []):
            if market.get("key") != "h2h": continue
            outcomes = {o["name"]: int(o["price"]) for o in market.get("outcomes", [])}
            home, away = event.get("home_team"), event.get("away_team")
            if home in outcomes and away in outcomes:
                hp, ap = implied(outcomes[home]), implied(outcomes[away])
                pairs.append((hp / (hp + ap), outcomes[home], outcomes[away], book.get("title", book.get("key")), updated_raw))
    if len(pairs) < MIN_BOOKS:
        return None
    center = median(p[0] for p in pairs)
    # Remove prices whose no-vig view is far from the market center. This prevents
    # stale/error quotes from becoming a fictitious executable best price.
    filtered = [p for p in pairs if abs(p[0] - center) <= .035]
    if len(filtered) < MIN_BOOKS:
        return None
    consensus = median(p[0] for p in filtered)
    # Require the offered side price itself to be reasonably consistent with consensus.
    executable = [p for p in filtered if abs(implied(p[1]) - consensus) <= .08 and
                  abs(implied(p[2]) - (1 - consensus)) <= .08]
    if len(executable) < MIN_BOOKS:
        return None
    best_home = max(p[1] for p in executable); best_away = max(p[2] for p in executable)
    return {"market_home": consensus, "home_odds": best_home, "away_odds": best_away,
            "books": len(executable), "consensus_books": sorted({p[3] for p in executable})}


def fetch_season_odds(year: int, api_key: str, cache_dir: Path) -> list[dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    latest: dict[str, dict] = {}
    for day in date_range(year):
        for hour in (15, 19, 23):
            stamp = day.replace(hour=hour).isoformat().replace("+00:00", "Z")
            cache = cache_dir / f"mlb_{year}_{day:%m%d}_{hour}.json"
            if cache.exists(): payload = json.loads(cache.read_text(encoding="utf-8"))
            else:
                params = {"apiKey": api_key, "regions": "us", "markets": "h2h", "oddsFormat": "american", "date": stamp}
                response = requests.get(API, params=params, timeout=45); response.raise_for_status()
                payload = response.json(); cache.write_text(json.dumps(payload), encoding="utf-8"); time.sleep(.12)
            for event in payload.get("data", []):
                commence = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
                snapshot = datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
                if snapshot >= commence: continue
                # A quote must be pregame and close enough to represent the intended
                # decision window, not an arbitrary morning number.
                if commence - snapshot > timedelta(hours=8): continue
                quote = quote_from_event(event, snapshot)
                if not quote: continue
                event_id = str(event.get("id") or f'{event["home_team"]}|{event["away_team"]}|{event["commence_time"]}')
                if event_id not in latest or latest[event_id]["snapshot"] < payload["timestamp"]:
                    latest[event_id] = {**quote, "event_id": event_id, "home": event["home_team"],
                                        "away": event["away_team"], "snapshot": payload["timestamp"],
                                        "commence": event["commence_time"]}
    return list(latest.values())


def match_quote(game: dict, quotes: list[dict]) -> dict | None:
    """Match by teams and nearest start time, preserving both games of a doubleheader."""
    game_start = datetime.fromisoformat(game["start"].replace("Z", "+00:00"))
    candidates = []
    for quote in quotes:
        if quote["home"] != game["home"] or quote["away"] != game["away"]:
            continue
        quote_start = datetime.fromisoformat(quote["commence"].replace("Z", "+00:00"))
        delta = abs((quote_start - game_start).total_seconds())
        if delta <= 90 * 60:
            candidates.append((delta, quote))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def observations(years: list[int], key: str, cache_dir: Path):
    rows=[]; ratings={}; strength={}
    for year in years:
        games=fetch_results(year); odds=fetch_season_odds(year,key,cache_dir)
        games.sort(key=lambda g:g["start"])
        for g in games:
            hid,aid=str(g["home_id"]),str(g["away_id"]); hr=ratings.get(hid,1500.); ar=ratings.get(aid,1500.)
            hs=strength.get(hid,0.); ass=strength.get(aid,0.)
            q=match_quote(g,odds)
            if q:
                rows.append({**g,**q,"year":year,"y":1 if g["home_score"]>g["away_score"] else 0,
                             "features":[1.,logit(q["market_home"]),(hr-ar)/400.,(hs-ass)/5.]})
            expected=1/(1+10**(-((hr+24)-ar)/400)); actual=1 if g["home_score"]>g["away_score"] else 0
            change=18*(actual-expected); ratings[hid]=hr+change; ratings[aid]=ar-change
            margin=g["home_score"]-g["away_score"]
            strength[hid]=.92*hs+.08*margin; strength[aid]=.92*ass-.08*margin
    return rows,ratings,strength


def fit_logistic(x,y,steps=30):
    beta=np.zeros(x.shape[1]); beta[1]=1.0
    for _ in range(steps):
        p=1/(1+np.exp(-np.clip(x@beta,-30,30))); w=np.clip(p*(1-p),1e-6,None)
        h=x.T@(x*w[:,None])+np.eye(x.shape[1])*1e-3; grad=x.T@(y-p)-1e-3*beta
        beta += np.linalg.solve(h,grad)
    return beta


def metrics(rows,beta):
    x=np.array([r["features"] for r in rows]); y=np.array([r["y"] for r in rows],dtype=float)
    p=1/(1+np.exp(-np.clip(x@beta,-30,30))); market=np.array([r["market_home"] for r in rows])
    brier=float(np.mean((p-y)**2)); mb=float(np.mean((market-y)**2))
    ll=float(-np.mean(y*np.log(np.clip(p,1e-6,1))+(1-y)*np.log(np.clip(1-p,1e-6,1))))
    mll=float(-np.mean(y*np.log(market)+(1-y)*np.log(1-market)))
    # Actual realized flat-stake returns, not model EV.
    actual=[]
    for r,prob in zip(rows,p):
        if prob-r["market_home"]>=.025: actual.append(decimal(r["home_odds"])-1 if r["y"] else -1)
        elif (1-prob)-(1-r["market_home"])>=.025: actual.append(decimal(r["away_odds"])-1 if not r["y"] else -1)
    roi=float(np.mean(actual)) if actual else 0.0
    return {"games":len(rows),"brier":brier,"market_brier":mb,"log_loss":ll,"market_log_loss":mll,
            "qualified_bets":len(actual),"flat_stake_roi":roi}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--train-year",type=int,default=2024); parser.add_argument("--test-year",type=int,default=2025)
    parser.add_argument("--cache",default="data/historical_odds"); parser.add_argument("--output",default="model_artifact.json")
    args=parser.parse_args(); key=os.environ["HISTORICAL_ODDS_API_KEY"]
    rows,ratings,strength=observations([args.train_year,args.test_year],key,Path(args.cache))
    train=[r for r in rows if r["year"]==args.train_year]; test=[r for r in rows if r["year"]==args.test_year]
    beta=fit_logistic(np.array([r["features"] for r in train]),np.array([r["y"] for r in train],dtype=float))
    report=metrics(test,beta)
    passed=(report["games"]>=1800 and report["brier"]<report["market_brier"]-.0005 and
            report["log_loss"]<report["market_log_loss"]-.001 and report["qualified_bets"]>=100 and report["flat_stake_roi"]>0)
    reason="Passed strict 2025 holdout gates" if passed else "Holdout gates not met; wagering remains locked"
    artifact={"version":f"mlb-market-elo-{datetime.now(timezone.utc):%Y%m%d}","trained_at":datetime.now(timezone.utc).isoformat(),
              "train_year":args.train_year,"test_year":args.test_year,"coefficients":beta.tolist(),"ratings":ratings,
              "feature_names":["intercept","market_logit","elo_difference","run_strength"],
              "data_quality":{"event_time_matching":True,"doubleheader_safe":True,"max_quote_age_minutes":MAX_QUOTE_AGE_MINUTES,
                              "minimum_books":MIN_BOOKS,"outlier_filter":True,"decision_window_hours":8},
              "run_strength":strength,"metrics":report,"validation_gate":{"passed":passed,"reason":reason}}
    Path(args.output).write_text(json.dumps(artifact,indent=2),encoding="utf-8")
    print(json.dumps({"validation_gate":artifact["validation_gate"],"metrics":report},indent=2))


if __name__=="__main__": main()
