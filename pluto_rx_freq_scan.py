"""Wideband spectrum scans with the ADALM-PLUTO -> one Parquet file per scan in data/.

Usage (from an activated `pluto` environment; close SDR++ first):
    python pluto_rx_freq_scan.py --start 2400e6 --stop 2500e6 --plot   # quick test
    python pluto_rx_freq_scan.py --gain 40 --plot                       # full 325-3800 MHz
    python pluto_rx_freq_scan.py --count 10                             # 10 scans back to back
    python pluto_rx_freq_scan.py --continuous --interval 60             # every 60 s until Ctrl+C
    python pluto_rx_freq_scan.py --count 3 --interval 5 --start 2400e6 --stop 2500e6

Files are named data/scan_<UTC start, ms>_<start>to<stop>MHz.parquet,
e.g. scan_20261031T200843.512Z_325to3800MHz.parquet (sorts by time).

RECEIVE ONLY: TX attenuation is forced to -89.75 dB, the TX LO is powered down,
and sdr.tx() is replaced with a function that raises an error.
"""
import argparse
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy import signal

FS = 20e6            # sample rate (Hz): each capture sees FS of spectrum
STEP = 15e6          # LO step = usable bandwidth kept per capture (center +/- 7.5 MHz)
RF_BW = 18e6         # analog baseband filter bandwidth
N_SAMPLES = 2**16    # IQ samples per capture (~3.3 ms at 20 MS/s)
NPERSEG = 1024       # Welch segment length -> FS/NPERSEG = 19.5 kHz bin spacing
DC_MASK_HZ = 40e3    # bins within +/- this of the LO are set to NaN (DC / LO leakage)
FULL_SCALE = 2048    # 12-bit ADC: samples span about +/-2048
CLIP_LEVEL = 0.95 * FULL_SCALE
TX_ATTEN_MAX = -89.75
DATA_DIR = Path(__file__).parent / "data"


def connect(uris):
    import adi
    for uri in uris:
        try:
            sdr = adi.Pluto(uri)
            print(f"connected on {uri}")
            return sdr
        except Exception as e:
            print(f"  {uri} failed: {e}")
    sys.exit("could not connect to the Pluto")


def make_rx_only(sdr):
    """Force TX off, block tx(), and verify. Abort if anything didn't stick."""
    def _blocked(*args, **kwargs):
        raise RuntimeError("TX is disabled: this project is receive-only")
    sdr.tx = _blocked   # this defines the sdr object's own local tx function that
                        # hides the pyadi-iio library's version.
                        # any accidental call to sdr.tx(...) raises an error

    sdr.tx_hardwaregain_chan0 = TX_ATTEN_MAX
    tx_lo = sdr._ctrl.find_channel("altvoltage1", True)  # altvoltage1 = TX LO
    tx_lo.attrs["powerdown"].value = "1"

    check_tx_safe(sdr)
    print(f"TX safe: atten {sdr.tx_hardwaregain_chan0} dB, TX LO powered down")


def check_tx_safe(sdr):
    """Read back the TX state; abort if it isn't max attenuation + LO powered down."""
    tx_lo = sdr._ctrl.find_channel("altvoltage1", True)
    if sdr.tx_hardwaregain_chan0 != TX_ATTEN_MAX or tx_lo.attrs["powerdown"].value != "1":
        sys.exit("TX is not in a safe state; aborting")


def configure_rx(sdr, gain):
    sdr.sample_rate = int(FS)
    sdr.rx_rf_bandwidth = int(RF_BW)
    sdr.rx_buffer_size = N_SAMPLES
    sdr.gain_control_mode_chan0 = "manual"   # no AGC: gain must not change mid-scan
    sdr.rx_hardwaregain_chan0 = gain
    # Fewer queued kernel buffers = less stale data after a retune.
    # Must happen before the first rx() call creates the buffer.
    try:
        sdr._rxadc.set_kernel_buffers_count(1)
    except Exception as e:
        print(f"note: could not set kernel buffer count ({e})")


def step_centers(start, stop):
    """LO frequencies whose +/- STEP/2 slices tile [start, stop)."""
    n = math.ceil((stop - start) / STEP)
    return start + STEP / 2 + STEP * np.arange(n)


def capture_psd(sdr, center):
    """Tune, discard stale data, capture, return (abs_freq_hz, psd_dbfs_hz, peak)."""
    sdr.rx_lo = int(center)
    sdr.rx()                      # throw away: may hold samples from the old LO
    iq = sdr.rx()

    peak = max(np.abs(iq.real).max(), np.abs(iq.imag).max())
    x = iq / FULL_SCALE           # normalize so ADC full scale = 1.0 -> dBFS
    x = x - x.mean()              # remove baseband DC offset

    # Two-sided Welch PSD (complex IQ has distinct +/- frequencies), like pwelch.
    f, p = signal.welch(x, fs=FS, window="hann", nperseg=NPERSEG,
                        noverlap=NPERSEG // 2, return_onesided=False,
                        detrend=False, scaling="density")
    f, p = np.fft.fftshift(f), np.fft.fftshift(p)

    keep = (f >= -STEP / 2) & (f < STEP / 2)      # drop filter roll-off edges
    f, p = f[keep], p[keep]
    psd_db = 10 * np.log10(p)
    psd_db[np.abs(f) < DC_MASK_HZ] = np.nan       # mask residual DC spike
    return center + f, psd_db, peak


def scan(sdr, start, stop):
    """One pass over [start, stop): capture every LO step and join the pieces."""
    centers = step_centers(start, stop)
    print(f"scanning {start/1e6:.1f}-{stop/1e6:.1f} MHz in {len(centers)} steps")
    freqs, psds, ctrs, clipped = [], [], [], []
    t0 = time.time()
    for i, c in enumerate(centers):
        f, p, peak = capture_psd(sdr, c)
        if peak >= CLIP_LEVEL:
            clipped.append(c)
        freqs.append(f)
        psds.append(p)
        ctrs.append(np.full(f.size, c))
        print(f"\r  step {i + 1}/{len(centers)}  {c/1e6:8.1f} MHz", end="", flush=True)
    print(f"\n  done in {time.time() - t0:.1f} s")
    if clipped:
        print(f"WARNING: near full scale at {len(clipped)} step(s) "
              f"(e.g. {clipped[0]/1e6:.1f} MHz): lower --gain")

    f, p, c = np.concatenate(freqs), np.concatenate(psds), np.concatenate(ctrs)
    inside = (f >= start) & (f < stop)            # trim overshoot past --stop
    return f[inside], p[inside], c[inside]


def scan_filename(ts, start, stop):
    """scan_<UTC, ms>_<start>to<stop>MHz.parquet. Time first, so names sort by time;
    milliseconds keep back-to-back scans of a narrow band (~0.3 s each) unique."""
    return (f"scan_{ts:%Y%m%dT%H%M%S}.{ts.microsecond // 1000:03d}Z_"
            f"{start/1e6:g}to{stop/1e6:g}MHz.parquet")


def save(freq, psd, center, ts, gain, start, stop):
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / scan_filename(ts, start, stop)
    table = pa.table({
        "timestamp": pa.array(np.full(freq.size, ts), pa.timestamp("ms", tz="UTC")),
        "freq_hz": freq,
        # from_pandas=True stores NaN (masked DC bins) as Parquet NULL, which SQL
        # aggregates like max()/avg() skip; NaN would sort above every number.
        "psd_dbfs_hz": pa.array(psd.astype(np.float32), from_pandas=True),
        "center_hz": center,
    })
    meta = {"gain_db": gain, "fs_hz": FS, "step_hz": STEP, "rf_bw_hz": RF_BW,
            "n_samples": N_SAMPLES, "nperseg": NPERSEG, "dc_mask_hz": DC_MASK_HZ,
            "start_hz": start, "stop_hz": stop}
    table = table.replace_schema_metadata({k: str(v) for k, v in meta.items()})
    # Write under a temporary name, then rename. A Ctrl+C mid-write leaves only a
    # .tmp file, never a truncated scan_*.parquet that a later query would choke on.
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(table, tmp)
    tmp.replace(path)
    print(f"saved {freq.size:,} rows -> {path}")
    return path


def plot(freq, psd, ts, gain):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(freq / 1e6, psd, lw=0.5)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("PSD (dBFS/Hz)")
    ax.set_title(f"Pluto scan {ts:%Y-%m-%d %H:%M:%S} UTC, gain {gain} dB")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    plt.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gain", type=float, default=40, help="manual RX gain, dB (default 40)")
    ap.add_argument("--start", type=float, default=325e6, help="start freq, Hz")
    ap.add_argument("--stop", type=float, default=3800e6, help="stop freq, Hz")
    ap.add_argument("--uri", help="e.g. usb: or ip:192.168.2.1 (default: try both)")
    ap.add_argument("--plot", action="store_true",
                    help="when done, show the spectrum of the last scan saved "
                         "(with --count N or --continuous: only the last one; "
                         "use tools/plot_sweeps.py to compare scans)")
    repeat = ap.add_mutually_exclusive_group()
    repeat.add_argument("--count", type=int, default=1,
                        help="number of scans (default 1)")
    repeat.add_argument("--continuous", action="store_true",
                        help="scan until Ctrl+C (instead of --count)")
    ap.add_argument("--interval", type=float,
                    help="seconds from one scan's start to the next "
                         "(default: start the next scan as soon as one finishes)")
    args = ap.parse_args()

    if not 325e6 <= args.start < args.stop <= 3800e6:
        sys.exit("need 325e6 <= start < stop <= 3800e6")
    if args.interval is not None and args.interval < 0:
        sys.exit("--interval must be >= 0 (seconds)")
    if args.count < 1:
        sys.exit("--count must be >= 1")

    sdr = connect([args.uri] if args.uri else ["usb:", "ip:192.168.2.1"])
    make_rx_only(sdr)
    configure_rx(sdr, args.gain)

    last_scan = scan_loop(sdr, args)
    if args.plot and last_scan is not None:
        plot(*last_scan, args.gain)


def scan_loop(sdr, args):
    """Scan args.count times, or until Ctrl+C with --continuous.

    Without --interval, each scan starts as soon as the previous one is saved.
    With --interval, scans start on a fixed schedule (start to start).
    Returns (freq, psd, ts) of the last saved scan, or None.
    """
    limit = "Ctrl+C" if args.continuous else f"{args.count} scan(s)"
    pace = f"every {args.interval:g} s" if args.interval else "back to back"
    print(f"scanning {pace} until {limit}")
    n_saved = 0
    last_scan = None
    next_start = time.monotonic()    # monotonic clock: unaffected by PC clock changes
    try:
        while args.continuous or n_saved < args.count:
            check_tx_safe(sdr)
            ts = datetime.now(timezone.utc)
            print(f"\nscan {n_saved + 1} at {ts:%Y-%m-%d %H:%M:%S} UTC")
            freq, psd, center = scan(sdr, args.start, args.stop)
            save(freq, psd, center, ts, args.gain, args.start, args.stop)
            n_saved += 1
            last_scan = (freq, psd, ts)
            if not args.continuous and n_saved >= args.count:
                break
            if not args.interval:
                continue                 # back to back: start the next scan now

            # Fixed-rate schedule: next start = previous start + interval.
            next_start += args.interval
            wait = next_start - time.monotonic()
            if wait > 0:
                print(f"next scan in {wait:.1f} s (Ctrl+C to stop)")
                time.sleep(wait)
            else:
                print("note: scan took longer than --interval; starting the next now")
                next_start = time.monotonic()   # don't try to "catch up" missed slots
    except KeyboardInterrupt:
        print("\nstopped by Ctrl+C (any unfinished scan was discarded)")
    print(f"{n_saved} scan(s) saved to {DATA_DIR}")
    return last_scan


if __name__ == "__main__":
    main()
