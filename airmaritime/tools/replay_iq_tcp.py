#!/usr/bin/env python3
"""Stand-in for the air/maritime Module 1: serve recorded AIS / ADS-B IQ over the
same TCP ports the live decoder reads (AIS 7009, ADS-B 7010), so the whole
software chain (airmaritime_decoder_live.py -> ZMQ 9201/9202 -> airmaritime_bridge
-> map) can be proven with real sample data and no USRP/HackRF at all.

Each port is a TCP server (server side, like Module 1). On a client connect it
streams the file's complex64 IQ at the file's real-time rate, looping, so the
decoder sees exactly the rate Module 1 configures for that band (AIS 250 kSps,
ADS-B 6 MSps). Stereo-IQ .wav (I=left, Q=right) or raw .cf32 both work.

  # stop Module 1 first so 7009/7010 are free, then:
  python3 tools/replay_iq_tcp.py \
      --ais  "/path/ais_marine_vessel_tracking_250k.wav"      --ais-rate 250000 \
      --adsb "/path/adsb_real_6M.cf32"   --adsb-rate 6000000   # real recording resampled to 6 MSps
"""
import argparse
import socket
import threading
import time
import wave

import numpy as np

CHUNK_MS = 10


def load_iq(path):
    if path.lower().endswith('.wav'):
        with wave.open(path) as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2) / 32768.0
        return (a[:, 0] + 1j * a[:, 1]).astype(np.complex64)
    return np.fromfile(path, dtype=np.complex64)


def serve(port, iq, rate, label):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', port))
    srv.listen(4)
    chunk = max(1, int(rate * CHUNK_MS / 1000))
    print(f'{label}: serving {len(iq) / rate:.1f} s of IQ on 127.0.0.1:{port} at {rate} Sps', flush=True)
    while True:
        c, _ = srv.accept()
        print(f'{label}: client connected on {port}', flush=True)
        pos = 0
        start = time.time()
        sent = 0
        try:
            while True:
                block = np.take(iq, range(pos, pos + chunk), mode='wrap')
                pos = (pos + chunk) % len(iq)
                c.sendall(block.tobytes())
                sent += chunk
                ahead = start + sent / rate - time.time()
                if ahead > 0:
                    time.sleep(ahead)
        except OSError:
            print(f'{label}: client on {port} disconnected', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ais')
    ap.add_argument('--ais-port', type=int, default=7009)
    ap.add_argument('--ais-rate', type=float, default=250000)
    ap.add_argument('--adsb')
    ap.add_argument('--adsb-port', type=int, default=7010)
    ap.add_argument('--adsb-rate', type=float, default=6000000)
    a = ap.parse_args()
    threads = []
    if a.ais:
        iq = load_iq(a.ais)
        threads.append(threading.Thread(target=serve, args=(a.ais_port, iq, int(a.ais_rate), 'AIS'), daemon=True))
    if a.adsb:
        iq = load_iq(a.adsb)
        threads.append(threading.Thread(target=serve, args=(a.adsb_port, iq, int(a.adsb_rate), 'ADSB'), daemon=True))
    if not threads:
        raise SystemExit('give --ais and/or --adsb')
    for t in threads:
        t.start()
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
