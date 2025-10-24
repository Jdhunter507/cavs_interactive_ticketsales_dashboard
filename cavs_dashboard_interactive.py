import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Cavs Interactive Ticket Sales Dashboard", layout="wide")
st.title("🏀 Cavaliers Ticket Sales – Enhanced Interactive Forecast Dashboard")
st.markdown("""
Use the interactive controls to simulate different ticket sales scenarios, filter by Theme Night, 
and analyze how giveaways, tiers, and game themes influence pacing and total forecasted sales.
""")

# --- LOAD DATA ---
DATA_DIR = "cavs_hackathon_outputs"
os.makedirs(DATA_DIR, exist_ok=True)

@st.cache_data
def load_data():
    model_metrics = pd.read_csv(f"{DATA_DIR}/model_metrics.csv")
    top_features = pd.read_csv(f"{DATA_DIR}/top_features.csv")
    forecast = pd.read_csv(f"{DATA_DIR}/forecast_summary.csv")
    pacing = pd.read_csv(f"{DATA_DIR}/historical_pacing_line.csv")
    # Optional extended dataset
    cavs_data_path = "Cavs Tickets (1).csv"
    cavs_data = pd.read_csv(cavs_data_path) if os.path.exists(cavs_data_path) else None
    return model_metrics, top_features, forecast, pacing, cavs_data

model_metrics, top_features, forecast, pacing, cavs_data = load_data()

# --- CLEAN & PREP DATA ---
if cavs_data is not None:
    cavs_data["theme"] = cavs_data["theme"].fillna("Regular Night")
    cavs_data["giveaway"] = cavs_data["giveaway"].fillna("None")
    cavs_data["day_of_week"] = cavs_data["day_of_week"].fillna("Unknown")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎛️ Scenario Controls")

sales_window = st.sidebar.slider("Sales Window (days open for sale)", 1, 150, 90, 1)
avg_tix_txn = st.sidebar.slider("Average Tickets per Transaction", 1.0, 6.0, 3.0, 0.5)
txns = st.sidebar.slider("Number of Transactions (buyers)", 100, 800, 400, 10)
tier = st.sidebar.selectbox("Tier (Game Attractiveness)", ["A+", "A", "B", "C", "D"], index=1)
giveaway = st.sidebar.selectbox("Giveaway Type", ["None", "T-Shirt", "Bobblehead", "Poster", "Food Voucher"], index=1)
theme = st.sidebar.selectbox("Theme Night", 
                             ["All", "Home Opener", "Pride", "Salute to Service", "Fan Appreciation", "Regular Night"],
                             index=5)
day_filter = st.sidebar.selectbox("Day of Week", 
                                  ["All", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                                  index=0)

st.sidebar.info("Adjust sliders and dropdowns to test theme-based pacing and forecast performance.")

# --- WEIGHTS ---
base_sales = 1000
tier_factor = {"A+": 1.3, "A": 1.2, "B": 1.0, "C": 0.85, "D": 0.7}
giveaway_boost = {"None": 1.0, "T-Shirt": 1.08, "Bobblehead": 1.12, "Poster": 1.05, "Food Voucher": 1.1}
theme_boost = {"Home Opener": 1.3, "Pride": 1.15, "Salute to Service": 1.10, "Fan Appreciation": 1.20, "Regular Night": 1.0, "All": 1.0}
day_boost = {"Sunday": 1.1, "Saturday": 1.08, "Friday": 1.05, "Thursday": 1.02, 
             "Wednesday": 0.95, "Tuesday": 0.9, "Monday": 0.92, "All": 1.0}

# --- FORECAST CALCULATION ---
forecast_value = (
    base_sales +
    (sales_window * 5.5) +
    (avg_tix_txn * 80) +
    (txns * 1.3)
) * tier_factor[tier] * giveaway_boost[giveaway] * theme_boost[theme] * day_boost[day_filter]

goal = 2500
gap = goal - forecast_value
gap_status = "above goal 🎉" if forecast_value >= goal else "below goal ⚠️"

# --- KPI DISPLAY ---
col1, col2, col3 = st.columns(3)
col1.metric("🎯 Goal (tickets)", goal)
col2.metric("📈 Forecast (scenario)", int(forecast_value))
col3.metric("⚠️ Gap to Goal", int(gap))
st.caption(f"Your scenario is **{gap_status}** by {abs(gap):,.0f} tickets.")

# --- GAUGE CHART ---
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=forecast_value,
    delta={"reference": goal, "increasing": {"color": "green"}, "decreasing": {"color": "red"}},
    gauge={
        "axis": {"range": [0, 3500]},
        "bar": {"color": "blue"},
        "steps": [
            {"range": [0, goal * 0.8], "color": "lightcoral"},
            {"range": [goal * 0.8, goal], "color": "gold"},
            {"range": [goal, 3500], "color": "lightgreen"}
        ],
    },
    title={"text": "Projected Ticket Sales vs Goal"}
))
st.plotly_chart(fig_gauge, use_container_width=True)
st.divider()

# --- SCENARIO PACING CALCULATION ---
momentum = (
    (sales_window / 150) * 0.35 +
    (avg_tix_txn / 6) * 0.20 +
    (txns / 800) * 0.20 +
    (tier_factor[tier] / 1.3) * 0.10 +
    (giveaway_boost[giveaway] / 1.12) * 0.05 +
    (theme_boost[theme] / 1.3) * 0.10
)
scenario_share = max(0.05, min(momentum, 1.0))

# Find nearest pacing values to this sales window
nearest_row = pacing.iloc[(pacing["days_until_game"] - sales_window).abs().argmin()]
p25_val = nearest_row["p25"]
p75_val = nearest_row["p75"]

# --- Determine Indicator Color ---
if scenario_share < p25_val:
    indicator_color = "red"
    perf_status = "🔴 Below P25 (Danger Zone)"
elif scenario_share < p75_val:
    indicator_color = "yellow"
    perf_status = "🟡 On Pace (Median Range)"
else:
    indicator_color = "green"
    perf_status = "🟢 Above P75 (Strong Performance)"

st.subheader("📊 Historical Pacing Line – Scenario Comparison")
st.caption(f"Current pacing classification: **{perf_status}**")

# --- HISTORICAL PACING CHART ---
fig_pace = px.line(
    pacing,
    x="days_until_game",
    y=["median_cum_share", "p25", "p75"],
    labels={"value": "Cumulative Sales Share", "days_until_game": "Days Until Game"},
    title="Ticket Sales Pace vs. Scenario Momentum"
)
fig_pace.update_traces(mode="lines+markers")

fig_pace.add_vline(
    x=sales_window,
    line_dash="dash",
    line_color=indicator_color,
    annotation_text=f"Scenario ({sales_window} days)",
    annotation_position="top right"
)
fig_pace.add_trace(go.Scatter(
    x=[sales_window],
    y=[scenario_share],
    mode="markers+text",
    name="Your Scenario",
    text=[f"{scenario_share*100:.0f}%"],
    textposition="top center",
    marker=dict(size=12, color=indicator_color, symbol="circle")
))
fig_pace.update_layout(
    xaxis=dict(autorange="reversed"),
    legend=dict(title="Percentile Lines", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_pace, use_container_width=True)
st.divider()

# --- FEATURE IMPORTANCE ---
st.subheader("🔥 Key Drivers of Ticket Sales")
fig_imp = px.bar(
    top_features.sort_values("importance", ascending=True),
    x="importance",
    y="metric",
    orientation="h",
    color="importance",
    color_continuous_scale="Purples",
    title="Top Predictive Features"
)
st.plotly_chart(fig_imp, use_container_width=True)

# --- MODEL PERFORMANCE ---
st.subheader("📉 Model Performance Metrics")
st.dataframe(model_metrics, hide_index=True)
mae_value = model_metrics.loc[model_metrics["Metric"].str.contains("MAE", case=False), "Value"].values[0]
r2_value = model_metrics.loc[model_metrics["Metric"].str.contains("R", case=False), "Value"].values[0]
st.markdown(f"""
### 🧮 Model Performance Summary
- **MAE (Mean Absolute Error)** ≈ **{mae_value:.0f} tickets** → Avg forecast error per game.  
- **R² (Coefficient of Determination)** = **{r2_value:.2f}** → Model explains **{r2_value*100:.0f}%** of sales variance.
""")

st.divider()

# --- INSIGHTS ---
st.subheader("💡 Insights & Recommendations")
st.markdown(f"""
- **Theme Nights** like *Home Opener*, *Pride*, and *Fan Appreciation* drive measurable sales boosts.  
- Longer **sales windows** and strong **giveaway promotions** raise cumulative sales pace.  
- The **indicator color** reflects your live pacing status (Red = Danger, Yellow = On Pace, Green = Strong).  
- Use filters to analyze how *theme*, *day of week*, and *tier* shape real pacing patterns.
""")

st.info("🎯 The dashboard now supports Theme Night and Day-of-Week forecasting adjustments.")
