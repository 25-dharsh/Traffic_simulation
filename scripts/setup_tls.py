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


def classify_phase(state: str) -> str:
    """
    Classify a TLS phase state string as 'green', 'yellow', or 'red'.
    Based on the dominant character in the state string.
    """
    state_lower = state.lower()
    g_count = state_lower.count("g")
    y_count = state_lower.count("y")
    r_count = state_lower.count("r")

    if y_count > 0 and y_count >= g_count:
        return "yellow"
    elif g_count >= r_count:
        return "green"
    else:
        return "red"


def get_duration(phase_type: str) -> int:
    if phase_type == "yellow":
        return YELLOW_DURATION
    elif phase_type == "green":
        return GREEN_DURATION
    else:
        return RED_DURATION


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
                              id=tls_id,
                              type=tls_type,
                              programID=program_id,
                              offset=offset)

        phases = tls.findall("phase")
        if not phases:
            phases_data = [
                ("GGGGrrrr", 30),
                ("yyyyrrrr", 5),
                ("rrrrGGGG", 30),
                ("rrrryyyy", 5),
            ]
            for state, dur in phases_data:
                ET.SubElement(logic, "phase", duration=str(dur), state=state)
        else:
            # Preserve ALL original phase strings (colors) correctly for complex intersections
            for phase in phases:
                state = phase.get("state", "r")
                
                # Determine color class (yellow vs green/red) to assign fixed timer constraint
                state_lower = state.lower()
                if "y" in state_lower and state_lower.count("y") >= state_lower.count("g"):
                    dur = "5"
                else:
                    dur = "30"
                    
                ET.SubElement(logic, "phase", duration=dur, state=state)
            
        generated_count += 1

    ET.indent(additional, space="  ")
    tree_out = ET.ElementTree(additional)
    tree_out.write(TLS_FILE, encoding="unicode", xml_declaration=True)

    print(f"[setup_tls] Ignored classify block. Generated {generated_count} TLS overrides → {TLS_FILE}")
    print(f"[setup_tls] Signal plan: Green={GREEN_DURATION}s | Yellow={YELLOW_DURATION}s | Red={RED_DURATION}s")

    assert network_tls_count == generated_count, f"Mismatch: Network has {network_tls_count} TLS, but {generated_count} programs generated. Aborting."

if __name__ == "__main__":
    generate_tls()
    print("[setup_tls.py] Phase 7 complete.")
