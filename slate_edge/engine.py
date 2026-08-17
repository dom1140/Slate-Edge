from __future__ import annotations

from collections import defaultdict
from slate_edge.domain import Game, OddsQuote, Recommendation
from slate_edge.predictive import ModelContext


def implied_probability(odds: int) -> float:
    return abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)


def decimal_odds(odds: int) -> float:
    return 1 + (100 / abs(odds) if odds < 0 else odds / 100)


def no_vig_probabilities(a: int, b: int) -> tuple[float, float]:
    pa, pb = implied_probability(a), implied_probability(b)
    return pa / (pa + pb), pb / (pa + pb)


def kelly(probability: float, odds: int) -> float:
    dec = decimal_odds(odds)
    return max(0.0, (probability * dec - 1) / (dec - 1))


def build_recommendations(games: list[Game], quotes: list[OddsQuote], bankroll: float, fraction: float,
                          max_bet_pct: float, max_slate_pct: float, min_edge: float,
                          model: ModelContext | None = None) -> list[Recommendation]:
    by_game: dict[str, list[OddsQuote]] = defaultdict(list)
    for quote in quotes:
        by_game[quote.game_id].append(quote)
    recs: list[Recommendation] = []
    for game in games:
        game_quotes = by_game.get(game.id, [])
        if not game_quotes:
            continue
        best: dict[str, OddsQuote] = {}
        for q in game_quotes:
            if q.selection not in best or q.american_odds > best[q.selection].american_odds:
                best[q.selection] = q
        if game.home.name not in best or game.away.name not in best:
            continue
        home_q, away_q = best[game.home.name], best[game.away.name]
        home_market, away_market = no_vig_probabilities(home_q.american_odds, away_q.american_odds)
        model_ready = bool(model and model.validated and model.coefficients)
        if model_ready:
            home_model = model.home_probability(home_market, game.home.id, game.away.id)
            reasons = [f"Validated model {model.version}", "Consensus no-vig market input",
                       "Frozen market/Elo/run-strength coefficients"]
        else:
            # Research-only baseline. It may display diagnostics, but the wagering gate below forces PASS.
            adjustment = .004
            reasons = ["Research baseline — wagering locked", "Consensus no-vig market baseline"]
            if game.home_pitcher.confirmed and not game.away_pitcher.confirmed:
                adjustment += .012; reasons.append("Home probable pitcher confirmed")
            elif game.away_pitcher.confirmed and not game.home_pitcher.confirmed:
                adjustment -= .012; reasons.append("Away probable pitcher confirmed")
            if game.home_lineup_status == "CONFIRMED" and game.away_lineup_status != "CONFIRMED":
                adjustment += .006; reasons.append("Home lineup confirmed first")
            elif game.away_lineup_status == "CONFIRMED" and game.home_lineup_status != "CONFIRMED":
                adjustment -= .006; reasons.append("Away lineup confirmed first")
            home_model = min(.95, max(.05, home_market + adjustment))
        for selection, quote, market_p, model_p in [
            (game.home.name, home_q, home_market, home_model),
            (game.away.name, away_q, away_market, 1 - home_model),
        ]:
            edge = model_p - market_p
            ev = model_p * (decimal_odds(quote.american_odds) - 1) - (1 - model_p)
            full_kelly = kelly(model_p, quote.american_odds)
            raw_stake = bankroll * full_kelly * fraction if model_ready and edge >= min_edge else 0
            stake = round(min(raw_stake, bankroll * max_bet_pct), 2)
            grade = "A" if edge >= .06 else "B" if edge >= .04 else "C" if edge >= min_edge else "PASS"
            confidence = "Validated" if model_ready else "Research only"
            recs.append(Recommendation(game, selection, quote.american_odds, quote.sportsbook, market_p, model_p,
                                       edge, ev, full_kelly, stake, grade, confidence, reasons.copy(), quote.fetched_at))
    recs.sort(key=lambda r: (r.stake > 0, r.expected_value), reverse=True)
    cap = bankroll * max_slate_pct
    total = sum(r.stake for r in recs)
    if total > cap and total > 0:
        scale = cap / total
        for r in recs:
            r.stake = round(r.stake * scale, 2)
    return recs
