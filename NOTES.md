# sdr-sweeper: status notes

## Done (2026-10-17)
- conda env `pluto` (conda-forge): Python 3.12, numpy, scipy, pandas, pyarrow,
  matplotlib, duckdb, jupyterlab, libiio 0.25, pylibiio 0.25, pyadi-iio 0.0.21.
- Pluto verified read-only over `usb:` and `ip:192.168.2.1`
  (AD9363A, fw v0.38). Check anytime: `python tools/check_pluto.py`.

## Gotchas
- Always run from an **activated** env (Anaconda Prompt -> `conda activate pluto`).
  Without activation, Windows loads the system libiio 1.0 from System32 and
  `import adi` fails.
- Avoid `conda run` for Pluto scripts; it hung during testing.

## Done (2026-10-18)
- git repo on branch `main`, with a `.gitignore` covering `data/`, `__pycache__/`,
  `.ipynb_checkpoints/` and `.claude/settings.local.json`.
  Global config: `core.autocrlf=true` and `init.defaultBranch=main`.

## Commit routine
1. `git status`: what changed?
2. `git diff`: review the actual changes.
3. `git add <files>`: stage only what belongs in this commit.
4. `git commit -m "Short imperative summary"`: one logical change per commit.
5. `git log --oneline`: see history.
Commit whenever something small works (it's a save point you can return to).

## Next
- Later: private GitHub remote for backup. Before notebooks: consider `nbstripout`.
- Part A: `pluto_sweep.py` single sweep -> Parquet in `data/`, quick plot.
  325-3800 MHz, 15 MHz steps, 20 MS/s, manual `--gain`, DC removal, Welch PSD.
  RX only: block tx(), TX atten -89.75 dB, TX LO powered down.
- Part B: continuous logging (`--interval`), `plot_sweeps.py`
  (heatmap + max-hold/average), Jupyter notebook for analysis.
- Also write `environment.yml` and `README.md`.

## Optional cleanup
- Delete unused venv `C:\Users\bchon\venvs\pluto`.
- Standalone Python 3.12 (python.org, per-user) is kept on purpose; use `py -3.12`.
