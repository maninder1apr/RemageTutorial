#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
# -*- coding: utf-8 -*-

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

# -----------------------------
# Material registry (cached_property)
# -----------------------------
class OpticalMaterialRegistry(BaseMaterialRegistry):
    def __init__(self, g4_registry: g4.Registry):
        self.lar_temperature = 88.8 * u.K
        super().__init__(g4_registry)

    @pg_cached_property
    def liquidargon(self) -> g4.Material:
        _lar = g4.Material(
            name="liquid_argon",
            density=1.390,
            number_of_components=1,
            state="liquid",
            temperature=self.lar_temperature,
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

    # -------------------------
    # PEN material as cached property
    # -------------------------
    @pg_cached_property
    def pen(self) -> g4.Material:
        # Build the PEN material once and attach optical properties via legendoptics.pen
        m = g4.Material(
            name="PEN",
            density=1.30,
            number_of_components=3,
            state="solid",
            temperature=293.15,
            registry=self.g4_registry,
        )
        # use base elements from registry
        m.add_element_natoms(self.get_element("C"), natoms=14)
        m.add_element_natoms(self.get_element("H"), natoms=10)
        m.add_element_natoms(self.get_element("O"), natoms=4)
        # attach PEN optical properties
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
    registry.detector_origins[name] = {
        "xloc": pv.position[0],
        "yloc": pv.position[1],
        "zloc": pv.position[2],
    }

# -----------------------------
# World & LAr (units: cm)
# -----------------------------
world_s = solid.Box("world_s", 200, 200, 200, registry=reg, lunit="cm")
world_lv = g4.LogicalVolume(world_s, mats.liquidargon, "World_lv", registry=reg)
reg.setWorld(world_lv)

# LAr detector volume (same as earlier example)
lar_radius_cm = 12.0   # cm
lar_half_height_cm = 25.0  # cm
lar_s = solid.Tubs("LAr_s", 0, lar_radius_cm, lar_half_height_cm, 0, 2 * math.pi, registry=reg, lunit="cm")
lar_lv = g4.LogicalVolume(lar_s, mats.liquidargon, "LAr_lv", registry=reg, lunit="cm")
lar_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], lar_lv, "LAr_pv", world_lv, registry=reg)

# -----------------------------
# HPGe detectors (use same meta as before)
# -----------------------------

bege_meta = {
    "name": "B00000B",
    "type": "bege",
    "production": {"enrichment": {"val": 0.874, "unc": 0.003}, "mass_in_g": 697.0},
    "geometry": {
        "height_in_mm": 32.00,
        "radius_in_mm": 37.00,
        "groove": {"depth_in_mm": 2.0, "radius_in_mm": {"outer": 10.5, "inner": 7.5}},
        "pp_contact": {"radius_in_mm": 7.5, "depth_in_mm": 0},
        "taper": {"top": {"angle_in_deg": 0.0, "height_in_mm": 0.0}, "bottom": {"angle_in_deg": 45.0, "height_in_mm": 5.0}},
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

# create logical volumes using legendhpges helper
bege_lv = make_hpge(bege_meta, name="BEGe_L", registry=reg)
coax_lv = make_hpge(coax_meta, name="Coax_L", registry=reg)

# detector positions (cm)
bege_pos = [0, 0, 7.0, "cm"]
coax_pos = [0, 0, -7.0, "cm"]

bege_pv = g4.PhysicalVolume([0, 0, 0], bege_pos, bege_lv, "BEGe_pv", lar_lv, registry=reg)
coax_pv = g4.PhysicalVolume([0, 0, 0], coax_pos, coax_lv, "Coax_pv", lar_lv, registry=reg)

# mark them as active detectors
bege_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 1, bege_meta)
coax_pv.pygeom_active_detector = RemageDetectorInfo("germanium", 2, coax_meta)

# -----------------------------
# Single PEN shroud (one entity) around both detectors
# -----------------------------
# Parameters (user requested):
clearance_cm = 1.0         # 1 cm clearance between HPGe exterior and PEN inner surface
pen_thickness_cm = 0.30   # 3 mm -> 0.30 cm

# Determine the largest detector outer radius (in cm) and half-height
bege_radius_cm = bege_meta["geometry"]["radius_in_mm"] / 10.0
bege_half_height_cm = bege_meta["geometry"]["height_in_mm"] / 20.0
coax_radius_cm = coax_meta["geometry"]["radius_in_mm"] / 10.0
coax_half_height_cm = coax_meta["geometry"]["height_in_mm"] / 20.0

max_det_radius_cm = max(bege_radius_cm, coax_radius_cm)
max_half_height_cm = max(bege_half_height_cm, coax_half_height_cm)

# PEN inner radius (cm) and outer radius
pen_inner_r = max_det_radius_cm + clearance_cm
pen_outer_r = pen_inner_r + pen_thickness_cm

# Make the PEN height such that it fully covers detectors + some margin
# Detectors sit at +/- 7 cm in z; we'll compute PEN center & half-height to cover both.
# We'll cover the z-range of both detectors plus a margin (here 1 cm)
det_top_z = max(bege_pos[2] + bege_half_height_cm, coax_pos[2] + coax_half_height_cm)
det_bottom_z = min(bege_pos[2] - bege_half_height_cm, coax_pos[2] - coax_half_height_cm)
required_height = (det_top_z - det_bottom_z) + 2.0  # add 2 cm margin (1 cm top, 1 cm bottom)
pen_half_height = required_height / 2.0

pen_s = solid.Tubs("PEN_shroud_s", pen_inner_r, pen_outer_r, pen_half_height, 0, 2 * math.pi, registry=reg, lunit="cm")
pen_lv = g4.LogicalVolume(pen_s, mats.pen, "PEN_shroud_lv", registry=reg)
# place centered at z = (det_top + det_bottom)/2
pen_center_z = (det_top_z + det_bottom_z) / 2.0
pen_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, pen_center_z, "cm"], pen_lv, "PEN_shroud_pv", lar_lv, registry=reg)

# register PEN as scintillator
pen_pv.pygeom_active_detector = RemageDetectorInfo("scintillator", 3, {"name": "PEN_shroud"})

# -----------------------------
# Fiber-optic hollow shroud (concentric, around PEN)
# -----------------------------
# Convert fiber thicknesses to cm
core_thickness_mm = 1.0       # 1.0 mm
cl2_thickness_mm = 0.4        # 0.4 mm
cl1_thickness_mm = 0.2        # 0.2 mm
tpb_thickness_mm = 0.001      # 0.001 mm (very thin)

core_thickness = core_thickness_mm / 10.0   # cm
cl2_thickness = cl2_thickness_mm / 10.0     # cm
cl1_thickness = cl1_thickness_mm / 10.0     # cm
tpb_thickness = tpb_thickness_mm / 10.0     # cm

fiber_inner_clearance_cm = 1.0  # 1 cm clearance between PEN outer surface and inner radius of fiber shroud
fiber_inner_r = pen_outer_r + fiber_inner_clearance_cm

# Radii from inside to out for concentric layers:
r0 = fiber_inner_r                    # inner surface (start)
r_tpb_out = r0 + tpb_thickness        # after TPB
r_cl1_in = r_tpb_out
r_cl1_out = r_cl1_in + cl1_thickness
r_cl2_in = r_cl1_out
r_cl2_out = r_cl2_in + cl2_thickness
r_core_in = r_cl2_out
r_core_out = r_core_in + core_thickness
r_cl2_out2 = r_core_out + cl2_thickness
r_cl1_out2 = r_cl2_out2 + cl1_thickness

fiber_length_cm = max( (2 * lar_half_height_cm), (required_height + 10.0) )  # make it at least slightly larger than PEN / LAr interior
fiber_half_len = fiber_length_cm / 2.0

# Build TPB (innermost)
tpb_s = solid.Tubs("fiber_tpb_s", r0, r_tpb_out, fiber_half_len, 0, 2 * math.pi, registry=reg, lunit="cm")
tpb_lv = g4.LogicalVolume(tpb_s, mats.tpb_on_fibers, "fiber_tpb_lv", registry=reg)
# cladding1 inner
cl1_inner_s = solid.Tubs("fiber_cl1_inner_s", r_tpb_out, r_cl1_out, fiber_half_len, 0, 2 * math.pi, registry=reg, lunit="cm")
cl1_inner_lv = g4.LogicalVolume(cl1_inner_s, mats.pmma, "fiber_cl1_inner_lv", registry=reg)
g4.PhysicalVolume([0,0,0], [0,0,0], tpb_lv, "tpb_in_cl1_inner", cl1_inner_lv, registry=reg)
# cladding2 inner
cl2_inner_s = solid.Tubs("fiber_cl2_inner_s", r_cl1_out, r_cl2_out, fiber_half_len, 0, 2 * math.pi, registry=reg, lunit="cm")
cl2_inner_lv = g4.LogicalVolume(cl2_inner_s, mats.pmma_out, "fiber_cl2_inner_lv", registry=reg)
g4.PhysicalVolume([0,0,0], [0,0,0], cl1_inner_lv, "cl1_in_cl2_inner", cl2_inner_lv, registry=reg)
# core
core_s = solid.Tubs("fiber_core_s", r_core_in, r_core_out, fiber_half_len, 0, 2 * math.pi, registry=reg, lunit="cm")
core_lv = g4.LogicalVolume(core_s, mats.ps_fibers, "fiber_core_lv", registry=reg)
g4.PhysicalVolume([0,0,0], [0,0,0], cl2_inner_lv, "cl2_inner_in_core", core_lv, registry=reg)
# outer cladding2
cl2_outer_s = solid.Tubs("fiber_cl2_outer_s", r_core_out, r_cl2_out2, fiber_half_len, 0, 2 * math.pi, registry=reg, lunit="cm")
cl2_outer_lv = g4.LogicalVolume(cl2_outer_s, mats.pmma_out, "fiber_cl2_outer_lv", registry=reg)
g4.PhysicalVolume([0,0,0], [0,0,0], core_lv, "core_in_cl2_outer", cl2_outer_lv, registry=reg)
# outer cladding1
cl1_outer_s = solid.Tubs("fiber_cl1_outer_s", r_cl2_out2, r_cl1_out2, fiber_half_len, 0, 2 * math.pi, registry=reg, lunit="cm")
cl1_outer_lv = g4.LogicalVolume(cl1_outer_s, mats.pmma, "fiber_cl1_outer_lv", registry=reg)
g4.PhysicalVolume([0,0,0], [0,0,0], cl2_outer_lv, "cl2_outer_in_cl1_outer", cl1_outer_lv, registry=reg)

# place the fiber shroud (concentric around PEN) - center at origin
fiber_phys = g4.PhysicalVolume([0,0,0], [0,0,0, "cm"], cl1_outer_lv, "fiber_shroud_pv", lar_lv, registry=reg)

# -----------------------------
# Optical surfaces for fiber layers
# -----------------------------
osurf = g4.solid.OpticalSurface("fiber_os", model="unified", finish="polished", surf_type="dielectric_dielectric", value=1.0, registry=reg)
g4.SkinSurface("tpb_os", tpb_lv, osurf, registry=reg)
g4.SkinSurface("cl1_inner_os", cl1_inner_lv, osurf, registry=reg)
g4.SkinSurface("cl2_inner_os", cl2_inner_lv, osurf, registry=reg)
g4.SkinSurface("core_os", core_lv, osurf, registry=reg)
g4.SkinSurface("cl2_outer_os", cl2_outer_lv, osurf, registry=reg)
g4.SkinSurface("cl1_outer_os", cl1_outer_lv, osurf, registry=reg)

# -----------------------------
# Add detector origins (so your tools that expect these keep working)
# -----------------------------
for pv in [bege_pv, coax_pv, pen_pv, fiber_phys, lar_pv]:
    add_detector_origin(pv.name, pv, reg)

# -----------------------------
# Print geometry summary (all key dimensions) for quick verification
# -----------------------------
print("===== Geometry summary (units: cm unless noted) =====")
print(f"HPGe BEGe radius: {bege_radius_cm:.3f} cm, half-height: {bege_half_height_cm:.3f} cm, position z: {bege_pos[2]} cm")
print(f"HPGe Coax radius: {coax_radius_cm:.3f} cm, half-height: {coax_half_height_cm:.3f} cm, position z: {coax_pos[2]} cm")
print("")
print("PEN shroud:")
print(f"  clearance to detectors: {clearance_cm:.3f} cm")
print(f"  pen inner radius: {pen_inner_r:.3f} cm")
print(f"  pen outer radius: {pen_outer_r:.3f} cm (thickness {pen_thickness_cm:.3f} cm)")
print(f"  pen half-height: {pen_half_height:.3f} cm, center z: {pen_center_z:.3f} cm")
print("")
print("Fiber shroud (concentric, from inside → out):")
print(f"  fiber inner clearance from PEN outer radius: {fiber_inner_clearance_cm:.3f} cm")
print(f"  TPB thickness (mm): {tpb_thickness_mm:.6f} mm  (={tpb_thickness:.6f} cm)")
print(f"  core thickness: {core_thickness_mm:.3f} mm (={core_thickness:.4f} cm)")
print(f"  cladding2 thickness: {cl2_thickness_mm:.3f} mm (={cl2_thickness:.4f} cm)")
print(f"  cladding1 thickness: {cl1_thickness_mm:.3f} mm (={cl1_thickness:.4f} cm)")
print("")
print("  computed concentric radii (inner→outer):")
print(f"    r0 (fiber inner radius) = {r0:.4f} cm")
print(f"    r_tpb_out = {r_tpb_out:.4f} cm")
print(f"    r_cl1_out = {r_cl1_out:.4f} cm")
print(f"    r_cl2_out = {r_cl2_out:.4f} cm")
print(f"    r_core_out = {r_core_out:.4f} cm")
print(f"    r_cl2_out2 = {r_cl2_out2:.4f} cm")
print(f"    r_cl1_out2 = {r_cl1_out2:.4f} cm (outermost)")
print("")
print(f"  fiber half-length (z): {fiber_half_len:.3f} cm (total length {fiber_length_cm:.3f} cm)")
print("=====================================================")

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
    }
)
viewer.addLogicalVolume(reg.getWorldVolume())
viewer.view()

# -----------------------------
# Export GDML
# -----------------------------
write_pygeom(reg, "combined_geometry.gdml")
print("✅ Written combined_geometry.gdml")
