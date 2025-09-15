#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
from lgdo import lh5
import awkward as ak
import hist
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # for 3D plotting

plt.rcParams["figure.figsize"] = (10, 3)

# ---------------------------
# Detector mapping
# ---------------------------
det_map = {
    "BEGe": ["det001"],
    "Coax": ["det002"],
    "PEN_BEGe": ["det003"],
    "PEN_Coax": ["det004"],
    "PMT_BEGe": ["det005"],
    "PMT_Coax": ["det006"],
}

# ---------------------------
# Function to plot energy deposition per event
# ---------------------------
def plot_edep(detid_label):
    detids = det_map[detid_label]

    # Sum energy per event for each detector
    total_edep_arrays = []
    for detid in detids:
        arr = lh5.read_as(f"stp/{detid}/edep", "output.lh5", "ak")
        # Sum over particles per event
        total_edep_arrays.append(ak.sum(arr, axis=-1))

    # Concatenate events across detectors
    total_edep = ak.concatenate(total_edep_arrays)

    # Fill histogram
    hist.new.Reg(2200, 0, 2200, name="energy [keV]").Double().fill(total_edep).plot(
        yerr=False, label=detid_label
    )

# ---------------------------
# Energy spectra
# ---------------------------
plt.figure()
for label in ["BEGe", "Coax", "PEN_BEGe", "PEN_Coax"]:
    plot_edep(label)

plt.ylabel("counts / 1 keV")
plt.yscale("log")
plt.legend()
plt.show()

# ---------------------------
# Combined detector mapping for scatter plots
# ---------------------------
scatter_groups = {
    "BEGe": ["det001"],                  # single detector
    "Coax": ["det002"],                  # single detector
    "PEN_BEGe + PMT_BEGe": ["det003", "det004"],  # combine detectors
    "PEN_Coax + PMT_Coax": ["det009"],  # combine detectors
}

# Create 2x2 subplots
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

colors = ["red", "blue"]  # colors for multiple detectors in the same group

for ax, (group_label, detids) in zip(axes.flat, scatter_groups.items()):
    for i, detid in enumerate(detids):
        arr = lh5.read_as(f"stp/{detid}", "output.lh5", "ak")[:20_000]
        ax.scatter(
            ak.flatten(arr.xloc),
            ak.flatten(arr.zloc),
            s=1,
            color=colors[i % len(colors)],
            label=detid
        )

    ax.set_title(group_label)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("z [m]")
    ax.axis("equal")
    ax.legend()

plt.tight_layout()
plt.show()

import lgdo.lh5 as lh5
import awkward as ak
import matplotlib.pyplot as plt

# Detector IDs for optical PMTs
detids = ["det007", "det008"]

data = {}
for detid in detids:
    # Read wavelength and time arrays
    wavelength = lh5.read_as(f"stp/{detid}/wavelength", "output.lh5", "ak")
    time = lh5.read_as(f"stp/{detid}/time", "output.lh5", "ak")
    
    # Flatten arrays for plotting
    wavelength_flat = ak.flatten(wavelength)
    time_flat = ak.flatten(time)
    
    data[detid] = {"wavelength": wavelength_flat, "time": time_flat}

# --- Histogram of wavelengths ---
plt.figure(figsize=(8,5))
plt.hist(data["det007"]["wavelength"], bins=50, alpha=0.7, label="det007")
plt.hist(data["det008"]["wavelength"], bins=50, alpha=0.7, label="det008")
plt.xlabel("Wavelength [nm]")
plt.ylabel("Counts")
plt.title("Photon Wavelength Distribution")
plt.legend()
plt.show()

# --- Histogram of arrival times ---
plt.figure(figsize=(8,5))
plt.hist(data["det007"]["time"], bins=100, alpha=0.7, label="det007")
plt.hist(data["det008"]["time"], bins=100, alpha=0.7, label="det008")
plt.xlabel("Time [ns]")
plt.ylabel("Counts")
plt.title("Photon Arrival Time Distribution")
plt.legend()
plt.show()

