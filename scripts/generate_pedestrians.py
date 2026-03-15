import os
import random
import xml.etree.ElementTree as ET
import sumolib

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE  = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
PED_ROUTES_FILE = os.path.join(BASE_DIR, "routes", "pedestrian_routes.rou.xml")

def generate_pedestrians():
    print(f"Loading network {NET_FILE}...")
    net = sumolib.net.readNet(NET_FILE)
    
    # Identify target junctions (same logic as expand_tls.py)
    target_junctions = []
    for node in net.getNodes():
        # Official traffic lights
        if node.getType() in ('traffic_light', 'traffic_light_unregulated', 'traffic_light_right_on_red'):
            target_junctions.append(node)
            continue
            
        # Major intersections (> 3 incoming edges)
        inc_edges = node.getIncoming()
        if len(inc_edges) > 3:
            target_junctions.append(node)
            
    print(f"Targeting {len(target_junctions)} intersections for pedestrians.")
    
    os.makedirs(os.path.dirname(PED_ROUTES_FILE), exist_ok=True)
    routes_root = ET.Element("routes")
    
    # Pedestrian vType
    ET.SubElement(routes_root, "vType", id="pedestrian", vClass="pedestrian", maxSpeed="1.5")
    
    count = 0
    for node in target_junctions:
        # Find edges connected to this junction that have pedestrian lanes
        edges = node.getIncoming() + node.getOutgoing()
        ped_edges = list(set([e for e in edges if e.allows("pedestrian")]))
                
        if len(ped_edges) >= 2:
            num_peds = random.randint(10, 30) # More pedestrians for realism
            for _ in range(num_peds):
                e1, e2 = random.sample(ped_edges, 2)
                depart = random.randint(0, 3500)
                ped_id = f"ped_{count}"
                
                person = ET.SubElement(routes_root, "person", id=ped_id, depart=str(depart))
                ET.SubElement(person, "walk", edges=f"{e1.getID()} {e2.getID()}")
                count += 1

    ET.indent(routes_root, space="  ")
    ET.ElementTree(routes_root).write(PED_ROUTES_FILE, encoding="unicode", xml_declaration=True)
    print(f"Generated {count} pedestrian routes.")

if __name__ == "__main__":
    generate_pedestrians()
