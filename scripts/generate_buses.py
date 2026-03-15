import sumolib
import os
import random
import xml.etree.ElementTree as ET
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NET_FILE = os.path.join(BASE_DIR, "data", "network", "chennai.net.xml")
BUS_STOPS_FILE = os.path.join(BASE_DIR, "additional", "bus_stops.add.xml")
BUS_ROUTES_FILE = os.path.join(BASE_DIR, "routes", "bus_routes.rou.xml")

def generate_buses():
    print(f"Loading network {NET_FILE}...")
    net = sumolib.net.readNet(NET_FILE)
    edges = net.getEdges()
    
    routes = []
    
    # Generate 15 valid bus routes
    random.seed(42)
    attempts = 0
    while len(routes) < 15 and attempts < 10000:
        attempts += 1
        e1 = random.choice(edges)
        e2 = random.choice(edges)
        if e1 == e2: continue
        path_info = net.getShortestPath(e1, e2)
        if path_info and path_info[0] is not None:
            path, cost = path_info
            if cost > 3000:  # > 3km
                routes.append(path)
                
    os.makedirs(os.path.dirname(BUS_STOPS_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(BUS_ROUTES_FILE), exist_ok=True)
    
    stops_root = ET.Element("additional")
    routes_root = ET.Element("routes")
    
    bus_stop_index = 0
    bus_id_index = 0
    
    for route_idx, path in enumerate(routes):
        route_id = f"bus_route_{route_idx}"
        edges_str = " ".join([e.getID() for e in path])
        # Define route
        ET.SubElement(routes_root, "route", id=route_id, edges=edges_str)
        
        # Place bus stops
        accumulated_dist = 0
        last_stop_dist = 0
        stops_for_this_route = []
        
        for edge in path:
            length = edge.getLength()
            accumulated_dist += length
            
            # Place bus stop every 500-800m
            if accumulated_dist - last_stop_dist > random.randint(500, 800):
                lane = edge.getLanes()[0].getID()  # Rightmost lane
                stop_id = f"busStop_{bus_stop_index}"
                bus_stop_index += 1
                
                end_pos = min(length, length) - 1.0 # 1m from end
                start_pos = max(0.0, end_pos - 15.0) # 15m long
                    
                ET.SubElement(stops_root, "busStop", id=stop_id, lane=lane, startPos=f"{start_pos:.2f}", endPos=f"{end_pos:.2f}", friendlyPos="true")
                stops_for_this_route.append(stop_id)
                last_stop_dist = accumulated_dist
        
        # Create buses for this route departing every 500s
        for dep_time in range(0, 3600, 500):
            veh = ET.SubElement(routes_root, "vehicle", id=f"pt_bus_{bus_id_index}", type="bus", route=route_id, depart=str(dep_time))
            bus_id_index += 1
            for stop in stops_for_this_route:
                duration = random.randint(20, 30)
                ET.SubElement(veh, "stop", busStop=stop, duration=str(duration))
                
    ET.indent(stops_root, space="  ")
    ET.ElementTree(stops_root).write(BUS_STOPS_FILE, encoding="unicode", xml_declaration=True)
    
    ET.indent(routes_root, space="  ")
    ET.ElementTree(routes_root).write(BUS_ROUTES_FILE, encoding="unicode", xml_declaration=True)
    
    print(f"Generated {bus_stop_index} bus stops.")
    print(f"Generated {len(routes)} bus routes and {bus_id_index} public transport vehicles.")

if __name__ == "__main__":
    generate_buses()
