#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

import pyg4ometry.geant4 as g4
import pyg4ometry as pg4
from math import pi
from functools import cached_property
import legendoptics.fibers
import legendoptics.tpb
import legendoptics.lar
import numpy as np
from pygeomtools.materials import BaseMaterialRegistry, cached_property

# -----------------------------
# Registry
# -----------------------------
reg = g4.Registry()

# -----------------------------
# Material Registry
# -----------------------------
class OpticalMaterialRegistry(BaseMaterialRegistry):
    def __init__(self, g4_registry: g4.Registry):
        self.lar_temperature = 88.8
        super().__init__(g4_registry)

    @cached_property
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
        legendoptics.lar.pyg4_lar_attach_rindex(_lar, self.g4_registry)
        return _lar

    @cached_property
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

    @cached_property
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

    @cached_property
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

    @cached_property
    def tpb_on_fibers(self) -> g4.Material:
        return self._tpb("tpb_on_fibers")

    @cached_property
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

# -----------------------------
# Instantiate materials
# -----------------------------
mats = OpticalMaterialRegistry(reg)

# -----------------------------
# World volume (LAr)
# -----------------------------
world_s = g4.solid.Box("world_s", 1000, 1000, 1000, registry=reg, lunit="mm")
world_lv = g4.LogicalVolume(world_s, mats.liquidargon, "world_lv", registry=reg)
reg.setWorld(world_lv)

# -----------------------------
# Hollow fiberoptic shroud
# -----------------------------
inner_radius = 300.0        # mm (40 cm)
core_thickness = 1.0        # mm
cl2_thickness = 0.4         # mm
cl1_thickness = 0.2         # mm
fiber_length = 900.0        # mm
tpb_thickness = 0.001       # mm

# Compute radii from inside out
r0 = inner_radius
r1 = r0 + tpb_thickness
r2 = r1 + cl1_thickness
r3 = r2 + cl2_thickness
r4 = r3 + core_thickness
r5 = r4 + cl2_thickness
r6 = r5 + cl1_thickness

# -----------------------------
# Define concentric cylindrical layers
# -----------------------------
# TPB layer (innermost)
tpb_s = g4.solid.Tubs("tpb_s", r0, r1, fiber_length/2, 0, 2*pi, registry=reg, lunit="mm")
tpb_lv = g4.LogicalVolume(tpb_s, mats.tpb_on_fibers, "tpb_lv", reg)

# Inner Cladding1
cl1_inner_s = g4.solid.Tubs("cl1_inner_s", r1, r2, fiber_length/2, 0, 2*pi, registry=reg, lunit="mm")
cl1_inner_lv = g4.LogicalVolume(cl1_inner_s, mats.pmma, "cl1_inner_lv", reg)
g4.PhysicalVolume([0, 0, 0], [0, 0, 0], tpb_lv, "tpb_in_cl1_inner", cl1_inner_lv, reg)

# Inner Cladding2
cl2_inner_s = g4.solid.Tubs("cl2_inner_s", r2, r3, fiber_length/2, 0, 2*pi, registry=reg, lunit="mm")
cl2_inner_lv = g4.LogicalVolume(cl2_inner_s, mats.pmma_out, "cl2_inner_lv", reg)
g4.PhysicalVolume([0,0,0], [0,0,0], cl1_inner_lv, "cl1_in_cl2_inner", cl2_inner_lv, reg)

# Core
core_s = g4.solid.Tubs("core_s", r3, r4, fiber_length/2, 0, 2*pi, registry=reg, lunit="mm")
core_lv = g4.LogicalVolume(core_s, mats.ps_fibers, "core_lv", reg)
g4.PhysicalVolume([0,0,0], [0,0,0], cl2_inner_lv, "cl2_inner_in_core", core_lv, reg)

# Outer Cladding2
cl2_outer_s = g4.solid.Tubs("cl2_outer_s", r4, r5, fiber_length/2, 0, 2*pi, registry=reg, lunit="mm")
cl2_outer_lv = g4.LogicalVolume(cl2_outer_s, mats.pmma_out, "cl2_outer_lv", reg)
g4.PhysicalVolume([0,0,0], [0,0,0], core_lv, "core_in_cl2_outer", cl2_outer_lv, reg)

# Outer Cladding1
cl1_outer_s = g4.solid.Tubs("cl1_outer_s", r5, r6, fiber_length/2, 0, 2*pi, registry=reg, lunit="mm")
cl1_outer_lv = g4.LogicalVolume(cl1_outer_s, mats.pmma, "cl1_outer_lv", reg)
g4.PhysicalVolume([0,0,0], [0,0,0], cl2_outer_lv, "cl2_outer_in_cl1_outer", cl1_outer_lv, reg)

# Place the shroud in the world
fiber_phys = g4.PhysicalVolume([0,0,0], [0,0,0], cl1_outer_lv, "fiber_phys", world_lv, reg)

# -----------------------------
# Optical surfaces
# -----------------------------
osurf = g4.solid.OpticalSurface(
    "fiber_os",
    model="unified",
    finish="polished",
    surf_type="dielectric_dielectric",
    value=1.0,
    registry=reg
)
g4.SkinSurface("tpb_os", tpb_lv, osurf, reg)
g4.SkinSurface("cl1_inner_os", cl1_inner_lv, osurf, reg)
g4.SkinSurface("cl2_inner_os", cl2_inner_lv, osurf, reg)
g4.SkinSurface("core_os", core_lv, osurf, reg)
g4.SkinSurface("cl2_outer_os", cl2_outer_lv, osurf, reg)
g4.SkinSurface("cl1_outer_os", cl1_outer_lv, osurf, reg)

# -----------------------------
# Visualization
# -----------------------------
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "ps_fibers": [1, 0, 0, 0.6],        # core → red, semi-transparent
        "pmma": [0, 1, 0, 0.3],             # cladding1 → green
        "pmma_cl2": [0, 0, 1, 0.3],         # cladding2 → blue
        "tpb_on_fibers": [1, 1, 0, 0.5],    # TPB → yellow
        "liquid_argon": [0, 1, 1, 0.1]      # LAr → cyan, very transparent
    }
)
viewer.addLogicalVolume(world_lv)
viewer.view()
