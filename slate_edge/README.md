# SlateEdge

SlateEdge is a local Streamlit betting-analysis application designed to:

- analyze a slate across multiple sports,
- remove sportsbook vig from two-way prices,
- compare market fair probability with a model probability,
- calculate expected value,
- recommend an exact stake using fractional Kelly,
- enforce max-bet and max-slate exposure controls,
- log bets in SQLite,
- settle bets and track bankroll/P&L/ROI,
- record closing odds for CLV review.

## Current build

MLB is the first test implementation. The included "MLB Matchup Lab" is a transparent
market-prior model that lets you grade pitcher, offense, bullpen, lineup, defense,
park/weather and home/rest edges.

**It is not yet a trained historical MLB model.** The architecture deliberately separates
probability estimation from bankroll sizing so a trained model can replace it later.

## Install

Requires Python 3.10+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. The SQLite database (`slate_edge.db`) is created automatically
in the project folder and persists your tracked bets.

## CSV format

Required columns:

- `sport`
- `event_date`
- `event`
- `market`
- `selection`
- `odds`
- `opposite_odds`
- `model_prob` (decimal, e.g. 0.58)

Example:

```csv
sport,event_date,event,market,selection,odds,opposite_odds,model_prob
MLB,2026-08-17,DET Tigers at PIT Pirates,Moneyline,DET Tigers,-120,100,0.585
```

## Default risk settings

- Bankroll: $1,000
- Kelly multiplier: 0.25 (quarter Kelly)
- Max single bet: 1.5% of bankroll
- Max slate exposure: 6% of bankroll
- Minimum edge: 2.5 percentage points vs no-vig market probability

These are deliberately conservative. No staking system can make a negative-EV betting model profitable.

## Recommended next upgrades

1. Historical MLB data ingestion.
2. Closing-odds history and line-shopping provider.
3. Fitted win-probability model (e.g. regularized logistic regression / gradient boosting).
4. Walk-forward backtesting and calibration curves.
5. Starting pitcher projection module.
6. Bullpen fatigue model.
7. Confirmed-lineup and injury adjustments.
8. Weather/park run-environment model.
9. Sports-specific plugins for NFL, NBA, NHL, soccer and UFC.
10. Cloud or hosted deployment if you want access from phone/desktop.


## Professional UI

v1.1 adds a mobile-friendly dark analytics interface with:
- dashboard KPIs,
- ranked best-bet cards,
- compact mobile layouts,
- premium sidebar risk controls,
- redesigned tables,
- improved bet tracker and bankroll views.

The app remains fully functional on desktop and mobile browsers.
