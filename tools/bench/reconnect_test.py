#!/usr/bin/env python3
"""Source-restart test: what happens to the decoder + bridge when the IQ source goes away and comes back?

A real front end (the final bigger USRP, or any process feeding the TCP ports) can crash, be restarted or
lose its link. This kills the replay source while the stack is running, leaves it down for DOWN s,
starts it again, and measures: did the decoder and bridge survive, and how long until real decoded
output is flowing again?

  python3 tools/bench/reconnect_test.py terrestrial 20
  python3 tools/bench/reconnect_test.py air 20

Needs the stack already running: tools/bench/run_ui_dev.sh (terrestrial) or the air stack from
soak_monitor_air.py's docstring (replay_iq_tcp.py + airmaritime_bridge.py + start_flowgraph).
"""
import glob
import os
import signal
import subprocess
import sys
import threading
import time

import numpy as np
import zmq

MODE, DOWN = sys.argv[1], float(sys.argv[2])
HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
G = '/home/shankar/am_gt'
if MODE == 'terrestrial':
    SRC_PAT = 'replay_bands.py'
    SRC_CMD = ['python3', '-u', 'tools/bench/replay_bands.py', '/tmp/securecom_uidev/replay_stats.txt']
    SRC_CWD = HERE
    TAPS = {9101: 'dmr', 9102: 'nxdn', 9103: 'p25', 9105: None, 9106: 'nxdn48', 9107: 'dstar'}
    TAPS = {p: n for p, n in TAPS.items() if n}
    PROCS = {'bridge': 'bridge_server.py', 'decoder': 'allinone.py'}
else:
    SRC_PAT = 'replay_iq_tcp.py'
    SRC_CMD = ['python3', '-u', 'tools/replay_iq_tcp.py', '--ais', f'{G}/cap7009.cf32', '--ais-rate', '250000',
               '--adsb', f'{G}/adsb_real_6M_10s.cf32', '--adsb-rate', '6000000']
    SRC_CWD = os.path.join(HERE, 'airmaritime')
    TAPS = {9201: 'ais', 9202: 'adsb'}
    PROCS = {'bridge': 'airmaritime_bridge.py', 'decoder': 'airmaritime_decoder_live.py'}

count = {n: 0 for n in TAPS.values()}
lock = threading.Lock()


def tap(port, name):
    s = zmq.Context().socket(zmq.SUB)
    s.connect(f'tcp://127.0.0.1:{port}')
    s.setsockopt(zmq.SUBSCRIBE, b'')
    s.setsockopt(zmq.RCVTIMEO, 300)
    while True:
        try:
            raw = s.recv()
        except zmq.Again:
            continue
        with lock:
            if MODE == 'terrestrial':
                count[name] += int(np.count_nonzero(np.abs(np.frombuffer(raw, dtype=np.float32)) > 1e-4))   # voice samples
            else:
                count[name] += 1                                                                        # decoded messages


def pids(pat):
    out = []
    for p in glob.glob('/proc/[0-9]*'):
        try:
            cmd = open(p + '/cmdline', 'rb').read().replace(b'\0', b' ').decode(errors='replace')
        except OSError:
            continue
        if pat in cmd and 'reconnect_test' not in cmd:
            out.append(int(p.split('/')[-1]))
    return out


def rate(seconds):
    with lock:
        a = dict(count)
    time.sleep(seconds)
    with lock:
        b = dict(count)
    return {n: (b[n] - a[n]) for n in a}


def main():
    for port, name in TAPS.items():
        threading.Thread(target=tap, args=(port, name), daemon=True).start()
    time.sleep(2)
    unit = 'voice samples' if MODE == 'terrestrial' else 'messages'
    base = rate(30)
    print(f'[{MODE}] baseline over 30 s ({unit}):', base, flush=True)
    before = {k: len(pids(p)) for k, p in PROCS.items()}
    for p in pids(SRC_PAT):
        os.kill(p, signal.SIGKILL)
    t_kill = time.time()
    print(f'source killed; staying down {DOWN:.0f} s', flush=True)
    time.sleep(DOWN)
    during = {k: len(pids(p)) for k, p in PROCS.items()}
    subprocess.Popen(SRC_CMD, cwd=SRC_CWD, stdout=open(f'{G}/reconnect_src.log', 'w'), stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    t_up = time.time()
    print('source restarted', flush=True)
    first = {}
    with lock:
        start = dict(count)
    while time.time() - t_up < 120 and len(first) < len(count):
        time.sleep(0.5)
        with lock:
            for n in count:
                if n not in first and count[n] - start[n] > 0:
                    first[n] = round(time.time() - t_up, 1)
    after = rate(30)
    final = {k: len(pids(p)) for k, p in PROCS.items()}
    print(f'processes before / during outage / after (count): {before} / {during} / {final}')
    print('seconds until each output came back after the source restarted:', first or 'NEVER within 120 s')
    print(f'rate over the 30 s after recovery ({unit}):', after)
    ok = all(after[n] > 0.5 * base[n] for n in base if base[n] > 0)
    print('RESULT:', 'recovered' if ok and during == before == final else 'NOT RECOVERED / process lost')


if __name__ == '__main__':
    main()
