import streamlit as st
import pandas as pd
from pathlib import Path
from core import (
    implied_probability, no_vig_two_way_prob, capped_fractional_kelly,
    mlb_market_adjusted_probability
)
from db import (
    init_db, get_bankroll, add_bankroll_adjustment, add_bet,
    bets_df, settle_bet, analytics
)

st.set_page_config(
    page_title="SlateEdge",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Premium UI ----------
st.markdown("""
<style>
:root {
    --bg: #0b0f17;
    --panel: #111827;
    --panel2: #161f2e;
    --border: #263247;
    --text: #f8fafc;
    --muted: #94a3b8;
    --accent: #7c3aed;
    --accent2: #22c55e;
    --warn: #f59e0b;
    --danger: #ef4444;
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 15% 10%, rgba(124,58,237,0.14), transparent 25%),
        radial-gradient(circle at 85% 0%, rgba(34,197,94,0.08), transparent 20%),
        var(--bg);
    color: var(--text);
}

.block-container {
    max-width: 1400px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #0b1220 100%);
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * {
    color: var(--text);
}

h1, h2, h3 {
    letter-spacing: -0.02em;
}

.hero {
    padding: 1.25rem 1.4rem;
    border: 1px solid rgba(124,58,237,.35);
    border-radius: 20px;
    background:
        linear-gradient(135deg, rgba(124,58,237,.16), rgba(17,24,39,.94) 48%, rgba(34,197,94,.07));
    box-shadow: 0 20px 70px rgba(0,0,0,.25);
    margin-bottom: 1rem;
}

.hero-kicker {
    color: #c4b5fd;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .14em;
    text-transform: uppercase;
}

.hero-title {
    font-size: 2.1rem;
    font-weight: 800;
    margin: .15rem 0 .25rem;
}

.hero-sub {
    color: var(--muted);
    margin: 0;
    font-size: .98rem;
}

.glass-card {
    background: linear-gradient(180deg, rgba(22,31,46,.92), rgba(17,24,39,.92));
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1rem 1.05rem;
    box-shadow: 0 12px 40px rgba(0,0,0,.18);
}

.metric-label {
    color: var(--muted);
    font-size: .76rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 700;
}

.metric-value {
    color: var(--text);
    font-weight: 800;
    font-size: 1.55rem;
    margin-top: .2rem;
}

.metric-positive {
    color: #86efac;
}

.metric-negative {
    color: #fca5a5;
}

div[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(22,31,46,.95), rgba(17,24,39,.95));
    border: 1px solid var(--border);
    padding: .9rem 1rem;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0,0,0,.16);
}

div[data-testid="stMetricLabel"] {
    color: var(--muted);
}

div[data-testid="stMetricValue"] {
    color: var(--text);
}

.stTabs [data-baseweb="tab-list"] {
    gap: .45rem;
    background: rgba(15,23,42,.55);
    border: 1px solid var(--border);
    padding: .35rem;
    border-radius: 14px;
}

.stTabs [data-baseweb="tab"] {
    height: 42px;
    border-radius: 10px;
    color: #cbd5e1;
    padding-left: .9rem;
    padding-right: .9rem;
}

.stTabs [aria-selected="true"] {
    background: rgba(124,58,237,.18) !important;
    color: white !important;
}

.stButton > button {
    border-radius: 12px;
    border: 1px solid rgba(124,58,237,.55);
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    color: white;
    font-weight: 700;
    min-height: 42px;
    box-shadow: 0 8px 22px rgba(124,58,237,.18);
}

.stButton > button:hover {
    border-color: #a78bfa;
    transform: translateY(-1px);
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
}

[data-testid="stFileUploader"] {
    background: rgba(17,24,39,.65);
    border: 1px dashed #475569;
    border-radius: 16px;
    padding: .4rem;
}

div[data-baseweb="select"] > div,
input, textarea {
    border-radius: 12px !important;
}

.pro-badge {
    display: inline-block;
    font-size: .72rem;
    font-weight: 800;
    padding: .25rem .55rem;
    border-radius: 999px;
    color: #ddd6fe;
    background: rgba(124,58,237,.18);
    border: 1px solid rgba(124,58,237,.4);
    margin-left: .35rem;
}

.edge-good {
    color: #86efac;
    font-weight: 800;
}

.edge-pass {
    color: #94a3b8;
    font-weight: 700;
}

.small-note {
    color: var(--muted);
    font-size: .84rem;
}

@media (max-width: 700px) {
    .block-container {
        padding-left: .75rem;
        padding-right: .75rem;
        padding-top: .65rem;
    }
    .hero {
        padding: 1rem;
        border-radius: 16px;
    }
    .hero-title {
        font-size: 1.65rem;
    }
    .hero-sub {
        font-size: .9rem;
    }
    div[data-testid="stMetric"] {
        padding: .7rem .75rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding-left: .55rem;
        padding-right: .55rem;
        font-size: .8rem;
    }
}
</style>
""", unsafe_allow_html=True)

init_db(1000)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">Sports betting analytics</div>
  <div class="hero-title">SlateEdge <span class="pro-badge">PRO</span></div>
  <p class="hero-sub">Model the edge. Size the risk. Track the result.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Risk Controls")
    st.caption("Conservative defaults designed for bankroll preservation.")
    kelly_mult = st.select_slider(
        "Kelly fraction",
        options=[0.10,0.15,0.20,0.25,0.33,0.50],
        value=0.25,
        help="Quarter Kelly is the default."
    )
    max_bet_pct = st.slider("Max single bet", 0.5, 3.0, 1.5, 0.1) / 100
    daily_cap_pct = st.slider("Max slate exposure", 2.0, 12.0, 6.0, 0.5) / 100
    min_edge_pp = st.slider("Minimum edge (pp)", 0.0, 8.0, 2.5, 0.5)

    st.divider()
    st.markdown("#### Risk profile")
    risk_name = "Conservative" if kelly_mult <= .25 and max_bet_pct <= .015 else "Moderate"
    st.write(f"**{risk_name}**")
    st.caption(f"{kelly_mult:.2f} Kelly • {max_bet_pct*100:.1f}% max bet • {daily_cap_pct*100:.1f}% slate cap")

bankroll = get_bankroll()
a = analytics()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Bankroll", f"${bankroll:,.2f}")
c2.metric("Settled P/L", f"${a['profit']:,.2f}")
c3.metric("ROI", f"{a['roi']*100:.1f}%")
c4.metric("Win rate", f"{a['win_rate']*100:.1f}%")

tabs = st.tabs(["Dashboard", "MLB Lab", "Bet Tracker", "Bankroll", "Methodology"])

with tabs[0]:
    st.markdown("### Today's Slate")
    st.caption("Rank the slate by model edge, expected value, and bankroll-adjusted stake.")
    sample_path = Path(__file__).with_name("sample_mlb_slate.csv")

    top1, top2 = st.columns([1.5,1])
    with top1:
        use_sample = st.checkbox("Use included MLB test slate", value=True)
    with top2:
        up = st.file_uploader("Upload slate CSV", type=["csv"], label_visibility="collapsed")

    if up is not None:
        slate = pd.read_csv(up)
    elif use_sample:
        slate = pd.read_csv(sample_path)
    else:
        slate = pd.DataFrame()

    if not slate.empty:
        rows = []
        for _, r in slate.iterrows():
            odds = float(r["odds"])
            opp = float(r["opposite_odds"])
            market_fair, _ = no_vig_two_way_prob(odds, opp)
            model_prob = float(r["model_prob"])
            x = capped_fractional_kelly(
                bankroll, model_prob, odds,
                kelly_multiplier=kelly_mult,
                max_bet_pct=max_bet_pct,
                min_edge_pp=min_edge_pp,
                market_fair_prob=market_fair
            )
            rows.append({
                **r.to_dict(),
                "market_fair_prob": market_fair,
                "edge_pp": x["edge_pp"],
                "ev_roi": x["ev_roi"],
                "grade": x["grade"],
                "raw_stake": x["stake"],
            })

        out = pd.DataFrame(rows)
        total_raw = out["raw_stake"].sum()
        slate_cap = bankroll * daily_cap_pct
        scale = min(1.0, slate_cap/total_raw) if total_raw > 0 else 1.0
        out["recommended_stake"] = (out["raw_stake"] * scale).round(2)
        out["implied_prob"] = out["odds"].apply(implied_probability)
        out["edge_pp"] = out["edge_pp"].round(2)
        out["ev_roi_pct"] = (out["ev_roi"]*100).round(2)
        out["market_fair_pct"] = (out["market_fair_prob"]*100).round(1)
        out["model_prob_pct"] = (out["model_prob"]*100).round(1)

        picks = out[out["recommended_stake"] > 0].copy().sort_values(
            ["recommended_stake","edge_pp"], ascending=False
        )

        s1,s2,s3 = st.columns(3)
        s1.metric("Qualified bets", f"{len(picks)}")
        s2.metric("Recommended exposure", f"${picks['recommended_stake'].sum():.2f}")
        s3.metric("Exposure %", f"{(picks['recommended_stake'].sum()/bankroll*100 if bankroll else 0):.1f}%")

        show_cols = [
            "event","market","selection","odds","market_fair_pct",
            "model_prob_pct","edge_pp","ev_roi_pct","grade","recommended_stake"
        ]
        styled = out[show_cols].sort_values(
            ["recommended_stake","edge_pp"], ascending=False
        ).rename(columns={
            "event":"Event",
            "market":"Market",
            "selection":"Pick",
            "odds":"Odds",
            "market_fair_pct":"Market %",
            "model_prob_pct":"Model %",
            "edge_pp":"Edge pp",
            "ev_roi_pct":"EV %",
            "grade":"Grade",
            "recommended_stake":"Bet $"
        })

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Odds": st.column_config.NumberColumn(format="%+d"),
                "Market %": st.column_config.NumberColumn(format="%.1f%%"),
                "Model %": st.column_config.NumberColumn(format="%.1f%%"),
                "Edge pp": st.column_config.NumberColumn(format="%.2f"),
                "EV %": st.column_config.NumberColumn(format="%.2f%%"),
                "Bet $": st.column_config.NumberColumn(format="$%.2f"),
            }
        )

        if len(picks):
            st.markdown("### Best Bets")
            for i, (_, r) in enumerate(picks.head(3).iterrows(), 1):
                left, mid, right = st.columns([2.4,1.2,1])
                with left:
                    st.markdown(f"**#{i} — {r['selection']}**  \n{r['event']} • {r['market']} • {int(r['odds']):+d}")
                with mid:
                    st.markdown(f"**Edge:** {r['edge_pp']:.2f} pp  \n**EV:** {r['ev_roi_pct']:.2f}%")
                with right:
                    st.markdown(f"**Grade {r['grade']}**  \n### ${r['recommended_stake']:.2f}")
                st.divider()

            selected = st.multiselect(
                "Log recommendations",
                options=list(picks.index),
                format_func=lambda i: f"{picks.loc[i,'selection']} {int(picks.loc[i,'odds']):+d} — ${picks.loc[i,'recommended_stake']:.2f}"
            )
            if st.button("Add selected bets to tracker", use_container_width=True):
                for i in selected:
                    r = picks.loc[i]
                    add_bet({
                        "sport": r["sport"], "event_date": r["event_date"],
                        "event": r["event"], "market": r["market"],
                        "selection": r["selection"], "odds": float(r["odds"]),
                        "stake": float(r["recommended_stake"]),
                        "model_prob": float(r["model_prob"]),
                        "market_fair_prob": float(r["market_fair_prob"]),
                        "edge_pp": float(r["edge_pp"]),
                        "ev_roi": float(r["ev_roi"]),
                        "notes": "Added from Slate Analyzer",
                    })
                st.success(f"Added {len(selected)} bet(s).")
                st.rerun()

        st.caption(
            f"Slate cap: ${slate_cap:.2f}. Recommendations are scaled if total raw Kelly sizing exceeds the cap."
        )

with tabs[1]:
    st.markdown("### MLB Matchup Lab")
    st.caption("Use the market as the baseline, then layer in matchup information.")

    col1,col2,col3 = st.columns(3)
    with col1:
        st.markdown("#### Market")
        side = st.text_input("Selection", "Example Team")
        odds = st.number_input("Selection odds", value=-120, step=5)
        opp_odds = st.number_input("Opposite side odds", value=110, step=5)

    market_fair, _ = no_vig_two_way_prob(float(odds), float(opp_odds))

    with col2:
        st.markdown("#### Core edges")
        starter = st.slider("Starting pitcher", -10, 10, 0)
        offense = st.slider("Offense", -10, 10, 0)
        bullpen = st.slider("Bullpen", -10, 10, 0)
        lineup = st.slider("Confirmed lineup", -10, 10, 0)

    with col3:
        st.markdown("#### Context edges")
        defense = st.slider("Defense / baserunning", -10, 10, 0)
        park = st.slider("Park / weather", -10, 10, 0)
        home = st.slider("Home / rest / travel", -10, 10, 0)

    p = mlb_market_adjusted_probability(
        market_fair, starter, offense, bullpen, defense, park, lineup, home
    )
    rec = capped_fractional_kelly(
        bankroll, p, float(odds),
        kelly_multiplier=kelly_mult,
        max_bet_pct=max_bet_pct,
        min_edge_pp=min_edge_pp,
        market_fair_prob=market_fair
    )

    x1,x2,x3,x4 = st.columns(4)
    x1.metric("Market fair", f"{market_fair*100:.1f}%")
    x2.metric("Model probability", f"{p*100:.1f}%")
    x3.metric("Estimated edge", f"{rec['edge_pp']:.2f} pp")
    x4.metric("Recommended stake", f"${rec['stake']:.2f}")

    st.markdown(
        f"**Grade {rec['grade']}** • Estimated ROI **{rec['ev_roi']*100:.2f}%** • "
        f"Full Kelly **{rec['full_kelly']*100:.2f}%**"
    )
    st.caption("The current MLB lab is a transparent test framework, not a trained predictive model.")

with tabs[2]:
    st.markdown("### Bet Tracker")
    df = bets_df()

    if df.empty:
        st.info("No bets tracked yet.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "stake": st.column_config.NumberColumn(format="$%.2f"),
                "profit": st.column_config.NumberColumn(format="$%.2f"),
                "model_prob": st.column_config.NumberColumn(format="%.3f"),
                "market_fair_prob": st.column_config.NumberColumn(format="%.3f"),
                "ev_roi": st.column_config.NumberColumn(format="%.3f"),
            }
        )

        open_df = df[df["result"]=="OPEN"]
        if not open_df.empty:
            st.markdown("#### Settle an open bet")
            ids = open_df["id"].tolist()
            bet_id = st.selectbox(
                "Open bet",
                ids,
                format_func=lambda x: f"#{x} — {open_df.loc[open_df['id']==x,'selection'].iloc[0]}"
            )
            r1,r2 = st.columns(2)
            with r1:
                result = st.selectbox("Result", ["WIN","LOSS","PUSH"])
            with r2:
                closing = st.number_input("Closing odds (0 = blank)", value=0, step=5)

            if st.button("Settle bet", use_container_width=True):
                settle_bet(int(bet_id), result, None if closing == 0 else float(closing))
                st.success("Bet settled.")
                st.rerun()

        settled = df[df["result"]!="OPEN"].copy()
        if not settled.empty and settled["closing_odds"].notna().any():
            st.markdown("#### Closing-line tracking")
            st.dataframe(
                settled[["event_date","event","selection","odds","closing_odds","result","profit"]],
                use_container_width=True, hide_index=True
            )

with tabs[3]:
    st.markdown("### Bankroll Management")
    st.caption("Deposits, withdrawals, and settled bet P/L automatically roll into your bankroll.")
    b1,b2 = st.columns(2)
    with b1:
        amt = st.number_input("Adjustment amount", value=0.0, step=10.0)
    with b2:
        reason = st.text_input("Reason", "Deposit / withdrawal")

    if st.button("Apply bankroll adjustment", use_container_width=True):
        if amt != 0:
            add_bankroll_adjustment(float(amt), reason)
            st.success("Bankroll updated.")
            st.rerun()

with tabs[4]:
    st.markdown("### Methodology")
    st.markdown("""
**Market baseline**  
Two-sided prices are converted into no-vig fair probabilities.

**Model edge**  
SlateEdge compares your model probability with the market's fair probability.

**Expected value filter**  
A wager must clear both your minimum edge threshold and positive expected value.

**Fractional Kelly**  
Default sizing is quarter Kelly with a hard single-bet cap.

**Slate exposure control**  
If all recommended wagers combined exceed the slate cap, stakes are scaled down proportionally.

**Tracking**  
Every logged bet can store model probability, market fair probability, edge, EV, closing odds, result and P/L.
""")
    st.warning(
        "A staking system cannot turn a bad predictive model into a profitable one. "
        "The next major upgrade should be a historically trained and backtested MLB probability model."
    )
