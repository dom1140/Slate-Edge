from slate_edge.providers.recent_form import MLBRecentFormProvider, RecentForm


def test_recent_form_rates_and_averages():
    form = RecentForm("Player", "batter_hits", [0, 1, 2, 1, 3, 0])
    assert form.last_five == [1, 2, 1, 3, 0]
    assert form.last_five_average == 1.4
    assert form.hit_rate(.5, "Over", 5) == .8
    assert form.hit_rate(1.5, "Under", 5) == .6


def test_innings_to_outs():
    assert MLBRecentFormProvider._outs("5.2") == 17
    assert MLBRecentFormProvider._outs("6.0") == 18
