#!/usr/bin/env python3
"""Stand-in for Module 1: serve recordings on the IQ ports with the burst schedule,
so the real decoder (allinone.py), bridge and UI can be tested with no radio.

During a band's dwell its port gets that band's recording (looped); the other
ports get zeros, all at 200 kSps in real time -- exactly what the Delhi Module 1
sends. Sends block like Module 1's, so a slow decoder shows up as lag.

  python3 tools/bench/replay_module1.py --tetra "../../../../tetra_test/TETRA IQ.wav" --secs 120
  python3 tools/bench/replay_module1.py --nxdn "NXDN96 IQ.wav" --dwell 10 --secs 96

Inputs: a stereo I/Q .wav at any rate, or raw complex64 at 200 kSps (.cf32).
Signals are used as recorded (not re-centred): the decoder's chains already
expect each recording's offset (e.g. TETRA IQ.wav sits at -1.714 kHz).
Stop the real stack first: it owns ports 7001-7004.
"""
import argparse
import socket
import threading
import time
import wave
from fractions import Fraction

import numpy as np

FS = 200000
TICK = 2000            # 10 ms per send
BANDS = [('dmr', 7001), ('nxdn', 7002), ('p25', 7003), ('tetra', 7004)]


def load(path):
    if path.lower().endswith('.wav'):
        from scipy.signal import resample_poly
        with wave.open(path) as w:
            fs = w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2) / 32768.0
        r = Fraction(FS, fs).limit_denominator(1000)
        return resample_poly(a[:, 0] + 1j * a[:, 1], r.numerator, r.denominator).astype(np.complex64)
    return np.fromfile(path, dtype=np.complex64)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for b, _ in BANDS:
        ap.add_argument(f'--{b}', help=f'recording for the {b.upper()} port')
    ap.add_argument('--dwell', type=float, default=10.0, help='seconds per band (default 10)')
    ap.add_argument('--gap', type=float, default=1.0, help='zero-fill between bands (default 1)')
    ap.add_argument('--secs', type=float, default=96.0, help='total run time (default 96)')
    ap.add_argument('--only', choices=[b for b, _ in BANDS],
                    help='keep this one band dwelling all the time (no schedule, no gaps)')
    a = ap.parse_args()

    rec = {b: load(getattr(a, b)) for b, _ in BANDS if getattr(a, b)}
    for b, x in rec.items():
        print(f'{b}: {len(x) / FS:.1f} s loaded', flush=True)
    conns = {}

    def accept(port, b):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        s.listen(1)
        c, _ = s.accept()
        conns[b] = c

    for b, p in BANDS:
        threading.Thread(target=accept, args=(p, b), daemon=True).start()
    t0 = time.time()
    while len(conns) < len(BANDS) and time.time() - t0 < 90:
        time.sleep(0.1)
    print(f'clients connected: {sorted(conns)}', flush=True)

    zero = np.zeros(TICK, np.complex64).tobytes()
    pos = {b: 0 for b in rec}
    slot_len = a.dwell + a.gap
    start = time.time()
    sent = 0
    lag = 0.0
    while sent / FS < a.secs:
        t = (sent / FS) % (slot_len * len(BANDS))
        slot = int(t // slot_len)
        active = BANDS[slot][0] if (t - slot * slot_len) < a.dwell else None
        if a.only:
            active = a.only
        for b, _ in BANDS:
            if b == active and b in rec:
                x = rec[b]
                data = np.take(x, range(pos[b], pos[b] + TICK), mode='wrap').tobytes()
                pos[b] = (pos[b] + TICK) % len(x)
            else:
                data = zero
            if b in conns:
                try:
                    conns[b].sendall(data)
                except OSError:
                    pass
        sent += TICK
        ahead = start + sent / FS - time.time()
        if ahead > 0:
            time.sleep(ahead)
        else:
            lag = max(lag, -ahead)
    print(f'replay done: {sent / FS:.0f} s served in {time.time() - start:.0f} s, '
          f'max lag behind real time {lag:.2f} s', flush=True)


if __name__ == '__main__':
    main()
