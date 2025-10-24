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
    pacing_path = os.path.join(DATA_DIR, "historical_pacing_line.csv")
    cavs_path   = "Cavs_Tickets.csv"

    # Load pacing safely
    pacing = pd.read_csv(pacing_path) if os.path.exists(pacing_path) else None

    # Load Cavs tickets file safely
    if os.path.exists(cavs_path):
        cavs = pd.read_csv(cavs_path)
    else:
        cavs = None

    return pacing, cavs

pacing, cavs = load_data()

# Check Cavs data availability
if cavs is None or cavs.empty:
    st.error("⚠️ Could not find or load **Cavs_Tickets.csv**.")
    st.info("""
    Make sure this file is in the same folder as your Streamlit app or uploaded to your Streamlit Cloud workspace.
    The dashboard will still run, but only the base pacing line will be shown.
    """)
    cavs = pd.DataFrame({
        "event_name": [],
        "days_since_onsale": [],
        "daily_tickets": [],
        "tier": [],
        "day_of_week": [],
        "giveaway": [],
        "theme": []
    })
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

if segment_df.empty:
    st.warning("No Cavs ticket data loaded — using default pacing line from historical_pacing_line.csv only.")
    pacing_segment = pacing.copy()
    pacing_segment.rename(columns={"median_cum_share": "median"}, inplace=True)
else:
    # Apply segmentation filters
    if tier_select != "All":
        segment_df = segment_df[segment_df["tier"] == tier_select]
    if giveaway_select != "All":
        segment_df = segment_df[segment_df["giveaway"] == giveaway_select]
    if theme_select != "All":
        segment_df = segment_df[segment_df["theme"] == theme_select]
    if day_select != "All":
        segment_df = segment_df[segment_df["day_of_week"] == day_select]

# Adaptive fallback: allow smaller samples but flag them
if len(segment_df) < 50:
    st.warning(f"⚠️ Limited data for {tier_select} / {theme_select} / {giveaway_select} "
               f"({len(segment_df)} records). Using smaller sample for pacing — interpret trends with caution.")
elif len(segment_df) < 150:
    st.info(f"ℹ️ Moderate sample size ({len(segment_df)} records) for {tier_select} / {theme_select} / {giveaway_select}. "
            "Pacing curve may show slight noise.")

# Compute pacing safely
if "cum_share" not in segment_df.columns or segment_df.empty:
    st.warning("Fallback pacing activated – insufficient data for selected filters.")
    pacing_segment = pd.DataFrame({
        "days_since_onsale": [120, 90, 60, 30, 7, 0],
        "p25": [0.05, 0.15, 0.35, 0.6, 0.8, 0.95],
        "median": [0.1, 0.25, 0.5, 0.75, 0.92, 1.0],
        "p75": [0.15, 0.35, 0.6, 0.85, 0.97, 1.0],
    })
else:
    pacing_segment = (
        segment_df.groupby("days_since_onsale")["cum_share"]
        .quantile([0.25, 0.5, 0.75])
        .unstack()
        .reset_index()
        .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
    )


    # Compute pacing by quantiles
    pacing_segment = (
        segment_df.groupby("days_since_onsale")["cum_share"]
        .quantile([0.25, 0.5, 0.75])
        .unstack()
        .reset_index()
        .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
    )

# ✅ Safety fallback if pacing_segment is still empty or missing columns
required_cols = {"days_since_onsale", "median", "p25", "p75"}
if pacing_segment is None or any(col not in pacing_segment.columns for col in required_cols):
    st.warning("Using default pacing fallback values.")
    pacing_segment = pd.DataFrame({
        "days_since_onsale": [120, 90, 60, 30, 7, 0],
        "p25": [0.05, 0.15, 0.35, 0.6, 0.8, 0.95],
        "median": [0.1, 0.25, 0.5, 0.75, 0.92, 1.0],
        "p75": [0.15, 0.35, 0.6, 0.85, 0.97, 1.0],
    })


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
# SALES GAUGE CHART
# ===========================
st.subheader("📟 Ticket Sales Gauge")

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=forecast_value,
    delta={"reference": goal, "increasing": {"color": "green"}, "decreasing": {"color": "red"}},
    gauge={
        "axis": {"range": [0, goal * 1.4]},
        "bar": {"color": "royalblue"},
        "steps": [
            {"range": [0, goal * 0.7], "color": "lightcoral"},
            {"range": [goal * 0.7, goal], "color": "gold"},
            {"range": [goal, goal * 1.4], "color": "lightgreen"},
        ],
        "threshold": {
            "line": {"color": "black", "width": 4},
            "thickness": 0.75,
            "value": forecast_value
        }
    },
    title={"text": "Forecasted Ticket Sales vs Goal"}
))
st.plotly_chart(fig_gauge, use_container_width=True)


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
# INTERVENTION TIMELINE (ENHANCED)
# ===========================
st.subheader("🕓 Strategic Intervention Timeline")

# Dynamic context message
if "Danger" in status:
    st.error("⚠️ Urgent: Implement interventions immediately to boost pace!")
elif "On Pace" in status:
    st.warning("🟡 Moderate pace — plan mid-cycle interventions.")
else:
    st.success("🟢 Strong pace — maintain current strategy.")

st.markdown("""
This timeline shows recommended interventions at key points in the sales cycle.  
The earlier you act, the stronger the compounding impact on pacing and forecast.
""")

# Data setup
interventions = pd.DataFrame({
    "Days Before Game": [90, 60, 30, 7],
    "Intervention": [
        "Launch Early Marketing",
        "Add Giveaway Promotion",
        "Push Urgency Campaign",
        "Offer Limited-Time Discount"
    ],
    "Expected Effect (%)": [10, 8, 5, 3],
    "Phase": ["Awareness", "Momentum", "Urgency", "Last Call"]
})

# Plotly timeline-style scatter
fig_timeline = px.scatter(
    interventions,
    x="Days Before Game",
    y="Expected Effect (%)",
    text="Intervention",
    color="Phase",
    color_discrete_sequence=["#C8102E", "#FDBB30", "#6BA539", "#4B9CD3"],
    size="Expected Effect (%)",
    hover_data={"Intervention": True, "Expected Effect (%)": True, "Days Before Game": True},
)

fig_timeline.update_traces(
    marker=dict(line=dict(width=1, color="black")),
    textposition="top center",
)

fig_timeline.update_layout(
    title="📈 Recommended Interventions and Expected Lift",
    xaxis_title="Days Before Game",
    yaxis_title="Expected Pacing Lift (%)",
    xaxis=dict(autorange="reversed"),
    template="plotly_white",
    height=450,
    legend_title_text="Sales Phase"
)

st.plotly_chart(fig_timeline, use_container_width=True)

st.caption("Each circle represents an intervention opportunity. Earlier phases yield higher potential lift.")


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
