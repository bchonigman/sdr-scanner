"""Read-only connectivity check for the ADALM-PLUTO.

Usage (from an activated `pluto` environment):
    python check_pluto.py                     # try usb:, fall back to ip:192.168.2.1
    python check_pluto.py ip:192.168.2.1
    python check_pluto.py ip:192.168.2.1 usb: # try several, in this order

Only reads settings. Never writes to the radio and never touches TX.
"""
import argparse
import sys
import time

# Parse arguments before importing adi, so -h works even if libiio would fail to load.
ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("uris", nargs="*", metavar="URI",
                help="URI(s) to try in order (default: usb:, then ip:192.168.2.1)")
args = ap.parse_args()
uris = args.uris or ["usb:", "ip:192.168.2.1"]

print("Initiating basic read-only connectivity check for the ADALM-PLUTO.", flush=True)


# Check if libraries and DLLs are loading correctly

print("importing adi...", flush=True)
# the following imports are deliberately not at the top of the file. 
# importing adi loads the libiio DLL, which fails or exits silently 
# when the correct env isn’t activated
import adi  # noqa: E402
import iio  # noqa: E402


print("libiio dll:", iio._lib._name, flush=True)  # Print path of the libiio DLL that loaded.
                                                  # Should be inside envs\pluto, not System32.


# Check if we can connect to the Pluto SDR and print basic info about the Pluto to terminal
sdr = None
for uri in uris:
    t0 = time.time()
    print(f"connecting to {uri} ...", flush=True)
    try:
        sdr = adi.Pluto(uri)
        print(f"connected in {time.time() - t0:.1f}s", flush=True)
        break
    except Exception as e:
        print(f"  failed: {e}", flush=True)

if sdr is None:
    sys.exit("could not connect to the Pluto SDR on any URI")

print("model     :", sdr.ctx.attrs["ad9361-phy,model"], "| fw", sdr.ctx.attrs["fw_version"])
print("rx_lo     :", sdr.rx_lo / 1e6, "MHz")
print("fs        :", sdr.sample_rate / 1e6, "MS/s")
print("rx_rf_bw  :", sdr.rx_rf_bandwidth / 1e6, "MHz")
print("gain mode :", sdr.gain_control_mode_chan0, "| rx gain", sdr.rx_hardwaregain_chan0, "dB")
print("tx atten  :", sdr.tx_hardwaregain_chan0, "dB")
print("TX_LO powerdown:", sdr._ctrl.find_channel("altvoltage1", True).attrs["powerdown"].value)
