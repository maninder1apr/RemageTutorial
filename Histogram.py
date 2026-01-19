#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
from lgdo import lh5
import awkward as ak
import hist
import matplotlib.pyplot as plt

plt.rcParams["figure.figsize"] = (10, 14)

# ---------------------------
# Detector mapping
# ---------------------------
det_map = {
    "BEGe": ["det101"],
    "ICPC": ["det102"],
    "PEN_BEGe": ["det201"],
    "PEN_ICPC": ["det202"],
    "LAr": ["det401"],
}

# ---------------------------
# Helper: sum energy per event
# ---------------------------
def get_total_edep(detid):
    edep = lh5.read_as(f"stp/{detid}/edep", "test_bi207.lh5", "ak")
    return ak.sum(edep, axis=-1)

# ---------------------------
# Build spectra
# ---------------------------
spectra = {}
for name, detids in det_map.items():
    spectra[name] = ak.concatenate([get_total_edep(d) for d in detids])

# ---------------------------
# Vertical subplots
# ---------------------------
n = len(spectra)
fig, axes = plt.subplots(n, 1, sharex=True)

bins = 4000
xmin = 0
xmax = 4000

for ax, (name, data) in zip(axes, spectra.items()):
    hist.new.Reg(bins, xmin, xmax, name="E [keV]") \
        .Double() \
        .fill(data) \
        .plot(ax=ax, yerr=False)

    ax.set_title(name, fontsize=11)
    ax.set_yscale("log")
    ax.set_xlim(0, 3500)

axes[-1].set_xlabel("Energy [keV]")
fig.text(0.04, 0.5, "Counts / 1 keV", va="center", rotation="vertical")

fig.suptitle("Energy deposition spectra per detector", fontsize=14)
plt.tight_layout(rect=[0.06, 0.03, 1, 0.97])
plt.show()
