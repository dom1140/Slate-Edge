from datetime import datetime, timezone
from slate_edge.domain import Game, OddsQuote, Team
from slate_edge.engine import build_recommendations, implied_probability, kelly, no_vig_probabilities
from slate_edge.predictive import ModelContext


def test_implied_probability():
    assert round(implied_probability(-110), 4) == .5238
    assert round(implied_probability(150), 4) == .4


def test_no_vig_sums_to_one():
    a, b = no_vig_probabilities(-120, 110)
    assert round(a + b, 10) == 1


def test_kelly_never_negative():
    assert kelly(.40, -150) == 0


def test_unvalidated_model_sizes_only_in_paper_mode():
    game = Game("1", "MLB", datetime.now(timezone.utc), Team(1,"Away","AWY"), Team(2,"Home","HME"))
    quotes = [OddsQuote("1","Book","h2h","Home",100,datetime.now(timezone.utc)),
              OddsQuote("1","Book","h2h","Away",100,datetime.now(timezone.utc))]
    model = ModelContext("test", False, "locked", [0,1,.8,0], {"1":1400,"2":1600}, {}, {})
    locked = build_recommendations([game],quotes,1000,.5,.02,.08,.01,model)
    paper = build_recommendations([game],quotes,1000,.5,.02,.08,.01,model,paper_test=True)
    assert sum(r.stake for r in locked) == 0
    assert any(r.stake > 0 and r.simulated for r in paper)
