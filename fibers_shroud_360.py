#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations
import pyg4ometry.geant4 as g4
from pygeoml1000.fibers import FiberModuleData, ModuleFactorySingleFibers


# ============================================================
# Dummy container (NO world, NO geometry)
# ============================================================
class DummyB:
    def __init__(self, registry, materials, hpge_string):
        self.registry = registry
        self.materials = materials
        self.runtime_config = {}

        # Metadata for fiber placement
        self.special_metadata = type("", (), {})()
        self.special_metadata.hpge_string = hpge_string


# ============================================================
# Fiber builder
# ============================================================
def build_fiber_shroud(registry, lar_pv, hpge_string, materials):
    """
    Build 360° LEGEND fiber shroud and attach SiPMs
    inside the existing LAr physical volume.
    """

    # ------------------------------------------------------------
    # 1) Container for pygeoml1000
    # ------------------------------------------------------------
    b = DummyB(registry, materials, hpge_string)

    # Tell pygeoml1000 where to place geometry
    b.mother_lv = lar_pv.logicalVolume
    b.mother_pv = lar_pv
    b.mother_z_displacement = 0.0
    b.mother_x_displacement = 0.0

    # This is the CRITICAL line: attach new PVs to LAr_pv
    registry._world = lar_pv

    # ------------------------------------------------------------
    # 2) Define fiber modules
    # ------------------------------------------------------------
    mods = []
    for i in range(6):
        mods.append(
            FiberModuleData(
                barrel="inner",
                name=f"IB{i}",
                tpb_thickness=150,  # nm
                channel_top_name=f"sipm_top_{i}",
                channel_bottom_name=f"sipm_bot_{i}",
                channel_top_rawid=1000 + 2 * i,
                channel_bottom_rawid=1001 + 2 * i,
                string_id=str(i),
            )
        )

    # ------------------------------------------------------------
    # 3) Fiber factory
    # ------------------------------------------------------------
    factory = ModuleFactorySingleFibers(
        radius_mm=50,
        fiber_length_mm=200,
        fiber_count_per_module=45,
        bend_radius_mm=None,
        number_of_modules=6,
        z_displacement_mm=100,
        materials=materials,
        registry=registry,
    )

    # ------------------------------------------------------------
    # 4) Build fibers + SiPMs inside LAr
    # ------------------------------------------------------------
    for m in mods:
        factory.create_module(m, b)

    # ------------------------------------------------------------
    # 5) Collect SiPM physical volumes
    # ------------------------------------------------------------
    sipms = {
        pv.name: pv
        for pv in registry.physicalVolumeDict.values()
        if pv.name.startswith("sipm_")
    }

    return sipms
