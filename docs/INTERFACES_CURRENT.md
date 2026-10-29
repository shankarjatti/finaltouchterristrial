# Interfaces as they exist today (CURRENT — captured 2026-10-29, NOT frozen)

Generated from the running system and the code. The point of this file is to know what the UIs, the core
and the IQ front end exchange today, so the publish/subscribe checks and the later freeze start from facts.

## 1. IQ front end → core (TCP, the "USRP side")

The core connects as a TCP **client** to each port; the front end is the server. Stream: `complex64` (8 bytes per
sample: float32 I, float32 Q, little endian), signal centred in the band, no header, no framing. The decoders use
`iq_tcp_source` (reconnects by itself within ~1-4 s when the source restarts; verified 2026-10-29).

### Terrestrial (200 kSps per port, 8 ports)
| port | band | centre (MHz) |
|---|---|---|
| 7001 | DMR446 | 446.118528 |
| 7002 | NXDN96 | 451.09375 |
| 7003 | P25-Ph1 | 450.09375 |
| 7004 | TETRA | 420.00000 |
| 7005 | NXDN48 | 451.00625 |
| 7006 | DSTAR | 439.41250 |
| 7007 | X2TDMA | 452.00000 |
| 7008 | PROVOICE | 453.00000 |

### Air & maritime
| port | band | rate | centre (MHz) |
|---|---|---|---|
| 7009 | AIS | 250 kSps | 162.000 (channels at 161.975 / 162.025) |
| 7010 | ADS-B | 6 MSps | 1090.000 |

## 2. Core → bridge (ZeroMQ PUB, bridge SUBscribes)

### Terrestrial decoder (allinone.py)
| port | content | format |
|---|---|---|
| 9101 | decoded audio, dmr | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9102 | decoded audio, nxdn | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9103 | decoded audio, p25 | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9104 | decoded audio, tetra | `float32` mono, 8000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9106 | decoded audio, nxdn48 | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9107 | decoded audio, dstar | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9108 | decoded audio, x2tdma | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9109 | decoded audio, provoice | `float32` mono, 48000 Hz, variable chunk sizes; exact silence (0.0) when nothing is decoded |
| 9105 | TETRA call-log events | PMT-serialised dict (see bridge `tetra_event`) |

### Air & maritime decoder (airmaritime_decoder_live.py)
| port | content | format |
|---|---|---|
| 9201 | AIS sentences | PMT pair `(meta . u8vector)`; the vector is the ASCII `!AIVDM,...` sentence |
| 9202 | ADS-B decoded | PMT pair `(dict . 112 bits)`; dict has icao, callsign, altitude, speed, heading, vertical_rate (gr-adsb lat/lon are NOT used) |
| 9203 | ADS-B raw frames | PMT pair `(dict{timestamp,snr} . 112 bits)`; every CRC-valid DF17/18 frame; the bridge decodes positions from these |

## 3. Bridge → UI (WebSocket, JSON text frames)

### Terrestrial — `ws://127.0.0.1:8787`

Commands the UI sends (`{"cmd": ...}`): `apply_gain`, `apply_schedule`, `delete_all_recordings`, `delete_recording`, `list_recordings`, `start`, `start_decoder`, `stop`, `stop_decoder`  — `apply_schedule {dwell:{band:s}}`, `apply_gain {gain_db}`, `delete_recording {file}`.
With `SECURECOM_EXTERNAL_IQ=1` (no Module 1) `start`, `stop`, `apply_schedule` and `apply_gain` are ignored.

#### `audio` (50609 per 40 s)
| field | type |
|---|---|
| `active` | bool |
| `band` | str |
| `pcm16` | str |
| `rate` | int |
| `rms_db` | float |
| `type` | str |
example: `{"type": "audio", "band": "dmr", "rate": 24000, "active": false, "rms_db": -120.0, "pcm16": "<str>"}`

#### `decoder_status` (1 per 40 s)
| field | type |
|---|---|
| `running` | bool |
| `type` | str |
example: `{"type": "decoder_status", "running": true}`

#### `iq` (3189 per 40 s)
| field | type |
|---|---|
| `active` | bool |
| `band` | str |
| `chan_best` | int |
| `chan_best_db` | float / null |
| `chan_bw_hz` | int |
| `chan_db` | list |
| `chan_occupied` | list |
| `floor_db` | float |
| `rms_db` | float |
| `spectrum` | list |
| `time` | list |
| `type` | str |
example: `{"type": "iq", "band": "dmr", "active": true, "rms_db": -49.9, "floor_db": -76.6, "spectrum": "<list>", "time": "<list>", "chan_db": "<list>", "chan_best": 0, "chan_best_db": 39.4, "chan_occupied": "<list>", "c`

#### `log` (1724 per 40 s)
| field | type |
|---|---|
| `band` | null / str |
| `t` | float |
| `text` | str |
| `type` | str |
example: `{"type": "log", "band": null, "t": 1793264239.1991825, "text": "<str>"}`

#### `recording` (11 per 40 s)
| field | type |
|---|---|
| `band` | str |
| `duration` | float |
| `file` | str |
| `had_audio` | bool |
| `peak_db` | float |
| `t` | float |
| `type` | str |
example: `{"type": "recording", "band": "p25", "file": "p25_20261029T142717.wav", "duration": 6.7, "had_audio": true, "peak_db": -10.4, "t": 1793264244.518729}`

#### `recordings_list` (1 per 40 s)
| field | type |
|---|---|
| `items` | list |
| `type` | str |
example: `{"type": "recordings_list", "items": "<list>"}`

#### `status` (1 per 40 s)
| field | type |
|---|---|
| `active_band` | null |
| `clients` | object |
| `cycle` | int |
| `lo_lock` | null |
| `pid` | null |
| `running` | bool |
| `rx_gain_actual` | null |
| `type` | str |
| `usb_mbps` | null |
example: `{"type": "status", "running": true, "pid": null, "rx_gain_actual": null, "lo_lock": null, "cycle": 0, "clients": "<object>", "active_band": null, "usb_mbps": null}`

#### `tetra_event` (20 per 40 s)
| field | type |
|---|---|
| `data` | object |
| `t` | float |
| `type` | str |
example: `{"type": "tetra_event", "data": "<object>", "t": 1793264240.3167207}`

### Air & maritime — `ws://127.0.0.1:8887`

Commands: `start_flowgraph`, `stop_flowgraph`, `ping`.

| message type | per 30 min (replay) | fields |
|---|---|---|
| `adsb_update` | 25736 | `target`, `type` |
| `ais_remove` | 1 | `mmsi`, `type` |
| `ais_update` | 454 | `target`, `type` |
| `init_state` | 1 | `adsb_aircraft`, `ais_vessels`, `flowgraph_running`, `type` |
| `spectrum` | 35840 | `active`, `band`, `ffts`, `peak`, `rms_db`, `spectrum`, `type` |

`adsb_update.target` fields: `alt`, `callsign`, `heading`, `icao`, `last_seen`, `lat`, `lon`, `msgs`, `speed`, `vertical_rate`

`ais_update.target` fields: `course`, `heading`, `last_seen`, `lat`, `lon`, `mmsi`, `msg_type`, `nav_status`, `speed`

## 4. Known points to settle before the freeze

- Two bridges, two WebSocket ports and two message vocabularies (terrestrial 8787, air 8887); integration may want one.
- Terrestrial `audio.pcm16` is base64 int16 PCM in JSON (about 1,100 messages/s): heavy; a binary frame or ZeroMQ-to-browser path is worth discussing.
- Terrestrial `status` carries Module 1 / B210 fields (`usb_mbps`, `lo_lock`, `rx_gain_actual`, `cycle`, `active_band`) that will not exist with the bigger USRP.
- The IQ port numbers and 200 kSps / 250 kSps / 6 MSps per-band rates are fixed in the decoders (channelizer settings); a different front end must match them or the decoder front stage changes.
- No authentication or TLS on any of these sockets (loopback only today).
