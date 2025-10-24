import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Cavs Ticket Sales – Forecast & Pacing", layout="wide")
st.title("🏀 Cleveland Cavaliers Ticket Sales – Forecast & Pacing Dashboard")
st.caption("Real pacing + interactive forecasting powered by **Cavs Tickets.csv**")

GOAL_TICKETS = 2500

# ==============================
# HELPERS (no sklearn required)
# ==============================
def minmax_scale_dict(values_dict, lo=0.75, hi=1.25):
    """
    Scale dictionary values linearly to [lo, hi]. If all equal or dict empty,
    return 1.0 for every key (neutral).
    """
    if not values_dict:
        return values_dict
    keys = list(values_dict.keys())
    vals = np.array([values_dict[k] for k in keys], dtype=float)
    vmin, vmax = float(np.min(vals)), float(np.max(vals))
    if vmax - vmin < 1e-12:
        return {k: 1.0 for k in keys}
    scaled = lo + (vals - vmin) * (hi - lo) / (vmax - vmin)
    return {k: float(s) for k, s in zip(keys, scaled)}

def scenario_cum_share(day, txns, avg_tix, tier_w, give_w, dow_w):
    """
    Map scenario controls to a plausible cumulative-share (0-1) for the chosen day.
    Simple, monotonic & interpretable. Uses normalized components + weights.
    """
    # Normalize inputs to 0..1-ish
    norm_day  = np.clip(day / 240.0, 0, 1)      # now 0..240 days
    norm_txns = np.clip(txns / 800.0, 0, 1)
    norm_avg  = np.clip(avg_tix / 6.0, 0, 1)
    norm_tier = np.clip((tier_w - 0.75) / (1.25 - 0.75), 0, 1)   # weights are in [0.75, 1.25]
    norm_give = np.clip((give_w - 0.75) / (1.25 - 0.75), 0, 1)
    norm_dow  = np.clip((dow_w  - 0.75) / (1.25 - 0.75), 0, 1)

    # Weighted blend (tunable)
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
    df = pd.read_csv(path)
    # Required numeric columns
    df["days_since_onsale"] = pd.to_numeric(df.get("days_since_onsale"), errors="coerce")
    df["daily_tickets"] = pd.to_numeric(df.get("daily_tickets"), errors="coerce")
    # Required id column
    if "event_name" not in df.columns:
        df["event_name"] = "Unknown_Event"

    # Optional categorical columns with safe defaults
    if "tier" not in df.columns:
        df["tier"] = "Unknown"
    if "giveaway" not in df.columns:
        df["giveaway"] = "None"
    if "day_of_sale" not in df.columns:
        df["day_of_sale"] = "Unknown"

    df = df.dropna(subset=["days_since_onsale", "daily_tickets"]).copy()
    df = df.sort_values(["event_name", "days_since_onsale"])

    # Per-event cumulative shares
    df["cum_tickets"] = df.groupby("event_name")["daily_tickets"].cumsum()
    df["total_tickets"] = df.groupby("event_name")["daily_tickets"].transform("sum")
    # guard divide-by-zero
    df["total_tickets"] = df["total_tickets"].replace({0: np.nan})
    df["cum_share"] = df["cum_tickets"] / df["total_tickets"]
    df["cum_share"] = df["cum_share"].fillna(0)

    # Event max window for bucketing cohorts
    evt_window = df.groupby("event_name")["days_since_onsale"].max().rename("event_sales_window")
    df = df.merge(evt_window, on="event_name", how="left")

    def bucket(win):
        if pd.isna(win):
            return "Unknown"
        if win <= 30: return "Short (1–30)"
        if win <= 90: return "Medium (31–90)"
        return "Long (91–150+)"
    df["sales_window_group"] = df["event_sales_window"].apply(bucket)
    return df

df = load_data()
if df.empty:
    st.error("Could not load **Cavs Tickets.csv** or it has no usable rows.")
    st.stop()

# ==============================
# DATA-DRIVEN WEIGHTS
# ==============================
@st.cache_data
def compute_weights(df):
    # Averages relative to global mean — then scaled to [0.75, 1.25]
    base = df["daily_tickets"].mean() if df["daily_tickets"].mean() > 0 else 1.0

    tier_raw = (df.groupby("tier")["daily_tickets"].mean() / base).to_dict()
    giveaway_raw = (df.groupby("giveaway")["daily_tickets"].mean() / base).to_dict()
    dow_raw = (df.groupby("day_of_sale")["daily_tickets"].mean() / base).to_dict()

    tier_w = minmax_scale_dict(tier_raw, 0.75, 1.25)
    give_w = minmax_scale_dict(giveaway_raw, 0.75, 1.25)
    dow_w  = minmax_scale_dict(dow_raw, 0.75, 1.25)

    # Ensure some sensible defaults present
    for k in ["A+", "A", "B", "C", "D", "Unknown"]:
        tier_w.setdefault(k, 1.0)
    for k in ["None", "T-Shirt", "Bobblehead", "Poster", "Unknown"]:
        give_w.setdefault(k, 1.0)
    for k in ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Unknown"]:
        dow_w.setdefault(k, 1.0)

    return tier_w, give_w, dow_w

tier_weight, giveaway_weight, dow_weight = compute_weights(df)

# ==============================
# PRECOMPUTE PACING CURVES (cached)
# ==============================
@st.cache_data
def precompute_pacing(df):
    pacing = (
        df.groupby(["sales_window_group", "days_since_onsale"])["cum_share"]
          .quantile([0.25, 0.5, 0.75])
          .unstack()
          .reset_index()
          .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
    )
    # Drop NaNs and sort
    pacing = pacing.dropna(subset=["median"]).sort_values(["sales_window_group", "days_since_onsale"])
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

# Sales window every 20 days from 0..240
sales_window_options = list(range(0, 241, 20))
sales_window = st.sidebar.select_slider(
    "Days on Sale (before game)",
    options=sales_window_options,
    value=60
)

txns = st.sidebar.slider("Number of Transactions (buyers)", min_value=50, max_value=1000, value=400, step=10)
avg_tix_per_txn = st.sidebar.slider("Avg Tickets per Transaction", min_value=1.0, max_value=6.0, value=3.0, step=0.5)

tier = st.sidebar.selectbox("Game Tier", sorted(tier_weight.keys()))
giveaway = st.sidebar.selectbox("Giveaway Type", sorted(giveaway_weight.keys()))
day_of_week = st.sidebar.selectbox("Day of Week", ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"])

# ==============================
# BUILD PACING FOR SELECTED COHORT
# ==============================
if window_group == "All Games":
    # Average curves across cohorts
    tmp = pacing_all.groupby("days_since_onsale")[["p25","median","p75"]].mean().reset_index()
    pacing = tmp.sort_values("days_since_onsale").copy()
else:
    pacing = pacing_all[pacing_all["sales_window_group"] == window_group].copy()

if pacing.empty:
    st.error("No pacing data available for the selected cohort.")
    st.stop()

# ==============================
# SCENARIO FORECAST (weighted + pace-adjusted)
# ==============================
tier_w = tier_weight.get(tier, 1.0)
give_w = giveaway_weight.get(giveaway, 1.0)
dow_w  = dow_weight.get(day_of_week, 1.0)

# Interpolate median pacing share at the chosen day (if outside range, use edge values)
pace_med = float(np.interp(sales_window,
                           pacing["days_since_onsale"].values,
                           pacing["median"].values,
                           left=pacing["median"].iloc[0],
                           right=pacing["median"].iloc[-1]))

# Forecast tickets — buyers * group size * multipliers * pace blend
forecast_tickets = txns * avg_tix_per_txn * tier_w * give_w * dow_w * (0.70 + 0.60 * pace_med)
gap = GOAL_TICKETS - forecast_tickets
progress_pct = float(np.clip((forecast_tickets / GOAL_TICKETS) * 100.0, 0, 100))

# ==============================
# TOP KPIs
# ==============================
c1, c2, c3 = st.columns(3)
c1.metric("🎯 Goal (Tickets)", GOAL_TICKETS)
c2.metric("📈 Forecast", int(round(forecast_tickets)))
c3.metric("⚠️ Gap to Goal", int(round(gap)))

# ==============================
# GAUGE (ARCH INDICATOR)
# ==============================
st.subheader("📟 Ticket Sales Indicator")
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=forecast_tickets,
    delta={'reference': GOAL_TICKETS,
           'increasing': {'color': "green"},
           'decreasing': {'color': "red"}},
    title={'text': "Forecasted Ticket Sales"},
    gauge={
        'axis': {'range': [None, max(3000, GOAL_TICKETS * 1.2)]},
        'bar': {'color': "royalblue"},
        'steps': [
            {'range': [0, GOAL_TICKETS * 0.72], 'color': "lightcoral"},     # ~under 1800 if goal=2500
            {'range': [GOAL_TICKETS * 0.72, GOAL_TICKETS * 0.96], 'color': "gold"},
            {'range': [GOAL_TICKETS * 0.96, max(3000, GOAL_TICKETS * 1.2)], 'color': "lightgreen"},
        ],
        'threshold': {
            'line': {'color': "black", 'width': 4},
            'thickness': 0.8,
            'value': forecast_tickets
        }
    }
))
st.plotly_chart(fig_gauge, use_container_width=True)

# ==============================
# PACING LINE + SCENARIO INDICATOR (color-coded)
# ==============================
st.subheader(f"📊 Historical Pacing – {window_group}")

# Scenario cumulative share using *all* scenario weights (not just pace_med)
scenario_share = scenario_cum_share(
    day=sales_window,
    txns=txns,
    avg_tix=avg_tix_per_txn,
    tier_w=tier_w,
    give_w=give_w,
    dow_w=dow_w
)

# Pull p25 and p75 at this day for status classification
p25_at_day = float(np.interp(sales_window,
                             pacing["days_since_onsale"].values,
                             pacing["p25"].values,
                             left=pacing["p25"].iloc[0],
                             right=pacing["p25"].iloc[-1]))
p75_at_day = float(np.interp(sales_window,
                             pacing["days_since_onsale"].values,
                             pacing["p75"].values,
                             left=pacing["p75"].iloc[0],
                             right=pacing["p75"].iloc[-1]))

if scenario_share < p25_at_day:
    indicator_color, status_label = "red", "🔴 Below P25 (Danger)"
elif scenario_share < p75_at_day:
    indicator_color, status_label = "gold", "🟡 Between P25–P75 (On Pace)"
else:
    indicator_color, status_label = "green", "🟢 Above P75 (Strong)"

# Plot
fig = px.line(pacing, x="days_since_onsale", y="median", title="Cumulative Ticket Sales Pacing")
fig.add_scatter(x=pacing["days_since_onsale"], y=pacing["p25"], mode="lines", name="P25 (Danger Zone)",
                line=dict(dash="dot", color="red"))
fig.add_scatter(x=pacing["days_since_onsale"], y=pacing["p75"], mode="lines", name="P75 (Strong Pace)",
                line=dict(dash="dot", color="green"))

# Scenario indicator: vertical line + point at scenario_share
fig.add_vline(x=sales_window, line_dash="dash", line_color=indicator_color,
              annotation_text=f"{status_label}", annotation_position="top right")
fig.add_scatter(
    x=[sales_window],
    y=[scenario_share],
    mode="markers+text",
    text=[f"{status_label}"],
    textposition="top center",
    marker=dict(size=12, color=indicator_color),
    name="Scenario"
)

fig.update_layout(
    xaxis_title="Days Since Onsale",
    yaxis_title="Cumulative Share (0–1)",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# ==============================
# FEATURE IMPORTANCE (illustrative)
# ==============================
st.subheader("🔥 Key Drivers of Ticket Sales")
feature_importance = pd.DataFrame({
    "Feature": ["Sales Window", "Transactions", "Avg Tickets/Txn", "Tier", "Giveaway", "Day of Week"],
    "Importance": [0.30, 0.25, 0.20, 0.15, 0.06, 0.04]
})
fig_imp = px.bar(
    feature_importance, x="Importance", y="Feature", orientation="h",
    color="Importance", color_continuous_scale="Reds", title="Feature Impact (Illustrative)"
)
st.plotly_chart(fig_imp, use_container_width=True)

# ==============================
# INSIGHTS
# ==============================
st.subheader("💡 Insights & Recommendations")
st.markdown(f"""
**Status:** {status_label}  
**Forecast vs Goal:** {int(round(forecast_tickets)):,} / {GOAL_TICKETS:,}  ({progress_pct:.1f}%)

- **Sales Window Group** matters: long-lead games typically build stronger early share.
- **Tier / Giveaways / Weekend** settings raise momentum; use for mid-window acceleration.
- If **Below P25**, deploy urgency (bundles, groups); if **Above P75**, push premium upsells.

**Next Actions**
1) Keep **A+/A** games on sale ≥90 days.  
2) Use **giveaways** to lift weekday and C/D-tier games.  
3) Track weekly; intervene on red/yellow to pull back to median or higher.
""")

st.caption("Cavs Hackathon • Streamlit + Plotly • Scenario-driven pacing & forecasting")
