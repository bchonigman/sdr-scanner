# sdr-scanner

Current status and next steps live in [NOTES.md](NOTES.md). Read it at the start of each session.

## Why this project exists

I'm learning to use the Analog Devices ADALM-PLUTO SDR Active Learning Module.
The longer-term goal is to use software-defined radios to help characterize the
ADCs my company develops, but the overall goal is better understanding of:

- the PlutoSDR itself
- SDR concepts, digital signal processing, and RF spectrum / communications
- setting up Python programming environments for this kind of work
- Jupyter notebooks (a standard industry skill)
- git version control and good habits around it

Background: I mostly use MATLAB at work and am new to Python, conda and Jupyter.
MATLAB analogies help.

## How to work with me

- Explain what you're about to do, and why, **before** running it.
- Ask before installing software, changing system settings, or anything hard to undo.
- Check what's already installed (e.g. Anaconda at `C:\Users\bchon\anaconda3`)
  before assuming something is missing.
- Treat this as a learning project: explain the DSP/RF reasoning behind design
  choices, not just the code.
- Prefer small steps I can validate before moving on.

## Original goal (as I wrote it)

Build a wideband spectrum sweep logger for an ADALM-PLUTO (AD9363, Rev C,
firmware v0.38) on Windows 11. Stock range is 325 MHz to 3.8 GHz. Use pyadi-iio
(try `usb:`, fall back to `ip:192.168.2.1`).

- Step the RX LO across the range in about 15 MHz steps (20 MHz sample rate,
  discarding the filter-rolloff edges), grab IQ per step, and compute a Welch PSD.
- Use manual gain, with gain as a command-line option, to avoid AGC artifacts.
  Remove or mask the DC spike at each center frequency.
- Log each full sweep with a timestamp to a file format that's easy to query
  later (Parquet or SQLite).
- Add a plotting script for a frequency-vs-time heatmap and a max-hold/average
  spectrum.
- Start with a single sweep and a quick plot to validate, then add continuous
  logging with a configurable interval.
- Receive only. The script must never enable or transmit on TX.

## Hard rules

- **Receive only.** Never call `tx()` or enable/transmit on TX. Keep TX attenuation
  at maximum (-89.75 dB) and the TX LO powered down.
  Why: so nothing accidentally transmits and interferes with others' Wi-Fi or cellular
  service while I'm still learning the tools and the RX side. TX experiments come later,
  but only when I explicitly say so. Until then, this rule holds.
- **Always use the activated `pluto` conda env** (Anaconda Prompt ->
  `conda activate pluto`). Without activation, Windows loads the system libiio 1.0
  from System32 and `import adi` fails. Avoid `conda run` for Pluto scripts (it hung).
- Install packages from **conda-forge** only (`--override-channels -c conda-forge`).
- Don't install into `pluto` while another install is running, and only one program
  should control the Pluto at a time.
- Sweep data goes in `data/` and stays out of git.
