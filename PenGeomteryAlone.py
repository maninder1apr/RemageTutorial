import math
import pyg4ometry.geant4 as g4
import pyg4ometry.geant4.solid as solid
import pyg4ometry.visualisation as vis
from legendoptics.pen import (
    pyg4_pen_attach_rindex,
    pyg4_pen_attach_attenuation,
    pyg4_pen_attach_wls,
    pyg4_pen_attach_scintillation,
)
from pygeomtools import RemageDetectorInfo, write_pygeom

# -----------------------------
# Setup Geant4 Registry
# -----------------------------
reg = g4.Registry()

# -----------------------------
# Define elements using ElementSimple
# -----------------------------
C = g4.ElementSimple("Carbon", "C", 6, 12.01, registry=reg)
H = g4.ElementSimple("Hydrogen", "H", 1, 1.008, registry=reg)
O = g4.ElementSimple("Oxygen", "O", 8, 16.00, registry=reg)
N = g4.ElementSimple("Nitrogen", "N", 7, 14.01, registry=reg)

# -----------------------------
# Create PEN material
# -----------------------------
pen = g4.Material(
    name="PEN",
    density=1.3,
    number_of_components=3,
    registry=reg
)
pen.add_element_natoms(C, 14)
pen.add_element_natoms(H, 10)
pen.add_element_natoms(O, 4)

# Attach optical properties
pyg4_pen_attach_rindex(pen, reg)
pyg4_pen_attach_attenuation(pen, reg)
pyg4_pen_attach_wls(pen, reg)
pyg4_pen_attach_scintillation(pen, reg)

# -----------------------------
# Create PEN bowl geometry (Hemisphere)
# -----------------------------
import math
solid_bowl = solid.Sphere(
    name="pen_bowl_solid",
    pRmin=0.0,            # inner radius
    pRmax=50.0,           # outer radius in mm
    pSPhi=0.0,
    pDPhi=2*math.pi,      # full azimuth
    pSTheta=0.0,
    pDTheta=math.pi/2,    # top hemisphere
    registry=reg
)


logical_bowl = g4.LogicalVolume(
    solid=solid_bowl,
    material=pen,
    name="pen_bowl_lv",
    registry=reg,
)

# -----------------------------
# Create World volume (Air)
# -----------------------------
solid_world = solid.Box(
    name="world_solid",
    pX=100.0,
    pY=100.0,
    pZ=100.0,
    registry=reg
)

air = g4.Material(
    name="Air",
    density=0.001225,
    number_of_components=2,
    registry=reg
)
air.add_element_massfraction(N, 0.78)
air.add_element_massfraction(O, 0.22)

logical_world = g4.LogicalVolume(
    solid=solid_world,
    material=air,
    name="world_lv",
    registry=reg,
)

# -----------------------------
# Place PEN bowl inside world
# -----------------------------
pen_bowl_pv = g4.PhysicalVolume(
    [0, 0, 0],           # translation
    [0, 0, 0],           # rotation
    logical_bowl,        # logical volume
    "pen_bowl_pv",       # name
    logical_world,       # parent logical volume
    registry=reg
)

# -----------------------------
# Register PEN bowl as active detector for Remage
# -----------------------------
pen_bowl_pv.pygeom_active_detector = RemageDetectorInfo(
    "pen_bowl",
    1,  # unique detector ID
    {
        "name": "PEN_Bowl",
        "type": "plastic",
        "material": "PEN",
        "dimensions": {
            "radius_in_mm": 50,
            "hemisphere": True,
        },
        "notes": "PEN plastic scintillator hemisphere",
    }
)

# -----------------------------
# Visualize and export
# -----------------------------
reg.worldVolume = logical_world  # set world
reg.worldName = logical_world.name  # add this line




# Create viewer and add volumes
viewer = vis.VtkViewer()

# Set PEN bowl color to teal
logical_bowl.visualisationColor = [0.0, 0.5, 0.5]  # teal
viewer.renWin.SetMultiSamples(10)  # anti-aliasing for smoother edges

viewer.addLogicalVolume(reg.getWorldVolume())  # add world volume
viewer.addLogicalVolume(logical_bowl)          # add PEN bowl with color
logical_bowl.visualisation = True     

viewer.view()                                   # display geometry

write_pygeom(reg, "geometry_with_pen.gdml")    # export GDML
