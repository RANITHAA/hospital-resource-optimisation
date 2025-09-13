"""
Hospital Resource Optimisation - Real-time Simulation & Prediction
Flask + SocketIO backend to simulate hospital data,
predict short-term usage, and stream results to dashboard.
"""

from flask import Flask, jsonify
from flask_socketio import SocketIO
import threading, time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initial Data (last 72 hours)
history_df = pd.DataFrame({
    "timestamp": pd.date_range(end=datetime.utcnow(), periods=72, freq="H"),
    "beds_occupied": np.random.randint(40, 70, 72),
    "oxygen_lph": np.random.randint(400, 600, 72)
})

# Current State
current_state = {
    "beds_occupied": int(history_df["beds_occupied"].iloc[-1]),
    "oxygen_lph": int(history_df["oxygen_lph"].iloc[-1])
}

# Prediction Function
def predict_next_hours(n=24):
    predictions = []
    last_time = history_df["timestamp"].max()
    avg_beds = history_df["beds_occupied"].tail(24).mean()
    avg_oxygen = history_df["oxygen_lph"].tail(24).mean()

    for i in range(1, n+1):
        future_time = last_time + timedelta(hours=i)
        pred_beds = int(max(0, avg_beds + np.random.normal(scale=2)))
        pred_oxygen = int(max(0, avg_oxygen + np.random.normal(scale=10)))
        predictions.append({
            "timestamp": future_time.isoformat(),
            "pred_beds": pred_beds,
            "pred_oxygen_lph": pred_oxygen
        })
    return predictions

# Live Data Simulator
def live_data_simulator():
    global history_df, current_state
    while True:
        current_state["beds_occupied"] = max(
            0, current_state["beds_occupied"] + np.random.choice([-1, 0, 1], p=[0.2, 0.6, 0.2])
        )
        current_state["oxygen_lph"] = max(
            0, current_state["oxygen_lph"] + int(np.random.normal(scale=5))
        )

        if datetime.utcnow().minute == 0:
            history_df = pd.concat([history_df, pd.DataFrame([{
                "timestamp": datetime.utcnow().replace(minute=0, second=0, microsecond=0),
                "beds_occupied": current_state["beds_occupied"],
                "oxygen_lph": current_state["oxygen_lph"]
            }])])

        socketio.emit("live_update", {
            "beds_occupied": current_state["beds_occupied"],
            "oxygen_lph": current_state["oxygen_lph"],
            "ts": datetime.utcnow().isoformat()
        })

        socketio.emit("predictions", predict_next_hours(24))
        time.sleep(5)

# Start background simulator
threading.Thread(target=live_data_simulator, daemon=True).start()

# API Endpoints
@app.route("/api/predictions")
def api_predictions():
    return jsonify(predict_next_hours(24))

@app.route("/api/history")
def api_history():
    return jsonify(history_df.tail(72).to_dict(orient="records"))

# Main
if __name__ == "__main__":
    print("✅ Server running at http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000)
