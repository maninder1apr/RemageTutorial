#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

from lgdo import lh5
import numpy as np
import matplotlib.pyplot as plt

# --- Input file ---
file_path = "fiber_scan_2m001.lh5"

# --- Detector list ---
detids = ["det101"]  # Adjust if you have multiple detectors

data = {}

for detid in detids:
    # Read LH5 datasets as NumPy arrays
    wavelength = lh5.read_as(f"stp/{detid}/wavelength/flattened_data", file_path, "np")
    time = lh5.read_as(f"stp/{detid}/time/flattened_data", file_path, "np")
    evtid = lh5.read_as(f"stp/{detid}/evtid", file_path, "np")

    data[detid] = {
        "wavelength": wavelength,
        "time": time,
        "evtid": evtid,
    }

# --- Wavelength histogram ---
plt.figure(figsize=(8, 5))
for detid in detids:
    plt.hist(data[detid]["wavelength"], bins=120, alpha=0.7, label=detid)
plt.xlabel("Wavelength [nm]")
plt.ylabel("Counts")
plt.title("Detected Photon Wavelength Distribution")
plt.legend()
plt.tight_layout()
plt.show()

# --- Arrival time histogram ---
plt.figure(figsize=(8, 5))
for detid in detids:
    plt.hist(data[detid]["time"], bins=100, alpha=0.7, label=detid)
plt.xlabel("Time [ns]")
plt.ylabel("Counts")
plt.title("Photon Arrival Time Distribution")
plt.legend()
plt.tight_layout()
plt.show()

# --- Event count summary ---
for detid in detids:
    unique_events = np.unique(data[detid]["evtid"])
    print(f"✅ {detid}: {len(unique_events)} unique detection events")
