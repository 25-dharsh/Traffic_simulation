"""
Phase 3 — Convert OSM to SUMO road network using netconvert.
Phase 4 — Import buildings/polygons using polyconvert.
"""

import os
import sys
import subprocess
import xml.etree.ElementTree as ET

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OSM_FILE        = os.path.join(BASE_DIR, "data", "osm",       "chennai.osm")
NET_FILE        = os.path.join(BASE_DIR, "data", "network",   "chennai.net.xml")
BUILDINGS_FILE  = os.path.join(BASE_DIR, "data", "buildings", "buildings.poly.xml")

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
TYPEMAP   = os.path.join(SUMO_HOME, "data", "typemap", "osmPolyconvert.typ.xml")


def run(cmd: list[str], label: str):
    print(f"\n[{label}] Running:\n  " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        sys.exit(f"[{label}] FAILED with return code {result.returncode}")
    print(f"[{label}] Success.")


# ── Phase 3: netconvert ───────────────────────────────────────────────────────
def build_network():
    if not os.path.exists(OSM_FILE):
        sys.exit(f"[build_network] OSM file not found: {OSM_FILE}\nRun download_osm.py first.")

    os.makedirs(os.path.dirname(NET_FILE), exist_ok=True)

    cmd = [
        "netconvert",
        "--osm-files",              OSM_FILE,
        "--output-file",            NET_FILE,
        "--geometry.remove",
        "--roundabouts.guess",
        "--ramps.guess",
        "--tls.guess-signals",
        "--tls.default-type",       "static",
        "--default.speed",          "13.9",
        "--junctions.join",
        "--remove-edges.isolated",
        "--keep-edges.by-vclass",   "passenger",
        "--no-warnings",
    ]
    run(cmd, "netconvert")

    # Verify output
    if not os.path.exists(NET_FILE):
        sys.exit("[build_network] Network file was not created.")

    tree = ET.parse(NET_FILE)
    tls_elements = tree.findall(".//tlLogic")
    print(f"[build_network] Network contains {len(tls_elements)} traffic light junction(s).")
    if len(tls_elements) == 0:
        print("[build_network] WARNING: No traffic lights found in network. TLS override will be empty.")

    print(f"[build_network] Phase 3 complete → {NET_FILE}")


# ── Phase 4: polyconvert ──────────────────────────────────────────────────────
def build_polygons():
    if not os.path.exists(NET_FILE):
        sys.exit(f"[build_polygons] Network file not found: {NET_FILE}\nRun build_network() first.")
    if not os.path.exists(TYPEMAP):
        sys.exit(f"[build_polygons] Typemap not found: {TYPEMAP}\nCheck SUMO_HOME = {SUMO_HOME}")

    os.makedirs(os.path.dirname(BUILDINGS_FILE), exist_ok=True)

    cmd = [
        "polyconvert",
        "--net-file",   NET_FILE,
        "--osm-files",  OSM_FILE,
        "--type-file",  TYPEMAP,
        "--output-file", BUILDINGS_FILE,
    ]
    run(cmd, "polyconvert")

    # Validation: check polygon variety
    if os.path.exists(BUILDINGS_FILE):
        content = open(BUILDINGS_FILE, encoding="utf-8", errors="ignore").read()
        for tag in ["building", "landuse", "park", "water"]:
            count = content.count(f'type="{tag}')
            if count == 0:
                # Try partial match
                count = content.lower().count(tag)
            print(f"  [{tag}] found ~{count} polygon(s)")
    else:
        print("[build_polygons] WARNING: buildings.poly.xml was not created.")

    print(f"[build_polygons] Phase 4 complete → {BUILDINGS_FILE}")


if __name__ == "__main__":
    build_network()
    build_polygons()
    print("\n[build_network.py] Phases 3 & 4 complete.")
