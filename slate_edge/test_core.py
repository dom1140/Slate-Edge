from core import implied_probability, no_vig_two_way_prob, kelly_fraction, expected_roi, capped_fractional_kelly

def approx(a,b,tol=1e-6):
    return abs(a-b) < tol

assert approx(implied_probability(-110), 110/210)
assert approx(implied_probability(150), 100/250)

p1,p2 = no_vig_two_way_prob(-120, 100)
assert approx(p1+p2, 1.0)

assert kelly_fraction(0.50, 100) == 0
assert expected_roi(0.60, -110) > 0

x = capped_fractional_kelly(
    bankroll=1000,
    prob=0.60,
    american_odds=-110,
    kelly_multiplier=0.25,
    max_bet_pct=0.015,
    min_edge_pp=2.5,
    market_fair_prob=0.52
)
assert 0 <= x["stake"] <= 15.0
print("All core tests passed.")
