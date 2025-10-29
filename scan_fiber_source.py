#!/Users/maninder/Desktop/Programs/remage/build/python_venv/bin/python
import os
import time
import numpy as np
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

GDML_FILE = "fiber_sim.gdml"
BASE_MACRO = "fiberoptic.mac"
OUTPUT_TEMPLATE = "fiber_scan_2m{:03d}.lh5"
N_STEPS = 20
FIBER_LENGTH = 2000.0  # mm
Z_POSITIONS = np.linspace(-FIBER_LENGTH/2, FIBER_LENGTH/2, N_STEPS)
THREADS_NUM = 3  # limit threads to keep CPU free and avoid GDML conflicts

def run_simulation(zpos, i):
    macro_file = f"scan_{i:03d}.mac"
    output_file = OUTPUT_TEMPLATE.format(i)
    log_file = f"log_{i:03d}.txt"

    # --- Generate the macro file dynamically ---
    with open(BASE_MACRO) as fin, open(macro_file, "w") as fout:
        for line in fin:
            if "/gps/position" in line:
                fout.write(f"/gps/position 0 0 {zpos:.2f} mm\n")
            elif "/gps/direction" in line:
                fout.write("/gps/direction 0 0 1\n")
            elif "/remage/output/file" in line:
                fout.write(f"/remage/output/file {output_file}\n")
            else:
                fout.write(line)
        fout.write("\n# Force perpendicular emission direction\n")
        fout.write("/gps/direction 1 0 0\n")

    # --- Run the simulation ---
    cmd = [
        "remage",
        "--gdml-files", GDML_FILE,
        "--overwrite",
        "--output-file", output_file,
        "--merge-output-files",
        "--", macro_file
    ]

    print(f"▶ [Thread-{i}] Starting simulation at z = {zpos:.1f} mm ...")
    start = time.time()

    try:
        with open(log_file, "w") as lf:
            subprocess.run(cmd, check=True, stdout=lf, stderr=lf)
        duration = time.time() - start
        print(f"✅ [Thread-{i}] Finished {output_file} in {duration:.1f}s")
        return (i, True, duration)
    except subprocess.CalledProcessError as e:
        print(f"❌ [Thread-{i}] Simulation failed: {e}")
        return (i, False, None)

# -----------------------------
# Run all simulations in parallel
# -----------------------------
start_time = time.time()
results = []

with ThreadPoolExecutor(max_workers=THREADS_NUM) as executor:
    future_to_index = {executor.submit(run_simulation, z, i): i for i, z in enumerate(Z_POSITIONS)}

    for future in as_completed(future_to_index):
        res = future.result()
        results.append(res)

# -----------------------------
# Summary
# -----------------------------
total_time = time.time() - start_time
successes = [r for r in results if r[1]]
failures = [r for r in results if not r[1]]

print("\n===== SUMMARY =====")
print(f"✅ Successful simulations: {len(successes)}")
print(f"❌ Failed simulations: {len(failures)}")
print(f"⏱ Total elapsed time: {total_time:.1f} s")

if failures:
    print("Failed indices:", [r[0] for r in failures])
else:
    print("All runs completed successfully 🎉")
