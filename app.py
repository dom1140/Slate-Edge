from __future__ import annotations

from datetime import date, datetime, timezone
import html
import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from slate_edge.engine import build_recommendations, decimal_odds
from slate_edge.providers.mlb import MLBLineupProvider, MLBStatsProvider
from slate_edge.providers.odds import DemoOddsProvider, TheOddsAPIProvider
from slate_edge.providers.weather import OpenMeteoProvider
from slate_edge.predictive import load_model, update_current_season
from slate_edge.storage import BetStore, clv_percent

st.set_page_config(page_title="SlateEdge v2", page_icon="◆", layout="wide", initial_sidebar_state="collapsed")


def secret(name: str, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


DB_PATH = secret("DATABASE_PATH", str(Path(__file__).with_name("slate_edge.db")))
store = BetStore(DB_PATH)
MODEL_PATH = Path(__file__).with_name("model_artifact.json")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
:root { --ink:#f4f8f6; --muted:#91a59d; --line:#20342c; --card:#0e1b17; --green:#64f58d; --amber:#ffcc66; }
.stApp { background: radial-gradient(circle at 80% -10%,#15392b 0,transparent 34%),#07110e; color:var(--ink); }
html,body,[class*="css"] { font-family:'DM Sans',sans-serif; }
h1,h2,h3 { font-family:'Manrope',sans-serif!important; letter-spacing:-.04em!important; }
.block-container { max-width:1180px; padding-top:1.2rem; padding-bottom:6rem; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stMetric"] { background:rgba(14,27,23,.88); border:1px solid var(--line); padding:16px; border-radius:18px; }
[data-testid="stMetricLabel"] { color:var(--muted); }
.topbar { display:flex;justify-content:space-between;align-items:center;padding:8px 0 20px; }
.brand { font:800 22px Manrope;color:white;letter-spacing:-.05em }.brand span{color:var(--green)}
.live { font-size:12px;color:var(--green);background:#10271d;border:1px solid #27583b;border-radius:99px;padding:7px 10px }
.hero { border:1px solid var(--line);border-radius:26px;padding:26px;background:linear-gradient(145deg,rgba(18,42,33,.94),rgba(9,20,16,.94));margin-bottom:18px }
.eyebrow{color:var(--green);font:700 11px Manrope;letter-spacing:.14em;text-transform:uppercase}.hero h1{font-size:clamp(28px,5vw,48px);margin:7px 0}.sub{color:var(--muted);max-width:720px}
.gamecard { border:1px solid var(--line);border-radius:20px;background:rgba(14,27,23,.92);padding:18px;margin:11px 0;box-shadow:0 12px 40px rgba(0,0,0,.18) }
.gamehead { display:flex;justify-content:space-between;color:var(--muted);font-size:12px;margin-bottom:12px }.match{font:700 19px Manrope;margin-bottom:5px}.pick{color:var(--green)}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0}.chip{font-size:11px;padding:5px 8px;border-radius:99px;background:#162a22;color:#bad0c7}.confirmed{color:var(--green);border:1px solid #285b3b}.projected{color:var(--amber);border:1px solid #5c4b28}
.grid5{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:14px}.datum{background:#0a1512;border-radius:12px;padding:10px}.datum small{display:block;color:var(--muted);font-size:10px;text-transform:uppercase}.datum b{font:700 15px Manrope}.stake{color:var(--green)!important}
.warning { border:1px solid #5c4b28;background:#211c10;color:#f5d797;border-radius:13px;padding:11px 13px;font-size:13px;margin:9px 0 }
.footer-note{color:#71887e;font-size:12px;margin-top:20px}
div.stButton>button { border-radius:13px;border:1px solid #2f6a46;background:#153a29;color:white;font-weight:700;min-height:44px }
@media(max-width:700px){.block-container{padding:12px 14px 76px}.hero{padding:19px}.grid5{grid-template-columns:repeat(2,1fr)}.grid5 .datum:last-child{grid-column:span 2}.gamecard{padding:15px}.topbar{padding-bottom:10px}}
</style>
""", unsafe_allow_html=True)


def fmt_odds(value):
    return f"+{value}" if value > 0 else str(value)


def age_label(ts):
    if not ts: return "unknown"
    mins = max(0, int((datetime.now(timezone.utc) - ts).total_seconds() / 60))
    return "just now" if mins < 1 else f"{mins}m ago"


def esc(value):
    return html.escape(str(value))


if "refresh_nonce" not in st.session_state:
    st.session_state.refresh_nonce = 0

st.markdown('<div class="topbar"><div class="brand">SLATE<span>EDGE</span></div><div class="live">● MLB v2</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Risk controls")
    paper_test = st.toggle("Aggressive paper test", value=False,
                           help="Simulates aggressive stakes. It never unlocks real-money recommendations.")
    bankroll = st.number_input("Current bankroll", min_value=10.0, value=float(secret("STARTING_BANKROLL", 1000)), step=50.0)
    if paper_test:
        kelly_fraction, max_bet_pct, max_slate_pct = .50, .02, .08
        st.warning("PAPER ONLY · 50% Kelly · 2% max bet · 8% slate cap · stop after a 20% drawdown")
    else:
        kelly_fraction = st.select_slider("Fractional Kelly", options=[.10, .20, .25, .33, .50], value=.25, format_func=lambda x:f"{x:.0%}")
        max_bet_pct = st.slider("Max single bet", .005, .05, .015, .005, format="%.3f")
        max_slate_pct = st.slider("Max slate exposure", .01, .15, .06, .01, format="%.2f")
    min_edge = st.slider("Minimum edge", .0, .10, .025, .005, format="%.3f")
    st.caption("Stake recommendations are sizing outputs, not guarantees. Set limits you can afford to lose.")

tab_board, tab_portfolio, tab_log, tab_data = st.tabs(["Today", "Portfolio", "Log bet", "Data desk"])

with tab_board:
    st.markdown('<section class="hero"><div class="eyebrow">Decision desk · MLB</div><h1>Today’s slate, ranked by edge.</h1><div class="sub">Live schedule context, best available moneyline, transparent probability baseline, and bankroll-aware sizing in one scan.</div></section>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1: slate_date = st.date_input("Slate date", value=date.today())
    with c2: st.write(""); refresh = st.button("↻ Refresh all feeds", use_container_width=True)
    with c3: st.write(""); st.caption("Refreshes schedule, lineups, weather, odds and model")
    if refresh:
        st.cache_data.clear(); st.session_state.refresh_nonce += 1

    @st.cache_data(ttl=300, show_spinner=False)
    def load_slate(day_iso: str, odds_key: str, nonce: int):
        day = date.fromisoformat(day_iso)
        errors = []
        try:
            games = MLBStatsProvider().games(day)
        except Exception as exc:
            return [], [], [f"MLB schedule unavailable: {exc}"], False
        try: games = MLBLineupProvider().enrich(games)
        except Exception as exc: errors.append(f"Lineups: {exc}")
        try: games = OpenMeteoProvider().enrich(games)
        except Exception as exc: errors.append(f"Weather: {exc}")
        is_demo = not bool(odds_key)
        try:
            odds = (TheOddsAPIProvider(odds_key) if odds_key else DemoOddsProvider()).quotes(day, games)
        except Exception as exc:
            odds, is_demo = DemoOddsProvider().quotes(day, games), True
            errors.append(f"Live odds unavailable; using demo prices: {exc}")
        return games, odds, errors, is_demo

    odds_key = secret("ODDS_API_KEY", "")
    with st.spinner("Building today’s decision board…"):
        games, quotes, errors, is_demo = load_slate(slate_date.isoformat(), odds_key, st.session_state.refresh_nonce)
    model_context = update_current_season(load_model(MODEL_PATH), slate_date.year)
    recs = build_recommendations(games, quotes, bankroll, kelly_fraction, max_bet_pct, max_slate_pct, min_edge,
                                 model_context, paper_test=paper_test)
    qualifying = [r for r in recs if r.stake > 0]
    freshest = max((q.fetched_at for q in quotes), default=None)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Games", len(games)); m2.metric("Qualified plays", len(qualifying)); m3.metric("Total exposure", f"${sum(r.stake for r in qualifying):,.2f}"); m4.metric("Odds updated", age_label(freshest))
    if is_demo:
        st.markdown('<div class="warning">Demo odds are active. Add ODDS_API_KEY before treating prices, edges, EV, or stakes as live.</div>', unsafe_allow_html=True)
    if paper_test and not model_context.validated:
        st.markdown('<div class="warning">AGGRESSIVE PAPER TEST · Every displayed stake is simulated. No recommendation is approved for real money.</div>', unsafe_allow_html=True)
    elif not model_context.validated:
        st.markdown(f'<div class="warning">RESEARCH MODE · Wager sizing is locked. {esc(model_context.reason)}</div>', unsafe_allow_html=True)
    else:
        st.success(f"Validated model active · {model_context.version} · unseen-season gate passed")
    for error in errors: st.warning(error)
    if freshest and (datetime.now(timezone.utc) - freshest).total_seconds() > 600:
        st.markdown('<div class="warning">Odds are more than 10 minutes old. Refresh before making a decision.</div>', unsafe_allow_html=True)
    if not games: st.info("No MLB games found for this date, or the public schedule feed is unavailable.")
    display_recs = qualifying or recs[:8]
    for r in display_recs:
        g = r.game
        lineup_class = "confirmed" if g.home_lineup_status == g.away_lineup_status == "CONFIRMED" else "projected"
        weather = "Weather pending" if g.weather.temperature_f is None else f"{g.weather.temperature_f:.0f}°F · wind {g.weather.wind_mph:.0f} mph · rain {g.weather.precipitation_probability:.0f}%"
        stake_label = "PASS" if r.stake <= 0 else f"PAPER ${r.stake:,.2f}" if r.simulated else f"${r.stake:,.2f}"
        card = f'''<article class="gamecard"><div class="gamehead"><span>{g.start_time.astimezone().strftime('%-I:%M %p') if os.name != 'nt' else g.start_time.astimezone().strftime('%I:%M %p').lstrip('0')} · {esc(g.venue)}</span><span>Odds {age_label(r.quote_fetched_at)}</span></div><div class="match">{esc(g.away.abbreviation)} <span style="color:#60786e">@</span> {esc(g.home.abbreviation)} · <span class="pick">{esc(r.selection)}</span></div><div style="color:#91a59d;font-size:13px">{esc(g.away_pitcher.name)} vs {esc(g.home_pitcher.name)} · {esc(weather)}</div><div class="chips"><span class="chip {lineup_class}">{esc(g.away.abbreviation)} {esc(g.away_lineup_status)}</span><span class="chip {lineup_class}">{esc(g.home.abbreviation)} {esc(g.home_lineup_status)}</span><span class="chip">{esc(r.sportsbook)}</span><span class="chip">{esc(r.confidence)}</span></div><div class="grid5"><div class="datum"><small>Best line</small><b>{fmt_odds(r.odds)}</b></div><div class="datum"><small>Market</small><b>{r.market_probability:.1%}</b></div><div class="datum"><small>Model</small><b>{r.model_probability:.1%}</b></div><div class="datum"><small>Edge / EV</small><b>{r.edge:+.1%} / {r.expected_value:+.1%}</b></div><div class="datum"><small>{r.grade} · Stake</small><b class="stake">{stake_label}</b></div></div></article>'''
        st.markdown(card, unsafe_allow_html=True)
        with st.expander("Why this number"):
            st.write(" • ".join(r.reasons))
            if model_context.validated:
                st.caption(f"Holdout metrics: {model_context.metrics}. Historical results do not guarantee future performance.")
            else:
                st.caption("Research output only. Exact stakes remain locked until the unseen-season validation gate passes.")
            if r.simulated and r.stake > 0:
                st.caption("Simulation only; this stake cannot be logged as an approved wager.")
            if r.stake > 0 and not r.simulated and st.button(f"Log {r.selection} · ${r.stake:.2f}", key=f"log-{g.id}-{r.selection}"):
                store.add(placed_at=datetime.now(timezone.utc).isoformat(), sport=g.sport, event=f"{g.away.name} @ {g.home.name}", selection=r.selection, market="Moneyline", sportsbook=r.sportsbook, odds=r.odds, stake=r.stake, model_probability=r.model_probability, edge=r.edge, notes="Logged from decision board")
                st.success("Bet added to portfolio.")

with tab_portfolio:
    st.subheader("Performance & CLV")
    frame = store.frame()
    if frame.empty:
        st.info("No bets logged yet. Add a recommendation or use Log bet.")
    else:
        settled = frame[frame.result != "OPEN"].copy()
        total_staked = float(settled.stake.sum()) if not settled.empty else 0
        profit = float((settled.payout - settled.stake).sum()) if not settled.empty else 0
        wins = int((settled.result == "WIN").sum())
        losses = int((settled.result == "LOSS").sum())
        frame["CLV %"] = frame.apply(lambda x: clv_percent(int(x.odds), int(x.closing_odds) if pd.notna(x.closing_odds) else None), axis=1)
        a,b,c,d = st.columns(4)
        a.metric("Net P/L", f"${profit:,.2f}"); b.metric("ROI", f"{profit/total_staked:.1%}" if total_staked else "—"); c.metric("Record", f"{wins}-{losses}"); d.metric("Avg CLV", f"{frame['CLV %'].mean():+.2f}%" if frame["CLV %"].notna().any() else "—")
        chronological = frame.iloc[::-1].copy(); chronological["Net"] = chronological.payout - chronological.stake; chronological["Bankroll curve"] = bankroll + chronological.Net.cumsum()
        fig = px.area(chronological, x="placed_at", y="Bankroll curve", template="plotly_dark", color_discrete_sequence=["#64F58D"])
        fig.update_layout(height=290, margin=dict(l=5,r=5,t=20,b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button("Export bet history CSV", frame.to_csv(index=False), "slateedge_bets.csv", "text/csv")
        open_bets = frame[frame.result == "OPEN"]
        if not open_bets.empty:
            st.markdown("#### Settle an open bet")
            choice = st.selectbox("Bet", open_bets.id.tolist(), format_func=lambda x: f"#{x} · {open_bets.loc[open_bets.id==x,'selection'].iloc[0]}")
            x,y,z = st.columns(3)
            result = x.selectbox("Result", ["WIN","LOSS","PUSH"])
            payout = y.number_input("Total returned", min_value=0.0, step=1.0)
            closing = z.number_input("Closing odds", value=0, step=5)
            if st.button("Save result"):
                store.settle(int(choice), result, payout, int(closing) if closing else None); st.success("Result saved. Refresh this tab to update metrics.")

with tab_log:
    st.subheader("Log a wager")
    with st.form("manual_bet", clear_on_submit=True):
        a,b = st.columns(2)
        event = a.text_input("Event", placeholder="DET @ CLE")
        selection = b.text_input("Selection", placeholder="Detroit ML")
        c,d,e = st.columns(3)
        odds = c.number_input("American odds", value=-110, step=5)
        stake = d.number_input("Stake", min_value=0.01, value=10.0)
        sportsbook = e.text_input("Sportsbook", value="Manual")
        notes = st.text_area("Notes")
        if st.form_submit_button("Add to portfolio", use_container_width=True):
            store.add(placed_at=datetime.now(timezone.utc).isoformat(), sport="MLB", event=event, selection=selection, market="Moneyline", sportsbook=sportsbook, odds=int(odds), stake=stake, model_probability=None, edge=None, notes=notes)
            st.success("Bet logged.")

with tab_data:
    st.subheader("Data desk")
    st.markdown("""
**Active adapters**

- Schedule and probable pitchers: public MLB Stats API, refresh on open and every 5 minutes.
- Official batting orders: MLB live game feed; marked **confirmed** only after a complete order appears.
- Weather: Open-Meteo hourly forecast for mapped MLB parks.
- Odds: The Odds API when configured; otherwise unmistakably labeled demo prices.
- Injuries: adapter slot reserved. No free feed in this build is treated as complete enough for wagering decisions.

**Recalculation triggers**

Opening the app, pressing **Refresh all feeds**, or expiration of the five-minute cache reloads inputs and recomputes every recommendation. A scheduled worker is required for alerts while nobody has the Streamlit page open.

**Model safety gate**

The paid historical pipeline trains on 2024 and evaluates once on 2025. Wager sizing unlocks only if the frozen model beats the no-vig market on Brier score and log loss, produces at least 100 qualifying holdout wagers, and has positive flat-stake holdout ROI. A failed gate cannot be overridden from the UI.
""")
    st.caption("Provider failures degrade visibly. SlateEdge never relabels demo or stale data as live.")

st.markdown('<div class="footer-note">SlateEdge is an analytics and record-keeping tool, not a sportsbook or a promise of profit. Confirm prices and availability at your book. If betting stops being fun or affordable, stop.</div>', unsafe_allow_html=True)
