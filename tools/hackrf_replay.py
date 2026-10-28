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

Wideband signals (ADS-B, 2.4 MSps recording): --hackrf-rate resamples the wav straight to that
rate (no 200 kSps stage). Keep --offset larger than half the B210's window so the HackRF's LO
leakage stays outside it (B210 ADS-B is 6 MSps = +-3 MHz):

  python3 tools/hackrf_replay.py --file 1_ADS-B_LiveRecorded_2.4MSps.wav --freq 1090e6 \
      --hackrf-rate 16e6 --offset 4e6 --tx-gain 20 --duration 90

Band frequencies (must match module1/src/main.cpp):
  DMR446 446.118528e6   NXDN96 451.09375e6   P25 450.09375e6   TETRA 420.0e6
"""
import argparse
import os
import signal
import sys
import threading
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
        wide = a.hackrf_rate != HACKRF_RATE
        self.hackrf_rate = hackrf_rate = a.hackrf_rate
        if a.file.lower().endswith('.wav'):
            with wave.open(a.file) as w:
                if w.getnchannels() != 2:
                    raise SystemExit(f'{a.file}: need a stereo I/Q wav, got {w.getnchannels()} channel(s)')
                wav_rate = w.getframerate()
            wav = blocks.wavfile_source(a.file, True)
            iq = blocks.float_to_complex(1)
            # --swap-iq: Q on the left, I on the right (TETRA IQ.wav is stored this way)
            i_ch, q_ch = (1, 0) if a.swap_iq else (0, 1)
            self.connect((wav, i_ch), (iq, 0))
            self.connect((wav, q_ch), (iq, 1))
            target = hackrf_rate if wide else BASE_RATE
            r = Fraction(int(target), wav_rate).limit_denominator(1000)
            to_base = filter.rational_resampler_ccc(interpolation=r.numerator, decimation=r.denominator,
                                                     taps=[], fractional_bw=0.4)
            if wide:
                # the recording's own DC (its receiver's LO leak) is not part of the signal
                dc = filter.dc_blocker_cc(1024, True)
                self.connect(iq, dc, to_base)
            else:
                self.connect(iq, to_base)
            src = to_base
            print(f'{a.file}: stereo IQ wav at {wav_rate} Hz, resampled x{r.numerator}/{r.denominator} '
                  f'to {target / 1e3:g} kSps')
        else:
            if wide:
                raise SystemExit('--hackrf-rate needs a .wav input (its sample rate is read from the file)')
            src = blocks.file_source(gr.sizeof_gr_complex, a.file, True)
        # keep peaks under full scale so the HackRF DAC never clips
        level = blocks.multiply_const_cc(a.scale)
        up = (blocks.copy(gr.sizeof_gr_complex) if wide else
              filter.rational_resampler_ccc(interpolation=INTERP, decimation=1, taps=[], fractional_bw=0.4))
        # signal sits --offset above the HackRF's centre, i.e. exactly on --freq
        shift = blocks.rotator_cc(2 * 3.141592653589793 * a.offset / hackrf_rate)
        if a.dry_run:
            snk = blocks.null_sink(gr.sizeof_gr_complex)
            self.probe = blocks.probe_rate(gr.sizeof_gr_complex, 1000.0, 0.15)
            self.connect(shift, self.probe)
        else:
            import osmosdr
            snk = osmosdr.sink(args=f'numchan=1 {a.device}')
            snk.set_sample_rate(hackrf_rate)
            # the HackRF's crystal is off by a.ppm; its samples come from the same clock, so
            # the whole output scales by (1 + ppm). Pre-scale the tuning to land on --freq.
            snk.set_center_freq(a.freq / (1 + a.ppm * 1e-6) - a.offset, 0)
            snk.set_gain(14 if a.amp else 0, 'RF', 0)      # HackRF TX amp: 0 = off, 14 dB = on
            snk.set_gain(a.tx_gain, 'IF', 0)              # TX VGA, 0-47 dB
            # baseband filter: must pass the signal at +offset (wideband: 0.75 x rate, HackRF's own default)
            snk.set_bandwidth(0.75 * hackrf_rate if wide else 1.75e6, 0)
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
    ap.add_argument('--swap-iq', action='store_true', help='wav stores Q left / I right (TETRA IQ.wav does)')
    ap.add_argument('--duration', type=float, default=0,
                    help='stop transmitting after this many seconds (0 = until Ctrl-C). Use it for over-the-air tests')
    ap.add_argument('--hackrf-rate', type=float, default=HACKRF_RATE,
                    help='HackRF sample rate (default 2e6, narrowband path via 200 kSps). Higher = wideband: '
                         'the wav is resampled straight to this rate, e.g. 16e6 for ADS-B')
    ap.add_argument('--dry-run', action='store_true', help='build and run the chain into a null sink, no hardware')
    a = ap.parse_args()

    tb = Replay(a)
    tb.start()
    limit = f', stops after {a.duration:g} s' if a.duration else ''
    mode = 'DRY RUN (null sink)' if a.dry_run else f'TX on {a.freq / 1e6:.5f} MHz (ppm corr {a.ppm:+g}), VGA {a.tx_gain:g} dB, amp {"ON" if a.amp else "off"}'
    print(f'hackrf_replay: {a.file} looped, {mode}{limit}. Ctrl-C to stop.', flush=True)

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    t_end = time.time() + (a.duration if a.duration else 3 if a.dry_run else float('inf'))
    while not stop.is_set() and time.time() < t_end:
        time.sleep(0.2)
    if a.dry_run:
        print(f'dry run OK: {tb.probe.rate() / 1e6:.2f} MSps through the chain (needs >= {a.hackrf_rate / 1e6:g} for real time)')

    # Stopping the osmosdr HackRF sink can hang; a transmitter must never outlive its
    # time limit, so force the process out if a clean stop takes longer than 3 s.
    threading.Timer(3.0, lambda: (print('hackrf_replay: stop hung, forcing exit', flush=True), os._exit(1))).start()
    tb.stop()
    tb.wait()
    print('hackrf_replay: TX stopped', flush=True)
    os._exit(0)

if __name__ == '__main__':
    main()
