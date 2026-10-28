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
  catch, exit code 3 after 5 failures in a row). A 60 s AIS dwell followed by ADS-B used to
  terminate Module 1 with `LIBUSB_TRANSFER_OVERFLOW`; it now completes (5000 Mbps link).
- AIS centre **162.000 MHz** (was 162.025): the decoder's two channels sit at ∓25 kHz from the
  tuned centre, i.e. 161.975 and 162.025. Module 1, bridge and console updated.
- `tools/replay_iq_tcp.py` added.

## Status
- Built; bridge (8887), tiles (8080), console and map verified. Module 1 holds AIS + ADS-B
  dwells on USB 3 with no errors.
- **ADS-B decodes:** 61 messages offline, 83 in a TCP replay (aircraft appear in the console's
  tracked-targets table).
- **AIS: not yet decoded in any test** (offline, TCP replay, over the HackRF). The centre-frequency
  fix above is untested on the air. Both are data (contacts), not audio: no `.wav`; output is the
  ships/aircraft tables and the map.
