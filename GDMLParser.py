#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
import xml.etree.ElementTree as ET

# Load GDML file
#gdml_file = "PENGeometry/PEN_stl.gdml"
gdml_file = "HPGe_with_PEN_and_STL.gdml"
tree = ET.parse(gdml_file)
root = tree.getroot()
# List materials
materials = root.find("materials")
if materials is not None:
    print("Materials:")
    for mat in materials.findall("material"):
        print("  -", mat.get("name"))

# List solids
solids = root.find("solids")
if solids is not None:
    print("\nSolids:")
    for solid in solids:
        print("  -", solid.get("name"), "type:", solid.tag)

# List volumes
structure = root.find("structure")
if structure is not None:
    print("\nVolumes:")
    for vol in structure.findall("volume"):
        print("  -", vol.get("name"))

# List physical volumes and positions
print("\nPhysical Volumes:")
for vol in structure.findall("volume"):
    for physvol in vol.findall("physvol"):
        vol_ref = physvol.find("volumeref")
        if vol_ref is not None:
            pos = physvol.find("position")
            if pos is not None:
                x = pos.get("x")
                y = pos.get("y")
                z = pos.get("z")
                unit = pos.get("unit")
                print(f"  - {vol_ref.get('ref')} at ({x}, {y}, {z}) {unit}")
