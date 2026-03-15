"""
Phase 8 — Traffic detector placement and metrics computation.

Part A: generate_detectors()
  - Parses chennai.net.xml
  - Places laneAreaDetectors on all incoming lanes of TLS junctions (lanes >= 5m only)
  - Outputs detectors/detectors.add.xml

Part B: compute_metrics()
  - Reads metrics_output/tripinfo.xml and summary.xml (post-simulation)
  - Computes all KPIs
  - Saves 5 analytics graphs to metrics_output/
"""

import os
import sys
import xml.etree.ElementTree as ET

BASE_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE       = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
DETECTORS_FILE = os.path.join(BASE_DIR, "detectors", "detectors.add.xml")
DET_OUTPUT     = os.path.join(BASE_DIR, "detectors", "det_output.xml")
TRIPINFO_FILE  = os.path.join(BASE_DIR, "metrics_output", "tripinfo.xml")
SUMMARY_FILE   = os.path.join(BASE_DIR, "metrics_output", "summary.xml")
METRICS_OUT    = os.path.join(BASE_DIR, "metrics_output")

DETECTOR_FREQ  = 60   # seconds


# ── Part A: Detector generation ───────────────────────────────────────────────
def generate_detectors():
    """Place laneAreaDetectors on all incoming lanes of TLS junctions."""
    if not os.path.exists(NET_FILE):
        sys.exit(f"[generate_detectors] Network not found: {NET_FILE}")

    tree = ET.parse(NET_FILE)
    root = tree.getroot()

    # Find all traffic-light junction IDs
    tl_junction_ids = set()
    for junction in root.findall(".//junction"):
        if junction.get("type") == "traffic_light":
            jid = junction.get("id")
            if jid:
                tl_junction_ids.add(jid)

    print(f"[generate_detectors] Found {len(tl_junction_ids)} TLS junctions.")

    # Map: junction_id → list of incoming edge elements
    tl_incoming: dict[str, list[ET.Element]] = {jid: [] for jid in tl_junction_ids}
    for edge in root.findall(".//edge"):
        edge_id = edge.get("id", "")
        if edge_id.startswith(":"):      # skip internal edges
            continue
        to_node = edge.get("to", "")
        if to_node in tl_junction_ids:
            tl_incoming[to_node].append(edge)

    os.makedirs(os.path.dirname(DETECTORS_FILE), exist_ok=True)
    additional = ET.Element("additional")
    det_count  = 0
    seen_lanes: set[str] = set()

    for jid, edges in tl_incoming.items():
        for edge_el in edges:
            edge_id = edge_el.get("id", "")
            for lane_el in edge_el.findall("lane"):
                ln_idx   = lane_el.get("index", "0")
                lane_id  = f"{edge_id}_{ln_idx}"
                if lane_id in seen_lanes:
                    continue

                lane_len = float(lane_el.get("length", "50"))
                if lane_len < 5.0:
                    continue     # skip micro-stub lanes

                seen_lanes.add(lane_id)
                det_id = (f"det_{edge_id}_{ln_idx}"
                          .replace("/", "_")
                          .replace("-", "_")
                          .replace("#", "_"))

                ET.SubElement(additional, "laneAreaDetector",
                              id=det_id,
                              lane=lane_id,
                              pos="0",
                              endPos=f"{lane_len:.2f}",
                              freq=str(DETECTOR_FREQ),
                              file=DET_OUTPUT)
                det_count += 1

    ET.indent(additional, space="  ")
    ET.ElementTree(additional).write(DETECTORS_FILE,
                                     encoding="unicode",
                                     xml_declaration=True)
    print(f"[generate_detectors] Placed {det_count} detectors → {DETECTORS_FILE}")
    return det_count


# ── Part B: Metrics & Graphs ──────────────────────────────────────────────────
def _parse_tripinfo(path: str) -> list[dict]:
    vehicles = []
    if not os.path.exists(path):
        return vehicles
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
    return vehicles


def _parse_summary(path: str) -> list[dict]:
    rows = []
    if not os.path.exists(path):
        return rows
    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == "step":
            rows.append({
                "time":    float(elem.get("time", 0) or 0),
                "running": int(elem.get("running", 0) or 0),
                "arrived": int(elem.get("arrived", 0) or 0),
                "waiting": float(elem.get("meanWaitingTime", 0) or 0),
            })
            elem.clear()
    return rows


def _save(fig, name: str):
    import matplotlib.pyplot as plt
    path = os.path.join(METRICS_OUT, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [graph] → {path}")


def compute_metrics(live_data: dict | None = None):
    """Generate all 5 analytics PNG graphs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(METRICS_OUT, exist_ok=True)

    vehicles = _parse_tripinfo(TRIPINFO_FILE)
    summary  = _parse_summary(SUMMARY_FILE)
    print(f"[metrics] {len(vehicles)} vehicles | {len(summary)} summary steps")

    times_s = [r["time"]    for r in summary]
    waits_s = [r["waiting"] for r in summary]
    run_s   = [r["running"] for r in summary]

    # Use live data if summary is empty
    if (not times_s) and live_data:
        times_s = live_data.get("times", [])
        waits_s = live_data.get("wait",  [])
        run_s   = live_data.get("queue", [])

    # ── 1. Average Waiting Time ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    if times_s:
        ax.plot(times_s, waits_s, color="#e74c3c", lw=1.5, label="Avg Wait Time")
        ax.fill_between(times_s, waits_s, alpha=0.2, color="#e74c3c")
    ax.set_xlabel("Simulation Time (s)")
    ax.set_ylabel("Average Waiting Time (s)")
    ax.set_title("Scenario A — Avg Vehicle Waiting Time (Fixed Timer Signals)")
    ax.legend(); ax.grid(True, alpha=0.4)
    _save(fig, "avg_waiting_time.png")

    # ── 2. Queue Length ────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    if times_s:
        ax.plot(times_s, run_s, color="#2980b9", lw=1.5, label="Stopped Vehicles")
        ax.fill_between(times_s, run_s, alpha=0.2, color="#2980b9")
    ax.set_xlabel("Simulation Time (s)")
    ax.set_ylabel("Queue Length (vehicles)")
    ax.set_title("Scenario A — Queue Length at Signalized Intersections")
    ax.legend(); ax.grid(True, alpha=0.4)
    _save(fig, "queue_length.png")

    # ── 3. Throughput ──────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    if summary:
        cumul, total = [], 0
        for r in summary:
            total += r["arrived"]
            cumul.append(total)
        ax.plot(times_s, cumul, color="#27ae60", lw=1.5,
                label="Cumulative Arrived")
        ax.fill_between(times_s, cumul, alpha=0.2, color="#27ae60")
    elif vehicles:
        arrivals = sorted(v["arrival"] for v in vehicles if v["arrival"] >= 0)
        ax.hist(arrivals, bins=60, color="#27ae60", edgecolor="white")
    ax.set_xlabel("Simulation Time (s)"); ax.set_ylabel("Vehicles")
    ax.set_title("Scenario A — Vehicle Throughput")
    ax.legend(); ax.grid(True, alpha=0.4)
    _save(fig, "throughput.png")

    # ── 4. Travel Time Distribution ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    if vehicles:
        durations = [v["duration"] for v in vehicles if v["duration"] > 0]
        ax.hist(durations, bins=80, color="#8e44ad", edgecolor="white", alpha=0.85)
        if durations:
            mean_d = sum(durations) / len(durations)
            ax.axvline(mean_d, color="#e74c3c", ls="--", lw=1.5,
                       label=f"Mean: {mean_d:.1f}s")
            ax.legend()
    ax.set_xlabel("Travel Time (s)"); ax.set_ylabel("Vehicles")
    ax.set_title("Scenario A — Travel Time Distribution")
    ax.grid(True, alpha=0.4)
    _save(fig, "travel_time_dist.png")

    # ── 5. Ambulance Delay ────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    ambs = [v for v in vehicles if "ambulance" in v["vtype"].lower()]
    if ambs:
        delays = [v["duration"] - max(1.0, v["routeLen"] / 20.0) for v in ambs]
        ax.bar(range(len(delays)), delays, color="#e74c3c",
               label="Ambulance Delay vs Free-Flow")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xlabel("Ambulance #"); ax.set_ylabel("Delay (s)")
        ax.set_title("Scenario A — Ambulance Delay due to Fixed Timer Signals")
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No ambulance data in tripinfo",
                ha="center", va="center", transform=ax.transAxes, fontsize=14)
        ax.set_title("Scenario A — Ambulance Delay")
    ax.grid(True, alpha=0.4)
    _save(fig, "ambulance_delay.png")

    print(f"[metrics] All 5 graphs saved to {METRICS_OUT}/")


if __name__ == "__main__":
    generate_detectors()
    print("\n[traffic_metrics.py] Phase 8 complete — detectors generated.")
    print("  Run compute_metrics() after simulation to generate graphs.")
