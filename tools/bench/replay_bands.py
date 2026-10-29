#!/usr/bin/env python3
"""Stand-in for Module 1 for the TERRESTRIAL decoder + bridge: serve recorded IQ on ports 7001-7008.

What a bigger USRP front end would deliver: every band streams continuously and at once (no
dwell/gap hopping), complex64 at 200 kSps on its own TCP port, signal centred in the band. Each
band loops a real recording, resampled to 200 kSps and scaled to a realistic level, on top of a
realistic idle-channel noise floor. A band with no recording gets the noise floor only.

  python3 tools/bench/replay_bands.py /path/to/stats.txt

Real-time paced per client. If a client (the decoder) stops reading, TCP back-pressure makes this
server fall behind real time; the worst lag per port is reported every 20 s in the stats file.
"""
import socket
import sys
import threading
import time
import wave
from fractions import Fraction

import numpy as np
from scipy import signal

FS = 200000
SIG_RMS_DBFS = -45.0     # rms of a recorded signal in the band (cable bench tests read -41 ... -50 dBFS)
NOISE_RMS_DBFS = -78.0   # idle B210 floor measured on every band
CHUNK = 4000             # 20 ms
BASE = '/home/shankar/Downloads/tutorials/'
SRC = '/home/shankar/Downloads/tutorials/delhi_testing/all_protocols_wav_samples/'
BANDS = [   # port, name, wav, swap I/Q, note
    (7001, 'DMR',      SRC + 'DMR/SDRSharp_20160101_231914Z_72125hz_IQ.wav', False, 'real recording'),
    (7002, 'NXDN96',   SRC + 'NXDN/NXDN96 IQ.wav', False, 'real recording'),
    (7003, 'P25',      BASE + 'sigidwiki_p25_voice/P25-C4FM-VC_IF.wav', False, 'real recording (sigidwiki)'),
    (7004, 'TETRA',    SRC + 'TETRA/TETRA IQ.wav', True, 'real recording'),
    (7005, 'NXDN48',   SRC + 'NXDN/NXDN48 IQ.wav', False, 'real recording'),
    (7006, 'DSTAR',    BASE + 'web_protocol_samples/dstar/DStar_Sound_fm_iq_48k.wav', False,
     'real off-air discriminator signal, FM-modulated to IQ'),
    (7007, 'X2TDMA',   None, False, 'no sample: noise floor only'),
    (7008, 'PROVOICE', None, False, 'no sample: noise floor only'),
]


def load_wav_iq(path, swap):
    w = wave.open(path)
    n, rate, sw = w.getnframes(), w.getframerate(), w.getsampwidth()
    raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        a = np.where(v >= 1 << 23, v - (1 << 24), v).reshape(-1, 2).astype(np.float32) / float(1 << 23)
    else:
        raise SystemExit(f'{path}: unsupported sample width {sw}')
    i, q = (a[:, 1], a[:, 0]) if swap else (a[:, 0], a[:, 1])
    return (i + 1j * q).astype(np.complex64), rate


def build(rng, wav, swap):
    secs = 30
    if wav is None:
        x = np.zeros(FS * secs, dtype=np.complex64)
    else:
        iq, rate = load_wav_iq(wav, swap)
        r = Fraction(FS, rate).limit_denominator(1000)
        x = signal.resample_poly(iq, r.numerator, r.denominator).astype(np.complex64)
        x = x - np.mean(x)                                   # the recording's own DC is not part of the signal
        x = x * (10 ** (SIG_RMS_DBFS / 20) / float(np.sqrt(np.mean(np.abs(x) ** 2))))
        reps = max(1, int(np.ceil(FS * 10 / len(x))))        # at least 10 s so the loop seam is rare
        x = np.tile(x, reps)
    sig = 10 ** (NOISE_RMS_DBFS / 20) / np.sqrt(2)
    nz = (rng.standard_normal(len(x)) + 1j * rng.standard_normal(len(x))).astype(np.complex64) * np.float32(sig)
    return (x + nz).astype(np.complex64)


stats = {}
lock = threading.Lock()


def serve(port, name, iq):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', port))
    srv.listen(4)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=client, args=(c, port, name, iq), daemon=True).start()


def client(c, port, name, iq):
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    pos, sent, t0 = 0, 0, time.time()
    with lock:
        st = stats.setdefault(port, {'name': name, 'clients': 0, 'bytes': 0, 'max_lag_s': 0.0, 'conn_total': 0})
        st['clients'] += 1
        st['conn_total'] += 1
    try:
        while True:
            end = pos + CHUNK
            block = iq[pos:end] if end <= len(iq) else np.concatenate([iq[pos:], iq[:end - len(iq)]])
            pos = end % len(iq)
            c.sendall(block.tobytes())
            sent += CHUNK
            due = t0 + sent / FS
            now = time.time()
            if due > now:
                time.sleep(due - now)
            else:
                with lock:
                    st['max_lag_s'] = max(st['max_lag_s'], now - due)
            with lock:
                st['bytes'] += CHUNK * 8
    except OSError:
        pass
    finally:
        with lock:
            st['clients'] -= 1
        c.close()


def main():
    out = sys.argv[1]
    rng = np.random.default_rng(1)
    for port, name, wav, swap, note in BANDS:
        iq = build(rng, wav, swap)
        print(f'{port} {name:9s} {len(iq) / FS:5.1f} s loop  ({note})', flush=True)
        threading.Thread(target=serve, args=(port, name, iq), daemon=True).start()
    print('serving 8 bands at 200 kSps; stats ->', out, flush=True)
    while True:
        time.sleep(20)
        with lock:
            lines = [f"{p} {s['name']:9s} clients {s['clients']} connections {s['conn_total']} "
                     f"sent {s['bytes'] / 1e6:9.1f} MB  worst lag {s['max_lag_s']:.3f} s" for p, s in sorted(stats.items())]
            for s in stats.values():
                s['max_lag_s'] = 0.0
        with open(out, 'w') as f:
            f.write(time.strftime('%H:%M:%S') + '\n' + '\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
