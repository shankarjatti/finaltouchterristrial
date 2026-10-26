#!/usr/bin/env python3
"""
GNU Radio in-flowgraph TETRA decoder block -- Decodio/Procitec-style:
multiple simultaneously-decoded timeslots, each with its own audio output,
plus a live call-log message stream (call setup/teardown, registration,
status) separate from the audio path.

Wraps tetra-kit's TetraDecoder (via libtetrakit_capi.so, built from this
directory's Makefile) and the existing ACELP vocoder (libtetra_codec.so) as
one gr.basic_block: raw channel bits in, decoded PCM audio out -- no
external process, no UDP hop on the input side.

The JSON/UDP path tetra-kit's Report class already uses internally
(Report::send() always sendto()s to 127.0.0.1:42100, hardcoded in
tetra-kit's own report.cc, not something this file changes) is kept exactly
as-is and simply received by a background thread in this same process,
instead of a separate Python script. Do not run the old external `decoder`
binary at the same time -- it would bind the same port.

Every layer (UPlane, CMCE, MM, MLE, SNDCP, SDS) already reports over this
same channel -- tetra-kit was not modified to add this, it was already
there. This file just stops discarding everything except TCH_S.
"""

import ctypes
import base64
import json
import os
import queue
import socket
import struct
import sys
import threading
import zlib

import numpy as np
import pmt
from gnuradio import gr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'decoder_framework'))
from decoder_event import DecoderEvent

HERE = os.path.dirname(os.path.abspath(__file__))
CAPI_SO = os.path.join(HERE, 'libtetrakit_capi.so')
CODEC_SO = os.path.join(HERE, '..', 'tetra-kit', 'recorder', 'audio', 'libtetra_codec.so')

REPORT_PORT = 42100  # fixed by tetra-kit's Report::send(), not configurable here
N_SLOTS = 4           # TETRA TDMA: exactly 4 timeslots per carrier, TN is 1-4


class tetra_decoder_block(gr.basic_block):
    """
    Input:  unpacked channel bits, one bit per item (uint8, 0 or 1) -- same
            format pi4dqpsk_rx.py's blocks_unpack_k_bits_bb already produces.
    Outputs: 4 streams of decoded speech PCM (float32, normalized [-1, 1],
             8 kHz) -- one per TETRA timeslot (TN 1-4), so up to 4
             simultaneous calls on one carrier stay separate instead of
             mixing into one stream.
    Message port "call_log": a PMT dict per non-voice report (CMCE call
             setup/teardown, MM registration, MLE broadcast, SDS
             status/text) -- service, pdu, tn/fn/mn, ssi, plus any other
             fields tetra-kit's Report attached.
    """

    def __init__(self, log_level=1, remove_fill_bits=True, wireshark_output=False, debug=False):
        gr.basic_block.__init__(
            self,
            name='tetra_decoder_block',
            in_sig=[np.uint8],
            out_sig=[np.float32] * N_SLOTS,
        )
        self.message_port_register_out(pmt.intern('call_log'))

        # GRC checkbox OR env var -- either turns on the audio-path packet trace
        self._debug = bool(debug) or os.environ.get('TETRA_BLOCK_DEBUG') == '1'

        self._audio_q = [queue.Queue() for _ in range(N_SLOTS)]
        self._carry = [None] * N_SLOTS
        self._stop = threading.Event()

        self._load_capi()
        self._load_codec()
        self._open_report_socket()

        # any valid UDP socket fd works here -- Report::send() specifies the
        # destination (127.0.0.1:42100) on every sendto() call itself.
        # Must be kept as an attribute: an unreferenced socket.socket(...) is
        # garbage-collected almost immediately, which closes its fd -- the
        # C++ side would then be sendto()-ing on a dead descriptor forever,
        # silently dropping every report with no error on either side.
        self._writer_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._handle = self._capi.tetrakit_create(
            self._writer_sock.fileno(), int(remove_fill_bits), int(log_level), int(wireshark_output)
        )

        self._rx_thread = threading.Thread(target=self._report_rx_loop, daemon=True)
        self._rx_thread.start()

    # ------------------------------------------------------------------ setup

    def _load_capi(self):
        self._capi = ctypes.CDLL(CAPI_SO)
        self._capi.tetrakit_create.restype = ctypes.c_void_p
        self._capi.tetrakit_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self._capi.tetrakit_rx_symbol.restype = None
        self._capi.tetrakit_rx_symbol.argtypes = [ctypes.c_void_p, ctypes.c_ubyte]
        self._capi.tetrakit_destroy.restype = None
        self._capi.tetrakit_destroy.argtypes = [ctypes.c_void_p]

    def _load_codec(self):
        self._codec = ctypes.CDLL(CODEC_SO)
        self._codec.tetra_codec_create.restype = ctypes.c_void_p
        self._codec.tetra_codec_create.argtypes = []
        self._codec.tetra_codec_destroy.restype = None
        self._codec.tetra_codec_destroy.argtypes = [ctypes.c_void_p]
        self._codec.tetra_codec_process_frame.restype = ctypes.c_int
        self._codec.tetra_codec_process_frame.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int16),
            ctypes.POINTER(ctypes.c_int16),
        ]
        self._codec_handle = self._codec.tetra_codec_create()

    def _open_report_socket(self):
        self._report_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._report_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._report_sock.bind(('127.0.0.1', REPORT_PORT))
        self._report_sock.settimeout(0.5)

    # ------------------------------------------------------------- rx thread

    def _report_rx_loop(self):
        _dbg = self._debug
        _n_pkts = _n_tchs = _n_frame = _n_codec_ok = _n_calllog = 0
        while not self._stop.is_set():
            try:
                data, _ = self._report_sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            _n_pkts += 1

            try:
                msg = json.loads(data.decode('utf-8', errors='ignore'))
            except json.JSONDecodeError:
                if _dbg:
                    print(f'[tetra_decoder_block] non-JSON packet #{_n_pkts}: {data[:80]!r}', flush=True)
                continue

            service = msg.get('service')
            pdu = msg.get('pdu')

            if service == 'UPLANE' and pdu == 'TCH_S':
                self._handle_tch_s(msg, _n_tchs, _dbg)
                _n_tchs += 1
                continue

            # everything else (CMCE/MM/MLE/SNDCP/SDS) -> call_log message port
            _n_calllog += 1
            if _dbg and _n_calllog % 5 == 1:
                print(f'[tetra_decoder_block] call_log #{_n_calllog}: service={service!r} pdu={pdu!r}', flush=True)
            self._publish_call_log(msg)

        if _dbg:
            print(f'[tetra_decoder_block] TOTALS: pkts={_n_pkts} tch_s={_n_tchs} call_log={_n_calllog}', flush=True)

    def _handle_tch_s(self, msg, idx, _dbg):
        tn = msg.get('tn')
        if not isinstance(tn, int) or not (1 <= tn <= N_SLOTS):
            if _dbg:
                print(f'[tetra_decoder_block] TCH_S #{idx} has bad/missing tn: {tn!r}', flush=True)
            return

        b64 = msg.get('frame', '')
        if not b64:
            if _dbg:
                print(f'[tetra_decoder_block] TCH_S #{idx} (tn={tn}) has no "frame" field: keys={list(msg.keys())}', flush=True)
            return

        try:
            frame_bytes = zlib.decompress(base64.b64decode(b64))
        except (zlib.error, ValueError) as e:
            if _dbg:
                print(f'[tetra_decoder_block] decompress failed on TCH_S #{idx} (tn={tn}): {e}', flush=True)
            return

        if len(frame_bytes) < 1380:
            if _dbg:
                print(f'[tetra_decoder_block] TCH_S #{idx} (tn={tn}) frame too short: {len(frame_bytes)} bytes', flush=True)
            return

        sf = (ctypes.c_int16 * 690)(*struct.unpack('<690h', frame_bytes[:1380]))
        out = (ctypes.c_int16 * 480)()
        ok = self._codec.tetra_codec_process_frame(self._codec_handle, sf, out)
        if ok == 1:
            pcm = np.frombuffer(bytes(out), dtype=np.int16).astype(np.float32) / 32768.0
            self._audio_q[tn - 1].put(pcm)
        elif _dbg:
            print(f'[tetra_decoder_block] codec_process_frame returned {ok} (not 1) on TCH_S #{idx} (tn={tn})', flush=True)

    def _publish_call_log(self, msg):
        ev = DecoderEvent.from_tetra_json(msg)
        if ev is None:
            return
        self.message_port_pub(pmt.intern('call_log'), ev.to_pmt())
        ev.publish()  # also push to the Decodio-style dashboard, if it's running

    # --------------------------------------------------------------- GR work

    def general_work(self, input_items, output_items):
        in0 = input_items[0]

        for i in range(len(in0)):
            self._capi.tetrakit_rx_symbol(self._handle, int(in0[i]) & 0x01)
        self.consume(0, len(in0))

        max_produced = 0
        for slot in range(N_SLOTS):
            out = output_items[slot]
            produced = 0
            while produced < len(out):
                if self._carry[slot] is None:
                    try:
                        self._carry[slot] = self._audio_q[slot].get_nowait()
                    except queue.Empty:
                        break
                carry = self._carry[slot]
                take = min(len(carry), len(out) - produced)
                out[produced:produced + take] = carry[:take]
                produced += take
                self._carry[slot] = None if take == len(carry) else carry[take:]
            # gr.basic_block.general_work() reports one produced-count for
            # all outputs; zero-fill each slot's buffer past its own real
            # audio so every output stays in sync at the buffer level (each
            # still only carries real audio during that slot's own call).
            if produced < len(out):
                out[produced:] = 0.0
            max_produced = max(max_produced, produced)

        return max_produced

    def stop(self):
        self._stop.set()
        try:
            self._report_sock.close()
        except OSError:
            pass
        try:
            self._writer_sock.close()
        except OSError:
            pass
        self._codec.tetra_codec_destroy(self._codec_handle)
        self._capi.tetrakit_destroy(self._handle)
        return True
