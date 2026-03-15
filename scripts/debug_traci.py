import traci
import os

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
SUMO_TOOLS = os.path.join(SUMO_HOME, "tools")
import sys
if SUMO_TOOLS not in sys.path:
    sys.path.insert(0, SUMO_TOOLS)

CFG_FILE = r"C:\Fixed_timer\traffic_simulation\config\simulation.sumocfg"

sumo_cmd = [os.path.join(SUMO_HOME, "bin", "sumo.exe"), "-c", CFG_FILE]

print("Starting Traci...")
try:
    traci.start(sumo_cmd)
    print("Connected.")
    for i in range(10):
        traci.simulationStep()
        print(f"Step {i}, Vehicles: {len(traci.vehicle.getIDList())}")
    traci.close()
    print("Done.")
except Exception as e:
    print(f"Error: {e}")
