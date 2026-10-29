"""Reconnecting TCP IQ source for GNU Radio (complex64 stream).

Drop-in for gnuradio's `network.tcp_source` (client side): connects to host:port and streams complex64
samples. Unlike the stock block it does NOT stop for good when the connection drops. A front end that
restarts, crashes or loses its link is retried until it is back, and the decoder keeps running and
resumes as soon as IQ arrives again (the stock block left the decoder alive but deaf: 0 output for
more than 120 s after the source was restarted).

  * only whole complex64 samples (8 bytes) are ever delivered, also across partial reads and reconnects
  * a new connection always starts on a sample boundary (the server's first byte is sample 0)
  * while disconnected the block produces nothing (no invented zeros, no fake samples)
  * `reconnects` counts how many times the link was re-established
"""
import socket
import time

import numpy as np
from gnuradio import gr

ITEM = 8   # bytes per complex64 sample


class iq_tcp_source(gr.sync_block):
    def __init__(self, addr='127.0.0.1', port=7000, retry_s=0.5):
        gr.sync_block.__init__(self, name='iq_tcp_source', in_sig=None, out_sig=[np.complex64])
        self.addr = str(addr)
        self.port = int(port)
        self.retry_s = float(retry_s)
        self.sock = None
        self.left = b''          # bytes of a sample not yet complete
        self.reconnects = 0
        self.connected_once = False

    def _connect(self):
        try:
            s = socket.create_connection((self.addr, self.port), timeout=1.0)
        except OSError:
            return False
        s.settimeout(0.5)        # never block forever: the scheduler must be able to stop the flowgraph
        self.sock = s
        self.left = b''
        if self.connected_once:
            self.reconnects += 1
        self.connected_once = True
        return True

    def _drop(self):
        try:
            self.sock.close()
        except OSError:
            pass
        self.sock = None
        self.left = b''

    def work(self, input_items, output_items):
        out = output_items[0]
        if self.sock is None and not self._connect():
            time.sleep(self.retry_s)
            return 0
        want = len(out) * ITEM - len(self.left)
        try:
            data = self.sock.recv(want)
        except socket.timeout:
            return 0
        except OSError:
            self._drop()
            return 0
        if not data:             # the source closed the connection
            self._drop()
            return 0
        buf = self.left + data
        n = len(buf) // ITEM
        self.left = buf[n * ITEM:]
        if n:
            out[:n] = np.frombuffer(buf[:n * ITEM], dtype=np.complex64)
        return n

    def stop(self):
        if self.sock is not None:
            self._drop()
        return True
