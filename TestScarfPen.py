#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
# -*- coding: utf-8 -*-

"""
Unified geometry script — all units in mm.
Preserves your BEGe + ICPC detectors (stacked) as in the original script.
"""

from __future__ import annotations
import math
import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
import pyg4ometry as pg4
from math import pi
from functools import cached_property

import legendoptics.tpb
import legendoptics.pen
import legendoptics.lar
from legendoptics.lar import (
    pyg4_lar_attach_rindex,
    pyg4_lar_attach_attenuation,
    pyg4_lar_attach_scintillation,
    u
)
from legendoptics.pen import (
    pyg4_pen_attach_rindex,
    pyg4_pen_attach_attenuation,
    pyg4_pen_attach_wls,
    pyg4_pen_attach_scintillation,
)


from fibers_shroud_360 import build_fiber_shroud
import numpy as np
import pint
from pygeomtools import RemageDetectorInfo, write_pygeom
from pygeomtools.materials import BaseMaterialRegistry, cached_property as pg_cached_property
from legendhpges import make_hpge

# -----------------------------
# Registry
# -----------------------------
reg = g4.Registry()

# -----------------------------
# Units
# -----------------------------
u = pint.get_application_registry()
# canonical unit in this file: mm

# -----------------------------
# Material registry (cached_property)
# -----------------------------
class OpticalMaterialRegistry(BaseMaterialRegistry):
    def __init__(self, g4_registry: g4.Registry):
        self.lar_temperature = 88.8 * u.K
        super().__init__(g4_registry)
        self._build_surfaces()

    def _build_surfaces(self):
        self.surfaces = type("Surfaces", (), {})()

    # -------------------------
    # LAr → TPB
    # -------------------------
        self.surfaces.lar_to_tpb = g4.solid.OpticalSurface(
        name="os_lar_tpb",
        model="unified",
        finish="ground",
        surf_type="dielectric_dielectric",
        value=1.0,
        registry=self.g4_registry,
    )
        self.surfaces.lar_to_tpb.addConstProperty("SIGMA_ALPHA", 0.2)
        self.surfaces.lar_to_tpb.addConstProperty("DIFFUSELOBECONSTANT", 0.7)
        self.surfaces.lar_to_tpb.addConstProperty("SPECULARLOBECONSTANT", 0.2)
        self.surfaces.lar_to_tpb.addConstProperty("SPECULARSPIKECONSTANT", 0.1)
        self.surfaces.lar_to_tpb.addConstProperty("BACKSCATTERCONSTANT", 0.0)

    # -------------------------
    # LAr → SiPM (PDE)
    # -------------------------
        self.surfaces.to_sipm_silicon = g4.solid.OpticalSurface(
        name="os_lar_sipm",
        model="unified",
        finish="polished",
        surf_type="dielectric_metal",
        value=0,
        registry=self.g4_registry,
        )

        # Photon energies in eV (ascending)
        E = [
        0.5,   # IR
        1.24,  # 1000 nm  (turn on)
        3.10,  # 400 nm   (turn off)
        6.0    # deep UV
            ]

# Quantum efficiency (PDE)
        QE = [
        0.0,   # below 1000 nm
        1.0,   # fully sensitive
        1.0,   # fully sensitive
        0.0    # above 400 nm
            ]

# Reflection (0 = absorb everything not detected)
        R = [
        0.0,
        0.0,
        0.0,
        0.0
            ]

        self.surfaces.to_sipm_silicon.addVecProperty("EFFICIENCY", E, QE)
        self.surfaces.to_sipm_silicon.addVecProperty("REFLECTIVITY", E, R)



    @pg_cached_property
    def liquidargon(self) -> g4.Material:
        _lar = g4.Material(
            name="liquid_argon",
            density=1.390,  # g/cm3 (legendoptics expects SI-ish values — keep as before)
            number_of_components=1,
            state="liquid",
            temperature=float(self.lar_temperature.m_as(u.kelvin)),
            pressure=1.0e5,
            registry=self.g4_registry,
        )
        _lar.add_element_natoms(self.get_element("Ar"), natoms=1)
        # attach optical properties for LAr (rindex, attenuation etc.)
        legendoptics.lar.pyg4_lar_attach_rindex(_lar, self.g4_registry)
        legendoptics.lar.pyg4_lar_attach_attenuation(
            lar_mat=_lar,
            reg=self.g4_registry,
            lar_temperature=self.lar_temperature,
            lar_dielectric_method="cern2020",
            attenuation_method_or_length="legend200-llama",
            rayleigh_enabled_or_length=True,
            absorption_enabled_or_length=True,
        )
        legendoptics.lar.pyg4_lar_attach_scintillation(_lar, self.g4_registry, flat_top_yield=1000 / u.MeV)
        return _lar

    @pg_cached_property
    def pmma(self) -> g4.Material:
        _pmma = g4.Material(
            name="pmma",
            density=1.2,
            number_of_components=3,
            registry=self.g4_registry,
        )
        _pmma.add_element_natoms(self.get_element("H"), natoms=8)
        _pmma.add_element_natoms(self.get_element("C"), natoms=5)
        _pmma.add_element_natoms(self.get_element("O"), natoms=2)
        legendoptics.fibers.pyg4_fiber_cladding1_attach_rindex(_pmma, self.g4_registry)
        return _pmma

    @pg_cached_property
    def pmma_out(self) -> g4.Material:
        _pmma_out = g4.Material(
            name="pmma_cl2",
            density=1.2,
            number_of_components=3,
            registry=self.g4_registry,
        )
        _pmma_out.add_element_natoms(self.get_element("H"), natoms=8)
        _pmma_out.add_element_natoms(self.get_element("C"), natoms=5)
        _pmma_out.add_element_natoms(self.get_element("O"), natoms=2)
        legendoptics.fibers.pyg4_fiber_cladding2_attach_rindex(_pmma_out, self.g4_registry)
        return _pmma_out

    @pg_cached_property
    def ps_fibers(self) -> g4.Material:
        _ps_fibers = g4.Material(
            name="ps_fibers",
            density=1.05,
            number_of_components=2,
            registry=self.g4_registry,
        )
        _ps_fibers.add_element_natoms(self.get_element("H"), natoms=8)
        _ps_fibers.add_element_natoms(self.get_element("C"), natoms=8)
        legendoptics.fibers.pyg4_fiber_core_attach_rindex(_ps_fibers, self.g4_registry)
        legendoptics.fibers.pyg4_fiber_core_attach_absorption(_ps_fibers, self.g4_registry)
        legendoptics.fibers.pyg4_fiber_core_attach_wls(_ps_fibers, self.g4_registry)
        return _ps_fibers

    def _tpb(self, name: str) -> g4.Material:
        t = g4.Material(
            name=name,
            density=1.08,
            number_of_components=2,
            state="solid",
            registry=self.g4_registry,
        )
        t.add_element_natoms(self.get_element("H"), natoms=22)
        t.add_element_natoms(self.get_element("C"), natoms=28)
        legendoptics.tpb.pyg4_tpb_attach_rindex(t, self.g4_registry)
        legendoptics.tpb.pyg4_tpb_attach_wls(t, self.g4_registry)
        return t
    
    @pg_cached_property
    def tpb_on_fibers(self) -> g4.Material:
        m = g4.Material(
        name="tpb_on_fibers",
        density=1.08,
        number_of_components=2,
        state="solid",
        registry=self.g4_registry,
        )
        m.add_element_natoms(self.get_element("H"), natoms=22)
        m.add_element_natoms(self.get_element("C"), natoms=28)

        legendoptics.tpb.pyg4_tpb_attach_rindex(m, self.g4_registry)
        legendoptics.tpb.pyg4_tpb_attach_wls(m, self.g4_registry)
        return m



    @pg_cached_property
    def os_fibers(self) -> g4.solid.OpticalSurface:
        osurf = g4.solid.OpticalSurface(
            name="os_fibers",
            model="unified",
            finish="polished",
            surf_type="dielectric_dielectric",
            value=1.0,
            registry=self.g4_registry,
        )
        return osurf

    @pg_cached_property
    def pen(self) -> g4.Material:
        # Build the PEN material once and attach optical properties via legendoptics.pen
        m = g4.Material(
            name="PEN",
            density=1.30,
            number_of_components=3,
            state="solid",
            temperature=88.15,
            registry=self.g4_registry,
        )
        m.add_element_natoms(self.get_element("C"), natoms=14)
        m.add_element_natoms(self.get_element("H"), natoms=10)
        m.add_element_natoms(self.get_element("O"), natoms=4)
        legendoptics.pen.pyg4_pen_attach_rindex(m, self.g4_registry)
        legendoptics.pen.pyg4_pen_attach_attenuation(m, self.g4_registry)
        legendoptics.pen.pyg4_pen_attach_wls(m, self.g4_registry)
        legendoptics.pen.pyg4_pen_attach_scintillation(m, self.g4_registry)
        return m
    
    @pg_cached_property
    def metal_silicon(self):
            m = g4.Material(name="metal_silicon", density=2.33, number_of_components=1, registry=self.g4_registry)
            m.add_element_natoms(self.get_element("Si"),1)
            return m

    @pg_cached_property
    def metal_copper(self):
        m = g4.Material(name="metal_copper", density=8.96, number_of_components=1, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("Cu"),1)
        return m
    
    
    '''
    
    @pg_cached_property
    def surfaces(self):
        class S:
            def __init__(self, reg):

            # -------------------------
            # LAr → TPB
            # -------------------------
                self.lar_to_tpb = g4.solid.OpticalSurface(
                name="os_lar_tpb",
                model="unified",
                finish="ground",
                surf_type="dielectric_dielectric",
                value=1.0,
                registry=reg,
            )

                self.lar_to_tpb.addConstProperty("SIGMA_ALPHA", 0.2)
                self.lar_to_tpb.addConstProperty("DIFFUSELOBECONSTANT", 0.7)
                self.lar_to_tpb.addConstProperty("SPECULARLOBECONSTANT", 0.2)
                self.lar_to_tpb.addConstProperty("SPECULARSPIKECONSTANT", 0.1)
                self.lar_to_tpb.addConstProperty("BACKSCATTERCONSTANT", 0.0)

            # -------------------------
            # LAr → SiPM
            # -------------------------
                self.to_sipm_silicon = g4.solid.OpticalSurface(
                name="os_lar_sipm",
                model="unified",
                finish="polished",
                surf_type="dielectric_metal",
                value=1.0,
                registry=reg,
            )

                self.to_sipm_silicon.addConstProperty("SIGMA_ALPHA", 0.05)
                self.to_sipm_silicon.addConstProperty("SPECULARSPIKECONSTANT", 0.6)
                self.to_sipm_silicon.addConstProperty("SPECULARLOBECONSTANT", 0.3)
                self.to_sipm_silicon.addConstProperty("DIFFUSELOBECONSTANT", 0.1)
                self.to_sipm_silicon.addConstProperty("BACKSCATTERCONSTANT", 0.0)

        return S(self.g4_registry)
  '''

# -----------------------------
# Instantiate materials
# -----------------------------
mats = OpticalMaterialRegistry(reg)
print("SiPM surface type:", type(mats.surfaces.to_sipm_silicon))
print("Is OpticalSurface:",
      isinstance(mats.surfaces.to_sipm_silicon, g4.solid.OpticalSurface))


# -----------------------------
# Helper: add detector origins (same as you use elsewhere)
# -----------------------------
def add_detector_origin(name, pv, registry):
    if not hasattr(registry, "detector_origins"):
        registry.detector_origins = {}
    # pv.position is expected to be [x,y,z,"mm"] or similar. Normalize.
    pos = getattr(pv, "position", None)
    if isinstance(pos, (list, tuple)):
        # pos might be [x,y,z,"mm"] or [x,y,z]
        if len(pos) >= 4 and isinstance(pos[3], str):
            registry.detector_origins[name] = {"xloc": pos[0], "yloc": pos[1], "zloc": pos[2], "units": pos[3]}
        else:
            registry.detector_origins[name] = {"xloc": pos[0], "yloc": pos[1], "zloc": pos[2], "units": "mm"}
    else:
        # fallback - store None
        registry.detector_origins[name] = {"xloc": None, "yloc": None, "zloc": None}

# -----------------------------
# World & LAr (units: mm)
# -----------------------------
# World half-sizes: originally 200 cm -> 2000 mm
world_half_mm = 500.0
world_s = solid.Box("world_s", world_half_mm, world_half_mm, world_half_mm, registry=reg, lunit="mm")
world_lv = g4.LogicalVolume(world_s, mats.liquidargon, "World_lv", registry=reg)
reg.setWorld(world_lv)

# LAr detector volume (originally given in cm; convert to mm)
lar_radius_mm = 12.0 * 10.0    # 12.0 cm -> 120 mm
lar_half_height_mm = 25.0 * 10.0  # 25.0 cm -> 250 mm
lar_s = solid.Tubs("LAr_s", 0.0, lar_radius_mm, lar_half_height_mm, 0.0, 2.0 * math.pi, registry=reg, lunit="mm")
lar_lv = g4.LogicalVolume(lar_s, mats.liquidargon, "LAr_lv", registry=reg, lunit="mm")
lar_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0, "mm"], lar_lv, "LAr_pv", world_lv, registry=reg)


lar_pv = reg.physicalVolumeDict["LAr_pv"]



#source_s = solid.Tubs("Source_s", 0, 1, 1, 0, 2*pi, registry=reg, lunit="cm")
#source_l = g4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg)
#g4.PhysicalVolume([0, 0, 0], [0, 0, +3.0, "cm"], source_l, "Source", lar_lv, registry=reg)

# -----------------------------
# HPGe detectors (same meta as before)
# -----------------------------
icpc_meta = {
    "name": "V99000A",
    "type": "icpc",
    "production": {
        "enrichment": {"val": 0.076, "unc": 0.003},
        "mass_in_g": 1500.0
    },
    "geometry": {
        "height_in_mm": 65.0,
        "radius_in_mm": 39.0,
        "borehole": {"radius_in_mm": 5.0, "depth_in_mm": 32.0},
        "pp_contact": {"radius_in_mm": 4.0, "depth_in_mm": 3.0},
        "outer_contact": {"thickness_in_mm": 0.7},
        "passivation": {"thickness_in_mm": 0.3},
        "groove": {"radius_in_mm": {"outer": 11.0, "inner": 7.5}, "depth_in_mm": 3.0},
        "taper": {
            "top": {"angle_in_deg": 45.0, "height_in_mm": 3.0},
            "bottom": {"angle_in_deg": 45.0, "height_in_mm": 3.0},
            "borehole": {"angle_in_deg": 45.0, "height_in_mm": 3.0}
        }
    }
}

bege_meta = {
    "name": "B00000B",
    "type": "bege",
    "production": {"enrichment": {"val": 0.076, "unc": 0.003}, "mass_in_g": 697.0},
    "geometry": {
        "height_in_mm": 32.00,
        "radius_in_mm": 37.00,
        "groove": {"depth_in_mm": 3.0, "radius_in_mm": {"outer": 11.0, "inner": 7.5}},
        "pp_contact": {"radius_in_mm": 7.5, "depth_in_mm": 0},
        "taper": {"top": {"angle_in_deg": 0.0, "height_in_mm": 0.0}, "bottom": {"angle_in_deg": 45.0, "height_in_mm": 8.0}},
    },
}

coax_meta = {
    "name": "C000RG1",
    "type": "coax",
    "production": {"enrichment": {"val": 0.855, "unc": 0.015}},
    "geometry": {
        "height_in_mm": 40.0,
        "radius_in_mm": 38.25,
        "borehole": {"radius_in_mm": 6.75, "depth_in_mm": 40},
        "groove": {"depth_in_mm": 2, "radius_in_mm": {"outer": 20, "inner": 17}},
        "pp_contact": {"radius_in_mm": 17, "depth_in_mm": 0},
        "taper": {"top": {"angle_in_deg": 45, "height_in_mm": 5}, "bottom": {"angle_in_deg": 45, "height_in_mm": 2}, "borehole": {"angle_in_deg": 0, "height_in_mm": 0}},
    },
}

# create logical volumes using legendhpges helper (assumes meta uses mm)
bege_lv = make_hpge(bege_meta, name="BEGe_L", registry=reg)
icpc_lv = make_hpge(icpc_meta, name="ICPC_L", registry=reg)

# -----------------------------
# Detector placements (units: mm)
# -----------------------------
# Using the same stacking arrangement as your script (stacked along z)
bege_placement_mm = 50.0    # mm (as in your original)
icpc_placement_mm = -75.0   # mm

# Build physical volumes for detectors inside the LAr volume
bege_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, bege_placement_mm, "mm"], bege_lv, "BEGe_pv", lar_lv, registry=reg)
icpc_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, icpc_placement_mm, "mm"], icpc_lv, "ICPC_pv", lar_lv, registry=reg)

# mark them as active detectors (RemageDetectorInfo expects mm metadata)
bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 101, bege_meta)
icpc_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 102, icpc_meta)

# -----------------------------
# Closed PEN enclosures around each detector
# -----------------------------
def make_closed_cylinder_mm(name, inner_r_mm, outer_r_mm, height_mm, thickness_mm, reg, plate_extra_r_mm):
    """
    Create a closed cylinder (wall + top & bottom plates) in mm. Returns a solid (union).
    inner_r_mm: inner radius in mm
    outer_r_mm: outer radius in mm
    height_mm: full height in mm (not half)
    thickness_mm: plate thickness in mm (cap thickness)
    plate_extra_r_mm: how much cap disc radius extends beyond outer_r_mm
    """
    half_h = height_mm / 2.0
    cap_radius = outer_r_mm + plate_extra_r_mm

    # Wall (Tubs takes half-height argument for the third param)
    wall = solid.Tubs(
        f"{name}_wall_s",
        inner_r_mm,
        outer_r_mm,
        half_h,
        0,
        2 * math.pi,
        registry=reg,
        lunit="mm"
    )

    # Cap (a short disc) - create as Tubs from 0 to cap_radius with half-thickness
    cap = solid.Tubs(
        f"{name}_cap_s",
        0,
        cap_radius,
        thickness_mm / 2.0,
        0,
        2 * math.pi,
        registry=reg,
        lunit="mm"
    )

    # Union top cap (move cap to +half_h)
    
    enclosure_top = solid.Union(
        f"{name}_union_top",
        wall,
        cap,
        tra2=([0.0, 0.0, 0.0], [0.0, 0.0, half_h/2, "mm"]),
        registry=reg
    )

    # Union bottom cap (move cap to -half_h)
    enclosure_full = solid.Union(
        f"{name}_union_full",
        enclosure_top,
        cap,
        tra2=([0.0, 0.0, 0.0], [0.0, 0.0, -half_h/2, "mm"]),
        registry=reg
    )

    return enclosure_full

# define enclosure geometry in mm (converted from your mm meta)
enclosure_bege_solid = make_closed_cylinder_mm(
    "enclosure_bege",
    inner_r_mm=37.5,     # mm
    outer_r_mm=39.0,     # mm
    height_mm=69.0,      # mm total height
    thickness_mm=1.5,    # mm cap thickness
    reg=reg,
    plate_extra_r_mm=5.0
)

enclosure_icpc_solid = make_closed_cylinder_mm(
    "enclosure_icpc",
    inner_r_mm=39.5,
    outer_r_mm=41.0,
    height_mm=134.0,
    thickness_mm=1.5,
    reg=reg,
    plate_extra_r_mm=5.0
)

enclosure_bege_lv = g4.LogicalVolume(enclosure_bege_solid, mats.pen, "enclosure_bege_lv", registry=reg)
enclosure_icpc_lv = g4.LogicalVolume(enclosure_icpc_solid, mats.pen, "enclosure_icpc_lv", registry=reg)


# ============================================================
# Fiber shroud + SiPMs
# ============================================================

class Center:
    def __init__(self, x, y):
        self.x_in_mm = float(x)
        self.y_in_mm = float(y)

class String:
    def __init__(self, angle, radius, center):
        self.angle_in_deg = angle
        self.radius_in_mm = float(radius)
        self.center = center

# LAr is centered at (0,0) in world coordinates
cx = 0.0
cy = 0.0

fiber_inner_radius = 150   # mm
fiber_outer_radius = 170   # mm

hpge_string = {
    "0": type("", (), {"angle_in_deg": 0,   "radius_in_mm": 150, "center": type("", (), {"x_in_mm": 0.0, "y_in_mm": 0.0})()})(),
    "1": type("", (), {"angle_in_deg": 120, "radius_in_mm": 150, "center": type("", (), {"x_in_mm": 0.0, "y_in_mm": 0.0})()})(),
    "2": type("", (), {"angle_in_deg": 240, "radius_in_mm": 150, "center": type("", (), {"x_in_mm": 0.0, "y_in_mm": 0.0})()})(),

    "3": type("", (), {"angle_in_deg": 60,  "radius_in_mm": 170, "center": type("", (), {"x_in_mm": 0.0, "y_in_mm": 0.0})()})(),
    "4": type("", (), {"angle_in_deg": 180, "radius_in_mm": 170, "center": type("", (), {"x_in_mm": 0.0, "y_in_mm": 0.0})()})(),
    "5": type("", (), {"angle_in_deg": 300, "radius_in_mm": 170, "center": type("", (), {"x_in_mm": 0.0, "y_in_mm": 0.0})()})(),
}


# Tell pyg4ometry that LAr is a valid placement root
reg.setWorld(lar_lv)

sipms = build_fiber_shroud(reg, lar_pv, hpge_string, mats)
# 🔧 Fix pyg4ometry orphaning: reattach SiPMs to LAr
for pv in sipms.values():
    pv.mother = lar_pv
    pv.motherLV = lar_pv.logicalVolume


reg.setWorld(world_lv)
# ============================================================
# SiPM optical detection surface (PDE)
# ============================================================
   

# -----------------------------
# PEN rough optical surface
# -----------------------------
pen_surface = g4.solid.OpticalSurface(
    name="PEN_surface",
    model="unified",
    finish="ground",                # makes the surface rough
    surf_type="dielectric_dielectric",  # PEN ↔ LAr
    value=0.1,                      # roughness sigma_alpha in radians
    registry=reg
)

# attach the PEN surface to the PEN enclosures
for lv in [enclosure_bege_lv, enclosure_icpc_lv]:
    g4.SkinSurface(f"{lv.name}_os", lv, pen_surface, reg)


# -----------------------------
# Place the PEN enclosures (stacked as in your script)
# -----------------------------
bege_encap_offset_mm = bege_placement_mm + 16.0   # your earlier +16 mm
icpc_encap_offset_mm = icpc_placement_mm + 32.5   # your earlier +32.5 mm

enclosure_bege_pv = g4.PhysicalVolume(
    [0, 0, 0], [0, 0, bege_encap_offset_mm, "mm"], enclosure_bege_lv,
    "enclosure_bege_pv", lar_lv, registry=reg
)

enclosure_icpc_pv = g4.PhysicalVolume(
    [0, 0, 0], [0, 0, icpc_encap_offset_mm, "mm"], enclosure_icpc_lv,
    "enclosure_icpc_pv", lar_lv, registry=reg
)


bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 101, bege_meta)
icpc_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 102, icpc_meta)
enclosure_bege_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 201, "name:enclosure_bege_pv")
enclosure_icpc_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 202, "name:enclosure_icpc_pv")
lar_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 401, {"name": "LAr_pv"})

print("\nRegistered optical detectors:")
for pv in reg.physicalVolumeDict.values():
    det = getattr(pv, "pygeom_active_detector", None)
    if det is not None and det.detector_type == "optical":
        print(pv.name, det.detector_type)

print("LAr PV object:", lar_pv)
print("Registry LAr PV:", reg.physicalVolumeDict["LAr_pv"])


# -----------------------------
# Add detector origins (so your tools that expect these keep working)
# -----------------------------
for pv in [bege_pv, icpc_pv, enclosure_bege_pv, enclosure_icpc_pv, lar_pv]:
    add_detector_origin(pv.name, pv, reg)


def pv_mother_name(pv):
    if hasattr(pv, "mother") and pv.mother is not None:
        return pv.mother.name
    if hasattr(pv, "motherLV") and pv.motherLV is not None:
        return pv.motherLV.name
    return None

print("\nOptical PV parents:")
for pv in reg.physicalVolumeDict.values():
    det = getattr(pv, "pygeom_active_detector", None)
    if det and det.detector_type == "optical":
        print(pv.name, "mother LV =", pv_mother_name(pv))



# -----------------------------
# Visualization (colours)
# -----------------------------
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "liquid_argon": [0, 1, 1, 0.08],
        "PEN": [0.0, 0.6, 0.6, 0.4]
    }
)
viewer.addLogicalVolume(reg.getWorldVolume())
viewer.view()

# viewer.view()  # uncomment if you want an interactive VTK viewer run

# -----------------------------
# Export GDML
# -----------------------------
write_pygeom(reg, "combined_geometry.gdml")
print("✅ Written combined_geometry.gdml")

def dump_geometry_tree(registry):
    print("\n========== GEOMETRY TREE ==========")

    # Map: parent -> children
    children = {}
    for pv in registry.physicalVolumeDict.values():
        parent = None
        if hasattr(pv, "mother") and pv.mother is not None:
            parent = pv.mother
        elif hasattr(pv, "motherLV") and pv.motherLV is not None:
            parent = pv.motherLV
        children.setdefault(parent, []).append(pv)

    def recurse(node, depth=0):
        for pv in children.get(node, []):
            lv = pv.logicalVolume
            mat = lv.material.name if lv.material else "None"
            print(
                "  " * depth
                + f"- {pv.name}  [LV={lv.name}, material={mat}]"
            )
            recurse(pv, depth + 1)

    world = registry.getWorldVolume()
    print(f"{world.name}  [WORLD]")
    recurse(world)

dump_geometry_tree(reg)






# done
