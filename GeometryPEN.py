import math
import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
import pyg4ometry.visualisation as vis
from legendhpges import make_hpge
from legendoptics.pen import (
    pyg4_pen_attach_rindex,
    pyg4_pen_attach_attenuation,
    pyg4_pen_attach_wls,
    pyg4_pen_attach_scintillation,
)
from pygeomtools import RemageDetectorInfo, write_pygeom
from numpy import pi

# -----------------------------
# Helper to register detector origins
# -----------------------------
def add_detector_origin(name, pv, registry):
    if not hasattr(registry, "detector_origins"):
        registry.detector_origins = {}
    registry.detector_origins[name] = {
        "xloc": pv.position[0],
        "yloc": pv.position[1],
        "zloc": pv.position[2],
    }

# -----------------------------
# Create Geant4 registry
# -----------------------------
reg = g4.Registry()

# -----------------------------
# Define elements
# -----------------------------
C = g4.ElementSimple("Carbon", "C", 6, 12.01, registry=reg)
H = g4.ElementSimple("Hydrogen", "H", 1, 1.008, registry=reg)
O = g4.ElementSimple("Oxygen", "O", 8, 16.00, registry=reg)
N = g4.ElementSimple("Nitrogen", "N", 7, 14.01, registry=reg)

# -----------------------------
# Create PEN material
# -----------------------------
pen = g4.Material(
    name="PEN",
    density=1.3,
    number_of_components=3,
    registry=reg
)
pen.add_element_natoms(C, 14)
pen.add_element_natoms(H, 10)
pen.add_element_natoms(O, 4)

# Attach optical properties
pyg4_pen_attach_rindex(pen, reg)
pyg4_pen_attach_attenuation(pen, reg)
pyg4_pen_attach_wls(pen, reg)
pyg4_pen_attach_scintillation(pen, reg)

# -----------------------------
# HPGe detector metadata
# -----------------------------
bege_meta = {
    "name": "B00000B",
    "type": "bege",
    "production": {"enrichment": {"val": 0.874, "unc": 0.003}, "mass_in_g": 697.0},
    "geometry": {
        "height_in_mm": 29.46,
        "radius_in_mm": 36.98,
        "groove": {"depth_in_mm": 2.0, "radius_in_mm": {"outer": 10.5, "inner": 7.5}},
        "pp_contact": {"radius_in_mm": 7.5, "depth_in_mm": 0},
        "taper": {"top": {"angle_in_deg": 0.0, "height_in_mm": 0.0}, "bottom": {"angle_in_deg": 0.0, "height_in_mm": 0.0}},
    },
}

coax_meta = {
    "name": "C000RG1",
    "type": "coax",
    "production": {"enrichment": {"val": 0.855, "unc": 0.015}},
    "geometry": {
        "height_in_mm": 40,
        "radius_in_mm": 38.25,
        "borehole": {"radius_in_mm": 6.75, "depth_in_mm": 40},
        "groove": {"depth_in_mm": 2, "radius_in_mm": {"outer": 20, "inner": 17}},
        "pp_contact": {"radius_in_mm": 17, "depth_in_mm": 0},
        "taper": {
            "top": {"angle_in_deg": 45, "height_in_mm": 5},
            "bottom": {"angle_in_deg": 45, "height_in_mm": 2},
            "borehole": {"angle_in_deg": 0, "height_in_mm": 0},
        },
    },
}

# -----------------------------
# Create world volume (20 cm radius sphere)
# -----------------------------
world_s = solid.Orb("World_s", 20, registry=reg, lunit="cm")
world_l = g4.LogicalVolume(world_s, "G4_Galactic", "World", registry=reg)
reg.setWorld(world_l)

# -----------------------------
# Liquid argon volume inside world (15 cm radius)
# -----------------------------
lar_s = solid.Orb("LAr_s", 15, registry=reg, lunit="cm")
lar_l = g4.LogicalVolume(lar_s, "G4_lAr", "LAr_l", registry=reg)
g4.PhysicalVolume([0, 0, 0], [0, 0, 0, "rad"], lar_l, "LAr", world_l, registry=reg)

# -----------------------------
# Create HPGe logical volumes
# -----------------------------
bege_l = make_hpge(bege_meta, name="BEGe_L", registry=reg)
coax_l = make_hpge(coax_meta, name="Coax_L", registry=reg)

# Place HPGe detectors inside LAr
bege_pv = g4.PhysicalVolume([0, 0, 0], [8, 0, -3, "cm"], bege_l, "BEGe", lar_l, registry=reg)
coax_pv = g4.PhysicalVolume([0, 0, 0], [-5, 0, -10, "cm"], coax_l, "Coax", lar_l, registry=reg)

# Register HPGe detectors as active
bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 1, bege_meta)
coax_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 2, coax_meta)

# -----------------------------
# Create PEN bowl solid (hemisphere)
# -----------------------------
pen_s = solid.Sphere(
    "PEN_Bowl_s",
    pRmin=5.0,
    pRmax=6.0,
    pSPhi=0.0,
    pDPhi=2*pi,
    pSTheta=0.0,
    pDTheta=pi/2,  # hemisphere
    registry=reg
)

pen_l = g4.LogicalVolume(pen_s, pen, "PEN_Bowl_l", registry=reg)
pen_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0, "rad"], pen_l, "PEN_Bowl_pv", lar_l, registry=reg)

# Register PEN as active detector (ID 4)
pen_pv.pygeom_active_detector = RemageDetectorInfo(
    "pen_scintillator",
    4,
    {
        "name": "PEN_Bowl",
        "type": "pen",
        "material": "polyethylene_naphthalate",
        "dimensions": {"inner_radius_cm": 5.0, "outer_radius_cm": 6.0, "shape": "bowl"},
        "notes": "PEN scintillator hemisphere",
    }
)

# -----------------------------
# Register detector origins
# -----------------------------
add_detector_origin("BEGe", bege_pv, reg)
add_detector_origin("Coax", coax_pv, reg)
add_detector_origin("PEN_Bowl", pen_pv, reg)

# -----------------------------
# Optional: Add small source
# -----------------------------
source_s = solid.Tubs("Source_s", 0, 1, 1, 0, 2*pi, registry=reg, lunit="cm")
source_l = g4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg)
g4.PhysicalVolume([0, 0, 0], [0, 5, 0, "cm"], source_l, "Source", lar_l, registry=reg)

# -----------------------------
# Visualization
# -----------------------------
viewer = vis.VtkViewerColoured(materialVisOptions={"G4_lAr": [0, 0, 1, 0.1]})
viewer.addLogicalVolume(reg.getWorldVolume())
viewer.renWin.SetMultiSamples(8)  # anti-aliasing
viewer.view()

# -----------------------------
# Export geometry
# -----------------------------
write_pygeom(reg, "geometry_with_pen.gdml")

# Print detector origins
print("Detector origins:")
for name, origin in reg.detector_origins.items():
    print(f"{name}: {origin}")
