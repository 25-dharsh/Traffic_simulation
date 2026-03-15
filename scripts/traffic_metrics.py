"""
Phase 8 — Traffic data analytics and visualization.
Computes KPIs and generates high-fidelity graphs using matplotlib.
"""

import os
import sys
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import csv

# Use non-interactive backend for server/agent environments
matplotlib.use("Agg")

BASE_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRIPINFO_FILE  = os.path.join(BASE_DIR, "metrics_output", "tripinfo.xml")
SUMMARY_FILE   = os.path.join(BASE_DIR, "metrics_output", "summary.xml")
DET_OUTPUT     = os.path.join(BASE_DIR, "detectors", "det_output.xml")
METRICS_OUT    = os.path.join(BASE_DIR, "metrics_output")

def _parse_tripinfo(path: str) -> list[dict]:
    vehicles = []
    if not os.path.exists(path):
        return vehicles
    try:
        for _, elem in ET.iterparse(path, events=("end",)):
            if elem.tag == "tripinfo":
                vehicles.append({
                    "id":       elem.get("id", ""),
                    "vtype":    elem.get("vType", ""),
                    "duration": float(elem.get("duration", 0) or 0),
                    "wait":     float(elem.get("waitingTime", 0) or 0),
                    "depart":   float(elem.get("depart", 0) or 0),
                    "arrival":  float(elem.get("arrival", -1) or -1),
                    "routeLen": float(elem.get("routeLength", 1) or 1),
                })
                elem.clear()
    except Exception as e:
        print(f"Error parsing tripinfo: {e}")
    return vehicles

def _parse_summary(path: str) -> list[dict]:
    rows = []
    if not os.path.exists(path):
        return rows
    try:
        for _, elem in ET.iterparse(path, events=("end",)):
            if elem.tag == "step":
                rows.append({
                    "time":    float(elem.get("time", 0) or 0),
                    "running": int(elem.get("running", 0) or 0),
                    "arrived": int(elem.get("arrived", 0) or 0),
                    "waiting": float(elem.get("meanWaitingTime", 0) or 0),
                })
                elem.clear()
    except Exception as e:
        print(f"Error parsing summary: {e}")
    return rows

def _save(fig, name: str):
    path = os.path.join(METRICS_OUT, name)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [graph] → {path}")

def compute_metrics(live_data: dict | None = None):
    print(f"[metrics] Computing expanded performance metrics...")
    os.makedirs(METRICS_OUT, exist_ok=True)

    vehicles = _parse_tripinfo(TRIPINFO_FILE)
    summary  = _parse_summary(SUMMARY_FILE)

    if not vehicles and not summary and not live_data:
        print("[metrics] No data found to compute metrics.")
        return

    # ── 1. Average Waiting Time Trend ──────────────────────────────────────────
    if summary:
        times = [r["time"] for r in summary]
        vals = [r["waiting"] for r in summary]
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(times, vals, color="#e74c3c", label="Avg Waiting Time (s)")
        ax.fill_between(times, vals, alpha=0.3, color="#e74c3c")
        ax.set_title("Average Waiting Time Trend", fontsize=14)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Wait Time (s)")
        ax.grid(True, alpha=0.3)
        _save(fig, "waiting_time_trend.png")

    # ── 2. Travel Time Distribution ────────────────────────────────────────────
    if vehicles:
        durations = [v["duration"] for v in vehicles]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(durations, bins=50, color="#3498db", edgecolor="white")
        ax.set_title("Travel Time Distribution", fontsize=14)
        ax.set_xlabel("Travel Time (s)")
        ax.set_ylabel("Vehicle Count")
        ax.grid(True, alpha=0.3)
        _save(fig, "travel_time_dist.png")

    # ── 3. Throughput Per Minute ───────────────────────────────────────────────
    if summary:
        minutes = []
        counts = []
        current_minute_arrived = 0
        throughput_data = []
        for r in summary:
            current_minute_arrived += r["arrived"]
            if int(r["time"]) % 60 == 0 and r["time"] > 0:
                minute = int(r["time"]) // 60
                minutes.append(minute)
                counts.append(current_minute_arrived)
                throughput_data.append({"minute": minute, "arrived": current_minute_arrived})
                current_minute_arrived = 0
        
        # Save CSV
        tp_csv = os.path.join(METRICS_OUT, "throughput_per_minute.csv")
        with open(tp_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["minute", "arrived"])
            writer.writeheader()
            writer.writerows(throughput_data)

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(minutes, counts, color="#2ecc71")
        ax.set_title("Throughput Per Minute", fontsize=14)
        ax.set_xlabel("Time (minutes)")
        ax.set_ylabel("Vehicles Arrived")
        ax.grid(True, alpha=0.3)
        _save(fig, "throughput_per_minute.png")

    # ── 4. Ambulance Delay Analysis ───────────────────────────────────────────
    ambs = [v for v in vehicles if "ambulance" in v["vtype"].lower()]
    if ambs:
        amb_data = []
        for v in ambs:
            ideal = v["routeLen"] / 20.0 # 20m/s approx
            delay = v["duration"] - ideal
            amb_data.append({
                "id": v["id"],
                "duration": v["duration"],
                "ideal": f"{ideal:.1f}",
                "delay": f"{delay:.1f}"
            })
        
        # Save CSV
        amb_csv = os.path.join(METRICS_OUT, "ambulance_performance.csv")
        with open(amb_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "duration", "ideal", "delay"])
            writer.writeheader()
            writer.writerows(amb_data)

        delays = [float(d["delay"]) for d in amb_data]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.boxplot(delays, patch_artist=True, boxprops=dict(facecolor="#c0392b"))
        ax.set_title("Ambulance Latency (Delay vs Ideal)", fontsize=14)
        ax.set_ylabel("Delay (s)")
        ax.set_xticks([1], ["Ambulances"])
        ax.grid(True, alpha=0.3)
        _save(fig, "ambulance_latency.png")

    # ── 5. Intersection Queue Length Analysis ────────────────────────────────
    if os.path.exists(DET_OUTPUT):
        print("[metrics] Parsing detector output for intersection queues...")
        try:
            intersections = {} 
            for _, elem in ET.iterparse(DET_OUTPUT, events=("end",)):
                if elem.tag == "interval":
                    det_id = elem.get("id", "")
                    parts = det_id.split("_")
                    if len(parts) >= 2:
                        node_id = parts[1]
                        jam = float(elem.get("maxJamLengthInVehicles", 0))
                        intersections[node_id] = max(intersections.get(node_id, 0), jam)
                elem.clear()
            
            if intersections:
                # Save all to CSV
                queue_csv = os.path.join(METRICS_OUT, "intersection_max_queues.csv")
                with open(queue_csv, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["node_id", "max_queue_vehicles"])
                    for nid, q in sorted(intersections.items(), key=lambda x: x[1], reverse=True):
                        writer.writerow([nid, f"{q:.1f}"])

                top_10 = sorted(intersections.items(), key=lambda x: x[1], reverse=True)[:10]
                nodes, queues = zip(*top_10)
                fig, ax = plt.subplots(figsize=(14, 7))
                ax.bar(nodes, queues, color="#f1c40f")
                ax.set_title("Top 10 Most Congested Intersections", fontsize=14)
                ax.set_ylabel("Max Queue (Vehicles)")
                ax.set_xlabel("Intersection (Node ID)")
                plt.xticks(rotation=45)
                ax.grid(True, alpha=0.3)
                _save(fig, "intersection_queues_top10.png")
        except Exception as e:
            print(f"[metrics] Could not parse detector output: {e}")

    print(f"[metrics] Expanded metrics and CSV exports generated successfully.")

if __name__ == "__main__":
    compute_metrics()
