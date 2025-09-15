import legendhpges as hpges
import legendoptics.pen as pen_module  # or correct import path
import pyg4ometry as pg4
from numpy import pi

import pygeomtools


# If you don’t have pygeomtools.detector_origins, define your own:
def add_detector_origin(name, pv, registry):
    if not hasattr(registry, "detector_origins"):
        registry.detector_origins = {}
    registry.detector_origins[name] = {
        "xloc": pv.position[0],
        "yloc": pv.position[1],
        "zloc": pv.position[2],
    }


reg = pg4.geant4.Registry()

bege_meta = {
    "name": "B00000B",
    "type": "bege",
    "production": {
        "enrichment": {"val": 0.874, "unc": 0.003},
        "mass_in_g": 697.0,
    },
    "geometry": {
        "height_in_mm": 29.46,
        "radius_in_mm": 36.98,
        "groove": {"depth_in_mm": 2.0, "radius_in_mm": {"outer": 10.5, "inner": 7.5}},
        "pp_contact": {"radius_in_mm": 7.5, "depth_in_mm": 0},
        "taper": {
            "top": {"angle_in_deg": 0.0, "height_in_mm": 0.0},
            "bottom": {"angle_in_deg": 0.0, "height_in_mm": 0.0},
        },
    },
}

coax_meta = {
    "name": "C000RG1",
    "type": "coax",
    "production": {
        "enrichment": {"val": 0.855, "unc": 0.015},
    },
    "geometry": {
        "height_in_mm": 40,
        "radius_in_mm": 38.25,
        "borehole": {"radius_in_mm": 6.75, "depth_in_mm": 40},
        "groove": {"depth_in_mm": 2, "radius_in_mm": {"outer": 20, "inner": 17}},
        "pp_contact": {"radius_in_mm": 17, "depth_in_mm": 0},
        "taper": {
            "top": {"angle_in_deg": 45, "height_in_mm": 5},
            "bottom": {"angle_in_deg": 45, "height_in_mm": 2},
            "borehole": {"angle_in_deg": 0, "height_in_mm": 0},
        },
    },
}



# create logical volumes for the two HPGe detectors
bege_l = hpges.make_hpge(bege_meta, name="BEGe_L", registry=reg)
coax_l = hpges.make_hpge(coax_meta, name="Coax_L", registry=reg)

# create a world volume
world_s = pg4.geant4.solid.Orb("World_s", 20, registry=reg, lunit="cm")
world_l = pg4.geant4.LogicalVolume(world_s, "G4_Galactic", "World", registry=reg)
reg.setWorld(world_l)

# let's make a liquid argon balloon
lar_s = pg4.geant4.solid.Orb("LAr_s", 15, registry=reg, lunit="cm")
lar_l = pg4.geant4.LogicalVolume(lar_s, "G4_lAr", "LAr_l", registry=reg)
pg4.geant4.PhysicalVolume([0, 0, 0], [0, 0, 0], lar_l, "LAr", world_l, registry=reg)

# now place the two HPGe detectors in the argon
bege_pv = pg4.geant4.PhysicalVolume(
    [0, 0, 0], [8, 0, -3, "cm"], bege_l, "BEGe", lar_l, registry=reg
)
coax_pv = pg4.geant4.PhysicalVolume(
    [0, 0, 0], [-5, 0, -10, "cm"], coax_l, "Coax", lar_l, registry=reg
)

# register them as sensitive in remage
# this also saves the metadata into the files for later use
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

# Create a cylinder solid (Tubs) for plastic scintillator
# Radius = 20 mm, Full height = 30 mm → Half-height = 15 mm
plastic_s = pg4.geant4.solid.Tubs("PlasticScint_s", 0, 20, 15, 0, 2 * pi, registry=reg)

# Create logical volume with plastic scintillator material
plastic_l = pg4.geant4.LogicalVolume(
    plastic_s,
    "G4_PLASTIC_SC_VINYLTOLUENE",
    "PlasticScint_l",
    registry=reg
)


# Place physical volume inside liquid argon, close to source
# Source is at [0, 5, 0] cm, so place plastic just below it
plastic_pv = pg4.geant4.PhysicalVolume(
    [0, 0, 0],
    [0, 2, 0, "cm"],  # <--- new position (Y = 2 cm)
    plastic_l,
    "PlasticScint_pv",
    lar_l,
    registry=reg
)

# Register plastic scintillator as active detector
plastic_pv.pygeom_active_detector = pygeomtools.RemageDetectorInfo(
    "plastic_scintillator",
    3,  # Unique detector ID
    {
        "name": "PlasticScint",
        "type": "plastic",
        "material": "scintillator",
        "dimensions": {
            "height_in_mm": 30,
            "radius_in_mm": 20,
        },
        "notes": "Plastic scintillator for veto",
    }
)


# Register detector origins after all physical volumes are placed:

add_detector_origin("BEGe", bege_pv, reg)
add_detector_origin("Coax", coax_pv, reg)
add_detector_origin("PlasticScint", plastic_pv, reg)

# finally create a small radioactive source
source_s = pg4.geant4.solid.Tubs("Source_s", 0, 1, 1, 0, 2 * pi, registry=reg)
source_l = pg4.geant4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg)
pg4.geant4.PhysicalVolume(
    [0, 0, 0], [0, 5, 0, "cm"], source_l, "Source", lar_l, registry=reg
)


# start an interactive VTK viewer instance
viewer = pg4.visualisation.VtkViewerColoured(
    materialVisOptions={
        "G4_lAr": [0, 0, 1, 0.1]
    }
)


viewer.addLogicalVolume(reg.getWorldVolume())
viewer.view()
pygeomtools.write_pygeom(reg, "geometry.gdml")


print("PlasticScint origin:", plastic_pv.position)
