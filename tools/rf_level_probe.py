#!/usr/bin/env python3
"""
RF level / clipping probe — sweeps RX gain and reports how hard the ADC is
being driven, so gain is chosen from measurement rather than guesswork.

Reads the USRP directly, so run it with the COUPLING stack STOPPED
(./run_securecom.sh --stop) — the radio can only be opened by one process.

Note on reading the output: DMR/NXDN/P25/TETRA are constant-envelope 4FSK, so a
high RMS is normal and is NOT by itself evidence of clipping. Judge clipping by
peak and by the fraction of samples near full scale. A real bench measurement
here read -5.6 dBFS RMS with peak 0.88 and 0.00% above 0.95 — hot, but perfectly
clean; cutting gain on the strength of the RMS alone would be a mistake.

    python3 tools/rf_level_probe.py
    python3 tools/rf_level_probe.py --freq 446.118528e6 --gains 10,20,30,40
"""
import argparse
import sys

import numpy as np

try:
    import uhd
except ImportError:
    sys.exit("uhd python bindings not available")


def dbfs(x):
    return 20.0 * np.log10(x) if x > 0 else -np.inf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--freq', type=float, default=446.118528e6,
                    help='default is the measured bench-radio centre')
    ap.add_argument('--rate', type=float, default=200e3)
    ap.add_argument('--gains', default='0,10,20,30,40,50,60')
    ap.add_argument('--nsamps', type=int, default=40000)
    a = ap.parse_args()

    usrp = uhd.usrp.MultiUSRP()
    print(f"\n  freq {a.freq/1e6:.6f} MHz   rate {a.rate/1e3:.0f} kSps   "
          f"{a.nsamps} samples/point")
    print("  KEY UP while this runs, or you are only measuring noise floor.\n")
    print(f"  {'gain':>6} {'peak':>8} {'rms':>8} {'pk/rms':>7} {'>0.95':>7}  verdict")
    print("  " + "-" * 56)

    rows = []
    for g in (float(x) for x in a.gains.split(',')):
        s = usrp.recv_num_samps(a.nsamps, a.freq, a.rate, [0], g)[0]
        mag = np.abs(s)
        peak, rms = float(mag.max()), float(np.sqrt(np.mean(mag ** 2)))
        near = float(np.mean(mag > 0.95)) * 100
        crest = dbfs(peak) - dbfs(rms) if rms > 0 else 0.0
        if near > 0.01:
            verdict = "CLIPPING"
        elif dbfs(peak) > -1:
            verdict = "at the rail"
        elif dbfs(peak) < -55:
            verdict = "nothing heard"
        else:
            verdict = "clean"
        rows.append((g, dbfs(peak), verdict))
        print(f"  {g:5.0f}dB {dbfs(peak):7.1f} {dbfs(rms):7.1f} "
              f"{crest:6.1f}dB {near:6.2f}%  {verdict}")

    clean = [r for r in rows if r[2] == "clean"]
    print()
    if clean:
        best = max(clean, key=lambda r: r[0])
        print(f"  -> highest clean gain: {best[0]:.0f} dB (peak {best[1]:.1f} dBFS)")
        print(f"     apply with:  ./run_securecom.sh --gain {best[0]:.0f}")
    else:
        print("  -> nothing clean in this sweep. If every row says 'nothing heard',")
        print("     check the radio is keyed, on this frequency, and the antenna is on RX2.")
    print()


if __name__ == '__main__':
    main()
