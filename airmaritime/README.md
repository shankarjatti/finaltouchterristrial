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
| `module1/` | C++/UHD backend, **AIS + ADS-B only**, per-band hardware rate (AIS 250 kSps @ 162.000 MHz → TCP 7009; ADS-B 2 MSps @ 1090 MHz → TCP 7010) |
| `airmaritime_decoder_live.py` | live decoder: reads 7009/7010, uses `gnuradio.ais` + `gnuradio.adsb`, publishes messages on ZMQ 9201 (AIS) / 9202 (ADS-B) |
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

## Status
- **AIS verified end to end over a cable**: real AIS recording → HackRF (161.975 MHz, VGA 40,
  amp off) → SMA + attenuator → B210 → Module 1 → decoder → bridge → map. 38 map updates in
  85 s from 6 real vessels; markers and table checked in the console.
- `ais_marine_vessel_tracking_250k.wav` contains **no AIS** (Q ≈ 0, no CRC-valid frame) — do
  not use it for AIS tests. Use `AIS IQ.wav` (48 kHz, real) or the B210 capture.
- **ADS-B**: decodes the synthetic `1_ADS-B_Synthetic_2.0MSps.wav` only (61 offline, 83 TCP
  replay). Not yet verified on a real recording or live 1090 MHz.
- Bundled map tiles: real only to zoom 6 over India.
- Hardware/Schedule tab needs the terrestrial bridge (8787); standalone it says "not connected".
