#!/usr/bin/env python3
"""
airmaritime_bridge.py
─────────────────────────────────────────────────────────────────
Air & Maritime Bridge Server for SecureCOM (Version 1)

Scope: AIS and ADS-B only. ACARS was dropped from this prototype — the
acars_*.py/.grc files live under acars_archive/ if that work is picked
back up later.

Roles:
1. Subscribes to ZMQ Pub sockets:
   - tcp://127.0.0.1:9201 (AIS NMEA messages / PMT from airmarin flowgraph)
   - tcp://127.0.0.1:9202 (ADS-B decoded frames / PMT from airmarin flowgraph)
2. Maintains state for:
   - Active AIS vessels (MMSI, position, speed, course, callsign, vessel name)
   - Active ADS-B aircraft (ICAO, callsign, altitude, speed, lat/lon)
3. Serves WebSocket client connections on ws://127.0.0.1:8887
4. Provides process management for:
   - airmaritime_decoder.py (GRC flowgraph)
"""

import asyncio
import json
import math
import os
import sys
import time
import subprocess
import zmq
import zmq.asyncio
import numpy as np

# PMT (GNU Radio's polymorphic type) is how gnuradio.ais / gnuradio.adsb hand
# decoded messages to this bridge. Import is guarded so a missing GNU Radio
# install fails at first real use (inside the listeners' own try/except)
# rather than crashing the whole bridge at startup.
try:
    import pmt
except ImportError:
    pmt = None

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("[ERROR] websockets python library required. Install via pip install websockets")

WS_PORT = 8887
ZMQ_AIS_PORT = 9201
ZMQ_ADSB_PORT = 9202

# Module 1's own raw-IQ TCP ports for these two bands (module1/src/main.cpp
# BANDS table -- same ports airmaritime_decoder_live.py's tcp_source blocks
# read from). Connecting here too, as a second plain client, is the same
# technique gui/bridge_server.py's iq_reader() uses for the 8 terrestrial
# bands: real FFT spectrum for the console's RF Spectrum graph.
IQ_AIS_PORT = 7009
IQ_ADSB_PORT = 7010
AIRMAR_BANDS = [
    {'key': 'ais',  'name': 'AIS',   'freq_mhz': 162.000,  'port': IQ_AIS_PORT,  'samp_rate_hz': 250_000.0},
    {'key': 'adsb', 'name': 'ADS-B', 'freq_mhz': 1090.000, 'port': IQ_ADSB_PORT, 'samp_rate_hz': 2_000_000.0},
]
IQ_FFT_N = 512
IQ_ACTIVE_THRESH_DBFS = -60.0

# Global State
CLIENTS = set()
AIS_VESSELS = {}    # mmsi -> dict
ADSB_AIRCRAFT = {}  # icao -> dict

proc_flowgraph = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLOWGRAPH_SCRIPT = os.path.join(BASE_DIR, "airmaritime_decoder_live.py")


async def broadcast(data):
    if not CLIENTS:
        return
    msg = json.dumps(data)
    dead = set()
    for ws in CLIENTS:
        try:
            await ws.send(msg)
        except Exception:
            dead.add(ws)
    CLIENTS.difference_update(dead)


# -----------------------------------------------------------------------------
# AIS AIVDM decoder (ITU-R M.1371) -- real 6-bit payload decode, not a guess.
#
# Previously this bridge just checked whether the string "AIVDM" appeared in
# the sentence and hashed the whole sentence into a fake MMSI and a fake
# lat/lon near San Francisco. Every ship shown on the map was a plausible-
# looking fabrication, even off a completely real decode. This decodes the
# actual 6-bit-armored payload per the standard, the same way any real AIS
# receiver does.
# -----------------------------------------------------------------------------
_AIS_6BIT_CHARS = ("@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&`()*+,-./0123456789:;<=>?")


def _aivdm_armor_to_bits(payload):
    """6-bit ASCII-armored AIVDM payload -> list of individual bits."""
    bits = []
    for ch in payload:
        c = ord(ch) - 48
        if c > 40:
            c -= 8
        bits.extend((c >> (5 - i)) & 1 for i in range(6))
    return bits


def _bits_uint(bits, start, length):
    v = 0
    for b in bits[start:start + length]:
        v = (v << 1) | b
    return v


def _bits_int(bits, start, length):
    v = _bits_uint(bits, start, length)
    if bits[start] == 1:          # sign bit set -> negative, two's complement
        v -= (1 << length)
    return v


def _bits_text(bits, start, length):
    """6-bit-per-character AIS text field (ship name, callsign, destination)."""
    out = []
    for i in range(start, start + length, 6):
        if i + 6 > len(bits):
            break
        v = _bits_uint(bits, i, 6)
        out.append(_AIS_6BIT_CHARS[v] if v < len(_AIS_6BIT_CHARS) else '?')
    return ''.join(out).rstrip('@').strip()


def parse_aivdm_payload(payload):
    """Decode one AIVDM 6-bit payload into a dict of real fields, or None if
    too short to contain even a message type + MMSI. Position fields
    (lat/lon/sog/cog/heading) are only present for the message types that
    actually carry them (1, 2, 3, 18) -- callers must not invent a position
    for other types."""
    bits = _aivdm_armor_to_bits(payload)
    if len(bits) < 38:
        return None

    msg_type = _bits_uint(bits, 0, 6)
    mmsi = _bits_uint(bits, 8, 30)
    out = {'msg_type': msg_type, 'mmsi': mmsi}

    if msg_type in (1, 2, 3) and len(bits) >= 143:
        lon = _bits_int(bits, 61, 28) / 600000.0
        lat = _bits_int(bits, 89, 27) / 600000.0
        sog_raw = _bits_uint(bits, 50, 10)
        cog_raw = _bits_uint(bits, 116, 12)
        hdg_raw = _bits_uint(bits, 128, 9)
        out.update({
            'nav_status': _bits_uint(bits, 38, 4),
            # Named speed/course (not sog/cog) to match what
            # airmaritime_console.html already reads for a vessel.
            'speed': sog_raw / 10.0 if sog_raw != 1023 else None,
            'lon': lon if abs(lon) <= 180 and lon != 181.0 else None,
            'lat': lat if abs(lat) <= 90 and lat != 91.0 else None,
            'course': cog_raw / 10.0 if cog_raw != 3600 else None,
            'heading': hdg_raw if hdg_raw != 511 else None,
        })
    elif msg_type == 18 and len(bits) >= 139:
        lon = _bits_int(bits, 57, 28) / 600000.0
        lat = _bits_int(bits, 85, 27) / 600000.0
        sog_raw = _bits_uint(bits, 46, 10)
        cog_raw = _bits_uint(bits, 112, 12)
        hdg_raw = _bits_uint(bits, 124, 9)
        out.update({
            'speed': sog_raw / 10.0 if sog_raw != 1023 else None,
            'lon': lon if abs(lon) <= 180 and lon != 181.0 else None,
            'lat': lat if abs(lat) <= 90 and lat != 91.0 else None,
            'course': cog_raw / 10.0 if cog_raw != 3600 else None,
            'heading': hdg_raw if hdg_raw != 511 else None,
        })
    elif msg_type == 5 and len(bits) >= 422:
        # Static & voyage data -- callsign/name, never a position.
        out.update({
            'callsign': _bits_text(bits, 70, 42) or None,
            'name': _bits_text(bits, 112, 120) or None,
        })

    return out


def update_ais_target(parsed):
    """Update AIS vessel state from a real decoded AIVDM dict
    (see parse_aivdm_payload). Only overwrites fields the message actually
    carried -- a static-data message (type 5) must not blank out a position
    learned from an earlier type-1 message for the same vessel, and a
    position message must not invent a name the vessel never sent."""
    if not parsed or 'mmsi' not in parsed:
        return None
    t_now = time.time()
    mmsi = str(parsed['mmsi'])
    v = AIS_VESSELS.setdefault(mmsi, {'mmsi': mmsi})
    for field in ('lat', 'lon', 'speed', 'course', 'heading', 'nav_status',
                  'callsign', 'name'):
        if parsed.get(field) is not None:
            v[field] = parsed[field]
    v['last_seen'] = t_now
    v['msg_type'] = parsed['msg_type']
    return v


def update_adsb_target(fields):
    """Update ADS-B aircraft state from the real decoded PMT dict that
    gnuradio.adsb's own decoder already produces (icao, callsign, longitude,
    latitude, altitude, speed, heading, vertical_rate) -- CPR position
    decoding is done inside gnuradio.adsb itself, not here. A field is NaN
    when that particular message didn't carry it (e.g. an identification
    message has a callsign but no position); NaN must never overwrite a
    position already known for this aircraft from an earlier message."""
    if not fields or not fields.get('icao'):
        return None
    t_now = time.time()
    icao = str(fields['icao']).upper()
    a = ADSB_AIRCRAFT.setdefault(icao, {'icao': icao})
    for src_key, dst_key in (('callsign', 'callsign'), ('longitude', 'lon'),
                              ('latitude', 'lat'), ('altitude', 'alt'),
                              ('speed', 'speed'), ('heading', 'heading'),
                              ('vertical_rate', 'vertical_rate')):
        val = fields.get(src_key)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            if isinstance(val, str):
                val = val.strip()
                if not val:
                    continue
            a[dst_key] = val
    a['last_seen'] = t_now
    return a


# -----------------------------------------------------------------------------
# ZMQ Listeners
# -----------------------------------------------------------------------------
def _nmea_payload(sentence):
    """Extract the 6-bit-armored payload field from a full !AIVDM/!AIVDO
    sentence, e.g. '!AIVDM,1,1,,A,15M67FC0...,0*5C' -> '15M67FC0...'."""
    parts = sentence.strip().split(',')
    if len(parts) >= 6 and parts[0] in ('!AIVDM', '!AIVDO'):
        return parts[5]
    return None


async def zmq_ais_listener(ctx):
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://127.0.0.1:{ZMQ_AIS_PORT}")
    sub.subscribe(b"")
    print(f"[ZMQ] Subscribed to AIS on tcp://127.0.0.1:{ZMQ_AIS_PORT}")
    while True:
        try:
            msg_bytes = await sub.recv()
            try:
                # NO .decode() here: pmt.deserialize_str wants the raw
                # serialized bytes exactly as pmt.serialize_str produced them
                # (it returns bytes, not str, despite the name). Decoding to
                # a Python str first (the previous latin-1 attempt) corrupts
                # the byte stream on anything but the simplest messages --
                # every AIS/ADS-B message silently fell into the except
                # branch below and got parsed as garbled text instead.
                p = pmt.deserialize_str(msg_bytes)
                if pmt.is_pair(p):
                    p = pmt.car(p)
                sentence = pmt.to_python(p) if pmt.is_symbol(p) else None
            except Exception:
                sentence = None

            if isinstance(sentence, str):
                payload = _nmea_payload(sentence)
                parsed = parse_aivdm_payload(payload) if payload else None
                target = update_ais_target(parsed)
                if target:
                    await broadcast({"type": "ais_update", "target": target})
        except asyncio.CancelledError:
            break
        except Exception as e:
            await asyncio.sleep(0.5)


async def zmq_adsb_listener(ctx):
    sub = ctx.socket(zmq.SUB)
    sub.connect(f"tcp://127.0.0.1:{ZMQ_ADSB_PORT}")
    sub.subscribe(b"")
    print(f"[ZMQ] Subscribed to ADS-B on tcp://127.0.0.1:{ZMQ_ADSB_PORT}")
    while True:
        try:
            msg_bytes = await sub.recv()
            try:
                # gnuradio.adsb's decoder publishes a PDU: (metadata-dict .
                # raw-112-bit-frame). The metadata dict already has icao,
                # callsign, longitude/latitude (CPR-decoded internally),
                # altitude, speed, heading -- car() is the dict; cdr() is
                # just the raw bits, which is what the old code was
                # accidentally reading (when it wasn't garbling the bytes
                # entirely -- see the AIS listener above for why).
                p = pmt.deserialize_str(msg_bytes)
                fields = pmt.to_python(pmt.car(p)) if pmt.is_pair(p) else None
            except Exception:
                fields = None

            if isinstance(fields, dict):
                target = update_adsb_target(fields)
                if target:
                    await broadcast({"type": "adsb_update", "target": target})
        except asyncio.CancelledError:
            break
        except Exception as e:
            await asyncio.sleep(0.5)


# -----------------------------------------------------------------------------
# RF Spectrum -- real IQ, connected directly to Module 1's AIS/ADS-B TCP ports
#
# Module 1 hops all 10 bands (8 terrestrial + AIS + ADS-B) on one shared burst
# schedule and sends literal zero-fill IQ to whichever bands it is NOT
# currently dwelling on (the same keep-alive convention gui/bridge_server.py
# already relies on for the terrestrial console). So RMS alone tells us which
# of AIS/ADS-B is the live dwell right now -- no separate schedule message
# needed, and nothing here is simulated: silence in means silence out.
# -----------------------------------------------------------------------------
async def iq_spectrum_reader(band):
    key, port = band['key'], band['port']
    bytes_per_samp = 8  # complex64 = 2 x float32
    chunk_bytes = IQ_FFT_N * bytes_per_samp

    while True:
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
        except OSError:
            await asyncio.sleep(1.0)
            continue

        buf = b''
        last_send = 0.0
        last_idle_send = 0.0
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                buf += data
                while len(buf) >= chunk_bytes:
                    chunk, buf = buf[:chunk_bytes], buf[chunk_bytes:]
                    now = time.time()
                    samples = np.frombuffer(chunk, dtype=np.complex64)
                    if not np.all(np.isfinite(samples)):
                        continue  # never let corrupted data reach the display

                    pwr = float(np.dot(samples.real, samples.real) +
                                np.dot(samples.imag, samples.imag)) / max(1, len(samples))
                    rms = pwr ** 0.5
                    rms_db = 20 * np.log10(rms) if rms > 1e-12 else -120.0
                    is_zerofill = rms <= 1e-12  # Module 1's keep-alive to a band it isn't tuned to

                    if is_zerofill:
                        if now - last_idle_send > 0.5:
                            last_idle_send = now
                            await broadcast({'type': 'spectrum', 'band': key, 'active': False,
                                              'spectrum': None, 'rms_db': round(rms_db, 1)})
                        continue

                    if now - last_send < 0.1:
                        continue
                    last_send = now

                    win = samples * np.hanning(len(samples))
                    spec = np.fft.fftshift(np.fft.fft(win, IQ_FFT_N))
                    spec_db = 10 * np.log10(np.maximum(np.abs(spec) ** 2, 1e-18))

                    await broadcast({
                        'type': 'spectrum', 'band': key,
                        'active': bool(rms_db > IQ_ACTIVE_THRESH_DBFS),
                        'spectrum': [round(float(x), 1) for x in spec_db],
                        'rms_db': round(rms_db, 1),
                    })
        except (ConnectionResetError, OSError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass
        await asyncio.sleep(1.0)


# -----------------------------------------------------------------------------
# WebSocket Server Handler
# -----------------------------------------------------------------------------
async def ws_handler(ws):
    global proc_flowgraph
    CLIENTS.add(ws)
    print(f"[WS] Client connected from {ws.remote_address}")

    # Send initial state snapshot
    init_state = {
        "type": "init_state",
        "ais_vessels": list(AIS_VESSELS.values()),
        "adsb_aircraft": list(ADSB_AIRCRAFT.values()),
        "flowgraph_running": proc_flowgraph is not None and proc_flowgraph.poll() is None,
    }
    await ws.send(json.dumps(init_state))

    try:
        async for raw_msg in ws:
            try:
                cmd_pkt = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            cmd = cmd_pkt.get("cmd")

            if cmd == "start_flowgraph":
                if proc_flowgraph is None or proc_flowgraph.poll() is not None:
                    if os.path.exists(FLOWGRAPH_SCRIPT):
                        proc_flowgraph = subprocess.Popen([sys.executable, FLOWGRAPH_SCRIPT])
                        print(f"[BRIDGE] Started flowgraph script {FLOWGRAPH_SCRIPT}")
                        await broadcast({"type": "status", "flowgraph_running": True})
                    else:
                        await ws.send(json.dumps({"type": "error", "text": f"Script not found: {FLOWGRAPH_SCRIPT}"}))
                else:
                    await ws.send(json.dumps({"type": "status", "flowgraph_running": True}))

            elif cmd == "stop_flowgraph":
                if proc_flowgraph and proc_flowgraph.poll() is None:
                    proc_flowgraph.terminate()
                    proc_flowgraph = None
                    print("[BRIDGE] Stopped flowgraph script")
                await broadcast({"type": "status", "flowgraph_running": False})

            elif cmd == "ping":
                await ws.send(json.dumps({"type": "pong", "time": time.time()}))

    except Exception:
        pass
    finally:
        CLIENTS.discard(ws)
        print("[WS] Client disconnected")


# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------
async def main():
    ctx = zmq.asyncio.Context()
    
    t_ais = asyncio.create_task(zmq_ais_listener(ctx))
    t_adsb = asyncio.create_task(zmq_adsb_listener(ctx))
    t_spec_ais = asyncio.create_task(iq_spectrum_reader(AIRMAR_BANDS[0]))
    t_spec_adsb = asyncio.create_task(iq_spectrum_reader(AIRMAR_BANDS[1]))

    print(f"Air & Maritime Bridge Server starting on ws://127.0.0.1:{WS_PORT}")
    async with websockets.serve(ws_handler, "127.0.0.1", WS_PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[BRIDGE] Server stopped by user.")
