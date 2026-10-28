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
