from datetime import datetime, timezone

from scripts.train_model import match_quote, quote_from_event


def _book(name, home, away, updated="2025-06-01T18:55:00Z"):
    return {"key": name, "title": name, "last_update": updated,
            "markets": [{"key": "h2h", "outcomes": [
                {"name": "Home", "price": home}, {"name": "Away", "price": away}]}]}


def test_stale_outlier_is_not_selected_as_best_price():
    event = {"home_team": "Home", "away_team": "Away", "bookmakers": [
        _book("a", -110, -110), _book("b", -108, -112), _book("c", -112, -108),
        _book("stale", 300, -500, "2025-06-01T08:00:00Z")]}
    quote = quote_from_event(event, datetime(2025, 6, 1, 19, tzinfo=timezone.utc))
    assert quote is not None
    assert quote["home_odds"] == -108
    assert "stale" not in quote["consensus_books"]


def test_doubleheader_matches_nearest_start():
    game = {"home": "Home", "away": "Away", "start": "2025-06-01T23:00:00Z"}
    quotes = [
        {"home": "Home", "away": "Away", "commence": "2025-06-01T18:00:00Z", "event_id": "one"},
        {"home": "Home", "away": "Away", "commence": "2025-06-01T23:05:00Z", "event_id": "two"},
    ]
    assert match_quote(game, quotes)["event_id"] == "two"
