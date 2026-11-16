# sdr-sweeper

Wideband spectrum scan logger for the ADALM-PLUTO SDR (AD9363, 325-3800 MHz).
**Receive only:** the scripts never transmit.

## Every new terminal: activate the `pluto` env first

The scripts need the `pluto` conda env. Without it, Windows loads the wrong libiio
(1.0, from System32) and `import adi` fails. Pick the section that matches your terminal.
You'll know it worked when the prompt starts with `(pluto)`.

### Anaconda PowerShell Prompt (Start menu)
```powershell
conda activate pluto
cd C:\Users\bchon\projects\sdr-sweeper
```

### Plain PowerShell (e.g. the Claude app's terminal, VS Code)
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& C:\Users\bchon\anaconda3\shell\condabin\conda-hook.ps1
conda activate pluto
```
- Line 1 lets PowerShell run script files, **for this window only**. Windows blocks
  them by default, and the Anaconda shortcut does the same bypass behind the scenes.
- Line 2 loads conda into this PowerShell session.
- Line 3 activates the env.

### Command Prompt (cmd)
```bat
C:\Users\bchon\anaconda3\Scripts\activate.bat pluto
```

## Running the scripts

Close SDR++ first: only one program can control the Pluto at a time.

| Command | What it does |
|---|---|
| `python check_pluto.py` | Read-only connection check |
| `python pluto_rx_freq_scan.py --start 2400e6 --stop 2500e6 --plot` | Quick test scan (2.4 GHz Wi-Fi band) |
| `python pluto_rx_freq_scan.py --plot` | Full 325-3800 MHz scan (~10 s), saved to `data/` |
| `python pluto_rx_freq_scan.py --gain 50` | Choose the manual RX gain in dB (default 40) |
| `python pluto_rx_freq_scan.py --count 10` | 10 scans back to back (each starts when the last is saved) |
| `python pluto_rx_freq_scan.py --continuous --interval 60` | A scan every 60 s (start to start) until Ctrl+C |
| `python pluto_rx_freq_scan.py --count 3 --interval 5 --start 2400e6 --stop 2500e6` | Short logging test: 3 scans, 5 s apart |
| `python plot_scan.py` | Plot the newest saved scan (no Pluto needed) |
| `python plot_scan.py --png --no-show` | Save a PNG next to the scan without opening a window |
| `python waterfall_plot_scans.py --last 20` | Waterfall + max-hold/average spectra of the newest 20 scans |
| `python waterfall_plot_scans.py --last 20 --start 2400e6 --stop 2500e6` | Same, zoomed to 2.4-2.5 GHz |
| `python waterfall_plot_scans.py "data/scan_20261107*.parquet"` | Pick scans by filename pattern (keep the quotes) |

Without `--interval`, each scan starts as soon as the previous one is saved. Each
finished scan is saved right away, so Ctrl+C loses at most the scan in progress. A full
325-3800 MHz scan is about 2.2 MB, so `--interval 60` writes about 3 GB per day, and
back-to-back `--continuous` about 20 GB per day (a 100 MHz band is about the same: smaller
files, but ~0.3 s each). Use a narrower `--start`/`--stop` or an `--interval` for long runs.

How to read `waterfall_plot_scans.py` (`--png` saves `data/scans_<first>_<last>.png`):
- **Waterfall:** each pixel shows the *peak* of the frequency bins it covers. A
  spectrum analyzer's peak detector works the same way, and it keeps narrow signals
  visible when zoomed out. As a result, the noise floor looks a little higher here than
  in the spectra.
- **Max hold:** the highest value each bin reached in any scan. This catches
  intermittent signals.
- **Average:** averaged in linear power, then converted to dB. For steady noise this
  barely differs from averaging the dB values (~0.02 dB), because each bin is already a
  Welch average of ~127 segments. It matters for signals that come and go: a burst at
  -90 dBFS/Hz in 1 of 10 scans over a -130 floor averages to about -100 in linear power,
  but to -126 in dB, which hides it near the noise floor.
- **Thin white lines** are the masked DC bins at each LO center (visible when zoomed in).
- Mixing scans taken at different gains prints a warning, because their dBFS levels
  don't compare. Gains are compared as numbers, so 40 and 40.0 count as the same.

Add `-h` to any script for all its options. A plot window blocks the prompt until you
close it. To keep working meanwhile, open a second terminal, or use `--png --no-show`.

## JupyterLab (notebooks)

JupyterLab is installed in `pluto`, so activate the env first (see above), then start it
from the project folder:
```powershell
cd C:\Users\bchon\projects\sdr-sweeper
jupyter lab
```
It opens in your browser. The terminal stays busy running the Jupyter server, so open a
second terminal if you need a prompt. To stop it, use File > Shut Down in JupyterLab, or
press Ctrl+C in the terminal.

- `Shift+Enter` runs a cell. Plots appear directly below the cell.
- A notebook's working directory is the folder it's saved in. A notebook in `scratch/`
  reaches the scan files at `../data/`.
- A notebook that has connected to the Pluto keeps the connection open. Use
  Kernel > Shut Down Kernel before using SDR++ or a terminal script with the radio.

To view a scan, run this in a cell. The last line displays the table (`df.info()` lists
the columns and types):
```python
import pandas as pd
df = pd.read_parquet("data/scan_20261023T200153.636Z_325to3800MHz.parquet")
df
```

### From the Start-menu Jupyter Notebook app

That app runs in Anaconda `base`, and new notebooks may default to `base` too. Choose
**Kernel > Change Kernel > Python (pluto)** to run a notebook's code in `pluto`. The
name "Python 3 (ipykernel)" doesn't tell you which env it is, so check when in doubt:
```python
import sys
print(sys.executable)   # should end in envs\pluto\python.exe
```
This kernel is registered in `%APPDATA%\jupyter\kernels\pluto`, with `pluto`'s folders added
to the front of PATH so the right libiio loads (Jupyter doesn't run `conda activate`). If the
env moves, re-register it from an activated `pluto` prompt in PowerShell:
```powershell
python -m ipykernel install --user --name pluto --display-name "Python (pluto)" --env PATH 'C:\Users\bchon\anaconda3\envs\pluto;C:\Users\bchon\anaconda3\envs\pluto\Library\bin;C:\Users\bchon\anaconda3\envs\pluto\Scripts;${PATH}'
```
To remove it: `jupyter kernelspec remove pluto`.

### Scratch notebooks

Anything in `scratch/`, or named `scratch*.ipynb`, is ignored by git,
so use those for trying things out. Before committing a real notebook, set up `nbstripout`
to keep saved outputs out of git.

## Spyder (MATLAB-style IDE)

Spyder 6.1 is installed in Anaconda `base`, and runs your code in `pluto` through
`spyder-kernels`. One-time setup: Tools > Preferences > Python interpreter > Selected
interpreter > `C:\Users\bchon\anaconda3\envs\pluto\python.exe`, then open a new console
(Consoles > New console).

To browse a scan as a table, run this and double-click `df` in the Variable Explorer:
```python
import pandas as pd
df = pd.read_parquet("data/scan_20261023T200153.636Z_325to3800MHz.parquet")
```
A console that has connected to the Pluto keeps the connection open. Restart the kernel
before using SDR++ or a terminal script with the radio.

If Spyder is ever updated, its `spyder-kernels` version in `pluto` must be updated to match.

## Data

Each scan is one Parquet file, `data/scan_<UTC start, ms>_<start>to<stop>MHz.parquet`
(e.g. `scan_20261031T200843.227Z_325to3800MHz.parquet`; time first, so names sort by
time), with one row per frequency bin: `timestamp, freq_hz, psd_dbfs_hz, center_hz`.
Settings (gain, sample rate, etc.) are stored as file metadata; files from 2026-11-11 on
also store the requested band as `start_hz`/`stop_hz`. `data/` is kept out of git.

Query all scans at once with DuckDB:
```python
import duckdb
duckdb.sql("SELECT timestamp, max(psd_dbfs_hz) FROM 'data/scan_*.parquet' "
           "WHERE freq_hz BETWEEN 2.4e9 AND 2.5e9 GROUP BY timestamp").df()
```

## Git routine

```powershell
git status                 # what changed?
git diff                   # review it (q to quit the pager)
git add <files>            # stage exactly what belongs in this commit
git commit -m "Add ..."    # short, imperative summary
git log --oneline          # history
```
