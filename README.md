# SlateEdge v2

An MLB-first, mobile-oriented Streamlit decision desk for daily slates, contextual data, live odds, transparent model outputs, bankroll-aware stake sizing, bet history, and closing-line value.

> SlateEdge does not place bets and does not guarantee profit. The bundled model is a transparent, market-anchored baseline intended for product testing. Do not treat it as a validated predictive advantage without historical training, calibration, and walk-forward backtesting.

## What v2 includes

- Automatic MLB schedule and probable-pitcher loading from the public MLB Stats API
- Official-game-feed lineup checks with PROJECTED / CONFIRMED labels
- Open-Meteo ballpark forecasts
- Live multi-book moneylines through The Odds API when a key is supplied
- Clearly labeled deterministic demo odds when no key is supplied
- Five-minute refresh-on-open cache, manual all-feed refresh, freshness labels, and stale warnings
- Automatic recalculation of no-vig market probability, model probability, edge, EV, fractional Kelly, grade, exact stake, and slate exposure cap
- Local SQLite bet history, settlement, bankroll curve, ROI, CSV export, and CLV
- Provider interfaces that keep schedule, odds, context, model, and storage replaceable
- Paid historical-odds training workflow with a frozen later-season validation set
- Non-bypassable research/validated model gate: bankroll sizing remains locked after a failed backtest

## Run locally

Use Python 3.11 or 3.12.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

On macOS/Linux, activation is `source .venv/bin/activate`.

## Secrets

Create `.streamlit/secrets.toml` locally (it is ignored by Git):

```toml
ODDS_API_KEY = "your-the-odds-api-key"
STARTING_BANKROLL = 1000
DATABASE_PATH = "slate_edge.db"
```

Only `ODDS_API_KEY` is needed for live prices. MLB schedule/lineup context and Open-Meteo need no key. Never commit `secrets.toml`.

## Training and validation

The manual GitHub Actions workflow in `.github/workflows/train-model.yml` uses a separate
`HISTORICAL_ODDS_API_KEY` repository secret. It downloads three pregame snapshots per MLB day,
caches the normalized source responses, trains on 2024, and evaluates the frozen model on 2025.

The live app unlocks stakes only when the artifact satisfies every holdout gate:

- at least 1,800 matched unseen games;
- Brier score beats the no-vig market by at least 0.0005;
- log loss beats the no-vig market by at least 0.001;
- at least 100 wagers meet the 2.5-point edge threshold;
- positive realized flat-stake ROI at the captured available prices.

Passing those gates is evidence, not a guarantee. A failed gate writes an artifact that keeps the
app in **RESEARCH MODE**. The UI cannot override that lock.

## GitHub + Streamlit Community Cloud

1. Create a GitHub repository and upload the **contents** of this folder so `app.py` is at the repository root.
2. In Streamlit Community Cloud, choose **Create app**, select the repository and `main` branch, and set the main file path to `app.py`.
3. Open **Advanced settings → Secrets** and paste:

   ```toml
   ODDS_API_KEY = "your-key"
   STARTING_BANKROLL = 1000
   ```

4. Deploy. On iPhone, open the app URL in Safari and choose **Share → Add to Home Screen**.

### Persistence warning

SQLite is durable locally, but Streamlit Community Cloud's filesystem is not a permanent database. Export the CSV regularly during testing. Before relying on months of history, replace `BetStore` with a managed Postgres/Supabase adapter. The storage boundary is isolated in `slate_edge/storage.py` for that migration.

## Background monitoring next step

Streamlit reruns only when the app is opened, interacted with, or externally awakened; it is not a dependable always-on monitor. The production next step is a scheduled worker (GitHub Actions cron, Cloudflare Worker, Render cron, or similar) that:

1. fetches schedule, odds, pitcher, lineup, injury, and weather providers every 2–5 minutes near first pitch;
2. snapshots normalized inputs in managed Postgres;
3. runs the versioned model and records recommendation changes;
4. sends a push/email notification when a lineup scratch, pitcher change, material line move, stale feed, or BET→PASS transition occurs;
5. leaves Streamlit as the read/write dashboard over the same database.

For injuries and projected lineups before official orders post, use a licensed provider with explicit coverage/SLA. Add it behind `ContextProvider`; do not scrape or silently treat an incomplete free source as authoritative.

## Model v2 roadmap and data integrity

The training pipeline now matches each quote to the nearest event start (including doubleheaders), rejects stale and market-outlier books, requires at least three agreeing books, and records the pregame decision window in the model artifact. Offseason team ratings are regressed toward league average before current-season updates.

The predictive interface has explicit slots for starting-pitcher quality, bullpen availability, confirmed-lineup value, platoon matchups, Statcast contact quality, defense/catching, park-weather interaction, and travel/rest. Missing inputs remain `unavailable` rather than being silently treated as real observations. These fields do not affect wagers until their coefficients are trained and pass a new forward holdout; the previously inspected 2025 set must not be reused as the final approval test.

## Product research translated into original patterns

- **[Action Network](https://www.actionnetwork.com/app/):** scan-first Today board, real-time odds/status, and unified bet tracking.
- **[Rithmm](https://www.rithmm.com/):** model probability plus plain-language reasoning rather than an unexplained pick.
- **[Pikkit](https://pikkit.com/features) / [Juice Reel](https://www.juicereel.com/download/android):** portfolio truth, ROI, history, and verified/automatic tracking as a primary surface.
- **[Unabated](https://unabated.com/articles/learn-about-the-game-odds-screen):** best-line emphasis, freshness/latency, line movement, no-vig thinking, and green visual treatment for positive edges.

SlateEdge uses those general information-design patterns with original code, styling, naming, and assets.
