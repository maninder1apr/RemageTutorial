#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

import xml.etree.ElementTree as ET

remage_file = "HPGe_with_PEN_optical.gdml"
stl_file = "PENGeometry/PEN_stl.gdml"
output_file = "merged_pen_stl_safe.gdml"

remage_tree = ET.parse(remage_file)
remage_root = remage_tree.getroot()

stl_tree = ET.parse(stl_file)
stl_root = stl_tree.getroot()

# -----------------------------
# Append STL materials, solids, and structure as-is
# -----------------------------
for tag in ["materials", "solids", "structure"]:
    remage_elem = remage_root.find(tag)
    stl_elem = stl_root.find(tag)
    for child in stl_elem:
        remage_elem.append(child)

# -----------------------------
# Place the STL logical volume in LAr
# -----------------------------
lar_lv = remage_root.find(".//volume[@name='LAr_lv']")

# Get the STL logical volume name (should match the GDML)
stl_lv = stl_root.find(".//volume")
stl_lv_name = stl_lv.get("name")

pen_phys = ET.Element("physvol")
vol_ref = ET.Element("volumeref")
vol_ref.set("ref", stl_lv_name)
pen_phys.append(vol_ref)

pos = ET.Element("position")
pos.set("name", "PEN_stl_pos")
pos.set("unit", "cm")
pos.set("x", "0")
pos.set("y", "0")
pos.set("z", "0")
pen_phys.append(pos)

lar_lv.append(pen_phys)

remage_tree.write(output_file, encoding="utf-8", xml_declaration=True)
print(f"Merged GDML written to: {output_file}")
