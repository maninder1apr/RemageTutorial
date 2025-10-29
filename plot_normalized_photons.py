#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python

from lgdo import lh5
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os, re

# --- SETTINGS ---
DATA_DIR = "."
N_SIMULATED = 10000
FIBER_LENGTH = 2000.0  # mm
DECIMALS = 5
MIN_ERROR = 0.005
DET101 = "det101"
DET102 = "det102"

# --- MODEL FUNCTIONS ---
def double_exponential(d, A1, lambda1, A2, lambda2):
    """Double exponential decay for det101"""
    return A1 * np.exp(-d / lambda1) + A2 * np.exp(-d / lambda2)

def mirrored_double_exponential(d, A1, A2, lambda1, lambda2):
    """Mirrored double exponential rise for det102 using same lambda1, lambda2"""
    return A1 * np.exp(-(FIBER_LENGTH - d) / lambda1) + A2 * np.exp(-(FIBER_LENGTH - d) / lambda2)

# --- FIND FILES ---
pattern = re.compile(r"fiber_scan_2m(\d+)\.lh5$")
files = sorted(
    [(int(pattern.search(f).group(1)), os.path.join(DATA_DIR, f))
     for f in os.listdir(DATA_DIR) if pattern.match(f)],
    key=lambda x: x[0]
)
if not files:
    raise FileNotFoundError("No 'fiber_scan_2m*.lh5' files found!")

# --- Skip last file if needed ---
files = files[:-1]
N = len(files)

# --- SOURCE POSITIONS ---
Z_POSITIONS = np.linspace(-FIBER_LENGTH/2, FIBER_LENGTH/2, N)
DISTANCES = FIBER_LENGTH/2 - Z_POSITIONS  # 0 mm = det101 side, 2000 mm = det102 side

# --- READ DATA ---
def read_counts(det):
    counts, errors = [], []
    for idx, path in files:
        try:
            times = lh5.read_as(f"stp/{det}/time/flattened_data", path, "np")
            n = len(times)
            norm = n / N_SIMULATED
            # realistic Poisson error: only floor if n=0
            err = np.sqrt(n) / N_SIMULATED if n > 0 else MIN_ERROR
        except Exception as e:
            print(f"⚠️ Could not read {path} for {det}: {e}")
            norm, err = 0.0, MIN_ERROR
        counts.append(norm)
        errors.append(err)
        print(f"{det:7s} | {os.path.basename(path):20s} → {norm:.{DECIMALS}f} ± {err:.{DECIMALS}f}")
    return np.array(counts), np.array(errors)

counts101, errors101 = read_counts(DET101)
counts102, errors102 = read_counts(DET102)

# --- DET101: remove extreme 2000 mm point ---
mask_det101 = DISTANCES < (FIBER_LENGTH - 1e-6)
dist101 = DISTANCES[mask_det101]
counts101 = counts101[mask_det101]
errors101 = errors101[mask_det101]

# --- DET102: remove first and last points ---
dist102 = DISTANCES[1:-1]
counts102 = counts102[1:-1]
errors102 = errors102[1:-1]

# --- FIT DET101 (double exponential decay) ---
p0_101 = [0.5, FIBER_LENGTH/5, 0.5, FIBER_LENGTH/2]
popt101, pcov101 = curve_fit(
    double_exponential, dist101, counts101,
    sigma=errors101, absolute_sigma=True,
    p0=p0_101, bounds=([0,0,0,0],[np.inf]*4)
)

A1_101, lambda1_101, A2_101, lambda2_101 = popt101

# --- FIT DET102 (mirrored, shared lambdas from det101) ---
def mirrored_fixed_lambda(d, A1, A2):
    return mirrored_double_exponential(d, A1, A2, lambda1_101, lambda2_101)

p0_102 = [0.5, 0.5]
popt102, pcov102 = curve_fit(
    mirrored_fixed_lambda, dist102, counts102,
    sigma=errors102, absolute_sigma=True,
    p0=p0_102, bounds=([0,0],[np.inf, np.inf])
)
A1_102, A2_102 = popt102

# --- COMPUTE FITS ---
fit101 = double_exponential(dist101, *popt101)
fit102 = mirrored_fixed_lambda(dist102, *popt102)

# --- TOTAL EFFICIENCY (sum of fits, no fit) ---
dist_common = np.linspace(0, FIBER_LENGTH, 300)
fit101_interp = double_exponential(dist_common, *popt101)
fit102_interp = mirrored_fixed_lambda(dist_common, *popt102)
total_eff = fit101_interp + fit102_interp

# --- PLOT ---
fig, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=True)

# Detector 101
axes[0].errorbar(dist101, counts101, yerr=errors101, fmt='o', color='C0', capsize=3, label='Data')
axes[0].plot(dist101, fit101, 'r-', label='Double Exp Fit')
axes[0].set_ylabel("Normalized photons")
axes[0].set_title("Detector 101 (Exponential Decay)")
axes[0].grid(True, ls="--", alpha=0.6)
axes[0].legend()

# Detector 102
axes[1].errorbar(dist102, counts102, yerr=errors102, fmt='o', color='C1', capsize=3, label='Data')
axes[1].plot(dist102, fit102, 'r-', label='Mirrored Fit (Shared λ)')
axes[1].set_ylabel("Normalized photons")
axes[1].set_title("Detector 102 (Exponential Rise / Mirrored)")
axes[1].grid(True, ls="--", alpha=0.6)
axes[1].legend()

# Total Efficiency (sum)
axes[2].plot(dist_common, fit101_interp, 'C0--', label='det101 fit')
axes[2].plot(dist_common, fit102_interp, 'C1--', label='det102 fit')
axes[2].plot(dist_common, total_eff, 'k-', label='Total = det101 + det102')
axes[2].set_xlabel("Distance from det101 [mm]")
axes[2].set_ylabel("Normalized photons")
axes[2].set_title("Total Efficiency (Sum of Fits, No Fit)")
axes[2].grid(True, ls="--", alpha=0.6)
axes[2].legend()

plt.tight_layout()
plt.savefig("fiber_decay_mirrored_sum_fixed.png", dpi=150)
plt.show()

print("\n✅ Plot saved as fiber_decay_mirrored_sum_fixed.png")

# --- PRINT FIT RESULTS ---
print("\nDetector 101 (Double Exp Fit):")
print(f"  A1 = {A1_101:.5f} ± {np.sqrt(pcov101[0,0]):.5f}")
print(f"  λ1 = {lambda1_101:.2f} ± {np.sqrt(pcov101[1,1]):.2f} mm")
print(f"  A2 = {A2_101:.5f} ± {np.sqrt(pcov101[2,2]):.5f}")
print(f"  λ2 = {lambda2_101:.2f} ± {np.sqrt(pcov101[3,3]):.2f} mm")

print("\nDetector 102 (Mirrored Fit, Shared λ):")
print(f"  A1 = {A1_102:.5f} ± {np.sqrt(pcov102[0,0]):.5f}")
print(f"  A2 = {A2_102:.5f} ± {np.sqrt(pcov102[1,1]):.5f}")
