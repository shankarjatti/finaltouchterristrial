#!/usr/bin/env python3
"""Transmit a recorded IQ file from a HackRF into the B210, over a CABLE.

Lets NXDN / P25 / TETRA be tested through the whole live system (B210, Module 1,
decoder, bridge, UI) without owning those radios:

    HackRF ANTENNA --SMA cable--[30-40 dB attenuator]--SMA cable-- B210 RX2

Never connect antennas: transmitting on these frequencies over the air needs a
licence. The attenuator also keeps the B210 input safe.

The input is either a stereo IQ .wav (I = left, Q = right, as SDR# and the
samples in all_protocols_wav_samples/ use) at any rate, or raw complex64 IQ at
200 kSps (the format Module 1 streams). The signal must be centred at 0 Hz.
It is looped forever.

The HackRF is tuned --offset away from --freq and the signal is shifted back
digitally, so the HackRF's own LO leakage lands outside the B210's 200 kHz window.

  python3 tools/hackrf_replay.py --file "NXDN96 IQ.wav" --freq 451.09375e6
  python3 tools/hackrf_replay.py --file p25_capture.cf32 --freq 450.09375e6 --tx-gain 10
  python3 tools/hackrf_replay.py --file "NXDN96 IQ.wav" --freq 451.09375e6 --dry-run

Band frequencies (must match module1/src/main.cpp):
  DMR446 446.118528e6   NXDN96 451.09375e6   P25 450.09375e6   TETRA 420.0e6
"""
import argparse
import signal
import sys
import time
import wave
from fractions import Fraction

from gnuradio import blocks, filter, gr

HACKRF_RATE = 2e6          # lowest rate the HackRF supports
BASE_RATE = 200e3          # everything is brought to Module 1's rate first
INTERP = 10                # 200 kSps -> 2 MSps


class Replay(gr.top_block):
    def __init__(self, a):
        gr.top_block.__init__(self, 'hackrf_replay')
        if a.file.lower().endswith('.wav'):
            with wave.open(a.file) as w:
                if w.getnchannels() != 2:
                    raise SystemExit(f'{a.file}: need a stereo I/Q wav, got {w.getnchannels()} channel(s)')
                wav_rate = w.getframerate()
            wav = blocks.wavfile_source(a.file, True)
            iq = blocks.float_to_complex(1)
            self.connect((wav, 0), (iq, 0))
            self.connect((wav, 1), (iq, 1))
            r = Fraction(int(BASE_RATE), wav_rate).limit_denominator(1000)
            to_base = filter.rational_resampler_ccc(interpolation=r.numerator, decimation=r.denominator,
                                                     taps=[], fractional_bw=0.4)
            self.connect(iq, to_base)
            src = to_base
            print(f'{a.file}: stereo IQ wav at {wav_rate} Hz, resampled x{r.numerator}/{r.denominator} to 200 kSps')
        else:
            src = blocks.file_source(gr.sizeof_gr_complex, a.file, True)
        # keep peaks under full scale so the HackRF DAC never clips
        level = blocks.multiply_const_cc(a.scale)
        up = filter.rational_resampler_ccc(interpolation=INTERP, decimation=1, taps=[], fractional_bw=0.4)
        # signal sits --offset above the HackRF's centre, i.e. exactly on --freq
        shift = blocks.rotator_cc(2 * 3.141592653589793 * a.offset / HACKRF_RATE)
        if a.dry_run:
            snk = blocks.null_sink(gr.sizeof_gr_complex)
            self.probe = blocks.probe_rate(gr.sizeof_gr_complex, 1000.0, 0.15)
            self.connect(shift, self.probe)
        else:
            import osmosdr
            snk = osmosdr.sink(args=f'numchan=1 {a.device}')
            snk.set_sample_rate(HACKRF_RATE)
            # the HackRF's crystal is off by a.ppm; its samples come from the same clock, so
            # the whole output scales by (1 + ppm). Pre-scale the tuning to land on --freq.
            snk.set_center_freq(a.freq / (1 + a.ppm * 1e-6) - a.offset, 0)
            snk.set_gain(14 if a.amp else 0, 'RF', 0)      # HackRF TX amp: 0 = off, 14 dB = on
            snk.set_gain(a.tx_gain, 'IF', 0)              # TX VGA, 0-47 dB
            snk.set_bandwidth(1.75e6, 0)
        self.connect(src, level, up, shift, snk)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--file', required=True, help='complex64 IQ, signal centred at 0 Hz')
    ap.add_argument('--freq', type=float, required=True, help='on-air centre frequency, Hz')
    ap.add_argument('--offset', type=float, default=500e3, help='HackRF tuned this far below --freq (default 500e3)')
    ap.add_argument('--ppm', type=float, default=0.0,
                    help='HackRF frequency error in ppm (measured: negative = transmits low). '
                         'Find it with tools/bench/rf_spectrum.py: ppm = offset_Hz / freq_MHz')
    ap.add_argument('--tx-gain', type=float, default=0, help='HackRF TX VGA 0-47 dB (default 0, start low)')
    ap.add_argument('--amp', action='store_true', help='enable the HackRF +14 dB TX amp (normally leave off)')
    ap.add_argument('--scale', type=float, default=0.5, help='digital level before the DAC (default 0.5)')
    ap.add_argument('--device', default='hackrf=0', help='osmosdr device string (default hackrf=0)')
    ap.add_argument('--dry-run', action='store_true', help='build and run the chain into a null sink, no hardware')
    a = ap.parse_args()

    tb = Replay(a)
    tb.start()
    mode = 'DRY RUN (null sink)' if a.dry_run else f'TX on {a.freq / 1e6:.5f} MHz (ppm corr {a.ppm:+g}), VGA {a.tx_gain:g} dB, amp {"ON" if a.amp else "off"}'
    print(f'hackrf_replay: {a.file} looped, {mode}. Ctrl-C to stop.', flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        if a.dry_run:
            time.sleep(3)
            print(f'dry run OK: {tb.probe.rate() / 1e6:.2f} MSps through the chain (expect ~2 at full speed or more)')
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        tb.stop()
        tb.wait()


if __name__ == '__main__':
    main()
