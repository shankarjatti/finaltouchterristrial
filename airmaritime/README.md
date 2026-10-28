# SecureCOM — Air & Maritime (AIS + ADS-B)

A standalone subsystem, separate from the terrestrial `version1` stack. Copied
from the `1stversiondone` reference (the air/maritime work was already proven);
nothing terrestrial is pulled in. One B210, one Module 1 at a time — run **this
or** the terrestrial `run_securecom.sh`, never both (both open the radio).

## Run
```bash
cd .../version1/airmaritime
env PATH=/usr/local/bin:/usr/bin:/bin ./run_airmaritime.sh      # --no-browser, --stop
```
Console: http://127.0.0.1:8790/airmaritime_console.html  ·  map tiles: http://127.0.0.1:8080

## Pieces
| File | Role |
|---|---|
| `module1/` | C++/UHD backend, **AIS + ADS-B only**, per-band hardware rate (AIS 250 kSps @ 162.025 MHz → TCP 7009; ADS-B 2 MSps @ 1090 MHz → TCP 7010) |
| `airmaritime_decoder_live.py` | live decoder: reads 7009/7010, uses `gnuradio.ais` + `gnuradio.adsb`, publishes messages on ZMQ 9201 (AIS) / 9202 (ADS-B) |
| `airmaritime_decoder.py` | offline regression reference (reads bundled WAVs) |
| `airmaritime_bridge.py` | tracks vessels/aircraft, serves WebSocket **8887**, spawns the live decoder |
| `gui/airmaritime_console.html` | Leaflet map + RF spectrum console |
| `mbtiles_server.py`, `world_zoom12.mbtiles` | offline map tiles on **8080** |
| `run_airmaritime.sh` | standalone launcher |

## Status
- Built and the services verified up (bridge 8887, tiles 8080, console, map renders).
- **Not yet verified on-air**: AIS (162 MHz) and ADS-B (1090 MHz) decode needs the
  B210 tuned there with suitable antennas — a field/cable test. Both are data
  (contacts), not audio: no `.wav`, output is the ships/aircraft tables + map.
