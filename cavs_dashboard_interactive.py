import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Cavs Interactive Ticket Sales Dashboard", layout="wide")
st.title("🏀 Cavaliers Ticket Sales – Interactive Forecast Dashboard")
st.markdown("""
Use the interactive controls to test different sales scenarios and see how they affect pacing and total forecasted ticket sales.
""")

# --- LOAD DATA ---
DATA_DIR = "cavs_hackathon_outputs"
os.makedirs(DATA_DIR, exist_ok=True)

@st.cache_data
def load_data():
    def safe_read(filename):
        path = os.path.join(DATA_DIR, filename)
        return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

    model_metrics = safe_read("model_metrics.csv")
    top_features = safe_read("top_features.csv")
    forecast = safe_read("forecast_summary.csv")
    pacing = safe_read("historical_pacing_line.csv")

    # Default pacing fallback if missing
    if pacing.empty:
        pacing = pd.DataFrame({
            "days_until_game": [120, 90, 60, 30, 7, 0],
            "median_cum_share": [0.10, 0.25, 0.50, 0.75, 0.92, 1.00],
            "p25": [0.05, 0.15, 0.35, 0.60, 0.80, 0.95],
            "p75": [0.15, 0.35, 0.60, 0.85, 0.97, 1.00]
        })
    return model_metrics, top_features, forecast, pacing

model_metrics, top_features, forecast, pacing = load_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎛️ Scenario Controls")
sales_window = st.sidebar.slider("Sales Window (days open for sale)", 1, 150, 90, 1)
avg_tix_txn = st.sidebar.slider("Average Tickets per Transaction", 1.0, 6.0, 3.0, 0.5)
txns = st.sidebar.slider("Number of Transactions (txns)", 100, 800, 400, 10)
tier = st.sidebar.selectbox("Tier (Game Attractiveness)", ["A+", "A", "B", "C", "D"], index=1)
giveaway = st.sidebar.selectbox("Giveaway Type", ["None", "T-Shirt", "Bobblehead", "Poster", "Food Voucher"], index=1)
theme = st.sidebar.selectbox("Theme Night", ["Regular Night", "Home Opener", "Pride", "Salute to Service", "Fan Appreciation"], index=0)
day_of_week = st.sidebar.selectbox("Day of Week", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], index=0)
st.sidebar.info("Adjust sliders and dropdowns to simulate real-time pacing and forecast performance.")

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

# --- FORECAST CALCULATION ---
base_sales = 1000
forecast_value = (
    base_sales +
    (sales_window * 5.5) +
    (avg_tix_txn * 80) +
    (txns * 1.3)
) * tier_w * give_w * theme_w * dow_w

goal = 2500
gap = goal - forecast_value
gap_status = "above goal 🎉" if forecast_value >= goal else "below goal ⚠️"

# --- KPI DISPLAY ---
col1, col2, col3 = st.columns(3)
col1.metric("🎯 Goal (tickets)", goal)
col2.metric("📈 Forecast (scenario)", int(forecast_value))
col3.metric("⚠️ Gap to Goal", int(gap))
st.caption(f"Your current scenario is **{gap_status}** by {abs(gap):,.0f} tickets.")

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
    (sales_window / 150) * 0.4 +
    (avg_tix_txn / 6) * 0.2 +
    (txns / 800) * 0.2 +
    (tier_w / 1.3) * 0.1 +
    (give_w / 1.12) * 0.1
)
scenario_share = max(0.05, min(momentum, 1.0))

# Find nearest pacing values to this sales window
nearest_row = pacing.iloc[(pacing["days_until_game"] - sales_window).abs().argmin()]
p25_val = nearest_row["p25"]
p75_val = nearest_row["p75"]

# --- Determine Indicator Color ---
if scenario_share < p25_val:
    indicator_color = "red"
    perf_status = "🔴 Danger Zone (<P25)"
elif scenario_share < p75_val:
    indicator_color = "gold"
    perf_status = "🟡 On Pace (Median Range)"
else:
    indicator_color = "green"
    perf_status = "🟢 Strong (>P75)"

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

# Add scenario marker
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

# --- ENHANCED INTERVENTION TIMELINE ---
st.subheader("🕓 Strategic Intervention Timeline")

if "Danger" in perf_status:
    st.error("⚠️ Urgent: Implement interventions immediately to boost pace!")
elif "On Pace" in perf_status:
    st.warning("🟡 Moderate pace — plan mid-cycle interventions.")
else:
    st.success("🟢 Strong pace — maintain current strategy.")

interventions = pd.DataFrame({
    "Days Before Game": [90, 60, 30, 7],
    "Intervention": ["Launch Early Marketing", "Add Giveaway Promotion", "Push Urgency Campaign", "Offer Limited-Time Discount"],
    "Expected Effect (%)": [10, 8, 5, 3],
    "Phase": ["Awareness", "Momentum", "Urgency", "Last Call"]
})

phase_colors = {phase: indicator_color for phase in interventions["Phase"]}

fig_timeline = px.scatter(
    interventions, x="Days Before Game", y="Expected Effect (%)",
    text="Intervention", color="Phase",
    color_discrete_map=phase_colors, size="Expected Effect (%)",
)
fig_timeline.update_traces(textposition="top center", marker=dict(line=dict(width=1, color="black")))
fig_timeline.update_layout(title="📈 Recommended Interventions and Expected Lift",
                           xaxis_title="Days Before Game", yaxis_title="Expected Pacing Lift (%)",
                           xaxis=dict(autorange="reversed"), template="plotly_white", height=450)
st.plotly_chart(fig_timeline, use_container_width=True)

st.caption("Each circle represents an intervention opportunity — earlier actions yield higher potential lift.")

# --- FEATURE IMPORTANCE ---
if not top_features.empty:
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
else:
    st.info("No feature importance data available.")

# --- MODEL PERFORMANCE ---
if not model_metrics.empty:
    st.subheader("📉 Model Performance Metrics")
    st.dataframe(model_metrics, hide_index=True)

    mae_value = model_metrics.loc[model_metrics["Metric"].str.contains("MAE", case=False), "Value"].values[0] if not model_metrics.empty else 0
    r2_value = model_metrics.loc[model_metrics["Metric"].str.contains("R", case=False), "Value"].values[0] if not model_metrics.empty else 0

    st.markdown(f"""
    ### 🧮 Model Performance Summary
    - **MAE (Mean Absolute Error)** ≈ **{mae_value:.0f} tickets**
    - **R² (Coefficient of Determination)** = **{r2_value:.2f}**
    """)
else:
    st.warning("No model performance data found.")

st.divider()

# --- INSIGHTS & STRATEGIC RECOMMENDATIONS ---
st.subheader("💡 Insights & Recommendations")
st.markdown("""
- Longer **sales windows**, **giveaways**, **theme nights**, and higher **transaction counts** improve overall ticket sales.  
- The **indicator color** (Red, Yellow, Green) shows your live pacing zone vs. historical benchmarks.  
- Use this dashboard weekly to test new strategies and visualize how changes impact performance.
""")

st.info("🎯 The scenario indicator updates automatically with your inputs — Red = Danger Zone, Yellow = On Pace, Green = Strong Performance.")

st.divider()
st.markdown("## 🎪 Strategic Recommendations from ML Analysis", unsafe_allow_html=True)

# Add enhanced HTML recommendations
recommendations_html = """
<div class="recommendations">
    <div style="background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h3 style="color: #FDBB30; font-size: 1.5em; margin-bottom: 10px;">📊 Historical Context</h3>
        <p style="font-size: 1.1em;">
            • Average Tier C game: <strong>2,163 tickets</strong><br>
            • Sunday games average: <strong>2,234 tickets</strong><br>
            • Games with promotions: <strong>2,311 tickets</strong><br>
            • <strong>Only 39.8%</strong> of games reach 2,500 goal historically
        </p>
    </div>

    <div class="rec-item">
        <h3>1️⃣ AGGRESSIVE PROMOTIONAL PACKAGE REQUIRED</h3>
        <p><strong>Critical Finding:</strong> Even with full promotion package (giveaway + theme + special jersey), forecast shows only 2,091 tickets — still 409 SHORT of goal.
        Standard promotions alone will NOT be sufficient.
        Recommend implementing enhanced promotional strategy including a popular bobblehead giveaway, "Family Fun Sunday" theme with pregame activities, and special jersey charity auction.</p>
    </div>

    <div class="rec-item">
        <h3>2️⃣ DYNAMIC PRICING & BUNDLE STRATEGY</h3>
        <p>Launch multi-tiered pricing approach:<br>
        • <strong>Early Bird (45+ days):</strong> 15% discount to drive early sales<br>
        • <strong>Family 4-Pack:</strong> 4 tickets + $40 concessions credit<br>
        • <strong>Group Sales (10+):</strong> 20% discount targeting youth leagues<br>
        • <strong>Flash Sales (7d out):</strong> 24-hour limited offers</p>
    </div>

    <div class="rec-item">
        <h3>3️⃣ MULTI-CHANNEL MARKETING BLITZ</h3>
        <p><strong>60 days out:</strong> Email campaign to 50k+ database<br>
        <strong>30 days out:</strong> Social media contest (win courtside seats)<br>
        <strong>14 days out:</strong> Radio partnership with local stations<br>
        <strong>7 days out:</strong> Emergency flash sale activation</p>
    </div>

    <div class="rec-item">
        <h3>4️⃣ STRATEGIC PARTNERSHIP ACTIVATION</h3>
        <p>Leverage Sunday timing for family/group sales:<br>
        • Youth basketball leagues (group packages)<br>
        • Corporate hospitality packages<br>
        • Cleveland-area school alumni associations<br>
        • Community organizations and churches</p>
    </div>

    <div class="rec-item">
        <h3>5️⃣ REAL-TIME PACING MONITORING</h3>
        <p><strong>Daily tracking</strong> against exponential pacing line. Trigger interventions automatically:<br>
        • <strong>30+ days:</strong> Boost digital marketing & email<br>
        • <strong>14–30 days:</strong> Activate social media promotions<br>
        • <strong>7–14 days:</strong> Deploy flash sales & group discounts<br>
        • <strong>Under 7 days:</strong> Aggressive last-minute pricing</p>
    </div>
</div>
"""

st.markdown(recommendations_html, unsafe_allow_html=True)

