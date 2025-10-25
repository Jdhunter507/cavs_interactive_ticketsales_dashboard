# 🏀 Cavaliers Interactive Ticket Sales Dashboard  
**Real-Time Forecasting • Dynamic Pacing • Strategic Insights**

---

## 📖 Overview  
The **Cavs Interactive Ticket Sales Dashboard** is a data-driven application built with Streamlit to help sports organizations like the **Cleveland Cavaliers** track, forecast, and optimize ticket sales for individual games.  

It combines historical pacing data with interactive scenario modeling to simulate sales outcomes, identify danger zones, and plan marketing interventions to maximize ticket revenue.  

This dashboard provides an **executive-ready view** that empowers sales analysts and marketing teams to make fast, informed decisions based on intuitive visuals and live feedback.

---

## 🚀 Features  

### 🎛️ Scenario Simulation  
Use sidebar controls to explore **what-if scenarios**:
- Adjust **Sales Window (days on sale)**
- Tune **Average Tickets per Transaction**
- Set **Number of Transactions (txns)**
- Select **Game Tier (A+ to D)**
- Choose **Giveaway Type** (e.g., T-Shirt, Bobblehead)

All metrics and visuals update automatically in real time.

---

### 📟 Ticket Sales Gauge  
Interactive **gauge chart** tracking progress toward the **2,500-ticket goal**:
- 🔴 **Danger Zone** – Below 80% of goal  
- 🟡 **On Pace** – Approaching goal  
- 🟢 **Strong Performance** – Above goal  

Provides an instant snapshot of whether your forecast is on track or needs attention.

---

### 📈 Historical Pacing Line  
Visualizes how your simulated scenario compares to historical benchmarks (P25, Median, P75).  
Quickly see how your pacing aligns with or deviates from typical game performance.

---

### 🔥 Key Drivers of Ticket Sales  
Displays the most influential features driving ticket performance:  
- Game Tier  
- Giveaway Promotions  
- Sales Window Duration  
- Day of Week Effects  

(Automatically hidden if `top_features.csv` is missing.)

---

### 🕓 Strategic Intervention Timeline  

| Phase | Timing | Intervention | Expected Lift |
|--------|---------|---------------|----------------|
| Awareness | 90 Days | Launch Early Marketing | +10% |
| Momentum | 60 Days | Add Giveaway Promotion | +8% |
| Urgency | 30 Days | Push Urgency Campaign | +5% |
| Last Call | 7 Days | Offer Limited-Time Discount | +3% |

Color-coded by performance:
- 🔴 **Danger Zone** → Act now  
- 🟡 **On Pace** → Plan mid-cycle  
- 🟢 **Strong** → Maintain strategy  

---

### 📊 Model Performance  
If available, shows ML model metrics from `model_metrics.csv`:  
- **MAE** → Mean Absolute Error (avg deviation per game)  
- **R²** → % of variance explained by the model  

Helps validate the accuracy and reliability of forecasts.

---

## 💡 How It Works  

### 🗂 Data Loading  
Pulls data from `/cavs_hackathon_outputs/`:  
- `historical_pacing_line.csv`  
- `model_metrics.csv`  
- `top_features.csv`  
- `forecast_summary.csv` *(optional)*  

Fallbacks are built-in for missing files.

### ⚖️ Scenario Weighting  
Forecasts are influenced by multipliers for **Tier**, **Giveaway**, and **Day of Week** to simulate realistic behavior.

### 📉 Forecast Calculation  
Combines a base model with your inputs to forecast final sales compared to the 2,500-ticket goal.

### 🧭 Visual Feedback  
Every visualization (Gauge, Pacing Line, Timeline) updates dynamically to reflect your chosen parameters.

---

## 🧠 Best Practices  

- Start broad – Tier **B**, Giveaway **None** for baseline pacing.  
- Test strategy shifts (Giveaway, Tier upgrades) to see lift.  
- Watch pacing color: **Red → Yellow → Green** as your forecast improves.  
- Cross-check model metrics for validation before final reporting.

---

## 🧩 Folder Structure  

```yaml
cavs_interactive_ticketsales_dashboard/
│
├── cavs_dashboard_interactive.py     # Main Streamlit app
├── Cavs_Tickets.csv                  # Optional dataset
│
├── cavs_hackathon_outputs/
│   ├── historical_pacing_line.csv
│   ├── top_features.csv
│   ├── model_metrics.csv
│   ├── forecast_summary.csv
│
└── README.md
```

⚙️ How to Run the App
▶️ Option 1 – Open the Hosted App (No Installation Needed)
Launch the interactive app instantly in your browser:
🔗 [Cavs Interactive Ticket Sales Dashboard (Live App)](https://cavsinteractiveticketsalesdashboard-5veot98qo5jvaxasahycha.streamlit.app/)


💻 Option 2 – Run Locally
bash
Copy code
# 1️⃣ Clone the repository
git clone https://github.com/jdhunter507/cavs_interactive_ticketsales_dashboard.git
cd cavs_interactive_ticketsales_dashboard

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Run the app
streamlit run cavs_dashboard_interactive.py
Then open http://localhost:8501

---

🧠 Tech Stack
Python 3.10+

Streamlit – interactive web UI

Plotly – visualizations (Gauge, Timeline, Pacing)

Pandas / NumPy – data manipulation and math

---

🏁 Summary
The Cavs Interactive Ticket Sales Dashboard turns complex ticketing data into actionable insights for sales and marketing.

It helps users:

Monitor pacing in real time

Forecast outcomes under different conditions

Identify intervention timing

Visualize performance clearly

A powerful data-storytelling tool for modern sports-business operations.
