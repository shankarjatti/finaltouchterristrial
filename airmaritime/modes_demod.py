#!/usr/bin/env python3
"""Mode-S / ADS-B demodulator block, a drop-in replacement for gnuradio.adsb's framer + demod.

Why: gr-adsb's demod reads ONE sample per half-bit at the framer's trigger position, with no
timing search. On a real 1090 MHz recording (1_ADS-B_LiveRecorded_2.4MSps.wav resampled to
4 MSps) it produced 173 DF17/18 frames in 10 s of which only 32 passed CRC; this block gets 140
CRC-valid frames from the same 10 s.

How: the input is complex IQ at fs (an even number of samples per microsecond, e.g. 4 MSps).
Magnitude is integrated over each half-bit (0.5 us), a vectorised preamble test (pulses at 0, 1,
3.5, 4.5 us, quiet in between) finds candidates relative to the measured noise floor -- no
absolute threshold -- then 112 PPM bits are sliced at a few sub-bit timing offsets and only
frames whose DF is 17/18 and whose CRC-24 remainder is 0 are published.

Outputs:
  * message port 'demodulated': the same PDU gr-adsb's demod emits --
    (dict(timestamp, snr) . u8vector of 112 bits) -- so adsb.decoder parses it unchanged.
  * stream 0 (float): the received amplitude |IQ|, delayed by `self.delay` samples, with a
    'burst' tag (value = (frame number, SNR dB)) at the preamble of every CRC-valid frame --
    trigger a time sink on it to see the real PPM pulses of decoded frames.
"""
import datetime

import numpy as np
import pmt
from gnuradio import gr

POLY = 0xFFF409
NBITS = 112


def crc24_remainder(bits):
    """bits: (N, 112) uint8 -> CRC-24 remainder per row (0 for a valid DF17/18 frame)."""
    reg = np.zeros(len(bits), dtype=np.int64)
    for i in range(NBITS):
        top = ((reg >> 23) & 1) ^ bits[:, i]
        reg = ((reg << 1) & 0xFFFFFF) ^ (top * POLY)
    return reg


class modes_demod(gr.sync_block):
    def __init__(self, fs=4e6, snr_db=6.0):
        gr.sync_block.__init__(self, name='modes_demod', in_sig=[np.complex64], out_sig=[np.float32])
        self.fs = float(fs)
        sps = self.fs / 1e6
        assert sps == int(sps) and int(sps) % 2 == 0, 'modes_demod needs an even number of samples per microsecond'
        self.h = int(sps) // 2                          # samples per half-bit (0.5 us)
        self.frame_len = 16 * self.h + 2 * self.h * NBITS + 4 * self.h   # preamble + data + margin
        self.min_ratio = 10 ** (snr_db / 10.0)          # preamble pulses vs noise floor (power)
        # Look-behind window carried between work() calls so a frame split across calls is still
        # seen. The output is delayed by exactly this many samples, so every frame is found while
        # its samples are still about to be written and can be tagged in place.
        self.delay = self.frame_len + 32 * self.h
        self.tail = np.zeros(self.delay, dtype=np.float32)
        self.burst_key = pmt.intern('burst')
        self.last_frame_abs = -10 ** 12
        self.start_ts = (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()
        self.port = pmt.intern('demodulated')
        self.message_port_register_out(self.port)
        self.frames = 0

    def work(self, input_items, output_items):
        x = input_items[0]
        n_in = len(x)
        m = np.concatenate([self.tail, (x.real * x.real + x.imag * x.imag).astype(np.float32)])
        # m[0] is the next sample to be written: output index nitems_written(0) + i <-> m[i]
        self._scan(m, self.nitems_written(0), n_in)
        output_items[0][:] = np.sqrt(m[:n_in])
        self.tail = m[n_in:]
        return n_in

    def _scan(self, m, base_abs, n_out):
        h = self.h
        # s[i]: power integrated over the half-bit starting at i
        c = np.concatenate([[0.0], np.cumsum(m, dtype=np.float64)])
        s = (c[h:] - c[:-h]).astype(np.float32)
        noise = float(np.median(s)) + 1e-20
        last = len(s) - (16 * h + 2 * h * NBITS + 2 * h)
        if last <= 0:
            return
        t = np.arange(last)
        hi = np.minimum.reduce([s[t], s[t + 2 * h], s[t + 7 * h], s[t + 9 * h]])
        lo = np.maximum.reduce([s[t + 4 * h], s[t + 5 * h], s[t + 6 * h],
                                s[t + 11 * h], s[t + 12 * h], s[t + 13 * h]])
        cand = np.flatnonzero((hi > self.min_ratio * noise) & (hi > 1.5 * lo))
        if not len(cand):
            return
        # strongest start in each cluster of adjacent candidates
        score = hi[cand]
        groups = np.concatenate([[0], np.flatnonzero(np.diff(cand) > 2 * h) + 1, [len(cand)]])
        starts = np.array([cand[a + np.argmax(score[a:b])] for a, b in zip(groups[:-1], groups[1:])])
        k = np.arange(NBITS) * 2 * h
        best = {}
        for off in range(-(h // 2), h // 2 + 1):
            st = starts + off
            st = st[(st >= 0) & (st + 16 * h + k[-1] + h < len(s))]
            if not len(st):
                continue
            first = s[st[:, None] + 16 * h + k]
            second = s[st[:, None] + 17 * h + k]
            bits = (first > second).astype(np.uint8)
            df = bits[:, 0] * 16 + bits[:, 1] * 8 + bits[:, 2] * 4 + bits[:, 3] * 2 + bits[:, 4]
            sel = (df == 17) | (df == 18)
            if not sel.any():
                continue
            ok = crc24_remainder(bits[sel]) == 0
            for b, t0 in zip(bits[sel][ok], st[sel][ok]):
                key = int(t0 - off)
                if key not in best:
                    best[key] = (b, t0)
        for key in sorted(best):
            b, t0 = best[key]
            if t0 >= n_out:          # not written yet: found again (and published) on a later call
                continue
            abs_t = base_abs + int(t0)
            if abs_t - self.last_frame_abs < 16 * h + 2 * h * NBITS:   # same frame seen again via the tail overlap
                continue
            self.last_frame_abs = abs_t
            snr = 10 * np.log10(max(float(s[t0]), 1e-20) / noise)
            meta = pmt.to_pmt({'timestamp': self.start_ts + abs_t / self.fs, 'snr': float(snr)})
            self.message_port_pub(self.port, pmt.cons(meta, pmt.to_pmt(b)))
            self.add_item_tag(0, abs_t, self.burst_key, pmt.to_pmt((self.frames, float(snr))))
            self.frames += 1
