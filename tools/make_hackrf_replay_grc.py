#!/usr/bin/env python3
"""Generate tools/hackrf_replay.grc -- the HackRF IQ replay as a GNU Radio Companion flowgraph.

Same signal path as tools/hackrf_replay.py, but openable/editable in GRC 3.10:

  wav (I=left,Q=right) -> [I/Q swap select] -> resample to 200 kSps -> x10 to 2 MSps
  -> frequency offset -> level -> Head (timed stop) -> osmocom sink (HackRF, amp OFF)

The HackRF is tuned `offset` below the wanted frequency and the signal shifted back
digitally, so the HackRF's own LO leakage stays outside the receiver's window; the
crystal error is pre-corrected: tune = freq / (1 + ppm*1e-6) - offset.

Everything adjustable is a GRC `parameter`, so it can be edited in GRC (double-click a
Parameter block) or overridden on the command line of the generated script:

  python3 hackrf_replay.py --wav-file "NXDN96 IQ.wav" --in-rate 48000 \
      --freq 451.09375e6 --ppm -6.24 --tx-gain 20 --duration 60
  python3 hackrf_replay.py --wav-file 1_ADS-B_LiveRecorded_2.4MSps.wav --in-rate 2400000 \
      --freq 1090e6 --ppm -6.24 --hackrf-rate 16e6 --offset 4e6 --tx-gain 20 --duration 90

Safe defaults: TX gain 0, RF amp off, stops by itself after `duration` seconds.
Use a CABLE + 30-40 dB attenuator into the receiver, never an antenna.

  python3 tools/make_hackrf_replay_grc.py tools/hackrf_replay.grc
"""
import sys

import yaml

DEFAULT_WAV = '/home/shankar/Downloads/tutorials/delhi_testing/all_protocols_wav_samples/NXDN/NXDN96 IQ.wav'


def blk(name, id_, params, x, y, state='enabled'):
    return {'name': name, 'id': id_, 'parameters': params,
            'states': {'bus_sink': False, 'bus_source': False, 'bus_structure': None,
                       'coordinate': [x, y], 'rotation': 0, 'state': state}}


def param(name, label, value, type_, short, x, y, comment=''):
    return blk(name, 'parameter', {'label': label, 'value': str(value),   # 'string' dtype: GRC stores the raw text, unquoted,
                                   'type': type_, 'short_id': short, 'hide': 'none', 'comment': comment}, x, y)


def var(name, value, x, y, comment=''):
    return blk(name, 'variable', {'value': value, 'comment': comment}, x, y)


def main():
    out = sys.argv[1]
    b = []
    b.append(blk('options', 'options', {
        'id': 'hackrf_replay', 'title': 'HackRF IQ replay (TX)', 'author': 'SecureCOM',
        'description': 'Replay a recorded IQ .wav through a HackRF on a chosen frequency. '
                       'Use a cable + 30-40 dB attenuator, never an antenna. Amp off, stops after `duration`.',
        'category': '[SecureCOM]', 'generate_options': 'no_gui', 'run_options': 'run',
        'output_language': 'python', 'realtime_scheduling': '', 'thread_safe_setters': '',
        'max_nouts': '0', 'catch_exceptions': 'True', 'window_size': '(1000,1000)',
        'placement': '(0,0)', 'sizing_mode': 'fixed', 'title_': ''}, 8, 8))
    b.append(blk('imp_fractions', 'import', {'imports': 'from fractions import Fraction\nimport math'}, 200, 12))

    # ---- parameters (edit these) ----
    b += [
        param('wav_file', 'IQ .wav file (stereo: I=left, Q=right)', DEFAULT_WAV, 'str', 'f', 8, 100),
        param('in_rate', 'Sample rate of the .wav (Hz)', 48000, 'intx', 'r', 8, 180,
              'NXDN96/NXDN48/TETRA IQ.wav = 48000, AIS sample = 250000, DMR/P25 72k files = 72125'),
        param('freq', 'On-air frequency (Hz)', '451.09375e6', 'eng_float', 'F', 8, 260,
              'NXDN96 451.09375e6, P25 450.09375e6, TETRA 420e6, AIS centre 162.000e6'),
        param('ppm', 'HackRF crystal error (ppm)', '-6.24', 'eng_float', 'p', 8, 340,
              "measured on this bench's HackRF; 0 for no correction"),
        param('tx_gain', 'HackRF TX VGA gain (dB, 0-47)', 0, 'intx', 'g', 8, 420,
              'start at 0 and raise; the +14 dB RF amp is permanently OFF'),
        param('duration', 'Stop after (seconds)', '60', 'eng_float', 'd', 8, 500),
        param('swap_iq', 'Swap I/Q (0 = no, 1 = yes)', 0, 'intx', 's', 8, 580,
              'TETRA IQ.wav stores Q left / I right -> 1'),
        param('offset', 'HackRF offset below the carrier (Hz)', '500e3', 'eng_float', 'o', 8, 660),
        param('scale', 'Digital level before the DAC', '0.5', 'eng_float', 'l', 8, 740),
        param('hackrf_rate', 'HackRF sample rate (2e6 narrowband; e.g. 16e6 for ADS-B)', '2e6', 'eng_float', 'R', 8, 820,
              'above 2e6 the wav goes straight to this rate (no 200 kSps stage); ADS-B: 16e6 with offset 4e6'),
    ]
    # ---- derived variables ----
    b += [
        var('base_rate', '200000 if hackrf_rate == 2e6 else int(hackrf_rate)', 232, 100,
            'stage-1 target: 200 kSps (narrowband) or straight to hackrf_rate (wideband)'),
        var('r1', 'Fraction(int(base_rate), int(in_rate)).limit_denominator(1000)', 232, 228,
            'stage-1 resample ratio: wav rate -> base_rate'),
        var('interp2', 'int(hackrf_rate // base_rate)', 232, 292, 'stage-2 interpolation (x10 narrowband, x1 wideband)'),
        var('tx_bw', '1.75e6 if hackrf_rate == 2e6 else 0.75 * hackrf_rate', 232, 420,
            'HackRF baseband filter: must pass the signal at +offset'),
        var('tune_freq', 'freq / (1 + ppm * 1e-6) - offset', 232, 356,
            'HackRF centre: crystal-corrected and moved down by the offset'),
    ]
    # ---- signal chain (left to right) ----
    y0 = 460
    b += [
        blk('wav', 'blocks_wavfile_source', {'file': 'wav_file', 'repeat': 'True', 'nchan': '2',
                                              'affinity': '', 'alias': '', 'comment': 'loops forever; Head stops it'}, 232, y0),
        blk('iq_straight', 'blocks_float_to_complex', {'vlen': '1', 'affinity': '', 'alias': '', 'comment': 'I=left, Q=right'}, 480, y0 - 40),
        blk('iq_swapped', 'blocks_float_to_complex', {'vlen': '1', 'affinity': '', 'alias': '', 'comment': 'I=right, Q=left'}, 480, y0 + 120),
        blk('iq_select', 'blocks_selector', {'type': 'complex', 'num_inputs': '2', 'num_outputs': '1',
                                              'input_index': 'swap_iq', 'output_index': '0', 'vlen': '1',
                                              'showports': 'True', 'enabled': 'True', 'affinity': '', 'alias': '', 'comment': ''}, 720, y0),
        blk('to_200k', 'rational_resampler_xxx', {'type': 'ccc', 'interp': 'r1.numerator', 'decim': 'r1.denominator',
                                                   'taps': '[]', 'fbw': '0.4', 'affinity': '', 'alias': '', 'comment': 'wav rate -> base_rate'}, 940, y0),
        blk('to_2M', 'rational_resampler_xxx', {'type': 'ccc', 'interp': 'interp2', 'decim': '1',
                                                 'taps': '[]', 'fbw': '0.4', 'affinity': '', 'alias': '', 'comment': 'base_rate -> hackrf_rate'}, 1170, y0),
        blk('shift', 'blocks_rotator_cc', {'phase_inc': '2 * math.pi * offset / hackrf_rate', 'tag_inc_update': 'False',
                                           'affinity': '', 'alias': '', 'comment': 'moves the signal up by `offset`'}, 1400, y0),
        blk('level', 'blocks_multiply_const_vxx', {'type': 'complex', 'const': 'scale', 'vlen': '1',
                                                    'affinity': '', 'alias': '', 'comment': 'keeps the HackRF DAC from clipping'}, 1620, y0),
        blk('stop_after', 'blocks_head', {'type': 'complex', 'num_items': 'int(duration * hackrf_rate)', 'vlen': '1',
                                          'affinity': '', 'alias': '', 'comment': 'timed stop: the flowgraph ends by itself'}, 1830, y0),
        blk('hackrf_tx', 'osmosdr_sink', {'args': '"hackrf=0"', 'sync': 'sync', 'num_mboards': '1', 'clock_source0': '',
                                          'time_source0': '', 'nchan': '1', 'sample_rate': 'hackrf_rate',
                                          'freq0': 'tune_freq', 'corr0': '0', 'gain0': '0', 'if_gain0': 'tx_gain',
                                          'bb_gain0': '0', 'ant0': '', 'bw0': 'tx_bw', 'affinity': '', 'alias': '',
                                          'comment': 'RF (amp) gain 0 = OFF. IF gain = TX VGA.'}, 2050, y0),
    ]
    conns = [
        ['wav', '0', 'iq_straight', '0'], ['wav', '1', 'iq_straight', '1'],
        ['wav', '1', 'iq_swapped', '0'], ['wav', '0', 'iq_swapped', '1'],
        ['iq_straight', '0', 'iq_select', '0'], ['iq_swapped', '0', 'iq_select', '1'],
        ['iq_select', '0', 'to_200k', '0'], ['to_200k', '0', 'to_2M', '0'], ['to_2M', '0', 'shift', '0'],
        ['shift', '0', 'level', '0'], ['level', '0', 'stop_after', '0'], ['stop_after', '0', 'hackrf_tx', '0'],
    ]
    # a note block for anyone opening it
    b.append(blk('safety_note', 'note', {'note': 'SAFETY: transmit only through a CABLE + 30-40 dB attenuator into the '
                                                 'receiver. Never into an antenna. TX gain starts at 0, RF amp is off, '
                                                 'the flowgraph stops itself after `duration` seconds.'}, 8, 820))
    # GRC stores the options block as a top-level key and the rest under blocks
    options = b[0]
    doc = {'options': {'parameters': options['parameters'], 'states': options['states']},
           'blocks': b[1:], 'connections': conns, 'metadata': {'file_format': 1, 'grc_version': '3.10.1.1'}}
    with open(out, 'w') as f:
        yaml.safe_dump(doc, f, default_flow_style=False, sort_keys=False, width=1000)
    print(f'{out}: {len(b) - 1} blocks, {len(conns)} connections')


if __name__ == '__main__':
    main()
