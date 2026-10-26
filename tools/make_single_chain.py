#!/usr/bin/env python3
"""Rewrite allinone.grc so DMR, NXDN and P25 each run ONE decode chain.

Before: every channelizer output had its own resampler -> LPF -> squelch ->
demod -> DSD -> resampler -> volume (16 DMR + 16 NXDN + 10 P25 = 42 chains),
summed per protocol, all sharing one squelch and one volume.

After, per protocol (the dmr_test structure):
    channelizer (N ch) -> sum of all N -> resampler -> LPF -> squelch -> demod
    -> DSD -> resampler -> volume -> that protocol's ZMQ tap (+ speaker)

Also applies the settings measured on real recordings (Oct 2026):
  * each protocol gets its own squelch and volume slider
  * volume 0.5 (DSD peaks at -0.8 dBFS; 0.04 left voice near -48 dBFS)
  * NXDN demod gain 1.0 (7.28 decoded nothing; 1.0 decoded 14.2 of 15.3 s)
  * P25 demod gain 1.0 (on a real P25 Phase 1 recording, 4.24 gave 0 syncs; 0.5-2.0
    all sync and 1.0 puts DSD's input level at ~51%). Frame mode stays P25_PHASE_1:
    it syncs exactly as well as AUTO_DETECT and cannot false-sync on other modes.

Speaker output, --audio:
  mixed     one blocks_add_master -> one audio sink (as before)
  separate  one audio sink per protocol; the sound server mixes them, so no
            GNU Radio adder ties the protocols' throughput together

  python3 tools/make_single_chain.py allinone.grc out.grc --audio separate
"""
import argparse
import copy

import yaml

PROTOS = {  # protocol -> (channelizer block, number of channels)
    'dmr':  ('pfb_channelizer_ccf_0', 16),
    'nxdn': ('pfb_channelizer_ccf_0_1', 16),
    'p25':  ('pfb_channelizer_ccf_0_0', 10),
}
CHAIN = ['resamp_iq', 'lpf', 'squelch', 'demod', 'dsd', 'aresamp', 'vol']
LABEL = {'dmr': 'DMR', 'nxdn': 'NXDN', 'p25': 'P25'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--audio', choices=['mixed', 'separate'], required=True)
    a = ap.parse_args()

    g = yaml.safe_load(open(a.src))
    blocks = {b['name']: b for b in g['blocks']}
    conns = [list(c) for c in g['connections']]
    if 'iq_sum_dmr' in blocks:
        raise SystemExit('already single-chain: run this on the original allinone.grc')

    rename, drop = {}, set()
    for p, (pfb, n) in PROTOS.items():
        for fam in CHAIN:
            rename[f'{fam}_{p}_ch0'] = f'{fam}_{p}'
            drop.update(f'{fam}_{p}_ch{k}' for k in range(1, n))
        drop.add(f'audio_mix_{p}')

    # audio_mix_<p> fed the master adder and the ZMQ tap; vol_<p> feeds them now
    mix_outs = {p: [(c[2], c[3]) for c in conns if c[0] == f'audio_mix_{p}'] for p in PROTOS}

    new = []
    for c in conns:
        if c[0] in drop or c[2] in drop:
            continue
        # the channelizer -> ch0 resampler link is replaced by the summed path below
        if any(c[0] == pfb and c[2] == f'resamp_iq_{p}_ch0' for p, (pfb, _) in PROTOS.items()):
            continue
        new.append([rename.get(c[0], c[0]), c[1], rename.get(c[2], c[2]), c[3]])

    out_blocks = []
    for b in g['blocks']:
        if b['name'] in drop:
            continue
        b = copy.deepcopy(b)
        b['name'] = rename.get(b['name'], b['name'])
        out_blocks.append(b)
    ob = {b['name']: b for b in out_blocks}

    for p, (pfb, n) in PROTOS.items():
        # sum of all N channelizer outputs -> the single chain
        s = copy.deepcopy(blocks['audio_mix_dmr'])
        s['name'] = f'iq_sum_{p}'
        s['parameters'].update({'num_inputs': str(n), 'type': 'complex', 'vlen': '1'})
        x, y = blocks[pfb]['states']['coordinate']
        s['states']['coordinate'] = [x + 240, y]
        out_blocks.append(s)
        new += [[pfb, str(k), f'iq_sum_{p}', str(k)] for k in range(n)]
        new.append([f'iq_sum_{p}', '0', f'resamp_iq_{p}', '0'])
        new += [[f'vol_{p}', '0', dst, port] for dst, port in mix_outs[p]]

        # own squelch and volume per protocol
        # variable names must not collide with the renamed chain blocks (squelch_<p>, vol_<p>)
        for var, base, value, label in (('squelch_thresh', 'squelch_thresh', '-20', 'Squelch {} (dB)'),
                                        ('volume', 'volume', '0.5', 'Volume {}')):
            v = copy.deepcopy(blocks[base])
            v['name'] = f'{var}_{p}'
            v['parameters']['value'] = value
            v['parameters']['label'] = label.format(LABEL[p])
            vx, vy = v['states']['coordinate']
            v['states']['coordinate'] = [vx, vy + 70 * list(PROTOS).index(p)]
            out_blocks.append(v)
        ob[f'squelch_{p}']['parameters']['threshold'] = f'squelch_thresh_{p}'
        ob[f'vol_{p}']['parameters']['const'] = f'volume_{p}'

    out_blocks = [b for b in out_blocks if b['name'] not in ('squelch_thresh', 'volume')]
    ob = {b['name']: b for b in out_blocks}
    ob['gain_demod_nxdn']['parameters']['value'] = '1.0'
    ob['gain_demod_p25']['parameters']['value'] = '1.0'

    if a.audio == 'separate':
        master = ob['blocks_add_master']
        sink = ob['audio_sink_0']
        out_blocks = [b for b in out_blocks if b['name'] not in ('blocks_add_master', 'audio_sink_0')]
        new = [c for c in new if 'blocks_add_master' not in (c[0], c[2])]
        mx, my = master['states']['coordinate']
        for i, p in enumerate(PROTOS):
            s = copy.deepcopy(sink)
            s['name'] = f'audio_sink_{p}'
            s['states']['coordinate'] = [mx, my + 90 * i]
            out_blocks.append(s)
            new.append([f'vol_{p}', '0', f'audio_sink_{p}', '0'])
        # the shared audio time plot gets one trace per protocol instead of the mix
        ts = next(b for b in out_blocks if b['name'] == 'qtgui_time_sink_dnp')
        ts['parameters']['nconnections'] = str(len(PROTOS))
        for i, p in enumerate(PROTOS, start=1):
            ts['parameters'][f'label{i}'] = LABEL[p]
            new.append([f'vol_{p}', '0', 'qtgui_time_sink_dnp', str(i - 1)])

    g['blocks'] = out_blocks
    g['connections'] = new
    with open(a.dst, 'w') as f:
        yaml.safe_dump(g, f, default_flow_style=False, sort_keys=False, width=1000)
    print(f'{a.dst}: {len(out_blocks)} blocks, {len(new)} connections, audio={a.audio}')


if __name__ == '__main__':
    main()
