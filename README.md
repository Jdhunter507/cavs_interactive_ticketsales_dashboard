# 🏀 Cavaliers Interactive Ticket Sales Dashboard

## 📘 Overview
Interactive Streamlit dashboard for simulating, forecasting, and visualizing Cleveland Cavaliers ticket sales pacing.

This project can be run **locally with Python** or deployed **directly from GitHub to Streamlit Cloud**, allowing anyone to access it from a web browser — **no installs required**.

---

## ☁️ Run the Dashboard Online (No Downloads Needed)

You can host this dashboard directly on **[Streamlit Cloud](https://share.streamlit.io)** using your GitHub repository.

### 🔧 1️⃣ Push Project to GitHub
1. Create a new GitHub repository (e.g., `cavs-ticket-sales-dashboard`).
2. Upload all project files:
   ```
   Cavs_Ticket_Sales_App_Final/
   ├── cavs_dashboard_interactive.py
   ├── cavs_hackathon_outputs/
   │   ├── model_metrics.csv
   │   ├── top_features.csv
   │   ├── forecast_summary.csv
   │   └── historical_pacing_line.csv
   ├── README.md
   └── Project_Summary.docx
   ```
3. Commit and push to your repo:
   ```bash
   git add .
   git commit -m "Initial commit: Cavs Interactive Ticket Sales Dashboard"
   git push origin main
   ```

---

### 🚀 2️⃣ Deploy on Streamlit Cloud
1. Go to [https://share.streamlit.io](https://share.streamlit.io)
2. Click **“New app”**
3. Connect your GitHub account
4. Choose:
   - **Repository:** `yourusername/cavs-ticket-sales-dashboard`
   - **Branch:** `main`
   - **Main file path:** `cavs_dashboard_interactive.py`
5. Click **Deploy**

✅ Done!  
You’ll receive a public link like:
```
https://yourusername-cavs-ticket-sales-dashboard.streamlit.app
```
Anyone can open that link and interact with your dashboard instantly — no installation required.

---

## ⚙️ Local Installation & Setup (Optional)
If you prefer running it on your own machine:

1. Install Python 3.10+
2. Open a terminal in this folder
3. Install dependencies:
   ```bash
   pip install streamlit pandas plotly
   ```
4. Run the app:
   ```bash
   streamlit run cavs_dashboard_interactive.py --server.port 8503
   ```
5. Open [http://localhost:8503](http://localhost:8503)

---

## 💡 Key Features
- Real-time sliders for scenario simulation  
- Interactive pacing and forecast visualization  
- Gauge chart showing progress toward 2,500-ticket goal  
- Dynamic pacing indicator (Red = danger, Yellow = on pace, Green = strong)  
- Online-ready deployment with GitHub + Streamlit Cloud  

---

## 🧠 Key Terms
| Term | Meaning |
|------|----------|
| **Transactions (txns)** | Number of distinct purchase events (each buyer or group checkout). |
| **Tickets** | Total seats sold across all transactions. |
| **avg_tix_per_txn** | Average number of tickets per purchase (group size). |

---

## 🏁 Credits
Developed for the **Cleveland Cavaliers Sports Business & Analytics Hackathon 2025**  
by the Walsh University Data Analysis Team 🏀  
