#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations
import pint
import pyg4ometry.geant4 as g4
import pyg4ometry as pg4

from pygeoml1000.fibers import FiberModuleData, ModuleFactorySingleFibers
from pygeomtools.materials import BaseMaterialRegistry, cached_property

import pygeomoptics.lar
import pygeomoptics.fibers
import pygeomoptics.tpb

u = pint.get_application_registry()
reg = g4.Registry()

# ============================================================
# Optical materials (UNCHANGED)
# ============================================================
class OpticalMaterialRegistry(BaseMaterialRegistry):
    def __init__(self, g4_registry):
        self.lar_temperature = 88.8 * u.K
        super().__init__(g4_registry)

    @cached_property
    def liquidargon(self):
        lar = g4.Material(
            name="liquid_argon", density=1.390, number_of_components=1,
            state="liquid", temperature=float(self.lar_temperature.m_as(u.kelvin)),
            pressure=1.0e5, registry=self.g4_registry)
        lar.add_element_natoms(self.get_element("Ar"), 1)
        pygeomoptics.lar.pyg4_lar_attach_rindex(lar, self.g4_registry)
        pygeomoptics.lar.pyg4_lar_attach_attenuation(
            lar_mat=lar, reg=self.g4_registry, lar_temperature=self.lar_temperature,
            lar_dielectric_method="cern2020",
            attenuation_method_or_length="legend200-llama",
            rayleigh_enabled_or_length=True,
            absorption_enabled_or_length=True)
        pygeomoptics.lar.pyg4_lar_attach_scintillation(
            lar, self.g4_registry, flat_top_yield=1000/u.MeV)
        return lar

    @cached_property
    def pmma(self):
        m = g4.Material(name="pmma", density=1.20, number_of_components=3, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("C"),5)
        m.add_element_natoms(self.get_element("H"),8)
        m.add_element_natoms(self.get_element("O"),2)
        pygeomoptics.fibers.pyg4_fiber_cladding1_attach_rindex(m, self.g4_registry)
        return m

    @cached_property
    def pmma_out(self):
        m = g4.Material(name="pmma_cl2", density=1.20, number_of_components=3, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("C"),5)
        m.add_element_natoms(self.get_element("H"),8)
        m.add_element_natoms(self.get_element("O"),2)
        pygeomoptics.fibers.pyg4_fiber_cladding2_attach_rindex(m, self.g4_registry)
        return m

    @cached_property
    def ps_fibers(self):
        m = g4.Material(name="ps_fibers", density=1.05, number_of_components=2, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("C"),8)
        m.add_element_natoms(self.get_element("H"),8)
        pygeomoptics.fibers.pyg4_fiber_core_attach_rindex(m, self.g4_registry)
        pygeomoptics.fibers.pyg4_fiber_core_attach_absorption(m, self.g4_registry)
        pygeomoptics.fibers.pyg4_fiber_core_attach_wls(m, self.g4_registry)
        pygeomoptics.fibers.pyg4_fiber_core_attach_scintillation(m, self.g4_registry)
        return m

    @cached_property
    def metal_silicon(self):
        m = g4.Material(name="metal_silicon", density=2.33, number_of_components=1, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("Si"),1)
        return m

    @cached_property
    def metal_copper(self):
        m = g4.Material(name="metal_copper", density=8.96, number_of_components=1, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("Cu"),1)
        return m

    @cached_property
    def tetratex(self):
        m = g4.Material(name="tetratex", density=2.2, number_of_components=1, registry=self.g4_registry)
        m.add_element_natoms(self.get_element("C"),1)
        return m

    @cached_property
    def tpb_on_fibers(self):
        m = g4.Material(name="tpb_on_fibers", density=1.08, number_of_components=2, state="solid", registry=self.g4_registry)
        m.add_element_natoms(self.get_element("H"),22)
        m.add_element_natoms(self.get_element("C"),28)
        pygeomoptics.tpb.pyg4_tpb_attach_rindex(m, self.g4_registry)
        pygeomoptics.tpb.pyg4_tpb_attach_wls(m, self.g4_registry)
        return m

   
    @cached_property
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

# ============================================================
# Dummy Instrumentation
# ============================================================
class DummyB:
    def __init__(self):
        self.registry = reg
        self.materials = OpticalMaterialRegistry(reg)
        self.runtime_config = {}

        class C:
            def __init__(self,x,y): self.x_in_mm=x; self.y_in_mm=y
        class S:
            def __init__(self,a,r): self.angle_in_deg=a; self.radius_in_mm=r; self.center=C(0,0)

        self.special_metadata = type("",(),{})()
        self.special_metadata.hpge_string = {
            "0": S(0,150),
            "1": S(120,150),
            "2": S(240,150),
        }

        world = g4.solid.Box("world",4000,4000,4000,reg)
        self.mother_lv = g4.LogicalVolume(world, self.materials.liquidargon, "world_lv", reg)
        self.mother_pv = g4.PhysicalVolume([0,0,0],[0,0,0],self.mother_lv,"world_pv",None,reg)

b = DummyB()

# ============================================================
# 3 fiber modules → 360°
# ============================================================
mods = [
    FiberModuleData(
        barrel="inner",
        name="IB0",
        tpb_thickness=150,
        channel_top_name="sipm_top_0",
        channel_bottom_name="sipm_bot_0",
        channel_top_rawid=1,
        channel_bottom_rawid=2,
        string_id="0",
    ),
    FiberModuleData(
        barrel="inner",
        name="IB1",
        tpb_thickness=150,
        channel_top_name="sipm_top_1",
        channel_bottom_name="sipm_bot_1",
        channel_top_rawid=3,
        channel_bottom_rawid=4,
        string_id="1",
    ),
    FiberModuleData(
        barrel="inner",
        name="IB2",
        tpb_thickness=150,
        channel_top_name="sipm_top_2",
        channel_bottom_name="sipm_bot_2",
        channel_top_rawid=5,
        channel_bottom_rawid=6,
        string_id="2",
    ),
]



factory = ModuleFactorySingleFibers(
    radius_mm=150,
    fiber_length_mm=1200,
    fiber_count_per_module=200,
    bend_radius_mm=None,
    number_of_modules=3,
    z_displacement_mm=0,
    materials=b.materials,
    registry=reg,
)

for m in mods:
    factory.create_module(m,b)

print("Fiber shroud successfully built")
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "liquid_argon":  [0.6, 0.8, 1.0, 0.10],
        "ps_fibers":    [0.0, 1.0, 0.0, 0.8],
        "pmma":         [0.8, 0.8, 0.8, 0.4],
        "pmma_cl2":     [0.4, 0.4, 0.4, 0.4],
        "tpb_on_fibers":[1.0, 1.0, 0.0, 0.6],
        "metal_silicon":[1.0, 0.0, 0.0, 1.0],
        "metal_copper":[1.0, 0.5, 0.0, 1.0],
        "tetratex":     [1.0, 1.0, 1.0, 0.6],
    }
)

viewer.addLogicalVolume(b.mother_lv)
viewer.view()

