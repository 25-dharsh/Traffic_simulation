"""
Phase 3 — Convert OSM to SUMO road network using netconvert.
Phase 4 — Import buildings/polygons using polyconvert.
Revised to support two-pass network building for TLS expansion.
"""

import os
import sys
import subprocess
import xml.etree.ElementTree as ET

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OSM_FILE        = os.path.join(BASE_DIR, "data", "osm",       "chennai.osm")
NET_FILE        = os.path.join(BASE_DIR, "data", "network",   "chennai.net.xml")
TEMP_NET_FILE   = os.path.join(BASE_DIR, "data", "network",   "temp.net.xml")
NOD_FILE        = os.path.join(BASE_DIR, "data", "network",   "tls_nodes.nod.xml")
BUILDINGS_FILE  = os.path.join(BASE_DIR, "data", "buildings", "buildings.poly.xml")

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
TYPEMAP   = os.path.join(SUMO_HOME, "data", "typemap", "osmPolyconvert.typ.xml")


def run(cmd: list[str], label: str):
    print(f"\n[{label}] Running:\n  " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        sys.exit(f"[{label}] FAILED with return code {result.returncode}")
    print(f"[{label}] Success.")


def build_network():
    if not os.path.exists(OSM_FILE):
        sys.exit(f"[build_network] OSM file not found: {OSM_FILE}")

    os.makedirs(os.path.dirname(NET_FILE), exist_ok=True)

    # Pass 1: OSM to Temp Network
    cmd1 = [
        "netconvert",
        "--osm-files",              OSM_FILE,
        "--output-file",            TEMP_NET_FILE,
        "--geometry.remove",
        "--roundabouts.guess",
        "--ramps.guess",
        "--tls.guess-signals",
        "--tls.default-type",       "static",
        "--default.speed",          "13.9",
        "--junctions.join",
        "--remove-edges.isolated",
        "--osm.turn-lanes",
        "--osm.sidewalks",
        "--osm.crossings",
        "--crossings.guess",
        "--sidewalks.guess",
        "--sidewalks.guess.min-speed", "5",
        "--keep-edges.by-vclass",   "passenger,bicycle,pedestrian,bus",
        "--no-warnings",
    ]
    run(cmd1, "netconvert (Pass 1)")

    # Pass 2: Apply TLS Node Conversions if file exists
    if os.path.exists(NOD_FILE):
        cmd2 = [
            "netconvert",
            "--sumo-net-file", TEMP_NET_FILE,
            "--node-files",     NOD_FILE,
            "--output-file",    NET_FILE,
            "--junctions.join-turns",
            "--no-warnings",
        ]
        run(cmd2, "netconvert (Pass 2 - TLS Nodes)")
    else:
        # Just rename temp to final if no nodes file
        if os.path.exists(NET_FILE): os.remove(NET_FILE)
        os.rename(TEMP_NET_FILE, NET_FILE)
        print("[build_network] No node file found, used Pass 1 output.")

    if os.path.exists(TEMP_NET_FILE):
        os.remove(TEMP_NET_FILE)

    print(f"[build_network] Phase 3 complete → {NET_FILE}")


def build_polygons():
    if not os.path.exists(NET_FILE):
        sys.exit(f"[build_polygons] Network file not found: {NET_FILE}")
    os.makedirs(os.path.dirname(BUILDINGS_FILE), exist_ok=True)
    cmd = [
        "polyconvert",
        "--net-file",   NET_FILE,
        "--osm-files",  OSM_FILE,
        "--type-file",  TYPEMAP,
        "--output-file", BUILDINGS_FILE,
    ]
    run(cmd, "polyconvert")
    print(f"[build_polygons] Phase 4 complete → {BUILDINGS_FILE}")


if __name__ == "__main__":
    build_network()
    build_polygons()
