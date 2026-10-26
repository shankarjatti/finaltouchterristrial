#!/usr/bin/env python3
"""
Measure where a transmission ACTUALLY is, from live IQ off Module 1.

This is the tool that found the biggest bug in this project: the receiver was
configured for 446.09375 MHz while the bench radio was really transmitting
~25 kHz higher. Signal showed up on the spectrum, but decode never worked.

Unlike the other probes this does NOT open the USRP — it connects to Module 1's
TCP port as another client, so run it with the stack UP and key the radio.

    python3 tools/measure_signal.py                 # DMR band (7001), 30 s
    python3 tools/measure_signal.py --port 7002 --secs 20

Reports the power centroid and occupied bandwidth of whatever it captures. Put
the resulting frequency into module1/src/main.cpp and rebuild.
"""
import argparse
import socket
import time

import numpy as np

BAND_BY_PORT = {7001: ('DMR446', 446.118528), 7002: ('NXDN96', 451.09375),
                7003: ('P25-Ph1', 450.09375), 7004: ('TETRA', 420.0)}
FS = 200_000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=7001)
    ap.add_argument('--secs', type=float, default=30.0)
    ap.add_argument('--thresh', type=float, default=-55.0,
                    help='dBFS RMS above which a chunk counts as signal')
    a = ap.parse_args()
    name, centre = BAND_BY_PORT.get(a.port, ('?', 0.0))

    print(f"\n  listening on 127.0.0.1:{a.port} ({name}, tuned {centre:.6f} MHz)")
    print(f"  KEY UP within the next {a.secs:.0f}s ...\n")

    s = socket.create_connection(('127.0.0.1', a.port), timeout=5)
    s.settimeout(1.0)
    keep = []
    t0 = time.time()
    while time.time() - t0 < a.secs:
        try:
            d = s.recv(65536)
        except socket.timeout:
            continue
        if not d:
            break
        arr = np.frombuffer(d[:len(d) // 8 * 8], dtype=np.complex64)
        if len(arr) == 0:
            continue
        rms = float(np.sqrt(np.mean(np.abs(arr) ** 2)))
        db = 20 * np.log10(rms) if rms > 1e-12 else -120.0
        if db > a.thresh:
            keep.append(arr)
    s.close()

    if not keep:
        print("  nothing above threshold — was the radio keyed during the window?")
        print("  (Module 1 zero-fills between dwells, so you must key during this")
        print("   band's dwell. A longer --dwell for this band makes that easier.)")
        return

    x = np.concatenate(keep)
    print(f"  captured {len(x)} signal samples ({len(x)/FS:.2f}s equivalent)")

    N = 32768
    if len(x) < N:
        N = 1 << int(np.floor(np.log2(len(x))))
    segs = [x[i*N:(i+1)*N] for i in range(len(x)//N)] or [x[:N]]
    P = np.zeros(N)
    for sg in segs:
        if len(sg) == N:
            P += np.abs(np.fft.fftshift(np.fft.fft(sg * np.hanning(N)))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(N, 1/FS))

    pk_i = int(np.argmax(P))
    # centroid over +/-25 kHz around the peak, so a strong IQ image on the other
    # side of DC cannot drag the estimate
    m = np.abs(f - f[pk_i]) < 25000
    cent = float((f[m] * P[m]).sum() / P[m].sum())
    thr = P[m].max() / 100.0            # -20 dB
    occ = f[m][P[m] > thr]

    print(f"  peak bin        : {f[pk_i]:+.0f} Hz from tuned centre")
    print(f"  power centroid  : {cent:+.0f} Hz from tuned centre")
    print(f"  occupied (-20dB): {occ.min():+.0f} .. {occ.max():+.0f} Hz "
          f"(width {occ.max()-occ.min():.0f} Hz)")
    if centre:
        real = centre + cent / 1e6
        print(f"\n  => real transmit frequency ~ {real:.6f} MHz")
        print(f"     if that differs from {centre:.6f} MHz, set it in")
        print(f"     module1/src/main.cpp and rebuild.")
    print("\n  Occupied width ~8-10 kHz is consistent with DMR/NXDN96/P25 in a")
    print("  12.5 kHz channel. A symmetric partner peak about DC is an IQ image,")
    print("  not a second transmission.\n")


if __name__ == '__main__':
    main()
