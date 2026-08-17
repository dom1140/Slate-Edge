from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

def american_to_decimal(odds: float) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be 0.")
    return 1 + (100 / abs(odds) if odds < 0 else odds / 100)

def implied_probability(odds: float) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)

def no_vig_two_way_prob(odds_a: float, odds_b: float) -> tuple[float, float]:
    pa = implied_probability(odds_a)
    pb = implied_probability(odds_b)
    s = pa + pb
    return pa / s, pb / s

def kelly_fraction(prob: float, american_odds: float) -> float:
    """Full Kelly fraction of bankroll."""
    d = american_to_decimal(american_odds)
    b = d - 1
    q = 1 - prob
    return max(0.0, (b * prob - q) / b)

def expected_roi(prob: float, american_odds: float) -> float:
    """Expected profit per $1 staked."""
    d = american_to_decimal(american_odds)
    return prob * (d - 1) - (1 - prob)

def payout_profit(stake: float, american_odds: float) -> float:
    if american_odds < 0:
        return stake * 100 / abs(american_odds)
    return stake * american_odds / 100

def grade_recommendation(edge_pp: float, ev_roi: float) -> str:
    if edge_pp >= 6 and ev_roi >= 0.06:
        return "A"
    if edge_pp >= 4 and ev_roi >= 0.035:
        return "B"
    if edge_pp >= 2.5 and ev_roi >= 0.02:
        return "C"
    return "PASS"

def capped_fractional_kelly(
    bankroll: float,
    prob: float,
    american_odds: float,
    kelly_multiplier: float = 0.25,
    max_bet_pct: float = 0.015,
    min_edge_pp: float = 2.5,
    market_fair_prob: Optional[float] = None,
) -> dict:
    implied = implied_probability(american_odds)
    reference = market_fair_prob if market_fair_prob is not None else implied
    edge_pp = (prob - reference) * 100
    full_k = kelly_fraction(prob, american_odds)
    frac_k = full_k * kelly_multiplier
    capped = min(frac_k, max_bet_pct)
    ev = expected_roi(prob, american_odds)
    if edge_pp < min_edge_pp or ev <= 0:
        capped = 0.0
    stake = max(0.0, bankroll * capped)
    return {
        "implied_prob": implied,
        "reference_prob": reference,
        "model_prob": prob,
        "edge_pp": edge_pp,
        "full_kelly": full_k,
        "kelly_used": frac_k,
        "stake_pct": capped,
        "stake": stake,
        "ev_roi": ev,
        "grade": grade_recommendation(edge_pp, ev),
    }

def mlb_market_adjusted_probability(
    market_fair_prob: float,
    starter_edge: float = 0.0,
    offense_edge: float = 0.0,
    bullpen_edge: float = 0.0,
    defense_edge: float = 0.0,
    park_weather_edge: float = 0.0,
    lineup_edge: float = 0.0,
    home_edge: float = 0.0,
) -> float:
    """
    Transparent test model.

    Each *_edge is entered on a -10 to +10 scale from the perspective of
    the selected side. The market's no-vig probability is the prior.
    Adjustments operate in log-odds space and are deliberately conservative.

    This is not a trained production model; it is a structured starting point
    that can later be replaced by a fitted model using historical data.
    """
    p = min(max(market_fair_prob, 0.02), 0.98)
    logit = math.log(p / (1-p))
    weights = {
        "starter": 0.032,
        "offense": 0.020,
        "bullpen": 0.018,
        "defense": 0.009,
        "park_weather": 0.007,
        "lineup": 0.016,
        "home": 0.008,
    }
    logit += starter_edge * weights["starter"]
    logit += offense_edge * weights["offense"]
    logit += bullpen_edge * weights["bullpen"]
    logit += defense_edge * weights["defense"]
    logit += park_weather_edge * weights["park_weather"]
    logit += lineup_edge * weights["lineup"]
    logit += home_edge * weights["home"]
    return 1 / (1 + math.exp(-logit))
