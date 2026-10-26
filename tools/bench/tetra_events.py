#!/usr/bin/env python3
"""Listen to the decoder's TETRA call-log events (ZMQ 9105, PMT messages) for N seconds.

  python3 tools/bench/tetra_events.py 60
"""
import collections
import sys
import time

import pmt
import zmq


def main():
    secs = float(sys.argv[1])
    s = zmq.Context().socket(zmq.SUB)
    s.connect('tcp://127.0.0.1:9105')
    s.setsockopt(zmq.SUBSCRIBE, b'')
    s.setsockopt(zmq.RCVTIMEO, 300)
    kinds = collections.Counter()
    samples = []
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            msg = pmt.deserialize_str(s.recv())
        except zmq.Again:
            continue
        except Exception:
            kinds['undecodable'] += 1
            continue
        py = pmt.to_python(msg)
        kind = py.get('event', py.get('type', '?')) if isinstance(py, dict) else type(py).__name__
        kinds[str(kind)] += 1
        if len(samples) < 5:
            samples.append(str(py)[:160])
    print(f'tetra events in {secs:.0f} s: {sum(kinds.values())} {dict(kinds)}')
    for x in samples:
        print('  e.g.', x)


if __name__ == '__main__':
    main()
