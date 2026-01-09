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
import legendoptics.fibers
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
        # keep LAr temperature in kelvin
        self.lar_temperature = 88.8 *u.K
        super().__init__(g4_registry)

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
        return self._tpb("tpb_on_fibers")

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

# -----------------------------
# Instantiate materials
# -----------------------------
mats = OpticalMaterialRegistry(reg)

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
world_half_mm = 2000.0
world_s = solid.Box("world_s", world_half_mm, world_half_mm, world_half_mm, registry=reg, lunit="mm")
world_lv = g4.LogicalVolume(world_s, mats.liquidargon, "World_lv", registry=reg)
reg.setWorld(world_lv)

# LAr detector volume (originally given in cm; convert to mm)
lar_radius_mm = 12.0 * 10.0    # 12.0 cm -> 120 mm
lar_half_height_mm = 25.0 * 10.0  # 25.0 cm -> 250 mm
lar_s = solid.Tubs("LAr_s", 0.0, lar_radius_mm, lar_half_height_mm, 0.0, 2.0 * math.pi, registry=reg, lunit="mm")
lar_lv = g4.LogicalVolume(lar_s, mats.liquidargon, "LAr_lv", registry=reg, lunit="mm")
lar_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0, "mm"], lar_lv, "LAr_pv", world_lv, registry=reg)


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



'''

def make_fully_nested_fiberoptic_shroud(
    name="fiber_shroud",
    core_radius_mm=1.0,
    cl1_thickness_mm=0.2,
    cl2_thickness_mm=0.3,
    tpb_thickness_mm=0.1,
    half_length_mm=50.0,
    parent_lv=None,
    registry=None
):
    

    # -----------------------------
    # Define radii and lengths
    # -----------------------------
    fiber_core_radius = core_radius_mm
    fiber_half_len = half_length_mm

    fiber_cl1_outer_radius = fiber_core_radius + cl1_thickness_mm
    fiber_cl2_outer_radius = fiber_cl1_outer_radius + cl2_thickness_mm
    fiber_outer_r = fiber_cl2_outer_radius + tpb_thickness_mm

    # -----------------------------
    # Core
    # -----------------------------
    core_solid = g4.Tubs(f"{name}_core_solid", 0, fiber_core_radius, fiber_half_len, 0, 360)
    fiber_core_lv = g4.LogicalVolume(core_solid, "Scintillator", f"{name}_core_lv")
    fiber_core_pv = g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], fiber_core_lv, f"{name}_core_pv", None, registry)

    # -----------------------------
    # Cladding 1
    # -----------------------------
    cl1_solid = g4.Tubs(f"{name}_cl1_solid", 0, fiber_cl1_outer_radius, fiber_half_len, 0, 360)
    cl1_lv = g4.LogicalVolume(cl1_solid, "PMMA", f"{name}_cl1_lv")
    cl1_pv = g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], fiber_core_lv, f"{name}_cl1_pv", fiber_core_lv, registry)

    # -----------------------------
    # Cladding 2
    # -----------------------------
    cl2_solid = g4.Tubs(f"{name}_cl2_solid", 0, fiber_cl2_outer_radius, fiber_half_len, 0, 360)
    cl2_lv = g4.LogicalVolume(cl2_solid, "FluoroPolymer", f"{name}_cl2_lv")
    cl2_pv = g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], cl2_lv, f"{name}_cl2_pv", cl1_lv, registry)

    # -----------------------------
    # TPB coating (outermost)
    # -----------------------------
    tpb_solid = g4.Tubs(f"{name}_tpb_solid", 0, fiber_outer_r, fiber_half_len, 0, 360)
    fiber_lv = g4.LogicalVolume(tpb_solid, "TPB", f"{name}_tpb_lv")
    tpb_pv = g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], fiber_lv, f"{name}_tpb_pv", parent_lv, registry)

    # -----------------------------
    # Nest daughters properly
    # -----------------------------
    # Core inside cl1
    g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], fiber_core_lv, f"{name}_core_pv", cl1_lv, registry)
    # Cl1 inside cl2
    g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], cl1_lv, f"{name}_cl1_pv", cl2_lv, registry)
    # Cl2 inside TPB
    g4.PhysicalVolume([0,0,0], [0,0,0,"mm"], cl2_lv, f"{name}_cl2_pv", fiber_lv, registry)

    # -----------------------------
    # Return in the order your code expects
    # -----------------------------
    return fiber_lv, fiber_core_lv, fiber_core_pv, fiber_outer_r, fiber_half_len
'''

def make_fiberoptic_shroud(
    registry,
    lar_lv,
    length,
    r_inner_most,
    t_core,
    t_clad1,
    t_clad2,
    t_tpb,
    material_core,
    material_clad1,
    material_clad2,
    material_tpb,
    base_name="fiber"
):
    """
    Build a fiber optic shroud with layers:
    TPB (innermost) -> Cladding2 inner -> Cladding1 inner -> Core 
    -> Cladding1 outer -> Cladding2 outer (outermost) -> LAr
    All radii are contiguous. Optical surfaces are added between layers.
    """

    # -------------------------
    # Radii (contiguous)
    # -------------------------
    r_tpb_in    = r_inner_most                       # 60 mm
    r_tpb_out   = r_tpb_in + t_tpb                   # 60 + 0.001

    r_cl2_in    = r_tpb_out                          # 60.001
    r_cl2_out   = r_cl2_in + t_clad2                 # 60.001 + 0.4 = 60.401

    r_cl1_in    = r_cl2_out                           # 60.401
    r_cl1_out   = r_cl1_in + t_clad1                  # 60.401 + 0.2 = 60.601

    r_core_in   = r_cl1_out                           # 60.601
    r_core_out  = r_core_in + t_core                  # 60.601 + t_core

    r_cl1_out_in  = r_core_out                       # outer Cladding1 inner radius
    r_cl1_out_out = r_cl1_out_in + t_clad1           # +0.2

    r_cl2_out_in  = r_cl1_out_out                     # outer Cladding2 inner radius
    r_cl2_out_out = r_cl2_out_in + t_clad2           # +0.4


    # -------------------------
    # Solids
    # -------------------------
    tpb_s      = g4.solid.Tubs(f"{base_name}_tpb_s", r_tpb_in, r_tpb_out, length, 0, 2*np.pi, registry=registry, lunit="mm")
    cl2_in_s   = g4.solid.Tubs(f"{base_name}_cl2_in_s", r_cl2_in, r_cl2_out, length, 0, 2*np.pi, registry=registry, lunit="mm")
    cl1_in_s   = g4.solid.Tubs(f"{base_name}_cl1_in_s", r_cl1_in, r_cl1_out, length, 0, 2*np.pi, registry=registry, lunit="mm")
    core_s     = g4.solid.Tubs(f"{base_name}_core_s", r_core_in, r_core_out, length, 0, 2*np.pi, registry=registry, lunit="mm")
    cl1_out_s  = g4.solid.Tubs(f"{base_name}_cl1_out_s", r_cl1_out_in, r_cl1_out_out, length, 0, 2*np.pi, registry=registry, lunit="mm")
    cl2_out_s  = g4.solid.Tubs(f"{base_name}_cl2_out_s", r_cl2_out_in, r_cl2_out_out, length, 0, 2*np.pi, registry=registry, lunit="mm")

    tpb_lv      = g4.LogicalVolume(tpb_s, material_tpb, f"{base_name}_tpb_lv", registry)
    cl2_in_lv   = g4.LogicalVolume(cl2_in_s, material_clad2, f"{base_name}_cl2_in_lv", registry)
    cl1_in_lv   = g4.LogicalVolume(cl1_in_s, material_clad1, f"{base_name}_cl1_in_lv", registry)
    core_lv     = g4.LogicalVolume(core_s, material_core, f"{base_name}_core_lv", registry)
    cl1_out_lv  = g4.LogicalVolume(cl1_out_s, material_clad1, f"{base_name}_cl1_out_lv", registry)
    cl2_out_lv  = g4.LogicalVolume(cl2_out_s, material_clad2, f"{base_name}_cl2_out_lv", registry)
    
    tpb_pv     = g4.PhysicalVolume([0,0,0],[0,0,0,"mm"], tpb_lv, f"{base_name}_tpb_pv", cl2_in_lv, registry)
    cl2_in_pv  = g4.PhysicalVolume([0,0,0],[0,0,0,"mm"], cl2_in_lv, f"{base_name}_cl2_in_pv", cl1_in_lv, registry)
    cl1_in_pv  = g4.PhysicalVolume([0,0,0],[0,0,0,"mm"], cl1_in_lv, f"{base_name}_cl1_in_pv", core_lv, registry)
    core_pv    = g4.PhysicalVolume([0,0,0],[0,0,0,"mm"], core_lv, f"{base_name}_core_pv", cl1_out_lv, registry)
    cl1_out_pv = g4.PhysicalVolume([0,0,0],[0,0,0,"mm"], cl1_out_lv, f"{base_name}_cl1_out_pv", cl2_out_lv, registry)
    cl2_out_pv = g4.PhysicalVolume([0,0,0],[0,0,0,"mm"], cl2_out_lv, f"{base_name}_cl2_out_pv", lar_lv, registry)


  

    # -------------------------
    # Optical boundaries
    # -------------------------
    osurf = g4.solid.OpticalSurface(
        f"{base_name}_os",
        model="unified",
        finish="polished",
        surf_type="dielectric_dielectric",
        value=1.0,
        registry=registry
    )

    for lv in (tpb_lv, cl2_in_lv, cl1_in_lv, core_lv, cl1_out_lv, cl2_out_lv):
        g4.SkinSurface(f"{lv.name}_os", lv, osurf, registry=registry)

    # -------------------------
    # Return
    # -------------------------
    return cl2_out_lv, {
        "tpb_pv": tpb_pv,
        "cl2_in_pv": cl2_in_pv,
        "cl1_in_pv": cl1_in_pv,
        "core_pv": core_pv,
        "cl1_out_pv": cl1_out_pv,
        "cl2_out_pv": cl2_out_pv,
        "tpb_lv": tpb_lv,
        "cl2_in_lv": cl2_in_lv,
        "cl1_in_lv": cl1_in_lv,
        "core_lv": core_lv,
        "cl1_out_lv": cl1_out_lv,
        "cl2_out_lv": cl2_out_lv
    }


fiber_outer_lv, fibers_dict = make_fiberoptic_shroud(
    registry=reg,
    lar_lv=lar_lv,
    length=220.0,
    r_inner_most=60.0,
    t_core = 1.0,
    t_clad1=0.2,
    t_clad2=0.4,
    t_tpb=0.001,
    material_core=mats.ps_fibers,
    material_clad1=mats.pmma,
    material_clad2=mats.pmma_out,
    material_tpb=mats.tpb_on_fibers,
    base_name="fiber_shroud"
)





# Access core for border surfaces
fiber_outer_pv = fibers_dict["cl2_out_pv"]
fiber_core_pv = fibers_dict["core_pv"]
tpb_pv = fibers_dict["tpb_pv"]


# -----------------------------
# Access PVs and LVs for optical surfaces / other use
# -----------------------------
fiber_core_pv = fibers_dict["core_pv"]
tpb_pv = fibers_dict["tpb_pv"]
cl1_in_pv = fibers_dict["cl1_in_pv"]
cl2_in_pv = fibers_dict["cl2_in_pv"]
cl2_out_lv = fibers_dict["cl2_out_lv"]
cl2_out_pv =fibers_dict["cl2_out_pv"]

fiber_outer_lv = fibers_dict["cl2_out_lv"]  # outermost logical volume



fibers =[]
# Save core PV for border surface
fibers = [{"fiber_core_phys": fiber_core_pv}]

# Place the entire fiber optic inside the LAr volume
cl2_out_pv = g4.PhysicalVolume(
    [0, 0, 0],              # position (x, y, z) in mm
    [0, 0, 0, "mm"],        # rotation (no rotation)
    cl2_out_lv,             # logical volume to place
    "fiber_shroud_cl2", # name of the physical volume
    lar_lv,                 # mother logical volume (LAr)
    registry=reg
)
# -----------------------------
# Build nested fiber shroud (single call)
# -----------------------------

# -----------------------------
# 2️⃣ Circular SiPM (G4_Si)
# -----------------------------
sipm_inner_r_mm = 60.0

fiber_outer_lv = fibers_dict["cl2_out_lv"]  # logical volume of outermost fiber
fiber_outer_r_mm = fiber_outer_lv.solid.pRMax  # outer radius
fiber_half_len_mm = fiber_outer_lv.solid.pDz  # half-length along z

print("Half-length along Z (mm):", fiber_outer_lv.solid.pDz)
print("Inner radius (mm):", fiber_outer_lv.solid.pRMin)
print("Outer radius (mm):", fiber_outer_lv.solid.pRMax)


sipm_outer_r_mm = fiber_outer_r_mm  # match fiber outer radius
sipm_half_thickness_mm = 0.5        # 1 mm thick -> half-length 0.5 mm

sipm_ring_s = solid.Tubs(
    "sipm_ring_s",
    sipm_inner_r_mm,
    sipm_outer_r_mm,
    sipm_half_thickness_mm,
    0,
    2 * math.pi,
    registry=reg,
    lunit="mm"
)



sipm_ring_lv = g4.LogicalVolume(sipm_ring_s, g4.MaterialPredefined("G4_Si"), "sipm_ring_lv", registry=reg)

# -----------------------------
# 3️⃣ Place top & bottom SiPMs
# -----------------------------
sipm_z_top = fiber_half_len_mm/2. + sipm_half_thickness_mm
sipm_z_bottom = -fiber_half_len_mm/2. - sipm_half_thickness_mm

sipm_top_pv = g4.PhysicalVolume(
    [0, 0, 0, "deg"],
    [0, 0, sipm_z_top, "mm"],
    sipm_ring_lv,
    "sipm_top_pv",
    lar_lv,
    reg
)

sipm_bottom_pv = g4.PhysicalVolume(
    [0, 0, 0, "deg"],
    [0, 0, sipm_z_bottom, "mm"],
    sipm_ring_lv,
    "sipm_bottom_pv",
    lar_lv,
    reg
)

# -----------------------------
# 4️⃣ Optical surface
# -----------------------------
sipm_surf = g4.solid.OpticalSurface(
    name="sipm_surf",
    model="unified",
    finish="polished",
    surf_type="dielectric_metal",
    value=1.0,
    registry=reg
)

# SkinSurface for visual / optical properties
g4.SkinSurface("surface_sipm_top", sipm_ring_lv, sipm_surf, reg)
g4.SkinSurface("surface_sipm_bottom", sipm_ring_lv, sipm_surf, reg)

# -----------------------------
# 5️⃣ BorderSurface: fiber core -> SiPM
# -----------------------------
g4.BorderSurface(
    "fiber_to_sipm_top",
    fibers[0]["fiber_core_phys"],  # fiber core PV
    sipm_top_pv,
    sipm_surf,
    reg
)

g4.BorderSurface(
    "fiber_to_sipm_bottom",
    fibers[0]["fiber_core_phys"],
    sipm_bottom_pv,
    sipm_surf,
    reg
)

sipm_surf.addVecProperty("EFFICIENCY", [1, 10], [1, 1])
sipm_surf.addVecProperty("REFLECTIVITY", [1, 10], [0, 0])


bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 101, bege_meta)
icpc_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 102, icpc_meta)
enclosure_bege_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 201, "name:enclosure_bege_pv")
enclosure_icpc_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 202, "name:enclosure_icpc_pv")
sipm_top_pv.pygeom_active_detector = RemageDetectorInfo("optical", 301, {"name": "sipm_top_pv"})
sipm_bottom_pv.pygeom_active_detector = RemageDetectorInfo("optical", 302, {"name": "sipm_bottom_pv"})
lar_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 401, {"name": "LAr_pv"})


# -----------------------------
# Add detector origins (so your tools that expect these keep working)
# -----------------------------
for pv in [bege_pv, icpc_pv, enclosure_bege_pv, enclosure_icpc_pv, lar_pv]:
    add_detector_origin(pv.name, pv, reg)


# -----------------------------
# Visualization (colours)
# -----------------------------
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "liquid_argon": [0, 1, 1, 0.08],
        "PEN": [0.0, 0.6, 0.6, 0.4],
        "ps_fibers": [1, 0, 0, 0.6],
        "pmma": [0, 1, 0, 0.3],
        "pmma_cl2": [0, 1, 0, 0.3],
        "tpb_on_fibers": [1, 1, 0, 0],
        "G4_Si":[1.0, 0.5, 0.0, 1.0]
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

# done
