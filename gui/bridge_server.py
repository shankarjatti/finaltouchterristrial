#!/usr/bin/env python3
"""
SecureCOM COUPLING — real-time bridge between Module 1 and the console GUI.

What this actually does (all real, no simulation):
  - Starts/stops the real securecom_module1 binary as a subprocess.
  - Parses its real stdout (RX gain, LO lock, cycle #, dwell/gap events,
    client connect/disconnect) and forwards it as console log lines.
  - Connects to Module 1's 8 TCP data ports itself (127.0.0.1:7001-7008),
    exactly like Module 2 does, and reads the real complex64 IQ stream.
    Computes a real FFT per band and forwards spectrum/waterfall/time data.
  - "Active" band detection is derived from real energy in the IQ stream
    (Module 1 sends zero-fill during gaps, so idle bands read near-zero).

What this does NOT do yet (protocol decode is out of scope for this piece):
  - No demodulation/decoding — that is Module 2 (allinone.py / GNU Radio),
    which is unaffected by this and can still be run separately.
  - No audio levels / voice-decode / .wav recording — those require tapping
    Module 2's dsd_block output, not just raw IQ. The GUI keeps those tiles
    in a clearly-marked "not live" state until that piece is built.

Run:
    python3 bridge_server.py
    then open securecom_gui.html in a browser (it connects to
    ws://127.0.0.1:8787 automatically; falls back to its own simulation
    if the bridge isn't reachable).
"""
import asyncio
import base64
import collections
import json
import os
import re
import subprocess
import time
import wave

import numpy as np
import pmt
import websockets
import zmq
import zmq.asyncio

MODULE1_BIN = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'module1', 'build', 'securecom_module1')
MODULE2_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recordings')
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# real decoded-audio taps added to allinone.grc (bridge_zmq_* blocks) -- see
# COUPLING/allinone.grc.pre_audiotap for the pre-patch version
AUDIO_TAPS = {
    'dmr':  {'addr': 'tcp://127.0.0.1:9101', 'rate': 48000},
    'nxdn': {'addr': 'tcp://127.0.0.1:9102', 'rate': 48000},
    'p25':  {'addr': 'tcp://127.0.0.1:9103', 'rate': 48000},
    'tetra':{'addr': 'tcp://127.0.0.1:9104', 'rate': 8000},
    # step 2 protocols (tools/add_protocols.py)
    'nxdn48':   {'addr': 'tcp://127.0.0.1:9106', 'rate': 48000},
    'dstar':    {'addr': 'tcp://127.0.0.1:9107', 'rate': 48000},
    'x2tdma':   {'addr': 'tcp://127.0.0.1:9108', 'rate': 48000},
    'provoice': {'addr': 'tcp://127.0.0.1:9109', 'rate': 48000},
}
TETRA_EVENTS_ADDR = 'tcp://127.0.0.1:9105'
REC_ON_DBFS = -38.0   # audio RMS above this = decoded voice actually present
# External IQ source (final system: a bigger USRP, not Module 1). SECURECOM_EXTERNAL_IQ=1 makes the
# bridge a pure backend + UI feed: it does not start Module 1, it connects its own IQ readers to
# ports 7001-7008 (every band streams continuously and at once), and the recorder saves one clip per
# decoded voice transmission (the 'whole dwell' rule has no dwell to follow).
EXTERNAL_IQ = os.environ.get('SECURECOM_EXTERNAL_IQ') == '1'
VOICE_HANG_S = 1.5     # external mode: a clip ends after this long without decoded voice
REC_MIN_VOICE_S = 0.5  # a recording is kept only if DSD decoded at least this much voice in it
                       # (only used to LABEL a recording now, not to gate it)
REC_HANGTIME_S = 1.2  # legacy, kept for reference
DWELL_TAIL_S = 0.45   # keep recording this long past the dwell's RF ending, to
                       # cover the flowgraph's pipeline delay so the tail of a
                       # dwell's audio is not truncated

zctx = zmq.asyncio.Context()
proc2 = None  # Module 2 (allinone.py) subprocess
recorders = {}  # band -> {'wf': wave.Wave_write, 'path':..., 'started':..., 'last_hot':...}

BANDS = [
    {'key': 'dmr',   'name': 'DMR446',  'freq': 446.118528, 'port': 7001},
    {'key': 'nxdn',  'name': 'NXDN96',  'freq': 451.09375, 'port': 7002},
    {'key': 'p25',   'name': 'P25-Ph1', 'freq': 450.09375, 'port': 7003},
    {'key': 'tetra', 'name': 'TETRA',   'freq': 420.00000, 'port': 7004},
    # step 2: names must match Module 1's band names (its DWELL log lines are parsed)
    {'key': 'nxdn48',   'name': 'NXDN48',   'freq': 451.00625, 'port': 7005},
    {'key': 'dstar',    'name': 'DSTAR',    'freq': 439.41250, 'port': 7006},
    {'key': 'x2tdma',   'name': 'X2TDMA',   'freq': 452.00000, 'port': 7007},
    {'key': 'provoice', 'name': 'PROVOICE', 'freq': 453.00000, 'port': 7008},
]
SAMP_RATE = 200_000.0
FFT_N = 512
ACTIVE_THRESH_DBFS = -60.0   # fallback only, until a band has enough history (see band_active)
# A fixed dBFS threshold cannot serve both a bare B210 (floor ~-78 dBFS) and one with a
# real antenna (room noise ~-62 dBFS): with an antenna, -60 sat 2 dB above the noise and
# an over-the-air NXDN signal at -63.7 dBFS read 'idle' and was never recorded. Each band
# now learns its own floor: the 5th percentile of its recent non-zero-fill frame levels.
NOISE_WIN = 1200            # frames of history per band (~110 s of that band's dwell time)
NOISE_MARGIN_DB = 6.0       # active when this far above the band's own floor
NOISE_MIN_FRAMES = 50       # below this much history, fall back to ACTIVE_THRESH_DBFS
# A band's history only holds its own dwell frames (gaps are zero-fill and are skipped). In a long
# dwell on a strong signal (D-STAR, 30 s, -41 dBFS vs -78 on every other band) that history is ALL
# signal, so the 5th percentile climbed to the signal itself (floor -45 dB): the band read 'idle',
# showed no DECODING and saved no recording while DSD was decoding voice. All bands share one
# receiver, so a band's noise cannot sit far above the quietest band's: cap its floor there.
CROSS_BAND_ALLOW_DB = 10.0
CROSS_BAND_MIN_FRAMES = 10   # a band's level is a usable reference after ~1 dwell, not 50 frames
BAND_REF_DB = {}             # band -> 5th percentile of its recent levels (reference for the others)

# Channel counts must match allinone.grc's pfb.channelizer_ccf blocks exactly:
# DMR 16, NXDN 16, P25 10. TETRA is not channelized (TDMA -- one carrier, 4
# timeslots), so it gets 1 "channel" here and its slot detail comes from the
# tetra_decoder_block call_log instead.
CHANNELS_PER_BAND = {'dmr': 16, 'nxdn': 16, 'p25': 10, 'tetra': 1,
                     'nxdn48': 32, 'dstar': 16, 'x2tdma': 16, 'provoice': 8}   # 6.25 / 12.5 / 12.5 / 25 kHz
CHAN_SNR_DB = 8.0            # channel counts as occupied this far above band median
BAND_RF_ACTIVE = {b['key']: False for b in BANDS}
BAND_RF_LAST = {b['key']: 0.0 for b in BANDS}
VOICE_LAST = {b['key']: 0.0 for b in BANDS}   # external mode: last time decoded voice was heard
BAND_LEVEL_HIST = {k: collections.deque(maxlen=NOISE_WIN) for k in BAND_RF_ACTIVE}
BAND_FLOOR_DB = {k: None for k in BAND_RF_ACTIVE}


def band_active(key, rms_db):
    """True when this frame is real signal: well above the band's own noise floor."""
    if rms_db <= -110.0:          # Module 1 zero-fill (gap or another band dwelling)
        return False
    hist = BAND_LEVEL_HIST[key]
    hist.append(rms_db)
    if len(hist) >= CROSS_BAND_MIN_FRAMES:
        BAND_REF_DB[key] = float(np.percentile(hist, 5))
    others = [v for k, v in BAND_REF_DB.items() if k != key]
    if len(hist) < NOISE_MIN_FRAMES:
        # not enough own history: a fixed threshold, but never above (quietest other band + margin)
        thr = ACTIVE_THRESH_DBFS
        if others:
            thr = min(thr, min(others) + CROSS_BAND_ALLOW_DB + NOISE_MARGIN_DB)
        return rms_db > thr
    floor = float(np.percentile(hist, 5))
    BAND_FLOOR_DB[key] = floor
    if others:
        floor = min(floor, min(others) + CROSS_BAND_ALLOW_DB)
    return rms_db > floor + NOISE_MARGIN_DB


def channel_powers(spec_pow, key):
    """Per-channelizer-channel power (dB) from the real FFT of this band's IQ.

    Mirrors how pfb.channelizer_ccf splits the band: channel k is centred at
    k*fs/N for k <= N/2 and (k-N)*fs/N above that. This is measured energy per
    channel, which answers "which channel is the signal in" -- it is NOT
    talkgroup/unit metadata, which gr-dsd-ext's dsd_block cannot provide at all
    (it exposes only an audio output, no message port).
    """
    n = CHANNELS_PER_BAND.get(key, 1)
    if n <= 1:
        return [float(10 * np.log10(max(spec_pow.sum(), 1e-18)))]
    nb = len(spec_pow)                 # fftshifted: index 0 = -fs/2
    bins_per_chan = nb / n
    out = []
    for k in range(n):
        # channel centre as a signed offset in "bins from DC"
        off = k if k <= n // 2 else k - n
        centre = nb / 2 + off * bins_per_chan
        lo = int(round(centre - bins_per_chan / 2))
        hi = int(round(centre + bins_per_chan / 2))
        idx = np.arange(lo, hi) % nb   # wrap the band-edge channel
        out.append(float(10 * np.log10(max(spec_pow[idx].sum(), 1e-18))))
    return out

CLIENTS = set()               # connected browser websockets
STATE = {
    'running': False,
    'pid': None,
    'rx_gain_actual': None,
    'lo_lock': None,
    'cycle': 0,
    'clients': {b['key']: 0 for b in BANDS},
    'active_band': None,
    'usb_mbps': None,        # the B210's real negotiated USB speed (480 = USB 2.0, 5000 = USB 3)
}
proc = None
BG_TASKS = set()  # strong refs -- asyncio only holds weak refs to tasks otherwise,
                   # and an unreferenced task can be silently garbage-collected mid-run

def spawn(coro):
    t = asyncio.create_task(coro)
    BG_TASKS.add(t)
    t.add_done_callback(BG_TASKS.discard)
    return t


async def broadcast(msg: dict):
    if not CLIENTS:
        return
    try:
        data = json.dumps(msg)
    except TypeError:
        data = json.dumps(msg, default=str)
    dead = []
    for ws in list(CLIENTS):  # snapshot -- CLIENTS mutates concurrently (new
                               # connections, disconnects) while many tasks
                               # (spectrum/audio/log) call broadcast() at once
        try:
            await ws.send(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)


# ---------------------------------------------------------------- Module 1 process + log parsing

RE_GAIN = re.compile(r'RX gain actual\s*:\s*([\d.]+)\s*dB')


def b210_usb_mbps():
    """The B210's negotiated USB speed from sysfs, or None if it is not on the bus.
    Read after Module 1 has opened the radio: until its firmware loads, the B210
    sits in its bootloader and always reports 480 Mbps."""
    base = '/sys/bus/usb/devices'
    try:
        for d in os.listdir(base):
            try:
                with open(os.path.join(base, d, 'idVendor')) as f:
                    if f.read().strip() != '2500':
                        continue
                with open(os.path.join(base, d, 'speed')) as f:
                    return int(float(f.read().strip()))
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return None
RE_LOCK = re.compile(r'LO Lock\s*:\s*(\w+)')
RE_CYCLE = re.compile(r'Cycle #(\d+)')
RE_DWELL = re.compile(r'DWELL\s+band=(\S+)\s+freq=([\d.]+)\s*MHz')
RE_GAP = re.compile(r'GAP\s+([\d.]+)s after (\S+)')
RE_CONNECT = re.compile(r'\[TCP:(\d+)\].*CLIENT CONNECTED')
RE_DISCONNECT = re.compile(r'\[TCP:(\d+)\].*CLIENT DISCONNECTED')

BAND_BY_NAME = {b['name']: b for b in BANDS}
BAND_BY_PORT = {b['port']: b for b in BANDS}


async def read_module1_stdout(loop):
    global proc
    my_proc = proc   # this reader belongs to ONE process; a restart spawns a new reader
    while True:
        line = await loop.run_in_executor(None, my_proc.stdout.readline)
        if not line:
            break
        line = line.decode(errors='replace').rstrip('\n')
        if not line.strip():
            continue

        m = RE_GAIN.search(line)
        if m:
            STATE['rx_gain_actual'] = float(m.group(1))
            STATE['usb_mbps'] = b210_usb_mbps()     # radio is up: firmware loaded, real link speed
        m = RE_LOCK.search(line)
        if m:
            STATE['lo_lock'] = m.group(1)
        m = RE_CYCLE.search(line)
        if m:
            STATE['cycle'] = int(m.group(1))
        m = RE_DWELL.search(line)
        band_key = None
        if m:
            b = BAND_BY_NAME.get(m.group(1))
            if b:
                STATE['active_band'] = b['key']
                band_key = b['key']
        m = RE_GAP.search(line)
        if m:
            STATE['active_band'] = None
            b = BAND_BY_NAME.get(m.group(2))
            if b:
                band_key = b['key']
        m = RE_CONNECT.search(line)
        if m:
            b = BAND_BY_PORT.get(int(m.group(1)))
            if b:
                STATE['clients'][b['key']] += 1
        m = RE_DISCONNECT.search(line)
        if m:
            b = BAND_BY_PORT.get(int(m.group(1)))
            if b:
                STATE['clients'][b['key']] = max(0, STATE['clients'][b['key']] - 1)

        await broadcast({'type': 'log', 'band': band_key, 'text': line, 't': time.time()})
        await broadcast({'type': 'status', **STATE})

    # EOF. If stop_module1() did this deliberately it has already cleared `proc`
    # (or a restart replaced it), so only an UNEXPECTED exit gets here with
    # proc still pointing at our process. Previously this was silent and the
    # console kept reading "RUNNING (real)" with the radio gone.
    if proc is my_proc:
        rc = my_proc.poll()
        STATE['running'] = False
        STATE['pid'] = None
        STATE['active_band'] = None
        STATE['clients'] = {b['key']: 0 for b in BANDS}
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': f'[BRIDGE] securecom_module1 EXITED unexpectedly (code {rc}) — '
                                  f'the radio stopped. If the log above shows LIBUSB_TRANSFER_ERROR, '
                                  f'the B210 is on a bad/USB 2.0 link; press Start hardware to retry.'})
        await broadcast({'type': 'status', **STATE})
        proc = None
        # Auto-recover. On a marginal (USB 2.0) link the B210 can get stuck
        # returning LIBUSB_TRANSFER_OVERFLOW on every dwell; only reopening the
        # device clears it, i.e. a fresh Module 1. The decoder's TCP sources
        # reconnect by themselves. Rate-limited so a dead radio is not hammered,
        # and skipped if anyone started/stopped Module 1 in the meantime.
        now = time.time()
        # A run that lasted a while proves the radio works and the failure was a
        # transient USB fault -- start the count over. Only quick repeated
        # deaths (a radio that is really gone) count towards giving up.
        if now - _m1_started_at > 30:
            _m1_auto_restarts.clear()
        _m1_auto_restarts[:] = [t for t in _m1_auto_restarts if now - t < 600]
        if len(_m1_auto_restarts) >= 6:
            await broadcast({'type': 'log', 'band': None, 't': now,
                              'text': '[BRIDGE] not auto-restarting: Module 1 died within 30 s of starting 6 times in a row. '
                                      'Move the B210 to a USB 3 port / cable, then press Start hardware.'})
            return
        _m1_auto_restarts.append(now)
        gen = _m1_generation
        await broadcast({'type': 'log', 'band': None, 't': now,
                          'text': f'[BRIDGE] auto-restarting securecom_module1 in 2 s '
                                  f'(quick-failure count {len(_m1_auto_restarts)}/6)'})
        await asyncio.sleep(2.0)
        if _m1_generation == gen and not STATE['running']:
            await start_module1()


ENV_VAR_BY_BAND = {
    'dmr': 'SECURECOM_DMR_DWELL_SEC', 'nxdn': 'SECURECOM_NXDN_DWELL_SEC',
    'p25': 'SECURECOM_P25_DWELL_SEC', 'tetra': 'SECURECOM_TETRA_DWELL_SEC',
    'nxdn48': 'SECURECOM_NXDN48_DWELL_SEC', 'dstar': 'SECURECOM_DSTAR_DWELL_SEC',
    'x2tdma': 'SECURECOM_X2TDMA_DWELL_SEC', 'provoice': 'SECURECOM_PROVOICE_DWELL_SEC',
}
# Module 1 has one shared GAP_SEC compiled in (module1/src/burst_controller.h),
# not one per band and not env-overridable -- so the schedule tab's gap column
# cannot be applied to the real process without rebuilding the C++ binary.
# Only dwell times are genuinely real-time-controllable right now.
current_dwell = {k: 1.0 for k in ENV_VAR_BY_BAND}
# Seed from this process's own environment so a launcher (run_securecom.sh) can
# set the schedule before anything starts. Pushing it over the WebSocket before
# 'start' is racy -- the value has to already be here when start_module1() builds
# the child env.
for _band, _var in ENV_VAR_BY_BAND.items():
    try:
        current_dwell[_band] = max(0.1, float(os.environ[_var]))
    except (KeyError, ValueError):
        pass
# 40 dB, matching the compiled-in default. An earlier reading of -5.6 dBFS RMS
# here looked like ADC overload, but peak/RMS was 4.5 dB with 0% of samples
# above 0.95 -- i.e. not clipping at all, so that diagnosis was wrong and the
# reduction to 20 dB was unnecessary. Adjustable from the Hardware tab.
current_rx_gain_db = 40.0
try:
    current_rx_gain_db = max(0.0, min(76.0, float(os.environ['SECURECOM_RX_GAIN_DB'])))
except (KeyError, ValueError):
    pass


_m1_generation = 0       # bumped by every deliberate start/stop of Module 1
_m1_auto_restarts = []   # times of automatic restarts, for the rate limit
_m1_started_at = 0.0      # when the current Module 1 was started


async def start_module1():
    global proc, _m1_generation, _m1_started_at
    if EXTERNAL_IQ:
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': '[BRIDGE] external IQ source: Module 1 is not used (nothing to start)'})
        return
    if STATE['running']:
        return
    _m1_generation += 1
    _m1_started_at = time.time()
    if not os.path.exists(MODULE1_BIN):
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': f'[BRIDGE] ERROR: binary not found at {MODULE1_BIN}'})
        return
    env = {**os.environ}
    for band, var in ENV_VAR_BY_BAND.items():
        env[var] = str(current_dwell[band])
    env['SECURECOM_RX_GAIN_DB'] = str(current_rx_gain_db)
    proc = subprocess.Popen([MODULE1_BIN], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             bufsize=0, env=env)  # bufsize=1 is ignored in binary mode
    STATE['running'] = True
    STATE['pid'] = proc.pid
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': f'[BRIDGE] started securecom_module1 (pid {proc.pid})'})
    await broadcast({'type': 'status', **STATE})
    loop = asyncio.get_event_loop()
    spawn(read_module1_stdout(loop))
    # give it a moment to open its listen sockets before we (and Module 2, if
    # you also run it) try to connect
    await asyncio.sleep(1.0)
    for b in BANDS:
        spawn(iq_reader(b, _m1_generation))


async def apply_gain(gain_db: float):
    """Same story as dwell: SECURECOM_RX_GAIN_DB is only read at process
    startup (usrp_controller.cpp), so a real gain change means a real
    restart with the new env var -- not a live parameter change."""
    global current_rx_gain_db
    try:
        current_rx_gain_db = max(0.0, min(76.0, float(gain_db)))
    except (TypeError, ValueError):
        return
    was_running = STATE['running']
    decoder_was_running = proc2 is not None
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': f'[BRIDGE] applying RX gain={current_rx_gain_db} dB (real restart required)'})
    if was_running:
        await stop_module1()
        if decoder_was_running:
            await stop_module2()
        await asyncio.sleep(0.3)
        await start_module1()
        if decoder_was_running:
            await asyncio.sleep(1.0)
            await start_module2()
    else:
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': '[BRIDGE] gain saved — will apply on next Start hardware'})


async def apply_schedule(new_dwell: dict):
    """Real dwell-time change: Module 1 only reads SECURECOM_*_DWELL_SEC at
    process startup (see module1/src/main.cpp), so there is no live-apply --
    the honest way to change it on the real process is to restart it with
    the new env vars. This does exactly that; it is NOT a simulation."""
    for band, val in new_dwell.items():
        if band in current_dwell:
            try:
                current_dwell[band] = max(0.1, float(val))
            except (TypeError, ValueError):
                pass
    was_running = STATE['running']
    decoder_was_running = proc2 is not None
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': f'[BRIDGE] applying schedule (real restart required — Module 1 only reads '
                              f'dwell times at startup): {current_dwell}'})
    if was_running:
        await stop_module1()
        if decoder_was_running:
            await stop_module2()
        await asyncio.sleep(0.3)
        await start_module1()
        if decoder_was_running:
            await asyncio.sleep(1.0)
            await start_module2()
    else:
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': '[BRIDGE] schedule saved — will apply on next Start hardware (nothing running to restart)'})


async def stop_module1():
    global proc, _m1_generation
    _m1_generation += 1
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        proc = None
    STATE['running'] = False
    STATE['pid'] = None
    STATE['active_band'] = None
    STATE['clients'] = {b['key']: 0 for b in BANDS}
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': '[BRIDGE] stopped securecom_module1'})
    await broadcast({'type': 'status', **STATE})


# ---------------------------------------------------------------- real IQ -> FFT per band

async def iq_reader(band, gen):
    """Connect to Module 1's TCP port for this band as a plain client (same
    as Module 2 would) and turn the real complex64 stream into spectrum /
    time-domain frames for the browser. Reconnects if Module 1 restarts."""
    key, port = band['key'], band['port']
    bytes_per_samp = 8  # complex64 = 2 x float32
    chunk_samps = FFT_N
    chunk_bytes = chunk_samps * bytes_per_samp

    # gen = the Module 1 run this reader belongs to. Without it, every restart
    # (gain/schedule change, auto-restart) left the old readers reconnecting
    # forever: 4 bridge clients per port were seen after a few changes.
    while STATE['running'] and gen == _m1_generation:
        try:
            reader, _writer = await asyncio.open_connection('127.0.0.1', port)
        except OSError:
            await asyncio.sleep(0.5)
            continue

        buf = b''
        last_send = 0.0
        try:
            while STATE['running'] and gen == _m1_generation:
                data = await reader.read(65536)
                if not data:
                    break
                buf += data
                while len(buf) >= chunk_bytes:
                    chunk, buf = buf[:chunk_bytes], buf[chunk_bytes:]
                    now = time.time()
                    if now - last_send < 0.09:
                        continue  # throttle to ~11 fps per band, plenty for a UI
                    last_send = now
                    samples = np.frombuffer(chunk, dtype=np.complex64)
                    mag = np.abs(samples)
                    rms = float(np.sqrt(np.mean(mag ** 2))) if len(mag) else 0.0
                    rms_db = 20 * np.log10(rms) if rms > 1e-12 else -120.0
                    active = band_active(key, rms_db)

                    win = samples * np.hanning(len(samples))
                    spec = np.fft.fftshift(np.fft.fft(win, FFT_N))
                    spec_pow = np.abs(spec) ** 2
                    spec_db = 10 * np.log10(np.maximum(spec_pow, 1e-18))

                    # RF-active gate drives whole-dwell recording (Module 1 sends
                    # zero-fill during gaps, so this tracks the real dwell window)
                    BAND_RF_ACTIVE[key] = bool(active)
                    if active:
                        BAND_RF_LAST[key] = now

                    chans = channel_powers(spec_pow, key)
                    best = max(range(len(chans)), key=lambda i: chans[i]) if chans else -1
                    noise = float(np.median(chans)) if chans else 0.0
                    # a channel counts as occupied when it stands clear of the
                    # median (noise) level of the other channels in the same band
                    occupied = [i for i, p in enumerate(chans)
                                if p - noise > CHAN_SNR_DB] if active else []

                    await broadcast({
                        'type': 'iq',
                        'band': key,
                        'active': bool(active),
                        'rms_db': round(rms_db, 1),
                        'floor_db': None if BAND_FLOOR_DB[key] is None else round(BAND_FLOOR_DB[key], 1),
                        'spectrum': [round(float(x), 1) for x in spec_db[::2]],  # 256 bins
                        'time': [round(float(x), 4) for x in samples.real[::4]][:64],
                        'chan_db': [round(float(p), 1) for p in chans],
                        'chan_best': best if active else -1,
                        'chan_best_db': round(float(chans[best] - noise), 1) if (active and chans) else None,
                        'chan_occupied': occupied,
                        'chan_bw_hz': int(SAMP_RATE / CHANNELS_PER_BAND[key]),
                    })
        except (ConnectionResetError, OSError):
            pass
        finally:
            try:
                _writer.close()
            except Exception:
                pass
        await asyncio.sleep(0.5)


# ---------------------------------------------------------------- Module 2 (decoder) process

async def start_module2():
    global proc2
    if proc2 is not None:
        return
    py_path = os.path.join(MODULE2_DIR, 'allinone.py')
    if not os.path.exists(py_path):
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': f'[BRIDGE] ERROR: {py_path} not found'})
        return
    proc2 = subprocess.Popen(['python3', py_path], cwd=MODULE2_DIR,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
                              env={**os.environ})
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': f'[BRIDGE] started allinone.py / Module 2 (pid {proc2.pid})'})
    await broadcast({'type': 'decoder_status', 'running': True})
    loop = asyncio.get_event_loop()
    spawn(read_module2_stdout(loop))
    for band in AUDIO_TAPS:
        spawn(audio_tap_reader(band))
    spawn(tetra_event_reader())


async def stop_module2():
    global proc2
    if proc2 is not None:
        proc2.terminate()
        try:
            proc2.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc2.kill()
        proc2 = None
    for band, rec in list(recorders.items()):
        close_recording(band)
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': '[BRIDGE] stopped allinone.py / Module 2'})
    await broadcast({'type': 'decoder_status', 'running': False})


async def read_module2_stdout(loop):
    while proc2 is not None:
        line = await loop.run_in_executor(None, proc2.stdout.readline)
        if not line:
            break
        line = line.decode(errors='replace').rstrip('\n')
        if line.strip():
            await broadcast({'type': 'log', 'band': None, 't': time.time(), 'text': '[M2] ' + line})


# ---------------------------------------------------------------- real decoded audio taps

def open_recording(band, rate):
    path = os.path.join(RECORDINGS_DIR, f'{band}_{time.strftime("%Y%m%dT%H%M%S")}.wav')
    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit PCM
    wf.setframerate(rate)
    recorders[band] = {'wf': wf, 'path': path, 'started': time.time(), 'last_hot': time.time()}
    return recorders[band]


def close_recording(band):
    rec = recorders.pop(band, None)
    if rec is None:
        return None
    rec['wf'].close()
    dur = time.time() - rec['started']
    return {'path': rec['path'], 'duration': round(dur, 1)}


async def audio_tap_reader(band):
    """Real decoded audio for one protocol, tapped straight off the
    compiled flowgraph's per-protocol mixer via the bridge_zmq_* blocks
    added to allinone.grc. No synthetic data anywhere in this path."""
    cfg = AUDIO_TAPS[band]
    sock = zctx.socket(zmq.SUB)
    sock.connect(cfg['addr'])
    sock.setsockopt(zmq.SUBSCRIBE, b'')
    sock.setsockopt(zmq.RCVTIMEO, 500)
    try:
        while proc2 is not None:
            try:
                raw = await sock.recv()
            except zmq.Again:
                continue
            except Exception:
                break
            samples = np.frombuffer(raw, dtype=np.float32)
            if len(samples) == 0:
                continue
            rms = float(np.sqrt(np.mean(samples ** 2)))
            rms_db = 20 * np.log10(rms) if rms > 1e-9 else -120.0
            hot = rms_db > REC_ON_DBFS
            # DSD outputs exact silence unless it decoded voice frames, so any
            # non-silent sample is decoded voice (an absolute level would drop
            # quiet but real voice: NXDN48 sits at ~-39 dBFS)
            voiced = int(np.count_nonzero(np.abs(samples) > 1e-4))

            # Whole-dwell recording: capture the FULL dwell window for this
            # band, not only the parts where decoded audio crosses a level.
            # Gated on real RF presence (Module 1 zero-fills during gaps), so
            # nothing inside a dwell is missed -- including audio DSD failed to
            # decode, which is exactly what you need in order to tell whether a
            # dwell was silent or merely undecoded.
            now_t = time.time()
            if EXTERNAL_IQ:
                if voiced > 0:
                    VOICE_LAST[band] = now_t
                in_dwell = (now_t - VOICE_LAST.get(band, 0.0)) < VOICE_HANG_S
            else:
                in_dwell = BAND_RF_ACTIVE.get(band, False) or \
                    (now_t - BAND_RF_LAST.get(band, 0.0) < DWELL_TAIL_S)

            pcm16 = np.clip(samples * 32767.0, -32768, 32767).astype('<i2')
            if in_dwell:
                rec = recorders.get(band)
                if rec is None:
                    rec = open_recording(band, cfg['rate'])
                    rec['peak_db'] = -200.0
                rec['wf'].writeframes(pcm16.tobytes())
                rec['voiced'] = rec.get('voiced', 0) + voiced
                if hot:
                    rec['had_audio'] = True
                rec['peak_db'] = max(rec.get('peak_db', -200.0), rms_db)
            elif band in recorders:
                rec = recorders[band]
                had = rec.get('had_audio', False)
                peak = rec.get('peak_db', -200.0)
                voice_s = rec.get('voiced', 0) / float(cfg['rate'])
                info = close_recording(band)
                # Keep a recording only when DSD decoded voice in it. Saving every
                # RF-active dwell filled the folder with silence (22 of 25 files
                # silent, 822 files / 362 MB), so undecoded dwells are dropped.
                if info and voice_s < REC_MIN_VOICE_S:
                    try:
                        os.remove(info['path'])
                    except OSError:
                        pass
                    info = None
                if info and info['duration'] >= 0.2:
                    await broadcast({'type': 'recording', 'band': band,
                                      'file': os.path.basename(info['path']),
                                      'duration': info['duration'],
                                      'had_audio': bool(had),
                                      'peak_db': round(peak, 1),
                                      't': time.time()})
                    kind = f'{voice_s:.1f} s decoded voice'
                    await broadcast({'type': 'log', 'band': band, 't': time.time(),
                                      'text': f'  ↳ saved {os.path.basename(info["path"])} '
                                              f'({info["duration"]}s, {kind}, peak {peak:.1f} dBFS)'})
                elif info:
                    try:
                        os.remove(info['path'])
                    except OSError:
                        pass

            # downsample the chunk a bit for the websocket payload -- still
            # real samples, just fewer of them, to keep the browser link light
            step = 2 if cfg['rate'] >= 44100 else 1
            await broadcast({
                'type': 'audio', 'band': band, 'rate': cfg['rate'] // step, 'active': hot,
                'rms_db': round(rms_db, 1),
                'pcm16': base64.b64encode(pcm16[::step].tobytes()).decode('ascii'),
            })
    finally:
        sock.close()


async def tetra_event_reader():
    """Real TETRA call-log metadata (service/pdu/ssi/tn/...), tapped from
    tetra_decoder_block_0's own 'call_log' message port -- this is genuine
    protocol decode output, not derived/guessed. DMR/NXDN/P25 have no
    equivalent: the dsd_block_ff block in gr-dsd-ext exposes no message
    port, only audio -- so there is no real per-call metadata available
    for those three without patching that C++ block, which this bridge
    does not attempt."""
    sock = zctx.socket(zmq.SUB)
    sock.connect(TETRA_EVENTS_ADDR)
    sock.setsockopt(zmq.SUBSCRIBE, b'')
    sock.setsockopt(zmq.RCVTIMEO, 500)
    try:
        while proc2 is not None:
            try:
                raw = await sock.recv()
            except zmq.Again:
                continue
            except Exception:
                break
            try:
                msg = pmt.deserialize_str(raw)
                d = pmt.to_python(msg)
            except Exception as e:
                await broadcast({'type': 'log', 'band': 'tetra', 't': time.time(),
                                  'text': f'[BRIDGE] tetra event undecodable: {e}'})
                continue
            await broadcast({'type': 'tetra_event', 'data': d, 't': time.time()})
            await broadcast({'type': 'log', 'band': 'tetra', 't': time.time(),
                              'text': f'[TETRA] {d}'})
    finally:
        sock.close()


# ---------------------------------------------------------------- recordings management

def list_recordings():
    """Every .wav on disk, newest first -- so the browser shows the real folder
    contents (including files from earlier sessions), not just what happened to
    be recorded while this page was open."""
    out = []
    try:
        for fn in os.listdir(RECORDINGS_DIR):
            if not fn.lower().endswith('.wav'):
                continue
            p = os.path.join(RECORDINGS_DIR, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            band = fn.split('_')[0] if '_' in fn else '?'
            dur = None
            try:
                with wave.open(p, 'rb') as w:
                    if w.getframerate():
                        dur = round(w.getnframes() / w.getframerate(), 2)
            except Exception:
                pass
            out.append({'file': fn, 'band': band, 'bytes': st.st_size,
                         'mtime': st.st_mtime, 'duration': dur})
    except OSError:
        pass
    out.sort(key=lambda r: r['mtime'], reverse=True)
    return out


async def send_recordings(ws=None):
    msg = {'type': 'recordings_list', 'items': list_recordings()}
    if ws is not None:
        await ws.send(json.dumps(msg))
    else:
        await broadcast(msg)


async def delete_recording(fn: str):
    """Delete one recording. Path is confined to RECORDINGS_DIR -- a bare
    basename only, so a crafted name cannot escape the folder."""
    safe = os.path.basename(fn or '')
    if not safe.lower().endswith('.wav'):
        return
    p = os.path.realpath(os.path.join(RECORDINGS_DIR, safe))
    if os.path.dirname(p) != os.path.realpath(RECORDINGS_DIR):
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': f'[BRIDGE] refused delete outside recordings dir: {fn}'})
        return
    try:
        os.remove(p)
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': f'[BRIDGE] deleted {safe}'})
    except OSError as e:
        await broadcast({'type': 'log', 'band': None, 't': time.time(),
                          'text': f'[BRIDGE] delete failed {safe}: {e}'})
    await send_recordings()


async def delete_all_recordings():
    items = list_recordings()
    n = 0
    for it in items:
        try:
            os.remove(os.path.join(RECORDINGS_DIR, it['file']))
            n += 1
        except OSError:
            pass
    await broadcast({'type': 'log', 'band': None, 't': time.time(),
                      'text': f'[BRIDGE] deleted {n} recording(s)'})
    await send_recordings()


# ---------------------------------------------------------------- WebSocket server (browser side)

async def handler(ws):
    CLIENTS.add(ws)
    try:
        await ws.send(json.dumps({'type': 'status', **STATE}))
        await ws.send(json.dumps({'type': 'decoder_status', 'running': proc2 is not None}))
        await send_recordings(ws)
        await ws.send(json.dumps({'type': 'log', 'band': None, 't': time.time(),
                                   'text': '[BRIDGE] browser connected to live bridge'}))
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            cmd = msg.get('cmd')
            if EXTERNAL_IQ and cmd in ('start', 'stop', 'apply_schedule', 'apply_gain'):
                await broadcast({'type': 'log', 'band': None, 't': time.time(),
                                  'text': f'[BRIDGE] external IQ source: "{cmd}" is a Module 1 control and is ignored'})
                continue
            if cmd == 'start':
                await start_module1()
            elif cmd == 'stop':
                await stop_module1()
            elif cmd == 'start_decoder':
                await start_module2()
            elif cmd == 'stop_decoder':
                await stop_module2()
            elif cmd == 'apply_schedule':
                await apply_schedule(msg.get('dwell', {}))
            elif cmd == 'apply_gain':
                await apply_gain(msg.get('gain_db'))
            elif cmd == 'list_recordings':
                await send_recordings(ws)
            elif cmd == 'delete_recording':
                await delete_recording(msg.get('file'))
            elif cmd == 'delete_all_recordings':
                await delete_all_recordings()
    except websockets.exceptions.ConnectionClosed:
        pass    # a browser tab closed or crashed without a close frame: normal, not an error
    finally:
        CLIENTS.discard(ws)


async def main():
    global _m1_generation
    print('SecureCOM bridge — ws://127.0.0.1:8787')
    if EXTERNAL_IQ:
        print('IQ source: EXTERNAL (SECURECOM_EXTERNAL_IQ=1) — Module 1 is not started; IQ readers on 7001-7008')
        _m1_generation += 1
        STATE['running'] = True
        STATE['pid'] = None
        for b in BANDS:
            spawn(iq_reader(b, _m1_generation))
    else:
        print(f'Module 1 binary: {MODULE1_BIN}')
    async with websockets.serve(handler, '127.0.0.1', 8787):
        await asyncio.Future()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
