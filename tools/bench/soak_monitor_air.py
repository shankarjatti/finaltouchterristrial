#!/usr/bin/env python3
"""Soak monitor for the AIR & MARITIME backend (decoder + bridge). Samples the running system only.

  python3 tools/bench/soak_monitor_air.py 1800 /path/air_soak.csv /path/adsb_file_truth.json

Every 20 s one CSV row: process alive/RSS/CPU (replay source, bridge, decoder), ZMQ message counts
(9201 AIS sentences, 9202 ADS-B decoded, 9203 raw CRC-valid Mode-S frames), bridge WebSocket traffic,
targets currently on the map, and two integrity checks:
  * false aircraft  : an ICAO the bridge shows that is not in the recording's known list (truth json)
  * implausible fix : a position farther than MAX_KM from the recording's receiver (London)
At the end <csv>.summary.json holds those findings and the observed message schema (type -> keys).
"""
import asyncio
import csv
import glob
import json
import math
import os
import sys
import threading
import time

import pmt
import websockets
import zmq

DURATION = float(sys.argv[1])
OUT = sys.argv[2]
TRUTH = set(json.load(open(sys.argv[3]))) if len(sys.argv) > 3 else set()
CENTER = (51.47, -0.45)
MAX_KM = 400.0
INTERVAL = 20.0
PROCS = {'source': 'replay_iq_tcp.py', 'bridge': 'airmaritime_bridge.py', 'decoder': 'airmaritime_decoder_live.py'}
TICK = os.sysconf('SC_CLK_TCK')

lock = threading.Lock()
S = {'ais_msgs': 0, 'ais_payloads': set(), 'adsb_msgs': 0, 'raw_msgs': 0, 'raw_icao': set(), 'ws_msgs': 0,
     'ws_types': {}, 'schema': {}, 'aircraft': {}, 'vessels': {}, 'false_aircraft': set(), 'bad_fixes': [],
     'all_aircraft': set(), 'all_vessels': set(), 'errors': []}


def km(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def zmq_thread(port, kind):
    s = zmq.Context().socket(zmq.SUB)
    s.connect(f'tcp://127.0.0.1:{port}')
    s.setsockopt(zmq.SUBSCRIBE, b'')
    s.setsockopt(zmq.RCVTIMEO, 500)
    while True:
        try:
            p = pmt.deserialize_str(s.recv())
        except zmq.Again:
            continue
        except Exception:
            return
        try:
            with lock:
                if kind == 'ais':
                    txt = bytes(pmt.u8vector_elements(pmt.cdr(p))).decode(errors='replace')
                    S['ais_msgs'] += 1
                    S['ais_payloads'].add(txt.split(',')[5])
                elif kind == 'adsb':
                    S['adsb_msgs'] += 1
                else:
                    bits = list(pmt.u8vector_elements(pmt.cdr(p)))
                    S['raw_msgs'] += 1
                    S['raw_icao'].add('%06X' % int(''.join(map(str, bits[8:32])), 2))
        except Exception as e:
            with lock:
                S['errors'].append(f'zmq {kind}: {e!r}')


async def ws_loop():
    while True:
        try:
            async with websockets.connect('ws://127.0.0.1:8887', max_size=None) as ws:
                while True:
                    d = json.loads(await ws.recv())
                    t = d.get('type')
                    with lock:
                        S['ws_msgs'] += 1
                        S['ws_types'][t] = S['ws_types'].get(t, 0) + 1
                        S['schema'].setdefault(t, set()).update(d.keys())
                        if t == 'init_state':
                            for a in d.get('adsb_aircraft', []):
                                S['aircraft'][a['icao']] = a
                            for v in d.get('ais_vessels', []):
                                S['vessels'][v['mmsi']] = v
                        elif t == 'adsb_update':
                            a = d['target']; ic = a['icao']
                            S['aircraft'][ic] = a; S['all_aircraft'].add(ic)
                            S['schema'].setdefault('adsb_update.target', set()).update(a.keys())
                            if TRUTH and ic not in TRUTH:
                                S['false_aircraft'].add(ic)
                            if a.get('lat') is not None and km(CENTER[0], CENTER[1], a['lat'], a['lon']) > MAX_KM:
                                S['bad_fixes'].append((ic, a['lat'], a['lon']))
                        elif t == 'adsb_remove':
                            S['aircraft'].pop(d.get('icao'), None)
                        elif t == 'ais_update':
                            v = d['target']; S['vessels'][v['mmsi']] = v; S['all_vessels'].add(v['mmsi'])
                            S['schema'].setdefault('ais_update.target', set()).update(v.keys())
                        elif t == 'ais_remove':
                            S['vessels'].pop(d.get('mmsi'), None)
                        elif t == 'error':
                            S['errors'].append(str(d)[:160])
        except Exception:
            await asyncio.sleep(1.0)


def pids(pattern):
    out = []
    for p in glob.glob('/proc/[0-9]*'):
        try:
            cmd = open(p + '/cmdline', 'rb').read().replace(b'\0', b' ').decode(errors='replace')
        except OSError:
            continue
        if pattern in cmd and 'soak_monitor' not in cmd and 'pgrep' not in cmd:
            out.append(int(p.split('/')[-1]))
    return out


def stats(pid):
    try:
        st = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
        return int(st[11]) + int(st[12]), int(open(f'/proc/{pid}/statm').read().split()[1]) * os.sysconf('SC_PAGE_SIZE') // 1024
    except (OSError, IndexError):
        return None, None


def main():
    for port, kind in ((9201, 'ais'), (9202, 'adsb'), (9203, 'raw')):
        threading.Thread(target=zmq_thread, args=(port, kind), daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(ws_loop()), daemon=True).start()
    cols = (['t_s'] + [f'alive_{k}' for k in PROCS] + [f'rss_mb_{k}' for k in PROCS] + [f'cpu_pct_{k}' for k in PROCS]
            + ['ais_msgs', 'ais_unique_total', 'adsb_msgs', 'raw_frames', 'raw_icao_total', 'ws_msgs',
               'aircraft_on_map', 'aircraft_with_pos', 'vessels_on_map', 'false_aircraft_total', 'bad_fixes_total'])
    f = open(OUT, 'w', newline='')
    w = csv.writer(f)
    w.writerow(cols)
    t0 = time.time()
    prev_j = {k: None for k in PROCS}
    prev = {'ais_msgs': 0, 'adsb_msgs': 0, 'raw_msgs': 0, 'ws_msgs': 0}
    time.sleep(1.0)
    while time.time() - t0 < DURATION:
        ta = time.time()
        row = {'t_s': round(ta - t0)}
        for k, pat in PROCS.items():
            ps = pids(pat)
            row[f'alive_{k}'] = 1 if ps else 0
            jf = rss = 0
            for p in ps:
                j, r = stats(p)
                if j is not None:
                    jf += j; rss += r
            row[f'rss_mb_{k}'] = round(rss / 1024.0, 1)
            pj = prev_j[k]
            row[f'cpu_pct_{k}'] = round(100.0 * (jf - pj[0]) / TICK / (ta - pj[1]), 1) if pj else ''
            prev_j[k] = (jf, ta)
        with lock:
            for k in ('ais_msgs', 'adsb_msgs', 'raw_msgs', 'ws_msgs'):
                row[{'raw_msgs': 'raw_frames'}.get(k, k)] = S[k] - prev[k]; prev[k] = S[k]
            row['ais_unique_total'] = len(S['ais_payloads']); row['raw_icao_total'] = len(S['raw_icao'])
            row['aircraft_on_map'] = len(S['aircraft'])
            row['aircraft_with_pos'] = sum(1 for a in S['aircraft'].values() if a.get('lat') is not None)
            row['vessels_on_map'] = len(S['vessels'])
            row['false_aircraft_total'] = len(S['false_aircraft']); row['bad_fixes_total'] = len(S['bad_fixes'])
        w.writerow([row.get(c, '') for c in cols]); f.flush()
        time.sleep(max(0.0, INTERVAL - (time.time() - ta)))
    with lock:
        out = {'duration_s': round(time.time() - t0), 'false_aircraft': sorted(S['false_aircraft']),
               'bad_fixes': S['bad_fixes'][:20], 'errors': S['errors'][:20],
               'aircraft_seen': len(S['all_aircraft']), 'vessels_seen': sorted(S['all_vessels']),
               'ws_types': S['ws_types'], 'schema': {k: sorted(v) for k, v in S['schema'].items()}}
    json.dump(out, open(OUT + '.summary.json', 'w'), indent=1)
    print('air soak monitor finished')


if __name__ == '__main__':
    main()
