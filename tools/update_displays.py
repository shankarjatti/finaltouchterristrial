#!/usr/bin/env python3
"""Give the decoder's shared Qt displays one trace per protocol, in the console's colours.

  qtgui_freq_sink_combined : raw IQ spectrum of all 8 bands (one trace per TCP source)
  qtgui_time_sink_dnp      : decoded audio of the 7 DSD protocols (TETRA's audio is
                             8 kHz and keeps its own qtgui_time_sink_tetra)

Colours are GRC's named Qt colours; the web console uses the same 8, so a band
looks the same in both. Also fixes the audio plot's rate: it was samp_rate (200 kSps)
on 48 kHz audio, which made its time axis ~4x too short. Safe to re-run.

  python3 tools/update_displays.py allinone.grc
"""
import sys

import yaml

# key, legend label, Qt colour name. GRC's Qt sinks only accept these named colours
# (blue, red, green, black, cyan, magenta, yellow, dark red, dark green, dark blue);
# yellow is unreadable on the white plot. The web console's --trace-* colours in
# gui/securecom_gui.html use the same 8 names, so a band looks the same in both.
BANDS = [
    ('dmr',      'DMR446 (7001)',   'blue'),
    ('nxdn',     'NXDN96 (7002)',   'red'),
    ('p25',      'P25 Ph1 (7003)',  'green'),
    ('tetra',    'TETRA (7004)',    'black'),
    ('nxdn48',   'NXDN48 (7005)',   'magenta'),
    ('dstar',    'D-STAR (7006)',   'cyan'),
    ('x2tdma',   'X2-TDMA (7007)',  'dark red'),
    ('provoice', 'ProVoice (7008)', 'dark blue'),
]
AUDIO_RATE = 48000


def set_traces(g, sink, sources, labels, colours, quoted, title):
    p = next(b for b in g['blocks'] if b['name'] == sink)['parameters']
    p['nconnections'] = str(len(sources))
    p['name'] = title
    for i in range(1, 11):
        on = i <= len(sources)
        p[f'label{i}'] = labels[i - 1] if on else ''
        c = colours[i - 1] if on else 'blue'
        p[f'color{i}'] = f'"{c}"' if quoted else c
    g['connections'] = [c for c in g['connections'] if c[2] != sink]
    g['connections'] += [[s, '0', sink, str(k)] for k, s in enumerate(sources)]
    return p


def main():
    path = sys.argv[1]
    g = yaml.safe_load(open(path))
    names = {b['name'] for b in g['blocks']}
    have = [b for b in BANDS if f'network_tcp_source_{b[0]}' in names]

    set_traces(g, 'qtgui_freq_sink_combined',
               [f'network_tcp_source_{k}' for k, _, _ in have], [l for _, l, _ in have], [c for _, _, c in have],
               quoted=True, title=f'SecureCOM Live Spectrum — {len(have)} bands (colours match the console)')

    audio = [b for b in have if f'vol_{b[0]}' in names]          # TETRA has no vol_ block
    tp = set_traces(g, 'qtgui_time_sink_dnp',
                    [f'vol_{k}' for k, _, _ in audio], [l.split(' (')[0] for _, l, _ in audio], [c for _, _, c in audio],
                    quoted=False, title=f'Decoded Audio — {len(audio)} DSD protocols (48 kHz)')
    tp['srate'] = str(AUDIO_RATE)

    with open(path, 'w') as f:
        yaml.safe_dump(g, f, default_flow_style=False, sort_keys=False, width=1000)
    print(f'{path}: spectrum {len(have)} traces, audio plot {len(audio)} traces at {AUDIO_RATE} Hz')


if __name__ == '__main__':
    main()
