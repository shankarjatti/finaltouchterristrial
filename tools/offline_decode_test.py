#!/usr/bin/env python3
"""Offline decode regression test against a REAL captured DMR transmission.

Runs the vendored capture (tools/testdata/dmr_real_capture.cf32.gz -- a genuine
0.97 s key-up from the bench radio) through the same DSP chain allinone.grc uses,
so decode can be verified with no radio and no timing coordination. This is the
test that found the demod-gain bug: gain 3.93 (the textbook fs/(2*pi*dev) value)
produces total silence, while 1.0 produces -20.5 dBFS of audio.

  python3 tools/offline_decode_test.py              # sweep gains at measured offset
  python3 tools/offline_decode_test.py 1.0 24778 0  # single run: gain offset dcblock
"""
import gzip
import os
import shutil
import sys
import tempfile

import numpy as np
from gnuradio import gr, blocks, filter, analog
from gnuradio.filter import firdes
import dsd

FS_IN = 200000.0
SWEEP = len(sys.argv) < 4
gain   = float(sys.argv[1]) if not SWEEP else 1.0
offset = float(sys.argv[2]) if not SWEEP else 24778.0   # measured signal centre
usedc  = int(sys.argv[3])   if not SWEEP else 0
HERE = os.path.dirname(os.path.abspath(__file__))
GZ   = os.path.join(HERE, 'testdata', 'dmr_real_capture.cf32.gz')
IQ   = os.path.join(tempfile.gettempdir(), 'securecom_dmr_real_capture.cf32')
if not os.path.exists(IQ):
    with gzip.open(GZ, 'rb') as fi, open(IQ, 'wb') as fo:
        shutil.copyfileobj(fi, fo)


class Chain(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)
        src = blocks.file_source(gr.sizeof_gr_complex, IQ, False)
        xlate = filter.freq_xlating_fir_filter_ccf(
            4, firdes.low_pass(1, FS_IN, 6250, 2000), offset, FS_IN)
        rs = filter.rational_resampler_ccf(interpolation=24, decimation=25,
                                          taps=[], fractional_bw=0.4)
        demod = analog.quadrature_demod_cf(gain)
        d = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.snk = blocks.vector_sink_f()
        if usedc:
            dcb = filter.dc_blocker_ff(1024, True)
            self.connect(src, xlate, rs, demod, dcb, d, self.snk)
        else:
            self.connect(src, xlate, rs, demod, d, self.snk)


def run_once(g, off, dc):
    global gain, offset, usedc
    gain, offset, usedc = g, off, dc
    tb = Chain(); tb.run()
    return np.array(tb.snk.data(), dtype=np.float32)


if SWEEP:
    print(f'\nreal captured DMR, offset {offset:.0f} Hz -- sweeping demod gain\n')
    print(f'{"gain":>7} {"samples":>9} {"rms dBFS":>10} {"peak":>7}  verdict')
    print('-'*48)
    for g in (0.2, 1.0, 3.93):   # the three that matter: low, correct, textbook-but-broken
        a = run_once(g, offset, usedc)
        r = float(np.sqrt(np.mean(a**2))) if len(a) else 0.0
        db = 20*np.log10(r) if r > 1e-9 else -200.0
        pk = float(np.abs(a).max()) if len(a) else 0.0
        v = 'DECODES' if db > -60 else 'silence'
        print(f'{g:7.2f} {len(a):9d} {db:10.1f} {pk:7.3f}  {v}')
    print()
    sys.exit(0)

tb = Chain()
tb.run()
a = np.array(tb.snk.data(), dtype=np.float32)
tag = f'gain={gain} off={offset:.0f} dcblock={usedc}'
if len(a):
    rms = float(np.sqrt(np.mean(a ** 2)))
    db = 20 * np.log10(rms) if rms > 1e-9 else -200.0
    nz = float(np.mean(np.abs(a) > 1e-6) * 100)
    print(f'RESULT {tag} samples={len(a)} rms={db:.1f}dBFS peak={np.abs(a).max():.4f} nonzero={nz:.1f}%', flush=True)
else:
    print(f'RESULT {tag} samples=0 NO_AUDIO', flush=True)
