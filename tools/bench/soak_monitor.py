#!/usr/bin/env python3
"""Soak monitor for the terrestrial stack: samples the RUNNING system, changes nothing.

  python3 tools/bench/soak_monitor.py 1800 /path/to/soak.csv

Every INTERVAL s it records (one CSV row): process alive + resident memory + CPU of Module 1, the
bridge and the decoder (allinone), the B210's USB link speed, how many schedule steps the bridge
reported, bridge WebSocket messages received (is it responsive?), seconds of decoded voice on a
protocol's audio tap (all 8 taps), module1/bridge log lines that look like errors or
data drops, and the size of gui/recordings. A summary is printed at the end.
"""
import asyncio
import csv
import glob
import json
import os
import re
import sys
import threading
import time

import numpy as np
import websockets
import zmq

DURATION = float(sys.argv[1])
OUT = sys.argv[2]
TAPS = {9101: ('dmr', 48000), 9102: ('nxdn', 48000), 9103: ('p25', 48000), 9104: ('tetra', 8000),
        9106: ('nxdn48', 48000), 9107: ('dstar', 48000), 9108: ('x2tdma', 48000), 9109: ('provoice', 48000)}
INTERVAL = 20.0
HERE = os.path.dirname(os.path.abspath(__file__))
REC_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'gui', 'recordings'))
PROCS = {'source': 'replay_bands.py', 'bridge': 'bridge_server.py', 'decoder': 'allinone.py'}   # source = Module 1 or the IQ replay
ERR_RE = re.compile(r'error|overflow|underrun|fail|exception|traceback|timeout|exit code|terminat|disconnected', re.I)
TICK = os.sysconf('SC_CLK_TCK')

state = {'voice': {n: 0 for n, _ in TAPS.values()}, 'tap_msgs': 0, 'ws_msgs': 0, 'steps': 0, 'last_step': None,
         'errors': [], 'drops': [], 'cycle': None}
lock = threading.Lock()


def tap_thread(port, name):
    s = zmq.Context().socket(zmq.SUB)
    s.connect(f'tcp://127.0.0.1:{port}')
    s.setsockopt(zmq.SUBSCRIBE, b'')
    s.setsockopt(zmq.RCVTIMEO, 500)
    while True:
        try:
            x = np.frombuffer(s.recv(), dtype=np.float32)
        except zmq.Again:
            continue
        except Exception:
            return
        with lock:
            state['tap_msgs'] += 1
            state['voice'][name] += int(np.count_nonzero(np.abs(x) > 1e-4))


async def ws_loop():
    while True:
        try:
            async with websockets.connect('ws://127.0.0.1:8787', max_size=None) as ws:
                while True:
                    d = json.loads(await ws.recv())
                    with lock:
                        state['ws_msgs'] += 1
                        t = d.get('type')
                        if t == 'status':
                            cur = (d.get('cycle'), d.get('active_band'))
                            if cur != state['last_step']:
                                state['last_step'] = cur
                                state['steps'] += 1
                            state['cycle'] = d.get('cycle')
                        elif t == 'log':
                            txt = d.get('text', '')
                            if 'slow client' in txt:
                                state['drops'].append(txt.strip()[:100])
                            elif ERR_RE.search(txt):
                                state['errors'].append(txt.strip()[:140])
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


def proc_stats(pid):
    try:
        st = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
        jiff = int(st[11]) + int(st[12])
        rss_kb = int(open(f'/proc/{pid}/statm').read().split()[1]) * os.sysconf('SC_PAGE_SIZE') // 1024
        return jiff, rss_kb
    except (OSError, IndexError):
        return None, None


def usb_speed():
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if open(d + '/idVendor').read().strip() == '2500':
                return int(open(d + '/speed').read().strip())
        except OSError:
            pass
    return 0


def rec_mb():
    return sum(os.path.getsize(f) for f in glob.glob(REC_DIR + '/*.wav')) / 1e6


def main():
    for port, (name, _) in TAPS.items():
        threading.Thread(target=tap_thread, args=(port, name), daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(ws_loop()), daemon=True).start()
    cols = (['t_s', 'alive_source', 'alive_bridge', 'alive_decoder', 'rss_mb_source', 'rss_mb_bridge', 'rss_mb_decoder',
             'cpu_pct_source', 'cpu_pct_bridge', 'cpu_pct_decoder', 'usb_mbps', 'steps', 'cycle', 'ws_msgs', 'tap_msgs']
            + ['voice_s_' + n for n, _ in TAPS.values()] + ['new_errors', 'new_drops', 'rec_mb'])
    f = open(OUT, 'w', newline='')
    w = csv.writer(f)
    w.writerow(cols)
    f.flush()
    t0 = time.time()
    prev = {k: (None, None) for k in PROCS}
    prev_state = {'voice': {n: 0 for n, _ in TAPS.values()}, 'steps': 0, 'ws_msgs': 0, 'tap_msgs': 0, 'errors': 0, 'drops': 0}
    time.sleep(1.0)
    while time.time() - t0 < DURATION:
        t_a = time.time()
        row = {'t_s': round(t_a - t0)}
        cur_j = {}
        for k, pat in PROCS.items():
            ps = pids(pat)
            row['alive_' + k] = 1 if ps else 0
            jiff = rss = 0
            for p in ps:
                j, r = proc_stats(p)
                if j is not None:
                    jiff += j
                    rss += r
            cur_j[k] = (jiff, t_a)
            row['rss_mb_' + k] = round(rss / 1024.0, 1)
            pj, pt = prev[k]
            row['cpu_pct_' + k] = round(100.0 * (jiff - pj) / TICK / (t_a - pt), 1) if pj is not None and t_a > pt else ''
        prev = cur_j
        row['usb_mbps'] = usb_speed()
        with lock:
            row['steps'] = state['steps'] - prev_state['steps']
            row['cycle'] = state['cycle']
            row['ws_msgs'] = state['ws_msgs'] - prev_state['ws_msgs']
            row['tap_msgs'] = state['tap_msgs'] - prev_state['tap_msgs']
            for port, (name, rate) in TAPS.items():
                row['voice_s_' + name] = round((state['voice'][name] - prev_state['voice'][name]) / float(rate), 2)
            row['new_errors'] = len(state['errors']) - prev_state['errors']
            row['new_drops'] = len(state['drops']) - prev_state['drops']
            prev_state = {'voice': dict(state['voice']), 'steps': state['steps'], 'ws_msgs': state['ws_msgs'],
                          'tap_msgs': state['tap_msgs'], 'errors': len(state['errors']), 'drops': len(state['drops'])}
        row['rec_mb'] = round(rec_mb(), 1)
        w.writerow([row.get(c, '') for c in cols])
        f.flush()
        time.sleep(max(0.0, INTERVAL - (time.time() - t_a)))
    with lock:
        summary = {'duration_s': round(time.time() - t0), 'errors': state['errors'][:20], 'drops': state['drops'][:20]}
    json.dump(summary, open(OUT + '.summary.json', 'w'), indent=1)
    print('soak monitor finished', summary['duration_s'], 's')


if __name__ == '__main__':
    main()
