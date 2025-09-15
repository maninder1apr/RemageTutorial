import pyg4ometry as pg4

# Create the geometry registry
reg = pg4.geant4.Registry()

# Create element instance by __new__ and manual setting (bypass __init__)
ar = pg4.geant4.Element.__new__(pg4.geant4.Element)
ar.name = "Ar"
ar.symbol = "Ar"
ar.atomicNumber = 18
ar.atomicMass = 39.948
ar.number_of_components = None

# Add element to registry dictionary
reg.defineDict[ar.name] = ar

# Create material instance by __new__ and manual setting
lAr = pg4.geant4.Material.__new__(pg4.geant4.Material)
lAr.name = "G4_lAr"
lAr.density = 1.390  # g/cm3
lAr.densityUnit = "g/cm3"
lAr.components = []
lAr.registry = reg

# Add element with fraction 1.0
lAr.addElement(ar, 1.0)

# Register material in registry dictionary
reg.defineDict[lAr.name] = lAr

# Print materials in registry
print("Materials in registry:")
for mat in reg.materialList:
    print(f"- {mat.name} ({mat.density} {mat.densityUnit})")
