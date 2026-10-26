#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: SecureCOM Module 2 — Multiband Real-Time Receiver
# Author: AVGARDE SYSTEMS — SecureCOM M1
# Description: Module 2 — 42-Channel Decoder with Combined Spectrum Analyzer
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
import math
from gnuradio import audio
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import network
from gnuradio import zeromq
from gnuradio.filter import pfb
from gnuradio.qtgui import Range, RangeWidget
from PyQt5 import QtCore
import dsd
import os
def _tetra_runtime():
    # TETRA_RUNTIME overrides; else walk up from this file to delhi_testing/tetra_test/gr_tetra_decoder
    env = os.environ.get('TETRA_RUNTIME')
    if env:
        return env
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        c = os.path.join(d, 'tetra_test', 'gr_tetra_decoder')
        if os.path.isdir(c):
            return c
        d = os.path.dirname(d)
    raise ImportError('tetra_test/gr_tetra_decoder not found above ' + __file__ + '; set TETRA_RUNTIME')
sys.path.insert(0, _tetra_runtime())
from tetra_decoder_block import tetra_decoder_block



from gnuradio import qtgui

class securecom_module2_decoder(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "SecureCOM Module 2 — Multiband Real-Time Receiver", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("SecureCOM Module 2 — Multiband Real-Time Receiver")
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

        self.settings = Qt.QSettings("GNU Radio", "securecom_module2_decoder")

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
        self.sps = sps = 2
        self.nfilts = nfilts = 32
        self.constel = constel = digital.constellation_dqpsk().base()
        self.constel.gen_soft_dec_lut(8)
        self.volume = volume = 0.04
        self.variable_adaptive_algorithm_0 = variable_adaptive_algorithm_0 = digital.adaptive_algorithm_cma( constel, 10e-3, 1).base()
        self.squelch_thresh = squelch_thresh = -20
        self.samp_rate = samp_rate = 200000
        self.rrc_taps = rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(sps), 0.35, 11*sps*nfilts)
        self.ppm_corr = ppm_corr = 0
        self.gain_demod_p25 = gain_demod_p25 = 4.24
        self.gain_demod_nxdn = gain_demod_nxdn = 7.28
        self.gain_demod = gain_demod = 1.0
        self.frequency_mhz = frequency_mhz = 467.5625
        self.freq_offset_khz = freq_offset_khz = -1.714
        self.decim = decim = 5
        self.channel_rate = channel_rate = 36000
        self.arity = arity = 4

        ##################################################
        # Blocks
        ##################################################
        self._volume_range = Range(0.01, 20.0, 0.01, 0.04, 200)
        self._volume_win = RangeWidget(self._volume_range, self.set_volume, "Audio Volume Boost", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_win)
        self._squelch_thresh_range = Range(-90, -10, 1, -30, 200)
        self._squelch_thresh_win = RangeWidget(self._squelch_thresh_range, self.set_squelch_thresh, "Noise Squelch Threshold (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_win)
        self._gain_demod_p25_range = Range(0.05, 10.0, 0.01, 4.24, 200)
        self._gain_demod_p25_win = RangeWidget(self._gain_demod_p25_range, self.set_gain_demod_p25, "FM Demod Gain (P25)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_p25_win)
        self._gain_demod_nxdn_range = Range(0.05, 14.0, 0.01, 7.28, 200)
        self._gain_demod_nxdn_win = RangeWidget(self._gain_demod_nxdn_range, self.set_gain_demod_nxdn, "FM Demod Gain (NXDN)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_nxdn_win)
        self._gain_demod_range = Range(0.05, 10.0, 0.01, 1.0, 200)
        self._gain_demod_win = RangeWidget(self._gain_demod_range, self.set_gain_demod, "FM Demod Gain (DMR)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_win)
        self._freq_offset_khz_tool_bar = Qt.QToolBar(self)
        self._freq_offset_khz_tool_bar.addWidget(Qt.QLabel("Baseband offset [kHz]" + ": "))
        self._freq_offset_khz_line_edit = Qt.QLineEdit(str(self.freq_offset_khz))
        self._freq_offset_khz_tool_bar.addWidget(self._freq_offset_khz_line_edit)
        self._freq_offset_khz_line_edit.returnPressed.connect(
            lambda: self.set_freq_offset_khz(eng_notation.str_to_num(str(self._freq_offset_khz_line_edit.text()))))
        self.top_grid_layout.addWidget(self._freq_offset_khz_tool_bar, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.vol_p25_ch9 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch9.set_max_output_buffer(1024)
        self.vol_p25_ch8 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch8.set_max_output_buffer(1024)
        self.vol_p25_ch7 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch7.set_max_output_buffer(1024)
        self.vol_p25_ch6 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch6.set_max_output_buffer(1024)
        self.vol_p25_ch5 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch5.set_max_output_buffer(1024)
        self.vol_p25_ch4 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch4.set_max_output_buffer(1024)
        self.vol_p25_ch3 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch3.set_max_output_buffer(1024)
        self.vol_p25_ch2 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch2.set_max_output_buffer(1024)
        self.vol_p25_ch1 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch1.set_max_output_buffer(1024)
        self.vol_p25_ch0 = blocks.multiply_const_ff(volume)
        self.vol_p25_ch0.set_max_output_buffer(1024)
        self.vol_nxdn_ch9 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch9.set_max_output_buffer(1024)
        self.vol_nxdn_ch8 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch8.set_max_output_buffer(1024)
        self.vol_nxdn_ch7 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch7.set_max_output_buffer(1024)
        self.vol_nxdn_ch6 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch6.set_max_output_buffer(1024)
        self.vol_nxdn_ch5 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch5.set_max_output_buffer(1024)
        self.vol_nxdn_ch4 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch4.set_max_output_buffer(1024)
        self.vol_nxdn_ch3 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch3.set_max_output_buffer(1024)
        self.vol_nxdn_ch2 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch2.set_max_output_buffer(1024)
        self.vol_nxdn_ch15 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch15.set_max_output_buffer(1024)
        self.vol_nxdn_ch14 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch14.set_max_output_buffer(1024)
        self.vol_nxdn_ch13 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch13.set_max_output_buffer(1024)
        self.vol_nxdn_ch12 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch12.set_max_output_buffer(1024)
        self.vol_nxdn_ch11 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch11.set_max_output_buffer(1024)
        self.vol_nxdn_ch10 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch10.set_max_output_buffer(1024)
        self.vol_nxdn_ch1 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch1.set_max_output_buffer(1024)
        self.vol_nxdn_ch0 = blocks.multiply_const_ff(volume)
        self.vol_nxdn_ch0.set_max_output_buffer(1024)
        self.vol_dmr_ch9 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch9.set_max_output_buffer(1024)
        self.vol_dmr_ch8 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch8.set_max_output_buffer(1024)
        self.vol_dmr_ch7 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch7.set_max_output_buffer(1024)
        self.vol_dmr_ch6 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch6.set_max_output_buffer(1024)
        self.vol_dmr_ch5 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch5.set_max_output_buffer(1024)
        self.vol_dmr_ch4 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch4.set_max_output_buffer(1024)
        self.vol_dmr_ch3 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch3.set_max_output_buffer(1024)
        self.vol_dmr_ch2 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch2.set_max_output_buffer(1024)
        self.vol_dmr_ch15 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch15.set_max_output_buffer(1024)
        self.vol_dmr_ch14 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch14.set_max_output_buffer(1024)
        self.vol_dmr_ch13 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch13.set_max_output_buffer(1024)
        self.vol_dmr_ch12 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch12.set_max_output_buffer(1024)
        self.vol_dmr_ch11 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch11.set_max_output_buffer(1024)
        self.vol_dmr_ch10 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch10.set_max_output_buffer(1024)
        self.vol_dmr_ch1 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch1.set_max_output_buffer(1024)
        self.vol_dmr_ch0 = blocks.multiply_const_ff(volume)
        self.vol_dmr_ch0.set_max_output_buffer(1024)
        self.tetra_decoder_block_0 = tetra_decoder_block(log_level=1, remove_fill_bits=True, wireshark_output=False, debug=True)
        self.squelch_p25_ch9 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch9.set_max_output_buffer(1024)
        self.squelch_p25_ch8 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch8.set_max_output_buffer(1024)
        self.squelch_p25_ch7 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch7.set_max_output_buffer(1024)
        self.squelch_p25_ch6 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch6.set_max_output_buffer(1024)
        self.squelch_p25_ch5 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch5.set_max_output_buffer(1024)
        self.squelch_p25_ch4 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch4.set_max_output_buffer(1024)
        self.squelch_p25_ch3 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch3.set_max_output_buffer(1024)
        self.squelch_p25_ch2 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch2.set_max_output_buffer(1024)
        self.squelch_p25_ch1 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch1.set_max_output_buffer(1024)
        self.squelch_p25_ch0 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_p25_ch0.set_max_output_buffer(1024)
        self.squelch_nxdn_ch9 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch9.set_max_output_buffer(1024)
        self.squelch_nxdn_ch8 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch8.set_max_output_buffer(1024)
        self.squelch_nxdn_ch7 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch7.set_max_output_buffer(1024)
        self.squelch_nxdn_ch6 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch6.set_max_output_buffer(1024)
        self.squelch_nxdn_ch5 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch5.set_max_output_buffer(1024)
        self.squelch_nxdn_ch4 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch4.set_max_output_buffer(1024)
        self.squelch_nxdn_ch3 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch3.set_max_output_buffer(1024)
        self.squelch_nxdn_ch2 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch2.set_max_output_buffer(1024)
        self.squelch_nxdn_ch15 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch15.set_max_output_buffer(1024)
        self.squelch_nxdn_ch14 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch14.set_max_output_buffer(1024)
        self.squelch_nxdn_ch13 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch13.set_max_output_buffer(1024)
        self.squelch_nxdn_ch12 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch12.set_max_output_buffer(1024)
        self.squelch_nxdn_ch11 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch11.set_max_output_buffer(1024)
        self.squelch_nxdn_ch10 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch10.set_max_output_buffer(1024)
        self.squelch_nxdn_ch1 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch1.set_max_output_buffer(1024)
        self.squelch_nxdn_ch0 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_nxdn_ch0.set_max_output_buffer(1024)
        self.squelch_dmr_ch9 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch9.set_max_output_buffer(1024)
        self.squelch_dmr_ch8 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch8.set_max_output_buffer(1024)
        self.squelch_dmr_ch7 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch7.set_max_output_buffer(1024)
        self.squelch_dmr_ch6 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch6.set_max_output_buffer(1024)
        self.squelch_dmr_ch5 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch5.set_max_output_buffer(1024)
        self.squelch_dmr_ch4 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch4.set_max_output_buffer(1024)
        self.squelch_dmr_ch3 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch3.set_max_output_buffer(1024)
        self.squelch_dmr_ch2 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch2.set_max_output_buffer(1024)
        self.squelch_dmr_ch15 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch15.set_max_output_buffer(1024)
        self.squelch_dmr_ch14 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch14.set_max_output_buffer(1024)
        self.squelch_dmr_ch13 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch13.set_max_output_buffer(1024)
        self.squelch_dmr_ch12 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch12.set_max_output_buffer(1024)
        self.squelch_dmr_ch11 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch11.set_max_output_buffer(1024)
        self.squelch_dmr_ch10 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch10.set_max_output_buffer(1024)
        self.squelch_dmr_ch1 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch1.set_max_output_buffer(1024)
        self.squelch_dmr_ch0 = analog.simple_squelch_cc(squelch_thresh, 0.05)
        self.squelch_dmr_ch0.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch9 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch9.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch8 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch8.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch7 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch7.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch6 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch6.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch5 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch5.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch4 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch4.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch3 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch3.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch2 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch2.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch1 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch1.set_max_output_buffer(1024)
        self.resamp_iq_p25_ch0 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25_ch0.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch9 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch9.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch8 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch8.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch7 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch7.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch6 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch6.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch5 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch5.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch4 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch4.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch3 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch3.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch2 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch2.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch15 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch15.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch14 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch14.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch13 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch13.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch12 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch12.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch11 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch11.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch10 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch10.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch1 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch1.set_max_output_buffer(1024)
        self.resamp_iq_nxdn_ch0 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn_ch0.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch9 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch9.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch8 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch8.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch7 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch7.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch6 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch6.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch5 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch5.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch4 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch4.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch3 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch3.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch2 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch2.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch15 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch15.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch14 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch14.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch13 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch13.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch12 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch12.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch11 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch11.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch10 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch10.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch1 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch1.set_max_output_buffer(1024)
        self.resamp_iq_dmr_ch0 = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr_ch0.set_max_output_buffer(1024)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_c(
            256, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            channel_rate, #bw
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.1)
        self.qtgui_waterfall_sink_x_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)



        labels = ['Data 0', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._qtgui_waterfall_sink_x_0_win, 3, 0, 1, 2)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_time_sink_tetra = qtgui.time_sink_f(
            1024, #size
            samp_rate, #samp_rate
            'Audio Time Domain — TETRA', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_tetra.set_update_time(0.10)
        self.qtgui_time_sink_tetra.set_y_axis(-1, 1)

        self.qtgui_time_sink_tetra.set_y_label('Amplitude', "")

        self.qtgui_time_sink_tetra.enable_tags(True)
        self.qtgui_time_sink_tetra.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_tetra.enable_autoscale(True)
        self.qtgui_time_sink_tetra.enable_grid(False)
        self.qtgui_time_sink_tetra.enable_axis_labels(True)
        self.qtgui_time_sink_tetra.enable_control_panel(False)
        self.qtgui_time_sink_tetra.enable_stem_plot(False)


        labels = ['audio', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_tetra.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_tetra.set_line_label(i, labels[i])
            self.qtgui_time_sink_tetra.set_line_width(i, widths[i])
            self.qtgui_time_sink_tetra.set_line_color(i, colors[i])
            self.qtgui_time_sink_tetra.set_line_style(i, styles[i])
            self.qtgui_time_sink_tetra.set_line_marker(i, markers[i])
            self.qtgui_time_sink_tetra.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_tetra_win = sip.wrapinstance(self.qtgui_time_sink_tetra.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_tetra_win)
        self.qtgui_time_sink_dnp = qtgui.time_sink_f(
            1024, #size
            samp_rate, #samp_rate
            'Audio Time Domain — DMR/NXDN/P25', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_dnp.set_update_time(0.10)
        self.qtgui_time_sink_dnp.set_y_axis(-1, 1)

        self.qtgui_time_sink_dnp.set_y_label('Amplitude', "")

        self.qtgui_time_sink_dnp.enable_tags(True)
        self.qtgui_time_sink_dnp.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_dnp.enable_autoscale(True)
        self.qtgui_time_sink_dnp.enable_grid(False)
        self.qtgui_time_sink_dnp.enable_axis_labels(True)
        self.qtgui_time_sink_dnp.enable_control_panel(False)
        self.qtgui_time_sink_dnp.enable_stem_plot(False)


        labels = ['audio', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_dnp.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_dnp.set_line_label(i, labels[i])
            self.qtgui_time_sink_dnp.set_line_width(i, widths[i])
            self.qtgui_time_sink_dnp.set_line_color(i, colors[i])
            self.qtgui_time_sink_dnp.set_line_style(i, styles[i])
            self.qtgui_time_sink_dnp.set_line_marker(i, markers[i])
            self.qtgui_time_sink_dnp.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_dnp_win = sip.wrapinstance(self.qtgui_time_sink_dnp.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_dnp_win)
        self.qtgui_freq_sink_combined = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            'SecureCOM Live Spectrum Activity (Blue=DMR, Red=NXDN, Green=P25)', #name
            4,
            None # parent
        )
        self.qtgui_freq_sink_combined.set_update_time(0.10)
        self.qtgui_freq_sink_combined.set_y_axis(-140, 10)
        self.qtgui_freq_sink_combined.set_y_label('Power Spectrum Density', 'dB')
        self.qtgui_freq_sink_combined.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, '')
        self.qtgui_freq_sink_combined.enable_autoscale(True)
        self.qtgui_freq_sink_combined.enable_grid(True)
        self.qtgui_freq_sink_combined.set_fft_average(0.2)
        self.qtgui_freq_sink_combined.enable_axis_labels(True)
        self.qtgui_freq_sink_combined.enable_control_panel(False)
        self.qtgui_freq_sink_combined.set_fft_window_normalized(False)



        labels = ['DMR446 (Port 7001)', 'NXDN96 (Port 7002)', 'P25 Phase 1 (Port 7003)', 'TETRA (Port 7004)', '',
            '', '', '', '', '']
        widths = [2, 2, 2, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(4):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_combined.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_combined.set_line_label(i, labels[i])
            self.qtgui_freq_sink_combined.set_line_width(i, widths[i])
            self.qtgui_freq_sink_combined.set_line_color(i, colors[i])
            self.qtgui_freq_sink_combined.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_combined_win = sip.wrapinstance(self.qtgui_freq_sink_combined.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_freq_sink_combined_win)
        self.qtgui_const_sink_x_0_0 = qtgui.const_sink_c(
            1024, #size
            'output', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0_0.set_y_axis(-2, 2)
        self.qtgui_const_sink_x_0_0.set_x_axis(-2, 2)
        self.qtgui_const_sink_x_0_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0_0.enable_grid(False)
        self.qtgui_const_sink_x_0_0.enable_axis_labels(True)

        self.qtgui_const_sink_x_0_0.disable_legend()

        labels = ['Data 0', 'other rx', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "red", "red", "red",
            "red", "red", "red", "red", "red"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_const_sink_x_0_0_win, 4, 0, 1, 2)
        for r in range(4, 5):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._ppm_corr_range = Range(-20, 15, 1, 0, 200)
        self._ppm_corr_win = RangeWidget(self._ppm_corr_range, self.set_ppm_corr, "PPM correction", "counter_slider", int, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._ppm_corr_win, 2, 0, 1, 2)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.pfb_channelizer_ccf_0_1 = pfb.channelizer_ccf(
            16,
            firdes.low_pass(16.0, samp_rate, (samp_rate/16.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_ccf_0_1.set_channel_map([])
        self.pfb_channelizer_ccf_0_1.declare_sample_delay(0)
        self.pfb_channelizer_ccf_0_1.set_max_output_buffer(1024)
        self.pfb_channelizer_ccf_0_0 = pfb.channelizer_ccf(
            10,
            firdes.low_pass(10.0, samp_rate, (samp_rate/10.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_ccf_0_0.set_channel_map([])
        self.pfb_channelizer_ccf_0_0.declare_sample_delay(0)
        self.pfb_channelizer_ccf_0_0.set_max_output_buffer(1024)
        self.pfb_channelizer_ccf_0 = pfb.channelizer_ccf(
            16,
            firdes.low_pass(16.0, samp_rate, (samp_rate/16.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_ccf_0.set_channel_map([])
        self.pfb_channelizer_ccf_0.declare_sample_delay(0)
        self.pfb_channelizer_ccf_0.set_max_output_buffer(1024)
        self.network_tcp_source_tetra = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7004,server=False)
        self.network_tcp_source_tetra.set_max_output_buffer(1024)
        self.network_tcp_source_p25 = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7003,server=False)
        self.network_tcp_source_p25.set_max_output_buffer(1024)
        self.network_tcp_source_nxdn = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7002,server=False)
        self.network_tcp_source_nxdn.set_max_output_buffer(1024)
        self.network_tcp_source_dmr = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7001,server=False)
        self.network_tcp_source_dmr.set_max_output_buffer(1024)
        self.mmse_resampler_xx_0 = filter.mmse_resampler_cc(0, float(samp_rate)/(float(decim)*float(channel_rate)))
        self.lpf_p25_ch9 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch9.set_max_output_buffer(1024)
        self.lpf_p25_ch8 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch8.set_max_output_buffer(1024)
        self.lpf_p25_ch7 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch7.set_max_output_buffer(1024)
        self.lpf_p25_ch6 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch6.set_max_output_buffer(1024)
        self.lpf_p25_ch5 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch5.set_max_output_buffer(1024)
        self.lpf_p25_ch4 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch4.set_max_output_buffer(1024)
        self.lpf_p25_ch3 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch3.set_max_output_buffer(1024)
        self.lpf_p25_ch2 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch2.set_max_output_buffer(1024)
        self.lpf_p25_ch1 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch1.set_max_output_buffer(1024)
        self.lpf_p25_ch0 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25_ch0.set_max_output_buffer(1024)
        self.lpf_nxdn_ch9 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch9.set_max_output_buffer(1024)
        self.lpf_nxdn_ch8 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch8.set_max_output_buffer(1024)
        self.lpf_nxdn_ch7 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch7.set_max_output_buffer(1024)
        self.lpf_nxdn_ch6 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch6.set_max_output_buffer(1024)
        self.lpf_nxdn_ch5 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch5.set_max_output_buffer(1024)
        self.lpf_nxdn_ch4 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch4.set_max_output_buffer(1024)
        self.lpf_nxdn_ch3 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch3.set_max_output_buffer(1024)
        self.lpf_nxdn_ch2 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch2.set_max_output_buffer(1024)
        self.lpf_nxdn_ch15 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch15.set_max_output_buffer(1024)
        self.lpf_nxdn_ch14 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch14.set_max_output_buffer(1024)
        self.lpf_nxdn_ch13 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch13.set_max_output_buffer(1024)
        self.lpf_nxdn_ch12 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch12.set_max_output_buffer(1024)
        self.lpf_nxdn_ch11 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch11.set_max_output_buffer(1024)
        self.lpf_nxdn_ch10 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch10.set_max_output_buffer(1024)
        self.lpf_nxdn_ch1 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch1.set_max_output_buffer(1024)
        self.lpf_nxdn_ch0 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn_ch0.set_max_output_buffer(1024)
        self.lpf_dmr_ch9 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch9.set_max_output_buffer(1024)
        self.lpf_dmr_ch8 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch8.set_max_output_buffer(1024)
        self.lpf_dmr_ch7 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch7.set_max_output_buffer(1024)
        self.lpf_dmr_ch6 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch6.set_max_output_buffer(1024)
        self.lpf_dmr_ch5 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch5.set_max_output_buffer(1024)
        self.lpf_dmr_ch4 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch4.set_max_output_buffer(1024)
        self.lpf_dmr_ch3 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch3.set_max_output_buffer(1024)
        self.lpf_dmr_ch2 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch2.set_max_output_buffer(1024)
        self.lpf_dmr_ch15 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch15.set_max_output_buffer(1024)
        self.lpf_dmr_ch14 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch14.set_max_output_buffer(1024)
        self.lpf_dmr_ch13 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch13.set_max_output_buffer(1024)
        self.lpf_dmr_ch12 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch12.set_max_output_buffer(1024)
        self.lpf_dmr_ch11 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch11.set_max_output_buffer(1024)
        self.lpf_dmr_ch10 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch10.set_max_output_buffer(1024)
        self.lpf_dmr_ch1 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch1.set_max_output_buffer(1024)
        self.lpf_dmr_ch0 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr_ch0.set_max_output_buffer(1024)
        self._frequency_mhz_tool_bar = Qt.QToolBar(self)
        self._frequency_mhz_tool_bar.addWidget(Qt.QLabel("Frequency [MHz]" + ": "))
        self._frequency_mhz_line_edit = Qt.QLineEdit(str(self.frequency_mhz))
        self._frequency_mhz_tool_bar.addWidget(self._frequency_mhz_line_edit)
        self._frequency_mhz_line_edit.returnPressed.connect(
            lambda: self.set_frequency_mhz(eng_notation.str_to_num(str(self._frequency_mhz_line_edit.text()))))
        self.top_grid_layout.addWidget(self._frequency_mhz_tool_bar, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(decim, firdes.low_pass(1,samp_rate,12500,12500*0.2), freq_offset_khz*1e3, samp_rate)
        self.dsd_p25_ch9 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch9.set_max_output_buffer(1024)
        self.dsd_p25_ch8 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch8.set_max_output_buffer(1024)
        self.dsd_p25_ch7 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch7.set_max_output_buffer(1024)
        self.dsd_p25_ch6 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch6.set_max_output_buffer(1024)
        self.dsd_p25_ch5 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch5.set_max_output_buffer(1024)
        self.dsd_p25_ch4 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch4.set_max_output_buffer(1024)
        self.dsd_p25_ch3 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch3.set_max_output_buffer(1024)
        self.dsd_p25_ch2 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch2.set_max_output_buffer(1024)
        self.dsd_p25_ch1 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch1.set_max_output_buffer(1024)
        self.dsd_p25_ch0 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25_ch0.set_max_output_buffer(1024)
        self.dsd_nxdn_ch9 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch9.set_max_output_buffer(1024)
        self.dsd_nxdn_ch8 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch8.set_max_output_buffer(1024)
        self.dsd_nxdn_ch7 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch7.set_max_output_buffer(1024)
        self.dsd_nxdn_ch6 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch6.set_max_output_buffer(1024)
        self.dsd_nxdn_ch5 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch5.set_max_output_buffer(1024)
        self.dsd_nxdn_ch4 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch4.set_max_output_buffer(1024)
        self.dsd_nxdn_ch3 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch3.set_max_output_buffer(1024)
        self.dsd_nxdn_ch2 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch2.set_max_output_buffer(1024)
        self.dsd_nxdn_ch15 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch15.set_max_output_buffer(1024)
        self.dsd_nxdn_ch14 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch14.set_max_output_buffer(1024)
        self.dsd_nxdn_ch13 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch13.set_max_output_buffer(1024)
        self.dsd_nxdn_ch12 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch12.set_max_output_buffer(1024)
        self.dsd_nxdn_ch11 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch11.set_max_output_buffer(1024)
        self.dsd_nxdn_ch10 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch10.set_max_output_buffer(1024)
        self.dsd_nxdn_ch1 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch1.set_max_output_buffer(1024)
        self.dsd_nxdn_ch0 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn_ch0.set_max_output_buffer(1024)
        self.dsd_dmr_ch9 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch9.set_max_output_buffer(1024)
        self.dsd_dmr_ch8 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch8.set_max_output_buffer(1024)
        self.dsd_dmr_ch7 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch7.set_max_output_buffer(1024)
        self.dsd_dmr_ch6 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch6.set_max_output_buffer(1024)
        self.dsd_dmr_ch5 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch5.set_max_output_buffer(1024)
        self.dsd_dmr_ch4 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch4.set_max_output_buffer(1024)
        self.dsd_dmr_ch3 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch3.set_max_output_buffer(1024)
        self.dsd_dmr_ch2 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch2.set_max_output_buffer(1024)
        self.dsd_dmr_ch15 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch15.set_max_output_buffer(1024)
        self.dsd_dmr_ch14 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch14.set_max_output_buffer(1024)
        self.dsd_dmr_ch13 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch13.set_max_output_buffer(1024)
        self.dsd_dmr_ch12 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch12.set_max_output_buffer(1024)
        self.dsd_dmr_ch11 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch11.set_max_output_buffer(1024)
        self.dsd_dmr_ch10 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch10.set_max_output_buffer(1024)
        self.dsd_dmr_ch1 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch1.set_max_output_buffer(1024)
        self.dsd_dmr_ch0 = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr_ch0.set_max_output_buffer(1024)
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, 0.06283185307179586, rrc_taps, nfilts, nfilts/2, 1.5, sps)
        self.digital_map_bb_0 = digital.map_bb(constel.pre_diff_code())
        self.digital_linear_equalizer_0 = digital.linear_equalizer(15, sps, variable_adaptive_algorithm_0, True, [ ], 'corr_est')
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, 0.35, 45, 0.03141592653589793)
        self.digital_diff_phasor_cc_0 = digital.diff_phasor_cc()
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(constel)
        self.demod_p25_ch9 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch9.set_max_output_buffer(1024)
        self.demod_p25_ch8 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch8.set_max_output_buffer(1024)
        self.demod_p25_ch7 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch7.set_max_output_buffer(1024)
        self.demod_p25_ch6 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch6.set_max_output_buffer(1024)
        self.demod_p25_ch5 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch5.set_max_output_buffer(1024)
        self.demod_p25_ch4 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch4.set_max_output_buffer(1024)
        self.demod_p25_ch3 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch3.set_max_output_buffer(1024)
        self.demod_p25_ch2 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch2.set_max_output_buffer(1024)
        self.demod_p25_ch1 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch1.set_max_output_buffer(1024)
        self.demod_p25_ch0 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25_ch0.set_max_output_buffer(1024)
        self.demod_nxdn_ch9 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch9.set_max_output_buffer(1024)
        self.demod_nxdn_ch8 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch8.set_max_output_buffer(1024)
        self.demod_nxdn_ch7 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch7.set_max_output_buffer(1024)
        self.demod_nxdn_ch6 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch6.set_max_output_buffer(1024)
        self.demod_nxdn_ch5 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch5.set_max_output_buffer(1024)
        self.demod_nxdn_ch4 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch4.set_max_output_buffer(1024)
        self.demod_nxdn_ch3 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch3.set_max_output_buffer(1024)
        self.demod_nxdn_ch2 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch2.set_max_output_buffer(1024)
        self.demod_nxdn_ch15 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch15.set_max_output_buffer(1024)
        self.demod_nxdn_ch14 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch14.set_max_output_buffer(1024)
        self.demod_nxdn_ch13 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch13.set_max_output_buffer(1024)
        self.demod_nxdn_ch12 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch12.set_max_output_buffer(1024)
        self.demod_nxdn_ch11 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch11.set_max_output_buffer(1024)
        self.demod_nxdn_ch10 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch10.set_max_output_buffer(1024)
        self.demod_nxdn_ch1 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch1.set_max_output_buffer(1024)
        self.demod_nxdn_ch0 = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn_ch0.set_max_output_buffer(1024)
        self.demod_dmr_ch9 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch9.set_max_output_buffer(1024)
        self.demod_dmr_ch8 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch8.set_max_output_buffer(1024)
        self.demod_dmr_ch7 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch7.set_max_output_buffer(1024)
        self.demod_dmr_ch6 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch6.set_max_output_buffer(1024)
        self.demod_dmr_ch5 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch5.set_max_output_buffer(1024)
        self.demod_dmr_ch4 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch4.set_max_output_buffer(1024)
        self.demod_dmr_ch3 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch3.set_max_output_buffer(1024)
        self.demod_dmr_ch2 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch2.set_max_output_buffer(1024)
        self.demod_dmr_ch15 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch15.set_max_output_buffer(1024)
        self.demod_dmr_ch14 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch14.set_max_output_buffer(1024)
        self.demod_dmr_ch13 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch13.set_max_output_buffer(1024)
        self.demod_dmr_ch12 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch12.set_max_output_buffer(1024)
        self.demod_dmr_ch11 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch11.set_max_output_buffer(1024)
        self.demod_dmr_ch10 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch10.set_max_output_buffer(1024)
        self.demod_dmr_ch1 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch1.set_max_output_buffer(1024)
        self.demod_dmr_ch0 = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr_ch0.set_max_output_buffer(1024)
        self.bridge_zmq_tetra_events = zeromq.pub_msg_sink('tcp://127.0.0.1:9105', 100, True)
        self.bridge_zmq_tetra = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9104', 100, False, -1, '')
        self.bridge_zmq_p25 = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9103', 100, False, -1, '')
        self.bridge_zmq_nxdn = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9102', 100, False, -1, '')
        self.bridge_zmq_dmr = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9101', 100, False, -1, '')
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(constel.bits_per_symbol())
        self.blocks_message_debug_0 = blocks.message_debug(True)
        self.blocks_add_master = blocks.add_vff(1)
        self.blocks_add_master.set_max_output_buffer(1024)
        self.audio_sink_tn4 = audio.sink(8000, '', True)
        self.audio_sink_tn3 = audio.sink(8000, '', True)
        self.audio_sink_tn2 = audio.sink(8000, '', True)
        self.audio_sink_tn1 = audio.sink(8000, '', True)
        self.audio_sink_tetra_combined = audio.sink(8000, '', True)
        self.audio_sink_0 = audio.sink(48000, '', False)
        self.audio_mix_tetra = blocks.add_vff(1)
        self.audio_mix_tetra.set_max_output_buffer(1024)
        self.audio_mix_p25 = blocks.add_vff(1)
        self.audio_mix_p25.set_max_output_buffer(1024)
        self.audio_mix_nxdn = blocks.add_vff(1)
        self.audio_mix_nxdn.set_max_output_buffer(1024)
        self.audio_mix_dmr = blocks.add_vff(1)
        self.audio_mix_dmr.set_max_output_buffer(1024)
        self.aresamp_p25_ch9 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch9.set_max_output_buffer(1024)
        self.aresamp_p25_ch8 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch8.set_max_output_buffer(1024)
        self.aresamp_p25_ch7 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch7.set_max_output_buffer(1024)
        self.aresamp_p25_ch6 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch6.set_max_output_buffer(1024)
        self.aresamp_p25_ch5 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch5.set_max_output_buffer(1024)
        self.aresamp_p25_ch4 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch4.set_max_output_buffer(1024)
        self.aresamp_p25_ch3 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch3.set_max_output_buffer(1024)
        self.aresamp_p25_ch2 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch2.set_max_output_buffer(1024)
        self.aresamp_p25_ch1 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch1.set_max_output_buffer(1024)
        self.aresamp_p25_ch0 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25_ch0.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch9 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch9.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch8 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch8.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch7 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch7.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch6 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch6.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch5 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch5.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch4 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch4.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch3 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch3.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch2 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch2.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch15 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch15.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch14 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch14.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch13 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch13.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch12 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch12.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch11 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch11.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch10 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch10.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch1 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch1.set_max_output_buffer(1024)
        self.aresamp_nxdn_ch0 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn_ch0.set_max_output_buffer(1024)
        self.aresamp_dmr_ch9 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch9.set_max_output_buffer(1024)
        self.aresamp_dmr_ch8 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch8.set_max_output_buffer(1024)
        self.aresamp_dmr_ch7 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch7.set_max_output_buffer(1024)
        self.aresamp_dmr_ch6 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch6.set_max_output_buffer(1024)
        self.aresamp_dmr_ch5 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch5.set_max_output_buffer(1024)
        self.aresamp_dmr_ch4 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch4.set_max_output_buffer(1024)
        self.aresamp_dmr_ch3 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch3.set_max_output_buffer(1024)
        self.aresamp_dmr_ch2 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch2.set_max_output_buffer(1024)
        self.aresamp_dmr_ch15 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch15.set_max_output_buffer(1024)
        self.aresamp_dmr_ch14 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch14.set_max_output_buffer(1024)
        self.aresamp_dmr_ch13 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch13.set_max_output_buffer(1024)
        self.aresamp_dmr_ch12 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch12.set_max_output_buffer(1024)
        self.aresamp_dmr_ch11 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch11.set_max_output_buffer(1024)
        self.aresamp_dmr_ch10 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch10.set_max_output_buffer(1024)
        self.aresamp_dmr_ch1 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch1.set_max_output_buffer(1024)
        self.aresamp_dmr_ch0 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr_ch0.set_max_output_buffer(1024)
        self.analog_feedforward_agc_cc_0 = analog.feedforward_agc_cc(8, 1)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.tetra_decoder_block_0, 'call_log'), (self.blocks_message_debug_0, 'print'))
        self.msg_connect((self.tetra_decoder_block_0, 'call_log'), (self.bridge_zmq_tetra_events, 'in'))
        self.connect((self.analog_feedforward_agc_cc_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.aresamp_dmr_ch0, 0), (self.vol_dmr_ch0, 0))
        self.connect((self.aresamp_dmr_ch1, 0), (self.vol_dmr_ch1, 0))
        self.connect((self.aresamp_dmr_ch10, 0), (self.vol_dmr_ch10, 0))
        self.connect((self.aresamp_dmr_ch11, 0), (self.vol_dmr_ch11, 0))
        self.connect((self.aresamp_dmr_ch12, 0), (self.vol_dmr_ch12, 0))
        self.connect((self.aresamp_dmr_ch13, 0), (self.vol_dmr_ch13, 0))
        self.connect((self.aresamp_dmr_ch14, 0), (self.vol_dmr_ch14, 0))
        self.connect((self.aresamp_dmr_ch15, 0), (self.vol_dmr_ch15, 0))
        self.connect((self.aresamp_dmr_ch2, 0), (self.vol_dmr_ch2, 0))
        self.connect((self.aresamp_dmr_ch3, 0), (self.vol_dmr_ch3, 0))
        self.connect((self.aresamp_dmr_ch4, 0), (self.vol_dmr_ch4, 0))
        self.connect((self.aresamp_dmr_ch5, 0), (self.vol_dmr_ch5, 0))
        self.connect((self.aresamp_dmr_ch6, 0), (self.vol_dmr_ch6, 0))
        self.connect((self.aresamp_dmr_ch7, 0), (self.vol_dmr_ch7, 0))
        self.connect((self.aresamp_dmr_ch8, 0), (self.vol_dmr_ch8, 0))
        self.connect((self.aresamp_dmr_ch9, 0), (self.vol_dmr_ch9, 0))
        self.connect((self.aresamp_nxdn_ch0, 0), (self.vol_nxdn_ch0, 0))
        self.connect((self.aresamp_nxdn_ch1, 0), (self.vol_nxdn_ch1, 0))
        self.connect((self.aresamp_nxdn_ch10, 0), (self.vol_nxdn_ch10, 0))
        self.connect((self.aresamp_nxdn_ch11, 0), (self.vol_nxdn_ch11, 0))
        self.connect((self.aresamp_nxdn_ch12, 0), (self.vol_nxdn_ch12, 0))
        self.connect((self.aresamp_nxdn_ch13, 0), (self.vol_nxdn_ch13, 0))
        self.connect((self.aresamp_nxdn_ch14, 0), (self.vol_nxdn_ch14, 0))
        self.connect((self.aresamp_nxdn_ch15, 0), (self.vol_nxdn_ch15, 0))
        self.connect((self.aresamp_nxdn_ch2, 0), (self.vol_nxdn_ch2, 0))
        self.connect((self.aresamp_nxdn_ch3, 0), (self.vol_nxdn_ch3, 0))
        self.connect((self.aresamp_nxdn_ch4, 0), (self.vol_nxdn_ch4, 0))
        self.connect((self.aresamp_nxdn_ch5, 0), (self.vol_nxdn_ch5, 0))
        self.connect((self.aresamp_nxdn_ch6, 0), (self.vol_nxdn_ch6, 0))
        self.connect((self.aresamp_nxdn_ch7, 0), (self.vol_nxdn_ch7, 0))
        self.connect((self.aresamp_nxdn_ch8, 0), (self.vol_nxdn_ch8, 0))
        self.connect((self.aresamp_nxdn_ch9, 0), (self.vol_nxdn_ch9, 0))
        self.connect((self.aresamp_p25_ch0, 0), (self.vol_p25_ch0, 0))
        self.connect((self.aresamp_p25_ch1, 0), (self.vol_p25_ch1, 0))
        self.connect((self.aresamp_p25_ch2, 0), (self.vol_p25_ch2, 0))
        self.connect((self.aresamp_p25_ch3, 0), (self.vol_p25_ch3, 0))
        self.connect((self.aresamp_p25_ch4, 0), (self.vol_p25_ch4, 0))
        self.connect((self.aresamp_p25_ch5, 0), (self.vol_p25_ch5, 0))
        self.connect((self.aresamp_p25_ch6, 0), (self.vol_p25_ch6, 0))
        self.connect((self.aresamp_p25_ch7, 0), (self.vol_p25_ch7, 0))
        self.connect((self.aresamp_p25_ch8, 0), (self.vol_p25_ch8, 0))
        self.connect((self.aresamp_p25_ch9, 0), (self.vol_p25_ch9, 0))
        self.connect((self.audio_mix_dmr, 0), (self.blocks_add_master, 0))
        self.connect((self.audio_mix_dmr, 0), (self.bridge_zmq_dmr, 0))
        self.connect((self.audio_mix_nxdn, 0), (self.blocks_add_master, 1))
        self.connect((self.audio_mix_nxdn, 0), (self.bridge_zmq_nxdn, 0))
        self.connect((self.audio_mix_p25, 0), (self.blocks_add_master, 2))
        self.connect((self.audio_mix_p25, 0), (self.bridge_zmq_p25, 0))
        self.connect((self.audio_mix_tetra, 0), (self.audio_sink_tetra_combined, 0))
        self.connect((self.audio_mix_tetra, 0), (self.bridge_zmq_tetra, 0))
        self.connect((self.audio_mix_tetra, 0), (self.qtgui_time_sink_tetra, 0))
        self.connect((self.blocks_add_master, 0), (self.audio_sink_0, 0))
        self.connect((self.blocks_add_master, 0), (self.qtgui_time_sink_dnp, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.tetra_decoder_block_0, 0))
        self.connect((self.demod_dmr_ch0, 0), (self.dsd_dmr_ch0, 0))
        self.connect((self.demod_dmr_ch1, 0), (self.dsd_dmr_ch1, 0))
        self.connect((self.demod_dmr_ch10, 0), (self.dsd_dmr_ch10, 0))
        self.connect((self.demod_dmr_ch11, 0), (self.dsd_dmr_ch11, 0))
        self.connect((self.demod_dmr_ch12, 0), (self.dsd_dmr_ch12, 0))
        self.connect((self.demod_dmr_ch13, 0), (self.dsd_dmr_ch13, 0))
        self.connect((self.demod_dmr_ch14, 0), (self.dsd_dmr_ch14, 0))
        self.connect((self.demod_dmr_ch15, 0), (self.dsd_dmr_ch15, 0))
        self.connect((self.demod_dmr_ch2, 0), (self.dsd_dmr_ch2, 0))
        self.connect((self.demod_dmr_ch3, 0), (self.dsd_dmr_ch3, 0))
        self.connect((self.demod_dmr_ch4, 0), (self.dsd_dmr_ch4, 0))
        self.connect((self.demod_dmr_ch5, 0), (self.dsd_dmr_ch5, 0))
        self.connect((self.demod_dmr_ch6, 0), (self.dsd_dmr_ch6, 0))
        self.connect((self.demod_dmr_ch7, 0), (self.dsd_dmr_ch7, 0))
        self.connect((self.demod_dmr_ch8, 0), (self.dsd_dmr_ch8, 0))
        self.connect((self.demod_dmr_ch9, 0), (self.dsd_dmr_ch9, 0))
        self.connect((self.demod_nxdn_ch0, 0), (self.dsd_nxdn_ch0, 0))
        self.connect((self.demod_nxdn_ch1, 0), (self.dsd_nxdn_ch1, 0))
        self.connect((self.demod_nxdn_ch10, 0), (self.dsd_nxdn_ch10, 0))
        self.connect((self.demod_nxdn_ch11, 0), (self.dsd_nxdn_ch11, 0))
        self.connect((self.demod_nxdn_ch12, 0), (self.dsd_nxdn_ch12, 0))
        self.connect((self.demod_nxdn_ch13, 0), (self.dsd_nxdn_ch13, 0))
        self.connect((self.demod_nxdn_ch14, 0), (self.dsd_nxdn_ch14, 0))
        self.connect((self.demod_nxdn_ch15, 0), (self.dsd_nxdn_ch15, 0))
        self.connect((self.demod_nxdn_ch2, 0), (self.dsd_nxdn_ch2, 0))
        self.connect((self.demod_nxdn_ch3, 0), (self.dsd_nxdn_ch3, 0))
        self.connect((self.demod_nxdn_ch4, 0), (self.dsd_nxdn_ch4, 0))
        self.connect((self.demod_nxdn_ch5, 0), (self.dsd_nxdn_ch5, 0))
        self.connect((self.demod_nxdn_ch6, 0), (self.dsd_nxdn_ch6, 0))
        self.connect((self.demod_nxdn_ch7, 0), (self.dsd_nxdn_ch7, 0))
        self.connect((self.demod_nxdn_ch8, 0), (self.dsd_nxdn_ch8, 0))
        self.connect((self.demod_nxdn_ch9, 0), (self.dsd_nxdn_ch9, 0))
        self.connect((self.demod_p25_ch0, 0), (self.dsd_p25_ch0, 0))
        self.connect((self.demod_p25_ch1, 0), (self.dsd_p25_ch1, 0))
        self.connect((self.demod_p25_ch2, 0), (self.dsd_p25_ch2, 0))
        self.connect((self.demod_p25_ch3, 0), (self.dsd_p25_ch3, 0))
        self.connect((self.demod_p25_ch4, 0), (self.dsd_p25_ch4, 0))
        self.connect((self.demod_p25_ch5, 0), (self.dsd_p25_ch5, 0))
        self.connect((self.demod_p25_ch6, 0), (self.dsd_p25_ch6, 0))
        self.connect((self.demod_p25_ch7, 0), (self.dsd_p25_ch7, 0))
        self.connect((self.demod_p25_ch8, 0), (self.dsd_p25_ch8, 0))
        self.connect((self.demod_p25_ch9, 0), (self.dsd_p25_ch9, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_map_bb_0, 0))
        self.connect((self.digital_diff_phasor_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_diff_phasor_cc_0, 0), (self.qtgui_const_sink_x_0_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))
        self.connect((self.digital_linear_equalizer_0, 0), (self.digital_diff_phasor_cc_0, 0))
        self.connect((self.digital_map_bb_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_linear_equalizer_0, 0))
        self.connect((self.dsd_dmr_ch0, 0), (self.aresamp_dmr_ch0, 0))
        self.connect((self.dsd_dmr_ch1, 0), (self.aresamp_dmr_ch1, 0))
        self.connect((self.dsd_dmr_ch10, 0), (self.aresamp_dmr_ch10, 0))
        self.connect((self.dsd_dmr_ch11, 0), (self.aresamp_dmr_ch11, 0))
        self.connect((self.dsd_dmr_ch12, 0), (self.aresamp_dmr_ch12, 0))
        self.connect((self.dsd_dmr_ch13, 0), (self.aresamp_dmr_ch13, 0))
        self.connect((self.dsd_dmr_ch14, 0), (self.aresamp_dmr_ch14, 0))
        self.connect((self.dsd_dmr_ch15, 0), (self.aresamp_dmr_ch15, 0))
        self.connect((self.dsd_dmr_ch2, 0), (self.aresamp_dmr_ch2, 0))
        self.connect((self.dsd_dmr_ch3, 0), (self.aresamp_dmr_ch3, 0))
        self.connect((self.dsd_dmr_ch4, 0), (self.aresamp_dmr_ch4, 0))
        self.connect((self.dsd_dmr_ch5, 0), (self.aresamp_dmr_ch5, 0))
        self.connect((self.dsd_dmr_ch6, 0), (self.aresamp_dmr_ch6, 0))
        self.connect((self.dsd_dmr_ch7, 0), (self.aresamp_dmr_ch7, 0))
        self.connect((self.dsd_dmr_ch8, 0), (self.aresamp_dmr_ch8, 0))
        self.connect((self.dsd_dmr_ch9, 0), (self.aresamp_dmr_ch9, 0))
        self.connect((self.dsd_nxdn_ch0, 0), (self.aresamp_nxdn_ch0, 0))
        self.connect((self.dsd_nxdn_ch1, 0), (self.aresamp_nxdn_ch1, 0))
        self.connect((self.dsd_nxdn_ch10, 0), (self.aresamp_nxdn_ch10, 0))
        self.connect((self.dsd_nxdn_ch11, 0), (self.aresamp_nxdn_ch11, 0))
        self.connect((self.dsd_nxdn_ch12, 0), (self.aresamp_nxdn_ch12, 0))
        self.connect((self.dsd_nxdn_ch13, 0), (self.aresamp_nxdn_ch13, 0))
        self.connect((self.dsd_nxdn_ch14, 0), (self.aresamp_nxdn_ch14, 0))
        self.connect((self.dsd_nxdn_ch15, 0), (self.aresamp_nxdn_ch15, 0))
        self.connect((self.dsd_nxdn_ch2, 0), (self.aresamp_nxdn_ch2, 0))
        self.connect((self.dsd_nxdn_ch3, 0), (self.aresamp_nxdn_ch3, 0))
        self.connect((self.dsd_nxdn_ch4, 0), (self.aresamp_nxdn_ch4, 0))
        self.connect((self.dsd_nxdn_ch5, 0), (self.aresamp_nxdn_ch5, 0))
        self.connect((self.dsd_nxdn_ch6, 0), (self.aresamp_nxdn_ch6, 0))
        self.connect((self.dsd_nxdn_ch7, 0), (self.aresamp_nxdn_ch7, 0))
        self.connect((self.dsd_nxdn_ch8, 0), (self.aresamp_nxdn_ch8, 0))
        self.connect((self.dsd_nxdn_ch9, 0), (self.aresamp_nxdn_ch9, 0))
        self.connect((self.dsd_p25_ch0, 0), (self.aresamp_p25_ch0, 0))
        self.connect((self.dsd_p25_ch1, 0), (self.aresamp_p25_ch1, 0))
        self.connect((self.dsd_p25_ch2, 0), (self.aresamp_p25_ch2, 0))
        self.connect((self.dsd_p25_ch3, 0), (self.aresamp_p25_ch3, 0))
        self.connect((self.dsd_p25_ch4, 0), (self.aresamp_p25_ch4, 0))
        self.connect((self.dsd_p25_ch5, 0), (self.aresamp_p25_ch5, 0))
        self.connect((self.dsd_p25_ch6, 0), (self.aresamp_p25_ch6, 0))
        self.connect((self.dsd_p25_ch7, 0), (self.aresamp_p25_ch7, 0))
        self.connect((self.dsd_p25_ch8, 0), (self.aresamp_p25_ch8, 0))
        self.connect((self.dsd_p25_ch9, 0), (self.aresamp_p25_ch9, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.mmse_resampler_xx_0, 0))
        self.connect((self.lpf_dmr_ch0, 0), (self.squelch_dmr_ch0, 0))
        self.connect((self.lpf_dmr_ch1, 0), (self.squelch_dmr_ch1, 0))
        self.connect((self.lpf_dmr_ch10, 0), (self.squelch_dmr_ch10, 0))
        self.connect((self.lpf_dmr_ch11, 0), (self.squelch_dmr_ch11, 0))
        self.connect((self.lpf_dmr_ch12, 0), (self.squelch_dmr_ch12, 0))
        self.connect((self.lpf_dmr_ch13, 0), (self.squelch_dmr_ch13, 0))
        self.connect((self.lpf_dmr_ch14, 0), (self.squelch_dmr_ch14, 0))
        self.connect((self.lpf_dmr_ch15, 0), (self.squelch_dmr_ch15, 0))
        self.connect((self.lpf_dmr_ch2, 0), (self.squelch_dmr_ch2, 0))
        self.connect((self.lpf_dmr_ch3, 0), (self.squelch_dmr_ch3, 0))
        self.connect((self.lpf_dmr_ch4, 0), (self.squelch_dmr_ch4, 0))
        self.connect((self.lpf_dmr_ch5, 0), (self.squelch_dmr_ch5, 0))
        self.connect((self.lpf_dmr_ch6, 0), (self.squelch_dmr_ch6, 0))
        self.connect((self.lpf_dmr_ch7, 0), (self.squelch_dmr_ch7, 0))
        self.connect((self.lpf_dmr_ch8, 0), (self.squelch_dmr_ch8, 0))
        self.connect((self.lpf_dmr_ch9, 0), (self.squelch_dmr_ch9, 0))
        self.connect((self.lpf_nxdn_ch0, 0), (self.squelch_nxdn_ch0, 0))
        self.connect((self.lpf_nxdn_ch1, 0), (self.squelch_nxdn_ch1, 0))
        self.connect((self.lpf_nxdn_ch10, 0), (self.squelch_nxdn_ch10, 0))
        self.connect((self.lpf_nxdn_ch11, 0), (self.squelch_nxdn_ch11, 0))
        self.connect((self.lpf_nxdn_ch12, 0), (self.squelch_nxdn_ch12, 0))
        self.connect((self.lpf_nxdn_ch13, 0), (self.squelch_nxdn_ch13, 0))
        self.connect((self.lpf_nxdn_ch14, 0), (self.squelch_nxdn_ch14, 0))
        self.connect((self.lpf_nxdn_ch15, 0), (self.squelch_nxdn_ch15, 0))
        self.connect((self.lpf_nxdn_ch2, 0), (self.squelch_nxdn_ch2, 0))
        self.connect((self.lpf_nxdn_ch3, 0), (self.squelch_nxdn_ch3, 0))
        self.connect((self.lpf_nxdn_ch4, 0), (self.squelch_nxdn_ch4, 0))
        self.connect((self.lpf_nxdn_ch5, 0), (self.squelch_nxdn_ch5, 0))
        self.connect((self.lpf_nxdn_ch6, 0), (self.squelch_nxdn_ch6, 0))
        self.connect((self.lpf_nxdn_ch7, 0), (self.squelch_nxdn_ch7, 0))
        self.connect((self.lpf_nxdn_ch8, 0), (self.squelch_nxdn_ch8, 0))
        self.connect((self.lpf_nxdn_ch9, 0), (self.squelch_nxdn_ch9, 0))
        self.connect((self.lpf_p25_ch0, 0), (self.squelch_p25_ch0, 0))
        self.connect((self.lpf_p25_ch1, 0), (self.squelch_p25_ch1, 0))
        self.connect((self.lpf_p25_ch2, 0), (self.squelch_p25_ch2, 0))
        self.connect((self.lpf_p25_ch3, 0), (self.squelch_p25_ch3, 0))
        self.connect((self.lpf_p25_ch4, 0), (self.squelch_p25_ch4, 0))
        self.connect((self.lpf_p25_ch5, 0), (self.squelch_p25_ch5, 0))
        self.connect((self.lpf_p25_ch6, 0), (self.squelch_p25_ch6, 0))
        self.connect((self.lpf_p25_ch7, 0), (self.squelch_p25_ch7, 0))
        self.connect((self.lpf_p25_ch8, 0), (self.squelch_p25_ch8, 0))
        self.connect((self.lpf_p25_ch9, 0), (self.squelch_p25_ch9, 0))
        self.connect((self.mmse_resampler_xx_0, 0), (self.analog_feedforward_agc_cc_0, 0))
        self.connect((self.mmse_resampler_xx_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.network_tcp_source_dmr, 0), (self.pfb_channelizer_ccf_0, 0))
        self.connect((self.network_tcp_source_dmr, 0), (self.qtgui_freq_sink_combined, 0))
        self.connect((self.network_tcp_source_nxdn, 0), (self.pfb_channelizer_ccf_0_1, 0))
        self.connect((self.network_tcp_source_nxdn, 0), (self.qtgui_freq_sink_combined, 1))
        self.connect((self.network_tcp_source_p25, 0), (self.pfb_channelizer_ccf_0_0, 0))
        self.connect((self.network_tcp_source_p25, 0), (self.qtgui_freq_sink_combined, 2))
        self.connect((self.network_tcp_source_tetra, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.network_tcp_source_tetra, 0), (self.qtgui_freq_sink_combined, 3))
        self.connect((self.pfb_channelizer_ccf_0, 0), (self.resamp_iq_dmr_ch0, 0))
        self.connect((self.pfb_channelizer_ccf_0, 1), (self.resamp_iq_dmr_ch1, 0))
        self.connect((self.pfb_channelizer_ccf_0, 10), (self.resamp_iq_dmr_ch10, 0))
        self.connect((self.pfb_channelizer_ccf_0, 11), (self.resamp_iq_dmr_ch11, 0))
        self.connect((self.pfb_channelizer_ccf_0, 12), (self.resamp_iq_dmr_ch12, 0))
        self.connect((self.pfb_channelizer_ccf_0, 13), (self.resamp_iq_dmr_ch13, 0))
        self.connect((self.pfb_channelizer_ccf_0, 14), (self.resamp_iq_dmr_ch14, 0))
        self.connect((self.pfb_channelizer_ccf_0, 15), (self.resamp_iq_dmr_ch15, 0))
        self.connect((self.pfb_channelizer_ccf_0, 2), (self.resamp_iq_dmr_ch2, 0))
        self.connect((self.pfb_channelizer_ccf_0, 3), (self.resamp_iq_dmr_ch3, 0))
        self.connect((self.pfb_channelizer_ccf_0, 4), (self.resamp_iq_dmr_ch4, 0))
        self.connect((self.pfb_channelizer_ccf_0, 5), (self.resamp_iq_dmr_ch5, 0))
        self.connect((self.pfb_channelizer_ccf_0, 6), (self.resamp_iq_dmr_ch6, 0))
        self.connect((self.pfb_channelizer_ccf_0, 7), (self.resamp_iq_dmr_ch7, 0))
        self.connect((self.pfb_channelizer_ccf_0, 8), (self.resamp_iq_dmr_ch8, 0))
        self.connect((self.pfb_channelizer_ccf_0, 9), (self.resamp_iq_dmr_ch9, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 0), (self.resamp_iq_p25_ch0, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 1), (self.resamp_iq_p25_ch1, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 2), (self.resamp_iq_p25_ch2, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 3), (self.resamp_iq_p25_ch3, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 4), (self.resamp_iq_p25_ch4, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 5), (self.resamp_iq_p25_ch5, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 6), (self.resamp_iq_p25_ch6, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 7), (self.resamp_iq_p25_ch7, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 8), (self.resamp_iq_p25_ch8, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 9), (self.resamp_iq_p25_ch9, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 0), (self.resamp_iq_nxdn_ch0, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 1), (self.resamp_iq_nxdn_ch1, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 10), (self.resamp_iq_nxdn_ch10, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 11), (self.resamp_iq_nxdn_ch11, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 12), (self.resamp_iq_nxdn_ch12, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 13), (self.resamp_iq_nxdn_ch13, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 14), (self.resamp_iq_nxdn_ch14, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 15), (self.resamp_iq_nxdn_ch15, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 2), (self.resamp_iq_nxdn_ch2, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 3), (self.resamp_iq_nxdn_ch3, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 4), (self.resamp_iq_nxdn_ch4, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 5), (self.resamp_iq_nxdn_ch5, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 6), (self.resamp_iq_nxdn_ch6, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 7), (self.resamp_iq_nxdn_ch7, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 8), (self.resamp_iq_nxdn_ch8, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 9), (self.resamp_iq_nxdn_ch9, 0))
        self.connect((self.resamp_iq_dmr_ch0, 0), (self.lpf_dmr_ch0, 0))
        self.connect((self.resamp_iq_dmr_ch1, 0), (self.lpf_dmr_ch1, 0))
        self.connect((self.resamp_iq_dmr_ch10, 0), (self.lpf_dmr_ch10, 0))
        self.connect((self.resamp_iq_dmr_ch11, 0), (self.lpf_dmr_ch11, 0))
        self.connect((self.resamp_iq_dmr_ch12, 0), (self.lpf_dmr_ch12, 0))
        self.connect((self.resamp_iq_dmr_ch13, 0), (self.lpf_dmr_ch13, 0))
        self.connect((self.resamp_iq_dmr_ch14, 0), (self.lpf_dmr_ch14, 0))
        self.connect((self.resamp_iq_dmr_ch15, 0), (self.lpf_dmr_ch15, 0))
        self.connect((self.resamp_iq_dmr_ch2, 0), (self.lpf_dmr_ch2, 0))
        self.connect((self.resamp_iq_dmr_ch3, 0), (self.lpf_dmr_ch3, 0))
        self.connect((self.resamp_iq_dmr_ch4, 0), (self.lpf_dmr_ch4, 0))
        self.connect((self.resamp_iq_dmr_ch5, 0), (self.lpf_dmr_ch5, 0))
        self.connect((self.resamp_iq_dmr_ch6, 0), (self.lpf_dmr_ch6, 0))
        self.connect((self.resamp_iq_dmr_ch7, 0), (self.lpf_dmr_ch7, 0))
        self.connect((self.resamp_iq_dmr_ch8, 0), (self.lpf_dmr_ch8, 0))
        self.connect((self.resamp_iq_dmr_ch9, 0), (self.lpf_dmr_ch9, 0))
        self.connect((self.resamp_iq_nxdn_ch0, 0), (self.lpf_nxdn_ch0, 0))
        self.connect((self.resamp_iq_nxdn_ch1, 0), (self.lpf_nxdn_ch1, 0))
        self.connect((self.resamp_iq_nxdn_ch10, 0), (self.lpf_nxdn_ch10, 0))
        self.connect((self.resamp_iq_nxdn_ch11, 0), (self.lpf_nxdn_ch11, 0))
        self.connect((self.resamp_iq_nxdn_ch12, 0), (self.lpf_nxdn_ch12, 0))
        self.connect((self.resamp_iq_nxdn_ch13, 0), (self.lpf_nxdn_ch13, 0))
        self.connect((self.resamp_iq_nxdn_ch14, 0), (self.lpf_nxdn_ch14, 0))
        self.connect((self.resamp_iq_nxdn_ch15, 0), (self.lpf_nxdn_ch15, 0))
        self.connect((self.resamp_iq_nxdn_ch2, 0), (self.lpf_nxdn_ch2, 0))
        self.connect((self.resamp_iq_nxdn_ch3, 0), (self.lpf_nxdn_ch3, 0))
        self.connect((self.resamp_iq_nxdn_ch4, 0), (self.lpf_nxdn_ch4, 0))
        self.connect((self.resamp_iq_nxdn_ch5, 0), (self.lpf_nxdn_ch5, 0))
        self.connect((self.resamp_iq_nxdn_ch6, 0), (self.lpf_nxdn_ch6, 0))
        self.connect((self.resamp_iq_nxdn_ch7, 0), (self.lpf_nxdn_ch7, 0))
        self.connect((self.resamp_iq_nxdn_ch8, 0), (self.lpf_nxdn_ch8, 0))
        self.connect((self.resamp_iq_nxdn_ch9, 0), (self.lpf_nxdn_ch9, 0))
        self.connect((self.resamp_iq_p25_ch0, 0), (self.lpf_p25_ch0, 0))
        self.connect((self.resamp_iq_p25_ch1, 0), (self.lpf_p25_ch1, 0))
        self.connect((self.resamp_iq_p25_ch2, 0), (self.lpf_p25_ch2, 0))
        self.connect((self.resamp_iq_p25_ch3, 0), (self.lpf_p25_ch3, 0))
        self.connect((self.resamp_iq_p25_ch4, 0), (self.lpf_p25_ch4, 0))
        self.connect((self.resamp_iq_p25_ch5, 0), (self.lpf_p25_ch5, 0))
        self.connect((self.resamp_iq_p25_ch6, 0), (self.lpf_p25_ch6, 0))
        self.connect((self.resamp_iq_p25_ch7, 0), (self.lpf_p25_ch7, 0))
        self.connect((self.resamp_iq_p25_ch8, 0), (self.lpf_p25_ch8, 0))
        self.connect((self.resamp_iq_p25_ch9, 0), (self.lpf_p25_ch9, 0))
        self.connect((self.squelch_dmr_ch0, 0), (self.demod_dmr_ch0, 0))
        self.connect((self.squelch_dmr_ch1, 0), (self.demod_dmr_ch1, 0))
        self.connect((self.squelch_dmr_ch10, 0), (self.demod_dmr_ch10, 0))
        self.connect((self.squelch_dmr_ch11, 0), (self.demod_dmr_ch11, 0))
        self.connect((self.squelch_dmr_ch12, 0), (self.demod_dmr_ch12, 0))
        self.connect((self.squelch_dmr_ch13, 0), (self.demod_dmr_ch13, 0))
        self.connect((self.squelch_dmr_ch14, 0), (self.demod_dmr_ch14, 0))
        self.connect((self.squelch_dmr_ch15, 0), (self.demod_dmr_ch15, 0))
        self.connect((self.squelch_dmr_ch2, 0), (self.demod_dmr_ch2, 0))
        self.connect((self.squelch_dmr_ch3, 0), (self.demod_dmr_ch3, 0))
        self.connect((self.squelch_dmr_ch4, 0), (self.demod_dmr_ch4, 0))
        self.connect((self.squelch_dmr_ch5, 0), (self.demod_dmr_ch5, 0))
        self.connect((self.squelch_dmr_ch6, 0), (self.demod_dmr_ch6, 0))
        self.connect((self.squelch_dmr_ch7, 0), (self.demod_dmr_ch7, 0))
        self.connect((self.squelch_dmr_ch8, 0), (self.demod_dmr_ch8, 0))
        self.connect((self.squelch_dmr_ch9, 0), (self.demod_dmr_ch9, 0))
        self.connect((self.squelch_nxdn_ch0, 0), (self.demod_nxdn_ch0, 0))
        self.connect((self.squelch_nxdn_ch1, 0), (self.demod_nxdn_ch1, 0))
        self.connect((self.squelch_nxdn_ch10, 0), (self.demod_nxdn_ch10, 0))
        self.connect((self.squelch_nxdn_ch11, 0), (self.demod_nxdn_ch11, 0))
        self.connect((self.squelch_nxdn_ch12, 0), (self.demod_nxdn_ch12, 0))
        self.connect((self.squelch_nxdn_ch13, 0), (self.demod_nxdn_ch13, 0))
        self.connect((self.squelch_nxdn_ch14, 0), (self.demod_nxdn_ch14, 0))
        self.connect((self.squelch_nxdn_ch15, 0), (self.demod_nxdn_ch15, 0))
        self.connect((self.squelch_nxdn_ch2, 0), (self.demod_nxdn_ch2, 0))
        self.connect((self.squelch_nxdn_ch3, 0), (self.demod_nxdn_ch3, 0))
        self.connect((self.squelch_nxdn_ch4, 0), (self.demod_nxdn_ch4, 0))
        self.connect((self.squelch_nxdn_ch5, 0), (self.demod_nxdn_ch5, 0))
        self.connect((self.squelch_nxdn_ch6, 0), (self.demod_nxdn_ch6, 0))
        self.connect((self.squelch_nxdn_ch7, 0), (self.demod_nxdn_ch7, 0))
        self.connect((self.squelch_nxdn_ch8, 0), (self.demod_nxdn_ch8, 0))
        self.connect((self.squelch_nxdn_ch9, 0), (self.demod_nxdn_ch9, 0))
        self.connect((self.squelch_p25_ch0, 0), (self.demod_p25_ch0, 0))
        self.connect((self.squelch_p25_ch1, 0), (self.demod_p25_ch1, 0))
        self.connect((self.squelch_p25_ch2, 0), (self.demod_p25_ch2, 0))
        self.connect((self.squelch_p25_ch3, 0), (self.demod_p25_ch3, 0))
        self.connect((self.squelch_p25_ch4, 0), (self.demod_p25_ch4, 0))
        self.connect((self.squelch_p25_ch5, 0), (self.demod_p25_ch5, 0))
        self.connect((self.squelch_p25_ch6, 0), (self.demod_p25_ch6, 0))
        self.connect((self.squelch_p25_ch7, 0), (self.demod_p25_ch7, 0))
        self.connect((self.squelch_p25_ch8, 0), (self.demod_p25_ch8, 0))
        self.connect((self.squelch_p25_ch9, 0), (self.demod_p25_ch9, 0))
        self.connect((self.tetra_decoder_block_0, 1), (self.audio_mix_tetra, 1))
        self.connect((self.tetra_decoder_block_0, 2), (self.audio_mix_tetra, 2))
        self.connect((self.tetra_decoder_block_0, 3), (self.audio_mix_tetra, 3))
        self.connect((self.tetra_decoder_block_0, 0), (self.audio_mix_tetra, 0))
        self.connect((self.tetra_decoder_block_0, 0), (self.audio_sink_tn1, 0))
        self.connect((self.tetra_decoder_block_0, 1), (self.audio_sink_tn2, 0))
        self.connect((self.tetra_decoder_block_0, 2), (self.audio_sink_tn3, 0))
        self.connect((self.tetra_decoder_block_0, 3), (self.audio_sink_tn4, 0))
        self.connect((self.vol_dmr_ch0, 0), (self.audio_mix_dmr, 0))
        self.connect((self.vol_dmr_ch1, 0), (self.audio_mix_dmr, 1))
        self.connect((self.vol_dmr_ch10, 0), (self.audio_mix_dmr, 10))
        self.connect((self.vol_dmr_ch11, 0), (self.audio_mix_dmr, 11))
        self.connect((self.vol_dmr_ch12, 0), (self.audio_mix_dmr, 12))
        self.connect((self.vol_dmr_ch13, 0), (self.audio_mix_dmr, 13))
        self.connect((self.vol_dmr_ch14, 0), (self.audio_mix_dmr, 14))
        self.connect((self.vol_dmr_ch15, 0), (self.audio_mix_dmr, 15))
        self.connect((self.vol_dmr_ch2, 0), (self.audio_mix_dmr, 2))
        self.connect((self.vol_dmr_ch3, 0), (self.audio_mix_dmr, 3))
        self.connect((self.vol_dmr_ch4, 0), (self.audio_mix_dmr, 4))
        self.connect((self.vol_dmr_ch5, 0), (self.audio_mix_dmr, 5))
        self.connect((self.vol_dmr_ch6, 0), (self.audio_mix_dmr, 6))
        self.connect((self.vol_dmr_ch7, 0), (self.audio_mix_dmr, 7))
        self.connect((self.vol_dmr_ch8, 0), (self.audio_mix_dmr, 8))
        self.connect((self.vol_dmr_ch9, 0), (self.audio_mix_dmr, 9))
        self.connect((self.vol_nxdn_ch0, 0), (self.audio_mix_nxdn, 0))
        self.connect((self.vol_nxdn_ch1, 0), (self.audio_mix_nxdn, 1))
        self.connect((self.vol_nxdn_ch10, 0), (self.audio_mix_nxdn, 10))
        self.connect((self.vol_nxdn_ch11, 0), (self.audio_mix_nxdn, 11))
        self.connect((self.vol_nxdn_ch12, 0), (self.audio_mix_nxdn, 12))
        self.connect((self.vol_nxdn_ch13, 0), (self.audio_mix_nxdn, 13))
        self.connect((self.vol_nxdn_ch14, 0), (self.audio_mix_nxdn, 14))
        self.connect((self.vol_nxdn_ch15, 0), (self.audio_mix_nxdn, 15))
        self.connect((self.vol_nxdn_ch2, 0), (self.audio_mix_nxdn, 2))
        self.connect((self.vol_nxdn_ch3, 0), (self.audio_mix_nxdn, 3))
        self.connect((self.vol_nxdn_ch4, 0), (self.audio_mix_nxdn, 4))
        self.connect((self.vol_nxdn_ch5, 0), (self.audio_mix_nxdn, 5))
        self.connect((self.vol_nxdn_ch6, 0), (self.audio_mix_nxdn, 6))
        self.connect((self.vol_nxdn_ch7, 0), (self.audio_mix_nxdn, 7))
        self.connect((self.vol_nxdn_ch8, 0), (self.audio_mix_nxdn, 8))
        self.connect((self.vol_nxdn_ch9, 0), (self.audio_mix_nxdn, 9))
        self.connect((self.vol_p25_ch0, 0), (self.audio_mix_p25, 0))
        self.connect((self.vol_p25_ch1, 0), (self.audio_mix_p25, 1))
        self.connect((self.vol_p25_ch2, 0), (self.audio_mix_p25, 2))
        self.connect((self.vol_p25_ch3, 0), (self.audio_mix_p25, 3))
        self.connect((self.vol_p25_ch4, 0), (self.audio_mix_p25, 4))
        self.connect((self.vol_p25_ch5, 0), (self.audio_mix_p25, 5))
        self.connect((self.vol_p25_ch6, 0), (self.audio_mix_p25, 6))
        self.connect((self.vol_p25_ch7, 0), (self.audio_mix_p25, 7))
        self.connect((self.vol_p25_ch8, 0), (self.audio_mix_p25, 8))
        self.connect((self.vol_p25_ch9, 0), (self.audio_mix_p25, 9))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "securecom_module2_decoder")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_rrc_taps(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.sps), 0.35, 11*self.sps*self.nfilts))

    def get_nfilts(self):
        return self.nfilts

    def set_nfilts(self, nfilts):
        self.nfilts = nfilts
        self.set_rrc_taps(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.sps), 0.35, 11*self.sps*self.nfilts))

    def get_constel(self):
        return self.constel

    def set_constel(self, constel):
        self.constel = constel

    def get_volume(self):
        return self.volume

    def set_volume(self, volume):
        self.volume = volume
        self.vol_dmr_ch0.set_k(self.volume)
        self.vol_dmr_ch1.set_k(self.volume)
        self.vol_dmr_ch10.set_k(self.volume)
        self.vol_dmr_ch11.set_k(self.volume)
        self.vol_dmr_ch12.set_k(self.volume)
        self.vol_dmr_ch13.set_k(self.volume)
        self.vol_dmr_ch14.set_k(self.volume)
        self.vol_dmr_ch15.set_k(self.volume)
        self.vol_dmr_ch2.set_k(self.volume)
        self.vol_dmr_ch3.set_k(self.volume)
        self.vol_dmr_ch4.set_k(self.volume)
        self.vol_dmr_ch5.set_k(self.volume)
        self.vol_dmr_ch6.set_k(self.volume)
        self.vol_dmr_ch7.set_k(self.volume)
        self.vol_dmr_ch8.set_k(self.volume)
        self.vol_dmr_ch9.set_k(self.volume)
        self.vol_nxdn_ch0.set_k(self.volume)
        self.vol_nxdn_ch1.set_k(self.volume)
        self.vol_nxdn_ch10.set_k(self.volume)
        self.vol_nxdn_ch11.set_k(self.volume)
        self.vol_nxdn_ch12.set_k(self.volume)
        self.vol_nxdn_ch13.set_k(self.volume)
        self.vol_nxdn_ch14.set_k(self.volume)
        self.vol_nxdn_ch15.set_k(self.volume)
        self.vol_nxdn_ch2.set_k(self.volume)
        self.vol_nxdn_ch3.set_k(self.volume)
        self.vol_nxdn_ch4.set_k(self.volume)
        self.vol_nxdn_ch5.set_k(self.volume)
        self.vol_nxdn_ch6.set_k(self.volume)
        self.vol_nxdn_ch7.set_k(self.volume)
        self.vol_nxdn_ch8.set_k(self.volume)
        self.vol_nxdn_ch9.set_k(self.volume)
        self.vol_p25_ch0.set_k(self.volume)
        self.vol_p25_ch1.set_k(self.volume)
        self.vol_p25_ch2.set_k(self.volume)
        self.vol_p25_ch3.set_k(self.volume)
        self.vol_p25_ch4.set_k(self.volume)
        self.vol_p25_ch5.set_k(self.volume)
        self.vol_p25_ch6.set_k(self.volume)
        self.vol_p25_ch7.set_k(self.volume)
        self.vol_p25_ch8.set_k(self.volume)
        self.vol_p25_ch9.set_k(self.volume)

    def get_variable_adaptive_algorithm_0(self):
        return self.variable_adaptive_algorithm_0

    def set_variable_adaptive_algorithm_0(self, variable_adaptive_algorithm_0):
        self.variable_adaptive_algorithm_0 = variable_adaptive_algorithm_0

    def get_squelch_thresh(self):
        return self.squelch_thresh

    def set_squelch_thresh(self, squelch_thresh):
        self.squelch_thresh = squelch_thresh
        self.squelch_dmr_ch0.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch1.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch10.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch11.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch12.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch13.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch14.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch15.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch2.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch3.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch4.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch5.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch6.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch7.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch8.set_threshold(self.squelch_thresh)
        self.squelch_dmr_ch9.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch0.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch1.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch10.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch11.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch12.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch13.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch14.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch15.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch2.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch3.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch4.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch5.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch6.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch7.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch8.set_threshold(self.squelch_thresh)
        self.squelch_nxdn_ch9.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch0.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch1.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch2.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch3.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch4.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch5.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch6.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch7.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch8.set_threshold(self.squelch_thresh)
        self.squelch_p25_ch9.set_threshold(self.squelch_thresh)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.freq_xlating_fir_filter_xxx_0.set_taps(firdes.low_pass(1,self.samp_rate,12500,12500*0.2))
        self.mmse_resampler_xx_0.set_resamp_ratio(float(self.samp_rate)/(float(self.decim)*float(self.channel_rate)))
        self.pfb_channelizer_ccf_0.set_taps(firdes.low_pass(16.0, self.samp_rate, (self.samp_rate/16.0)/2.0, 1000))
        self.pfb_channelizer_ccf_0_0.set_taps(firdes.low_pass(10.0, self.samp_rate, (self.samp_rate/10.0)/2.0, 1000))
        self.pfb_channelizer_ccf_0_1.set_taps(firdes.low_pass(16.0, self.samp_rate, (self.samp_rate/16.0)/2.0, 1000))
        self.qtgui_freq_sink_combined.set_frequency_range(0, self.samp_rate)
        self.qtgui_time_sink_dnp.set_samp_rate(self.samp_rate)
        self.qtgui_time_sink_tetra.set_samp_rate(self.samp_rate)

    def get_rrc_taps(self):
        return self.rrc_taps

    def set_rrc_taps(self, rrc_taps):
        self.rrc_taps = rrc_taps
        self.digital_pfb_clock_sync_xxx_0.update_taps(self.rrc_taps)

    def get_ppm_corr(self):
        return self.ppm_corr

    def set_ppm_corr(self, ppm_corr):
        self.ppm_corr = ppm_corr

    def get_gain_demod_p25(self):
        return self.gain_demod_p25

    def set_gain_demod_p25(self, gain_demod_p25):
        self.gain_demod_p25 = gain_demod_p25
        self.demod_p25_ch0.set_gain(self.gain_demod_p25)
        self.demod_p25_ch1.set_gain(self.gain_demod_p25)
        self.demod_p25_ch2.set_gain(self.gain_demod_p25)
        self.demod_p25_ch3.set_gain(self.gain_demod_p25)
        self.demod_p25_ch4.set_gain(self.gain_demod_p25)
        self.demod_p25_ch5.set_gain(self.gain_demod_p25)
        self.demod_p25_ch6.set_gain(self.gain_demod_p25)
        self.demod_p25_ch7.set_gain(self.gain_demod_p25)
        self.demod_p25_ch8.set_gain(self.gain_demod_p25)
        self.demod_p25_ch9.set_gain(self.gain_demod_p25)

    def get_gain_demod_nxdn(self):
        return self.gain_demod_nxdn

    def set_gain_demod_nxdn(self, gain_demod_nxdn):
        self.gain_demod_nxdn = gain_demod_nxdn
        self.demod_nxdn_ch0.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch1.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch10.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch11.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch12.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch13.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch14.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch15.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch2.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch3.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch4.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch5.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch6.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch7.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch8.set_gain(self.gain_demod_nxdn)
        self.demod_nxdn_ch9.set_gain(self.gain_demod_nxdn)

    def get_gain_demod(self):
        return self.gain_demod

    def set_gain_demod(self, gain_demod):
        self.gain_demod = gain_demod
        self.demod_dmr_ch0.set_gain(self.gain_demod)
        self.demod_dmr_ch1.set_gain(self.gain_demod)
        self.demod_dmr_ch10.set_gain(self.gain_demod)
        self.demod_dmr_ch11.set_gain(self.gain_demod)
        self.demod_dmr_ch12.set_gain(self.gain_demod)
        self.demod_dmr_ch13.set_gain(self.gain_demod)
        self.demod_dmr_ch14.set_gain(self.gain_demod)
        self.demod_dmr_ch15.set_gain(self.gain_demod)
        self.demod_dmr_ch2.set_gain(self.gain_demod)
        self.demod_dmr_ch3.set_gain(self.gain_demod)
        self.demod_dmr_ch4.set_gain(self.gain_demod)
        self.demod_dmr_ch5.set_gain(self.gain_demod)
        self.demod_dmr_ch6.set_gain(self.gain_demod)
        self.demod_dmr_ch7.set_gain(self.gain_demod)
        self.demod_dmr_ch8.set_gain(self.gain_demod)
        self.demod_dmr_ch9.set_gain(self.gain_demod)

    def get_frequency_mhz(self):
        return self.frequency_mhz

    def set_frequency_mhz(self, frequency_mhz):
        self.frequency_mhz = frequency_mhz
        Qt.QMetaObject.invokeMethod(self._frequency_mhz_line_edit, "setText", Qt.Q_ARG("QString", eng_notation.num_to_str(self.frequency_mhz)))

    def get_freq_offset_khz(self):
        return self.freq_offset_khz

    def set_freq_offset_khz(self, freq_offset_khz):
        self.freq_offset_khz = freq_offset_khz
        Qt.QMetaObject.invokeMethod(self._freq_offset_khz_line_edit, "setText", Qt.Q_ARG("QString", eng_notation.num_to_str(self.freq_offset_khz)))
        self.freq_xlating_fir_filter_xxx_0.set_center_freq(self.freq_offset_khz*1e3)

    def get_decim(self):
        return self.decim

    def set_decim(self, decim):
        self.decim = decim
        self.mmse_resampler_xx_0.set_resamp_ratio(float(self.samp_rate)/(float(self.decim)*float(self.channel_rate)))

    def get_channel_rate(self):
        return self.channel_rate

    def set_channel_rate(self, channel_rate):
        self.channel_rate = channel_rate
        self.mmse_resampler_xx_0.set_resamp_ratio(float(self.samp_rate)/(float(self.decim)*float(self.channel_rate)))
        self.qtgui_waterfall_sink_x_0.set_frequency_range(0, self.channel_rate)

    def get_arity(self):
        return self.arity

    def set_arity(self, arity):
        self.arity = arity




def main(top_block_cls=securecom_module2_decoder, options=None):

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
