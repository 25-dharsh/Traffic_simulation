"""
Phase 7 — Generate fixed timer TLS override file.
Reads existing phase state strings from the network, only changes durations.
Green=30s, Yellow=5s, Red=30s — state strings never modified.
"""

import os
import sys
import xml.etree.ElementTree as ET

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE  = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
TLS_FILE  = os.path.join(BASE_DIR, "traffic_lights", "tls.add.xml")

# Fixed timer durations (seconds)
GREEN_DURATION  = 30
YELLOW_DURATION = 5
RED_DURATION    = 30


def generate_tls():
    if not os.path.exists(NET_FILE):
        sys.exit(f"[setup_tls] Network file not found: {NET_FILE}\nRun build_network.py first.")

    tree = ET.parse(NET_FILE)
    root = tree.getroot()

    network_tls = root.findall(".//tlLogic")
    network_tls_count = len(network_tls)
    if network_tls_count == 0:
        print("[setup_tls] WARNING: No tlLogic elements found in network.")

    os.makedirs(os.path.dirname(TLS_FILE), exist_ok=True)

    additional = ET.Element("additional")
    generated_count = 0

    for tls in network_tls:
        tls_id      = tls.get("id")
        tls_type    = tls.get("type", "static")
        program_id  = "SA_fixed"
        offset      = tls.get("offset", "0")

        logic = ET.SubElement(additional, "tlLogic",
                              id=str(tls_id),
                              type=str(tls_type),
                              programID=str(program_id),
                              offset=str(offset))

        phases = tls.findall("phase")
        if not phases:
            # Determine link count from connections for robust defaults
            connections = root.findall(f".//connection[@tl='{tls_id}']")
            link_indices = set()
            for c in connections:
                idx = c.get("linkIndex")
                if idx: link_indices.add(int(idx))
            
            num_links = max(link_indices) + 1 if link_indices else 8
            
            h1 = num_links // 2
            h2 = num_links - h1
            
            phases_data = [
                ("G"*h1 + "r"*h2, GREEN_DURATION),
                ("y"*h1 + "r"*h2, YELLOW_DURATION),
                ("r"*h1 + "G"*h2, GREEN_DURATION),
                ("r"*h1 + "y"*h2, YELLOW_DURATION),
            ]
            for state, dur in phases_data:
                ET.SubElement(logic, "phase", duration=str(dur), state=str(state))
        else:
            for phase in phases:
                state = phase.get("state", "r")
                state_lower = state.lower()
                if "y" in state_lower and state_lower.count("y") >= state_lower.count("g"):
                    dur = str(YELLOW_DURATION)
                else:
                    dur = str(GREEN_DURATION)
                ET.SubElement(logic, "phase", duration=dur, state=str(state))
            
        generated_count += 1

    ET.indent(additional, space="  ")
    tree_out = ET.ElementTree(additional)
    tree_out.write(TLS_FILE, encoding="unicode", xml_declaration=True)

    print(f"[setup_tls] Generated {generated_count} TLS overrides → {TLS_FILE}")
    print(f"[setup_tls] Signal plan: Green={GREEN_DURATION}s | Yellow={YELLOW_DURATION}s")

if __name__ == "__main__":
    generate_tls()
