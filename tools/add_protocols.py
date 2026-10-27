#!/usr/bin/env python3
"""Add the step-2 protocols (NXDN48, D-STAR, X2-TDMA, ProVoice) to allinone.grc.

Each new protocol gets the same single-chain design as DMR/NXDN/P25 (see
make_single_chain.py), cloned from the DMR chain, with its own channel plan:

    TCP source (Module 1 port) -> channelizer (N channels) -> sum of all N
    -> resampler to 48 kHz -> LPF -> squelch -> FM demod -> DSD (frame, mod)
    -> resampler x6 -> volume -> ZMQ tap (bridge) + own speaker output

| protocol | port | channels in 200 kHz | channel rate -> 48 kHz | LPF     | DSD frame / mod      |
| NXDN48   | 7005 | 32 x 6.25 kHz       | x192/25                | 3.0 kHz | NXDN48_IDAS / GFSK   |
| D-STAR   | 7006 | 16 x 12.5 kHz       | x96/25                 | 6.25 k  | DSTAR / GFSK         |
| X2-TDMA  | 7007 | 16 x 12.5 kHz       | x96/25                 | 6.25 k  | X2_TDMA / C4FM       |
| ProVoice | 7008 |  8 x 25 kHz         | x48/25                 | 9.5 k   | PROVOICE / GFSK      |

Rates follow each protocol's standard and DSD's own symbol timing at 48 kHz
(NXDN48 2400 baud = 20 samples/symbol, D-STAR and X2-TDMA 4800 baud = 10,
ProVoice 9600 baud = 5). Squelch -73 dB, volume 0.5 and demod gain 1.0 start
from the values measured for the first four (NXDN48 volume 3.0: its DSD output
peaks ~10 dB lower on the real recording); tune them once real signals exist.

  python3 tools/add_protocols.py allinone.grc
"""
import copy
import sys

import yaml

NEW = {
    'nxdn48':   dict(label='NXDN48',   port=7005, tap=9106, nch=32, interp=192, decim=25,
                     cutoff=3000, width=1000, frame='NXDN48_IDAS', mod='GFSK',
                     volume='3.0'),   # DSD's NXDN48 output peaks ~-16 dBFS on the real recording
    'dstar':    dict(label='D-STAR',   port=7006, tap=9107, nch=16, interp=96,  decim=25,
                     cutoff=6250, width=2000, frame='DSTAR',       mod='GFSK'),
    'x2tdma':   dict(label='X2-TDMA',  port=7007, tap=9108, nch=16, interp=96,  decim=25,
                     cutoff=6250, width=2000, frame='X2_TDMA',     mod='C4FM'),
    'provoice': dict(label='ProVoice', port=7008, tap=9109, nch=8,  interp=48,  decim=25,
                     cutoff=9500, width=2000, frame='PROVOICE',    mod='GFSK'),
}
# DMR's blocks are the template; map template name -> new name pattern
TEMPLATE = {
    'network_tcp_source_dmr': 'network_tcp_source_{p}',
    'pfb_channelizer_ccf_0':  'pfb_channelizer_{p}',
    'iq_sum_dmr':             'iq_sum_{p}',
    'resamp_iq_dmr':          'resamp_iq_{p}',
    'lpf_dmr':                'lpf_{p}',
    'squelch_dmr':            'squelch_{p}',
    'demod_dmr':              'demod_{p}',
    'dsd_dmr':                'dsd_{p}',
    'aresamp_dmr':            'aresamp_{p}',
    'vol_dmr':                'vol_{p}',
    'bridge_zmq_dmr':         'bridge_zmq_{p}',
    'audio_sink_dmr':         'audio_sink_{p}',
    'squelch_thresh_dmr':     'squelch_thresh_{p}',
    'volume_dmr':             'volume_{p}',
    'gain_demod':             'gain_demod_{p}',
}


def main():
    path = sys.argv[1]
    g = yaml.safe_load(open(path))
    blocks = {b['name']: b for b in g['blocks']}
    if 'dsd_nxdn48' in blocks:
        raise SystemExit(f'{path} already has the step-2 protocols')
    for i, (p, c) in enumerate(NEW.items(), start=1):
        nb = {}
        for tname, pattern in TEMPLATE.items():
            b = copy.deepcopy(blocks[tname])
            b['name'] = pattern.format(p=p)
            x, y = b['states']['coordinate']
            b['states']['coordinate'] = [x, y + 1400 * i]      # own row on the canvas
            nb[tname] = b
        P = lambda t: nb[t]['parameters']
        P('network_tcp_source_dmr')['port'] = str(c['port'])
        P('pfb_channelizer_ccf_0')['nchans'] = str(c['nch'])
        P('pfb_channelizer_ccf_0')['taps'] = f"firdes.low_pass({c['nch']}.0, samp_rate, (samp_rate/{c['nch']}.0)/2.0, 1000)"
        P('iq_sum_dmr')['num_inputs'] = str(c['nch'])
        P('resamp_iq_dmr').update(interp=str(c['interp']), decim=str(c['decim']))
        P('lpf_dmr').update(cutoff_freq=str(c['cutoff']), width=str(c['width']))
        P('squelch_dmr')['threshold'] = f'squelch_thresh_{p}'
        P('demod_dmr')['gain'] = f'gain_demod_{p}'
        P('dsd_dmr').update(frame=f"dsd.dsd_FRAME_{c['frame']}", mod=f"dsd.dsd_MOD_{c['mod']}")
        P('vol_dmr')['const'] = f'volume_{p}'
        P('bridge_zmq_dmr')['address'] = f"tcp://127.0.0.1:{c['tap']}"
        P('squelch_thresh_dmr').update(value='-73', label=f"Squelch {c['label']} (dB)")
        P('volume_dmr').update(value=c.get('volume', '0.5'), label=f"Volume {c['label']}")
        P('gain_demod').update(value='1.0', label=f"FM Demod Gain ({c['label']})")
        g['blocks'] += list(nb.values())

        n = lambda t: nb[t]['name']
        g['connections'].append([n('network_tcp_source_dmr'), '0', n('pfb_channelizer_ccf_0'), '0'])
        g['connections'] += [[n('pfb_channelizer_ccf_0'), str(k), n('iq_sum_dmr'), str(k)] for k in range(c['nch'])]
        for a, b in zip(['iq_sum_dmr', 'resamp_iq_dmr', 'lpf_dmr', 'squelch_dmr', 'demod_dmr', 'dsd_dmr', 'aresamp_dmr'],
                        ['resamp_iq_dmr', 'lpf_dmr', 'squelch_dmr', 'demod_dmr', 'dsd_dmr', 'aresamp_dmr', 'vol_dmr']):
            g['connections'].append([n(a), '0', n(b), '0'])
        g['connections'].append([n('vol_dmr'), '0', n('bridge_zmq_dmr'), '0'])
        g['connections'].append([n('vol_dmr'), '0', n('audio_sink_dmr'), '0'])
    with open(path, 'w') as f:
        yaml.safe_dump(g, f, default_flow_style=False, sort_keys=False, width=1000)
    print(f'{path}: added {", ".join(NEW)} -> {len(g["blocks"])} blocks, {len(g["connections"])} connections')


if __name__ == '__main__':
    main()
