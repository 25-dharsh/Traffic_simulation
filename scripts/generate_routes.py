"""
Phase 6 — Generate peak-hour traffic routes.
Single unified randomTrips call → probabilistic type assignment → duarouter.
"""

import os
import sys
import subprocess
import random
import xml.etree.ElementTree as ET

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE   = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
TRIPS_FILE = os.path.join(BASE_DIR, "routes", "trips.xml")
ROUTES_FILE = os.path.join(BASE_DIR, "routes", "routes.rou.xml")

SUMO_HOME  = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
RANDOM_TRIPS = os.path.join(SUMO_HOME, "tools", "randomTrips.py")

# Peak-hour simulation params
SIM_END     = 3600
PERIOD      = 1.5       # ~2400 trips in 3600s
FRINGE_FACTOR = 5

# Vehicle type distribution (must sum to 1.0)
VTYPES = ["car", "bike", "bus", "truck", "auto", "ambulance"]
WEIGHTS = [0.60, 0.25, 0.05, 0.05, 0.04, 0.01]

random.seed(42)  # reproducibility


def run(cmd: list[str], label: str):
    print(f"\n[{label}] Running:\n  " + " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, text=True)
    if result.returncode not in (0, 1):   # randomTrips exits 1 for warnings
        sys.exit(f"[{label}] Failed (exit {result.returncode})")
    print(f"[{label}] Done.")


def step1_generate_trips():
    """Run randomTrips.py to generate raw trips."""
    os.makedirs(os.path.dirname(TRIPS_FILE), exist_ok=True)
    cmd = [
        sys.executable, RANDOM_TRIPS,
        "-n", NET_FILE,
        "-o", TRIPS_FILE,
        "--end",          str(SIM_END),
        "--period",       str(PERIOD),
        "--fringe-factor", str(FRINGE_FACTOR),
        "--validate",
    ]
    run(cmd, "randomTrips")


def step2_assign_types():
    """Assign vehicle type to each trip probabilistically."""
    if not os.path.exists(TRIPS_FILE):
        sys.exit(f"[assign_types] Trips file not found: {TRIPS_FILE}")

    ET.register_namespace("", "")
    tree = ET.parse(TRIPS_FILE)
    root = tree.getroot()

    trips = root.findall("trip")
    if not trips:
        # Some versions of randomTrips write <vehicle> elements
        trips = root.findall("vehicle")

    assigned = {v: 0 for v in VTYPES}
    for trip in trips:
        vtype = random.choices(VTYPES, weights=WEIGHTS, k=1)[0]
        trip.set("type", vtype)
        assigned[vtype] += 1

    tree.write(TRIPS_FILE, encoding="unicode", xml_declaration=True)
    print(f"[assign_types] Assigned types to {len(trips)} trips:")
    for vt, cnt in assigned.items():
        print(f"  {vt}: {cnt} ({cnt/max(len(trips),1)*100:.1f}%)")


def step3_duarouter():
    """Convert trips to routes using duarouter."""
    cmd = [
        "duarouter",
        "--net-file",    NET_FILE,
        "--route-files", TRIPS_FILE,
        "--output-file", ROUTES_FILE,
        "--ignore-errors", "true",
        "--no-step-log",  "true",
        "--no-warnings",
    ]
    run(cmd, "duarouter")

    if not os.path.exists(ROUTES_FILE):
        sys.exit("[duarouter] routes.rou.xml was not created.")

    size_kb = os.path.getsize(ROUTES_FILE) / 1024
    print(f"[duarouter] Route file size: {size_kb:.1f} KB → {ROUTES_FILE}")


if __name__ == "__main__":
    if not os.path.exists(NET_FILE):
        sys.exit(f"Network file not found: {NET_FILE}\nRun build_network.py first.")
    if not os.path.exists(RANDOM_TRIPS):
        sys.exit(f"randomTrips.py not found at: {RANDOM_TRIPS}\nCheck SUMO_HOME.")

    step1_generate_trips()
    step2_assign_types()
    step3_duarouter()

    print("\n[generate_routes.py] Phase 6 complete.")
