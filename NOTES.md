# sdr-sweeper: status notes

## Current status (2026-10-31)
Part A (single sweep) is done, working on hardware, and committed. Nothing has been
started on Part B yet. The next step is to choose from the options below
(recommended: B1 + B2).

## Done
- **2026-10-17:** conda env `pluto` (conda-forge): Python 3.12, numpy, scipy, pandas,
  pyarrow, matplotlib, duckdb, jupyterlab, libiio 0.25, pylibiio 0.25, pyadi-iio 0.0.21.
  Pluto verified read-only over `usb:` and `ip:192.168.2.1` (AD9363A, fw v0.38).
  Check anytime: `python tools/check_pluto.py`.
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
- Commits so far: initial commit, the sweep script + viewer, and the README.

## Gotchas
- Always run from an **activated** env. Without activation, Windows loads the system
  libiio 1.0 from System32 and `import adi` fails (in Claude's shell it exits silently
  with code 127).
- In plain PowerShell (e.g. the Claude app terminal), the default execution policy
  blocks `conda-hook.ps1`. The user chose a per-window bypass
  (`Set-ExecutionPolicy -Scope Process Bypass`) over a permanent change; see README.
  Possible later: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` +
  `conda init powershell`. The PowerShell profile lives in OneDrive, so that change
  would sync to other PCs.
- Avoid `conda run` for Pluto scripts; it hung during testing.
- PowerShell has no `cmd &` for background jobs. Use a second terminal,
  `Start-Process`, or `show_sweep.py --png --no-show`.
- A plot window blocks the prompt until it's closed.

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
- **B3. Jupyter notebook** for analysis with DuckDB. Set up `nbstripout` **before** the
  first notebook is committed.

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

## Part A spec (reference)
`pluto_sweep.py`: 325-3800 MHz, 15 MHz steps (center +/- 7.5 MHz kept), 20 MS/s,
18 MHz RF BW, 65,536 samples per step, Welch PSD (Hann, 1024 points, 50% overlap),
mean removal + NaN mask within +/-40 kHz of each LO, clipping warning at 95% of full
scale, manual `--gain` (default 40). Output: `data/sweep_<UTC>.parquet` with columns
`timestamp, freq_hz, psd_dbfs_hz, center_hz` plus settings as metadata.
RX only: `tx()` blocked, TX atten -89.75 dB, TX LO powered down, verified at startup.
