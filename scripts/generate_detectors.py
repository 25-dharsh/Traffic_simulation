import os
import xml.etree.ElementTree as ET
import sumolib

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE  = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
DET_FILE  = os.path.join(BASE_DIR, "detectors", "detectors.add.xml")
DET_OUT   = os.path.join(BASE_DIR, "detectors", "det_output.xml")

def generate_detectors():
    print(f"Loading network {NET_FILE}...")
    net = sumolib.net.readNet(NET_FILE)
    
    os.makedirs(os.path.dirname(DET_FILE), exist_ok=True)
    additional = ET.Element("additional")
    
    count = 0
    # Place laneAreaDetectors at all traffic lights to measure queue length
    for node in net.getNodes():
        if node.getType() in ('traffic_light', 'traffic_light_unregulated', 'traffic_light_right_on_red'):
            node_id = node.getID()
            for edge in node.getIncoming():
                for lane in edge.getLanes():
                    lane_id = lane.getID()
                    length = lane.getLength()
                    
                    if length < 5.0: continue
                    
                    # LaneAreaDetector (E2) covers the whole lane or a significant part
                    # We'll use it to measure the jam length
                    ET.SubElement(additional, "laneAreaDetector",
                                  id=f"det_{node_id}_{lane_id}",
                                  lane=lane_id,
                                  pos="0",
                                  endPos=f"{length:.2f}",
                                  freq="60",
                                  file="det_output.xml")
                    count += 1
                    
    ET.indent(additional, space="  ")
    ET.ElementTree(additional).write(DET_FILE, encoding="unicode", xml_declaration=True)
    print(f"Generated {count} E2 detectors → {DET_FILE}")

if __name__ == "__main__":
    generate_detectors()
