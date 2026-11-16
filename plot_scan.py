"""Plot a saved sweep from data/ (no Pluto needed).

Usage:
    python show_sweep.py                       # newest sweep in data/
    python show_sweep.py data/scan_XXXX.parquet
    python show_sweep.py --png                 # also save a PNG next to the file
    python show_sweep.py --png --no-show       # PNG only, no window
"""
import argparse
import sys
from pathlib import Path

import pyarrow.parquet as pq

DATA_DIR = Path(__file__).resolve().parent / "data"

ap = argparse.ArgumentParser()
ap.add_argument("file", nargs="?", help="Parquet file (default: newest in data/)")
ap.add_argument("--png", action="store_true", help="save a PNG next to the file")
ap.add_argument("--no-show", action="store_true", help="don't open a plot window")
args = ap.parse_args()

if args.file:
    path = Path(args.file)
else:
    files = sorted(DATA_DIR.glob("scan_*.parquet"))   # UTC names sort by time
    if not files:
        sys.exit(f"no sweeps in {DATA_DIR}")
    path = files[-1]

table = pq.read_table(path)
meta = {k.decode(): v.decode() for k, v in (table.schema.metadata or {}).items()
        if not k.startswith(b"pandas")}
df = table.to_pandas()
ts = df["timestamp"].iloc[0]

print(path.name, "|", f"{len(df):,} rows |", ts)
print("settings:", meta)
print(f"noise floor (median): {df.psd_dbfs_hz.median():.1f} dBFS/Hz")
print("strongest bins:")
top = df.nlargest(8, "psd_dbfs_hz")
for f, p in zip(top.freq_hz, top.psd_dbfs_hz):
    print(f"  {f/1e6:9.3f} MHz  {p:6.1f} dBFS/Hz")

if args.no_show:
    import matplotlib
    matplotlib.use("Agg")          # draw without a window
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df.freq_hz / 1e6, df.psd_dbfs_hz, lw=0.5)
ax.set_xlabel("Frequency (MHz)")
ax.set_ylabel("PSD (dBFS/Hz)")
ax.set_title(f"{path.name}  |  gain {meta.get('gain_db', '?')} dB")
ax.grid(alpha=0.3)
fig.tight_layout()

if args.png:
    png = path.with_suffix(".png")
    fig.savefig(png, dpi=150)
    print("saved", png)
if not args.no_show:
    plt.show()
