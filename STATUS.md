# SecureCOM COUPLING — Status

Living status of the work: what is done, what is in progress, what has not started.
Updated with every verified change. Settings and the reasons behind them are in
`README.md` §5; how to test is in `README.md` §9.

**Last updated:** 2026-10-27 (step 2: 8 protocols built and running; NXDN48 verified on a real recording)

---

## The plan

| # | Step | Status |
|---|---|---|
| 1 | Get the 4 protocols (DMR, NXDN, P25, TETRA) working properly | **Done** (user sign-off 10-27), open items below |
| 2 | Add 4 more protocols (NXDN48, D-STAR, X2-TDMA, ProVoice) | **In progress** — built and running; voice verified for NXDN48 only |
| 3 | Finalize the backend (freeze ports and message formats) | Not started |
| 4 | Finalize the UI | **In progress** — yesterday's 4-protocol console restored; 8-band version kept separately |
| 5 | Convert to C++ (Module 1 already is; decide the scope first) | Not started |

`docs/DELHI_HANDOFF.md` is a copy of `delhi_testing/DELHI_HANDOFF.md`, refreshed on every push.

Outside the plan but needed: a Delhi field test with IQ capture (real NXDN/P25/TETRA
frequencies and levels), and deciding which tree is canonical (this Delhi copy vs the
8-protocol bench tree).

---

## Step 1 — the 4 protocols

### Per protocol

| | DMR | NXDN96 | P25 Phase 1 | TETRA |
|---|---|---|---|---|
| Decode chain | 1 chain (was 16) | 1 chain (was 16) | 1 chain (was 10) | unchanged (1 chain) |
| Decodes a real recording | ✅ | ✅ 14.2 of 15.3 s | ✅ **syncs** (control channel, no voice) | ✅ 25 s voice in 40 s |
| Live, real radio | ✅ handheld, 12.2 s voice / 9 dwells | — no radio | — no radio | — no radio |
| Live over HackRF cable | — | ✅ every second on air | ✅ signal arrives, no voice in the sample | ✅ 31 s voice / 80 s, 23 call-log events |
| Over the air (HackRF, antennas) | — | ✅ 18.5 s voice / 31 s |
| **Voice verified** | ✅ | ✅ | ❌ **no P25 voice recording yet** | ✅ |
| Demod gain | 1.0 | 1.0 (was 7.28 → silent) | 1.0 (4.24 → 0 syncs) | n/a |
| Frame mode | DMR_MOTOTRBO | NXDN96 | P25_PHASE_1 | n/a |
| Squelch | −73 dB (live) | −73 dB (cable) | −73 dB (not voice-verified) | n/a |
| Volume | 0.2 (live: 0.5 clipped) | 0.5 | 0.5 | fixed (0.001% clipped) |
| Centre frequency | 446.118528 MHz, measured | 451.09375, **not measured on a real radio** | 450.09375, **not measured** | 420.0 placeholder; decoder offset −1.714 kHz is the recording's |

### System

| Item | Status |
|---|---|
| Module 1 survives USB errors; bridge detects a dead Module 1 and restarts it; UI shows it | ✅ 5-min soak: 3 failures, each recovered in ~2 s |
| Console status arrives live (was ~20 s late) | ✅ |
| Launcher reads the B210's own USB speed | ✅ |
| No hardcoded `/home/shankar` TETRA paths; `grcc` regenerates cleanly | ✅ |
| B210 on USB 3 (5000 Mbps) | ✅ port 2-10, 0 USB errors since |
| Long soak (30+ min) with the new decoder | ❌ not done |
| Squelch/volume checked by ear for NXDN/P25/TETRA | ❌ only by measurement |
| Console ACTIVE/recording threshold adapts to each band's noise floor | ✅ NXDN learned −69.2 dBFS with an antenna; room noise stays `idle` |

---

## Step 2 — the 4 new protocols

Built the same way as step 1 (one chain per protocol), each with its own channel plan,
from the protocol standards and DSD's own symbol timing at 48 kHz.

| | NXDN48 | D-STAR | X2-TDMA | ProVoice (EDACS) |
|---|---|---|---|---|
| Channel / modulation / rate | 6.25 kHz, 4FSK, 2400 baud | GMSK, 4800 baud | 12.5 kHz, 4FSK, 4800 baud | 25 kHz, GFSK, 9600 baud |
| Channelizer in 200 kHz | 32 × 6.25 kHz | 16 × 12.5 kHz | 16 × 12.5 kHz | 8 × 25 kHz |
| Channel rate → 48 kHz / LPF | ×192/25, 3 kHz | ×96/25, 6.25 kHz | ×96/25, 6.25 kHz | ×48/25, 9.5 kHz |
| DSD frame / mod | NXDN48_IDAS / GFSK | DSTAR / GFSK | X2_TDMA / C4FM | PROVOICE / GFSK |
| Port / tap | 7005 / 9106 | 7006 / 9107 | 7007 / 9108 | 7008 / 9109 |
| Frequency | 451.00625 (placeholder) | 439.4125 (placeholder) | 452.0 (placeholder) | 453.0 (placeholder) |
| Squelch / volume / gain | −73 / **3.0** / 1.0 | −73 / 0.5 / 1.0 | −73 / 0.5 / 1.0 | −73 / 0.5 / 1.0 |
| **Voice verified** | ✅ real recording | ❌ only a synthetic sample | ❌ no recording | ❌ no recording |

Built with `tools/add_protocols.py` (clones the DMR chain); `tools/layout_grc.py` lays
`allinone.grc` out as one row per protocol (layout only — generated code identical).

## Test results log

Newest first. Numbers are measured, not estimated.

| Date | What | Result |
|---|---|---|
| 10-28 | HackRF replay as a GRC flowgraph (`tools/hackrf_replay.grc`) | same chain as hackrf_replay.py, editable in GRC 3.10 with Parameter blocks; compiles with grcc; no-RF check (memory sink): exactly 2,000,000 samples per second of run, signal at +500.1 kHz, stops by itself, CLI options exposed. **Not yet run on the HackRF itself** |
| 10-28 | Air/maritime Module 1: USB-error recovery ported | drain after stop + per-band catch + exit code 3; a 60 s AIS dwell followed by ADS-B (the case that crashed with LIBUSB_TRANSFER_OVERFLOW) now completes its full 6,000,000 ADS-B samples, 0 USB errors, same process alive, on the 5000 Mbps link. The crash was software, not USB 2.0 |
| 10-28 | Air/maritime AIS centre corrected 162.025 -> 162.000 MHz | the decoder demodulates channels at -/+25 kHz from the tuned centre (161.975/162.025); tuned to 162.025 it looked at 162.000/162.050, neither an AIS channel. Changed in Module 1, bridge and console. **AIS decode through the HackRF still unverified** (0 messages in every test so far); ADS-B decodes (83 messages in a TCP replay, 61 offline) |
| 10-28 | `airmaritime/tools/replay_iq_tcp.py` | serves recorded AIS (7009, 250 kSps) / ADS-B (7010, 2 MSps) IQ so the live decoder -> bridge -> map chain can be proven without a radio |
| 10-28 | Added Air & Maritime (AIS + ADS-B) as a standalone subsystem | copied verbatim from the 1stversiondone repo (no terrestrial pulled in): decoders, bridge (ws 8887), Leaflet map console + offline tiles (8080). Own air-only Module 1 (AIS 250 kSps/162.025 MHz/7009, ADS-B 2 MSps/1090 MHz/7010), built on UHD 4.10. Verified: builds, bridge/tiles/console come up, map renders, bridge connects. Not on-air yet (needs B210 on 162/1090 MHz + antennas). Lives in version1/airmaritime/ with run_airmaritime.sh; run this OR the terrestrial stack |
| 10-27 | Fix: audio meters now decode-driven for all 8 bands | two updaters conflicted — handleRealAudio set each meter from decoded audio, but feedFrame overwrote all meters with raw IQ energy every 90 ms, so only DMR (strong signal + 15 s dwell) ever showed a bar. feedFrame now uses the decoded-audio level (decaying to 0 when stale). Bridge confirmed sending audio for 7/8 bands continuously (TETRA only while decoding); verified the meter responds per band |
| 10-27 | Console: replaced free-dragging with resizable borders (user's choice) | 5 splitter bars on the grid borders: sidebar width, spectrum/waterfall and waterfall/time heights, main/bottom height, audio/log width. Hover highlights the border; drag resizes, with min clamps. Verified live: dragging the sidebar border changed the column sizes |
| 10-27 | Console: every panel/plot is a draggable floating window | each of the 6 panels (spectrum, waterfall, time, the tabbed panel, audio, log) has a grip; drag pops it out as a fixed window at its size, double-click docks it back. Verified live: 6 grips, drag moves exactly, dock resets |
| 10-27 | Recordings: play button is a play/pause toggle | clicking ▶ plays and turns to ⏸ with a m:ss / m:ss time readout; clicking ⏸ pauses; only one recording plays at a time; resets to ▶ at the end. Verified live |
| 10-27 | Console spectrum + waterfall restyled to the Decodio reference | spectrum: black, yellow trace, dBm scale on both sides, per-carrier grey markers (channel no. + level on occupied ones); waterfall: blue->cyan->green->yellow->red heat scale with a dB colour bar. Same real IQ/channel data as before, front-end only; verified live, no page errors |
| 10-27 | Yesterday's console + the 4 new bands (same look, muted colours) | 8 bands in Signals/legend/audio/schedule; frequency axis 419–454 MHz; header on one line. **USB link now measured** (bridge reads the B210's sysfs speed after the firmware loads; was a fixed 'USB 3.0' string): shows USB 3.x (5000 Mb/s). **TCP clients** now 'ports with a client / 8 (connections)': 8 / 8 (16) |
| 10-27 | Bridge IQ-reader leak fixed | readers exit when their Module 1 run ends; after a schedule restart exactly 2 connections per port (decoder + bridge), was growing (4 per port seen) |
| 10-27 | DMR dwell 15 s, others 1 s (user's demo setting) | applied; Module 1 sends 3,000,000 samples (15 s) per DMR dwell |
| 10-27 | Console: back to yesterday's 4-protocol page (user's choice) | `gui/securecom_gui.html` restored byte-identical to the pre-step-2 version; today's 8-band page kept as `gui/securecom_gui_8band.html`. Works against the 8-band bridge (it ignores the 4 new bands), no page errors |
| 10-27 | **8-band stack on USB 3** (B210 back on port 2-10, 5000 Mbps) | 60 s: 29 dwells across all 8 bands, **0 USB errors, 0 Module 1 restarts**, live IQ from every band (36–48 frames each). On USB 2.0 (port 1-8) earlier the same stack hit LIBUSB_TRANSFER_ERROR within seconds and restarted repeatedly |
| 10-27 | One colour per band, same in decoder window and console | Qt spectrum: 8 traces (all bands); Qt audio plot: 7 DSD traces (TETRA keeps its own 8 kHz plot), rate fixed 200 kSps → 48 kHz (time axis was ~4× short). GRC allows only named Qt colours, so both use: DMR blue, NXDN96 red, P25 green, TETRA black, NXDN48 magenta, D-STAR cyan, X2-TDMA dark red, ProVoice dark blue. Console served no-cache (browser had kept the old page) |
| 10-27 | **8-band stack live** (B210, receive only) | 8/8 IQ ports, 9/9 taps; Module 1 rotates all 8 bands (~2 s each); bridge gets live IQ from all 8 with the right channel plans (NXDN48 32×6.25 kHz, ProVoice 8×25 kHz) |
| 10-27 | NXDN48 recording through the real decoder (replayed on 7005) | **28.2 s voice in 32 s**, −39 dBFS rms, −5 dBFS peak, 0% clipped at volume 3.0; other 7 taps silent as they should be; decoder 91% of one core |
| 10-27 | NXDN48 recording decoded directly by DSD (frame log) | `Sync: -NXDN48 … VOICE` with error-free frames, input level 42–46%; same 16.8 s at demod gain 0.5/1/2; DSD output peaks only −16 dBFS (quiet speech) → volume 3.0 |
| 10-26 | **Root cause of the over-the-air NXDN drop-outs** | the **HackRF's USB link fails while it radiates**: 14 disconnects on port 1-8 since 18:20 with `error -71`, worsening with TX gain (4 in 23 s at gain 30); a live capture had **2 ms holes every ~6 ms** (15.6% of the time >20 dB down), and it decoded only 1.32 s / 12.2 s even offline. With the HackRF idle: **0 disconnects in 3 min**. Over the cable it never happened. Over-the-air testing stopped; cable is the test path |
| 10-26 | NXDN over the air, HackRF continuous at **gain 30**, amp off | **36.0 s voice in 60 s** in 5 bursts, −22.5 dBFS rms, 0% clipped |
| 10-26 | NXDN over the air at gain 20 later in the session | dropped to 1–17 s / 60 s. *First read as room fading — **corrected below**: it was mostly HackRF transmit dropouts.* Measured then: 10 ms level median −52.8 dBFS but 1% of frames at −67 (the noise floor), 6% >10 dB below median; signal also moved 17 dB between minutes (antennas/people moving). Stream, decoder, squelch and RX gain all checked fine (TCP queues 0, decoder restart only partly helped) |
| 10-26 | HackRF USB resets on port 1-8 (18:20, 18:51) | transmitter silently stuck on the dead device; a keepalive now restarts it within ~6 s. Consider another USB port/cable for the HackRF |
| 10-26 | NXDN over the air, HackRF continuous, gain 20, amp off, NXDN dwell 30 s, adaptive activity threshold | **27.8 s voice in 59.5 s** (−42.8 dBFS band level), console `DECODING`, 8 dwell recordings with voice, 0% clipped |
| 10-26 | Console showed NXDN `idle` over the air and recorded nothing | fixed absolute −60 dBFS threshold sat 2 dB above room noise; now per-band adaptive (floor + 6 dB) |
| 10-26 | **NXDN over the air**, UHF (DMR radio) antennas both sides ~0.5 m, HackRF gain 20, amp off, 40 s | **18.5 s voice in 31 s**, −44.5 dB in channel (~29 dB over room noise), −24 dBFS rms, 0% clipped |
| 10-26 | NXDN over the air, same antennas, HackRF gain 0 | signal arrives (+10 dB, −63.5 dB) but only ~10 dB over room noise: no voice |
| 10-26 | UHF antenna on B210, nothing transmitting | band −62.2 dBFS (was −78.1 with the first antennas): antenna now picks up the room |
| 10-26 | **Over the air** (antennas both sides, ~0.5 m), NXDN, HackRF gain 0 / 20 / 30, amp off, 40 s each | **nothing received**: NXDN channel −84.7 / −84.7 / −84.4 dB, same as no signal. DMR handheld at 0.5 m also nothing. B210 antenna most likely not on RX2 (RF A). |
| 10-26 | Clear-channel check, receive only, all 4 test frequencies | all clear (−78 dBFS, flat noise) |
| 10-26 | HackRF over-the-air stop | **bug**: `timeout 75` left it transmitting for 2+ min (osmosdr stop hung). Fixed: `--duration` + 3 s force-exit watchdog; verified 3× (stops itself at 42 s) |
| 10-26 | TETRA over HackRF cable, 420 MHz, `--swap-iq --ppm -6.24`, gain 20 | 31.0 s voice in 80 s, 23 call-log events, 0% clipped |
| 10-26 | TETRA chain, coupled (200k/5) vs standalone (48k/1), swapped I/Q | identical: 39 syncs, 25.0 vs 24.9 s voice |
| 10-26 | P25 frame mode/gain on the real P25 recording (30 s) | P25_PHASE_1 1.0: 1088 syncs; AUTO_DETECT 1.0: 1089; gain 4.24: 0 |
| 10-26 | NXDN over HackRF cable, 451.09375 MHz, gain 20 | 23.5 s voice in 39 s (all on-air time), −22 dBFS rms |
| 10-26 | NXDN over cable without ppm correction | no voice — HackRF 6.24 ppm low (−2.8 kHz) |
| 10-26 | DMR live, handheld, squelch −73 | clean voice, less noise (user, by ear) |
| 10-26 | DMR live, handheld, new decoder, volume 0.5 | 12.2 s voice / 9 dwells, 2 recordings clipped (0.3–0.5%) |
| 10-26 | Replay through burst schedule, old vs new decoder | NXDN none → 18.5 s; DMR −48 → −26 dBFS; CPU 262% → 62% |
| 10-26 | 5-min soak, 10 s DMR dwell, USB 2.0 link | 71 dwells, 3 USB failures, all auto-recovered |

---

## Open issues

0c. **D-STAR, X2-TDMA and ProVoice need real recordings** to verify voice; their frequencies are placeholders.
0d. **The B210 must be on USB 3** (port 2-10, 5000 Mbps; the launcher reports it). On USB 2.0 Module 1 fails within seconds. In its bootloader stage it always shows 480 Mbps first; check the speed after the launcher has loaded the firmware.

0. **Over-the-air HackRF tests are unreliable**: its own radiated RF breaks its USB link (dropouts, then resets). Test through the cable + attenuator. Over-the-air is stopped.
0b. ~~**Bridge leaks IQ readers**~~ fixed 10-27 —: every schedule/gain change starts new per-port readers without stopping the old ones (4 per port after a few changes). Stream not stalled (send queues 0), but it wastes CPU and must be fixed in step 3.

1. **No P25 voice recording.** `(IQ)P25 Trunked Channel.wav` is a control channel
   (TSDU only); `SDRSharp_…_IQ.wav` turned out to be DMR. Need a P25 voice sample.
2. **Real frequencies** for NXDN, P25 and TETRA are placeholders until measured on real
   signals (Delhi). TETRA's decoder offset (−1.714 kHz) must be set per carrier.
3. **30-minute soak** with the new decoder not yet run.
4. **The UI's Schedule tab** shows a Gap column that does nothing (gap is compiled in).
5. **tetra-kit segfaults at end of a file.** Harmless live (the stream never ends), but
   offline tests must loop and pace their input.

## Sample notes

* `P25/SDRSharp_20160101_231914Z_*_IQ.wav` (also under `DMR/`) is **DMR**.
* `P25/(IQ)P25 Trunked Channel.wav` is P25 Phase 1 control channel, no voice.
* `TETRA/TETRA IQ.wav` stores **Q left / I right** — use `--swap-iq`.
* `DSTAR/DSTAR_GMSK_4.8k_IQ.wav` is synthetic (random bits) and can never decode.

## Commits

| Commit | What |
|---|---|
| (this) | STATUS: step 1 closed, over-the-air dropout root cause, bridge reader leak |
| `e8fedfe` | STATUS: over-the-air NXDN at gain 30 |
| `8397961` | Bridge: per-band adaptive activity threshold |
| `1e6e4b7` | NXDN decodes over the air |
| `3d6d704` | HackRF `--duration` + stop watchdog |
| `2fbd486` | STATUS.md added; DELHI_HANDOFF.md updated and copied to `docs/` |
| `abe98dc` | TETRA validated over RF; swapped I/Q explained; tap_audio 8 kHz fix |
| `41b8420` | NXDN validated over RF; P25 back to P25_PHASE_1; HackRF replay + bench tools |
| `351e671` | DMR volume 0.5 → 0.2 |
| `cb3c0f9` | DMR squelch −20 → −73 |
| `d91127a` | One decode chain per protocol; NXDN/P25 gains fixed; per-protocol squelch/volume |
| `8548d5b` | Baseline: USB recovery, auto-restart, launcher speed check, path fixes |

## Over-the-air testing

Done on 2026-10-26 under the user's authorization (defence test, closed room): clear-channel
check first, HackRF amp off, timed transmissions with `--duration`. The first antennas (black
hinged, Wi-Fi style) added nothing — the B210's noise floor was the same as with no antenna,
consistent with RP-SMA plugs on SMA jacks (no centre contact). With UHF antennas from the
DMR radios, NXDN decoded over the air at HackRF gain 20. **Use UHF antennas; check the
noise floor rises when one is fitted.** Over-the-air testing was then stopped: the HackRF's
USB link fails while it radiates (see the results log), so the cable is the test path.

Not done, on purpose: transmitting the HackRF into antennas would radiate on 420–451 MHz,
the bands of real NXDN/P25/TETRA networks, and needs a licence (WPC in India). Use the
cable + attenuator (equivalent for the decoder), a shielded RF box, or receive-only
against real radios.
