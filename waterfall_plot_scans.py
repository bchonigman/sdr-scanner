"""Waterfall (frequency vs time) plus max-hold and average spectra over many scans.

No Pluto needed: reads the Parquet files that pluto_rx_freq_scan.py saved in data/.

Usage:
    python waterfall_plot_scans.py                                  # all scans in data/
    python waterfall_plot_scans.py --last 5                         # newest 5 scans
    python waterfall_plot_scans.py --last 5 --start 2400e6 --stop 2500e6   # zoom in
    python waterfall_plot_scans.py "data/scan_20261107*.parquet"    # pick files by pattern
    python waterfall_plot_scans.py --last 5 --png --no-show         # save as PNG, dont display window

Waterfall pixels show the PEAK of the bins they cover (like a spectrum analyzer's
peak detector), so narrow signals stay visible when zoomed out. The noise floor looks
a few dB higher there than in the spectra below, which use full resolution.
"""
import argparse
import glob
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pyarrow.parquet as pq

DATA_DIR = Path(__file__).resolve().parent / "data"


def pick_files(args):
    if args.files:
        files = []
        for pattern in args.files:   # PowerShell passes "*" through, so expand here
            matches = glob.glob(pattern)
            if not matches:
                sys.exit(f"no files match {pattern}")
            files += [Path(m) for m in matches]
    else:
        files = list(DATA_DIR.glob("scan_*.parquet"))
    files = sorted(set(files), key=lambda p: p.name)   # UTC names sort by time
    if args.last:
        files = files[-args.last:]
    if not files:
        sys.exit(f"no scans in {DATA_DIR}")
    return files


def scan_time(path):
    # scan_20261031T200843.512Z_325to3800MHz.parquet -> the time part after "scan_"
    stamp = path.stem.split("_")[1]
    return datetime.strptime(stamp, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)


def read_settings(files):
    """Return (gain label, native bin spacing in Hz); warn if gains differ."""
    gains = {}   # gain in dB -> list of files with that gain
    meta = {}
    for f in files:
        meta = {k.decode(): v.decode() for k, v in (pq.read_schema(f).metadata or {}).items()}
        # Compare as numbers, not text: --gain 40 stores '40.0', the default stores '40'.
        g = meta.get("gain_db")
        gains.setdefault(None if g is None else float(g), []).append(f)

    def label(g):
        return "?" if g is None else f"{g:g}"     # :g prints 40.0 as 40, 40.5 as 40.5

    if len(gains) > 1:  # some scans had different gain values
        counts = ", ".join(f"{label(g)} dB x{len(fs)}" for g, fs in gains.items())
        print(f"WARNING: scans used different gains ({counts}); "
              "their dBFS levels aren't directly comparable")
    bin_hz = float(meta.get("fs_hz", 20e6)) / float(meta.get("nperseg", 1024))
    return "/".join(label(g) for g in gains), bin_hz


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="Parquet files or patterns (default: data/)")
    ap.add_argument("--last", type=int, help="use only the newest N scans")
    ap.add_argument("--start", type=float, help="lowest frequency to show, Hz")
    ap.add_argument("--stop", type=float, help="highest frequency to show, Hz")
    ap.add_argument("--bins", type=int, default=1500,
                    help="waterfall columns (default 1500)")
    ap.add_argument("--vmin", type=float, help="waterfall color floor, dBFS/Hz")
    ap.add_argument("--vmax", type=float, help="waterfall color ceiling, dBFS/Hz")
    ap.add_argument("--png", action="store_true", help="save a PNG in data/")
    ap.add_argument("--no-show", action="store_true", help="don't open a plot window")
    args = ap.parse_args()

    files = pick_files(args)
    gain, bin_hz = read_settings(files)
    times = [scan_time(f) for f in files]

    # DuckDB reads the files directly and does the heavy grouping, so only small
    # results come back to Python (like a SQL query instead of loading everything).
    file_list = "[" + ", ".join("'" + f.as_posix().replace("'", "''") + "'"
                                for f in files) + "]"
    con = duckdb.connect()
    con.execute(f"CREATE VIEW all_bins AS "
                f"SELECT * FROM read_parquet({file_list}, filename=true)")
    lo, hi = con.execute("SELECT min(freq_hz), max(freq_hz) FROM all_bins").fetchone()
    fmin = lo if args.start is None else max(args.start, lo)
    fmax = hi if args.stop is None else min(args.stop, hi)
    if fmin >= fmax:
        sys.exit(f"no data between {fmin/1e6:.1f} and {fmax/1e6:.1f} MHz")
    con.execute(f"CREATE VIEW s AS SELECT * FROM all_bins "
                f"WHERE freq_hz BETWEEN {fmin} AND {fmax}")

    # --- waterfall: one row per scan, peak-detect bins into --bins columns ---
    span = fmax - fmin + bin_hz
    pixel_hz = max(span / args.bins, bin_hz)       # never finer than the real bins
    n_cols = math.ceil(span / pixel_hz)
    wf = con.execute(f"""
        SELECT filename,
               least(floor((freq_hz - {fmin}) / {pixel_hz} + 1e-6), {n_cols - 1})::INT AS col,
               max(psd_dbfs_hz) AS p
        FROM s GROUP BY ALL""").df()
    row_of = {f.as_posix(): i for i, f in enumerate(files)}
    W = np.full((len(files), n_cols), np.nan, dtype=np.float32)
    W[wf.filename.map(row_of).to_numpy(), wf.col.to_numpy()] = wf.p.to_numpy()

    # --- full-resolution spectra across scans ---
    # Averaging in linear power, then convert back to dB. Each bin is already a Welch
    # average of ~127 segments, so for steady noise a linear power avg and a log power avg
    # only differ by only ~0.02 dB. It matters for signals that come and go:
    # a -90 dBFS/Hz burst in 1 of 10 scans over a -130 floor averages to about -100 in
    # linear power, but averaging the dB values gives -126, close to the noise floor.
    sp = con.execute("""
        SELECT freq_hz,
               max(psd_dbfs_hz) AS max_hold,
               10 * log10(avg(pow(10, psd_dbfs_hz / 10))) AS avg_db
        FROM s GROUP BY freq_hz ORDER BY freq_hz""").df()

    print(f"{len(files)} scans, {times[0]:%Y-%m-%d %H:%M:%S} to "
          f"{times[-1]:%Y-%m-%d %H:%M:%S} UTC, gain {gain} dB")
    print(f"{fmin/1e6:.1f}-{fmax/1e6:.1f} MHz; waterfall pixel = {pixel_hz/1e3:.1f} kHz "
          f"(peak of ~{pixel_hz/bin_hz:.0f} bins of {bin_hz/1e3:.1f} kHz)")
    print(f"average noise floor (median): {sp.avg_db.median():.1f} dBFS/Hz")

    # --- plot ---
    if args.no_show:
        import matplotlib
        matplotlib.use("Agg")      # draw without a window
    import matplotlib.pyplot as plt

    vmin = args.vmin if args.vmin is not None else np.nanpercentile(W, 2)
    vmax = args.vmax if args.vmax is not None else np.nanpercentile(W, 99.9)

    fig, (ax_w, ax_s) = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                                     layout="constrained",
                                     gridspec_kw={"height_ratios": [2, 1]})
    x_edges = (fmin + pixel_hz * np.arange(n_cols + 1)) / 1e6
    mesh = ax_w.pcolormesh(x_edges, np.arange(len(files) + 1), W,
                           vmin=vmin, vmax=vmax, cmap="viridis")
    fig.colorbar(mesh, ax=(ax_w, ax_s), shrink=0.6, label="peak PSD (dBFS/Hz)")
    rows = np.unique(np.linspace(0, len(files) - 1, min(len(files), 10)).round().astype(int))
    ax_w.set_yticks(rows + 0.5, [f"{times[i]:%m-%d %H:%M:%S}" for i in rows])
    ax_w.set_ylabel("scan start (UTC), newest at top")
    ax_w.set_title(f"{len(files)} scans, {times[0]:%Y-%m-%d %H:%M:%S} to "
                   f"{times[-1]:%Y-%m-%d %H:%M:%S} UTC  |  gain {gain} dB")

    ax_s.plot(sp.freq_hz / 1e6, sp.max_hold, lw=0.5, color="tab:red", label="max hold")
    ax_s.plot(sp.freq_hz / 1e6, sp.avg_db, lw=0.5, color="tab:blue",
              label="average (linear power)")
    ax_s.set_xlabel("Frequency (MHz)")
    ax_s.set_ylabel("PSD (dBFS/Hz)")
    ax_s.set_xlim(fmin / 1e6, fmax / 1e6)
    ax_s.grid(alpha=0.3)
    for line in ax_s.legend(loc="upper right").get_lines():
        line.set_linewidth(2)

    if args.png:
        png = DATA_DIR / (f"scans_{times[0]:%Y%m%dT%H%M%SZ}_"
                          f"{times[-1]:%Y%m%dT%H%M%SZ}.png")
        fig.savefig(png, dpi=150)
        print("saved", png)
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
