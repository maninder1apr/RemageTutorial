#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
"""
Merge STL-converted PEN GDML into a Remage-generated GDML
and place it as a scintillator in the LAr volume.
"""

import pyg4ometry.geant4 as g4
from pyg4ometry.gdml import Reader, Writer
from pyg4ometry.geant4 import Material, ElementSimple, PhysicalVolume
from legendoptics.pen import (
    pyg4_pen_attach_rindex,
    pyg4_pen_attach_attenuation,
    pyg4_pen_attach_wls,
    pyg4_pen_attach_scintillation,
)
from pygeomtools import RemageDetectorInfo
from pyg4ometry import visualisation as vis


# -----------------------------
# Input & Output GDML
# -----------------------------
remage_gdml = "HPGe_with_PEN_optical.gdml"
stl_gdml    = "PENGeometry/PEN-L.gdml"
merged_gdml = "HPGe_with_PEN_and_STL.gdml"

# -----------------------------
# Create a fresh registry
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

# Attach optical properties
pyg4_pen_attach_rindex(pen, reg)
pyg4_pen_attach_attenuation(pen, reg)
pyg4_pen_attach_wls(pen, reg)
pyg4_pen_attach_scintillation(pen, reg)

'''
# -----------------------------
# Read GDML files into separate registries
# -----------------------------
remage_reader = Reader(remage_gdml)   # returns a Registry
remage_reg    = remage_reader  # Reader itself is a Registry-like object
stl_reader    = Reader(stl_gdml)
stl_reg       = stl_reader     # same here
'''

# -----------------------------
# Read GDML files into separate registries
# -----------------------------
remage_reader = Reader(remage_gdml)
remage_reg = remage_reader.getRegistry()  # ✅ This works

stl_reader = Reader(stl_gdml)
stl_reg = stl_reader.getRegistry()


print("Remage logical volumes:")
for name, lv in remage_reg.logicalVolumeDict.items():
    print(" -", name)

print("STL logical volumes:")
for name, lv in stl_reg.logicalVolumeDict.items():
    print(" -", name)

# Rename duplicate "PEN" material in STL registry to avoid conflict
for mat in getattr(stl_reg, "materialList", []):
    if mat.name == "PEN":
        print(f"Renaming material {mat.name} to PEN_STL to avoid duplicates")
        mat.name = "PEN_STL"

# Update logical volumes that reference PEN material
for lv_name, lv in stl_reg.logicalVolumeDict.items():
    if lv.material and lv.material.name == "PEN":
        print(f"Updating material of logical volume {lv_name} from PEN to PEN_STL")
        lv.material.name = "PEN_STL"

print("\nSTL solids:")
for s in stl_reg.solidDict.keys():
    print(" -", s)

print("\nSTL logical volumes:")
for lv in stl_reg.logicalVolumeDict.keys():
    print(" -", lv)

print("\nSTL physical volumes:")
for pv in getattr(stl_reg, "physicalVolumeList", []):
    print(" -", pv.name)


# Rename STL PEN material before merge
for mat in stl_reg.materialList:
    if 'PEN' in mat.name:
        mat.name = 'PEN_stl'

# Update logical volumes to use renamed material
for lv in stl_reg.logicalVolumeDict.values():
    if lv.material and 'PEN' in lv.material.name:
        lv.material.name = 'PEN_stl'

# -----------------------------
# Merge STL registry into Remage registry
# -----------------------------

# 1️⃣ Merge defineDict entries (positions, rotations, etc.)
for name, obj in stl_reg.defineDict.items():
    new_name = name
    # Ensure unique keys if there is overlap
    while new_name in remage_reg.defineDict:
        new_name += "_stl"
    obj.name = new_name
    remage_reg.defineDict[new_name] = obj

print(f"Total defines in merged registry: {len(remage_reg.defineDict)}")
print("Sample define keys:", list(remage_reg.defineDict.keys())[:10])

# 2️⃣ Merge materials
for mat in getattr(stl_reg, "materialList", []):
    if all(mat.name != m.name for m in remage_reg.materialList):
        remage_reg.materialList.append(mat)

# Remove duplicate materials by name, keeping first occurrence
unique_mats = {}
new_material_list = []
for mat in remage_reg.materialList:
    if mat.name not in unique_mats:
        unique_mats[mat.name] = True
        new_material_list.append(mat)
    else:
        print(f"Duplicate material removed: {mat.name}")
remage_reg.materialList = new_material_list

# Re-attach PEN optical properties to the merged PEN material
pen_material = next((m for m in remage_reg.materialList if m.name == "PEN"), None)
if pen_material is not None:
    pyg4_pen_attach_rindex(pen_material, remage_reg)
    pyg4_pen_attach_attenuation(pen_material, remage_reg)
    pyg4_pen_attach_wls(pen_material, remage_reg)
    pyg4_pen_attach_scintillation(pen_material, remage_reg)

# 3️⃣ Merge solids
for name, solid_obj in getattr(stl_reg, "solidDict", {}).items():
    if name not in remage_reg.solidDict:
        remage_reg.solidDict[name] = solid_obj

# 4️⃣ Merge logical volumes
for name, lv in stl_reg.logicalVolumeDict.items():
    if name not in remage_reg.logicalVolumeDict:
        remage_reg.logicalVolumeDict[name] = lv

# 5️⃣ Merge physical volumes
for pv_name, pv in stl_reg.physicalVolumeDict.items():
    if pv_name not in remage_reg.physicalVolumeDict:
        remage_reg.physicalVolumeDict[pv_name] = pv

# Print counts
print(f"Total solids in merged registry: {len(remage_reg.solidDict)}")
print(f"Total logical volumes in merged registry: {len(remage_reg.logicalVolumeDict)}")
print(f"Total physical volumes in merged registry: {len(remage_reg.physicalVolumeDict)}")



# -----------------------------
# Place STL PEN in LAr
# -----------------------------

def find_logical_volume(registry, name):
    try:
        return registry.logicalVolumeDict[name]
    except KeyError:
        raise ValueError(f"Logical volume '{name}' not found in registry.")


# Automatically pick the first logical volume from STL GDML
pen_lv_name = list(stl_reg.logicalVolumeDict.keys())[0]
pen_lv = find_logical_volume(stl_reg, pen_lv_name)
print(f"Using STL logical volume: {pen_lv_name}")


lar_lv = find_logical_volume(remage_reg, "LAr_lv")
world_lv = find_logical_volume(remage_reg, "World_lv")
#pen_lv = find_logical_volume(stl_reg, "log_PEN0x600003544320")  # use actual name seen in STL



print(f"pen_lv type: {type(pen_lv)}")
print(f"lar_lv type: {type(lar_lv)}")
print(f"reg type: {type(remage_reg)}")


# Define the locations where you want PEN placed (x, y, z in mm)
pen_positions = [
    [0, 0, 60],
    [0, 0, -90],
    [0, 0, 0]
]

for i, pos in enumerate(pen_positions):
    phys_name = f"PEN_stl_pv_{i}"  # unique name for each copy
    phys_pen = PhysicalVolume(
        [0, 0, 0],      # rotation
        pos,             # position
        pen_lv,          # logicalVolume
        phys_name,       # name
        lar_lv,          # motherVolume
        remage_reg       # registry
    )

    # Attach detector info if not already present
    if not hasattr(phys_pen, "pygeom_active_detector"):
        phys_pen.pygeom_active_detector = RemageDetectorInfo(
            "scintillator",
            100,
            {"name": "PEN_stl"}
        )
    else:
        print(f"Detector info already set for {phys_pen.name}. Skipping assignment.")


'''
phys_pen = PhysicalVolume(
    [0, 0, 0],      # rotation
    [0, 0, 0],      # position
    pen_lv,         # logicalVolume (daughter volume)
    "PEN_stl_pv",   # name (string)
    lar_lv,         # motherVolume
    remage_reg      # registry (optional keyword argument)
)


if not hasattr(phys_pen, "pygeom_active_detector"):
    phys_pen.pygeom_active_detector = RemageDetectorInfo(
        "scintillator",
        100,
        {"name": "PEN_stl"}
    )
else:
    print(f"Detector info already set for {phys_pen.name}. Skipping assignment.")

'''

print("\nPhysical Volumes in registry:")
for pv_name, pv in remage_reg.physicalVolumeDict.items():
    mother_name = pv.motherVolume.name if pv.motherVolume else "None"
    print(f"PV '{pv_name}' inside mother '{mother_name}'")


print("\nPhysical Volumes in registry:")
for pv_name, pv in remage_reg.physicalVolumeDict.items():
    mother_name = pv.motherVolume.name if pv.motherVolume else "None"
    print(f"PV '{pv_name}' inside mother '{mother_name}'")

# Add your snippet here:
print("\nPhysical Volumes and their mother volumes:")
for pv_name, pv in remage_reg.physicalVolumeDict.items():
    mother_name = pv.motherVolume.name if pv.motherVolume else "None"
    print(f"PV '{pv_name}' inside mother '{mother_name}'")

# Also check PEN material usage
print("\nMaterials in merged registry:")
for mat in remage_reg.materialList:
    print(f"Material: {mat.name}")

# Check PEN_stl logical volume material
pen_lv = remage_reg.logicalVolumeDict.get('PEN_stl_lv0x6000028bd540', None)
if pen_lv and pen_lv.material:
    print(f"\nLogical volume 'PEN_stl_lv0x6000028bd540' uses material '{pen_lv.material.name}'")
else:
    print("\nPEN_stl_lv0x6000028bd540 or its material not found!")

print("\nPhysical Volumes and their mother volumes:")
for pv_name, pv in remage_reg.physicalVolumeDict.items():
    mother_name = pv.motherVolume.name if pv.motherVolume else "None"
    print(f"PV '{pv_name}' inside mother '{mother_name}'")

print("\nMaterials in merged registry:")
for mat in remage_reg.materialList:
    print(f"Material: {mat.name}")

pen_lv = remage_reg.logicalVolumeDict.get('PEN_stl_lv0x6000028bd540', None)
if pen_lv and pen_lv.material:
    print(f"\nLogical volume 'PEN_stl_lv0x6000028bd540' uses material '{pen_lv.material.name}'")
else:
    print("\nPEN_stl_lv0x6000028bd540 or its material not found!")



# -----------------------------
# Write merged GDML
# -----------------------------
writer = Writer()
writer.addDetector(remage_reg)
writer.write(merged_gdml)

print(f"[OK] Merged GDML written to: {merged_gdml}")

print("\n========== MERGED REGISTRY SUMMARY ==========")

# Solids
print(f"Total solids: {len(remage_reg.solidDict)}")
print("Sample solids:", list(remage_reg.solidDict.keys())[:10])

# Logical Volumes
print(f"Total logical volumes: {len(remage_reg.logicalVolumeDict)}")
print("Sample logical volumes:", list(remage_reg.logicalVolumeDict.keys())[:10])

# Physical Volumes
print(f"Total physical volumes: {len(remage_reg.physicalVolumeDict)}")
print("Sample physical volumes:", list(remage_reg.physicalVolumeDict.keys())[:10])

# Materials
print(f"Total materials: {len(remage_reg.materialList)}")
print("Materials:")
for mat in remage_reg.materialList:
    print(f" - {mat.name}")

# Define objects (positions, rotations, etc.)
if hasattr(remage_reg, "defineDict"):
    print(f"Total define objects: {len(remage_reg.defineDict)}")
    print("Sample defines:", list(remage_reg.defineDict.keys())[:10])
else:
    print("No defineDict found in registry.")

print("============================================")
# -----------------------------
# Optional: Visualize the merged geometry using VTK
# -----------------------------
viewer = vis.VtkViewerColoured(
    materialVisOptions={
        "LAr": [0, 0, 1, 0.1],
        "PEN": [0, 0.5, 0.5, 0.3],
        "G4_Galactic": [0.5, 0.5, 0.5, 0.2],
    }
)
viewer.addLogicalVolume(remage_reg.getWorldVolume())  # Use your merged registry
viewer.view()
