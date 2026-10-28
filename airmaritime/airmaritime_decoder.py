#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Air & Maritime Dual-Protocol Decoder (AIS, ADS-B)
# Description: Air & Maritime Dual-Protocol Receiver (AIS on 9201, ADS-B on 9202)
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
from gnuradio import qtgui
from gnuradio.filter import firdes
import sip
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import zeromq
import airmaritime_decoder_modes_demod_0 as modes_demod_0  # embedded python block
import gnuradio.adsb as adsb
import gnuradio.ais as ais



from gnuradio import qtgui

class airmaritime_decoder(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Air & Maritime Dual-Protocol Decoder (AIS, ADS-B)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Air & Maritime Dual-Protocol Decoder (AIS, ADS-B)")
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

        self.settings = Qt.QSettings("GNU Radio", "airmaritime_decoder")

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
        self.samp_rate_0 = samp_rate_0 = 250000
        self.samp_rate = samp_rate = 1152000
        self.low_pass_taps = low_pass_taps = firdes.low_pass(1.0, samp_rate_0, 11000,1000, window.WIN_HAMMING, 6.76)
        self.fs = fs = 6e6

        ##################################################
        # Blocks
        ##################################################
        self.zeromq_pub_msg_sink_0_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:9201', 10, True)
        self.zeromq_pub_msg_sink_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:9202', 10, True)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(
            int(fs*150e-6), #size
            int(fs), #samp_rate
            "ADS-B Pulse Telemetry", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(1.0/100.0)
        self.qtgui_time_sink_x_0.set_y_axis(0, 1)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0, 1.25e-6, 0, "")
        self.qtgui_time_sink_x_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0.enable_grid(True)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)

        self.qtgui_time_sink_x_0.disable_legend()

        labels = ['Received |IQ|^2', 'Threshold', '', '', '',
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
        self.modes_demod_0 = modes_demod_0.modes_demod(fs=fs, snr_db=6.0)
        self.freq_xlating_fir_filter_xxx_1 = filter.freq_xlating_fir_filter_ccc(5, low_pass_taps, 25000, samp_rate_0)
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(5, low_pass_taps, -25000, samp_rate_0)
        self.digital_hdlc_deframer_bp_1 = digital.hdlc_deframer_bp(11, 64)
        self.digital_hdlc_deframer_bp_0 = digital.hdlc_deframer_bp(11, 64)
        self.digital_gmsk_demod_1 = digital.gmsk_demod(
            samples_per_symbol=5,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,log=False)
        self.digital_gmsk_demod_0 = digital.gmsk_demod(
            samples_per_symbol=5,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,log=False)
        self.blocks_wavfile_source_0_0 = blocks.wavfile_source('/home/shankar/Downloads/tutorials/delhi_testing/all_protocols_wav_samples/AIS_Marine/ais_b210_cable_capture_250k.wav', True)
        self.blocks_wavfile_source_0 = blocks.wavfile_source('/home/shankar/Downloads/tutorials/sigtel_protocol_wav_folders/1_ADS-B/1_ADS-B_LiveRecorded_2.4MSps.wav', True)
        self.blocks_throttle_0_1 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate_0,True)
        self.blocks_throttle_0_0 = blocks.throttle(gr.sizeof_gr_complex*1, fs,True)
        self.blocks_float_to_complex_0_0 = blocks.float_to_complex(1)
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(1)
        self.ais_to_48k_1 = filter.rational_resampler_ccc(
                interpolation=24,
                decimation=25,
                taps=[],
                fractional_bw=0)
        self.ais_to_48k_0 = filter.rational_resampler_ccc(
                interpolation=24,
                decimation=25,
                taps=[],
                fractional_bw=0)
        self.ais_pdu_to_nmea_1 = ais.pdu_to_nmea("B")
        self.ais_pdu_to_nmea_0 = ais.pdu_to_nmea("A")
        self.ais_nrzi_1 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.ais_nrzi_0 = digital.diff_decoder_bb(2, digital.DIFF_DIFFERENTIAL)
        self.ais_invert_1 = ais.invert()
        self.ais_invert_0 = ais.invert()
        self.adsb_to_6M = filter.rational_resampler_ccc(
                interpolation=5,
                decimation=2,
                taps=[],
                fractional_bw=0)
        self.adsb_decoder_0 = adsb.decoder("Extended Squitter Only", "None", "Brief")


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.adsb_decoder_0, 'decoded'), (self.zeromq_pub_msg_sink_0, 'in'))
        self.msg_connect((self.ais_pdu_to_nmea_0, 'out'), (self.zeromq_pub_msg_sink_0_0, 'in'))
        self.msg_connect((self.ais_pdu_to_nmea_1, 'out'), (self.zeromq_pub_msg_sink_0_0, 'in'))
        self.msg_connect((self.digital_hdlc_deframer_bp_0, 'out'), (self.ais_pdu_to_nmea_0, 'print'))
        self.msg_connect((self.digital_hdlc_deframer_bp_1, 'out'), (self.ais_pdu_to_nmea_1, 'print'))
        self.msg_connect((self.modes_demod_0, 'demodulated'), (self.adsb_decoder_0, 'demodulated'))
        self.connect((self.adsb_to_6M, 0), (self.blocks_throttle_0_0, 0))
        self.connect((self.ais_invert_0, 0), (self.digital_hdlc_deframer_bp_0, 0))
        self.connect((self.ais_invert_1, 0), (self.digital_hdlc_deframer_bp_1, 0))
        self.connect((self.ais_nrzi_0, 0), (self.ais_invert_0, 0))
        self.connect((self.ais_nrzi_1, 0), (self.ais_invert_1, 0))
        self.connect((self.ais_to_48k_0, 0), (self.digital_gmsk_demod_0, 0))
        self.connect((self.ais_to_48k_1, 0), (self.digital_gmsk_demod_1, 0))
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.adsb_to_6M, 0))
        self.connect((self.blocks_float_to_complex_0_0, 0), (self.blocks_throttle_0_1, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_complex_to_mag_squared_0, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.modes_demod_0, 0))
        self.connect((self.blocks_throttle_0_1, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.blocks_throttle_0_1, 0), (self.freq_xlating_fir_filter_xxx_1, 0))
        self.connect((self.blocks_wavfile_source_0, 1), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_wavfile_source_0, 0), (self.blocks_float_to_complex_0, 1))
        self.connect((self.blocks_wavfile_source_0_0, 0), (self.blocks_float_to_complex_0_0, 0))
        self.connect((self.blocks_wavfile_source_0_0, 1), (self.blocks_float_to_complex_0_0, 1))
        self.connect((self.digital_gmsk_demod_0, 0), (self.ais_nrzi_0, 0))
        self.connect((self.digital_gmsk_demod_1, 0), (self.ais_nrzi_1, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.ais_to_48k_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_1, 0), (self.ais_to_48k_1, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "airmaritime_decoder")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate_0(self):
        return self.samp_rate_0

    def set_samp_rate_0(self, samp_rate_0):
        self.samp_rate_0 = samp_rate_0
        self.set_low_pass_taps(firdes.low_pass(1.0, self.samp_rate_0, 11000, 1000, window.WIN_HAMMING, 6.76))
        self.blocks_throttle_0_1.set_sample_rate(self.samp_rate_0)

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
        self.blocks_throttle_0_0.set_sample_rate(self.fs)
        self.qtgui_time_sink_x_0.set_samp_rate(int(self.fs))
        self.modes_demod_0.fs = self.fs




def main(top_block_cls=airmaritime_decoder, options=None):

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
