🏀 Cavaliers Interactive Ticket Sales Dashboard
Real-Time Forecasting • Dynamic Pacing • Strategic Insights
📖 Overview

The Cavs Interactive Ticket Sales Dashboard is a data-driven application built with Streamlit to help sports organizations like the Cleveland Cavaliers track, forecast, and optimize ticket sales for individual games.

It combines historical pacing data with interactive scenario modeling to simulate sales outcomes, identify danger zones, and plan marketing interventions to maximize ticket revenue.

This dashboard provides an executive-ready view that empowers sales analysts and marketing teams to make fast, informed decisions based on intuitive visuals and live feedback.

🚀 Features
🎛️ Scenario Simulation

Use sidebar controls to explore what-if scenarios:

Adjust Sales Window (days on sale)

Tune Average Tickets per Transaction

Set Number of Transactions (txns)

Select Game Tier (A+ to D)

Choose Giveaway Type (e.g., T-Shirt, Bobblehead)

Automatically updates all metrics and visuals in real time

📟 Ticket Sales Gauge

Interactive gauge chart that tracks progress toward the 2,500-ticket goal:

🔴 Danger Zone – Below 80% of goal

🟡 On Pace – Approaching goal

🟢 Strong Performance – Above goal

Provides an immediate snapshot of whether your forecast is on track or needs attention.

📈 Historical Pacing Line

Visualizes how your simulated scenario compares against historical benchmarks (P25, Median, P75).
This allows you to see how your current pacing aligns with or deviates from historical game performance.

🔥 Key Drivers of Ticket Sales

Displays a ranked list of the most influential variables driving ticket performance, based on your model data (top_features.csv):

Game Tier

Giveaway Promotions

Sales Window Duration

Day of Week Effects

(Automatically hidden if the dataset is not available.)

🕓 Strategic Intervention Timeline

A visual timeline showing when and how to act during the sales cycle:

Phase	Timing	Intervention	Expected Lift
Awareness	90 Days	Launch Early Marketing	+10%
Momentum	60 Days	Add Giveaway Promotion	+8%
Urgency	30 Days	Push Urgency Campaign	+5%
Last Call	7 Days	Offer Limited-Time Discount	+3%

Color-coded by current performance zone:

🔴 Danger Zone → Act now

🟡 On Pace → Plan mid-cycle actions

🟢 Strong → Maintain strategy

📊 Model Performance

If available, displays machine learning metrics from model_metrics.csv:

MAE (Mean Absolute Error) → Average forecast deviation per game

R² (Coefficient of Determination) → % of variation explained by the model

This helps validate the accuracy and reliability of the predictive model.

💡 How It Works

Data Loading
Loads data from the /cavs_hackathon_outputs/ directory:

historical_pacing_line.csv

model_metrics.csv

top_features.csv

forecast_summary.csv (optional)
If any file is missing, the dashboard uses a default dataset for continuity.

Scenario Weighting
Forecasts are influenced by multipliers for Tier, Giveaway, Theme, and Day of Week to simulate realistic outcomes.

Forecast Calculation
Combines a base sales model with your inputs to generate a scenario-adjusted forecast compared against a 2,500-ticket goal.

Visual Feedback
Every visualization (gauge, pacing, timeline) updates dynamically to reflect your chosen parameters.

🧭 Best User Experience Tips

Start broad – Use Tier = B and Giveaway = None for baseline pacing.

Test strategies – Increase giveaways or raise tier to see forecast improvement.

Use the pacing line – Identify if your scenario dips below P25 (danger zone).

Leverage the timeline – Plan interventions by phase: Awareness → Momentum → Urgency → Last Call.

Track gauge color – Your status (🔴/🟡/🟢) updates instantly.

Cross-check model metrics – Confirm forecast accuracy before reporting.

🧩 Folder Structure
cavs_interactive_ticketsales_dashboard/
│
├── cavs_dashboard_interactive.py      # Main Streamlit app
│── Cavs_Tickets.csv                   # Optional additional dataset
│
├── cavs_hackathon_outputs/
│   ├── historical_pacing_line.csv     # Historical pacing (median, P25, P75)
│   ├── top_features.csv               # Model feature importance
│   ├── model_metrics.csv              # Model performance
│   ├── forecast_summary.csv           # Optional forecast baseline data
│
└── README.md

⚙️ How to Run Locally
▶️ Recommended (Hosted App)

Visit the deployed version:
🔗 Cavs Interactive Ticket Sales Dashboard (Streamlit Cloud)

💻 Run Locally
1️⃣ Clone the Repository
git clone https://github.com/jdhunter507/cavs_interactive_ticketsales_dashboard.git
cd cavs_interactive_ticketsales_dashboard

2️⃣ Install Dependencies
pip install -r requirements.txt


(Ensure streamlit, plotly, pandas, and numpy are included.)

3️⃣ Run the App
streamlit run cavs_dashboard_interactive.py

4️⃣ Open in Browser

Navigate to:
👉 http://localhost:8501

🧠 Tech Stack

Python 3.10+

Streamlit – Front-end web interface

Plotly – Interactive visualizations (Gauge, Timeline, Pacing Line)

Pandas / NumPy – Data wrangling and numerical computation

🏁 Summary

The Cavs Interactive Ticket Sales Dashboard transforms complex ticketing data into actionable insights for business and marketing teams.

It allows users to:

Monitor ticket sales pacing in real-time

Forecast final sales outcomes under different conditions

Identify when interventions are needed

Visualize performance for quick decision-making

By blending analytics, forecasting, and storytelling, this tool serves as an AI-assisted, data-driven decision engine for modern sports organizations.
