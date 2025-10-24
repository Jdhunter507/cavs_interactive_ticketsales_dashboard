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
    """
    Scale dictionary values linearly to [lo, hi]. If all equal or dict empty,
    return 1.0 for every key (neutral).
    """
    if not values_dict or len(values_dict) == 0:
        return {}
    
    keys = list(values_dict.keys())
    vals = np.array([values_dict[k] for k in keys], dtype=float)
    
    # Handle NaN values
    vals = np.nan_to_num(vals, nan=1.0)
    
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
    # Normalize inputs to 0..1 range
    norm_day  = np.clip(day / 240.0, 0, 1)
    norm_txns = np.clip(txns / 1000.0, 0, 1)  # Fixed: changed from 800 to 1000 to match slider max
    norm_avg  = np.clip(avg_tix / 6.0, 0, 1)
    norm_tier = np.clip((tier_w - 0.75) / 0.5, 0, 1)  # Simplified calculation
    norm_give = np.clip((give_w - 0.75) / 0.5, 0, 1)
    norm_dow  = np.clip((dow_w  - 0.75) / 0.5, 0, 1)

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
    """Load and preprocess ticket sales data with robust error handling."""
    try:
        # Check if file exists
        if not Path(path).exists():
            return None, f"File not found: {path}"
        
        df = pd.read_csv(path)
        
        # Validate minimum required columns
        required_cols = ["days_since_onsale", "daily_tickets"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"Missing required columns: {missing_cols}"
        
        # Convert numeric columns
        df["days_since_onsale"] = pd.to_numeric(df["days_since_onsale"], errors="coerce")
        df["daily_tickets"] = pd.to_numeric(df["daily_tickets"], errors="coerce")
        
        # Handle event identifier
        if "event_name" not in df.columns:
            df["event_name"] = "Event_" + df.index.astype(str)
        
        # Optional categorical columns with safe defaults
        df["tier"] = df.get("tier", "Unknown").fillna("Unknown")
        df["giveaway"] = df.get("giveaway", "None").fillna("None")
        df["day_of_sale"] = df.get("day_of_sale", "Unknown").fillna("Unknown")
        
        # Clean data
        df = df.dropna(subset=["days_since_onsale", "daily_tickets"]).copy()
        df = df[df["daily_tickets"] >= 0]  # Remove negative ticket sales
        df = df[df["days_since_onsale"] >= 0]  # Remove negative days
        
        if df.empty:
            return None, "No valid data rows after cleaning"
        
        df = df.sort_values(["event_name", "days_since_onsale"])
        
        # Per-event cumulative shares
        df["cum_tickets"] = df.groupby("event_name")["daily_tickets"].cumsum()
        df["total_tickets"] = df.groupby("event_name")["daily_tickets"].transform("sum")
        
        # Guard against divide-by-zero
        df["cum_share"] = np.where(
            df["total_tickets"] > 0,
            df["cum_tickets"] / df["total_tickets"],
            0
        )
        df["cum_share"] = df["cum_share"].clip(0, 1)  # Ensure valid range
        
        # Event max window for bucketing cohorts
        evt_window = df.groupby("event_name")["days_since_onsale"].max()
        evt_window.name = "event_sales_window"
        df = df.merge(evt_window, on="event_name", how="left")
        
        # Bucket sales windows
        def bucket(win):
            if pd.isna(win):
                return "Unknown"
            if win <= 30:
                return "Short (1–30)"
            if win <= 90:
                return "Medium (31–90)"
            return "Long (91–150+)"
        
        df["sales_window_group"] = df["event_sales_window"].apply(bucket)
        
        return df, None
        
    except Exception as e:
        return None, f"Error loading data: {str(e)}"

df, error = load_data()

if error or df is None:
    st.error(f"⚠️ Could not load **Cavs Tickets.csv**: {error}")
    st.info("Please ensure the file exists and contains the required columns: days_since_onsale, daily_tickets")
    st.stop()

# ==============================
# DATA-DRIVEN WEIGHTS
# ==============================
@st.cache_data
def compute_weights(df):
    """Compute feature weights from historical data."""
    base = df["daily_tickets"].mean()
    if base <= 0:
        base = 1.0
    
    # Calculate raw weights
    tier_raw = (df.groupby("tier")["daily_tickets"].mean() / base).to_dict()
    giveaway_raw = (df.groupby("giveaway")["daily_tickets"].mean() / base).to_dict()
    dow_raw = (df.groupby("day_of_sale")["daily_tickets"].mean() / base).to_dict()
    
    # Scale to [0.75, 1.25]
    tier_w = minmax_scale_dict(tier_raw, 0.75, 1.25)
    give_w = minmax_scale_dict(giveaway_raw, 0.75, 1.25)
    dow_w  = minmax_scale_dict(dow_raw, 0.75, 1.25)
    
    # Ensure sensible defaults for common values
    default_tiers = ["A+", "A", "B", "C", "D", "Unknown"]
    default_giveaways = ["None", "T-Shirt", "Bobblehead", "Poster", "Unknown"]
    default_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Unknown"]
    
    for k in default_tiers:
        tier_w.setdefault(k, 1.0)
    for k in default_giveaways:
        give_w.setdefault(k, 1.0)
    for k in default_days:
        dow_w.setdefault(k, 1.0)
    
    return tier_w, give_w, dow_w

tier_weight, giveaway_weight, dow_weight = compute_weights(df)

# ==============================
# PRECOMPUTE PACING CURVES
# ==============================
@st.cache_data
def precompute_pacing(df):
    """Precompute pacing curves for each sales window group."""
    pacing = (
        df.groupby(["sales_window_group", "days_since_onsale"])["cum_share"]
          .quantile([0.25, 0.5, 0.75])
          .unstack()
          .reset_index()
          .rename(columns={0.25: "p25", 0.5: "median", 0.75: "p75"})
    )
    
    # Clean and validate
    pacing = pacing.dropna(subset=["median"])
    pacing = pacing.sort_values(["sales_window_group", "days_since_onsale"])
    
    # Ensure monotonic increasing (cumulative shares should only increase)
    for group in pacing["sales_window_group"].unique():
        mask = pacing["sales_window_group"] == group
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

# Sales window slider
sales_window = st.sidebar.slider(
    "Days on Sale (before game)",
    min_value=0,
    max_value=240,
    value=60,
    step=10,
    help="Number of days the event has been on sale"
)

txns = st.sidebar.slider(
    "Number of Transactions (buyers)",
    min_value=50,
    max_value=1000,
    value=400,
    step=10,
    help="Expected number of purchase transactions"
)

avg_tix_per_txn = st.sidebar.slider(
    "Avg Tickets per Transaction",
    min_value=1.0,
    max_value=6.0,
    value=3.0,
    step=0.5,
    help="Average tickets purchased per transaction"
)

tier = st.sidebar.selectbox(
    "Game Tier",
    sorted(tier_weight.keys()),
    help="Quality/desirability of the game"
)

giveaway = st.sidebar.selectbox(
    "Giveaway Type",
    sorted(giveaway_weight.keys()),
    help="Promotional giveaway for the game"
)

day_of_week = st.sidebar.selectbox(
    "Day of Week",
    ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    index=5,  # Default to Friday
    help="Day of the week for the game"
)

# ==============================
# BUILD PACING FOR SELECTED COHORT
# ==============================
if window_group == "All Games":
    # Average curves across all cohorts
    pacing = (
        pacing_all.groupby("days_since_onsale")[["p25", "median", "p75"]]
        .mean()
        .reset_index()
        .sort_values("days_since_onsale")
    )
else:
    pacing = pacing_all[pacing_all["sales_window_group"] == window_group].copy()

if pacing.empty:
    st.error(f"⚠️ No pacing data available for cohort: {window_group}")
    st.info("Try selecting 'All Games' or a different sales window group.")
    st.stop()

# ==============================
# SCENARIO FORECAST
# ==============================
tier_w = tier_weight.get(tier, 1.0)
give_w = giveaway_weight.get(giveaway, 1.0)
dow_w  = dow_weight.get(day_of_week, 1.0)

# Interpolate median pacing share at the chosen day
pace_med = float(np.interp(
    sales_window,
    pacing["days_since_onsale"].values,
    pacing["median"].values,
    left=pacing["median"].iloc[0] if len(pacing) > 0 else 0,
    right=pacing["median"].iloc[-1] if len(pacing) > 0 else 1
))

# Forecast tickets using weighted formula
base_forecast = txns * avg_tix_per_txn
multipliers = tier_w * give_w * dow_w
pace_adjustment = 0.70 + 0.60 * pace_med

forecast_tickets = base_forecast * multipliers * pace_adjustment
gap = GOAL_TICKETS - forecast_tickets
progress_pct = float(np.clip((forecast_tickets / GOAL_TICKETS) * 100.0, 0, 150))

# ==============================
# TOP KPIs
# ==============================
c1, c2, c3 = st.columns(3)
c1.metric("🎯 Goal (Tickets)", f"{GOAL_TICKETS:,}")
c2.metric("📈 Forecast", f"{int(round(forecast_tickets)):,}")
c3.metric("⚠️ Gap to Goal", f"{int(round(gap)):,}", delta=f"{progress_pct:.1f}%")

# ==============================
# GAUGE (ARCH INDICATOR)
# ==============================
st.subheader("📟 Ticket Sales Indicator")

max_gauge = max(3000, GOAL_TICKETS * 1.2, forecast_tickets * 1.1)

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=forecast_tickets,
    delta={
        'reference': GOAL_TICKETS,
        'increasing': {'color': "green"},
        'decreasing': {'color': "red"}
    },
    title={'text': "Forecasted Ticket Sales", 'font': {'size': 20}},
    number={'font': {'size': 40}},
    gauge={
        'axis': {'range': [0, max_gauge], 'tickwidth': 1},
        'bar': {'color': "royalblue"},
        'steps': [
            {'range': [0, GOAL_TICKETS * 0.72], 'color': "lightcoral"},
            {'range': [GOAL_TICKETS * 0.72, GOAL_TICKETS * 0.96], 'color': "gold"},
            {'range': [GOAL_TICKETS * 0.96, max_gauge], 'color': "lightgreen"},
        ],
        'threshold': {
            'line': {'color': "black", 'width': 4},
            'thickness': 0.8,
            'value': GOAL_TICKETS
        }
    }
))

fig_gauge.update_layout(height=300)
st.plotly_chart(fig_gauge, use_container_width=True)

# ==============================
# PACING LINE + SCENARIO INDICATOR
# ==============================
st.subheader(f"📊 Historical Pacing – {window_group}")

# Calculate scenario cumulative share
scenario_share = scenario_cum_share(
    day=sales_window,
    txns=txns,
    avg_tix=avg_tix_per_txn,
    tier_w=tier_w,
    give_w=give_w,
    dow_w=dow_w
)

# Get percentile values at selected day
p25_at_day = float(np.interp(
    sales_window,
    pacing["days_since_onsale"].values,
    pacing["p25"].values,
    left=pacing["p25"].iloc[0] if len(pacing) > 0 else 0,
    right=pacing["p25"].iloc[-1] if len(pacing) > 0 else 0.25
))

p75_at_day = float(np.interp(
    sales_window,
    pacing["days_since_onsale"].values,
    pacing["p75"].values,
    left=pacing["p75"].iloc[0] if len(pacing) > 0 else 0,
    right=pacing["p75"].iloc[-1] if len(pacing) > 0 else 0.75
))

# Determine status
if scenario_share < p25_at_day:
    indicator_color, status_label = "red", "🔴 Below P25 (Danger)"
elif scenario_share < p75_at_day:
    indicator_color, status_label = "gold", "🟡 Between P25–P75 (On Pace)"
else:
    indicator_color, status_label = "green", "🟢 Above P75 (Strong)"

# Create pacing plot
fig = go.Figure()

# Add median line
fig.add_trace(go.Scatter(
    x=pacing["days_since_onsale"],
    y=pacing["median"],
    mode='lines',
    name='Median',
    line=dict(color='blue', width=2)
))

# Add P25 line
fig.add_trace(go.Scatter(
    x=pacing["days_since_onsale"],
    y=pacing["p25"],
    mode='lines',
    name='P25 (Danger Zone)',
    line=dict(dash='dot', color='red')
))

# Add P75 line
fig.add_trace(go.Scatter(
    x=pacing["days_since_onsale"],
    y=pacing["p75"],
    mode='lines',
    name='P75 (Strong Pace)',
    line=dict(dash='dot', color='green')
))

# Add scenario indicator
fig.add_vline(
    x=sales_window,
    line_dash="dash",
    line_color=indicator_color,
    annotation_text=f"{status_label}",
    annotation_position="top right"
)

fig.add_trace(go.Scatter(
    x=[sales_window],
    y=[scenario_share],
    mode='markers+text',
    text=[f"Your Scenario<br>{scenario_share:.1%}"],
    textposition='top center',
    marker=dict(size=15, color=indicator_color, symbol='star'),
    name='Your Scenario',
    showlegend=True
))

fig.update_layout(
    title="Cumulative Ticket Sales Pacing",
    xaxis_title="Days Since Onsale",
    yaxis_title="Cumulative Share",
    yaxis=dict(tickformat='.0%', range=[0, 1.05]),
    template="plotly_white",
    hovermode='x unified',
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# ==============================
# FEATURE IMPORTANCE
# ==============================
st.subheader("🔥 Key Drivers of Ticket Sales")

feature_importance = pd.DataFrame({
    "Feature": ["Sales Window", "Transactions", "Avg Tickets/Txn", "Tier", "Giveaway", "Day of Week"],
    "Importance": [0.30, 0.25, 0.20, 0.15, 0.06, 0.04]
})

fig_imp = px.bar(
    feature_importance,
    x="Importance",
    y="Feature",
    orientation="h",
    color="Importance",
    color_continuous_scale="Reds",
    title="Feature Impact (Illustrative)",
    text=feature_importance["Importance"].apply(lambda x: f"{x:.0%}")
)

fig_imp.update_traces(textposition='outside')
fig_imp.update_layout(height=400, showlegend=False)
st.plotly_chart(fig_imp, use_container_width=True)

# ==============================
# INSIGHTS & RECOMMENDATIONS
# ==============================
st.subheader("💡 Insights & Recommendations")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    **Current Status:** {status_label}  
    **Forecast vs Goal:** {int(round(forecast_tickets)):,} / {GOAL_TICKETS:,} ({progress_pct:.1f}%)
    
    **Applied Multipliers:**
    - Tier ({tier}): {tier_w:.2f}x
    - Giveaway ({giveaway}): {give_w:.2f}x
    - Day of Week ({day_of_week}): {dow_w:.2f}x
    """)

with col2:
    if gap > 0:
        st.warning(f"⚠️ **Action Needed:** {int(round(gap)):,} tickets short of goal")
        st.markdown("""
        **Recommended Actions:**
        - Deploy urgency campaigns (limited-time offers)
        - Promote group packages and bundles
        - Increase marketing spend on high-performing channels
        - Consider flash sales or early-bird extensions
        """)
    else:
        st.success(f"✅ **On Track:** Exceeding goal by {abs(int(round(gap))):,} tickets!")
        st.markdown("""
        **Optimization Strategies:**
        - Focus on premium upsells
        - Maintain current marketing momentum
        - Test higher price points for remaining inventory
        """)

st.markdown("""
---
**Strategic Insights:**
- **Sales Window Group** matters: long-lead games typically build stronger early share
- **Tier / Giveaways / Weekend** settings raise momentum; use for mid-window acceleration
- Track weekly and intervene on red/yellow status to pull back to median or higher

**Best Practices:**
1. Keep **A+/A** games on sale ≥90 days for maximum revenue
2. Use **giveaways** strategically to lift weekday and C/D-tier games
3. Monitor pacing curves and adjust tactics based on current position
""")

st.caption("Cavs Analytics Dashboard • Built with Streamlit + Plotly • Data-driven forecasting & pacing analysis")
