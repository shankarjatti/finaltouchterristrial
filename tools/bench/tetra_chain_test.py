#!/usr/bin/env python3
"""Run the TETRA demod chain from allinone.grc / tetra_native_rx11.grc on a recording,
at either input rate, and report what tetra-kit decoded.

  python3 tools/bench/tetra_chain_test.py "TETRA IQ.wav" --rate 48000  --decim 1   # standalone path
  python3 tools/bench/tetra_chain_test.py "TETRA IQ.wav" --rate 200000 --decim 5   # coupled path

Chain (identical in both flowgraphs):
  freq_xlating(decim, LPF 12.5 kHz, offset) -> mmse_resampler(to 36 kSps) -> feedforward AGC
  -> FLL band-edge -> PFB clock sync (RRC) -> CMA equalizer -> diff phasor
  -> DQPSK decoder -> map -> unpack bits -> tetra_decoder_block
Prints a one-line summary: BSCH/MAC-SYNC lines seen and the block's TOTALS.
"""
import argparse
import os
import sys
import time
import wave
from fractions import Fraction

from gnuradio import analog, blocks, digital, filter, gr
from gnuradio.filter import firdes


def tetra_block():
    # same lookup the flowgraphs use: walk up to delhi_testing/tetra_test/gr_tetra_decoder
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        c = os.path.join(d, 'tetra_test', 'gr_tetra_decoder')
        if os.path.isdir(c):
            sys.path.insert(0, c)
            break
        d = os.path.dirname(d)
    from tetra_decoder_block import tetra_decoder_block
    return tetra_decoder_block(log_level=1, remove_fill_bits=True, wireshark_output=False, debug=True)


class Chain(gr.top_block):
    def __init__(self, a):
        gr.top_block.__init__(self, 'tetra_chain_test')
        sps, nfilts, channel_rate = 2, 32, 36000
        constel = digital.constellation_dqpsk().base()
        rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0 / float(sps), 0.35, 11 * sps * nfilts)

        # looped and paced at real time like a live stream: tetra-kit crashes at end of file
        wav = blocks.wavfile_source(a.file, True)
        iq = blocks.float_to_complex(1)
        # --swap-iq: left channel is Q, right is I (how TETRA IQ.wav is stored --
        # tetra_native_rx11.grc wires it this way)
        i_ch, q_ch = (1, 0) if a.swap_iq else (0, 1)
        self.connect((wav, i_ch), (iq, 0))
        self.connect((wav, q_ch), (iq, 1))
        with wave.open(a.file) as w:
            pace = blocks.throttle(gr.sizeof_gr_complex, w.getframerate(), True)
        self.connect(iq, pace)
        src = pace
        with wave.open(a.file) as w:
            fs = w.getframerate()
        if a.rate != fs:
            r = Fraction(int(a.rate), fs).limit_denominator(1000)
            rs = filter.rational_resampler_ccc(interpolation=r.numerator, decimation=r.denominator,
                                               taps=[], fractional_bw=0.4)
            self.connect(src, rs)
            src = rs
        taps = firdes.low_pass(1, a.rate, 12500, 12500 * 0.2) if a.taps == 'flowgraph' else \
            firdes.low_pass(1, a.rate, 12500, a.transition)
        self.xlat = filter.freq_xlating_fir_filter_ccc(a.decim, taps, a.offset, a.rate)
        mmse = filter.mmse_resampler_cc(0, float(a.rate) / (float(a.decim) * float(channel_rate)))
        agc = analog.feedforward_agc_cc(8, 1)
        fll = digital.fll_band_edge_cc(sps, 0.35, 45, 0.03141592653589793)
        clk = digital.pfb_clock_sync_ccf(sps, 0.06283185307179586, rrc_taps, nfilts, nfilts / 2, 1.5, sps)
        eq = digital.linear_equalizer(15, sps, digital.adaptive_algorithm_cma(constel, 10e-3, 1).base(),
                                      True, [], 'corr_est')
        diff = digital.diff_phasor_cc()
        dec = digital.constellation_decoder_cb(constel)
        mp = digital.map_bb(constel.pre_diff_code())
        unpack = blocks.unpack_k_bits_bb(constel.bits_per_symbol())
        self.tetra = tetra_block()
        self.connect(src, self.xlat, mmse, agc, fll, clk, eq, diff, dec, mp, unpack, self.tetra)
        self.slots = [blocks.vector_sink_f() for _ in range(4)]
        for k in range(4):
            self.connect((self.tetra, k), self.slots[k])
        print(f'chain: rate {a.rate:g}, decim {a.decim}, xlat taps {len(taps)}, '
              f'mmse ratio {float(a.rate) / (a.decim * channel_rate):.4f}, swap_iq {a.swap_iq}', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file')
    ap.add_argument('--rate', type=float, default=48000, help='rate the chain runs at (input is resampled to it)')
    ap.add_argument('--decim', type=int, default=1)
    ap.add_argument('--offset', type=float, default=-1714.0, help='carrier offset in Hz (default -1714)')
    ap.add_argument('--taps', choices=['flowgraph', 'custom'], default='flowgraph')
    ap.add_argument('--transition', type=float, default=2500.0)
    ap.add_argument('--swap-iq', action='store_true', help='wav stores Q on the left, I on the right')
    ap.add_argument('--secs', type=float, default=30.0, help='wall time to run')
    a = ap.parse_args()
    tb = Chain(a)
    tb.start()
    time.sleep(a.secs)
    # report from the sinks, then hard-exit: tetra-kit can crash while shutting down,
    # which would lose the block's own TOTALS line
    import numpy as np
    voice = [float(np.sum(np.abs(np.array(s.data())) > 1e-5)) / 8000.0 for s in tb.slots]
    print('RESULT voice seconds per timeslot: ' + ' '.join(f'TN{k + 1}={v:.2f}' for k, v in enumerate(voice)), flush=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
