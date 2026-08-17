from datetime import datetime, timezone
from slate_edge.engine import implied_probability, kelly, no_vig_probabilities


def test_implied_probability():
    assert round(implied_probability(-110), 4) == .5238
    assert round(implied_probability(150), 4) == .4


def test_no_vig_sums_to_one():
    a, b = no_vig_probabilities(-120, 110)
    assert round(a + b, 10) == 1


def test_kelly_never_negative():
    assert kelly(.40, -150) == 0

