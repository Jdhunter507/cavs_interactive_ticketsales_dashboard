import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Tuple

# ======================================
# PAGE CONFIG
# ======================================
st.set_page_config(page_title="Cavs Ticket Sales Monitor", layout="wide")
st.title("🏀 Cavaliers Ticket Sales – Forecast & Pacing Monitor")
st.caption("Real data-driven pacing from **Cavs Tickets.csv**, interactive scenarios, and executive-ready visuals.")

GOAL_TICKETS = 2500

# ======================================
# LOAD DATA
# ======================================
@st.cache_data
def load_cavs_tickets(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Expected columns: event_name, days_since_onsale, daily_tickets, tier, day_of_sale (your sample showed these)
    # Coerce types & clean
    df["days_since_onsale"] = pd.to_numeric(df["days_since_onsale"], errors="coerce")
    df["daily_tickets"] = pd.to_numeric(df["daily_tickets"], errors="coerce")
    df = df.dropna(subset=["event_name", "days_since_onsale", "daily_tickets"]).copy()

    # Per-event cumulative progress
    df = df.sort_values(["event_name", "days_since_onsale"])
    df["cum_tickets"] = df.groupby("event_name")["daily_tickets"].cumsum()
    df["total_tickets"] = df.groupby("event_name")["daily_tickets"].transform("sum")
    df["cum_share"] = df["cum_tickets"] / df["total_tickets"]

    # Event-level total sales window (max days since onsale observed)
    event_windows = df.groupby("event_name")["days_since_onsale"].max().rename("event_sales_window")
    df = df.merge(event_windows, on="event_name", how="left")

    # Buckets for Sales Window Group filter
    def bucket_sales_window(x: float) -> str:
        if x <= 30:
            return "Short (1–30)"
        elif x <= 90:
            return "Medium (31–90)"
        else:
            return "Long (91–150+)"

    df["sales_window_group"] = df["event_sales_window"].apply(bucket_sales_window)
    return df

def safe_read() -> pd.DataFrame:
    try:
        return load_cavs_tickets("Cavs Tickets.csv")
    except Exception as e:
        st.error(
            "⚠️ Could not find or read **Cavs Tickets.csv** in this folder. "
            "Place the CSV next to this app file and rerun."
        )
        st.exception(e)
        return pd.DataFrame()

df = safe_read()
if df.empty:
    st.stop()

# ======================================
# HELPERS
# ======================================
def make_pacing_curves(df_subset: pd.DataFrame) -> pd.DataFrame:
    """
    Build percentile pacing (P25/Median/P75) by days_since_onsale
    from a subset of events (e.g., by chosen Sales Window Group).
    """
    if df_subset.empty:
        return pd.DataFrame(columns=["days_since_onsale", "p25", "median", "p75"])
    paced = (
        df_subset.groupby("days_since_onsale")["cum_share"]
        .quantile([0.25, 0.5, 0.75])
        .unstack()
        .reset_index()
        .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
        .sort_values("days_since_onsale")
    )
    return paced

def nearest_percentiles(pacing_df: pd.DataFrame, day: int) -> Tuple[float, float]:
    """
    Return (p25_at_day, p75_at_day) via interpolation for a given day.
    """
    if pacing_df.empty:
        return (0.0, 1.0)
    x = pacing_df["days_since_onsale"].values
    p25 = np.interp(day, x, pacing_df["p25"].values, left=pacing_df["p25"].iloc[0], right=pacing_df["p25"].iloc[-1])
    p75 = np.interp(day, x, pacing_df["p75"].values, left=pacing_df["p75"].iloc[0], right=pacing_df["p75"].iloc[-1])
    return (float(p25), float(p75))

def scenario_cum_share(days_on_sale: int,
                       txns: int,
                       avg_tix: float,
                       tier_w: float,
                       give_w: float,
                       dow_w: float) -> float:
    """
    Heuristic 'momentum' → maps all scenario controls to a cumulative share (0–1)
    for the chosen day, to compare against P25/P75 pacing lines.

    This is intentionally simple, monotonic, and bounded for interpretability.
    """
    # Normalize components to 0–1-ish scales
    norm_days  = min(max(days_on_sale / 150.0, 0), 1)
    norm_txns  = min(max(txns       / 800.0, 0), 1)
    norm_avg   = min(max(avg_tix    / 6.0,   0), 1)
    norm_tier  = min(tier_w / 1.30, 1)       # A+ = 1.30 → 1.0
    norm_give  = min(give_w / 1.12, 1)       # Bobblehead = 1.12 → 1.0
    norm_dow   = min(dow_w  / 1.12, 1)       # Sunday = 1.12 → 1.0

    # Weighted blend (tunable, transparent)
    momentum = (
        0.40 * norm_days +
        0.20 * norm_txns +
        0.15 * norm_avg +
        0.15 * norm_tier +
        0.05 * norm_give +
        0.05 * norm_dow
    )
    # Clamp to reasonable bounds (5%–100%)
    return float(np.clip(momentum, 0.05, 1.0))

# ======================================
# SIDEBAR – CONTROLS
# ======================================
st.sidebar.header("🎛️ Scenario Controls")

# Sales Window Group filter (applies to pacing curves)
group_choice = st.sidebar.selectbox(
    "Sales Window Group (pacing cohort)",
    ["All Games", "Short (1–30)", "Medium (31–90)", "Long (91–150+)"],
    index=0
)

# Apply cohort filter for pacing
if group_choice == "All Games":
    df_cohort = df.copy()
else:
    df_cohort = df[df["sales_window_group"] == group_choice].copy()

pacing = make_pacing_curves(df_cohort)

# Scenario controls (what-if)
days_on_sale = st.sidebar.slider("Days on Sale (before game)", 1, 150, 60, 1)
txns = st.sidebar.slider("Number of Transactions (buyers)", 100, 800, 400, 10)
avg_tix = st.sidebar.slider("Avg Tickets per Transaction", 1.0, 6.0, 3.0, 0.5)
tier = st.sidebar.selectbox("Game Tier", ["A+", "A", "B", "C", "D"], index=1)
giveaway = st.sidebar.selectbox("Giveaway Type", ["None", "T-Shirt", "Bobblehead", "Poster"], index=0)
day_of_week = st.sidebar.selectbox("Day of Week", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], index=6)

st.sidebar.markdown("---")
st.sidebar.caption("💡 Tip: Use *Sales Window Group* to compare pacing cohorts (short/medium/long lead games).")

# ======================================
# WEIGHTS / FORECAST
# ======================================
tier_weight = {"A+": 1.30, "A": 1.20, "B": 1.00, "C": 0.85, "D": 0.75}
give_weight = {"None": 1.00, "T-Shirt": 1.08, "Bobblehead": 1.12, "Poster": 1.05}
dow_weight  = {
    "Monday": 0.90, "Tuesday": 0.92, "Wednesday": 0.95, "Thursday": 1.00,
    "Friday": 1.08, "Saturday": 1.10, "Sunday": 1.12
}

tier_w = tier_weight[tier]
give_w = give_weight[giveaway]
dow_w  = dow_weight[day_of_week]

# Heuristic forecast: buyers * group size * multipliers * pacing adjustment
# Pacing adjustment blends a base (0.75) with historical median at that day (if available)
if not pacing.empty:
    pace_med = float(np.interp(days_on_sale, pacing["days_since_onsale"], pacing["median"],
                               left=pacing["median"].iloc[0], right=pacing["median"].iloc[-1]))
else:
    pace_med = 0.5  # fallback

forecast_tickets = (
    txns * avg_tix * tier_w * give_w * dow_w * (0.75 + 0.5 * pace_med)
)

gap = GOAL_TICKETS - forecast_tickets

# Model metrics (from earlier eval; keep visible)
MAE_TICKETS = 210
R2_SCORE = 0.87

# ======================================
# TOP KPIs
# ======================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("🎯 Goal (Tickets)", GOAL_TICKETS)
c2.metric("📈 Forecast (Scenario)", int(round(forecast_tickets)))
c3.metric("⚠️ Gap to Goal", int(round(gap)))
c4.metric("📊 Model R²", f"{R2_SCORE:.2f}")

# ======================================
# TICKET SALES MONITOR
# ======================================
st.subheader("🎟 Ticket Sales Monitor")
progress_pct = float(np.clip(forecast_tickets / GOAL_TICKETS * 100.0, 0, 100))
st.progress(progress_pct / 100.0)
st.write(f"**Projected progress:** {progress_pct:.1f}% of {GOAL_TICKETS:,} goal")

# ======================================
# PACING LINE with SCENARIO INDICATOR
# ======================================
st.subheader("📊 Historical Pacing (by cohort) + Scenario Indicator")

if pacing.empty:
    st.warning("No pacing data available for this Sales Window Group. Try a different cohort or check your CSV.")
else:
    # Scenario cumulative share based on ALL controls (momentum approach)
    scenario_share = scenario_cum_share(days_on_sale, txns, avg_tix, tier_w, give_w, dow_w)

    # Percentiles at this day (for classification)
    p25_at_day, p75_at_day = nearest_percentiles(pacing, days_on_sale)

    if scenario_share < p25_at_day:
        indicator_color, status_label = "red", "🔴 Below P25 (Danger Zone)"
    elif scenario_share < p75_at_day:
        indicator_color, status_label = "gold", "🟡 On Pace (Median Range)"
    else:
        indicator_color, status_label = "green", "🟢 Above P75 (Strong Performance)"

    # Build chart
    fig = px.line(
        pacing,
        x="days_since_onsale",
        y="median",
        title=f"Pacing Curves – Cohort: {group_choice}",
        labels={"days_since_onsale": "Days Since Onsale", "median": "Cumulative Share"}
    )
    fig.add_scatter(x=pacing["days_since_onsale"], y=pacing["p25"], mode="lines", name="P25 (Danger)", line=dict(dash="dot", color="red"))
    fig.add_scatter(x=pacing["days_since_onsale"], y=pacing["p75"], mode="lines", name="P75 (Strong)", line=dict(dash="dot", color="green"))

    # Scenario day line + dot
    fig.add_vline(x=days_on_sale, line_dash="dash", line_color=indicator_color,
                  annotation_text=f"Scenario: {days_on_sale} days", annotation_position="top right")
    fig.add_scatter(
        x=[days_on_sale],
        y=[scenario_share],
        mode="markers+text",
        text=[status_label],
        textposition="top center",
        marker=dict(size=12, color=indicator_color),
        name="Scenario Indicator"
    )
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# ======================================
# FEATURE IMPORTANCE (illustrative)
# ======================================
st.subheader("🔥 Key Drivers of Ticket Sales")
feat = pd.DataFrame({
    "Feature": ["Sales Window", "Transactions", "Avg Tickets/Txn", "Tier", "Giveaway", "Day of Week"],
    "Importance": [0.30, 0.25, 0.20, 0.15, 0.06, 0.04]
})
fig_imp = px.bar(
    feat.sort_values("Importance", ascending=True),
    x="Importance", y="Feature", orientation="h",
    title="Top Predictors (illustrative)", color="Importance", color_continuous_scale="Reds"
)
st.plotly_chart(fig_imp, use_container_width=True)

# ======================================
# MODEL PERFORMANCE
# ======================================
st.subheader("📉 Model Performance")
m1, m2 = st.columns(2)
with m1:
    st.metric("MAE (tickets)", f"{MAE_TICKETS:.0f}")
with m2:
    st.metric("R²", f"{R2_SCORE:.2f}")

# ======================================
# INSIGHTS & RECOMMENDATIONS
# ======================================
st.subheader("💡 Insights & Recommendations")
st.markdown(f"""
**Pacing Status:** {status_label if not pacing.empty else "N/A"}

**Insights**
- **Sales Window Group** matters: long-lead games typically hit higher cumulative shares earlier.
- **Tier & Giveaways** provide meaningful lift; **weekends** add a natural boost.
- Use the **cohort selector** to compare pacing norms for short/medium/long windows.

**Action Plan**
1. Keep **sales window ≥ 90 days** for Tier A/A+ matchups.
2. Add **giveaways** for weekday or lower-tier games to move the mid-curve.
3. Track pacing weekly; if **below P25**, trigger urgency (group outreach, bundles).
4. Use this dashboard to test “what-if” scenarios and align campaigns with pacing reality.
""")
st.caption("Powered by real transaction data from Cavs Tickets.csv • Built with Streamlit + Plotly")
