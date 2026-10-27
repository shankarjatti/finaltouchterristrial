# SecureCOM COUPLING — Status

Living status of the work: what is done, what is in progress, what has not started.
Updated with every verified change. Settings and the reasons behind them are in
`README.md` §5; how to test is in `README.md` §9.

**Last updated:** 2026-10-27 (step 1 closed; over-the-air dropout cause logged; step 2 starting)

---

## The plan

| # | Step | Status |
|---|---|---|
| 1 | Get the 4 protocols (DMR, NXDN, P25, TETRA) working properly | **Done** (user sign-off 10-27), open items below |
| 2 | Add 4 more protocols | **In progress** — planning |
| 3 | Finalize the backend (freeze ports and message formats) | Not started |
| 4 | Finalize the UI | Not started |
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

## Test results log

Newest first. Numbers are measured, not estimated.

| Date | What | Result |
|---|---|---|
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

0. **Over-the-air HackRF tests are unreliable**: its own radiated RF breaks its USB link (dropouts, then resets). Test through the cable + attenuator. Over-the-air is stopped.
0b. **Bridge leaks IQ readers**: every schedule/gain change starts new per-port readers without stopping the old ones (4 per port after a few changes). Stream not stalled (send queues 0), but it wastes CPU and must be fixed in step 3.

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
