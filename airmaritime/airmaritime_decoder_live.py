#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Air & Maritime Dual-Protocol Decoder -- LIVE (AIS, ADS-B)
# Description: Same decode chain as airmaritime_decoder.py, but reading from
# Module 1's TCP ports (AIS 7009, ADS-B 7010) instead of the two bundled WAV
# files. airmaritime_decoder.py stays as-is -- it is the proven, working
# regression reference, the same role allinone.py/offline_decode_test.py play
# for the terrestrial protocols. This file is what runs once the USRP is
# actually dwelling on AIS/ADS-B; point tools/replay_iq_tcp.py at these same
# two ports first to validate the chain against real recorded content with no
# USRP attached at all -- see README's base-station field procedure.
#
# ADS-B needs real instantaneous bandwidth (~2 MHz for 1090ES Mode-S) that
# Module 1's shared 200 kSps rate cannot provide -- its dwell slot requests a
# genuinely wider hardware rate instead (BandConfig::samp_rate_hz in
# module1/src/main.cpp). ADSB_SOURCE_RATE_HZ below is what that TCP port
# ACTUALLY delivers; update it from Module 1's own startup log line
# ("[USRP] RX rate actual : ...") once run against a real B210 -- B210 rates
# are quantised by its master clock and may not land exactly on the request.
# The resampler bridges that real rate to `fs`, the rate every adsb.* block
# below is built around, so a request-vs-achieved mismatch never needs a
# second file edited to match.
#
# GNU Radio version: 3.10.1.1

from packaging.version import Version as StrictVersion

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print("Warning: failed to XInitThreads()")

from PyQt5 import Qt
from gnuradio import eng_notation
from gnuradio import qtgui
from gnuradio.filter import firdes
import sip
from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio import network
from gnuradio.fft import window
from math import gcd
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import zeromq
import gnuradio.adsb as adsb
from modes_demod import modes_demod
from iq_tcp_source import iq_tcp_source   # reconnects when the IQ source restarts (stock tcp_source never does)
import gnuradio.ais as ais
# AIS symbol timing: 250 kSps / decimation 5 = 50 kSps at 9600 baud = 5.208 samples/symbol.
# (The copied flowgraph said 5; the clock recovery may only drift 0.5 %, so a 4 % error
# produced 10 kbit/s of garbage and no AIS frame ever passed the HDLC CRC.)
AIS_SPS = 250000 / 5 / 9600


from gnuradio import qtgui

# Module 1's live ports for these two bands (module1/src/main.cpp BANDS table)
AIS_TCP_PORT  = 7009
AIS_AFC_OFFSETS_HZ = (-900, -450, 450, 900)   # extra carrier-offset hypotheses per AIS channel
ADSB_TCP_PORT = 7010

# What Module 1's ADS-B dwell slot ACTUALLY delivers -- see file header.
ADSB_SOURCE_RATE_HZ = 6_000_000.0   # Module 1's ADS-B rate (main.cpp); 2 MSps decoded 0 frames of a real recording

class airmaritime_decoder_live(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Air & Maritime Dual-Protocol Decoder -- LIVE (AIS, ADS-B)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Air & Maritime Dual-Protocol Decoder -- LIVE (AIS, ADS-B)")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "airmaritime_decoder_live")

        try:
            if StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
                self.restoreGeometry(self.settings.value("geometry").toByteArray())
            else:
                self.restoreGeometry(self.settings.value("geometry"))
        except:
            pass

        ##################################################
        # Variables
        ##################################################
        # AIS: 250 kSps, same as the WAV-based reference -- NOT the shared
        # 200 kSps default. The 25 kHz channel itself would fit either rate,
        # the GMSK demod below runs at 250 kSps / 5 = 50 kSps, i.e. AIS_SPS =
        # 5.208 samp/sym at 9600 baud (must be the exact value, see AIS_SPS).
        # Module 1's AIS band requests this same
        # 250 kSps explicitly (BandConfig::samp_rate_hz, main.cpp) rather
        # than the shared default, so the two stay in lock-step.
        self.samp_rate_0 = samp_rate_0 = 250000
        self.samp_rate = samp_rate = 1152000
        self.low_pass_taps = low_pass_taps = firdes.low_pass(1.0, samp_rate_0, 11000,1000, window.WIN_HAMMING, 6.76)
        self.fs = fs = 6e6                              # rate modes_demod runs at (even samples per microsecond)
        self.adsb_source_rate = adsb_source_rate = ADSB_SOURCE_RATE_HZ  # rate actually arriving over TCP

        ##################################################
        # Blocks
        ##################################################
        self.zeromq_pub_msg_sink_0_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:9201', 10, True)
        self.zeromq_pub_msg_sink_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:9202', 10, True)
        # every CRC-valid Mode-S frame (meta . 112 bits): the bridge decodes positions from these (adsb_cpr.py)
        self.zeromq_pub_raw_adsb = zeromq.pub_msg_sink('tcp://127.0.0.1:9203', 10, True)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(
            int(fs*150e-6), #size
            int(fs), #samp_rate
            "ADS-B Pulse Telemetry", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(1.0/100.0)
        self.qtgui_time_sink_x_0.set_y_axis(0, 0.01)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        # one sweep per CRC-valid frame: modes_demod tags each decoded frame's preamble "burst"
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_TAG, qtgui.TRIG_SLOPE_POS, 0.0, 2e-6, 0, "burst")
        self.qtgui_time_sink_x_0.enable_autoscale(True)   # B210 level depends on the RF chain
        self.qtgui_time_sink_x_0.enable_grid(True)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)

        self.qtgui_time_sink_x_0.disable_legend()

        labels = ['|IQ| of decoded frame', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [0, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_time_sink_x_0_win, 1, 0, 1, 2)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.freq_xlating_fir_filter_xxx_1 = filter.freq_xlating_fir_filter_ccc(5, low_pass_taps, 25000, samp_rate_0)
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(5, low_pass_taps, -25000, samp_rate_0)
        self.digital_hdlc_deframer_bp_1 = digital.hdlc_deframer_bp(11, 64)
        self.digital_hdlc_deframer_bp_0 = digital.hdlc_deframer_bp(11, 64)
        self.digital_gmsk_demod_1 = digital.gmsk_demod(
            samples_per_symbol=AIS_SPS,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,log=False)
        self.digital_gmsk_demod_0 = digital.gmsk_demod(
            samples_per_symbol=AIS_SPS,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,log=False)

        # ── LIVE sources: Module 1's TCP ports, replacing the two
        #    blocks.wavfile_source + float_to_complex pairs from
        #    airmaritime_decoder.py. Both already deliver complex64 directly
        #    (Module 1's wire format, same as every other terrestrial port),
        #    so no float_to_complex recombination step is needed here.
        self.tcp_source_ais = iq_tcp_source('127.0.0.1', AIS_TCP_PORT)
        self.tcp_source_adsb = iq_tcp_source('127.0.0.1', ADSB_TCP_PORT)

        # Resample whatever Module 1's ADS-B dwell slot actually delivers
        # (adsb_source_rate) to exactly `fs`, the rate every adsb.* block
        # below is built around. Degenerates to a 1:1 passthrough if the two
        # already match (interp == decim), so it is always safe to leave in
        # place even before a real achieved-rate figure is available.
        g = gcd(int(adsb_source_rate), int(fs))
        self.resampler_adsb = filter.rational_resampler_ccc(
            interpolation=int(fs) // g,
            decimation=int(adsb_source_rate) // g,
            taps=[],
            fractional_bw=0.4)

        # No Throttle on live sources: Module 1 already paces the IQ in real time. A throttle
        # (copied from the file-based flowgraph) stopped the decoder catching up after any stall,
        # so Module 1 kept dropping its data. Plain pass-throughs keep the existing block names.
        self.blocks_throttle_0_1 = blocks.copy(gr.sizeof_gr_complex*1)
        self.blocks_throttle_0_0 = blocks.copy(gr.sizeof_gr_complex*1)
        self.ais_pdu_to_nmea_1 = ais.pdu_to_nmea("B")
        self.ais_pdu_to_nmea_0 = ais.pdu_to_nmea("A")
        self.ais_invert_1 = ais.invert()
        self.ais_invert_0 = ais.invert()
        # gr-adsb's framer + demod replaced by modes_demod (preamble test against the measured
        # noise floor, half-bit integration, timing search, CRC-24): see modes_demod.py
        self.adsb_modes_demod = modes_demod(fs)
        self.adsb_decoder_0 = adsb.decoder("Extended Squitter Only", "None", "Brief")


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.adsb_decoder_0, 'decoded'), (self.zeromq_pub_msg_sink_0, 'in'))
        self.msg_connect((self.adsb_modes_demod, 'demodulated'), (self.adsb_decoder_0, 'demodulated'))
        self.msg_connect((self.adsb_modes_demod, 'demodulated'), (self.zeromq_pub_raw_adsb, 'in'))
        self.msg_connect((self.ais_pdu_to_nmea_0, 'out'), (self.zeromq_pub_msg_sink_0_0, 'in'))
        self.msg_connect((self.ais_pdu_to_nmea_1, 'out'), (self.zeromq_pub_msg_sink_0_0, 'in'))
        self.msg_connect((self.digital_hdlc_deframer_bp_0, 'out'), (self.ais_pdu_to_nmea_0, 'print'))
        self.msg_connect((self.digital_hdlc_deframer_bp_1, 'out'), (self.ais_pdu_to_nmea_1, 'print'))
        self.connect((self.adsb_modes_demod, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.ais_invert_0, 0), (self.digital_hdlc_deframer_bp_0, 0))
        self.connect((self.ais_invert_1, 0), (self.digital_hdlc_deframer_bp_1, 0))
        self.connect((self.blocks_throttle_0_1, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.blocks_throttle_0_1, 0), (self.freq_xlating_fir_filter_xxx_1, 0))
        self.connect((self.tcp_source_ais, 0), (self.blocks_throttle_0_1, 0))
        self.connect((self.tcp_source_adsb, 0), (self.resampler_adsb, 0))
        self.connect((self.resampler_adsb, 0), (self.blocks_throttle_0_0, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.adsb_modes_demod, 0))
        self.ais_nrzi_0 = digital.diff_decoder_bb(2)   # AIS is NRZI: transition -> 0 after ais.invert
        self.connect((self.digital_gmsk_demod_0, 0), (self.ais_nrzi_0, 0))
        self.connect((self.ais_nrzi_0, 0), (self.ais_invert_0, 0))
        self.ais_nrzi_1 = digital.diff_decoder_bb(2)   # AIS is NRZI: transition -> 0 after ais.invert
        self.connect((self.digital_gmsk_demod_1, 0), (self.ais_nrzi_1, 0))
        self.connect((self.ais_nrzi_1, 0), (self.ais_invert_1, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.digital_gmsk_demod_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_1, 0), (self.digital_gmsk_demod_1, 0))

        # Carrier-offset hypotheses. A transmitter/receiver oscillator mismatch (AIS allows
        # +-500 Hz; a HackRF -> B210 bench pair showed ~550 Hz) appears as a DC bias after the FM
        # demod and the fixed-centre branch above then drops most frames. Run the same demod chain
        # at a few small offsets around each channel; the HDLC CRC rejects bad frames, so the extra
        # branches only add valid ones (the bridge de-duplicates by MMSI).
        self._ais_afc = []
        for center, pdu in ((-25000, self.ais_pdu_to_nmea_0), (25000, self.ais_pdu_to_nmea_1)):
            for off in AIS_AFC_OFFSETS_HZ:
                xl = filter.freq_xlating_fir_filter_ccc(5, low_pass_taps, center + off, samp_rate_0)
                dm = digital.gmsk_demod(samples_per_symbol=AIS_SPS, gain_mu=0.175, mu=0.5,
                                        omega_relative_limit=0.005, freq_error=0.0, verbose=False, log=False)
                nrzi = digital.diff_decoder_bb(2)
                inv = ais.invert()
                hd = digital.hdlc_deframer_bp(11, 64)
                self.connect((self.blocks_throttle_0_1, 0), (xl, 0))
                self.connect((xl, 0), (dm, 0))
                self.connect((dm, 0), (nrzi, 0))
                self.connect((nrzi, 0), (inv, 0))
                self.connect((inv, 0), (hd, 0))
                self.msg_connect((hd, 'out'), (pdu, 'print'))
                self._ais_afc.append((xl, dm, nrzi, inv, hd))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "airmaritime_decoder_live")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate_0(self):
        return self.samp_rate_0

    def set_samp_rate_0(self, samp_rate_0):
        self.samp_rate_0 = samp_rate_0
        self.set_low_pass_taps(firdes.low_pass(1.0, self.samp_rate_0, 11000, 1000, window.WIN_HAMMING, 6.76))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_low_pass_taps(self):
        return self.low_pass_taps

    def set_low_pass_taps(self, low_pass_taps):
        self.low_pass_taps = low_pass_taps
        self.freq_xlating_fir_filter_xxx_0.set_taps(self.low_pass_taps)
        self.freq_xlating_fir_filter_xxx_1.set_taps(self.low_pass_taps)

    def get_fs(self):
        return self.fs

    def set_fs(self, fs):
        self.fs = fs
        self.qtgui_time_sink_x_0.set_samp_rate(int(self.fs))

    def get_adsb_source_rate(self):
        return self.adsb_source_rate

    def set_adsb_source_rate(self, adsb_source_rate):
        # Changing this at runtime would need the resampler's interp/decim
        # recomputed and re-set -- not wired up, since in practice this only
        # ever needs updating once, from Module 1's own rate-actual log line,
        # then the module-level ADSB_SOURCE_RATE_HZ constant edited to match.
        self.adsb_source_rate = adsb_source_rate




def main(top_block_cls=airmaritime_decoder_live, options=None):

    if StrictVersion("4.5.0") <= StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
