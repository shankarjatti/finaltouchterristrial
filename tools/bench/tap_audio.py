#!/usr/bin/env python3
"""Record one protocol's decoded-audio ZMQ tap and report how much voice came out.

  python3 tools/bench/tap_audio.py 9102 36       # NXDN tap, 36 s
Taps: 9101 DMR, 9102 NXDN, 9103 P25 (float32, 48 kHz); 9104 TETRA (float32, 8 kHz).
"""
import sys
import time

import numpy as np
import zmq

RATE = {9101: 48000, 9102: 48000, 9103: 48000, 9104: 8000}   # as in gui/bridge_server.py


def main():
    port, secs = int(sys.argv[1]), float(sys.argv[2])
    fs = RATE.get(port, 48000)
    s = zmq.Context().socket(zmq.SUB)
    s.connect(f'tcp://127.0.0.1:{port}')
    s.setsockopt(zmq.SUBSCRIBE, b'')
    s.setsockopt(zmq.RCVTIMEO, 300)
    buf = []
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            buf.append(np.frombuffer(s.recv(), dtype=np.float32))
        except zmq.Again:
            pass
    x = np.concatenate(buf) if buf else np.zeros(0, np.float32)
    nz = np.abs(x) > 1e-5
    if not nz.any():
        print(f'tap {port}: {len(x) / fs:.1f} s streamed, NO VOICE')
        return
    v = x[nz]
    bursts = int(np.sum(np.diff(np.flatnonzero(nz)) > fs // 2)) + 1
    print(f'tap {port}: {len(x) / fs:.1f} s streamed, {nz.sum() / fs:.2f} s voice in {bursts} burst(s), '
          f'rms {20 * np.log10(np.sqrt(np.mean(v ** 2))):.1f} dBFS, peak {20 * np.log10(np.abs(v).max()):.1f} dBFS, '
          f'clipped {np.mean(np.abs(x) >= 0.999) * 100:.2f}%')


if __name__ == '__main__':
    main()
