"""Plot one saved scan from data/ and print a short summary (no Pluto needed).

Usage:
    python plot_scan.py                       # newest scan in data/
    python plot_scan.py data/scan_XXXX.parquet
    python plot_scan.py --png                 # also save a PNG next to the file
    python plot_scan.py --png --no-show       # PNG only, no window

From a notebook or Spyder console (importing runs nothing by itself):
    from plot_scan import newest_scan, load_scan, plot_spectrum
    df, meta = load_scan(newest_scan())
"""
import argparse
import sys
from pathlib import Path

import pyarrow.parquet as pq

DATA_DIR = Path(__file__).resolve().parent / "data"


def newest_scan(data_dir=DATA_DIR):
    """Path of the newest scan_*.parquet in data_dir (names sort by time)."""
    files = sorted(Path(data_dir).glob("scan_*.parquet"))
    if not files:
        raise FileNotFoundError(f"no scans in {data_dir}")
    return files[-1]


def load_scan(path):
    """Read one scan file. Returns (df, meta): a pandas DataFrame with one row per
    frequency bin, and the settings metadata as a dict of strings."""
    table = pq.read_table(path)
    meta = {k.decode(): v.decode() for k, v in (table.schema.metadata or {}).items()
            if not k.startswith(b"pandas")}    # skip pandas' own metadata, if any
    return table.to_pandas(), meta


def gain_label(meta):
    """Gain as a number for display: '40' and '40.0' both print as 40."""
    g = meta.get("gain_db")
    return "?" if g is None else f"{float(g):g}"


def print_summary(path, df, meta):
    print(Path(path).name, "|", f"{len(df):,} rows |", df["timestamp"].iloc[0])
    print("settings:", meta)
    # Median: most bins are noise, so a few strong signals don't move it.
    print(f"noise floor (median): {df.psd_dbfs_hz.median():.1f} dBFS/Hz")
    print("strongest bins:")
    top = df.nlargest(8, "psd_dbfs_hz")
    for f, p in zip(top.freq_hz, top.psd_dbfs_hz):
        print(f"  {f/1e6:9.3f} MHz  {p:6.1f} dBFS/Hz")


def plot_spectrum(df, title=""):
    """Plot PSD vs frequency for one scan; returns the matplotlib figure."""
    import matplotlib.pyplot as plt   # imported here so main() can pick the backend first
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.freq_hz / 1e6, df.psd_dbfs_hz, lw=0.5)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("PSD (dBFS/Hz)")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="Parquet file (default: newest in data/)")
    ap.add_argument("--png", action="store_true", help="save a PNG next to the file")
    ap.add_argument("--no-show", action="store_true", help="don't open a plot window")
    args = ap.parse_args()

    try:
        path = Path(args.file) if args.file else newest_scan()
    except FileNotFoundError as e:
        sys.exit(str(e))
    df, meta = load_scan(path)
    print_summary(path, df, meta)

    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")          # draw without a window; must come before pyplot
    fig = plot_spectrum(df, f"{path.name}  |  gain {gain_label(meta)} dB")

    if args.png:
        png = path.with_suffix(".png")
        fig.savefig(png, dpi=150)
        print("saved", png)
    if not args.no_show:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()
