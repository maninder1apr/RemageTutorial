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
    [0, 0, 0], [5, 0, -3, "cm"], bege_l, "BEGe", lar_l, registry=reg
)
coax_pv = pg4.geant4.PhysicalVolume(
    [0, 0, 0], [-5, 0, -3, "cm"], coax_l, "Coax", lar_l, registry=reg
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

# finally create a small radioactive source
source_s = pg4.geant4.solid.Tubs("Source_s", 0, 1, 1, 0, 2 * pi, registry=reg)
source_l = pg4.geant4.LogicalVolume(source_s, "G4_BRAIN_ICRP", "Source_L", registry=reg)
pg4.geant4.PhysicalVolume(
    [0, 0, 0], [0, 5, 0, "cm"], source_l, "Source", lar_l, registry=reg
)