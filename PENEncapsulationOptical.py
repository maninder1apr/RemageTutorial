import math
import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
import pygeomtools
import pyg4ometry as pg4
from legendhpges import make_hpge
from legendoptics.pen import (
    pyg4_pen_attach_rindex,
    pyg4_pen_attach_attenuation,
    pyg4_pen_attach_wls,
    pyg4_pen_attach_scintillation,
)
from legendoptics.lar import (
    pyg4_lar_attach_rindex,
    pyg4_lar_attach_attenuation,
    pyg4_lar_attach_scintillation,
)
from pygeomtools import RemageDetectorInfo
from numpy import pi








# -----------------------------
# Registry
# -----------------------------
reg = g4.Registry()

# -----------------------------
# Utility: add detector origins
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

# Attach optical properties to PEN
pyg4_pen_attach_rindex(pen, reg)
pyg4_pen_attach_attenuation(pen, reg)
pyg4_pen_attach_wls(pen, reg)
pyg4_pen_attach_scintillation(pen, reg)



# define LAr temperature as a pint quantity

lar_temperature = 88.8       # Temperature in Kelvin
scint_yield = 1000 / 1.0          # 1000 photons per MeV


# create the material
Ar = g4.ElementSimple("Argon", "Ar", 18, 39.95, registry=reg)

lar = g4.Material(
    name="LAr",
    density=1.390,           # g/cm3
    number_of_components=1,
    state="liquid",
    temperature=lar_temperature,  # use pint Quantity
    pressure=1e5,             # Pa
    registry=reg
)
lar.add_element_natoms(Ar, 1)

# Attach optical properties with proper units
pyg4_lar_attach_rindex(lar, reg)
pyg4_lar_attach_attenuation(lar, reg, lar_temperature)
pyg4_lar_attach_scintillation(lar, reg, scint_yield)



# -----------------------------
# World volume
# -----------------------------
world_s = solid.Box("world_s", 100, 100, 100, registry=reg, lunit="cm")  # cm
world_l = g4.LogicalVolume(world_s, "G4_Galactic", "World_lv", registry=reg)
reg.setWorld(world_l)

# -----------------------------
# LAr volume
# -----------------------------
lar_s = solid.Orb("LAr_s", 100, registry=reg)  # radius in cm
lar_l = g4.LogicalVolume(lar_s, lar, "LAr_lv", registry=reg, lunit="cm")
g4.PhysicalVolume([0, 0, 0], [0, 0, 0], lar_l, "LAr_pv", world_l, registry=reg)

# -----------------------------
# HPGe detectors metadata
# -----------------------------
bege_meta = {
    "name": "B00000B",
    "type": "bege",
    "production": {"enrichment": {"val": 0.874, "unc": 0.003}, "mass_in_g": 697.0},
    "geometry": {
        "height_in_mm": 29.46,
        "radius_in_mm": 36.98,
        "groove": {"depth_in_mm": 2.0, "radius_in_mm": {"outer": 10.5, "inner": 7.5}},
        "pp_contact": {"radius_in_mm": 7.5, "depth_in_mm": 0},   # <-- add this
        "taper": {
            "top": {"angle_in_deg": 0.0, "height_in_mm": 0.0},
            "bottom": {"angle_in_deg": 0.0, "height_in_mm": 0.0},
        },
    },
}


coax_meta = {
    "name": "C000RG1",
    "type": "coax",
    "production": {"enrichment": {"val": 0.855, "unc": 0.015}},
    "geometry": {
        "height_in_mm": 40,
        "radius_in_mm": 38.25,
        "borehole": {"radius_in_mm": 6.75, "depth_in_mm": 40},       # <-- required
        "groove": {"depth_in_mm": 2, "radius_in_mm": {"outer": 20, "inner": 17}},
        "pp_contact": {"radius_in_mm": 17, "depth_in_mm": 0},        # <-- required
        "taper": {
            "top": {"angle_in_deg": 45, "height_in_mm": 5},
            "bottom": {"angle_in_deg": 45, "height_in_mm": 2},
            "borehole": {"angle_in_deg": 0, "height_in_mm": 0},
        },
    },
}


# -----------------------------
# Create HPGe logical volumes
# -----------------------------
bege_l = make_hpge(bege_meta, name="BEGe_L", registry=reg)
coax_l = make_hpge(coax_meta, name="Coax_L", registry=reg)

# -----------------------------
# Place HPGe detectors inside LAr
# -----------------------------
bege_pos = [0, +45, 0]  # cm
coax_pos = [0, -45, 0]  # cm

bege_pv = g4.PhysicalVolume([0,0,0], bege_pos, bege_l, "BEGe_pv", lar_l, registry=reg)
coax_pv = g4.PhysicalVolume([0,0,0], coax_pos, coax_l, "Coax_pv", lar_l, registry=reg)

bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 1, bege_meta)
coax_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 2, coax_meta)

# -----------------------------
# PEN encapsulation around detectors
# -----------------------------
def create_pen(det_meta, det_pos, name_prefix, det_id):
    radius = det_meta["geometry"]["radius_in_mm"]/10.0 + 0.2  # cm + margin
    half_height = det_meta["geometry"]["height_in_mm"]/20.0 + 0.2
    pen_s = solid.Tubs(f"{name_prefix}_s", 0, radius, half_height, 0, 2*math.pi, registry=reg)
    pen_l = g4.LogicalVolume(pen_s, pen, f"{name_prefix}_lv", registry=reg)
    pen_pv = g4.PhysicalVolume([0,0,0], det_pos, pen_l, f"{name_prefix}_pv", lar_l, registry=reg)
    pen_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", det_id, {"name":name_prefix,"material":"PEN"})
    return pen_pv

pen_bege_pv = create_pen(bege_meta, bege_pos, "PEN_BEGe", 3)
pen_coax_pv = create_pen(coax_meta, coax_pos, "PEN_Coax", 4)

# -----------------------------
# PMTs below PEN (optical detectors)
# -----------------------------
def create_pmt(det_pos, name_prefix, det_id):
    pmt_size = 5.08  # cm half-length
    thickness = 0.25  # cm
    pmt_s = solid.Box(f"{name_prefix}_s", pmt_size, pmt_size, thickness, registry=reg)
    pmt_l = g4.LogicalVolume(pmt_s, "G4_Galactic", f"{name_prefix}_lv", registry=reg)
    pmt_pos = [det_pos[0], det_pos[1], det_pos[2] - 5]  # below PEN
    pmt_pv = g4.PhysicalVolume([0,0,0], pmt_pos, pmt_l, f"{name_prefix}_pv", lar_l, registry=reg)
    pmt_pv.pygeom_active_detector = RemageDetectorInfo("optical", det_id, {"name":name_prefix})
    return pmt_pv

pmt_bege_pv = create_pmt(bege_pos, "PMT_BEGe", 5)
pmt_coax_pv = create_pmt(coax_pos, "PMT_Coax", 6)

# -----------------------------
# Add detector origins
# -----------------------------
for pv in [bege_pv, coax_pv, pen_bege_pv, pen_coax_pv, pmt_bege_pv, pmt_coax_pv]:
    add_detector_origin(pv.name, pv, reg)


# finally create a small radioactive source
source_s = pg4.geant4.solid.Tubs("Source_s", 0, 1, 1, 0, 2 * pi, registry=reg)
source_l = pg4.geant4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg)
pg4.geant4.PhysicalVolume(
    [0, 0, 0], [0, 0, 0, "cm"], source_l, "Source", lar_l, registry=reg
)

# -----------------------------
# Visualization (FIXED)
# -----------------------------
# Use the viewer from pygeomtools.visualization (American spelling)
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "LAr": [0,0,1,0.1],        # your custom LAr
        "PEN": [0,0.5,0.5,0.3],    # your PEN encapsulation
        "G4_LAr": [0.5,0.5,0.5,0.2]
    }
)

viewer.addLogicalVolume(reg.getWorldVolume())
viewer.view()
# -----------------------------
# Export GDML
# -----------------------------
pygeomtools.write_pygeom(reg, "HPGe_with_PEN_optical.gdml")

