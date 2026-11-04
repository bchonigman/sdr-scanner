# sdr-sweeper

Wideband spectrum sweep logger for the ADALM-PLUTO SDR (AD9363, 325-3800 MHz).
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
| `python tools/check_pluto.py` | Read-only connection check |
| `python pluto_sweep.py --start 2400e6 --stop 2500e6 --plot` | Quick test sweep (2.4 GHz Wi-Fi band) |
| `python pluto_sweep.py --plot` | Full 325-3800 MHz sweep (~10 s), saved to `data/` |
| `python pluto_sweep.py --gain 50` | Choose the manual RX gain in dB (default 40) |
| `python tools/show_sweep.py` | Plot the newest saved sweep (no Pluto needed) |
| `python tools/show_sweep.py --png --no-show` | Save a PNG next to the sweep without opening a window |

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
  reaches the sweep files at `../data/`.
- A notebook that has connected to the Pluto keeps the connection open. Use
  Kernel > Shut Down Kernel before using SDR++ or a terminal script with the radio.

To view a sweep, run this in a cell. The last line displays the table (`df.info()` lists
the columns and types):
```python
import pandas as pd
df = pd.read_parquet("data/sweep_20261023T200153Z.parquet")
df
```

Scratch notebooks: anything in `scratch/`, or named `scratch*.ipynb`, is ignored by git,
so use those for trying things out. Before committing a real notebook, set up `nbstripout`
to keep saved outputs out of git.

## Spyder (MATLAB-style IDE)

Spyder 6.1 is installed in Anaconda `base`, and runs your code in `pluto` through
`spyder-kernels`. One-time setup: Tools > Preferences > Python interpreter > Selected
interpreter > `C:\Users\bchon\anaconda3\envs\pluto\python.exe`, then open a new console
(Consoles > New console).

To browse a sweep as a table, run this and double-click `df` in the Variable Explorer:
```python
import pandas as pd
df = pd.read_parquet("data/sweep_20261023T200153Z.parquet")
```
A console that has connected to the Pluto keeps the connection open. Restart the kernel
before using SDR++ or a terminal script with the radio.

If Spyder is ever updated, its `spyder-kernels` version in `pluto` must be updated to match.

## Data

Each sweep is one Parquet file, `data/sweep_<UTC time>.parquet`, with one row per
frequency bin: `timestamp, freq_hz, psd_dbfs_hz, center_hz`. Settings (gain, sample rate,
etc.) are stored as file metadata. `data/` is kept out of git.

Query all sweeps at once with DuckDB:
```python
import duckdb
duckdb.sql("SELECT timestamp, max(psd_dbfs_hz) FROM 'data/sweep_*.parquet' "
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
