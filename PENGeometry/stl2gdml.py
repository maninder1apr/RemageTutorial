#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
import pyg4ometry as pg4
import xml.etree.ElementTree as ET

# -----------------------------
# Files
# -----------------------------
remage_gdml_file = "../HPGe_with_PEN_optical.gdml"
stl_file = "PEN-L.STL"
output_gdml_file = "merged_remage_pen.gdml"

# -----------------------------
# Create registry
# -----------------------------
reg = g4.Registry()

# -----------------------------
# Define PEN material
# -----------------------------
C = g4.ElementSimple("Carbon", "C", 6, 12.01, registry=reg)
H = g4.ElementSimple("Hydrogen", "H", 1, 1.008, registry=reg)
O = g4.ElementSimple("Oxygen", "O", 8, 16.00, registry=reg)

pen = g4.Material(
    name="PEN",
    density=1.3,
    number_of_components=3,
    state="solid",
    temperature=293.15,
    registry=reg,
)
pen.add_element_natoms(C, 14)
pen.add_element_natoms(H, 10)
pen.add_element_natoms(O, 4)
# -----------------------------
# Load STL as TessellatedSolid
# -----------------------------
# tessellated solid with registry
tess_name = "PEN_stl"
solid_pen = solid.TessellatedSolid(tess_name, reg)
solid_pen.readSTL(stl_file, registry=reg)  # properly registers facets

# Create logical volume
lv_pen = g4.LogicalVolume(solid_pen, pen, "PEN_stl_lv", registry=reg)

# -----------------------------
# Parse Remage GDML
# -----------------------------
tree = ET.parse(remage_gdml_file)
root = tree.getroot()

# Add PEN material if not already present
materials_tag = root.find("materials")
if not any(mat.get("name") == "PEN" for mat in materials_tag):
    pen_mat_tag = ET.Element("material")
    pen_mat_tag.set("name", "PEN")
    materials_tag.append(pen_mat_tag)

# Add tessellated solid
solids_tag = root.find("solids")
solid_tag = ET.Element("tessellated")
solid_tag.set("name", "PEN_stl")
solids_tag.append(solid_tag)

# Add logical volume
structure_tag = root.find("structure")
lv_tag = ET.Element("volume")
lv_tag.set("name", "PEN_stl_lv")
structure_tag.append(lv_tag)

# Place PEN inside LAr_lv
lar_lv_tag = structure_tag.find(".//volume[@name='LAr_lv']")
phys_tag = ET.Element("physvol")
vol_ref = ET.Element("volumeref")
vol_ref.set("ref", "PEN_stl_lv")
pos_tag = ET.Element("position")
pos_tag.set("name", "PEN_pos")
pos_tag.set("unit", "cm")
pos_tag.set("x", "0")
pos_tag.set("y", "0")
pos_tag.set("z", "0")
phys_tag.append(vol_ref)
phys_tag.append(pos_tag)
lar_lv_tag.append(phys_tag)

# -----------------------------
# Write merged GDML
# -----------------------------
tree.write(output_gdml_file, encoding="utf-8", xml_declaration=True)
print(f"Merged GDML written to: {output_gdml_file}")
