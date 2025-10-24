import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(page_title="Cavs Advanced Pacing Dashboard", layout="wide")
st.title("🏀 Cleveland Cavaliers – Advanced Ticket Sales Pacing & Forecast Dashboard")
st.markdown("""
Enhanced pacing analysis with segmentation by **Tier**, **Giveaway**, **Theme Night**, and **Day of Week**.  
Track real-time performance vs benchmarks and visualize historical interventions.
""")

# ===========================
# LOAD DATA
# ===========================
DATA_DIR = "cavs_hackathon_outputs"
os.makedirs(DATA_DIR, exist_ok=True)

@st.cache_data
def load_data():
    pacing = pd.read_csv(f"{DATA_DIR}/historical_pacing_line.csv")
    cavs = pd.read_csv("Cavs Tickets (1).csv") if os.path.exists("Cavs Tickets (1).csv") else None
    return pacing, cavs

pacing, cavs = load_data()

# ===========================
# DATA PREPARATION
# ===========================
if cavs is not None:
    cavs["theme"] = cavs["theme"].fillna("Regular Night")
    cavs["giveaway"] = cavs["giveaway"].fillna("None")
    cavs["tier"] = cavs["tier"].fillna("B")
    cavs["day_of_week"] = cavs["day_of_week"].fillna("Unknown")

    # Compute cumulative shares per event
    cavs = cavs.sort_values(["event_name", "days_since_onsale"])
    cavs["cum_tickets"] = cavs.groupby("event_name")["daily_tickets"].cumsum()
    cavs["total_tickets"] = cavs.groupby("event_name")["daily_tickets"].transform("sum")
    cavs["cum_share"] = np.where(
        cavs["total_tickets"] > 0,
        cavs["cum_tickets"] / cavs["total_tickets"],
        0
    )
    cavs["cum_share"] = cavs["cum_share"].clip(0, 1)

# ===========================
# SIDEBAR FILTERS
# ===========================
st.sidebar.header("🎮 Scenario Controls")

tier_select = st.sidebar.selectbox("Game Tier", ["All", "A+", "A", "B", "C", "D"], index=2)
giveaway_select = st.sidebar.selectbox("Giveaway", ["All", "None", "T-Shirt", "Bobblehead", "Poster", "Food Voucher"], index=0)
theme_select = st.sidebar.selectbox("Theme Night", ["All", "Home Opener", "Pride", "Salute to Service", "Fan Appreciation", "Regular Night"], index=5)
day_select = st.sidebar.selectbox("Day of Week", ["All", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], index=0)

sales_window = st.sidebar.slider("Days Until Game", 0, 150, 60, 5)
txns = st.sidebar.slider("Number of Transactions", 100, 800, 400, 10)
avg_tix_txn = st.sidebar.slider("Avg Tickets / Transaction", 1.0, 6.0, 3.0, 0.5)

st.sidebar.caption("Use the filters to segment pacing and forecast behavior.")

# ===========================
# SEGMENTED PACING CALCULATION
# ===========================
segment_df = cavs.copy()
if tier_select != "All":
    segment_df = segment_df[segment_df["tier"] == tier_select]
if giveaway_select != "All":
    segment_df = segment_df[segment_df["giveaway"] == giveaway_select]
if theme_select != "All":
    segment_df = segment_df[segment_df["theme"] == theme_select]
if day_select != "All":
    segment_df = segment_df[segment_df["day_of_week"] == day_select]

# If segment empty, fallback
if len(segment_df) < 100:
    st.warning("Not enough data for this segmentation. Showing all games instead.")
    segment_df = cavs

pacing_segment = (
    segment_df.groupby("days_since_onsale")["cum_share"]
    .quantile([0.25, 0.5, 0.75])
    .unstack()
    .reset_index()
    .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
)

# ===========================
# SCENARIO FORECAST MODEL
# ===========================
tier_weight = {"A+": 1.3, "A": 1.2, "B": 1.0, "C": 0.85, "D": 0.7}
giveaway_weight = {"None": 1.0, "T-Shirt": 1.08, "Bobblehead": 1.12, "Poster": 1.05, "Food Voucher": 1.1}
theme_weight = {"Home Opener": 1.3, "Pride": 1.15, "Salute to Service": 1.10, "Fan Appreciation": 1.20, "Regular Night": 1.0, "All": 1.0}
dow_weight = {"Sunday": 1.1, "Saturday": 1.08, "Friday": 1.05, "Thursday": 1.02, "Wednesday": 0.95, "Tuesday": 0.9, "Monday": 0.92, "All": 1.0}

tier_w = tier_weight.get(tier_select, 1.0)
give_w = giveaway_weight.get(giveaway_select, 1.0)
theme_w = theme_weight.get(theme_select, 1.0)
dow_w = dow_weight.get(day_select, 1.0)

# Use current cumulative share at sales_window
pace_med = np.interp(
    sales_window,
    pacing_segment["days_since_onsale"],
    pacing_segment["median"],
    left=0.05,
    right=1.0
)

goal = 2500
forecast_value = txns * avg_tix_txn * (0.7 + pace_med * 0.6) * tier_w * give_w * theme_w * dow_w
gap = goal - forecast_value
progress_pct = np.clip((forecast_value / goal) * 100, 0, 150)

# ===========================
# KPI SECTION
# ===========================
col1, col2, col3 = st.columns(3)
col1.metric("🎯 Goal (Tickets)", goal)
col2.metric("📈 Forecast", int(forecast_value))
col3.metric("⚠️ Gap to Goal", int(gap))

# ===========================
# PACING STATUS
# ===========================
p25_val = np.interp(sales_window, pacing_segment["days_since_onsale"], pacing_segment["p25"])
p75_val = np.interp(sales_window, pacing_segment["days_since_onsale"], pacing_segment["p75"])

if pace_med < p25_val:
    status, color = "🔴 Danger Zone (<P25)", "red"
elif pace_med < p75_val:
    status, color = "🟡 On Pace (P25–P75)", "gold"
else:
    status, color = "🟢 Strong (>P75)", "green"

st.subheader(f"📊 Pacing Analysis – {status}")

# ===========================
# PACING CHART
# ===========================
fig = go.Figure()

fig.add_trace(go.Scatter(x=pacing_segment["days_since_onsale"], y=pacing_segment["p25"], mode="lines", name="P25", line=dict(dash="dot", color="red")))
fig.add_trace(go.Scatter(x=pacing_segment["days_since_onsale"], y=pacing_segment["median"], mode="lines", name="Median", line=dict(color="blue", width=2)))
fig.add_trace(go.Scatter(x=pacing_segment["days_since_onsale"], y=pacing_segment["p75"], mode="lines", name="P75", line=dict(dash="dot", color="green")))

fig.add_vline(x=sales_window, line_dash="dash", line_color=color, annotation_text=f"{status}", annotation_position="top right")
fig.add_trace(go.Scatter(x=[sales_window], y=[pace_med], mode="markers+text", text=[f"{pace_med:.0%}"], textposition="top center", marker=dict(size=14, color=color, symbol="star")))

fig.update_layout(
    title=f"Cumulative Ticket Sales Pace ({tier_select}, {theme_select}, {day_select})",
    xaxis_title="Days Until Game",
    yaxis_title="Cumulative Share of Sales",
    template="plotly_white",
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# ===========================
# INTERVENTION TIMELINE (EXAMPLE)
# ===========================
st.subheader("🕓 Example Intervention Timeline")
st.markdown("""
If a game falls into the **Danger Zone (<P25)**, teams should consider:
- Triggering **marketing push** or **bundle offers**
- Adding **Giveaway/Theme activation**
- Using **dynamic pricing** to stimulate demand  
Below are sample interventions and their effect windows:
""")

interventions = pd.DataFrame({
    "Days Before Game": [90, 60, 30, 7],
    "Intervention": ["Launch early marketing", "Add Giveaway promotion", "Push urgency campaign", "Offer limited-time discount"],
    "Expected Effect": ["+10% pace", "+8% pace", "+5% pace", "+3% pace"]
})
st.dataframe(interventions, hide_index=True)

# ===========================
# INSIGHTS
# ===========================
st.subheader("💡 Insights & Recommendations")
st.markdown(f"""
- **Segmented pacing** improves accuracy: separate curves for premium vs regular, theme vs non-theme, weekend vs weekday.
- **Current Status:** {status} → {progress_pct:.1f}% toward goal ({forecast_value:.0f}/{goal} tickets)
- **Forecast Model** now adjusts automatically based on cumulative progress at {sales_window} days before game.
- **Next Step:** If pacing <P25 for ≥7 days, trigger intervention campaign.
""")

st.caption("Cavs Hackathon Advanced Dashboard • Incorporates segmented cumulative analysis, forecasting, and intervention modeling.")
