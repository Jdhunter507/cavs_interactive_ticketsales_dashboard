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
Real-time pacing and forecasting with scenario-based weighting by **Tier**, **Giveaway**, **Theme Night**, and **Day of Week**.  
Compare your live performance to median cumulative pacing benchmarks and plan interventions.
""")

# ===========================
# LOAD DATA
# ===========================
DATA_DIR = "cavs_hackathon_outputs"
os.makedirs(DATA_DIR, exist_ok=True)
pacing_path = os.path.join(DATA_DIR, "historical_pacing_line.csv")
cavs_path = "Cavs_Tickets.csv"

@st.cache_data
def load_data(pacing_path, cavs_path):
    pacing = pd.read_csv(pacing_path) if os.path.exists(pacing_path) else None
    cavs = pd.read_csv(cavs_path) if os.path.exists(cavs_path) else None
    return pacing, cavs

pacing, cavs = load_data(pacing_path, cavs_path)

# Default median pacing fallback (always available)
if pacing is None:
    pacing = pd.DataFrame({
        "days_until_game": [120, 90, 60, 30, 7, 0],
        "median_cum_share": [0.10, 0.25, 0.50, 0.75, 0.92, 1.00],
        "p25": [0.05, 0.15, 0.35, 0.60, 0.80, 0.95],
        "p75": [0.15, 0.35, 0.60, 0.85, 0.97, 1.00]
    })

# ===========================
# SIDEBAR CONTROLS
# ===========================
st.sidebar.header("🎮 Scenario Controls")
tier = st.sidebar.selectbox("Game Tier", ["A+", "A", "B", "C", "D"], index=2)
giveaway = st.sidebar.selectbox("Giveaway Type", ["None", "T-Shirt", "Bobblehead", "Poster", "Food Voucher"], index=1)
theme = st.sidebar.selectbox("Theme Night", ["Regular Night", "Home Opener", "Pride", "Salute to Service", "Fan Appreciation"], index=0)
day_of_week = st.sidebar.selectbox("Day of Week", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], index=5)
sales_window = st.sidebar.slider("Days Until Game", 0, 150, 60, 5)
txns = st.sidebar.slider("Transactions", 100, 800, 400, 10)
avg_tix_txn = st.sidebar.slider("Avg Tickets per Transaction", 1.0, 6.0, 3.0, 0.5)
st.sidebar.caption("Adjust sliders and dropdowns to simulate ticket pacing scenarios.")

# ===========================
# WEIGHTS AND SCENARIO CALCULATION
# ===========================
tier_weight = {"A+": 1.30, "A": 1.20, "B": 1.00, "C": 0.85, "D": 0.70}
giveaway_weight = {"None": 1.00, "T-Shirt": 1.08, "Bobblehead": 1.12, "Poster": 1.05, "Food Voucher": 1.10}
theme_weight = {"Home Opener": 1.30, "Pride": 1.15, "Salute to Service": 1.10, "Fan Appreciation": 1.20, "Regular Night": 1.00}
dow_weight = {"Sunday": 1.10, "Saturday": 1.08, "Friday": 1.05, "Thursday": 1.02,
              "Wednesday": 0.95, "Tuesday": 0.90, "Monday": 0.92}

tier_w = tier_weight.get(tier, 1.0)
give_w = giveaway_weight.get(giveaway, 1.0)
theme_w = theme_weight.get(theme, 1.0)
dow_w = dow_weight.get(day_of_week, 1.0)

# ===========================
# FORECAST MODEL
# ===========================
goal = 2500
pace_med = np.interp(sales_window, pacing["days_until_game"], pacing["median_cum_share"])
forecast_value = txns * avg_tix_txn * (0.7 + pace_med * 0.6) * tier_w * give_w * theme_w * dow_w
gap = goal - forecast_value
progress_pct = np.clip((forecast_value / goal) * 100, 0, 150)

# ===========================
# KPI METRICS
# ===========================
col1, col2, col3 = st.columns(3)
col1.metric("🎯 Goal (Tickets)", goal)
col2.metric("📈 Forecast", int(forecast_value))
col3.metric("⚠️ Gap to Goal", int(gap))

# ===========================
# SALES GAUGE
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
        "threshold": {"line": {"color": "black", "width": 4}, "value": forecast_value}
    },
    title={"text": "Forecasted Ticket Sales vs Goal"}
))
st.plotly_chart(fig_gauge, use_container_width=True)

# ===========================
# PACING STATUS
# ===========================
p25_val = np.interp(sales_window, pacing["days_until_game"], pacing["p25"])
p75_val = np.interp(sales_window, pacing["days_until_game"], pacing["p75"])
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
fig.add_trace(go.Scatter(x=pacing["days_until_game"], y=pacing["p25"], mode="lines", name="P25", line=dict(dash="dot", color="red")))
fig.add_trace(go.Scatter(x=pacing["days_until_game"], y=pacing["median_cum_share"], mode="lines", name="Median", line=dict(color="blue", width=2)))
fig.add_trace(go.Scatter(x=pacing["days_until_game"], y=pacing["p75"], mode="lines", name="P75", line=dict(dash="dot", color="green")))
fig.add_vline(x=sales_window, line_dash="dash", line_color=color, annotation_text=f"{status}", annotation_position="top right")
fig.add_trace(go.Scatter(x=[sales_window], y=[pace_med], mode="markers+text",
                         text=[f"{pace_med:.0%}"], textposition="top center",
                         marker=dict(size=14, color=color, symbol="star")))
fig.update_layout(title=f"Cumulative Ticket Sales Pace ({tier}, {theme}, {day_of_week})",
                  xaxis_title="Days Until Game", yaxis_title="Cumulative Share of Sales",
                  template="plotly_white", height=500)
st.plotly_chart(fig, use_container_width=True)

# ===========================
# ENHANCED INTERVENTION TIMELINE
# ===========================
st.subheader("🕓 Strategic Intervention Timeline")

if "Danger" in status:
    st.error("⚠️ Urgent: Implement interventions immediately to boost pace!")
elif "On Pace" in status:
    st.warning("🟡 Moderate pace — plan mid-cycle interventions.")
else:
    st.success("🟢 Strong pace — maintain current strategy.")

st.markdown("Earlier interventions drive stronger long-term pacing improvements.")

interventions = pd.DataFrame({
    "Days Before Game": [90, 60, 30, 7],
    "Intervention": ["Launch Early Marketing", "Add Giveaway Promotion", "Push Urgency Campaign", "Offer Limited-Time Discount"],
    "Expected Effect (%)": [10, 8, 5, 3],
    "Phase": ["Awareness", "Momentum", "Urgency", "Last Call"]
})

phase_colors = {"Awareness": "red" if "Danger" in status else "gold" if "On Pace" in status else "green",
                "Momentum": "red" if "Danger" in status else "gold" if "On Pace" in status else "green",
                "Urgency": "red" if "Danger" in status else "gold" if "On Pace" in status else "green",
                "Last Call": "red" if "Danger" in status else "gold" if "On Pace" in status else "green"}

fig_timeline = px.scatter(
    interventions, x="Days Before Game", y="Expected Effect (%)",
    text="Intervention", color="Phase",
    color_discrete_map=phase_colors, size="Expected Effect (%)",
    hover_data={"Days Before Game": True, "Expected Effect (%)": True}
)
fig_timeline.update_traces(textposition="top center", marker=dict(line=dict(width=1, color="black")))
fig_timeline.update_layout(title="📈 Recommended Interventions and Expected Lift",
                           xaxis_title="Days Before Game", yaxis_title="Expected Pacing Lift (%)",
                           xaxis=dict(autorange="reversed"), template="plotly_white", height=450)
st.plotly_chart(fig_timeline, use_container_width=True)

st.caption("Each circle represents an intervention opportunity — earlier actions yield higher potential lift.")

# ===========================
# INSIGHTS
# ===========================
st.subheader("💡 Insights & Recommendations")
st.markdown(f"""
- **Current Status:** {status} → {progress_pct:.1f}% of goal ({forecast_value:.0f}/{goal} tickets)
- **Scenario Weights:** Tier {tier} ({tier_w:.2f}×), Giveaway {giveaway} ({give_w:.2f}×), Theme {theme} ({theme_w:.2f}×)
- **Forecast Model:** Adjusts automatically based on cumulative pacing and weighted scenario factors.
""")

st.caption("Cavs Hackathon Advanced Dashboard • Median cumulative pacing • Interactive forecasting • Consistent intervention design")
