#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

import math
import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
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
    u,
)
from pygeomtools import RemageDetectorInfo
from numpy import pi

import pygeomtools
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
# PEN material
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

pyg4_pen_attach_rindex(pen, reg)
pyg4_pen_attach_attenuation(pen, reg)
pyg4_pen_attach_wls(pen, reg)
pyg4_pen_attach_scintillation(pen, reg)

# -----------------------------
# LAr material
# -----------------------------
Ar = g4.ElementSimple("Argon", "Ar", 18, 39.95, registry=reg)
lar = g4.Material(
    name="LAr",
    density=1.390,
    number_of_components=1,
    state="liquid",
    temperature=88.8,
    pressure=1e5,
    registry=reg,
)
lar.add_element_natoms(Ar, 1)

lar_temperature = 88.8 * u.K

pyg4_lar_attach_rindex(lar, reg)
pyg4_lar_attach_attenuation(
    lar_mat=lar,
    reg=reg,
    lar_temperature=lar_temperature,
    lar_dielectric_method="cern2020",
    attenuation_method_or_length="legend200-llama",
    rayleigh_enabled_or_length=True,
    absorption_enabled_or_length=True,
)
pyg4_lar_attach_scintillation(lar, reg, flat_top_yield=1000/u.MeV)

# -----------------------------
# World volume
# -----------------------------
world_s = solid.Box("world_s", 100, 100, 100, registry=reg, lunit="cm")
world_l = g4.LogicalVolume(world_s, "G4_Galactic", "World_lv", registry=reg)
reg.setWorld(world_l)

# -----------------------------
# LAr volume (cylinder)
# -----------------------------
lar_radius = 12
lar_half_height = 25
lar_s = solid.Tubs("LAr_s", 0, lar_radius, lar_half_height, 0, 2*math.pi, registry=reg, lunit="cm")
lar_l = g4.LogicalVolume(lar_s, lar, "LAr_lv", registry=reg, lunit="cm")
lar_pv = g4.PhysicalVolume([0,0,0], [0,0,0], lar_l, "LAr_pv", world_l, registry=reg)



# -----------------------------
# HPGe metadata
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


# -----------------------------
# Create HPGe logical volumes
# -----------------------------
bege_l = make_hpge(bege_meta, name="BEGe_L", registry=reg)
coax_l = make_hpge(coax_meta, name="Coax_L", registry=reg)

# -----------------------------
# Place HPGe detectors inside LAr
# -----------------------------
bege_pos = [0, 0, 7.0, "cm"]
coax_pos = [0, 0, -7.0, "cm"]

bege_pv = g4.PhysicalVolume([0,0,0], bege_pos, bege_l, "BEGe_pv", lar_l, registry=reg)
coax_pv = g4.PhysicalVolume([0,0,0], coax_pos, coax_l, "Coax_pv", lar_l, registry=reg)

# -----------------------------
# PEN with bottom function
# -----------------------------
def create_pen_with_bottom(det_meta, det_pos, name_prefix, det_id,
                           margin=0.1, thickness=0.2, bottom_thickness=0.2):
    det_radius_cm = det_meta["geometry"]["radius_in_mm"] / 10.0
    det_half_height_cm = det_meta["geometry"]["height_in_mm"] / 20.0

    # Cylindrical wall
    inner_r = det_radius_cm + margin
    outer_r = inner_r + thickness
    height = 2*(det_half_height_cm + margin)
    wall_s = solid.Tubs(f"{name_prefix}_wall_s", inner_r, outer_r, height,
                        0, 2*math.pi, registry=reg, lunit="cm")
    wall_l = g4.LogicalVolume(wall_s, pen, f"{name_prefix}_wall_lv", registry=reg)

    # PEN center shifted so bottom at detector center
    pen_center_z = det_pos[2] + height/2.0
    wall_pv = g4.PhysicalVolume([0,0,0], [det_pos[0], det_pos[1], pen_center_z, "cm"], wall_l,
                                f"{name_prefix}_wall_pv", lar_l, registry=reg)

    # Bottom plate
    bottom_s = solid.Tubs(f"{name_prefix}_bottom_s", 0, outer_r, bottom_thickness/2.0,
                          0, 2*math.pi, registry=reg, lunit="cm")
    bottom_l = g4.LogicalVolume(bottom_s, pen, f"{name_prefix}_bottom_lv", registry=reg)
    bottom_pos_z = pen_center_z  - height/2.0-margin/2.0 - bottom_thickness/2.0
    bottom_pos = [det_pos[0], det_pos[1], bottom_pos_z, "cm"]
    bottom_pv = g4.PhysicalVolume([0,0,0], bottom_pos, bottom_l, f"{name_prefix}_bottom_pv",
                                  lar_l, registry=reg)

# Register PEN wall as scintillator
    wall_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", det_id, {"name": name_prefix})

    effective_height = height + bottom_thickness
    return wall_pv, bottom_pv, bottom_pos_z

# -----------------------------
# Create PEN volumes
# -----------------------------

wall_pv_bege, bottom_pv_bege, pen_bege_half_height = create_pen_with_bottom(
    bege_meta, bege_pos, "PEN_BEGe", 3, margin=0.1, thickness=0.2, bottom_thickness=0.2
)
wall_pv_coax, bottom_pv_coax, pen_coax_half_height = create_pen_with_bottom(
    coax_meta, coax_pos, "PEN_Coax", 4, margin=0.1, thickness=0.2, bottom_thickness=0.2
)
'''
def create_pmt_under_pen(det_pos, pen_half_height, name_prefix, det_id, gap=0.1):
    """
    Places a PMT exactly `gap` cm below the bottom of a PEN shell.
    Default gap = 0.1 cm = 1 mm.
    """
    # PMT geometry
    side_half = 2.54     # cm (PMT is 5.08x5.08 cm square)
    thickness = 0.5      # cm total thickness
    half_thickness = thickness / 2.0

    # Detector center (in cm)
    det_x, det_y, det_z = float(det_pos[0]), float(det_pos[1]), float(det_pos[2])

    # PEN bottom z
    pen_bottom_z = pen_half_height

    # PMT center = PEN bottom - gap - half_thickness
    pmt_center_z = pen_bottom_z - gap - half_thickness

    # Solid: pass half-extents
    pmt_s = solid.Box(f"{name_prefix}_s", side_half, side_half, half_thickness, registry=reg, lunit="cm")
    pmt_l = g4.LogicalVolume(pmt_s, "G4_Galactic", f"{name_prefix}_lv", registry=reg)
    pmt_pos = [det_x, det_y, pmt_center_z, "cm"]

    # Place physical volume
    pmt_pv = g4.PhysicalVolume([0,0,0], pmt_pos, pmt_l, f"{name_prefix}_pv", lar_l, registry=reg)
    pmt_pv.pygeom_active_detector = RemageDetectorInfo("optical", det_id, {"name": name_prefix})

    # --- Add optical surface ---
    surf = g4.solid.OpticalSurface(
        f"{name_prefix}_surface",
        finish="ground",
        model="unified",
        surf_type="dielectric_metal",
        value=0,
        registry=reg
    )
    surf.addVecProperty("EFFICIENCY", [400, 600], [1, 1])    # 100% detection efficiency
    surf.addVecProperty("REFLECTIVITY", [1, 10], [0, 0])  # no reflection
    g4.SkinSurface(f"{name_prefix}_skin", pmt_l, surf, registry=reg)

    print(
        f"[DEBUG] {name_prefix}: det_z={det_z:.2f} cm, pen_half_height={pen_half_height:.2f} cm, "
        f"pen_bottom_z={pen_bottom_z:.2f} cm, pmt_center_z={pmt_center_z:.2f} cm"
    )

    return pmt_pv

'''

def create_pmt_under_pen(det_pos, pen_half_height, name_prefix, det_id, gap=0.1):
    """
    Places a PMT exactly `gap` cm below the bottom of a PEN shell.
    Default gap = 0.1 cm = 1 mm.
    """
    # PMT geometry
    side_half = 2.54     # cm (PMT is 5.08x5.08 cm square)
    thickness = 0.5      # cm total thickness
    half_thickness = thickness / 2.0

    # Detector center (in cm)
    det_x, det_y, det_z = float(det_pos[0]), float(det_pos[1]), float(det_pos[2])

   
    pen_bottom_z = pen_half_height

    
    pmt_center_z = pen_bottom_z - gap - half_thickness

    # Solid: pass half-extents
    pmt_s = solid.Box(f"{name_prefix}_s", side_half, side_half, half_thickness, registry=reg, lunit="cm")
    pmt_l = g4.LogicalVolume(pmt_s, "G4_Galactic", f"{name_prefix}_lv", registry=reg)
    pmt_pos = [det_x, det_y, pmt_center_z, "cm"]

    # Place physical volume
    pmt_pv = g4.PhysicalVolume([0,0,0], pmt_pos, pmt_l, f"{name_prefix}_pv", lar_l, registry=reg)

    # --- Register as optical detector (this is the key line) ---
    pmt_pv.pygeom_active_detector = RemageDetectorInfo("optical", det_id, {"name": name_prefix})

    # --- Add optical surface ---
    surf = g4.solid.OpticalSurface(
        f"{name_prefix}_surface",
        finish="ground",
        model="unified",
        surf_type="dielectric_metal",
        value=0,
        registry=reg
    )
    surf.addVecProperty("EFFICIENCY", [400, 600], [1, 1])    # 100% detection efficiency
    surf.addVecProperty("REFLECTIVITY", [1, 10], [0, 0])     # no reflection
    g4.SkinSurface(f"{name_prefix}_skin", pmt_l, surf, registry=reg)

    print(
        f"[DEBUG] {name_prefix}: det_z={det_z:.2f} cm, pen_half_height={pen_half_height:.2f} cm, "
        f"pen_bottom_z={pen_bottom_z:.2f} cm, pmt_center_z={pmt_center_z:.2f} cm"
    )

    return pmt_pv


pmt_bege_pv = create_pmt_under_pen(bege_pos, pen_bege_half_height, "PMT_BEGe", 5)
pmt_coax_pv = create_pmt_under_pen(coax_pos, pen_coax_half_height, "PMT_Coax", 6)


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

# PEN walls as scintillators
wall_pv_bege.pygeom_active_detector = RemageDetectorInfo("scintillator", 3, {"name": "PEN_BEGe_wall"})
wall_pv_coax.pygeom_active_detector = RemageDetectorInfo("scintillator", 5, {"name": "PEN_Coax_wall"})

# PEN bottom plates as scintillators
bottom_pv_bege.pygeom_active_detector = RemageDetectorInfo("scintillator", 4, {"name": "PEN_BEGe_bottom"})
bottom_pv_coax.pygeom_active_detector = RemageDetectorInfo("scintillator", 6, {"name": "PEN_Coax_bottom"})

# PMTs as optical
pmt_bege_pv.pygeom_active_detector = RemageDetectorInfo("optical", 7, {"name": "PMT_BEGe"})
pmt_coax_pv.pygeom_active_detector = RemageDetectorInfo("optical", 8, {"name": "PMT_Coax"})

# Optional: LAr as scintillator
lar_l.pygeom_active_detector = RemageDetectorInfo("scintillator", 9, {"name": "LAr"})


# -----------------------------
# Add detector origins
# -----------------------------
for pv in [bege_pv, coax_pv,
           wall_pv_bege, bottom_pv_bege,
           wall_pv_coax, bottom_pv_coax,
           pmt_bege_pv, pmt_coax_pv, lar_pv]:
    add_detector_origin(pv.name, pv, reg)


# -----------------------------
# Source
# -----------------------------
source_s = solid.Tubs("Source_s", 0, 1, 1, 0, 2*pi, registry=reg)
source_l = g4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg, lunit="mm")
g4.PhysicalVolume([0,0,0], [0,0,0], source_l, "Source", lar_l, registry=reg)

# -----------------------------
# Visualization
# -----------------------------
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "LAr": [0,0,1,0.1],
        "PEN": [0,0.5,0.5,0.3],
        "G4_Galactic": [0.5,0.5,0.5,0.2],
    }
)
viewer.addLogicalVolume(reg.getWorldVolume())
viewer.view()

# -----------------------------
# Export GDML
# -----------------------------
import pygeomtools
pygeomtools.write_pygeom(reg, "HPGe_with_PEN_optical.gdml")
