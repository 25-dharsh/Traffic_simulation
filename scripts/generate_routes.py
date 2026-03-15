"""
Phase 6 — Generate time-varying traffic routes.
Generates dynamic routes separated by periods using randomTrips, 
merges them, assigns probabilistic vehicle types, and converts to routes via duarouter.
"""

import os
import sys
import subprocess
import random
import xml.etree.ElementTree as ET

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE   = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
TRIPS_FILE = os.path.join(BASE_DIR, "routes", "trips_merged.xml")
ROUTES_FILE = os.path.join(BASE_DIR, "routes", "dynamic_routes.rou.xml")

SUMO_HOME  = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
RANDOM_TRIPS = os.path.join(SUMO_HOME, "tools", "randomTrips.py")

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


def step1_generate_and_merge_trips():
    """Run randomTrips.py to generate raw trips for each period and merge them."""
    os.makedirs(os.path.dirname(TRIPS_FILE), exist_ok=True)
    
    periods = [
        ("low", 0, 1200, 2.0),
        ("peak", 1200, 2400, 0.5),
        ("mod", 2400, 3600, 1.2)
    ]
    
    trip_files = []
    for prefix, start, end, period in periods:
        tf = os.path.join(BASE_DIR, "routes", f"trips_{prefix}.xml")
        cmd = [
            sys.executable, RANDOM_TRIPS,
            "-n", NET_FILE,
            "-o", tf,
            "--begin", str(start),
            "--end", str(end),
            "--period", str(period),
            "--prefix", prefix + "_",
            "--fringe-factor", str(FRINGE_FACTOR),
            "--validate",
        ]
        run(cmd, f"randomTrips ({prefix})")
        trip_files.append(tf)

    print("\n[merge_trips] Merging trip files...")
    root = ET.Element("routes")
    
    for tf in trip_files:
        if not os.path.exists(tf):
            sys.exit(f"Trip file not found: {tf}")
        tree = ET.parse(tf)
        # Some versions of randomTrips write <trip> elements, some write <vehicle>
        for child in tree.getroot():
            root.append(child)
            
    print(f"[merge_trips] Total trips loaded: {len(list(root))}")
    
    # Assign types
    assigned = {v: 0 for v in VTYPES}
    trips = list(root)
    for trip_elem in trips:
        vtype = random.choices(VTYPES, weights=WEIGHTS, k=1)[0]
        trip_elem.set("type", vtype)
        assigned[vtype] += 1
        
    print(f"[assign_types] Assigned types:")
    for vt, cnt in assigned.items():
        print(f"  {vt}: {cnt} ({cnt/max(len(trips),1)*100:.1f}%)")
        
    # Sort trips by depart time
    def get_depart(elem):
        dep = elem.get("depart")
        return float(dep) if dep else 0.0
    
    trips.sort(key=get_depart)
    
    # clear and append sorted
    for child in list(root):
        root.remove(child)
    root.extend(trips)
    
    ET.ElementTree(root).write(TRIPS_FILE, encoding="unicode", xml_declaration=True)
    print(f"[merge_trips] Saved merged and sorted trips to {TRIPS_FILE}")


def step2_duarouter():
    """Convert merged trips to routes using duarouter."""
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
        sys.exit("[duarouter] dynamic_routes.rou.xml was not created.")

    size_kb = os.path.getsize(ROUTES_FILE) / 1024
    print(f"[duarouter] Route file size: {size_kb:.1f} KB → {ROUTES_FILE}")


if __name__ == "__main__":
    if not os.path.exists(NET_FILE):
        sys.exit(f"Network file not found: {NET_FILE}\nRun build_network.py first.")
    if not os.path.exists(RANDOM_TRIPS):
        sys.exit(f"randomTrips.py not found at: {RANDOM_TRIPS}\nCheck SUMO_HOME.")

    step1_generate_and_merge_trips()
    step2_duarouter()

    print("\n[generate_routes.py] Time-varying traffic demand generation complete.")
