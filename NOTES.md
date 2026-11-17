# sdr-sweeper: status notes

## Current status (2026-11-16)
Part B is complete: single scan, B1 (continuous logging), B2 (`waterfall_plot_scans.py`)
and B3 (`notebooks/scan_analysis.ipynb`, with `nbstripout` guarding git). The scripts are
`pluto_rx_freq_scan.py`, `waterfall_plot_scans.py`, `plot_scan.py` and `check_pluto.py`,
all at the top level. Open question from B3: why did the band pattern change on 11-16?
(see Done). Next options: C1 (`environment.yml`, which should now include nbstripout),
D (measurement experiments), or the notebook's exercises.

## Done
- **2026-10-17:** conda env `pluto` (conda-forge): Python 3.12, numpy, scipy, pandas,
  pyarrow, matplotlib, duckdb, jupyterlab, libiio 0.25, pylibiio 0.25, pyadi-iio 0.0.21.
  Pluto verified read-only over `usb:` and `ip:192.168.2.1` (AD9363A, fw v0.38).
  Check anytime: `python check_pluto.py`.
- **2026-10-18:** git repo on `main`. `.gitignore` covers `data/`, `__pycache__/`,
  `.ipynb_checkpoints/` and `.claude/settings.local.json`. Global config:
  `user.name`/`user.email`, `init.defaultBranch=main`, `core.autocrlf=true`.
- **2026-10-23:** `pluto_sweep.py` works on hardware. A full 325-3800 MHz sweep at 40 dB
  gain takes 9.1 s (232 steps, 177,920 bins, noise floor about -131 dBFS/Hz).
  Cellular downlink bands are clearly visible (600/700/850 MHz, PCS ~1.95 GHz,
  AWS ~2.1 GHz, 2.5-2.7 GHz). `tools/show_sweep.py` replots a saved sweep
  (`--png --no-show` writes a PNG only).
- **2026-10-27:** `README.md` covers the per-terminal activation commands, script usage,
  the data layout and the git routine.
- **2026-10-31:** masked DC bins are stored as Parquet NULL instead of NaN, because NaN
  sorts above every number in SQL `max()`. Existing files were converted.
- **2026-11-04:** `spyder-kernels` 3.1.7 installed in `pluto` for Spyder 6.1.0 (in `base`).
  This downgraded `ipykernel` 7.4 -> 6.31, which Spyder's kernel requires. Imports and a
  Jupyter kernel test pass. The user still has to point Spyder at `pluto` (see README) and
  test `import adi` from inside Spyder.
- **2026-11-04:** registered Jupyter kernel "Python (pluto)" in the user's kernels folder,
  with PATH set so libiio 0.25 loads without activation. Tested from `base` Jupyter code
  (kernel starts, `import adi` OK, env's `libiio.dll` loaded), no radio connection yet.
  The Start-menu Jupyter server stays in `base`; `Scratch.ipynb` was running in `base`.
- **2026-11-07 (B1):** `pluto_sweep.py --interval N [--count M]`. Hardware-tested:
  3 sweeps of 2.4-2.5 GHz at 5 s, and 5 full sweeps at 10 s stopped with Ctrl+C. One file
  per sweep, no `.tmp` left over (the `.tmp` file exists only for the milliseconds of the
  write, so Explorer never shows it).
  Fixed-rate schedule (start to start), using a monotonic clock. A slow sweep starts the
  next one right away, with no catch-up. TX safety is checked again before each sweep.
  Files are written as `.tmp` and then renamed, and Ctrl+C discards only the unfinished
  sweep. `--interval` must be >= 1 because filenames have 1 s resolution (a 100 MHz band
  takes ~0.3 s, so sweeps could otherwise overwrite each other). `--plot` is single-sweep
  only. The first Parquet write in a process takes ~1.2 s of one-time setup.
- **2026-11-07 (B2):** `tools/plot_sweeps.py`. A waterfall (one row per sweep, labeled
  by UTC time) over max-hold and average spectra. DuckDB does the grouping on the Parquet
  files. The waterfall peak-detects bins into `--bins` (1500) columns. The spectra are full
  resolution, and the average is taken in linear power. It warns on mixed gains and
  expands `*` patterns itself (PowerShell doesn't). Tested on the B1 sweeps; PNGs are in
  `data/sweeps_*.png`. Observed: in the 2.4 GHz zoom, Wi-Fi shows up as boxes cut off at
  the 15 MHz step edges, because each step is a separate ~3 ms capture taken at a
  different moment.
- **2026-11-11 (rename batch 1):** `pluto_sweep.py` -> `pluto_rx_freq_scan.py` (`git mv`).
  "Sweep" -> "scan" throughout (`sweep()` -> `scan()`, `log_loop()` -> `scan_loop()`).
  Behavior changed: it always runs `scan_loop`; `--count` (default 1) sets how many scans,
  `--continuous` (new, excludes `--count`) runs until Ctrl+C. Without `--interval` scans
  run back to back; `--interval` (now >= 0) keeps the fixed start-to-start schedule. `--plot`
  works with any count and shows only the last scan saved (also after Ctrl+C with
  `--continuous`). New filename: `scan_<UTC, ms>_<start>to<stop>MHz.parquet` (time
  first so names sort by time; ms instead of seconds so back-to-back narrow-band scans
  can't collide; this replaces the old `--interval >= 1` rule). New metadata keys
  `start_hz`/`stop_hz` (new files only). Columns and older metadata keys unchanged.
  The 36 old `data/sweep_*.parquet` files were renamed to the new scheme (time from the
  `timestamp` column, band from `freq_hz`; contents unchanged). Old PNGs kept their names.
  `plot_sweeps.py`/`show_sweep.py` got only the glob and filename-time parsing changes
  they need. Found: `gain_db` is stored as `'40'` (default) or `'40.0'` (`--gain 40`), so
  plot_sweeps' text comparison of gains can warn falsely. This was already in the code;
  it's for the plot_sweeps batch.
- **2026-11-15 (rename batch 2):** all `tools/` scripts moved to the top level (`git mv`;
  `DATA_DIR` is now `parent / "data"`), so they sit next to the scan script and a notebook
  in the repo root can import them. `tools/plot_sweeps.py` -> `waterfall_plot_scans.py`;
  "sweep" -> "scan" in it (`sweep_time()` -> `scan_time()`, messages, labels). `--png`
  now writes `data/scans_<first>_<last>.png` (old `sweeps_*.png` kept their names).
  Fixed: gains are compared as numbers (`float(gain_db)`), so `'40'` and `'40.0'` no longer
  warn. Corrected the "averaging dB reads ~2.5 dB low" claim: that holds for raw FFT bins,
  but our bins are Welch averages of ~127 segments, so for steady noise it's ~0.02 dB. The
  linear average matters for bursty signals (1-in-10 burst: -100 linear vs -126 in dB).
- **2026-11-15 (rename batch 3):** `show_sweep.py` -> `plot_scan.py` ("sweep" -> "scan" in
  its wording). Restructured into functions + `main()`, so importing it runs nothing:
  `newest_scan()`, `load_scan(path)` -> `(df, meta)`, `gain_label(meta)`,
  `print_summary(...)`, `plot_spectrum(df, title)` -> figure (for B3 notebooks).
  `-h` now shows the usage examples. The title shows gain as a number (`40`, not
  `'40'`/`'40.0'`). Idea for later: "strongest bins" lists neighbors of the same signal;
  `scipy.signal.find_peaks` with a minimum spacing would list distinct signals.
- **2026-11-16 (rename batch 4):** `check_pluto.py` kept its name and stays a flat script
  (the user's choice: it's a command-line check, not a library). It now uses argparse, so
  `-h` prints the usage examples instead of being tried as a URI. Parsing happens before
  `import adi`, so `-h` works even without the env activated. The user added comments
  explaining the late imports and the libiio DLL path line.
- **2026-11-16 (hardware test after renames):**
  `pluto_rx_freq_scan.py --count 3 --start 2400e6 --stop 2500e6` gave 3 scans of 0.3 s
  each, one file per scan. Scan 1 to scan 2 took 1.7 s, because of the one-time ~1.2 s
  setup cost of the first Parquet write. Scan 2 to scan 3 took 0.33 s.
  **Settings persist in the radio, not the script.** `check_pluto.py` read the same
  values before and after the run:
  - **Before (power-up defaults):** 30.72 MS/s, slow_attack AGC at 71 dB, LO 2400 MHz,
    **TX atten -10 dB, TX LO powerdown 0**.
  - **After the script exited:** the script's settings were still there: 20 MS/s,
    manual 40 dB, LO at the last step (2497.5), TX -89.75 dB, TX LO powered down.

  So the AD9363 driver holds its settings until a power cycle or replug. A replug
  restores the TX defaults. The scanner forces TX safe at startup anyway.
- **2026-11-16 (nbstripout):** `nbstripout` 0.9.1 installed in `pluto` from conda-forge
  (one 24 KB noarch package, nothing else changed). `nbstripout --install --attributes
  .gitattributes` registered it. The filter command in `.git/config` uses pluto's
  python.exe by full path, so it works without activation. `required = true` makes
  `git add` fail rather than commit outputs if the filter breaks. Tested: the stored blob
  had `outputs: []` and `execution_count: null`.
- **2026-11-16 (B3):** `notebooks/scan_analysis.ipynb`, written by a generator script and
  executed end to end in the "Python (pluto)" kernel with nbconvert (the executed copy
  went to scratch, so the committed file has no outputs). Sections: setup (finds
  `data/` from `notebooks/` or the project root), a DuckDB view over `scan_*.parquet`,
  an inventory (one row per scan, gain joined from `parquet_kv_metadata`), the noise
  floor per scan, band occupancy (bins > per-scan median + 10 dB, bands registered as a
  DataFrame, range join), reuse of `plot_scan.py` functions, and exercises.
  Results on 49 scans (42 full, all at 40 dB):
  - The noise floor is very stable: -130.77 to -130.90 dBFS/Hz, std 0.04 dB.
  - **On 11-16 the pattern changes:** 700 MHz downlink jumps to ~80% occupancy, AWS rises,
    LTE 600 drops, and the noise floor is ~0.08 dB lower. Possibly a different
    location/antenna position, or carrier changes. The user hasn't explained it yet.
  - ADS-B 1090 and C-band read 0%. ADS-B replies last ~120 us, so a ~3 ms capture rarely
    catches one above the threshold.
- `Scratch.ipynb` is the user's play-around notebook. `.gitignore` covers `scratch/` and
  `[Ss]cratch*.ipynb`.

## Gotchas
- Always run from an **activated** env. Without activation, Windows loads the system
  libiio 1.0 from System32 and `import adi` fails (in Claude's shell it exits silently
  with code 127). Matplotlib's PNG saving does the same without activation. In Claude's
  bash, put `envs/pluto`, `envs/pluto/Library/bin` and `envs/pluto/Scripts` at the front of PATH.
- In plain PowerShell (e.g. the Claude app terminal), the default execution policy
  blocks `conda-hook.ps1`. The user chose a per-window bypass
  (`Set-ExecutionPolicy -Scope Process Bypass`) over a permanent change; see README.
  Possible later: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` +
  `conda init powershell`. The PowerShell profile lives in OneDrive, so that change
  would sync to other PCs.
- Avoid `conda run` for Pluto scripts; it hung during testing.
- PowerShell has no `cmd &` for background jobs. Use a second terminal,
  `Start-Process`, or `plot_scan.py --png --no-show`.
- A plot window blocks the prompt until it's closed.
- Printing a DuckDB result directly (`print(con.sql(...))`) in a Windows terminal can fail
  with `UnicodeEncodeError` (cp1252 can't draw the box characters). Use `.df()`, or set
  `PYTHONIOENCODING=utf-8`. Notebooks aren't affected.

## Commit routine
1. `git status`: what changed?
2. `git diff`: review the actual changes (`q` quits the pager).
3. `git add <files>`: stage only what belongs in this commit.
4. `git commit -m "Short imperative summary"`: one logical change per commit.
5. `git log --oneline`: see history.
Commit whenever something small works (it's a save point you can return to).
The user wants to be walked through git steps (learning goal).

## Options for next steps

### B. Finish the original plan (recommended next)
- **B1. Continuous logging:** `pluto_sweep.py --interval N` repeats sweeps until
  Ctrl+C, one Parquet file per sweep.
- **B2. `plot_sweeps.py`:** frequency-vs-time heatmap (waterfall) plus max-hold and
  average spectra across many sweeps.
- **B3. Jupyter notebook** for analysis with DuckDB. Done: `notebooks/scan_analysis.ipynb`.

### C. Cleanup
- **C1. `environment.yml`** so the `pluto` env can be rebuilt with one command.
- **C2. Private GitHub remote** for backup (teaches push/pull). The `gh` CLI isn't
  installed.
- **C3. Optional:** delete the unused venv `C:\Users\bchon\venvs\pluto`. The standalone
  Python 3.12 (python.org, per-user) is kept on purpose; use `py -3.12`.

### D. Understand the measurement (DSP learning)
- **D1. Spike comb above ~2.7 GHz:** evenly spaced small spikes, possibly one per
  15 MHz step. Change one thing at a time (step size, gain, antenna vs. a 50-ohm
  terminator) to tell instrument artifacts apart from real signals.
- **D2. Gain experiments:** sweep the same band at 30/40/50/60 dB to see where the noise
  floor stops improving and overload/intermod begins. SDR++ suggested ~50 dB.
- **D3. Fill the DC gaps:** use overlapping steps so each LO center falls inside a
  neighboring step's valid band.

### E. Toward ADC characterization (work goal)
- **E1. Single-tone tests:** SNR, SFDR, THD and ENOB from an FFT of a clean tone
  (coherent sampling, windowing). Needs a signal source, e.g. a borrowed signal
  generator.
- **E2. Calibration** from dBFS to dBm using a known input power.

### F. Transmit (later, only when the user says so)
Receive-only is for the learning phase, so nothing interferes with others' Wi-Fi or
cellular service. The user plans to try TX once the tools and RX side feel solid. A safe
first step would be a cabled loopback: TX -> SMA attenuators -> RX, at the lowest output,
with no antenna, so nothing radiates. E2 could use the result as a rough known source.
Transmitting over the air needs care with frequency, power and licensing rules.

## Part A spec (reference)
`pluto_sweep.py` (now `pluto_rx_freq_scan.py`): 325-3800 MHz, 15 MHz steps (center +/- 7.5 MHz kept), 20 MS/s,
18 MHz RF BW, 65,536 samples per step, Welch PSD (Hann, 1024 points, 50% overlap),
mean removal + NaN mask within +/-40 kHz of each LO, clipping warning at 95% of full
scale, manual `--gain` (default 40). Output: `data/sweep_<UTC>.parquet` (now `scan_<UTC ms>_<band>MHz.parquet`) with columns
`timestamp, freq_hz, psd_dbfs_hz, center_hz` plus settings as metadata.
RX only: `tx()` blocked, TX atten -89.75 dB, TX LO powered down, verified at startup.
