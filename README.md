# EdgeCare V1

**Live Demo:** [https://edgecare-1.onrender.com](https://edgecare-1.onrender.com)

EdgeCare V1 is a professional, athlete-centered pain logging and coach analytics platform. It provides a streamlined interface for players to track their physical well-being and for coaches to monitor athlete health and training load through data-driven insights.

## 🚀 Key Features

### For Players
- **Interactive Body Map**: Log pain locations easily with a visual front/back 3D-style body map.
- **Severity Tracking**: Rate pain on a scale of 1-10 for precise monitoring.
- **"No Pain Today" Logging**: Quick one-click entry for healthy days.
- **Weekly Overview**: View personal pain trends, average severity, and frequency peaks over the last 7 days.

### For Coaches
- **Coach Dashboard**: Secure, dedicated view for monitoring multiple athletes.
- **Player Selector**: Quickly switch between athlete profiles to view individual data.
- **Visual Analytics**: Dynamic charts (Chart.js) showing weekly trends and body part frequency.
- **Rule-Based Load Guidance**: Automated training load advisories based on clinical-style observations (e.g., Recovery Focus, Reduced Load, Full Load).
- **Neutral Insights**: Data-driven, neutral feedback on athlete logs.

## 🛠️ Tech Stack
- **Backend**: Python, Flask
- **Data Handling**: Pandas (CSV-based persistence)
- **Frontend**: JavaScript (Vanilla), HTML5, CSS3
- **Visualization**: Chart.js

## 📦 Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/rk-srinath/EdgeCare.git
   cd edgecare_v1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`.

## 📂 Usage

### Default Credentials
- **Coach**: `coach1` / `coachpass`
- **Player**: `player1` / `playerpass`

### Workflow
1. **Login**: Access the application and log in as either a Player or a Coach.
2. **Player**: Use the interactive body map to select a body part and severity, then click "Log Entry".
3. **Coach**: Use the dashboard to select a player and analyze their weekly logs and load guidance.

---

[View live on Render](https://edgecare-1.onrender.com)
