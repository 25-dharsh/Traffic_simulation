import xml.etree.ElementTree as ET
import json
import os

net_file = r'c:\Fixed_timer\traffic_simulation\data\network\chennai.net.xml'
tree = ET.parse(net_file)
root = tree.getroot()

out = {'connections': [], 'junctions': []}
count = 0
for c in root.findall('connection'):
    if c.get('from') and not c.get('from').startswith(':'):
        out['connections'].append(c.attrib)
        count += 1
        if count >= 3:
            break

count = 0
for j in root.findall('junction'):
    if j.get('type') != 'internal':
        inc = j.get('incLanes', '').split()
        if len(inc) > 3:
            out['junctions'].append(j.attrib)
            count += 1
            if count >= 3:
                break

with open('temp_out.json', 'w') as f:
    json.dump(out, f, indent=2)
