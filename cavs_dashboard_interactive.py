import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Cavs Ticket Sales – Forecast & Pacing", layout="wide")
st.title("🏀 Cleveland Cavaliers Ticket Sales – Forecast & Pacing Dashboard")
st.caption("Real pacing + interactive forecasting powered by **Cavs Tickets.csv**")

GOAL_TICKETS = 2500

# ==============================
# HELPERS
# ==============================
def minmax_scale_dict(values_dict, lo=0.75, hi=1.25):
    """Scale dictionary values linearly to [lo, hi]."""
    if not values_dict or len(values_dict) == 0:
        return {}
    
    keys = list(values_dict.keys())
    vals = np.array([values_dict[k] for k in keys], dtype=float)
    vals = np.nan_to_num(vals, nan=1.0)
    
    vmin, vmax = float(np.min(vals)), float(np.max(vals))
    if vmax - vmin < 1e-12:
        return {k: 1.0 for k in keys}
    
    scaled = lo + (vals - vmin) * (hi - lo) / (vmax - vmin)
    return {k: float(s) for k, s in zip(keys, scaled)}


def scenario_cum_share(day, txns, avg_tix, tier_w, give_w, dow_w):
    """Map scenario controls to plausible cumulative-share (0–1)."""
    norm_day  = np.clip(day / 240.0, 0, 1)
    norm_txns = np.clip(txns / 1000.0, 0, 1)
    norm_avg  = np.clip(avg_tix / 6.0, 0, 1)
    norm_tier = np.clip((tier_w - 0.75) / 0.5, 0, 1)
    norm_give = np.clip((give_w - 0.75) / 0.5, 0, 1)
    norm_dow  = np.clip((dow_w  - 0.75) / 0.5, 0, 1)

    momentum = (
        0.40 * norm_day +
        0.20 * norm_txns +
        0.15 * norm_avg +
        0.15 * norm_tier +
        0.05 * norm_give +
        0.05 * norm_dow
    )
    return float(np.clip(momentum, 0.02, 0.999))

# ==============================
# LOAD DATA
# ==============================
@st.cache_data
def load_data(path="Cavs Tickets.csv"):
    """Load and preprocess Cavs ticket sales data."""
    if not Path(path).exists():
        return None, f"File not found: {path}"

    try:
        df = pd.read_csv(path)
    except Exception as e:
        return None, f"Error reading CSV: {e}"

    required_cols = ["days_since_onsale", "daily_tickets"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return None, f"Missing required columns: {missing_cols}"

    # Clean and validate
    df["days_since_onsale"] = pd.to_numeric(df["days_since_onsale"], errors="coerce")
    df["daily_tickets"] = pd.to_numeric(df["daily_tickets"], errors="coerce")
    df = df.dropna(subset=["days_since_onsale", "daily_tickets"])
    df = df[df["days_since_onsale"] >= 0]
    df = df[df["daily_tickets"] >= 0]
    if df.empty:
        return None, "No valid rows after cleaning."

    if "event_name" not in df.columns:
        df["event_name"] = "Event_" + df.index.astype(str)

    # ✅ Fixed optional column handling
    for col, default in [("tier", "Unknown"), ("giveaway", "None"), ("day_of_sale", "Unknown")]:
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)

    df = df.sort_values(["event_name", "days_since_onsale"])
    df["cum_tickets"] = df.groupby("event_name")["daily_tickets"].cumsum()
    df["total_tickets"] = df.groupby("event_name")["daily_tickets"].transform("sum")
    df["cum_share"] = np.where(df["total_tickets"] > 0, df["cum_tickets"] / df["total_tickets"], 0)
    df["cum_share"] = df["cum_share"].clip(0, 1)

    evt_window = df.groupby("event_name")["days_since_onsale"].max().rename("event_sales_window")
    df = df.merge(evt_window, on="event_name", how="left")

    def bucket(win):
        if pd.isna(win):
            return "Unknown"
        if win <= 30: return "Short (1–30)"
        if win <= 90: return "Medium (31–90)"
        return "Long (91–150+)"

    df["sales_window_group"] = df["event_sales_window"].apply(bucket)
    return df, None

df, error = load_data()

if error or df is None:
    st.error(f"⚠️ Could not load Cavs Tickets.csv: {error}")
    st.stop()

# ==============================
# DATA-DRIVEN WEIGHTS
# ==============================
@st.cache_data
def compute_weights(df):
    """Compute weights for tier, giveaway, and day_of_week."""
    base = max(df["daily_tickets"].mean(), 1.0)
    tier_raw = (df.groupby("tier")["daily_tickets"].mean() / base).to_dict()
    giveaway_raw = (df.groupby("giveaway")["daily_tickets"].mean() / base).to_dict()
    dow_raw = (df.groupby("day_of_sale")["daily_tickets"].mean() / base).to_dict()

    tier_w = minmax_scale_dict(tier_raw, 0.75, 1.25)
    give_w = minmax_scale_dict(giveaway_raw, 0.75, 1.25)
    dow_w = minmax_scale_dict(dow_raw, 0.75, 1.25)

    defaults = {
        "tier": ["A+", "A", "B", "C", "D", "Unknown"],
        "giveaway": ["None", "T-Shirt", "Bobblehead", "Poster", "Unknown"],
        "dow": ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Unknown"]
    }
    for k in defaults["tier"]: tier_w.setdefault(k, 1.0)
    for k in defaults["giveaway"]: give_w.setdefault(k, 1.0)
    for k in defaults["dow"]: dow_w.setdefault(k, 1.0)
    return tier_w, give_w, dow_w

tier_weight, giveaway_weight, dow_weight = compute_weights(df)

# ==============================
# PRECOMPUTE PACING CURVES
# ==============================
@st.cache_data
def precompute_pacing(df):
    pacing = (
        df.groupby(["sales_window_group", "days_since_onsale"])["cum_share"]
        .quantile([0.25, 0.5, 0.75])
        .unstack()
        .reset_index()
        .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
        .dropna(subset=["median"])
    )
    pacing = pacing.sort_values(["sales_window_group", "days_since_onsale"])
    # Enforce cumulative monotonicity
    for g in pacing["sales_window_group"].unique():
        mask = pacing["sales_window_group"] == g
        for col in ["p25", "median", "p75"]:
            pacing.loc[mask, col] = pacing.loc[mask, col].cummax()
    return pacing

pacing_all = precompute_pacing(df)

# ==============================
# SIDEBAR CONTROLS
# ==============================
st.sidebar.header("🎮 Scenario Controls")

window_group = st.sidebar.selectbox(
    "Sales Window Group (cohort for pacing)",
    ["All Games", "Short (1–30)", "Medium (31–90)", "Long (91–150+)"],
    index=0
)

sales_window = st.sidebar.slider("Days on Sale (before game)", 0, 240, 60, 10)
txns = st.sidebar.slider("Number of Transactions (buyers)", 50, 1000, 400, 10)
avg_tix_per_txn = st.sidebar.slider("Avg Tickets per Transaction", 1.0, 6.0, 3.0, 0.5)
tier = st.sidebar.selectbox("Game Tier", sorted(tier_weight.keys()))
giveaway = st.sidebar.selectbox("Giveaway Type", sorted(giveaway_weight.keys()))
day_of_week = st.sidebar.selectbox("Day of Week", ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], index=5)

# ==============================
# BUILD PACING CURVE
# ==============================
if window_group == "All Games":
    pacing = pacing_all.groupby("days_since_onsale")[["p25","median","p75"]].mean().reset_index()
else:
    pacing = pacing_all[pacing_all["sales_window_group"] == window_group].copy()

if pacing.empty:
    st.warning(f"No pacing data for {window_group}. Try 'All Games'.")
    st.stop()

# ==============================
# FORECAST CALCULATION
# ==============================
tier_w = tier_weight.get(tier, 1.0)
give_w = giveaway_weight.get(giveaway, 1.0)
dow_w = dow_weight.get(day_of_week, 1.0)

pace_med = np.interp(
    sales_window, pacing["days_since_onsale"], pacing["median"],
    left=pacing["median"].iloc[0], right=pacing["median"].iloc[-1]
)

forecast_tickets = txns * avg_tix_per_txn * tier_w * give_w * dow_w * (0.70 + 0.60 * pace_med)
gap = GOAL_TICKETS - forecast_tickets
progress_pct = np.clip(forecast_tickets / GOAL_TICKETS * 100, 0, 150)

# ==============================
# KPIs
# ==============================
col1, col2, col3 = st.columns(3)
col1.metric("🎯 Goal (Tickets)", f"{GOAL_TICKETS:,}")
col2.metric("📈 Forecast", f"{int(round(forecast_tickets)):,}")
col3.metric("⚠️ Gap to Goal", f"{int(round(gap)):,}", delta=f"{progress_pct:.1f}%")

# ==============================
# GAUGE INDICATOR
# ==============================
st.subheader("📟 Ticket Sales Indicator")
max_gauge = max(3000, GOAL_TICKETS * 1.2, forecast_tickets * 1.1)

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=forecast_tickets,
    delta={'reference': GOAL_TICKETS, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
    title={'text': "Forecasted Ticket Sales"},
    number={'font': {'size': 40}},
    gauge={
        'axis': {'range': [0, max_gauge]},
        'bar': {'color': "royalblue"},
        'steps': [
            {'range': [0, GOAL_TICKETS * 0.72], 'color': "lightcoral"},
            {'range': [GOAL_TICKETS * 0.72, GOAL_TICKETS * 0.96], 'color': "gold"},
            {'range': [GOAL_TICKETS * 0.96, max_gauge], 'color': "lightgreen"},
        ],
        'threshold': {'line': {'color': "black", 'width': 4}, 'value': GOAL_TICKETS}
    }
))
fig_gauge.update_layout(height=300)
st.plotly_chart(fig_gauge, use_container_width=True)

# ==============================
# PACING LINE WITH INDICATOR
# ==============================
st.subheader(f"📊 Historical Pacing – {window_group}")

scenario_share = scenario_cum_share(sales_window, txns, avg_tix_per_txn, tier_w, give_w, dow_w)
p25_at_day = np.interp(sales_window, pacing["days_since_onsale"], pacing["p25"])
p75_at_day = np.interp(sales_window, pacing["days_since_onsale"], pacing["p75"])

if scenario_share < p25_at_day:
    color, label = "red", "🔴 Below P25 (Danger)"
elif scenario_share < p75_at_day:
    color, label = "gold", "🟡 Between P25–P75 (On Pace)"
else:
    color, label = "green", "🟢 Above P75 (Strong)"

fig = px.line(pacing, x="days_since_onsale", y="median", title="Cumulative Ticket Sales Pacing")
fig.add_scatter(x=pacing["days_since_onsale"], y=pacing["p25"], mode="lines", name="P25 (Danger)", line=dict(dash="dot", color="red"))
fig.add_scatter(x=pacing["days_since_onsale"], y=pacing["p75"], mode="lines", name="P75 (Strong)", line=dict(dash="dot", color="green"))
fig.add_vline(x=sales_window, line_dash="dash", line_color=color, annotation_text=label, annotation_position="top right")
fig.add_scatter(x=[sales_window], y=[scenario_share], mode="markers+text", text=[f"Your Scenario<br>{scenario_share:.1%}"],
                textposition="top center", marker=dict(size=14, color=color, symbol="star"), name="Scenario")
fig.update_layout(xaxis_title="Days Since Onsale", yaxis_title="Cumulative Share (0–1)", yaxis=dict(range=[0,1.05]), template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

# ==============================
# INSIGHTS
# ==============================
st.subheader("💡 Insights & Recommendations")
st.markdown(f"""
**Status:** {label}  
**Forecast vs Goal:** {int(round(forecast_tickets)):,} / {GOAL_TICKETS:,}  ({progress_pct:.1f}%)

- Longer sales windows lead to stronger early pacing.
- Tier, Giveaways, and Weekends provide meaningful lift.
- If below P25, trigger urgency campaigns.
""")

st.caption("🏀 Cavs Analytics Dashboard • Streamlit + Plotly • Data-driven ticket sales pacing & forecasting")
