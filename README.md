# SecureCOM — COUPLING Console, version1

Working multi-protocol terrestrial radio decoder with a browser operator console.
**One USRP B210, one antenna, 4 protocols (DMR / NXDN / P25 / TETRA)**, burst-hop
scheduled, with live spectrum/waterfall/time graphs, real decoded audio, `.wav`
recording, hardware control and dwell scheduling — all driven from the console.

Verified working against a real DMR handheld on 2026-09-01: real decode, real
audio, real recordings (see *Verified results* below).

---

## 1. Layout

```
version1/
├── run_securecom.sh        one-shot launcher: builds, starts, verifies all 8 stages
├── README.md
├── allinone.grc            Module 2 flowgraph source (GNU Radio Companion)
├── allinone.py             Module 2 compiled from the .grc — this is what runs
├── allinone_nogui.grc      headless variant (shares the .grc's flowgraph ID — see §6)
├── module1/
│   ├── CMakeLists.txt
│   └── src/                Module 1 C++ sources (USRP tuner + TCP server)
├── gui/
│   ├── bridge_server.py    Bridge: process control + real IQ/audio → WebSocket
│   ├── securecom_gui.html  Operator console (browser)
│   └── recordings/         Decoded .wav files land here at runtime
├── deps/                   vendored dependencies — see §8
│   ├── gr_tetra_decoder/   TETRA decoder block + libtetrakit_capi.so
│   └── grc_blocks/         custom GRC block YAMLs (tetra, dsd)
└── tools/                  diagnostics — see §9
    ├── offline_decode_test.py   verify decode with no radio (found the gain bug)
    ├── measure_signal.py        find a transmission's REAL frequency
    ├── rf_level_probe.py        gain / clipping sweep
    ├── dwell_probe.py           audio level + TCP backlog across a dwell
    └── testdata/
        └── dmr_real_capture.cf32.gz   real 0.97 s DMR key-up, for regression
```

### The three processes

| # | What | Role |
|---|------|------|
| 1 | `securecom_module1` (C++/UHD) | Retunes the B210 across the 4 bands on a dwell schedule; streams raw IQ for the active band out over TCP `7001-7004` |
| 2 | `allinone.py` (GNU Radio) | Reads those 4 TCP ports, channelizes and decodes; exposes real audio + TETRA call-log on ZMQ `9101-9105` |
| 3 | `bridge_server.py` | Starts/stops 1 and 2, reads their real output, serves the console over WebSocket `8787` |

The console never fabricates data. If the bridge is not connected it shows
`NOT CONNECTED` and nothing else — there is no simulation path in the code.

---

## 2. Build (once)

```bash
cd version1/module1
mkdir -p build && cd build
cmake .. && make
```

Produces `module1/build/securecom_module1`. Requires UHD dev headers and CMake.

`allinone.py` is already compiled and committed. Only recompile if you edit the
flowgraph — see *Editing the flowgraph* below.

---

## 3. Run

### The easy way — one command

```bash
cd version1
./run_securecom.sh                     # defaults (1 s dwell per band)
./run_securecom.sh --dwell-dmr 15      # 15 s DMR dwell
./run_securecom.sh --gain 30           # RX gain 30 dB
./run_securecom.sh --no-browser        # headless / remote X
./run_securecom.sh --stop              # shut the whole stack down
```

It runs all 8 stages in order and **verifies each before continuing**: preflight →
cleanup → C++ build → bridge → web server → hardware → decoder → console. Ctrl-C
tears everything down cleanly.

Two things it handles that are easy to get wrong by hand:
- **Stale processes are killed first.** A leftover `allinone.py` holding ZMQ port
  9101 silently stops the new decoder's audio taps from binding, and the console
  still reports `RUNNING` — no audio, no obvious cause.
- **The USRP check runs *after* that cleanup.** A still-running Module 1 holds the
  radio open, which makes `uhd_find_devices` report no device at all.

### The manual way

Plug in the B210 first and confirm it is seen:

```bash
uhd_find_devices
```

**Terminal 1 — bridge (starts/stops everything else for you):**

```bash
cd version1/gui
python3 bridge_server.py
```

**Terminal 2 — serve the console over HTTP:**

```bash
cd version1/gui
python3 -m http.server 8788 --bind 127.0.0.1
```

> Serve over HTTP rather than opening the file directly. `file://` breaks the
> WebSocket connection and `.wav` playback in some browsers.

**Then in a browser:**

```
http://127.0.0.1:8788/securecom_gui.html
```

The header should read `LIVE — real IQ + real decode/audio`.

**Finally, in the console's Hardware tab:**
1. **Start hardware** → launches the real `securecom_module1`
2. **Start decoder** → launches the real `allinone.py`

Both must be running to get audio. Starting the decoder also enables browser
audio playback (browsers require a user gesture before playing sound).

To stop: **Stop** / **Stop decoder** in the Hardware tab, then Ctrl-C the bridge.

---

## 4. Using the console

### Signals tab
Per-band state (`idle` / `ACTIVE` / `DECODING`) and RF level, plus:
- **Channel activity** — measured energy per channelizer channel
- **Decoded field** — protocol, band centre, channel number, channel offset,
  absolute channel frequency, channel SNR, occupied channels, RF level, decode state

### Hardware tab
Device, USB link, LO lock, sample rate, RX gain (**Apply gain** restarts the
radio), cycle counter, TCP client count, and Start/Stop for both modules.

### Schedule tab
Per-protocol **dwell time**. **Apply** genuinely restarts Module 1 with new
`SECURECOM_*_DWELL_SEC` values — the binary only reads dwell at startup, so a
restart is the only real way to change it.

> The **Gap** column is inert. Gap is a compile-time constant (`GAP_SEC` in
> `module1/src/burst_controller.h`), not an env var. Changing gap needs a C++
> edit and rebuild.

### Recordings tab
Reads the real `gui/recordings/` folder (including files from earlier sessions).
Per file: **▶** play, **↓** save, **✕** delete. Plus **Refresh** and **Delete all**.

Recording captures the **entire dwell**, not only when audio crosses a level, and
each entry is labelled `decoded audio present` or `dwell captured, no decode` —
so you can tell a silent dwell from an undecoded one.

### Graphs
Frequency, waterfall and time. **Drag** to zoom a region, **wheel** to scale,
**double-click** or **reset zoom** to restore — same interaction model as GNU
Radio's own Qt GUI widgets.

---

## 5. Tuned values, and why

These were found by measurement, not assumption. Do not change them casually.

| Where | Value | Why |
|---|---|---|
| `module1/src/main.cpp` | DMR446 = **446.118528 MHz** | A real IQ capture of the test radio put its power centroid at +24778 Hz from the nominal 446.09375 MHz, with 8.3 kHz occupied bandwidth. Tuning here centres the signal in channelizer channel 0. **Retune this for your own radio.** |
| `allinone.grc` | **One decode chain per protocol** | DMR, NXDN and P25 each run `channelizer → sum of all N channels → resampler → LPF → squelch → demod → ONE DSD` (the `dmr_test` structure), built by `tools/make_single_chain.py`. Replaces 42 parallel chains (16+16+10): same DMR decode (5.12 s vs 5.14 s on the real capture), 3 DSD instances instead of 42, decoder CPU 62% vs 262%. |
| `allinone.grc` | demod gain **1.0** for DMR, NXDN and P25 | Measured on real recordings: NXDN at 7.28 and P25 at 4.24 decoded **nothing**; at 1.0 NXDN decoded 14.2 of 15.3 s. The theoretical `fs/(2π·dev)` does *not* work — DSD's slicer overdrives. |
| `allinone.grc` | P25 frame **`AUTO_DETECT`** | `P25_PHASE_1` decoded nothing with any gain or modulation; `AUTO_DETECT` decoded 5.0 s of a 34 s recording (3.7 s with the standalone `p25_decoder.grc`). |
| `allinone.grc` | `squelch_thresh_dmr` = **−73 dB**; `_nxdn/_p25` = −20 dB, one slider each | DMR −73 found live (Oct 26 2026, real DMR handheld, 40 dB RX gain): clean voice, less noise. In the single summed chain DSD itself mutes on noise (no sync, no audio), so the squelch should stay open — at −20 it chattered on weaker speech, breaking DSD frames into garble and losing whole dwells. NXDN/P25 are still −20 (not tested live). The old single `squelch_thresh` drove all 42 squelches, so lowering it for DMR also opened every NXDN and P25 channel. Squelch is absolute: re-check it if you change RX gain. |
| `allinone.grc` | `volume_dmr/_nxdn/_p25` = **0.5**, one slider each | DSD output peaks at −0.8 dBFS; 0.5 gives about −24 dBFS rms / −6 dBFS peak with 0% clipping. The old 0.04 put voice near −48 dBFS. |
| `allinone.grc` | **Separate speaker output per protocol** | One `audio_sink` per protocol, mixed by the sound server — no GNU Radio adder ties the protocols' throughput together. Measured equal or better than one mixed adder; `allinone_single_mixed.grc` is the mixed alternative. |
| `gui/bridge_server.py` | RX gain default **40 dB** | An earlier reading of −5.6 dBFS looked like ADC overload, but peak/RMS was 4.5 dB with 0% of samples above 0.95 — not clipping. Adjustable from the Hardware tab. |

### Verified results (2026-09-01, real DMR handheld)

```
dmr_20260901T131321.wav   15.33 s   rms -24.0 dBFS   peak 0.602   clipped 0.00%
```

Before the squelch/volume fix the same setup produced peak `1.000` and
0.5–0.9% clipped samples, with audio degrading a few seconds into each dwell.

---

## 6. Editing the flowgraph

`allinone.grc` and `allinone_nogui.grc` share an internal flowgraph ID, so
`grcc` writes both to the **same** output filename. Always copy afterwards:

```bash
cd version1
grcc allinone.grc
cp securecom_module2_decoder.py allinone.py
```

Skipping the `cp` silently leaves you running the previous build.

### The ZMQ taps
`allinone.grc` contains 5 blocks added for this console — `bridge_zmq_dmr`,
`bridge_zmq_nxdn`, `bridge_zmq_p25`, `bridge_zmq_tetra` (audio, ports 9101-9104)
and `bridge_zmq_tetra_events` (TETRA `call_log`, port 9105). They are purely
additive taps off the existing `audio_mix_*` blocks and the TETRA decoder's
message port; no original block or connection was modified. Removing them breaks
console audio, recordings and TETRA events.

---

## 7. Known limits

- **No talkgroup / unit ID for DMR, NXDN, P25.** `dsd_block_ff` in gr-dsd-ext
  exposes only an audio output — no message port — so there is nothing to read.
  The console shows `unavailable — dsd_block exposes no metadata port` rather
  than inventing a value. Real talkgroups would require patching that C++ block.
  TETRA is different: it has a real `call_log` message port, which is tapped.
- **Channel number is derived**, from measured per-channel FFT energy. It tells
  you *where* a signal sits; it is not protocol metadata.
- **Only DMR has been tested against a live signal.** The NXDN, P25 and TETRA
  paths are wired and running but have never seen real RF, and the TETRA
  call-log tap has never carried real data.
- **Burst-hop means you only ever see one band at a time.** Traffic on the other
  three bands during a dwell is missed by construction. This is the cost of one
  USRP instead of four.
- **200 kSps sits on the AD9361's analog filter floor** (~200 kHz minimum), so
  UHD warns every retune and some energy from ±100–200 kHz folds in. Not fixable
  by tuning; it would need a wider sample rate with digital decimation.
- **Symmetric occupied channels are images, not signals.** IQ imbalance mirrors a
  strong signal about DC (e.g. channels 15 and 1, or 13 and 3). The weaker of a
  symmetric pair is the artefact.

---

## 8. Dependencies

### Vendored here (`deps/`)
- **`gr_tetra_decoder/`** — the `tetra_decoder_block` Python block and its
  `libtetrakit_capi.so`. This one matters: **`allinone.py` line 48 hardcodes an
  absolute path** to where this module lived originally:

  ```python
  sys.path.insert(0, '/home/shankar/Downloads/tutorials/tetra_sigtel_v2_project/gr_tetra_decoder')
  ```

  That path is injected by the GRC block definition, so it comes back every time
  you re-run `grcc`. The copy here means the code is preserved with the project;
  if you relocate anything, fix the path in
  `deps/grc_blocks/tetra_decoder_block.block.yml` (and in
  `~/.grc_gnuradio/tetra_decoder_block.block.yml`, which is where GRC actually
  reads it from) and regenerate.

- **`grc_blocks/`** — the custom block YAMLs the flowgraph references
  (`tetra_decoder_block`, `dsd_dsd_block_ff`). GRC loads these from
  `~/.grc_gnuradio/` and `/usr/local/share/gnuradio/grc/blocks/`; copies are kept
  here so the flowgraph can be opened again on a fresh machine.

### Verified environment (measured 2026-09-15, the bench machine)

This is not "should work with" — it is what the working stack actually runs on.
Commands to re-check each one are in §8.1.

| Component | Version | Installed from | Lives in |
|---|---|---|---|
| OS | Ubuntu 22.04.5 LTS | — | — |
| Kernel | 6.8.0-138-generic | — | — |
| GNU Radio | **3.10.1.1-2** | apt | `/usr` |
| UHD (for GNU Radio) | **4.1.0.5-3** | apt (`libuhd4.1.0`) | `/usr/lib/x86_64-linux-gnu` |
| UHD (for Module 1) | **4.10.0.0-0-g2af4ddb9** | source build | `/usr/local/lib` |
| Python | 3.10.12 | apt | `/usr` |
| gr-dsd-ext | `libgnuradio-dsd.so.1.0.0.0` | source build | `/usr/local` |
| CMake | 3.22.1 | apt | `/usr` |
| numpy | 1.26.4 | pip | |
| pyzmq | 27.1.0 | pip | |
| websockets | 16.1.1 | pip | |
| Radio | USRP B210, serial `3273AC6`, USB 3.0 | — | — |

#### Two UHD versions are installed, and that is deliberate

`ldd` proves they are both in use, by different processes:

```
securecom_module1        -> /usr/local/lib/libuhd.so.4.10.0     (source build)
gnuradio/uhd/uhd_python  -> /lib/x86_64-linux-gnu/libuhd.so.4.1.0  (apt)
```

Normally that is the classic UHD-conflict footgun. Here it is harmless, and the
reason is the whole point of the split architecture: **only Module 1 ever opens
the radio.** GNU Radio receives IQ over TCP (7001-7004) and never touches UHD at
runtime, so its older apt UHD 4.1 is never exercised. Do not "fix" this by
uninstalling either one — removing the apt `libuhd4.1.0` breaks `libgnuradio-uhd`
dependencies, and removing the `/usr/local` 4.10 build stops Module 1 compiling.

Consequence worth knowing: `uhd_find_devices` resolves to `/usr/local/bin` and
will report **"No UHD Devices Found" whenever the stack is up**, because Module 1
already holds the B210 exclusively. That is expected, not a fault. Stop the stack
before running any tool that opens the radio directly.

### External prerequisites (NOT vendored)
- **GNU Radio 3.10** with `gnuradio-companion`, plus python modules
  `numpy`, `websockets`, `pyzmq`, `pmt`.
- **UHD 4.x** with B210 firmware/FPGA images (`uhd_find_devices`, `uhd_usrp_probe`).
- **gr-dsd-ext** — provides the `dsd` python module and `dsd_block_ff`, which does
  all DMR/NXDN/P25 decoding. Deliberately **not** copied in: it is ~55 MB of
  third-party source (gr wrapper + `dsd` + `mbelib`) and must be compiled and
  installed system-wide anyway.

  **The source is NOT in this repo**, despite what earlier notes here claimed.
  This repo's root is `delhi_testing/coupled/`, and it contains only `secuecom/COUPLING/`.
  The gr-dsd-ext tree lives outside it, alongside the other tutorial projects:

  ```
  /home/shankar/Downloads/tutorials/secuecom/decoder_framework/gr-dsd-ext
  ```

  Installed to: `/usr/local/lib/python3.10/dist-packages/dsd/`

  ```bash
  cd /home/shankar/Downloads/tutorials/secuecom/decoder_framework/gr-dsd-ext
  mkdir -p build && cd build && cmake .. && make -j && sudo make install && sudo ldconfig
  ```

  On a fresh machine that path will not exist — you must bring the gr-dsd-ext
  tree with you, or clone it separately. Nothing in this repo can rebuild it.

  Verify with `python3 -c "import dsd; print(dsd.__file__)"`. `run_securecom.sh`
  checks for it in preflight and refuses to start without it.

---

## 8.1 Installing from scratch on Linux

Full build-up for a bare Ubuntu 22.04 machine, in the order that works. Later
steps depend on earlier ones, so do not reorder. Budget ~1 hour, most of it the
two source builds.

### Step 0 — check what you already have

```bash
lsb_release -ds && uname -r
gnuradio-config-info --version
uhd_config_info --version
python3 --version && cmake --version | head -1
python3 -c "import dsd; print('gr-dsd OK:', dsd.__file__)"
```

### Step 1 — base toolchain and GNU Radio (apt)

GNU Radio comes from apt deliberately. Building it from source is a multi-hour
job with no benefit here, and it pulls the apt UHD 4.1 in as a dependency —
which, per §8, is fine.

```bash
sudo apt update
sudo apt install -y build-essential cmake git pkg-config \
     gnuradio gnuradio-dev \
     libuhd-dev uhd-host \
     python3-pip python3-pyqt5 \
     libitpp-dev libsndfile1-dev libboost-all-dev \
     libusb-1.0-0-dev
```

`libitpp-dev` and `libsndfile1-dev` are not optional — gr-dsd links against both
(`ldd` on `libgnuradio-dsd.so` shows `libitpp.so.8` and `libsndfile.so.1`).

### Step 2 — Python modules

```bash
pip3 install --user numpy pyzmq websockets
```

Versions on the bench machine: numpy 1.26.4, pyzmq 27.1.0, websockets 16.1.1.
Note apt's scipy 1.8.0 warns that it wants numpy < 1.25 — the warning is
cosmetic here, nothing in this project calls the affected scipy paths.

### Step 3 — UHD 4.10 from source (for Module 1)

The apt UHD 4.1 stays where it is. This installs 4.10 alongside it in
`/usr/local`, which is what `module1/CMakeLists.txt` finds via
`find_package(UHD 4.0 REQUIRED)`.

```bash
git clone https://github.com/EttusResearch/uhd.git
cd uhd && git checkout v4.10.0.0
mkdir -p host/build && cd host/build
cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig
```

Then fetch the B210 FPGA/firmware images (without these the radio enumerates on
USB but never initialises):

```bash
sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py
```

Confirm `/usr/local/lib` is on the linker path — it already is via
`/etc/ld.so.conf.d/`, but verify:

```bash
ldconfig -p | grep libuhd     # should list BOTH 4.1.0 and 4.10.0
```

### Step 4 — gr-dsd-ext (the actual DMR/NXDN/P25 decoder)

This is what `dsd_block_ff` in the flowgraph resolves to. Not vendored, and
**not inside this repo** — see §8. On the bench machine it sits at:

```bash
cd /home/shankar/Downloads/tutorials/secuecom/decoder_framework/gr-dsd-ext
mkdir -p build && cd build
cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig
python3 -c "import dsd; print(dsd.__file__)"
```

On any other machine you must supply that tree yourself first.

Expect `/usr/local/lib/python3.10/dist-packages/dsd/__init__.py`.

### Step 5 — USB permissions for the B210

`uhd-host` ships `/lib/udev/rules.d/60-uhd-host.rules`, so this normally works
without extra setup. If `uhd_find_devices` finds nothing **while the stack is
stopped**, reload the rules and replug:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Verify the B210 is on the bus and reachable (stack stopped):

```bash
lsusb | grep -i ettus          # -> ID 2500:0020 Ettus Research LLC USRP B210
uhd_find_devices               # -> serial, e.g. 3273AC6
```

### Step 6 — custom GRC blocks

GRC reads block definitions from `~/.grc_gnuradio/`, not from this repo. Copy
them across or the flowgraph will not open:

```bash
mkdir -p ~/.grc_gnuradio
cp deps/grc_blocks/*.block.yml ~/.grc_gnuradio/
```

If you relocate the project, fix the hardcoded TETRA path called out in §8 —
it is baked into the block YAML and returns on every `grcc` regeneration.

### Step 7 — build Module 1 and run

```bash
cd module1 && mkdir -p build && cd build
cmake .. && make -j"$(nproc)"
cd ../.. && ./run_securecom.sh
```

`cmake` prints the UHD it picked — confirm it says 4.10, not 4.1:

```
-- UHD Version  : 4.10.0.0-0-g2af4ddb9
```

---

## 9. Diagnostic tools (`tools/`)

These are the tools that actually found this project's bugs — keep them.

### `offline_decode_test.py` — decode verification with no radio
Runs the vendored real capture through the same DSP chain and reports whether DSD
produces audio. **This is how the demod-gain bug was found.** No hardware, no
timing coordination, repeatable.

```bash
python3 tools/offline_decode_test.py               # sweep gains
python3 tools/offline_decode_test.py 1.0 24778 0   # gain offset dcblock
```

Measured result on the real capture — note the textbook value fails outright:

| gain | audio out |
|---|---|
| 0.2 | −31.2 dBFS (decodes) |
| **1.0** | **−20.5 dBFS (best — this is what ships)** |
| 3.93 | **silence** — the theoretical `fs/(2π·dev)` value overdrives DSD's slicer |

Run this before and after touching a `gain_demod*`, `squelch_thresh_*` or the
channelizer. It takes ~30 s per gain point (DSD is slow).

### `measure_signal.py` — find a transmission's real frequency
Connects to Module 1's TCP port (stack must be **up**) and reports the power
centroid and occupied bandwidth of what it hears. Use it whenever a signal is
visible but never decodes — that is almost always a frequency mismatch.

```bash
python3 tools/measure_signal.py --port 7001 --secs 30   # then key up
```

This is what revealed the radio was ~25 kHz off the configured frequency.

### `rf_level_probe.py` — gain / clipping sweep
Opens the USRP directly, so run with the stack **stopped**. Reports peak, RMS,
crest factor and the fraction of samples near full scale per gain setting.

```bash
./run_securecom.sh --stop
python3 tools/rf_level_probe.py
```

> Read it carefully: these protocols are constant-envelope 4FSK, so high RMS is
> normal and is **not** proof of clipping. Judge by peak and `>0.95`. A −5.6 dBFS
> RMS reading here was initially misdiagnosed as ADC overload when peak was 0.88
> with 0.00% near full scale — perfectly clean.

### `dwell_probe.py` — audio level and TCP backlog across a dwell
Samples decoded-audio RMS and Module 1's TCP Send-Q together, twice a second.
Use it when decode quality varies *within* a dwell.

```bash
python3 tools/dwell_probe.py     # stack up, long dwell, key up
```

This distinguished the two candidate causes of "good for 5 s then unclear":
Send-Q returned to 0 every time (so **not** TCP backpressure), while audio read
**+14.9 dBFS** — positive, i.e. ~5× over full scale. It was clipping.

### `testdata/dmr_real_capture.cf32.gz`
A genuine 0.97 s DMR key-up from the bench radio (complex64 @ 200 kSps, centred
+24778 Hz from 446.09375 MHz). Kept as a regression fixture so decode changes can
be validated without a radio. `offline_decode_test.py` unpacks it automatically.

---

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| Header says `NOT CONNECTED` | `bridge_server.py` running? Port 8787 free? |
| `No UHD Devices Found` | Reseat USB; prefer a direct port over a hub. `lsusb \| grep -i ettus`, then `lsusb -t` to confirm it enumerated at **5000M** (USB 3.0), not 480M |
| Hardware starts, no audio | Did you also press **Start decoder**? Both modules are required |
| No sound in browser | Press **Start decoder** — that gesture unlocks browser audio |
| Signal visible, never decodes | Frequency mismatch. Capture IQ and measure your radio's real centre, then set it in `main.cpp` (see §5) |
| Audio distorted / mushy | that protocol's `volume_*` too high or `squelch_thresh_*` too permissive (see §5) |
| Decode good briefly then degrades | Check the dwell (§6) and RX gain overload; with one chain per protocol there is no longer a multi-channel sum to over-drive |
| Recordings list empty after reload | Press **Refresh**; it reads the real folder |
| Flowgraph edit had no effect | You skipped `cp securecom_module2_decoder.py allinone.py` (§6) |

### Confirm the pipeline by hand

```bash
# raw IQ from Module 1 (DMR band)
ss -tlnp | grep 700
# decoded audio taps from Module 2
ss -tlnp | grep 910
# processes
ps aux | grep -E "securecom_module1|allinone.py|bridge_server"
```
