#!/usr/bin/env python3
"""Measure one band's live IQ from Module 1 (as an extra client): level, where the
signal sits, how wide, and how far above the noise. Only dwell time is used
(Module 1 zero-fills between dwells), so give the band a long dwell.

  python3 tools/bench/rf_spectrum.py 7002 22     # NXDN port, 22 s
Ports: 7001 DMR, 7002 NXDN, 7003 P25, 7004 TETRA.
"""
import socket
import sys
import time

import numpy as np

FS = 200000
N = 8192


def main():
    port, secs = int(sys.argv[1]), float(sys.argv[2])
    s = socket.create_connection(('127.0.0.1', port))
    s.settimeout(2)
    buf = bytearray()
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            d = s.recv(1 << 20)
        except socket.timeout:
            continue
        if not d:
            break
        buf += d
    x = np.frombuffer(bytes(buf[:len(buf) // 8 * 8]), dtype=np.complex64)
    live = [x[i:i + N] for i in range(0, len(x) - N, N) if np.any(x[i:i + N] != 0)]
    if not live:
        print(f'port {port}: no dwell samples in {secs:.0f} s')
        return
    w = np.hanning(N)
    P = np.mean([np.abs(np.fft.fftshift(np.fft.fft(b * w))) ** 2 for b in live], axis=0) / (N * np.sum(w ** 2))
    f = np.fft.fftshift(np.fft.fftfreq(N, 1 / FS))
    Pd = 10 * np.log10(P + 1e-20)
    k = int(500 / (FS / N))
    sm = np.convolve(Pd, np.ones(k) / k, mode='same')
    # noise floor from an empty part of the passband (the B210's filter skirts
    # near +-100 kHz sit far below the real floor and would drag a percentile down)
    floor = float(np.median(sm[(np.abs(f) > 30e3) & (np.abs(f) < 80e3)]))
    # ignore the B210's own DC/LO spike at 0 Hz: it is there with nothing on the air
    # and would otherwise read as a 'signal' 57 dB up on every band
    hot = (sm > floor + 10) & (np.abs(f) > 600)
    # and a real signal must stand clear of the receiver's own floor in a 6.25 kHz window
    if hot.sum() < int(1000 / (FS / N)):
        hot[:] = False
    tot = 10 * np.log10(np.mean([np.mean(np.abs(b) ** 2) for b in live]) + 1e-20)
    pk = max(float(np.abs(b).max()) for b in live)
    ch0 = 10 * np.log10(np.sum(P[(f >= -6250) & (f < 6250)]) + 1e-20)
    print(f'port {port}: {len(live) * N / FS:.1f} s of dwell')
    print(f'  total {tot:6.1f} dBFS, peak sample {20 * np.log10(pk):5.1f} dBFS (clip risk above -1)')
    print(f'  channel 0 (+-6.25 kHz) {ch0:6.1f} dB, noise floor per bin {floor:6.1f} dB')
    if hot.any():
        lin = P * hot
        cen = float(np.sum(f * lin) / np.sum(lin))
        occ = f[hot]
        print(f'  signal {occ.min():+.0f} .. {occ.max():+.0f} Hz (width {occ.max() - occ.min():.0f} Hz), '
              f'centroid {cen:+.0f} Hz, peak {sm.max() - floor:.1f} dB above floor')
    else:
        print('  no signal 10 dB above the floor')
    # coarse spectrum around the centre, 1 kHz steps, dB above the floor
    row = []
    for c in range(-12, 13):
        m = (f >= c * 1000 - 500) & (f < c * 1000 + 500)
        row.append(f'{c:+d}k:{np.mean(sm[m]) - floor:.0f}')
    print('  dB above floor by offset: ' + ' '.join(row))


if __name__ == '__main__':
    main()
