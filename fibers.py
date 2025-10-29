#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

from __future__ import annotations

import pyg4ometry as pg4
import pyg4ometry.geant4 as g4
from math import pi
import legendoptics.fibers
import legendoptics.lar
import legendoptics.tpb
import numpy as np
import pint
from pygeomtools import RemageDetectorInfo
import pygeomtools
from pygeomtools.materials import BaseMaterialRegistry, cached_property
from pygeomtools import write_pygeom

def add_detector_origin(name, pv, registry):
    if not hasattr(registry, "detector_origins"):
        registry.detector_origins = {}
    registry.detector_origins[name] = {
        "xloc": pv.position[0],
        "yloc": pv.position[1],
        "zloc": pv.position[2],
    }

# -----------------------------
# Units
# -----------------------------
u = pint.get_application_registry()


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
    def air(self) -> g4.Material:
        _air = g4.Material(
            name="Air",
            density=1.290e-3,
            number_of_components=2,
            temperature=300,
            temperature_unit="K",
            pressure=1013e2,
            pressure_unit="pascal",
            state="gas",
            registry=self.g4_registry,
        )
        _air.add_element_natoms(self.get_element("N"), natoms=78)
        _air.add_element_natoms(self.get_element("O"), natoms=21)
        _air.addVecProperty("RINDEX", [1.0, 10.0], [1.0, 1.0])
        return _air
    
    @cached_property
    def pmma(self) -> g4.Material:
        _pmma = g4.Material(
            name="pmma", density=1.2, number_of_components=3, registry=self.g4_registry
        )
        _pmma.add_element_natoms(self.get_element("H"), natoms=8)
        _pmma.add_element_natoms(self.get_element("C"), natoms=5)
        _pmma.add_element_natoms(self.get_element("O"), natoms=2)
        legendoptics.fibers.pyg4_fiber_cladding1_attach_rindex(_pmma, self.g4_registry)
        return _pmma

    @cached_property
    def pmma_out(self) -> g4.Material:
        _pmma_out = g4.Material(
            name="pmma_cl2", density=1.2, number_of_components=3, registry=self.g4_registry
        )
        _pmma_out.add_element_natoms(self.get_element("H"), natoms=8)
        _pmma_out.add_element_natoms(self.get_element("C"), natoms=5)
        _pmma_out.add_element_natoms(self.get_element("O"), natoms=2)
        legendoptics.fibers.pyg4_fiber_cladding2_attach_rindex(_pmma_out, self.g4_registry)
        return _pmma_out

    @cached_property
    def ps_fibers(self) -> g4.Material:
        _ps_fibers = g4.Material(
            name="ps_fibers", density=1.05, number_of_components=2, registry=self.g4_registry
        )
        _ps_fibers.add_element_natoms(self.get_element("H"), natoms=8)
        _ps_fibers.add_element_natoms(self.get_element("C"), natoms=8)
        legendoptics.fibers.pyg4_fiber_core_attach_rindex(_ps_fibers, self.g4_registry)
        legendoptics.fibers.pyg4_fiber_core_attach_absorption(_ps_fibers, self.g4_registry)
        legendoptics.fibers.pyg4_fiber_core_attach_wls(_ps_fibers, self.g4_registry)
        return _ps_fibers

    def _tpb(self, name: str, **wls_opts) -> g4.Material:
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
        legendoptics.tpb.pyg4_tpb_attach_wls(t, self.g4_registry, **wls_opts)
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
# Initialize registry and materials
# -----------------------------
add_tpb = True
use_air = True

reg = g4.Registry()
mats = OpticalMaterialRegistry(reg)
air = mats.air

# -----------------------------
# World volume
# -----------------------------
ws = g4.solid.Box("ws", 4, 4, 4, reg, "m")
wl = g4.LogicalVolume(ws, mats.air, "wl", reg)
reg.setWorld(wl)

world_phys = g4.PhysicalVolume(
    [0, 0, 0], [0, 0, 0], wl, "world_phys", None, reg
)


# -----------------------------
# LAr / cryostat
# -----------------------------
use_air=True
cryo_inner_rad = 160
cryo_inner_height = 3000
lar = g4.solid.Tubs("lar", 0, cryo_inner_rad, cryo_inner_height, 0, 2*pi, reg, lunit="mm")
lar_log = g4.LogicalVolume(
    lar,
    mats.air if use_air else mats.liquidargon,
    "lar_log",
    reg
)
lar_phys = g4.PhysicalVolume([0,0,0], [0,0,0], lar_log, "lar_phys", wl, reg)
'''
def create_fiber(
    trans: list,
    rot: list,
    idx: int,
    registry: g4.Registry,
    mats: OpticalMaterialRegistry,
    world_lv: g4.LogicalVolume,
    add_tpb: bool = True
) -> dict:
    """Create a single optical fiber with fully nested logical volumes."""

    # -----------------------------
    # Geometry parameters
    # -----------------------------
    fiber_full_width = 1.0       # mm total width
    fiber_full_length = 1000.0   # mm total length

    fiber_dim = fiber_full_width
    fiber_length = fiber_full_length

    # Layer thicknesses (full)
    fiber_thickness_tpb = 0.001
    fiber_thickness_cl1 = 0.04 * fiber_full_width
    fiber_thickness_cl2 = 0.02 * fiber_full_width

    # Convert to half-thickness
    t_tpb = fiber_thickness_tpb / 2.0
    t_cl1 = fiber_thickness_cl1 / 2.0
    t_cl2 = fiber_thickness_cl2 / 2.0

    # -----------------------------
    # Solids
    # -----------------------------
    if add_tpb:
        fiber_outer = g4.solid.Box(f"fiber_outer_{idx}", fiber_dim, fiber_dim, fiber_length, registry, "mm")

    fiber_cl2 = g4.solid.Box(f"fiber_cl2_{idx}", fiber_dim - t_tpb, fiber_dim - t_tpb, fiber_length, registry, "mm")
    fiber_cl1 = g4.solid.Box(f"fiber_cl1_{idx}", fiber_dim - t_tpb - t_cl2, fiber_dim - t_tpb - t_cl2, fiber_length, registry, "mm")
    fiber_core = g4.solid.Box(f"fiber_core_{idx}", fiber_dim - t_tpb - t_cl2 - t_cl1, fiber_dim - t_tpb - t_cl2 - t_cl1, fiber_length, registry, "mm")

    # -----------------------------
    # Logical volumes
    # -----------------------------
    if add_tpb:
        fiber_outer_log = g4.LogicalVolume(fiber_outer, mats.tpb_on_fibers, f"fiber_outer_log_{idx}", registry)

    fiber_cl2_log = g4.LogicalVolume(fiber_cl2, mats.pmma_out, f"fiber_cl2_log_{idx}", registry)
    fiber_cl1_log = g4.LogicalVolume(fiber_cl1, mats.pmma, f"fiber_cl1_log_{idx}", registry)
    fiber_core_log = g4.LogicalVolume(fiber_core, mats.ps_fibers, f"fiber_core_log_{idx}", registry)

    # -----------------------------
    # Physical hierarchy — all PVs have unique names
    # -----------------------------
    # Core inside cl1
    pv_core = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], fiber_core_log, f"fiber_core_phys_{idx}", fiber_cl1_log, registry)

    # Cl1 inside cl2
    pv_cl1 = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], fiber_cl1_log, f"fiber_cl1_phys_{idx}", fiber_cl2_log, registry)

    # Cl2 inside outer TPB if present
    if add_tpb:
        pv_cl2 = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], fiber_cl2_log, f"fiber_cl2_phys_{idx}", fiber_outer_log, registry)
        top_lv = fiber_outer_log
    else:
        top_lv = fiber_cl2_log

    # Top-level fiber in the world volume
    fiber_phys = g4.PhysicalVolume(
        trans,           # translation
        rot,             # rotation
        top_lv,
        f"fiber_phys_{idx}",
        world_lv,
        registry
    )

    # -----------------------------
    # Optical surfaces
    # -----------------------------
    # Interfaces between layers
    g4.SkinSurface(f"os_core_cl1_{idx}", fiber_core_log, mats.os_fibers, registry)
    g4.SkinSurface(f"os_cl1_cl2_{idx}", fiber_cl1_log, mats.os_fibers, registry)
    if add_tpb:
        g4.SkinSurface(f"os_cl2_tpb_{idx}", fiber_cl2_log, mats.os_fibers, registry)

    # Fiber ends (front/back)
    surf_front = g4.OpticalSurface(
        name=f"os_front_{idx}",
        model="unified",
        finish="polished",
        type="dielectric_dielectric",
        value=1.0,
        registry=registry
    )
    g4.SkinSurface(f"fiber_front_surface_{idx}", fiber_core_log, surf_front, registry)

    surf_back = g4.OpticalSurface(
        name=f"os_back_{idx}",
        model="unified",
        finish="polished",
        type="dielectric_dielectric",
        value=1.0,
        registry=registry
    )
    g4.SkinSurface(f"fiber_back_surface_{idx}", fiber_core_log, surf_back, registry)



    #g4.SkinSurface(f"os_fiber_{idx}", fiber_core_log, mats.os_fibers, registry)
    return {
        "fiber_phys": fiber_phys,
        "fiber_outer_log": fiber_outer_log if add_tpb else None,
        "fiber_cl2_log": fiber_cl2_log,
        "fiber_cl1_log": fiber_cl1_log,
        "fiber_core_log": fiber_core_log,
        "fiber_core_phys": pv_core,
        "fiber_cl1_phys": pv_cl1,
        "fiber_cl2_phys": pv_cl2 if add_tpb else None
    }
'''
def create_fiber(
    trans: list,
    rot: list,
    idx: int,
    registry: g4.Registry,
    mats: OpticalMaterialRegistry,
    world_lv: g4.LogicalVolume,
    add_tpb: bool = True
) -> dict:
    """Create a single optical fiber with fully nested logical volumes and optical surfaces."""

    # -----------------------------
    # Geometry parameters
    # -----------------------------
    fiber_full_width = 1.0       # mm total width
    fiber_full_length = 2000.0   # mm total length

    fiber_dim = fiber_full_width
    fiber_length = fiber_full_length

    # Layer thicknesses (full)
    fiber_thickness_tpb = 0.001
    fiber_thickness_cl1 = 0.04 * fiber_full_width
    fiber_thickness_cl2 = 0.02 * fiber_full_width

    # Convert to half-thickness
    t_tpb = fiber_thickness_tpb / 2.0
    t_cl1 = fiber_thickness_cl1 / 2.0
    t_cl2 = fiber_thickness_cl2 / 2.0

    # -----------------------------
    # Solids
    # -----------------------------
    if add_tpb:
        fiber_outer = g4.solid.Box(f"fiber_outer_{idx}", fiber_dim, fiber_dim, fiber_length, registry, "mm")

    fiber_cl2 = g4.solid.Box(f"fiber_cl2_{idx}", fiber_dim - t_tpb, fiber_dim - t_tpb, fiber_length, registry, "mm")
    fiber_cl1 = g4.solid.Box(f"fiber_cl1_{idx}", fiber_dim - t_tpb - t_cl2, fiber_dim - t_tpb - t_cl2, fiber_length, registry, "mm")
    fiber_core = g4.solid.Box(f"fiber_core_{idx}", fiber_dim - t_tpb - t_cl2 - t_cl1, fiber_dim - t_tpb - t_cl2 - t_cl1, fiber_length, registry, "mm")

    # -----------------------------
    # Logical volumes
    # -----------------------------
    if add_tpb:
        fiber_outer_log = g4.LogicalVolume(fiber_outer, mats.tpb_on_fibers, f"fiber_outer_log_{idx}", registry)

    fiber_cl2_log = g4.LogicalVolume(fiber_cl2, mats.pmma_out, f"fiber_cl2_log_{idx}", registry)
    fiber_cl1_log = g4.LogicalVolume(fiber_cl1, mats.pmma, f"fiber_cl1_log_{idx}", registry)
    fiber_core_log = g4.LogicalVolume(fiber_core, mats.ps_fibers, f"fiber_core_log_{idx}", registry)

    # -----------------------------
    # Physical hierarchy — all PVs have unique names
    # -----------------------------
    # Step 1: Core inside Cladding1
    pv_core = g4.PhysicalVolume([0,0,0], [0,0,0], fiber_core_log, f"fiber_core_phys_{idx}", fiber_cl1_log, registry)

    # Step 2: Cladding1 inside Cladding2
    pv_cl1 = g4.PhysicalVolume([0,0,0], [0,0,0], fiber_cl1_log, f"fiber_cl1_phys_{idx}", fiber_cl2_log, registry)

    # Step 3: Cladding2 inside TPB (optional)
    if add_tpb:
        pv_cl2 = g4.PhysicalVolume([0,0,0], [0,0,0], fiber_cl2_log, f"fiber_cl2_phys_{idx}", fiber_outer_log, registry)
        top_lv = fiber_outer_log
    else:
        top_lv = fiber_cl2_log

    # Step 4: Top-level fiber placed in world
    fiber_phys = g4.PhysicalVolume([0,0,0], [x_pos, y_pos, z_pos], top_lv, f"fiber_phys_{idx}", lar_log, registry)

    '''
    pv_core = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], fiber_core_log, f"fiber_core_phys_{idx}", fiber_cl1_log, registry)
    pv_cl1 = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], fiber_cl1_log, f"fiber_cl1_phys_{idx}", fiber_cl2_log, registry)
    
    if add_tpb:
        pv_cl2 = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], fiber_cl2_log, f"fiber_cl2_phys_{idx}", fiber_outer_log, registry)
        top_lv = fiber_outer_log
    else:
        top_lv = fiber_cl2_log

    # Top-level fiber in the world volume
    fiber_phys = g4.PhysicalVolume(rot, trans, top_lv, f"fiber_phys_{idx}", lar_log, registry)
    # Correct
    fiber_phys = g4.PhysicalVolume(rot, trans, top_lv, f"fiber_phys_{idx}", lar_log, registry)
    '''

    # -----------------------------
    # Optical surfaces at interfaces
    # -----------------------------
    g4.SkinSurface(f"os_core_cl1_{idx}", fiber_core_log, mats.os_fibers, registry)
    g4.SkinSurface(f"os_cl1_cl2_{idx}", fiber_cl1_log, mats.os_fibers, registry)
    if add_tpb:
        g4.SkinSurface(f"os_cl2_tpb_{idx}", fiber_cl2_log, mats.os_fibers, registry)


    # -----------------------------
    # Optional: add visual markers at corners to check thickness
    # -----------------------------
    # --- Add tiny corner markers for visualization ---
    marker_r = 0.05  # mm, tiny marker sphere
    marker_solid = g4.solid.Sphere(f"marker_solid_{idx}", 0, marker_r, 0, 2*pi, 0, pi, registry, "mm")
    marker_log = g4.LogicalVolume(marker_solid, mats.air, f"marker_log_{idx}", registry)
   
    #corner_offset = (fiber_dim - t_tpb - t_cl2 - t_cl1) / 2.0
    #for dx in [-corner_offset, corner_offset]:
     #   for dy in [-corner_offset, corner_offset]:
     #       for dz in [-fiber_length / 2, fiber_length / 2]:
      #          g4.PhysicalVolume([dx, dy, dz], [0, 0, 0],
       #                          marker_log,
      #                          f"fiber_core_corner_{idx}_{dx}_{dy}_{dz}",
       #                         fiber_core_log,
        #                        registry)

    
    return {
        "fiber_phys": fiber_phys,
        "fiber_outer_log": fiber_outer_log if add_tpb else None,
        "fiber_cl2_log": fiber_cl2_log,
        "fiber_cl1_log": fiber_cl1_log,
        "fiber_core_log": fiber_core_log,
        "fiber_core_phys": pv_core,
        "fiber_cl1_phys": pv_cl1,
        "fiber_cl2_phys": pv_cl2 if add_tpb else None
    }

# -----------------------------
# Optical detectors (SiPMs) — AFTER fibers are created
# -----------------------------
optdet = g4.solid.Box("optdet", 1.0, 1.0, 0.12, reg, "cm")
optdet1 = g4.LogicalVolume(optdet, g4.MaterialPredefined("G4_Si"), "optdet1", reg)
optdet2 = g4.LogicalVolume(optdet, g4.MaterialPredefined("G4_Si"), "optdet2", reg)

# Place SiPM at fiber end along z
pv_optdet1 = g4.PhysicalVolume(
    [0, 0, 0],   # fiber length / 2 in mm
    [0, 0, 1001, "mm"],     # no rotation
    optdet1,
    "optdet1",
    lar_log,
    reg
)


pv_optdet2 = g4.PhysicalVolume(
    [0, 0, 0],   # fiber length / 2 in mm
    [0, 0, -1001, "mm"],     # no rotation
    optdet2,
    "optdet2",
    lar_log,
    reg
)


# Attach optical surface to the first fiber’s core
surf_to_sipm = g4.solid.OpticalSurface(
    "surface_to_sipm",
    finish="polished",
    model="unified",
    surf_type="dielectric_metal",
    value=0,
    registry=reg,
)
surf_to_sipm.addVecProperty("EFFICIENCY", [1, 10], [1, 1])
surf_to_sipm.addVecProperty("REFLECTIVITY", [1, 10], [0, 0])



pv_optdet1.pygeom_active_detector = RemageDetectorInfo("optical", 101, {"name": "optdet1"})
pv_optdet2.pygeom_active_detector = RemageDetectorInfo("optical", 102, {"name": "optdet2"})
add_detector_origin("opdet1", pv_optdet1, reg)
add_detector_origin("opdet2", pv_optdet2, reg)


    # -----------------------------
# Fiber Array Setup — with Center Fiber at (0, 0, 0)
# -----------------------------
fibers = []
fiber_spacing = 2.0
grid_size = 3
center_offset = (grid_size - 1) / 2
'''
for i in range(grid_size):
    for j in range(grid_size):
        x_pos = (i - center_offset) * fiber_spacing
        y_pos = (j - center_offset) * fiber_spacing
        z_pos = 0

        # Create the fiber
        f = create_fiber(
            trans=[x_pos, y_pos, z_pos, "mm"],
            rot=[0, 0, 0],
            idx=i * grid_size + j,
            registry=reg,
            mats=mats,
            world_lv=lar_log,
            add_tpb=True
        )
        fibers.append(f)

        # Create border surface from fiber core to SiPM
        g4.BorderSurface(
            f"fiber{f['fiber_core_phys'].name}_to_sipm",
            f["fiber_core_phys"],
            pv_optdet1,
            surf_to_sipm,
            reg
        )
'''

# -----------------------------
# Single Fiber Setup
# -----------------------------
fibers = []

# Place one fiber at the origin
x_pos, y_pos, z_pos = 0, 0, 0

# Create the single fiber
f = create_fiber(
    trans=[x_pos, y_pos, z_pos, "mm"],
    rot=[0, 0, 0],
    idx=0,
    registry=reg,
    mats=mats,
    world_lv=lar_log,
    add_tpb=True
)
fibers.append(f)



g4.SkinSurface("surface_sipm1", optdet1, surf_to_sipm, reg)
g4.BorderSurface(
    "fiber_to_sipm_surface",
    fibers[0]["fiber_core_phys"],  # fiber core PV at end
    pv_optdet1,
    surf_to_sipm,
    reg
)

# Attach same surface to second SiPM
g4.SkinSurface("surface_sipm2", optdet2, surf_to_sipm, reg)
g4.BorderSurface(
    "fiber_to_sipm_surface_2",
    fibers[-1]["fiber_core_phys"],  # the fiber core at far end
    pv_optdet2,
    surf_to_sipm,
    reg
)


# Add skin surface on outermost fiber volume so photons from LAr/air can enter
for idx, f in enumerate(fibers):
    outer_lv = f["fiber_outer_log"] if f["fiber_outer_log"] else f["fiber_cl2_log"]
    g4.SkinSurface(f"os_outer_{idx}", outer_lv, mats.os_fibers, reg)


# -----------------------------
# Visualization
# -----------------------------
viewer = pg4.visualisation.VtkViewerColoured()

# Add world
viewer.addLogicalVolume(reg.getWorldVolume())

# Add all fiber layers
for f in fibers:
    if f["fiber_outer_log"]:
        viewer.addLogicalVolume(f["fiber_outer_log"])
    viewer.addLogicalVolume(f["fiber_cl2_log"])
    viewer.addLogicalVolume(f["fiber_cl1_log"])
    viewer.addLogicalVolume(f["fiber_core_log"])

viewer.view()


# -----------------------------
# Write GDML
# -----------------------------
write_pygeom(reg, "fiber_sim.gdml")
print("✅ GDML geometry written to fiber_sim.gdml")
