"""Read-only connectivity check for the ADALM-PLUTO.

Usage (from an activated `pluto` environment):
    python check_pluto.py                    # try usb:, fall back to ip:192.168.2.1
    python check_pluto.py ip:192.168.2.1

Only reads settings. Never writes to the radio and never touches TX.
"""
import sys
import time

uris = sys.argv[1:] or ["usb:", "ip:192.168.2.1"]

print("importing adi...", flush=True)
import adi  # noqa: E402
import iio  # noqa: E402

print("libiio dll:", iio._lib._name, flush=True)

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
    sys.exit("could not connect on any URI")

print("model     :", sdr.ctx.attrs["ad9361-phy,model"], "| fw", sdr.ctx.attrs["fw_version"])
print("rx_lo     :", sdr.rx_lo / 1e6, "MHz")
print("fs        :", sdr.sample_rate / 1e6, "MS/s")
print("rx_rf_bw  :", sdr.rx_rf_bandwidth / 1e6, "MHz")
print("gain mode :", sdr.gain_control_mode_chan0, "| rx gain", sdr.rx_hardwaregain_chan0, "dB")
print("tx atten  :", sdr.tx_hardwaregain_chan0, "dB")
print("TX_LO powerdown:", sdr._ctrl.find_channel("altvoltage1", True).attrs["powerdown"].value)
