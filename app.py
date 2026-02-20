from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# =============================
# CONFIG
# =============================

app = Flask(__name__)

# =============================
# AUTH CONFIG
# =============================

# Secret key used to sign session cookies.
# Replace with a long random string in production (e.g. secrets.token_hex(32)).
app.secret_key = "edgecare-secret-key-change-in-production"

# Temporary hardcoded user store.
# Replace with a database in production.
USERS = {
    "coach1": {"password": "coachpass", "role": "coach"},
    "player1": {"password": "playerpass", "role": "player"},
}

DATA_FILE = "pain_events.csv"
PLAYER_ID = "player_001"

ALLOWED_BODY_PARTS = [
    "Head / Neck",
    "Left Shoulder",
    "Right Shoulder",
    "Chest",
    "Abdomen",
    "Upper Back",
    "Lower Back",
    "Left Hip",
    "Right Hip",
    "Left Hamstring",
    "Right Hamstring",
    "Left Knee",
    "Right Knee",
    "Left Ankle",
    "Right Ankle"
]

# =============================
# INIT STORAGE
# =============================

def init_storage():
    """Create CSV with headers if it doesn't exist. Never overwrites existing data."""
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["timestamp", "player_id", "body_part", "severity"])
        df.to_csv(DATA_FILE, index=False)

init_storage()

# =============================
# HELPERS
# =============================

def append_event(body_part: str, severity: int) -> dict:
    """Append a single pain event to the CSV. Returns the logged record."""
    timestamp = datetime.utcnow().isoformat()
    new_row = pd.DataFrame([{
        "timestamp": timestamp,
        "player_id": PLAYER_ID,
        "body_part": body_part,
        "severity": severity
    }])
    new_row.to_csv(DATA_FILE, mode="a", header=False, index=False)
    return {
        "timestamp": timestamp,
        "player_id": PLAYER_ID,
        "body_part": body_part,
        "severity": severity
    }

# =============================
# ROUTES
# =============================

# =============================
# AUTH ROUTES
# =============================

@app.route("/login", methods=["GET", "POST"])
def login():
    """Layer 4 — Login. Validates credentials and stores role in session."""
    # Already logged in → go home
    if "username" in session:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(username)

        if user and user["password"] == password:
            session["username"] = username
            session["role"]     = user["role"]
            # Coaches go directly to their analytics dashboard, never to the player logging page
            if user["role"] == "coach":
                return redirect(url_for("coach"))
            return redirect(url_for("index"))

        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Layer 4 — Clears the session and redirects to login."""
    session.clear()
    return redirect(url_for("login"))


# =============================
# ROUTES
# =============================

@app.route("/")
def index():
    # Require login for main page
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Coaches must not see the logging interface
    if session.get("role") == "coach":
        return redirect(url_for("coach"))

    return render_template("index.html")


@app.route("/log_pain", methods=["POST"])
def log_pain():
    # Enforce Role — Players Only
    if session.get("role") != "player":
        return jsonify({"success": False, "message": "Unauthorized: Players only."}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Invalid request body."}), 400

    body_part = data.get("body_part", "")
    severity = data.get("severity", 5)

    if body_part not in ALLOWED_BODY_PARTS:
        return jsonify({"success": False, "message": "Invalid body part."}), 400

    severity = max(1, min(10, int(severity)))
    record = append_event(body_part, severity)

    return jsonify({
        "success": True,
        "message": f"Pain logged: {body_part} (severity {severity})",
        "record": record
    })


@app.route("/log_no_pain", methods=["POST"])
def log_no_pain():
    """
    Records a 'No Pain Today' event for the player.
    Uses body_part='No Pain' and severity=0 as sentinel values.
    Stored in the same CSV for complete daily audit trail.
    """
    # Enforce Role — Players Only
    if session.get("role") != "player":
        return jsonify({"success": False, "message": "Unauthorized: Players only."}), 403

    record = append_event("No Pain", 0)

    return jsonify({
        "success": True,
        "message": "No pain recorded for today.",
        "record": record
    })


@app.route("/recent_logs")
def recent_logs():
    """Returns the last 5 pain events as a JSON array."""
    if not os.path.exists(DATA_FILE):
        return jsonify([])
    df = pd.read_csv(DATA_FILE)
    df = df.dropna(how="all")          # drop any blank rows
    recent = df.tail(5).to_dict(orient="records")
    return jsonify(recent)


@app.route("/weekly_summary")
def weekly_summary():
    """
    Layer 3 — Weekly Overview (read-only analytics).
    Computes in-memory from CSV. Never writes back.
    Filters: last 7 calendar days from current UTC time.
    Returns: average_pain, pain_days, most_affected_area
    """
    if not os.path.exists(DATA_FILE):
        return jsonify({"has_data": False})

    df = pd.read_csv(DATA_FILE)
    df = df.dropna(how="all")

    if df.empty:
        return jsonify({"has_data": False})

    # Parse timestamps (stored as UTC ISO strings)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Cutoff: 7 days ago from now (UTC)
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=7)

    week_df = df[df["timestamp"] >= cutoff].copy()

    # Exclude "No Pain" sentinel rows from pain metrics
    pain_df = week_df[week_df["body_part"] != "No Pain"].copy()

    if pain_df.empty:
        return jsonify({"has_data": False})

    # A) Average Pain — sum / total logs (not unique days)
    average_pain = round(pain_df["severity"].sum() / len(pain_df), 1)

    # B) Pain Days — unique calendar dates with at least one pain log
    pain_df["date"] = pain_df["timestamp"].dt.date
    pain_days = pain_df["date"].nunique()

    # C) Most Affected Area — highest frequency body part
    most_affected = pain_df["body_part"].value_counts().idxmax()

    return jsonify({
        "has_data": True,
        "average_pain": average_pain,
        "pain_days": pain_days,
        "most_affected_area": most_affected
    })


@app.route("/weekly-overview")
def weekly_overview():
    """Layer 3 — Serves the standalone Weekly Overview page. Requires login."""
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Redirect coaches to their own dashboard
    if session.get("role") == "coach":
        return redirect(url_for("coach"))

    return render_template("weekly.html")


@app.route("/api/weekly-data")
def weekly_data():
    """
    Layer 3 — Weekly analytics API. Read-only. Never modifies CSV.
    Returns:
      - labels: list of 7 day-name strings (Mon, Tue, ...)
      - daily_averages: average severity per day (0 if no logs)
      - weekly_avg: overall average rounded to 1 decimal
      - pain_days: count of unique calendar days with pain logs
      - most_affected: body_part with highest log count
      - body_part_counts: dict of {body_part: count} for bar chart
      - has_data: boolean
    """
    if not os.path.exists(DATA_FILE):
        return jsonify({"has_data": False})

    df = pd.read_csv(DATA_FILE)
    df = df.dropna(how="all")

    if df.empty:
        return jsonify({"has_data": False})

    # Parse timestamps as UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Filter last 7 calendar days (UTC)
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=7)
    week_df = df[df["timestamp"] >= cutoff].copy()

    # Exclude "No Pain" sentinel rows from pain metrics
    pain_df = week_df[week_df["body_part"] != "No Pain"].copy()

    if pain_df.empty:
        return jsonify({"has_data": False})

    # Build the ordered list of last 7 calendar dates
    day_names = []
    day_dates = []
    for i in range(6, -1, -1):
        d = (now_utc - timedelta(days=i)).date()
        day_dates.append(d)
        day_names.append(d.strftime("%a"))  # Mon, Tue, ...

    # A) Daily average pain per calendar day
    pain_df["date"] = pain_df["timestamp"].dt.date
    daily_group = pain_df.groupby("date")["severity"].mean()

    daily_averages = []
    for d in day_dates:
        avg = round(daily_group.get(d, 0), 1)
        daily_averages.append(avg)

    # B) Weekly average (all pain logs this week)
    weekly_avg = round(pain_df["severity"].mean(), 1)

    # C) Pain days (unique calendar dates with ≥1 pain log)
    pain_days = int(pain_df["date"].nunique())

    # D) Most affected area (by frequency)
    body_counts = pain_df["body_part"].value_counts()
    most_affected = str(body_counts.idxmax())

    # E) Body part frequency dict for bar chart
    body_part_counts = body_counts.to_dict()

    return jsonify({
        "has_data": True,
        "labels": day_names,
        "daily_averages": daily_averages,
        "weekly_avg": weekly_avg,
        "pain_days": pain_days,
        "most_affected": most_affected,
        "body_part_counts": body_part_counts
    })


@app.route("/coach")
def coach():
    """
    Layer 4 — Coach Weekly View. Requires coach role.
    Players receive 403 Forbidden even if logged in.
    """
    if "role" not in session:
        return redirect(url_for("login"))
    if session["role"] != "coach":
        return render_template("403.html"), 403
    return render_template("coach.html")


@app.route("/api/players")
def get_players():
    """Returns a unique list of player IDs from the CSV. Requires coach role."""
    if "role" not in session or session["role"] != "coach":
        return jsonify({"error": "Unauthorized"}), 403
    if not os.path.exists(DATA_FILE):
        return jsonify([])
    df = pd.read_csv(DATA_FILE)
    players = df["player_id"].dropna().unique().tolist()
    return jsonify(players)


def compute_load_guidance(avg_severity, pain_days, frequency_by_area):
    """
    Computes rule-based load guidance based on weekly stats.
    Returns a single advisory sentence. 
    Strictly deterministic based on provided rules.
    """
    # Get max frequency for any single area
    max_area_count = 0
    if frequency_by_area:
        max_area_count = max(frequency_by_area.values())

    # RULE 4 — RECOVERY FOCUS (Priority 1)
    if avg_severity >= 7 or pain_days >= 5:
        return "Current patterns indicate prioritizing recovery-focused sessions."

    # RULE 3 — REDUCED LOAD (Priority 2)
    # "between 5 and 7" -> [5, 7).
    if (avg_severity >= 5) or (max_area_count >= 3):
        return "Recent entries suggest considering a reduced training load."

    # RULE 2 — CONTROLLED LOAD (Priority 3)
    # "average_severity between 3 and 5" -> [3, 5)
    # "pain_days between 2 and 3" -> [2, 3]
    if (avg_severity >= 3) or (2 <= pain_days <= 3):
        return "A controlled training load may be appropriate based on recent observations."

    # RULE 1 — FULL LOAD (Priority 4)
    if avg_severity < 3 and pain_days <= 1:
        return "Current observations support full training load."

    # Fallback for gaps (e.g. sev < 3 but pain_days = 4)
    # Defaulting to Controlled Load as safe middle ground per safety-first advisory logic.
    return "A controlled training load may be appropriate based on recent observations."



@app.route("/api/coach_weekly/<player_id>")
def coach_weekly(player_id):
    """
    Coach Weekly API — read-only analytics for a single player.
    Requires coach role. Returns 403 JSON for unauthorized callers.
    Filters: last 7 days, selected player only.
    Never writes to CSV. All computation is in-memory.
    """
    # Layer 4 — backend role enforcement
    if "role" not in session or session["role"] != "coach":
        return jsonify({"error": "Unauthorized"}), 403

    if not os.path.exists(DATA_FILE):
        return jsonify({"has_data": False})

    df = pd.read_csv(DATA_FILE)
    df = df.dropna(how="all")

    if df.empty:
        return jsonify({"has_data": False})

    # Parse timestamps as UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Filter: correct player + last 7 days
    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc - timedelta(days=7)
    df = df[(df["player_id"] == player_id) & (df["timestamp"] >= cutoff)].copy()

    # Exclude "No Pain" sentinel rows from analytics
    df = df[df["body_part"] != "No Pain"].copy()

    if df.empty:
        return jsonify({"has_data": False, "player_id": player_id})

    # ── Metrics ──────────────────────────────────────────────────
    total_logs       = int(len(df))
    average_severity = round(float(df["severity"].mean()), 1)

    freq = df["body_part"].value_counts()
    most_logged_area  = str(freq.idxmax())
    frequency_by_area = {str(k): int(v) for k, v in freq.items()}

    # Pain days — unique calendar dates with at least one log
    df["date"] = df["timestamp"].dt.date
    pain_days   = int(df["date"].nunique())

    # Most active day — weekday name with the most log entries
    df["weekday"] = df["timestamp"].dt.strftime("%A")
    day_counts    = df["weekday"].value_counts()
    most_active_day = str(day_counts.idxmax()) if not day_counts.empty else "N/A"

    # Daily average — last 7 calendar days in order
    daily_group   = df.groupby("date")["severity"].mean()
    daily_average = {}
    for i in range(6, -1, -1):
        d     = (now_utc - timedelta(days=i)).date()
        label = d.strftime("%a")
        avg   = daily_group.get(d, None)
        daily_average[label] = round(float(avg), 1) if avg is not None else None

    # ── Neutral insight lines ─────────────────────────────────────
    top_area  = freq.idxmax()
    top_count = int(freq.max())
    insight_lines = []

    # Insight 1: repeated area
    if top_count >= 3:
        insight_lines.append(
            f"Consistent entries noted for {top_area} over the past week."
        )
    elif top_count >= 2:
        insight_lines.append(
            f"Multiple entries recorded for {top_area} this week."
        )

    # Insight 2: spread of areas
    if len(freq) >= 4:
        insight_lines.append(
            "Entries observed across multiple body areas this week."
        )
    elif len(freq) >= 2:
        insight_lines.append(
            f"Observations recorded across {len(freq)} body areas."
        )

    # Insight 3: severity consistency
    non_null = [v for v in daily_average.values() if v is not None]
    if len(non_null) >= 3 and (max(non_null) - min(non_null)) <= 2:
        insight_lines.append(
            "Severity levels remained relatively consistent throughout the week."
        )

    if not insight_lines:
        insight_lines.append("Observations recorded across the selected period.")

    # ── Recent logs (read-only table, last 5) ────────────────────
    df_sorted = df.sort_values("timestamp", ascending=False).head(5)
    recent_logs = [
        {
            "date":      row["timestamp"].strftime("%d %b"),
            "body_part": str(row["body_part"]),
            "severity":  int(row["severity"])
        }
        for _, row in df_sorted.iterrows()
    ]

    # Compute load guidance
    load_guidance = compute_load_guidance(
        average_severity,
        pain_days,
        frequency_by_area
    )

    return jsonify({
        "has_data":          True,
        "player_id":         player_id,
        "total_logs":        total_logs,
        "average_severity":  average_severity,
        "pain_days":         pain_days,
        "most_logged_area":  most_logged_area,
        "most_active_day":   most_active_day,
        "frequency_by_area": frequency_by_area,
        "daily_average":     daily_average,
        "summary_text":      " ".join(insight_lines),
        "recent_logs":       recent_logs,
        "load_guidance":     load_guidance
    })


if __name__ == "__main__":

    app.run(debug=True, port=5000)


