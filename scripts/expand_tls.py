"""
Phase 5 — Identify major intersections and mark them for TLS conversion.
Generates a SUMO node file (.nod.xml) to force requested junctions to type="traffic_light".
"""

import os
import xml.etree.ElementTree as ET

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE  = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
NOD_FILE  = os.path.join(BASE_DIR, "data", "network", "tls_nodes.nod.xml")

def generate_tls_nodes():
    if not os.path.exists(NET_FILE):
        print(f"[expand_tls] Network not found, skipping node identification. Run build_network first.")
        return

    tree = ET.parse(NET_FILE)
    root = tree.getroot()

    junction_targets = []
    
    for j in root.findall("junction"):
        if j.get("type") == "internal":
            continue
        
        inc_lanes = j.get("incLanes", "")
        if not inc_lanes:
            continue
            
        edge_ids = set()
        for lane in inc_lanes.split():
            edge_id = lane.rsplit("_", 1)[0]
            edge_ids.add(edge_id)
            
        if len(edge_ids) > 3:
            # Mark for conversion if it lacks a signal
            if j.get("type") not in ("traffic_light", "traffic_light_unregulated", "traffic_light_right_on_red"):
                junction_targets.append(j.get("id"))

    if not junction_targets:
        print("[expand_tls] No new major intersections found for conversion.")
        # Create empty nodes file to avoid build errors if expected
        nodes_root = ET.Element("nodes")
        ET.ElementTree(nodes_root).write(NOD_FILE)
        return

    nodes_root = ET.Element("nodes")
    for j_id in junction_targets:
        ET.SubElement(nodes_root, "node", id=str(j_id), type="traffic_light")

    os.makedirs(os.path.dirname(NOD_FILE), exist_ok=True)
    ET.indent(nodes_root, space="  ")
    tree_out = ET.ElementTree(nodes_root)
    tree_out.write(NOD_FILE, encoding="unicode", xml_declaration=True)
    
    print(f"[expand_tls] Identified {len(junction_targets)} junctions for TLS conversion.")
    print(f"[expand_tls] Created {NOD_FILE}")

if __name__ == "__main__":
    generate_tls_nodes()
