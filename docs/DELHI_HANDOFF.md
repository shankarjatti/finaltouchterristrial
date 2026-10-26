# Delhi Testing — Handoff

Everything needed to take this stack to Delhi and test it against radios other
than the DMR handheld it was developed on.

Written 2026-09-15 from the working bench machine. Every version, level and
measurement below was read off the running system, not assumed. Where something
is **unverified**, it says so explicitly — trust those warnings.

---

> **Update 2026-10-26 — read this first.** Much below changed. Current status, results and
> open issues: `coupled/secuecom/COUPLING/version1/STATUS.md`; current settings and why:
> its `README.md` §5; testing without radios (HackRF over a cable): `README.md` §9.1.
> Repo: github.com/shankarjatti/finaltouchterristrial.
>
> * The decoder now runs **one chain per protocol** (was 42), with **its own squelch and
>   volume per protocol**: squelch **−73 dB** for DMR/NXDN/P25, volume DMR **0.2**,
>   NXDN/P25 **0.5**. NXDN gain 7.28 → **1.0** and P25 gain 4.24 → **1.0** (both decoded
>   nothing before). §6.1 and §6.2 below are superseded.
> * Module 1 now survives USB errors and the bridge restarts it automatically; the console
>   shows when the radio has stopped. **Use a USB 3 port** — check the launcher's
>   "USB 3.x link (B210 at 5000 Mbps)" line; on USB 2.0 the stream breaks every few minutes.
> * The hardcoded TETRA path (§3.3) is fixed.
> * On this bench PC, `~/.bashrc` loads GNU Radio 3.8 by default. Run 3.10 tools through
>   `gr310 <cmd>` (GRC: `grc310`), e.g. `gr310 ./run_securecom.sh`.

## 0. Read this first — the three things most likely to waste your day

1. **Check the USB link before anything else.** The launcher prints the B210's own link
   speed. 480 Mbps (USB 2.0) means LIBUSB transfer errors every few minutes — the
   stack now recovers, but you lose seconds of audio each time. Use a blue USB 3 port.

2. **`uhd_find_devices` reporting "No UHD Devices Found" is normal while the
   stack is running.** Module 1 holds the USRP exclusively. Stop the stack before
   running anything that opens the radio directly. See §3.2.

3. **The DMR frequency is a channel number, not a calibration.**
   `446.118528 MHz` is 446.09375 **+24778 Hz**. That is **not** crystal error:
   the bench radio is a **Sparrow D-446**, and on its 16-channel PMR446 plan
   446.09375 is **channel 8** while 446.118528 is **channel 10** (446.11875) to
   within −222 Hz / 0.5 ppm. Confirm which channel a radio is set to before
   assuming drift — a mismatch like this is the single biggest bug this project
   ever had: signal shows on the spectrum, decode never works.

---

## 1. What this is

SecureCOM COUPLING — a multi-protocol radio receiver. A USRP B210 is time-shared
across four bands; each band is channelized, squelched, demodulated and decoded
to voice, then surfaced in a browser console with recordings.

Main project: `delhi_testing/coupled/secuecom/COUPLING/version1/`
Its own detailed README is in that folder; this document is the wider handoff.

### The three processes

| # | Process | Language | Job |
|---|---|---|---|
| 1 | `securecom_module1` | C++ / UHD | Owns the radio. Tunes, dwells band to band, serves raw IQ over TCP |
| 2 | `allinone.py` | GNU Radio | Channelize → squelch → demod → DSD decode → audio |
| 3 | `bridge_server.py` | Python | Starts/stops 1 and 2, serves the web console, records WAVs |

**Only Module 1 ever opens the USRP.** Module 2 receives IQ over TCP and never
touches UHD. This matters — see §3.2.

### Ports

| Port | Purpose |
|---|---|
| 7001 / 7002 / 7003 / 7004 | Raw IQ out of Module 1 — DMR / NXDN / P25 / TETRA |
| 9101 / 9102 / 9103 / 9104 | Decoded audio taps (ZMQ PUB, float32) — same order |
| 9105 | TETRA call-log events (ZMQ PUB, messages) |
| 8787 | Bridge WebSocket (console control) |
| 8788 | Web console HTTP |

A stale process holding 9101 silently stops a new decoder's audio taps from
binding, **while the console still reports "RUNNING"**. If audio is missing,
check for leftovers first.

---

## 2. Verified environment

Measured 2026-09-15 on the bench machine.

| Component | Version | Installed from | Lives in |
|---|---|---|---|
| OS | Ubuntu 22.04.5 LTS | — | — |
| Kernel | 6.8.0-138-generic | — | — |
| GNU Radio | **3.10.1.1-2** | apt | `/usr` |
| UHD (for GNU Radio) | **4.1.0.5-3** | apt `libuhd4.1.0` | `/usr/lib/x86_64-linux-gnu` |
| UHD (for Module 1) | **4.10.0.0-0-g2af4ddb9** | source build | `/usr/local/lib` |
| Python | 3.10.12 | apt | `/usr` |
| gr-dsd-ext | `libgnuradio-dsd.so.1.0.0.0` | source build | `/usr/local` |
| CMake | 3.22.1 | apt | `/usr` |
| numpy | 1.26.4 | pip | |
| pyzmq | 27.1.0 | pip | |
| websockets | 16.1.1 | pip | |
| scipy | 1.8.0 | apt | |
| Radio | USRP B210, serial `3273AC6`, USB 3.0 | — | — |

Re-check any of these with:

```bash
lsb_release -ds && uname -r
gnuradio-config-info --version
uhd_config_info --version
python3 --version && cmake --version | head -1
python3 -c "import dsd; print('gr-dsd OK:', dsd.__file__)"
python3 -c "import numpy,zmq,websockets;print(numpy.__version__,zmq.__version__,websockets.__version__)"
lsusb | grep -i ettus
```

---

## 3. Dependencies and where they really live

### 3.1 What is inside `delhi_testing/` (good news — it travels)

| What | Path | Size |
|---|---|---|
| Main project | `coupled/secuecom/COUPLING/version1/` | — |
| **gr-dsd-ext source** | `dmr_test/gr-dsd-ext/` | 5.7 MB |
| **TETRA decoder** | `tetra_test/gr_tetra_decoder/` | — |
| tetra-kit source | `tetra_test/tetra-kit/` | — |
| Test IQ / audio samples | `dmr_test/`, `tetra_test/`, `coupled/` | — |

`dmr_test/gr-dsd-ext` is a clean source tree (no `build/`, no `.git`) and is
otherwise identical to the copy that was actually compiled and installed on this
machine. **It is sufficient to rebuild the decoder in Delhi.**

### 3.2 Two UHD versions are installed on purpose — do not "fix" this

`ldd` proves both are in use, by different processes:

```
securecom_module1        -> /usr/local/lib/libuhd.so.4.10.0     (source build)
gnuradio/uhd/uhd_python  -> /lib/x86_64-linux-gnu/libuhd.so.4.1.0  (apt)
```

Normally this is the classic UHD footgun. Here it is harmless, because only
Module 1 opens the radio and GNU Radio never exercises its older UHD at runtime.

**Do not uninstall either.** Removing apt `libuhd4.1.0` breaks `libgnuradio-uhd`
dependencies; removing the `/usr/local` 4.10 build stops Module 1 compiling.

Consequence: `uhd_find_devices` resolves to `/usr/local/bin` and reports
**"No UHD Devices Found" whenever the stack is up** — Module 1 has the B210
exclusively. That is expected. Stop the stack before running `rf_level_probe.py`,
`uhd_usrp_probe` or `uhd_find_devices`.

### 3.3 The hardcoded path problem (TETRA) — FIXED 2026-10-26 (paths now resolve relative to the files)

`allinone.py` line 48 contains an absolute path to this developer's home dir:

```python
sys.path.insert(0, '/home/shankar/Downloads/tutorials/tetra_sigtel_v2_project/gr_tetra_decoder')
```

**This will not exist on the Delhi machine, and TETRA decode will fail on
import.** The path is injected by the GRC block definition, so it returns every
time the flowgraph is regenerated with `grcc`.

The fix: a byte-identical copy (verified by MD5 `bd4ed280ce5f9ed2adc9335868f6e6ad`)
is vendored at `COUPLING/version1/deps/gr_tetra_decoder/`. Point the path there,
and fix it permanently in:

- `deps/grc_blocks/tetra_decoder_block.block.yml`
- `~/.grc_gnuradio/tetra_decoder_block.block.yml` ← what GRC actually reads

---

## 4. Installing from scratch on Linux

Bare Ubuntu 22.04 → working stack. Do not reorder; later steps depend on earlier
ones. Budget ~1 hour, mostly the two source builds.

### Step 1 — base toolchain and GNU Radio (apt)

GNU Radio comes from apt deliberately — building it from source is a multi-hour
job with no benefit here.

```bash
sudo apt update
sudo apt install -y build-essential cmake git pkg-config \
     gnuradio gnuradio-dev \
     libuhd-dev uhd-host \
     python3-pip python3-pyqt5 \
     libitpp-dev libsndfile1-dev libboost-all-dev \
     libusb-1.0-0-dev
```

`libitpp-dev` and `libsndfile1-dev` are **not optional** — gr-dsd links against
both (`libitpp.so.8`, `libsndfile.so.1`).

### Step 2 — Python modules

```bash
pip3 install --user numpy pyzmq websockets
```

apt's scipy 1.8.0 warns it wants numpy < 1.25. Cosmetic — nothing here calls the
affected scipy paths.

### Step 3 — UHD 4.10 from source (for Module 1)

Apt's UHD 4.1 stays. This installs 4.10 alongside it in `/usr/local`, which
`module1/CMakeLists.txt` finds via `find_package(UHD 4.0 REQUIRED)`.

```bash
git clone https://github.com/EttusResearch/uhd.git
cd uhd && git checkout v4.10.0.0
mkdir -p host/build && cd host/build
cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig
```

Then the B210 FPGA/firmware images — without these the radio enumerates on USB
but never initialises:

```bash
sudo /usr/local/lib/uhd/utils/uhd_images_downloader.py
ldconfig -p | grep libuhd     # should list BOTH 4.1.0 and 4.10.0
```

### Step 4 — gr-dsd-ext (the DMR/NXDN/P25 decoder)

This is what `dsd_block_ff` in the flowgraph resolves to.

```bash
cd delhi_testing/dmr_test/gr-dsd-ext
mkdir -p build && cd build
cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig
python3 -c "import dsd; print(dsd.__file__)"
```

Expect `/usr/local/lib/python3.10/dist-packages/dsd/__init__.py`.
`run_securecom.sh` checks for this in preflight and refuses to start without it.

### Step 5 — USB permissions for the B210

`uhd-host` ships `/lib/udev/rules.d/60-uhd-host.rules`, so this usually just
works. If `uhd_find_devices` finds nothing **with the stack stopped**:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
# then unplug and replug the B210
lsusb | grep -i ettus     # -> ID 2500:0020 Ettus Research LLC USRP B210
uhd_find_devices          # -> serial
```

### Step 6 — custom GRC blocks

GRC reads block definitions from `~/.grc_gnuradio/`, not from the repo:

```bash
mkdir -p ~/.grc_gnuradio
cp coupled/secuecom/COUPLING/version1/deps/grc_blocks/*.block.yml ~/.grc_gnuradio/
```

Then fix the TETRA path inside those YAMLs — see §3.3.

### Step 7 — build Module 1 and run

```bash
cd coupled/secuecom/COUPLING/version1/module1
mkdir -p build && cd build
cmake .. && make -j"$(nproc)"
cd ../.. && ./run_securecom.sh
```

`cmake` prints the UHD it picked — confirm **4.10**, not 4.1:

```
-- UHD Version  : 4.10.0.0-0-g2af4ddb9
```

---

## 5. Running

```bash
./run_securecom.sh                 # defaults, opens browser
./run_securecom.sh --dwell-dmr 20  # long DMR dwell (see §6.3)
./run_securecom.sh --gain 30       # RX gain
./run_securecom.sh --no-browser    # headless / remote X
./run_securecom.sh --stop          # shut everything down
```

Console: http://127.0.0.1:8788 — header should read
`LIVE — real IQ + real decode/audio`.

Logs: `/tmp/securecom_v1/{bridge,http,build}.log`
Recordings: `COUPLING/version1/gui/recordings/`

Steps 6 and 7 of the launcher are driven through the bridge's WebSocket, not
started directly — the bridge owns those processes, and starting them behind its
back desyncs the console.

---

## 6. Tuning — what changed, what is measured, what is not

### 6.1 Squelch — SUPERSEDED 2026-10-26 (now −73 dB per protocol; see README §5)

`squelch_thresh`: **-30 dB → -20 dB** in `allinone.py` and `allinone.grc`.

One shared variable drives all 36 squelch blocks
(`analog.simple_squelch_cc(threshold_db, 0.05)`) across DMR, NXDN, P25 and TETRA.
Signal power must exceed the threshold for audio to pass; a **less negative**
threshold is a **stronger** squelch.

Verified 2026-09-15 with a long DMR dwell so nothing was masked:

| Condition | Result |
|---|---|
| Radio idle | 100% of frames fully muted, pure digital zero |
| Radio keyed | Voice passes; 8% of frames above the -38 dBFS voice line |

Idle vs keyed came out essentially binary — 90.9% silent, 8.0% voice, ~1% in
between. That in-between band is where noise used to leak.

**Caveat:** verified on **DMR only**. NXDN, P25 and TETRA share this variable and
have never been tested at -20 dB. If a protocol is silent in Delhi, try -30 first.

### 6.2 Volume — SUPERSEDED 2026-10-26 (now per protocol, DMR 0.2 / NXDN 0.5 / P25 0.5; see README §5)

`volume`: **0.5 → 0.04**, and the slider range floor **0.1 → 0.01** (0.1 was
itself too loud to reach a clean level).

Why: decoded audio was clipping hard. Measured off recordings:

| Recording | Peak | Clipped samples |
|---|---|---|
| `dmr_20260915T160903.wav` | 0.0 dBFS | 1.98% |
| `dmr_20260915T160950.wav` | 0.0 dBFS | 5.75% |
| `dmr_20260915T161055.wav` | 0.0 dBFS | 6.76% |

Peaks pinned at exactly 0.0 dBFS; the raw tap peaked at **+18.2 dBFS** — roughly
18–20 dB over full scale, chopped flat going into 16-bit PCM. Harsh, crackly
voice that no squelch setting can fix.

**0.04 was calculated, never heard.** The confirming test never caught a
transmission. To verify or re-tune in Delhi:

```bash
# with the stack up and a radio keyed, watch the DMR audio tap
python3 - <<'PY'
import numpy as np, zmq, time
s = zmq.Context().socket(zmq.SUB); s.connect('tcp://127.0.0.1:9101')
s.setsockopt(zmq.SUBSCRIBE, b''); s.setsockopt(zmq.RCVTIMEO, 500)
blocks=[]; t0=time.time()
while time.time()-t0 < 30:
    try: a=np.frombuffer(s.recv(), dtype=np.float32)
    except zmq.Again: continue
    if len(a): blocks.append(a)
if not blocks: raise SystemExit("no data on tap 9101 - is the decoder running?")
x=np.concatenate(blocks); pk=float(np.abs(x).max())
print(f"peak {20*np.log10(pk) if pk>0 else -120:.1f} dBFS  "
      f"clipping {np.mean(np.abs(x)>=0.999)*100:.2f}%")
PY
```

A reading of exactly **-120.0 dBFS with 0.00% clipping means silence** — nothing
was transmitted during the window. That is the "no signal" answer, not a level
answer. Key the radio and run it again.

Target: **peak around -3 to -6 dBFS, clipping 0.00%**.
- Peak near 0 dBFS or clipping > 0 → lower `volume`
- Peak below -25 dBFS → raise `volume`

Change it in `allinone.py` line ~95 (and `allinone.grc` to survive regeneration),
then restart the decoder.

### 6.3 Dwell rotation — the trap that produces false conclusions

Module 1 rotates DMR → NXDN → P25 → TETRA at **1.0 s each** by default
(`module1/src/main.cpp`), overridable per band:

```
SECURECOM_DMR_DWELL_SEC, SECURECOM_NXDN_DWELL_SEC,
SECURECOM_P25_DWELL_SEC, SECURECOM_TETRA_DWELL_SEC
```

Module 1 only reads these **at startup** — the bridge restarts it to apply a
change. The shared `GAP_SEC` is compiled in and needs a rebuild.

**The trap:** between dwells, Module 1 **zero-fills** the stream. An idle audio
measurement then reads 100% digital silence and looks like a perfectly working
squelch, when it is really just measuring zero-fill. This produced a wrong
conclusion during development.

**Always raise a band's dwell before judging its squelch, and confirm RF presence
on the IQ port alongside the audio tap.** Never judge the audio tap alone.

At 1 s dwells a band is only listening ~20% of the time, and part of each dwell
is lost re-acquiring lock — during a 70 s continuous transmission only ~9% of
audio came through. For focused single-protocol testing, give that band 15–20 s.

**For Delhi's multi-radio testing, leave dwells balanced** — the 20 s DMR dwell
used on this bench was for DMR-only work and starves the other three.

### 6.4 Frequencies — re-measure per radio

`module1/src/main.cpp`:

| Band | Configured | Port |
|---|---|---|
| DMR446 | 446.118528 MHz | 7001 |
| NXDN96 | 451.09375 MHz | 7002 |
| P25-Ph1 | 450.09375 MHz | 7003 |
| TETRA | 420.00000 MHz | 7004 |

**DMR446 is not a standard value.** It is 446.09375 **+24778 Hz**, measured
from the bench handheld's power centroid. That offset is **not crystal drift** —
it is a different channel. The bench radio is a **Sparrow D-446**, whose 16-channel
PMR446 plan is in `dmr_test/sparrow_dmr_nfm_decoder.py`: 446.09375 is channel 8,
and 446.118528 is channel 10 (446.11875) to within **-222 Hz / 0.5 ppm**.

Confirm which channel a radio is set to before assuming drift.

For each new radio, with the stack up and the radio keyed:

```bash
python3 tools/measure_signal.py --port 7001 --secs 30
```

It reports the real centre frequency. Put it in `main.cpp` and rebuild. Occupied
width ~8–10 kHz is normal for DMR/NXDN96/P25 in a 12.5 kHz channel; a symmetric
partner peak about DC is an IQ image, not a second transmission.

### 6.5 RX gain and ADC overload

Default 40 dB. During testing, RF frames were seen hitting **+0.8 dBFS** — at the
ADC rail. Front-end overload distorts the demodulator itself, and no squelch or
volume tuning cleans that up.

```bash
./run_securecom.sh --stop        # required: this tool opens the USRP directly
python3 tools/rf_level_probe.py  # sweeps gain, reports the highest clean setting
```

Note: DMR/NXDN/P25/TETRA are constant-envelope 4FSK, so **high RMS is normal and
is not by itself evidence of clipping.** Judge by peak and by the fraction of
samples near full scale. A real bench reading of -5.6 dBFS RMS with peak 0.88 and
0.00% above 0.95 was hot but perfectly clean — cutting gain on the RMS alone
would have been a mistake.

### 6.6 Measured reference values (bench, 2026-09-15)

| Quantity | Value |
|---|---|
| DMR noise floor (IQ, port 7001) | **-75 dBFS** |
| Keyed transmission above floor | ~75 dB |
| Recording "voice present" label line | -38 dBFS (`REC_ON_DBFS`) |
| Channels per protocol | DMR 16, NXDN 16, P25 10 |
| Squelch smoothing alpha | 0.05 |

The ~75 dB gap between noise floor and signal is why squelch separation is easy
once the threshold is in the right place.

---

## 7. Delhi test procedure, per radio

For each new radio type:

1. **Confirm RF arrives.** Stack up, radio keyed, watch the band's IQ port. If
   nothing is 20 dB above the noise floor, it is a frequency/antenna problem —
   stop and fix that before touching squelch or volume.
2. **Find the real frequency** — §6.4. Update `main.cpp`, rebuild, restart.
3. **Give that band a long dwell** while testing it (§6.3), so you are not
   measuring zero-fill.
4. **Check gain** is not overloading — §6.5.
5. **Check the audio level** — §6.2. Fix clipping before judging voice quality.
6. **Then** judge squelch. Idle should be silent; keyed should pass voice.
7. Save a recording and listen to it, rather than trusting the level numbers.

Always measure RF and audio **together**. A silent audio tap usually means
nothing was transmitted, not a bad setting — that mistake cost several test
cycles here.

---

## 8. Diagnostic tools (`COUPLING/version1/tools/`)

These found this project's real bugs.

| Tool | Needs stack | Purpose |
|---|---|---|
| `measure_signal.py` | **UP** | Real transmit frequency + occupied bandwidth. Found the 25 kHz offset bug |
| `rf_level_probe.py` | **STOPPED** | Gain sweep, clipping verdict. Opens the USRP directly |
| `dwell_probe.py` | UP | Audio level and TCP backlog across a dwell |
| `offline_decode_test.py` | either | Decode verification with no radio at all |
| `testdata/dmr_real_capture.cf32.gz` | — | Real DMR capture for offline testing |

`offline_decode_test.py` with the bundled capture is the fastest way to prove the
decoder chain works on a fresh machine before any radio is involved.

---

## 9. Troubleshooting

| Symptom | Likely cause |
|---|---|
| "No UHD Devices Found" while running | Normal — Module 1 owns the radio (§3.2) |
| Console says RUNNING but no audio | Stale process holding 9101; kill leftovers and restart |
| TETRA import error on a new machine | Hardcoded path, §3.3 |
| `import dsd` fails | gr-dsd-ext not built/installed, §4 step 4 |
| Signal visible on spectrum, no decode | Frequency offset — §6.4 |
| Voice harsh/crackly | Clipping — §6.2, not a squelch problem |
| Voice inaudibly quiet | `volume` 0.04 overcorrected — §6.2 |
| Idle looks perfectly silent | May be dwell zero-fill, not squelch — §6.3 |
| Only ~20% of a transmission decodes | Dwell too short — §6.3 |
| Radio enumerates but won't initialise | Missing FPGA images — §4 step 3 |

Manual pipeline check:

```bash
ss -ltnp | grep -E ':(700[1-4]|910[1-5]|8787|8788)\b'   # ports
ps aux | grep -E 'allinone|securecom_module1|bridge_server' | grep -v grep
tail -40 /tmp/securecom_v1/bridge.log
```

Expect 4/4 IQ ports (7001-7004) and 5/5 taps (9101-9105) when fully up.

---

## 10. State at handoff

**Uncommitted** in `delhi_testing/coupled` at time of writing: `README.md`,
`allinone.grc`, `allinone.py` — the squelch and volume changes plus README
documentation. Commit before shipping.

**Verified working:** squelch at -20 dB on DMR; full pipeline start-to-audio;
recordings; the three-process architecture end to end.

**Not verified:** the `volume = 0.04` setting (§6.2); NXDN, P25 and TETRA at the
new squelch value; any radio other than the one DMR handheld; the hardcoded TETRA
path on a machine other than this one.

**Known-good reference:** git history in `delhi_testing/coupled`, and the
recordings in `COUPLING/version1/gui/recordings/` from 2026-09-15, which are real
decoded DMR audio — though clipped, per §6.2.
