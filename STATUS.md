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
| 10-29 | **X2-TDMA and ProVoice: second search, still no usable sample** | ProVoice clips: level histograms are single-peaked (speech-like), not two-level FSK; polarity-inverted re-test also 0 frames → not discriminator data. Checked for test data: `mbt25/dsd` `samples/` = two **P25** FLACs only; `arancormonk/dsd-neo` (supports both) commits no recordings (its test WAVs are generated in the build tree); `lwvmobile/dsd-fme` `examples/` = CSVs only; sigidwiki, BARRA, RadioReference: none. **Risk found in the DSD source:** DSD defaults `inverted_x2tdma = 1` ("most scanner/sound-card combinations show inverted signals"); gr-dsd's block exposes no inversion setting, and our GNU Radio FM demod gives the non-inverted polarity, so a real X2-TDMA signal may need the demod gain negated (`gain_demod_x2tdma = -1`) — cannot be decided without a real recording. X2-TDMA is also described as QPSK on the DSD wiki while the chain uses `dsd_MOD_C4FM`; unverified |
| 10-29 | **D-STAR verified on a real transmission, through the live stack** (sigidwiki `DStar_Sound.mp3`) | the MP3 is real off-air FM-**discriminator** audio (DSD decodes real headers: RPT WB7DZG B, MY KB7WUK H, CQCQCQ). Offline in DSD: 87 % voice. To send it through HackRF → cable → B210 it was FM-modulated to IQ (`web_protocol_samples/dstar/DStar_Sound_fm_iq_48k.wav`, ±1.2 kHz, **synthesised from the real discriminator signal: data real, RF channel not**; README in that folder). Live at 439.4125 MHz, D-STAR dwell 30 s: audio tap 9107 **32.3 s voice** in 100 s (−20.9 dBFS rms, 0 % clipped); same headers through the chain's own blocks at 3 demod gains; only D-STAR shows decoded voice |
| 10-29 | **Console showed D-STAR as idle / saved no recording while decoding** (bridge bug, not the cable or transmitter) | D-STAR RF level −41 dBFS (+37 dB over the other bands) flagged active in 8 of 755 frames: a band's noise floor was the 5th percentile of its OWN history, which in a 30 s dwell is all signal → floor rose to −45 dB. Fix in `gui/bridge_server.py`: floor capped at the quietest other band + 10 dB (cross-band reference from 10 frames). After: RF-active 696/696, two 30.4 s D-STAR clips saved with voice. 2/24 frames of the empty X2-TDMA band also flagged active — minor, watching |
| 10-29 | ProVoice clips tested | sigidwiki `Provoice.mp3` (68 KB) and BARRA `069/034/070.mp3` (92 KB / 589 KB / 1.08 MB) downloaded to `web_protocol_samples/provoice/`: **0 ProVoice frames** in DSD (ProVoice and auto-detect) — speech-like spectra, i.e. decoded/heard voice, not the 9600-baud data. **X2-TDMA: no sample exists** (sigidwiki page has no media, BARRA lists none, web search found only requests). ProVoice and X2-TDMA remain **unverified** |
| 10-29 | **No real IQ exists for D-STAR, X2-TDMA, ProVoice** | local `DSTAR_GMSK_4.8k_IQ.wav` (5 s, 48 kHz) is generated: |x| = 0.9999 ± 0.00001 (constant envelope, no noise) and DSD finds **0 D-STAR frames** in it at three demod gains. The other `dstar_*.wav` in version1 were made from an MP3, so they prove nothing. sigidwiki: D-STAR and EDACS/ProVoice pages list only images; no X2-TDMA page found (wiki search sits behind a bot check — not bypassed); DMR/NXDN/TETRA pages carry `DMR.zip`, `NXDN_IQ.zip`, `TETRA_IQ.zip`, probably the samples already used (not downloaded). D-STAR / X2-TDMA / ProVoice stay **unverified** until a real recording or radio is available |
| 10-29 | **P25 voice over the cable, whole live stack** (sigidwiki `P25-C4FM-VC_IF.wav` → HackRF 450.09375 MHz, VGA 20, amp off, ppm −6.24 → cable + attenuator → B210 → Module 1 → decoder → bridge) | P25 dwell 30 s, other bands 1 s. Audio tap 9103, 100 s: **35.7 s voice** (11 bursts), −25.6 dBFS rms, peak −4.9, 0 % clipped. Bridge/console recorder saved P25 clips of 5.7–5.8 s each dwell, all `had_audio`, peak −8…−13 dB. Envelope match of the live clips to the offline decode: 0.64 mean (time-reversed reference 0.49, shuffled 0.21 — only moderate evidence; the strong evidence is DSD syncing on real P25 frames). The 8787 bridge showed P25 `active_band`, 3 clients, 5000 Mbps USB. **The terrestrial console page itself was not opened in a browser (port 8788 was not permitted in the browser pane); its data feed was read from the bridge** |
| 10-29 | **P25 voice verified on a real recording** (sigidwiki `P25-C4FM-VC_IF.wav`, https://www.sigidwiki.com/images/2/25/P25-C4FM-VC_IF.wav, 1.14 MB, Motorola XTS5000, 24-bit I/Q at 24 kHz, 8.3 s) | the live P25 chain's blocks (x2 resample, LPF, FM demod, DSD P25 Phase 1), file looped 4×: per pass 1 HDU + 15 LDU1 + 14 LDU2 + 1 TDU, **NAC 293, talkgroup 1**, ≈5.2 s of voice; identical at demod gains 1.0 / 0.5 / 0.2; 33 s of 8 kHz audio out. Offline only: **not yet through HackRF → B210 → Module 1 → console** |
| 10-28 | Air console spectrum looked like pure noise while ADS-B decoded | the bridge FFT'd one 512-sample snapshot per 0.1 s (85 us of 100 ms) and missed nearly every 120 us Mode-S frame; Avg/Len/Refresh/AutoScale/MaxHold were not wired to anything; axis said dBm (uncalibrated). Now every sample of each 0.1 s is analysed (1171 FFTs/update at 6 MSps): average trace + peak-per-0.1 s trace (+ working MaxHold, Auto Scale, Avg); Len/Refresh removed; axis "dB". Live, synthetic aircraft over the cable: 163 updates / 20 s, noise floor −42.8 dB, bursts up to +3.6 dB, 83 of 163 updates show a frame >20 dB over the floor. Bridge CPU 22 %. Not yet looked at in the browser |
| 10-28 | Single-aircraft file over the cable (`1_ADS-B_Synthetic_2.0MSps.wav`, synthetic) | UI shows exactly 1 aircraft: A12345 / H81H, 38000 ft, 446 kt, hdg 114°, map marker at 46.26 N 3.44 E. The file's even and odd position frames encode two points 7.4 km apart (a real transponder cannot do that): the tracker now confirms from two decodes of the **same parity** and rejects the contradicting frames |
| 10-28 | Old aircraft never left the map | `broadcast()` iterated the live client set across awaits → RuntimeError killed `prune_stale()` silently. Fixed (iterate a copy; prune survives errors). Verified: HackRF stopped → aircraft removed after 61 s |
| 10-28 | **ADS-B: wrong positions, false aircraft and a garbage stream fixed** | live 90 s over the cable after the fixes: 725 map updates, 33 aircraft, 20 with position, **0 positions >300 km from London, 0 aircraft not in the recording, 0 Module 1 drops** |
| 10-28 | Real content of the ADS-B recording | one pass, two independent decoders: **39 aircraft** (modes_demod, 1,393 CRC-valid frames) / 38 (native-rate probe, all within the 39); 400981 is real but weak (2 frames, found by a sensitive search). The file is real but **not continuous**: every aircraft moves 2.46× faster than its own reported speed → 102 s of samples ≈ 250 s of flight (≈60% of samples dropped when it was recorded) |
| 10-28 | Wrong positions (Norwegian Sea, Atlantic, Germany, Italy) | gr-adsb's CPR pairs even/odd by whole-second wall clock with a 30 s window and its check (`(lat-prev)<0.1` twice, no abs, no lon) passes bad fixes. New `airmaritime/adsb_cpr.py`: pair only within 10 s (message time) and same NL zone, confirm by two agreeing global decodes, then local decode + max 1000 kt; gr-adsb lat/lon no longer used. On the recording: 377 fixes, all ≤142 km from London |
| 10-28 | False aircraft 34440B / 4008E6 | exist nowhere in the recording (sensitive search): single velocity frames that passed the 24-bit CRC by chance. Bridge now shows an ICAO only after 2 CRC-valid frames within 10 s; AIS vessels after 2 messages within 10 min (16-bit CRC × 10 branches) |
| 10-28 | ADS-B went to 0 decodes after a while | Module 1 dropped a slow client's remainder **mid-sample** → that client's complex64 stream misaligned for good (overflow warnings, garbage); the slow client was the live decoder, held back by a Throttle block on its live TCP source, with a 256 kB send buffer = 5 ms at 6 MSps. Fixed: drops keep whole samples (pending bytes per client), send buffer 0.16 s per band (ADS-B 7.7 MB), throttles removed from the live decoder. **The terrestrial Module 1 has the same TCP drop code** |
| 10-28 | Targets now expire | ADS-B removed after 60 s unheard, AIS after 10 min (bridge `adsb_remove`/`ais_remove`, console deletes marker + row) |
| 10-28 | **ADS-B decodes over the B210 and shows on the map** (HackRF → SMA cable + attenuator → B210, Module 1 at 1090 MHz, 6 MSps) | real recording `1_ADS-B_LiveRecorded_2.4MSps.wav` replayed wideband (HackRF 16 MSps, 4 MHz offset, VGA 20, amp off): **501 messages in 80 s, 35 aircraft, 29 with position, 500 map updates**; callsigns BAW2761, EIN239, RYR1KC, EJU46DN, VOE9269, NJE478Q, RCH145 …; console: 30 markers over southern England on real tiles. B210 level −50 dBFS. Same test driven by the GRC flowgraph `tools/hackrf_replay.grc` (`--hackrf-rate 16e6`): 384 messages / 55 s, 32 aircraft |
| 10-28 | **Root cause: ADS-B decoded 0 frames of a real recording** | (1) 2 MSps is too slow for 0.5 µs Mode-S pulses; (2) fixed absolute framer threshold (0.010 on |IQ|²) — level-dependent; (3) gr-adsb's demod samples one point per half-bit with no timing search: 173 DF17/18 frames → 32 pass CRC. New `airmaritime/modes_demod.py` (noise-relative preamble test, half-bit integration, timing search, CRC-24) feeding gr-adsb's own decoder: CRC-valid frames / 10 s of the real file **12 @ 2 MSps, 116 @ 4, 155 @ 6 MSps** (old chain at 2 MSps: 0). Runs at 0.43 s per second of 6 MSps. Module 1 ADS-B now 6 MSps (B210 clock 48 MHz, exact); bridge spectrum reader skips backlog; headings normalised 0–360 |
| 10-28 | ADS-B sample files | **only one real recording exists**: `1_ADS-B_LiveRecorded_2.4MSps.wav` = `adsb.2021-11-26T15_03_30_573.wav` (same file, 102 s, London). `adsb_sample_iq.wav` = `1_ADS-B_Synthetic_2.0MSps.wav` (synthetic, one fake aircraft `a12345`). The offline reference (`airmarin.grc`) now reads the real recording: 327 messages / 40 s, 28 aircraft |
| 10-28 | **AIS decodes over the B210 and shows on the map** (HackRF → SMA cable + attenuator → B210, Module 1 at 162.000 MHz) | real recording (`AIS IQ.wav`, sigidwiki) replayed on 161.975 MHz, TX VGA 40, amp off: **38 map updates in 85 s from 6 real vessels** (MMSI 538002019, 538002030, 222222222, 219380012, 11388, 232004345) at 57.0 N 10.0 E; console table + markers verified in the browser. B210 level −50 dBFS |
| 10-28 | **Root cause: AIS never decoded anywhere (3 bugs in the copied chain)** | (1) no NRZI decode — `ais.invert` only flips bits; added `digital.diff_decoder_bb(2)`; (2) symbol rate: 250 kSps / 5 = 50 kSps is **5.208** samp/sym, the flowgraph said 5 (clock recovery may drift only 0.5 %) — demod ran at 9,994 bit/s instead of 9,600; (3) bridge read `car()` of the `(None . u8vector)` PDU, so **every** decoded AIS sentence was dropped before the map. Measured on a 45 s B210 capture: old chain 0 frames, fixed 5 (one branch per channel) / **9 unique** (with ±450/±900 Hz carrier-offset branches; HackRF↔B210 offset measured 550 Hz). Independent CRC-checked Python demod: 7 |
| 10-28 | `ais_marine_vessel_tracking_250k.wav` is **not** AIS IQ | Q channel ≈ 0 (std 0.0004 vs I 0.557), mirror-symmetric spectrum; 0 CRC-valid frames at any offset, real or analytic. Every earlier "AIS: 0 decodes" test used this file. The user's `usrp_ais_offline_rx.py` on it also gives 0. Offline reference now uses `ais_b210_cable_capture_250k.wav` (real B210 capture, 5 unique frames offline) |
| 10-28 | No fake / fallback in the air console | tile server serves only stored tiles (404 otherwise; the generated "tactical grid" and enlarged parent crops are gone); map opens on the world and frames the first real target at the deepest real tile zoom (bundled DB: zoom 6 for Delhi/Denmark); fixed "ACTIVE" state replaced with time since last real decode; spectrum "SIGNAL" now means a real decode in the last 5 s; dwell detection from non-zero IQ (8787 is not running standalone); an undefined variable that threw on every spectrum redraw fixed |
| 10-28 | HackRF replay as a GRC flowgraph (`tools/hackrf_replay.grc`) | same chain as hackrf_replay.py, editable in GRC 3.10 with Parameter blocks; compiles with grcc; no-RF check (memory sink): exactly 2,000,000 samples per second of run, signal at +500.1 kHz, stops by itself, CLI options exposed. **Not yet run on the HackRF itself** |
| 10-28 | Air/maritime Module 1: USB-error recovery ported | drain after stop + per-band catch + exit code 3; a 60 s AIS dwell followed by ADS-B (the case that crashed with LIBUSB_TRANSFER_OVERFLOW) now completes its full 6,000,000 ADS-B samples, 0 USB errors, same process alive, on the 5000 Mbps link. The crash was software, not USB 2.0 |
| 10-28 | Air/maritime AIS centre corrected 162.025 -> 162.000 MHz | the decoder demodulates channels at -/+25 kHz from the tuned centre (161.975/162.025); tuned to 162.025 it looked at 162.000/162.050, neither an AIS channel. Changed in Module 1, bridge and console. AIS decode through the HackRF: verified later the same day, see above; ADS-B decodes (83 messages in a TCP replay, 61 offline) — on the synthetic file; real-recording result above |
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

0h. **Terrestrial Module 1 (`version1/module1/src/tcp_server.cpp`) still has the mid-sample drop bug** fixed in the air Module 1 on 10-28: a slow client gets a misaligned (garbage) stream after its first drop.

0e. ~~ADS-B verified only on a synthetic file~~ — fixed 10-28: real recording decodes over the cable. Still to do: live 1090 MHz reception in Delhi (receive only, antenna on the B210).
0f. **Air console Hardware/Schedule tab** talks to the terrestrial bridge (ws 8787), which `run_airmaritime.sh` does not start: it reports "not connected"; dwell is set by the launcher's `--dwell-ais/--dwell-adsb`.
0g. **Offline map tiles**: the bundled DB has real tiles only to zoom 6 over India; deeper zooms need real tiles downloaded for the operating area (`download_mbtiles.py`).

0c. ~~D-STAR~~ verified 10-29 (real transmission, see log). **X2-TDMA and ProVoice still need real recordings** (two searches, no public sample); their frequencies are placeholders, and X2-TDMA has an unresolved polarity/modulation question (see log 10-29).
0d. **The B210 must be on USB 3** (port 2-10, 5000 Mbps; the launcher reports it). On USB 2.0 Module 1 fails within seconds. In its bootloader stage it always shows 480 Mbps first; check the speed after the launcher has loaded the firmware.

0. **Over-the-air HackRF tests are unreliable**: its own radiated RF breaks its USB link (dropouts, then resets). Test through the cable + attenuator. Over-the-air is stopped.
0b. ~~**Bridge leaks IQ readers**~~ fixed 10-27 —: every schedule/gain change starts new per-port readers without stopping the old ones (4 per port after a few changes). Stream not stalled (send queues 0), but it wastes CPU and must be fixed in step 3.

1. ~~**No P25 voice recording.**~~ — real voice found 10-29 (sigidwiki, see log); over the cable through the live stack verified 10-29. Earlier: **No P25 voice recording.** `(IQ)P25 Trunked Channel.wav` is a control channel
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
