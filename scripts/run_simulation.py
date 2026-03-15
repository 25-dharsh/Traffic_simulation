"""
Phase 10 — Run Simulation.
Pre-flight checks → SUMO headless via TraCI → live metrics → analytics graphs.
Separate view_gui() opens SUMO-GUI for visual inspection.
"""

import os
import sys
import time
import subprocess
import traceback
import csv
import random
import json

# ── SUMO/TraCI setup ──────────────────────────────────────────────────────────
SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
SUMO_TOOLS = os.path.join(SUMO_HOME, "tools")
if SUMO_TOOLS not in sys.path:
    sys.path.insert(0, SUMO_TOOLS)

try:
    import traci
except ImportError:
    sys.exit(
        "[run_simulation] ERROR: traci not importable.\n"
        f"  SUMO_HOME = {SUMO_HOME}\n"
        "  Make sure SUMO is installed and SUMO_HOME is correct."
    )

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CFG_FILE    = os.path.join(BASE_DIR, "config", "simulation.sumocfg")
METRICS_DIR = os.path.join(BASE_DIR, "metrics_output")

REQUIRED_FILES = [
    os.path.join(BASE_DIR, "data", "osm",       "chennai.osm"),
    os.path.join(BASE_DIR, "data", "network",   "chennai.net.xml"),
    os.path.join(BASE_DIR, "routes",             "vehicle_types.xml"),
    os.path.join(BASE_DIR, "routes",             "dynamic_routes.rou.xml"),
    os.path.join(BASE_DIR, "routes",             "bus_routes.rou.xml"),
    os.path.join(BASE_DIR, "routes",             "pedestrian_routes.rou.xml"),
    os.path.join(BASE_DIR, "traffic_lights",     "tls.add.xml"),
    os.path.join(BASE_DIR, "data", "network",    "tls_nodes.nod.xml"),
    os.path.join(BASE_DIR, "data", "buildings",  "buildings.poly.xml"),
    os.path.join(BASE_DIR, "detectors",          "detectors.add.xml"),
    os.path.join(BASE_DIR, "additional",         "bus_stops.add.xml"),
    CFG_FILE,
]

SIM_END          = 3600
METRICS_INTERVAL = 60   # sample every N simulation steps
TRACI_PORT       = 8813

# ── In-memory metric containers ────────────────────────────────────────────────
_times  = []
_waits  = []
_queues = []


# ─────────────────────────────────────────────────────────────────────────────
def preflight_check():
    """Abort with clear message if any required file is missing."""
    print("[preflight] Checking required files…")
    missing = [f for f in REQUIRED_FILES if not os.path.exists(f)]
    if missing:
        for m in missing:
            print(f"  [MISSING] {m}")
        sys.exit("\n[preflight] FATAL: Required files missing. Build the pipeline first.")
    print(f"[preflight] All {len(REQUIRED_FILES)} files present. ✓\n")


def collect_metrics(step: int):
    """Sample live TraCI metrics."""
    try:
        vehicle_ids = traci.vehicle.getIDList()
        n = len(vehicle_ids)
        if n == 0:
            _times.append(step)
            _waits.append(0.0)
            _queues.append(0)
            return
        total_wait = sum(traci.vehicle.getWaitingTime(v) for v in vehicle_ids)
        stopped    = sum(1 for v in vehicle_ids if traci.vehicle.getSpeed(v) < 0.1)
        _times.append(step)
        _waits.append(total_wait / n)
        _queues.append(stopped)
    except Exception as e:
        print(f"  [metrics warn] step {step}: {e}")


def export_metrics():
    """Write collected live metrics to CSV."""
    os.makedirs(METRICS_DIR, exist_ok=True)
    csv_path = os.path.join(METRICS_DIR, "live_metrics.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "avg_wait_s", "stopped_vehicles"])
        for t, w, q in zip(_times, _waits, _queues):
            writer.writerow([t, f"{w:.3f}", q])
    print(f"[export] Live metrics → {csv_path} ({len(_times)} rows)")


def generate_graphs():
    """Call traffic_metrics.compute_metrics() to produce PNG graphs."""
    sys.path.insert(0, SCRIPT_DIR)
    try:
        from traffic_metrics import compute_metrics
        live_data = {"times": _times, "wait": _waits, "queue": _queues}
        compute_metrics(live_data=live_data)
    except Exception as e:
        print(f"[graphs] Error: {e}")
        traceback.print_exc()

# ── Incident Management ────────────────────────────────────────────────────────
_incident_logs = []

def apply_random_incident(step: int):
    """Introduce a random traffic incident."""
    try:
        edges = traci.edge.getIDList()
        # Filter out internal/junction edges
        valid_edges = [e for e in edges if not e.startswith(":")]
        if not valid_edges:
            return

        edge_id = random.choice(valid_edges)
        incident_type = random.choice(["stalled_vehicle", "blocked_lane", "reduced_speed"])
        
        description = ""
        
        if incident_type == "stalled_vehicle":
            vehs = traci.edge.getLastStepVehicleIDs(edge_id)
            if vehs:
                target_veh = random.choice(vehs)
                # Force vehicle to stop for 120 seconds
                traci.vehicle.setStop(target_veh, edge_id, pos=10.0, duration=120)
                description = f"Vehicle {target_veh} stalled on {edge_id}"
            else:
                incident_type = "stalled_attempt_failed"
                description = f"Attempted stall on {edge_id} but no vehicles found"
                
        elif incident_type == "blocked_lane":
            lanes = traci.edge.getLaneNumber(edge_id)
            target_lane = f"{edge_id}_{random.randint(0, lanes-1)}"
            # Block the lane by setting disallowed to everything
            traci.lane.setDisallowed(target_lane, ["passenger", "bus", "truck", "motorcycle", "bicycle"])
            description = f"Lane {target_lane} manually blocked"
            
        elif incident_type == "reduced_speed":
            # Reduce speed to 2.0 m/s (approx 7 km/h)
            traci.edge.setMaxSpeed(edge_id, 2.0)
            description = f"Speed limit on {edge_id} reduced to 2.0m/s (Incident)"

        _incident_logs.append({
            "step": step,
            "type": incident_type,
            "edge": edge_id,
            "description": description
        })
        print(f"  [INCIDENT] {description} at step {step}")
        
    except Exception as e:
        print(f"  [incident error] {e}")

def export_incident_logs():
    """Save incident history to CSV."""
    csv_path = os.path.join(METRICS_DIR, "incident_logs.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "type", "edge", "description"])
        for log in _incident_logs:
            writer.writerow([log["step"], log["type"], log["edge"], log["description"]])
    print(f"[export] Incident logs → {csv_path}")
# ─────────────────────────────────────────────────────────────────────────────
def run_simulation():
    """
    Headless TraCI simulation for metrics collection.
    Uses traci.start() which internally spawns sumo and manages the port.
    """
    preflight_check()

    sumo_exe = os.path.join(SUMO_HOME, "bin", "sumo.exe")
    if not os.path.isfile(sumo_exe):
        sumo_exe = "sumo"

    sumo_cmd = [
        sumo_exe,
        "-c", CFG_FILE,
    ]

    print(f"[run_simulation] Launching: {' '.join(sumo_cmd)}\n")

    step = 0
    start_wall = time.time()

    try:
        traci.start(sumo_cmd, port=TRACI_PORT)
        print("[run_simulation] TraCI connected ✓  Running 3600 steps…\n")

        while traci.simulation.getMinExpectedNumber() > 0 or step < SIM_END:
            traci.simulationStep()
            step += 1

            if step % 600 == 0:
                apply_random_incident(step)

            if step % METRICS_INTERVAL == 0:
                n_veh   = len(traci.vehicle.getIDList())
                elapsed = time.time() - start_wall
                print(f"  Step {step:5d}/{SIM_END} | Vehicles running: {n_veh:5d} | "
                      f"Wall: {elapsed:5.1f}s")
                collect_metrics(step)

            if step >= SIM_END:
                break

        print(f"\n[run_simulation] Finished {step} steps in "
              f"{time.time()-start_wall:.1f}s.")

    except KeyboardInterrupt:
        print(f"\n[run_simulation] Interrupted at step {step}.")

    except Exception as e:
        print(f"\n[run_simulation] ERROR at step {step}: {e}")
        traceback.print_exc()

    finally:
        try:
            traci.close()
        except Exception:
            pass
        export_metrics()
        export_incident_logs()
        generate_graphs()
        elapsed_total = time.time() - start_wall
        print(f"\n[run_simulation] Total wall time: {elapsed_total:.1f}s")
        print(f"[run_simulation] Analytics in: {METRICS_DIR}/")


# ─────────────────────────────────────────────────────────────────────────────
def view_gui():
    """
    Open SUMO-GUI for visual inspection.
    Run AFTER run_simulation() — all files must exist.
    """
    preflight_check()
    sumo_gui = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe")
    if not os.path.isfile(sumo_gui):
        sumo_gui = "sumo-gui"
    print("[view_gui] Launching SUMO-GUI…")
    subprocess.Popen([sumo_gui, "-c", CFG_FILE, "--delay", "100"])
    print("[view_gui] SUMO-GUI opened. Close the window when done.")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scenario A — SUMO Simulation Runner")
    parser.add_argument("--gui", action="store_true",
                        help="Open SUMO-GUI for visual inspection only (no metrics)")
    args = parser.parse_args()

    if args.gui:
        view_gui()
    else:
        run_simulation()
