import math
import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
import pyg4ometry as pg4
import pygeomtools
from legendhpges import make_hpge
from legendoptics.pen import (
    pyg4_pen_attach_rindex,
    pyg4_pen_attach_attenuation,
    pyg4_pen_attach_wls,
    pyg4_pen_attach_scintillation,
)
from pygeomtools import RemageDetectorInfo
from numpy import pi

reg = g4.Registry()

# If you don’t have pygeomtools.detector_origins, define your own:
def add_detector_origin(name, pv, registry):
    if not hasattr(registry, "detector_origins"):
        registry.detector_origins = {}
    registry.detector_origins[name] = {
        "xloc": pv.position[0],
        "yloc": pv.position[1],
        "zloc": pv.position[2],
    }

# -----------------------------
# Define PEN material
# -----------------------------
C = g4.ElementSimple("Carbon", "C", 6, 12.01, registry=reg)
H = g4.ElementSimple("Hydrogen", "H", 1, 1.008, registry=reg)
O = g4.ElementSimple("Oxygen", "O", 8, 16.00, registry=reg)

pen = g4.Material(name="PEN", density=1.3, number_of_components=3, registry=reg)
pen.add_element_natoms(C, 14)
pen.add_element_natoms(H, 10)
pen.add_element_natoms(O, 4)

# Attach optical properties
pyg4_pen_attach_rindex(pen, reg)
pyg4_pen_attach_attenuation(pen, reg)
pyg4_pen_attach_wls(pen, reg)
pyg4_pen_attach_scintillation(pen, reg)

# -----------------------------
# World and LAr volume
# -----------------------------
world_s = solid.Box("world_s", 50, 50, 50, registry=reg)  # large enough world
world_l = g4.LogicalVolume(world_s, "G4_Galactic", "World_lv", registry=reg)
reg.setWorld(world_l)

lar_s = pg4.geant4.solid.Orb("LAr_s", 15, registry=reg, lunit="cm")
lar_l = pg4.geant4.LogicalVolume(lar_s, "G4_lAr", "LAr_l", registry=reg)
pg4.geant4.PhysicalVolume([0, 0, 0], [0, 0, 0], lar_l, "LAr", world_l, registry=reg)

# -----------------------------
# HPGe detectors
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
        "taper": {"top": {"angle_in_deg": 45, "height_in_mm": 5}, "bottom": {"angle_in_deg": 45, "height_in_mm": 2}, "borehole": {"angle_in_deg": 0, "height_in_mm": 0}},
    },
}

bege_l = make_hpge(bege_meta, name="BEGe_L", registry=reg)
coax_l = make_hpge(coax_meta, name="Coax_L", registry=reg)

# -----------------------------
# Positions diametrically opposite along Y-axis
# -----------------------------
bege_pos = [0, +45, 0]  # 5 cm along Y
coax_pos = [0, -45, 0]  # opposite

bege_pv = pg4.geant4.PhysicalVolume([0,0,0], bege_pos, bege_l, "BEGe_pv", lar_l, registry=reg)
coax_pv = pg4.geant4.PhysicalVolume([0,0,0], coax_pos, coax_l, "Coax_pv", lar_l, registry=reg)

#bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 1, bege_meta)
#coax_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 2, coax_meta)

bege_pv.pygeom_active_detector = pygeomtools.RemageDetectorInfo(
    "germanium",
    1,
    bege_meta,
)
coax_pv.pygeom_active_detector = pygeomtools.RemageDetectorInfo(
    "germanium",
    2,
    coax_meta,
)

# -----------------------------
# PEN encapsulation around each detector
# -----------------------------
bege_radius = bege_meta["geometry"]["radius_in_mm"]
bege_half_height = bege_meta["geometry"]["height_in_mm"]/2
pen_bege_s = solid.Tubs("PEN_BEGe_s", 0, bege_radius+2, bege_half_height+2, 0, 2*math.pi, registry=reg)
pen_bege_l = g4.LogicalVolume(pen_bege_s, pen, "PEN_BEGe_lv", registry=reg)
pen_bege_pv = g4.PhysicalVolume([0,0,0], bege_pos, pen_bege_l, "PEN_BEGe_pv", lar_l, registry=reg)
pen_bege_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 3, {"name":"PEN_BEGe","material":"PEN"})

coax_radius = coax_meta["geometry"]["radius_in_mm"]
coax_half_height = coax_meta["geometry"]["height_in_mm"]/2
pen_coax_s = solid.Tubs("PEN_Coax_s", 0, coax_radius+2, coax_half_height+2, 0, 2*math.pi, registry=reg)
pen_coax_l = g4.LogicalVolume(pen_coax_s, pen, "PEN_Coax_lv", registry=reg)
pen_coax_pv = g4.PhysicalVolume([0,0,0], coax_pos, pen_coax_l, "PEN_Coax_pv", lar_l, registry=reg)
pen_coax_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 4, {"name":"PEN_Coax","material":"PEN"})

source_s = solid.Tubs("Source_s", 0, 0.25, 0.25, 0, 2*pi, registry=reg, lunit="cm")
source_l = g4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg)
g4.PhysicalVolume([0, 0, 0], [0, 0, 0, "cm"], source_l, "Source", lar_l, registry=reg)




# Register PEN around BEGe as active detector (ID 3)
pen_bege_pv.pygeom_active_detector = pygeomtools.RemageDetectorInfo(
    "scintillator",
    3,
    {
        "name": "PEN_BEGe",
        "type": "pen",
        "material": "PEN",
        "notes": "Encapsulation for BEGe detector",
    }
)

add_detector_origin("BEGe", bege_pv, reg)
add_detector_origin("Coax", coax_pv, reg)
add_detector_origin("PEN_BEGe", pen_bege_pv, reg)
add_detector_origin("PEN_Coax", pen_coax_pv, reg)


# Register PEN around Coax as active detector (ID 4)
pen_coax_pv.pygeom_active_detector = pygeomtools.RemageDetectorInfo(
    "scintillator",
    4,
    {
        "name": "PEN_Coax",
        "type": "pen",
        "material": "PEN",
        "notes": "Encapsulation for Coax detector",
    }
)



# -----------------------------
# Visualization
# -----------------------------
viewer = pg4.visualisation.VtkViewerColoured(materialVisOptions={"G4_lAr":[0,0,1,0.1], "PEN":[0,0.5,0.5,0.3]})
viewer.addLogicalVolume(reg.getWorldVolume())
viewer.view()

# -----------------------------
# Export GDML
# -----------------------------
pygeomtools.write_pygeom(reg, "HPGe_with_PEN.gdml")
