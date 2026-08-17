from slate_edge.predictive import BaseballFactors, ModelContext


def test_model_probability_is_bounded():
    model = ModelContext("test", True, "ok", [0.0, 1.0, 0.3, 0.1], {"1": 1550, "2": 1450}, {"1": .5, "2": -.5}, {})
    result = model.home_probability(.55, 1, 2)
    assert .55 < result < .95


def test_missing_team_state_uses_neutral_defaults():
    model = ModelContext("test", True, "ok", [0.0, 1.0, 0.0, 0.0], {}, {}, {})
    assert abs(model.home_probability(.5, 1, 2) - .5) < 1e-9


def test_unavailable_rich_factors_are_explicit_and_neutral():
    factors = BaseballFactors(starter_quality=.2)
    model = ModelContext("future", False, "research", [0, 1, 0, 0, .5], {}, {}, {})
    assert "bullpen_availability" in factors.missing()
    assert model.home_probability(.5, 1, 2, factors) > .5
