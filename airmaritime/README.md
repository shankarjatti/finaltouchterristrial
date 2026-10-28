# SecureCOM — Air & Maritime (AIS + ADS-B)

A standalone subsystem, separate from the terrestrial `version1` stack. Copied from the
`1stversiondone` reference (the air/maritime work was already proven); nothing terrestrial is
pulled in. One B210, one Module 1 at a time — run **this or** the terrestrial
`run_securecom.sh`, never both (both open the radio).

## Run
```bash
cd .../version1/airmaritime
env PATH=/usr/local/bin:/usr/bin:/bin ./run_airmaritime.sh      # --no-browser, --stop, --dwell-ais N, --dwell-adsb N
```
Console: http://127.0.0.1:8790/airmaritime_console.html  ·  map tiles: http://127.0.0.1:8080

## Pieces
| File | Role |
|---|---|
| `module1/` | C++/UHD backend, **AIS + ADS-B only**, per-band hardware rate (AIS 250 kSps @ 162.000 MHz → TCP 7009; ADS-B 6 MSps @ 1090 MHz → TCP 7010) |
| `airmaritime_decoder_live.py` | live decoder: reads 7009/7010, uses `gnuradio.ais`, `modes_demod.py` + `gnuradio.adsb`'s decoder, publishes messages on ZMQ 9201 (AIS) / 9202 (ADS-B) |
| `modes_demod.py` | Mode-S demodulator block (replaces gr-adsb's framer + demod) |
| `adsb_cpr.py` | validated CPR position decoding (used by the bridge) |
| `airmaritime_decoder.py` | offline regression reference (reads bundled WAVs) |
| `airmaritime_bridge.py` | tracks vessels/aircraft, serves WebSocket **8887**, spawns the live decoder |
| `gui/airmaritime_console.html` | Leaflet map + RF spectrum console |
| `mbtiles_server.py`, `world_zoom12.mbtiles` | offline map tiles on **8080** |
| `tools/replay_iq_tcp.py` | feeds recorded AIS/ADS-B IQ to ports 7009/7010 — proves decoder → bridge → map with no radio |
| `run_airmaritime.sh` | standalone launcher |

## Changes made after copying (everything else is verbatim from 1stversiondone)
- `module1/`: USB-error recovery from the terrestrial Module 1 (drain after stop, per-band
  catch, exit code 3 after 5 failures in a row, non-throwing stop in the destructor so a
  replugged B210 no longer aborts the process).
- AIS centre **162.000 MHz** (was 162.025): the decoder's two channels sit at ∓25 kHz from the
  tuned centre, i.e. 161.975 and 162.025.
- **AIS demod fixed** (it had never decoded a frame): NRZI decode added (`diff_decoder_bb(2)`
  before `ais.invert`); correct symbol timing (250 kSps / 5 = 50 kSps = 5.208 samp/sym; the
  live decoder uses `AIS_SPS`, `airmarin.grc` resamples 50 → 48 kSps for exactly 5); the live
  decoder adds ±450/±900 Hz carrier-offset branches per channel (HDLC CRC rejects bad frames).
- **Bridge**: AIS PDUs are `(meta . u8vector)` — the sentence is in `cdr()`; it read `car()`
  and dropped every message. Duplicate frames from the offset branches are dropped (2 s window).
- **No fake / fallback data**: tile server serves only stored tiles (404 otherwise); console map
  opens on the world and frames the first real target at the deepest stored zoom; band state
  shows time since the last real decode; spectrum "DECODING" only after a real decode.
- `airmaritime_decoder.py` regenerated from `airmarin.grc` (grcc); its AIS input is now
  `all_protocols_wav_samples/AIS_Marine/ais_b210_cable_capture_250k.wav` (real B210 capture).
- `tools/replay_iq_tcp.py` added.
- **Positions** (`adsb_cpr.py`): gr-adsb's lat/lon are not used (bad CPR pairing); the bridge decodes
  positions from every raw CRC-valid frame (decoder → ZMQ **9203**): even/odd within 10 s, same NL zone,
  two agreeing decodes to confirm, then local decode with a 1000 kt plausibility limit.
- **No single-frame targets**: an ICAO needs 2 CRC-valid frames within 10 s, a vessel 2 messages within
  10 min. Targets expire: ADS-B after 60 s unheard, AIS after 10 min.
- **Module 1 TCP**: drops keep whole 8-byte samples (a mid-sample drop misaligned the stream for good);
  send buffer = 0.16 s of the band's rate. Live decoder: no Throttle on its TCP sources.
- **ADS-B demod replaced** (`modes_demod.py`): gr-adsb's framer used a fixed absolute threshold
  and its demod one sample per half-bit with no timing search (32 of 173 real frames passed CRC;
  0 decoded at 2 MSps). The new block uses a noise-relative preamble test, half-bit integration,
  timing search and CRC-24, and feeds gr-adsb's own decoder (CPR position, callsign, velocity).
  ADS-B now runs at **6 MSps** (Module 1, live decoder, bridge, console, `airmarin.grc` via an
  embedded Python block). Bridge spectrum reader skips backlog (48 MB/s); headings 0–360.

## Status
- **AIS verified end to end over a cable**: real AIS recording → HackRF (161.975 MHz, VGA 40,
  amp off) → SMA + attenuator → B210 → Module 1 → decoder → bridge → map. 38 map updates in
  85 s from 6 real vessels; markers and table checked in the console.
- `ais_marine_vessel_tracking_250k.wav` contains **no AIS** (Q ≈ 0, no CRC-valid frame) — do
  not use it for AIS tests. Use `AIS IQ.wav` (48 kHz, real) or the B210 capture.
- **ADS-B verified end to end over a cable**: real recording `1_ADS-B_LiveRecorded_2.4MSps.wav`
  → HackRF (1090 MHz, `--hackrf-rate 16e6 --offset 4e6`, VGA 20, amp off) → SMA + attenuator →
  B210 (6 MSps) → decoder → bridge → map: 501 messages / 80 s, 35 aircraft, 29 with position.
  Live 1090 MHz reception (antenna, receive only) not yet tried.
- The real recording holds **39 aircraft** (two independent decoders) and is not continuous: aircraft
  move 2.46× faster than their reported speed (≈60% of its samples were dropped when recorded).
- `adsb_sample_iq.wav` / `1_ADS-B_Synthetic_2.0MSps.wav` are synthetic (one fake aircraft) — not
  used anywhere now.
- Bundled map tiles: real only to zoom 6 over India.
- Hardware/Schedule tab needs the terrestrial bridge (8787); standalone it says "not connected".
