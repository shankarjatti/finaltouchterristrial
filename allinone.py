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
import sys, os
def _tetra_runtime():
    # TETRA_RUNTIME overrides; else walk up from this file to delhi_testing/tetra_test/gr_tetra_decoder
    env = os.environ.get('TETRA_RUNTIME')
    if env:
        return env
    # __file__ is undefined while GRC evaluates this at compile time; use the cwd then
    d = os.path.dirname(os.path.abspath(globals().get('__file__', os.path.join(os.getcwd(), '_'))))
    for _ in range(8):
        c = os.path.join(d, 'tetra_test', 'gr_tetra_decoder')
        if os.path.isdir(c):
            return c
        d = os.path.dirname(d)
    raise ImportError('tetra_test/gr_tetra_decoder not found; set TETRA_RUNTIME')
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
        self.volume_x2tdma = volume_x2tdma = 0.5
        self.volume_provoice = volume_provoice = 0.5
        self.volume_p25 = volume_p25 = 0.5
        self.volume_nxdn48 = volume_nxdn48 = 3.0
        self.volume_nxdn = volume_nxdn = 0.5
        self.volume_dstar = volume_dstar = 0.5
        self.volume_dmr = volume_dmr = 0.2
        self.variable_adaptive_algorithm_0 = variable_adaptive_algorithm_0 = digital.adaptive_algorithm_cma( constel, 10e-3, 1).base()
        self.squelch_thresh_x2tdma = squelch_thresh_x2tdma = -73
        self.squelch_thresh_provoice = squelch_thresh_provoice = -73
        self.squelch_thresh_p25 = squelch_thresh_p25 = -73
        self.squelch_thresh_nxdn48 = squelch_thresh_nxdn48 = -73
        self.squelch_thresh_nxdn = squelch_thresh_nxdn = -73
        self.squelch_thresh_dstar = squelch_thresh_dstar = -73
        self.squelch_thresh_dmr = squelch_thresh_dmr = -73
        self.samp_rate = samp_rate = 200000
        self.rrc_taps = rrc_taps = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(sps), 0.35, 11*sps*nfilts)
        self.ppm_corr = ppm_corr = 0
        self.gain_demod_x2tdma = gain_demod_x2tdma = 1.0
        self.gain_demod_provoice = gain_demod_provoice = 1.0
        self.gain_demod_p25 = gain_demod_p25 = 1.0
        self.gain_demod_nxdn48 = gain_demod_nxdn48 = 1.0
        self.gain_demod_nxdn = gain_demod_nxdn = 1.0
        self.gain_demod_dstar = gain_demod_dstar = 1.0
        self.gain_demod = gain_demod = 1.0
        self.frequency_mhz = frequency_mhz = 467.5625
        self.freq_offset_khz = freq_offset_khz = -1.714
        self.decim = decim = 5
        self.channel_rate = channel_rate = 36000
        self.arity = arity = 4

        ##################################################
        # Blocks
        ##################################################
        self._volume_x2tdma_range = Range(0.01, 20.0, 0.01, 0.5, 200)
        self._volume_x2tdma_win = RangeWidget(self._volume_x2tdma_range, self.set_volume_x2tdma, "Volume X2-TDMA", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_x2tdma_win)
        self._volume_provoice_range = Range(0.01, 20.0, 0.01, 0.5, 200)
        self._volume_provoice_win = RangeWidget(self._volume_provoice_range, self.set_volume_provoice, "Volume ProVoice", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_provoice_win)
        self._volume_p25_range = Range(0.01, 20.0, 0.01, 0.5, 200)
        self._volume_p25_win = RangeWidget(self._volume_p25_range, self.set_volume_p25, "Volume P25", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_p25_win)
        self._volume_nxdn48_range = Range(0.01, 20.0, 0.01, 3.0, 200)
        self._volume_nxdn48_win = RangeWidget(self._volume_nxdn48_range, self.set_volume_nxdn48, "Volume NXDN48", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_nxdn48_win)
        self._volume_nxdn_range = Range(0.01, 20.0, 0.01, 0.5, 200)
        self._volume_nxdn_win = RangeWidget(self._volume_nxdn_range, self.set_volume_nxdn, "Volume NXDN", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_nxdn_win)
        self._volume_dstar_range = Range(0.01, 20.0, 0.01, 0.5, 200)
        self._volume_dstar_win = RangeWidget(self._volume_dstar_range, self.set_volume_dstar, "Volume D-STAR", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_dstar_win)
        self._volume_dmr_range = Range(0.01, 20.0, 0.01, 0.2, 200)
        self._volume_dmr_win = RangeWidget(self._volume_dmr_range, self.set_volume_dmr, "Volume DMR", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_dmr_win)
        self._squelch_thresh_x2tdma_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_x2tdma_win = RangeWidget(self._squelch_thresh_x2tdma_range, self.set_squelch_thresh_x2tdma, "Squelch X2-TDMA (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_x2tdma_win)
        self._squelch_thresh_provoice_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_provoice_win = RangeWidget(self._squelch_thresh_provoice_range, self.set_squelch_thresh_provoice, "Squelch ProVoice (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_provoice_win)
        self._squelch_thresh_p25_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_p25_win = RangeWidget(self._squelch_thresh_p25_range, self.set_squelch_thresh_p25, "Squelch P25 (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_p25_win)
        self._squelch_thresh_nxdn48_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_nxdn48_win = RangeWidget(self._squelch_thresh_nxdn48_range, self.set_squelch_thresh_nxdn48, "Squelch NXDN48 (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_nxdn48_win)
        self._squelch_thresh_nxdn_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_nxdn_win = RangeWidget(self._squelch_thresh_nxdn_range, self.set_squelch_thresh_nxdn, "Squelch NXDN (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_nxdn_win)
        self._squelch_thresh_dstar_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_dstar_win = RangeWidget(self._squelch_thresh_dstar_range, self.set_squelch_thresh_dstar, "Squelch D-STAR (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_dstar_win)
        self._squelch_thresh_dmr_range = Range(-90, -10, 1, -73, 200)
        self._squelch_thresh_dmr_win = RangeWidget(self._squelch_thresh_dmr_range, self.set_squelch_thresh_dmr, "Squelch DMR (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._squelch_thresh_dmr_win)
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
        self.vol_x2tdma = blocks.multiply_const_ff(volume_x2tdma)
        self.vol_x2tdma.set_max_output_buffer(1024)
        self.vol_provoice = blocks.multiply_const_ff(volume_provoice)
        self.vol_provoice.set_max_output_buffer(1024)
        self.vol_p25 = blocks.multiply_const_ff(volume_p25)
        self.vol_p25.set_max_output_buffer(1024)
        self.vol_nxdn48 = blocks.multiply_const_ff(volume_nxdn48)
        self.vol_nxdn48.set_max_output_buffer(1024)
        self.vol_nxdn = blocks.multiply_const_ff(volume_nxdn)
        self.vol_nxdn.set_max_output_buffer(1024)
        self.vol_dstar = blocks.multiply_const_ff(volume_dstar)
        self.vol_dstar.set_max_output_buffer(1024)
        self.vol_dmr = blocks.multiply_const_ff(volume_dmr)
        self.vol_dmr.set_max_output_buffer(1024)
        self.tetra_decoder_block_0 = tetra_decoder_block(log_level=1, remove_fill_bits=True, wireshark_output=False, debug=True)
        self.squelch_x2tdma = analog.simple_squelch_cc(squelch_thresh_x2tdma, 0.05)
        self.squelch_x2tdma.set_max_output_buffer(1024)
        self.squelch_provoice = analog.simple_squelch_cc(squelch_thresh_provoice, 0.05)
        self.squelch_provoice.set_max_output_buffer(1024)
        self.squelch_p25 = analog.simple_squelch_cc(squelch_thresh_p25, 0.05)
        self.squelch_p25.set_max_output_buffer(1024)
        self.squelch_nxdn48 = analog.simple_squelch_cc(squelch_thresh_nxdn48, 0.05)
        self.squelch_nxdn48.set_max_output_buffer(1024)
        self.squelch_nxdn = analog.simple_squelch_cc(squelch_thresh_nxdn, 0.05)
        self.squelch_nxdn.set_max_output_buffer(1024)
        self.squelch_dstar = analog.simple_squelch_cc(squelch_thresh_dstar, 0.05)
        self.squelch_dstar.set_max_output_buffer(1024)
        self.squelch_dmr = analog.simple_squelch_cc(squelch_thresh_dmr, 0.05)
        self.squelch_dmr.set_max_output_buffer(1024)
        self.resamp_iq_x2tdma = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_x2tdma.set_max_output_buffer(1024)
        self.resamp_iq_provoice = filter.rational_resampler_ccf(
                interpolation=48,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_provoice.set_max_output_buffer(1024)
        self.resamp_iq_p25 = filter.rational_resampler_ccf(
                interpolation=12,
                decimation=5,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_p25.set_max_output_buffer(1024)
        self.resamp_iq_nxdn48 = filter.rational_resampler_ccf(
                interpolation=192,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn48.set_max_output_buffer(1024)
        self.resamp_iq_nxdn = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_nxdn.set_max_output_buffer(1024)
        self.resamp_iq_dstar = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dstar.set_max_output_buffer(1024)
        self.resamp_iq_dmr = filter.rational_resampler_ccf(
                interpolation=96,
                decimation=25,
                taps=[],
                fractional_bw=0.4)
        self.resamp_iq_dmr.set_max_output_buffer(1024)
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
            48000, #samp_rate
            'Decoded Audio — 7 DSD protocols (48 kHz)', #name
            7, #number of inputs
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


        labels = ['DMR446', 'NXDN96', 'P25 Ph1', 'NXDN48', 'D-STAR',
            'X2-TDMA', 'ProVoice', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'magenta', 'cyan',
            'dark red', 'dark blue', 'blue', 'blue', 'blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(7):
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
            'SecureCOM Live Spectrum — 8 bands (colours match the console)', #name
            8,
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



        labels = ['DMR446 (7001)', 'NXDN96 (7002)', 'P25 Ph1 (7003)', 'TETRA (7004)', 'NXDN48 (7005)',
            'D-STAR (7006)', 'X2-TDMA (7007)', 'ProVoice (7008)', '', '']
        widths = [2, 2, 2, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "magenta",
            "cyan", "dark red", "dark blue", "blue", "blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(8):
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
        self.pfb_channelizer_x2tdma = pfb.channelizer_ccf(
            16,
            firdes.low_pass(16.0, samp_rate, (samp_rate/16.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_x2tdma.set_channel_map([])
        self.pfb_channelizer_x2tdma.declare_sample_delay(0)
        self.pfb_channelizer_x2tdma.set_max_output_buffer(1024)
        self.pfb_channelizer_provoice = pfb.channelizer_ccf(
            8,
            firdes.low_pass(8.0, samp_rate, (samp_rate/8.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_provoice.set_channel_map([])
        self.pfb_channelizer_provoice.declare_sample_delay(0)
        self.pfb_channelizer_provoice.set_max_output_buffer(1024)
        self.pfb_channelizer_nxdn48 = pfb.channelizer_ccf(
            32,
            firdes.low_pass(32.0, samp_rate, (samp_rate/32.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_nxdn48.set_channel_map([])
        self.pfb_channelizer_nxdn48.declare_sample_delay(0)
        self.pfb_channelizer_nxdn48.set_max_output_buffer(1024)
        self.pfb_channelizer_dstar = pfb.channelizer_ccf(
            16,
            firdes.low_pass(16.0, samp_rate, (samp_rate/16.0)/2.0, 1000),
            1.0,
            100)
        self.pfb_channelizer_dstar.set_channel_map([])
        self.pfb_channelizer_dstar.declare_sample_delay(0)
        self.pfb_channelizer_dstar.set_max_output_buffer(1024)
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
        self.network_tcp_source_x2tdma = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7007,server=False)
        self.network_tcp_source_x2tdma.set_max_output_buffer(1024)
        self.network_tcp_source_tetra = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7004,server=False)
        self.network_tcp_source_tetra.set_max_output_buffer(1024)
        self.network_tcp_source_provoice = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7008,server=False)
        self.network_tcp_source_provoice.set_max_output_buffer(1024)
        self.network_tcp_source_p25 = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7003,server=False)
        self.network_tcp_source_p25.set_max_output_buffer(1024)
        self.network_tcp_source_nxdn48 = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7005,server=False)
        self.network_tcp_source_nxdn48.set_max_output_buffer(1024)
        self.network_tcp_source_nxdn = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7002,server=False)
        self.network_tcp_source_nxdn.set_max_output_buffer(1024)
        self.network_tcp_source_dstar = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7006,server=False)
        self.network_tcp_source_dstar.set_max_output_buffer(1024)
        self.network_tcp_source_dmr = network.tcp_source.tcp_source(itemsize=gr.sizeof_gr_complex*1,addr='127.0.0.1',port=7001,server=False)
        self.network_tcp_source_dmr.set_max_output_buffer(1024)
        self.mmse_resampler_xx_0 = filter.mmse_resampler_cc(0, float(samp_rate)/(float(decim)*float(channel_rate)))
        self.lpf_x2tdma = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_x2tdma.set_max_output_buffer(1024)
        self.lpf_provoice = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_provoice.set_max_output_buffer(1024)
        self.lpf_p25 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                9500,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_p25.set_max_output_buffer(1024)
        self.lpf_nxdn48 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                3000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn48.set_max_output_buffer(1024)
        self.lpf_nxdn = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_nxdn.set_max_output_buffer(1024)
        self.lpf_dstar = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dstar.set_max_output_buffer(1024)
        self.lpf_dmr = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1.0,
                48000,
                6250,
                2000,
                window.WIN_HAMMING,
                6.76))
        self.lpf_dmr.set_max_output_buffer(1024)
        self.iq_sum_x2tdma = blocks.add_vcc(1)
        self.iq_sum_x2tdma.set_max_output_buffer(1024)
        self.iq_sum_provoice = blocks.add_vcc(1)
        self.iq_sum_provoice.set_max_output_buffer(1024)
        self.iq_sum_p25 = blocks.add_vcc(1)
        self.iq_sum_p25.set_max_output_buffer(1024)
        self.iq_sum_nxdn48 = blocks.add_vcc(1)
        self.iq_sum_nxdn48.set_max_output_buffer(1024)
        self.iq_sum_nxdn = blocks.add_vcc(1)
        self.iq_sum_nxdn.set_max_output_buffer(1024)
        self.iq_sum_dstar = blocks.add_vcc(1)
        self.iq_sum_dstar.set_max_output_buffer(1024)
        self.iq_sum_dmr = blocks.add_vcc(1)
        self.iq_sum_dmr.set_max_output_buffer(1024)
        self._gain_demod_x2tdma_range = Range(0.05, 10.0, 0.01, 1.0, 200)
        self._gain_demod_x2tdma_win = RangeWidget(self._gain_demod_x2tdma_range, self.set_gain_demod_x2tdma, "FM Demod Gain (X2-TDMA)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_x2tdma_win)
        self._gain_demod_provoice_range = Range(0.05, 10.0, 0.01, 1.0, 200)
        self._gain_demod_provoice_win = RangeWidget(self._gain_demod_provoice_range, self.set_gain_demod_provoice, "FM Demod Gain (ProVoice)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_provoice_win)
        self._gain_demod_p25_range = Range(0.05, 10.0, 0.01, 1.0, 200)
        self._gain_demod_p25_win = RangeWidget(self._gain_demod_p25_range, self.set_gain_demod_p25, "FM Demod Gain (P25)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_p25_win)
        self._gain_demod_nxdn48_range = Range(0.05, 10.0, 0.01, 1.0, 200)
        self._gain_demod_nxdn48_win = RangeWidget(self._gain_demod_nxdn48_range, self.set_gain_demod_nxdn48, "FM Demod Gain (NXDN48)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_nxdn48_win)
        self._gain_demod_nxdn_range = Range(0.05, 14.0, 0.01, 1.0, 200)
        self._gain_demod_nxdn_win = RangeWidget(self._gain_demod_nxdn_range, self.set_gain_demod_nxdn, "FM Demod Gain (NXDN)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_nxdn_win)
        self._gain_demod_dstar_range = Range(0.05, 10.0, 0.01, 1.0, 200)
        self._gain_demod_dstar_win = RangeWidget(self._gain_demod_dstar_range, self.set_gain_demod_dstar, "FM Demod Gain (D-STAR)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_demod_dstar_win)
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
        self.dsd_x2tdma = dsd.dsd_block_ff(dsd.dsd_FRAME_X2_TDMA, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_x2tdma.set_max_output_buffer(1024)
        self.dsd_provoice = dsd.dsd_block_ff(dsd.dsd_FRAME_PROVOICE, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_provoice.set_max_output_buffer(1024)
        self.dsd_p25 = dsd.dsd_block_ff(dsd.dsd_FRAME_P25_PHASE_1, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_p25.set_max_output_buffer(1024)
        self.dsd_nxdn48 = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN48_IDAS, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn48.set_max_output_buffer(1024)
        self.dsd_nxdn = dsd.dsd_block_ff(dsd.dsd_FRAME_NXDN96, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_nxdn.set_max_output_buffer(1024)
        self.dsd_dstar = dsd.dsd_block_ff(dsd.dsd_FRAME_DSTAR, dsd.dsd_MOD_GFSK, 3, True, 0)
        self.dsd_dstar.set_max_output_buffer(1024)
        self.dsd_dmr = dsd.dsd_block_ff(dsd.dsd_FRAME_DMR_MOTOTRBO, dsd.dsd_MOD_C4FM, 3, True, 0)
        self.dsd_dmr.set_max_output_buffer(1024)
        self.digital_pfb_clock_sync_xxx_0 = digital.pfb_clock_sync_ccf(sps, 0.06283185307179586, rrc_taps, nfilts, nfilts/2, 1.5, sps)
        self.digital_map_bb_0 = digital.map_bb(constel.pre_diff_code())
        self.digital_linear_equalizer_0 = digital.linear_equalizer(15, sps, variable_adaptive_algorithm_0, True, [ ], 'corr_est')
        self.digital_fll_band_edge_cc_0 = digital.fll_band_edge_cc(sps, 0.35, 45, 0.03141592653589793)
        self.digital_diff_phasor_cc_0 = digital.diff_phasor_cc()
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(constel)
        self.demod_x2tdma = analog.quadrature_demod_cf(gain_demod_x2tdma)
        self.demod_x2tdma.set_max_output_buffer(1024)
        self.demod_provoice = analog.quadrature_demod_cf(gain_demod_provoice)
        self.demod_provoice.set_max_output_buffer(1024)
        self.demod_p25 = analog.quadrature_demod_cf(gain_demod_p25)
        self.demod_p25.set_max_output_buffer(1024)
        self.demod_nxdn48 = analog.quadrature_demod_cf(gain_demod_nxdn48)
        self.demod_nxdn48.set_max_output_buffer(1024)
        self.demod_nxdn = analog.quadrature_demod_cf(gain_demod_nxdn)
        self.demod_nxdn.set_max_output_buffer(1024)
        self.demod_dstar = analog.quadrature_demod_cf(gain_demod_dstar)
        self.demod_dstar.set_max_output_buffer(1024)
        self.demod_dmr = analog.quadrature_demod_cf(gain_demod)
        self.demod_dmr.set_max_output_buffer(1024)
        self.bridge_zmq_x2tdma = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9108', 100, False, -1, '')
        self.bridge_zmq_tetra_events = zeromq.pub_msg_sink('tcp://127.0.0.1:9105', 100, True)
        self.bridge_zmq_tetra = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9104', 100, False, -1, '')
        self.bridge_zmq_provoice = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9109', 100, False, -1, '')
        self.bridge_zmq_p25 = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9103', 100, False, -1, '')
        self.bridge_zmq_nxdn48 = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9106', 100, False, -1, '')
        self.bridge_zmq_nxdn = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9102', 100, False, -1, '')
        self.bridge_zmq_dstar = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9107', 100, False, -1, '')
        self.bridge_zmq_dmr = zeromq.pub_sink(gr.sizeof_float, 1, 'tcp://127.0.0.1:9101', 100, False, -1, '')
        self.blocks_unpack_k_bits_bb_0 = blocks.unpack_k_bits_bb(constel.bits_per_symbol())
        self.blocks_message_debug_0 = blocks.message_debug(True)
        self.audio_sink_x2tdma = audio.sink(48000, '', False)
        self.audio_sink_tn4 = audio.sink(8000, '', True)
        self.audio_sink_tn3 = audio.sink(8000, '', True)
        self.audio_sink_tn2 = audio.sink(8000, '', True)
        self.audio_sink_tn1 = audio.sink(8000, '', True)
        self.audio_sink_tetra_combined = audio.sink(8000, '', True)
        self.audio_sink_provoice = audio.sink(48000, '', False)
        self.audio_sink_p25 = audio.sink(48000, '', False)
        self.audio_sink_nxdn48 = audio.sink(48000, '', False)
        self.audio_sink_nxdn = audio.sink(48000, '', False)
        self.audio_sink_dstar = audio.sink(48000, '', False)
        self.audio_sink_dmr = audio.sink(48000, '', False)
        self.audio_mix_tetra = blocks.add_vff(1)
        self.audio_mix_tetra.set_max_output_buffer(1024)
        self.aresamp_x2tdma = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_x2tdma.set_max_output_buffer(1024)
        self.aresamp_provoice = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_provoice.set_max_output_buffer(1024)
        self.aresamp_p25 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_p25.set_max_output_buffer(1024)
        self.aresamp_nxdn48 = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn48.set_max_output_buffer(1024)
        self.aresamp_nxdn = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_nxdn.set_max_output_buffer(1024)
        self.aresamp_dstar = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dstar.set_max_output_buffer(1024)
        self.aresamp_dmr = filter.rational_resampler_fff(
                interpolation=6,
                decimation=1,
                taps=[],
                fractional_bw=0.4)
        self.aresamp_dmr.set_max_output_buffer(1024)
        self.analog_feedforward_agc_cc_0 = analog.feedforward_agc_cc(8, 1)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.tetra_decoder_block_0, 'call_log'), (self.blocks_message_debug_0, 'print'))
        self.msg_connect((self.tetra_decoder_block_0, 'call_log'), (self.bridge_zmq_tetra_events, 'in'))
        self.connect((self.analog_feedforward_agc_cc_0, 0), (self.digital_fll_band_edge_cc_0, 0))
        self.connect((self.aresamp_dmr, 0), (self.vol_dmr, 0))
        self.connect((self.aresamp_dstar, 0), (self.vol_dstar, 0))
        self.connect((self.aresamp_nxdn, 0), (self.vol_nxdn, 0))
        self.connect((self.aresamp_nxdn48, 0), (self.vol_nxdn48, 0))
        self.connect((self.aresamp_p25, 0), (self.vol_p25, 0))
        self.connect((self.aresamp_provoice, 0), (self.vol_provoice, 0))
        self.connect((self.aresamp_x2tdma, 0), (self.vol_x2tdma, 0))
        self.connect((self.audio_mix_tetra, 0), (self.audio_sink_tetra_combined, 0))
        self.connect((self.audio_mix_tetra, 0), (self.bridge_zmq_tetra, 0))
        self.connect((self.audio_mix_tetra, 0), (self.qtgui_time_sink_tetra, 0))
        self.connect((self.blocks_unpack_k_bits_bb_0, 0), (self.tetra_decoder_block_0, 0))
        self.connect((self.demod_dmr, 0), (self.dsd_dmr, 0))
        self.connect((self.demod_dstar, 0), (self.dsd_dstar, 0))
        self.connect((self.demod_nxdn, 0), (self.dsd_nxdn, 0))
        self.connect((self.demod_nxdn48, 0), (self.dsd_nxdn48, 0))
        self.connect((self.demod_p25, 0), (self.dsd_p25, 0))
        self.connect((self.demod_provoice, 0), (self.dsd_provoice, 0))
        self.connect((self.demod_x2tdma, 0), (self.dsd_x2tdma, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_map_bb_0, 0))
        self.connect((self.digital_diff_phasor_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_diff_phasor_cc_0, 0), (self.qtgui_const_sink_x_0_0, 0))
        self.connect((self.digital_fll_band_edge_cc_0, 0), (self.digital_pfb_clock_sync_xxx_0, 0))
        self.connect((self.digital_linear_equalizer_0, 0), (self.digital_diff_phasor_cc_0, 0))
        self.connect((self.digital_map_bb_0, 0), (self.blocks_unpack_k_bits_bb_0, 0))
        self.connect((self.digital_pfb_clock_sync_xxx_0, 0), (self.digital_linear_equalizer_0, 0))
        self.connect((self.dsd_dmr, 0), (self.aresamp_dmr, 0))
        self.connect((self.dsd_dstar, 0), (self.aresamp_dstar, 0))
        self.connect((self.dsd_nxdn, 0), (self.aresamp_nxdn, 0))
        self.connect((self.dsd_nxdn48, 0), (self.aresamp_nxdn48, 0))
        self.connect((self.dsd_p25, 0), (self.aresamp_p25, 0))
        self.connect((self.dsd_provoice, 0), (self.aresamp_provoice, 0))
        self.connect((self.dsd_x2tdma, 0), (self.aresamp_x2tdma, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.mmse_resampler_xx_0, 0))
        self.connect((self.iq_sum_dmr, 0), (self.resamp_iq_dmr, 0))
        self.connect((self.iq_sum_dstar, 0), (self.resamp_iq_dstar, 0))
        self.connect((self.iq_sum_nxdn, 0), (self.resamp_iq_nxdn, 0))
        self.connect((self.iq_sum_nxdn48, 0), (self.resamp_iq_nxdn48, 0))
        self.connect((self.iq_sum_p25, 0), (self.resamp_iq_p25, 0))
        self.connect((self.iq_sum_provoice, 0), (self.resamp_iq_provoice, 0))
        self.connect((self.iq_sum_x2tdma, 0), (self.resamp_iq_x2tdma, 0))
        self.connect((self.lpf_dmr, 0), (self.squelch_dmr, 0))
        self.connect((self.lpf_dstar, 0), (self.squelch_dstar, 0))
        self.connect((self.lpf_nxdn, 0), (self.squelch_nxdn, 0))
        self.connect((self.lpf_nxdn48, 0), (self.squelch_nxdn48, 0))
        self.connect((self.lpf_p25, 0), (self.squelch_p25, 0))
        self.connect((self.lpf_provoice, 0), (self.squelch_provoice, 0))
        self.connect((self.lpf_x2tdma, 0), (self.squelch_x2tdma, 0))
        self.connect((self.mmse_resampler_xx_0, 0), (self.analog_feedforward_agc_cc_0, 0))
        self.connect((self.mmse_resampler_xx_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.network_tcp_source_dmr, 0), (self.pfb_channelizer_ccf_0, 0))
        self.connect((self.network_tcp_source_dmr, 0), (self.qtgui_freq_sink_combined, 0))
        self.connect((self.network_tcp_source_dstar, 0), (self.pfb_channelizer_dstar, 0))
        self.connect((self.network_tcp_source_dstar, 0), (self.qtgui_freq_sink_combined, 5))
        self.connect((self.network_tcp_source_nxdn, 0), (self.pfb_channelizer_ccf_0_1, 0))
        self.connect((self.network_tcp_source_nxdn, 0), (self.qtgui_freq_sink_combined, 1))
        self.connect((self.network_tcp_source_nxdn48, 0), (self.pfb_channelizer_nxdn48, 0))
        self.connect((self.network_tcp_source_nxdn48, 0), (self.qtgui_freq_sink_combined, 4))
        self.connect((self.network_tcp_source_p25, 0), (self.pfb_channelizer_ccf_0_0, 0))
        self.connect((self.network_tcp_source_p25, 0), (self.qtgui_freq_sink_combined, 2))
        self.connect((self.network_tcp_source_provoice, 0), (self.pfb_channelizer_provoice, 0))
        self.connect((self.network_tcp_source_provoice, 0), (self.qtgui_freq_sink_combined, 7))
        self.connect((self.network_tcp_source_tetra, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.network_tcp_source_tetra, 0), (self.qtgui_freq_sink_combined, 3))
        self.connect((self.network_tcp_source_x2tdma, 0), (self.pfb_channelizer_x2tdma, 0))
        self.connect((self.network_tcp_source_x2tdma, 0), (self.qtgui_freq_sink_combined, 6))
        self.connect((self.pfb_channelizer_ccf_0, 3), (self.iq_sum_dmr, 3))
        self.connect((self.pfb_channelizer_ccf_0, 11), (self.iq_sum_dmr, 11))
        self.connect((self.pfb_channelizer_ccf_0, 5), (self.iq_sum_dmr, 5))
        self.connect((self.pfb_channelizer_ccf_0, 0), (self.iq_sum_dmr, 0))
        self.connect((self.pfb_channelizer_ccf_0, 1), (self.iq_sum_dmr, 1))
        self.connect((self.pfb_channelizer_ccf_0, 6), (self.iq_sum_dmr, 6))
        self.connect((self.pfb_channelizer_ccf_0, 4), (self.iq_sum_dmr, 4))
        self.connect((self.pfb_channelizer_ccf_0, 13), (self.iq_sum_dmr, 13))
        self.connect((self.pfb_channelizer_ccf_0, 12), (self.iq_sum_dmr, 12))
        self.connect((self.pfb_channelizer_ccf_0, 9), (self.iq_sum_dmr, 9))
        self.connect((self.pfb_channelizer_ccf_0, 7), (self.iq_sum_dmr, 7))
        self.connect((self.pfb_channelizer_ccf_0, 14), (self.iq_sum_dmr, 14))
        self.connect((self.pfb_channelizer_ccf_0, 15), (self.iq_sum_dmr, 15))
        self.connect((self.pfb_channelizer_ccf_0, 10), (self.iq_sum_dmr, 10))
        self.connect((self.pfb_channelizer_ccf_0, 2), (self.iq_sum_dmr, 2))
        self.connect((self.pfb_channelizer_ccf_0, 8), (self.iq_sum_dmr, 8))
        self.connect((self.pfb_channelizer_ccf_0_0, 4), (self.iq_sum_p25, 4))
        self.connect((self.pfb_channelizer_ccf_0_0, 9), (self.iq_sum_p25, 9))
        self.connect((self.pfb_channelizer_ccf_0_0, 2), (self.iq_sum_p25, 2))
        self.connect((self.pfb_channelizer_ccf_0_0, 8), (self.iq_sum_p25, 8))
        self.connect((self.pfb_channelizer_ccf_0_0, 0), (self.iq_sum_p25, 0))
        self.connect((self.pfb_channelizer_ccf_0_0, 7), (self.iq_sum_p25, 7))
        self.connect((self.pfb_channelizer_ccf_0_0, 5), (self.iq_sum_p25, 5))
        self.connect((self.pfb_channelizer_ccf_0_0, 3), (self.iq_sum_p25, 3))
        self.connect((self.pfb_channelizer_ccf_0_0, 6), (self.iq_sum_p25, 6))
        self.connect((self.pfb_channelizer_ccf_0_0, 1), (self.iq_sum_p25, 1))
        self.connect((self.pfb_channelizer_ccf_0_1, 10), (self.iq_sum_nxdn, 10))
        self.connect((self.pfb_channelizer_ccf_0_1, 6), (self.iq_sum_nxdn, 6))
        self.connect((self.pfb_channelizer_ccf_0_1, 14), (self.iq_sum_nxdn, 14))
        self.connect((self.pfb_channelizer_ccf_0_1, 9), (self.iq_sum_nxdn, 9))
        self.connect((self.pfb_channelizer_ccf_0_1, 1), (self.iq_sum_nxdn, 1))
        self.connect((self.pfb_channelizer_ccf_0_1, 15), (self.iq_sum_nxdn, 15))
        self.connect((self.pfb_channelizer_ccf_0_1, 3), (self.iq_sum_nxdn, 3))
        self.connect((self.pfb_channelizer_ccf_0_1, 8), (self.iq_sum_nxdn, 8))
        self.connect((self.pfb_channelizer_ccf_0_1, 11), (self.iq_sum_nxdn, 11))
        self.connect((self.pfb_channelizer_ccf_0_1, 13), (self.iq_sum_nxdn, 13))
        self.connect((self.pfb_channelizer_ccf_0_1, 4), (self.iq_sum_nxdn, 4))
        self.connect((self.pfb_channelizer_ccf_0_1, 0), (self.iq_sum_nxdn, 0))
        self.connect((self.pfb_channelizer_ccf_0_1, 12), (self.iq_sum_nxdn, 12))
        self.connect((self.pfb_channelizer_ccf_0_1, 7), (self.iq_sum_nxdn, 7))
        self.connect((self.pfb_channelizer_ccf_0_1, 2), (self.iq_sum_nxdn, 2))
        self.connect((self.pfb_channelizer_ccf_0_1, 5), (self.iq_sum_nxdn, 5))
        self.connect((self.pfb_channelizer_dstar, 8), (self.iq_sum_dstar, 8))
        self.connect((self.pfb_channelizer_dstar, 12), (self.iq_sum_dstar, 12))
        self.connect((self.pfb_channelizer_dstar, 1), (self.iq_sum_dstar, 1))
        self.connect((self.pfb_channelizer_dstar, 15), (self.iq_sum_dstar, 15))
        self.connect((self.pfb_channelizer_dstar, 3), (self.iq_sum_dstar, 3))
        self.connect((self.pfb_channelizer_dstar, 4), (self.iq_sum_dstar, 4))
        self.connect((self.pfb_channelizer_dstar, 14), (self.iq_sum_dstar, 14))
        self.connect((self.pfb_channelizer_dstar, 10), (self.iq_sum_dstar, 10))
        self.connect((self.pfb_channelizer_dstar, 7), (self.iq_sum_dstar, 7))
        self.connect((self.pfb_channelizer_dstar, 9), (self.iq_sum_dstar, 9))
        self.connect((self.pfb_channelizer_dstar, 6), (self.iq_sum_dstar, 6))
        self.connect((self.pfb_channelizer_dstar, 0), (self.iq_sum_dstar, 0))
        self.connect((self.pfb_channelizer_dstar, 5), (self.iq_sum_dstar, 5))
        self.connect((self.pfb_channelizer_dstar, 13), (self.iq_sum_dstar, 13))
        self.connect((self.pfb_channelizer_dstar, 2), (self.iq_sum_dstar, 2))
        self.connect((self.pfb_channelizer_dstar, 11), (self.iq_sum_dstar, 11))
        self.connect((self.pfb_channelizer_nxdn48, 29), (self.iq_sum_nxdn48, 29))
        self.connect((self.pfb_channelizer_nxdn48, 31), (self.iq_sum_nxdn48, 31))
        self.connect((self.pfb_channelizer_nxdn48, 9), (self.iq_sum_nxdn48, 9))
        self.connect((self.pfb_channelizer_nxdn48, 4), (self.iq_sum_nxdn48, 4))
        self.connect((self.pfb_channelizer_nxdn48, 1), (self.iq_sum_nxdn48, 1))
        self.connect((self.pfb_channelizer_nxdn48, 8), (self.iq_sum_nxdn48, 8))
        self.connect((self.pfb_channelizer_nxdn48, 11), (self.iq_sum_nxdn48, 11))
        self.connect((self.pfb_channelizer_nxdn48, 10), (self.iq_sum_nxdn48, 10))
        self.connect((self.pfb_channelizer_nxdn48, 18), (self.iq_sum_nxdn48, 18))
        self.connect((self.pfb_channelizer_nxdn48, 12), (self.iq_sum_nxdn48, 12))
        self.connect((self.pfb_channelizer_nxdn48, 22), (self.iq_sum_nxdn48, 22))
        self.connect((self.pfb_channelizer_nxdn48, 7), (self.iq_sum_nxdn48, 7))
        self.connect((self.pfb_channelizer_nxdn48, 15), (self.iq_sum_nxdn48, 15))
        self.connect((self.pfb_channelizer_nxdn48, 28), (self.iq_sum_nxdn48, 28))
        self.connect((self.pfb_channelizer_nxdn48, 21), (self.iq_sum_nxdn48, 21))
        self.connect((self.pfb_channelizer_nxdn48, 16), (self.iq_sum_nxdn48, 16))
        self.connect((self.pfb_channelizer_nxdn48, 26), (self.iq_sum_nxdn48, 26))
        self.connect((self.pfb_channelizer_nxdn48, 0), (self.iq_sum_nxdn48, 0))
        self.connect((self.pfb_channelizer_nxdn48, 14), (self.iq_sum_nxdn48, 14))
        self.connect((self.pfb_channelizer_nxdn48, 3), (self.iq_sum_nxdn48, 3))
        self.connect((self.pfb_channelizer_nxdn48, 30), (self.iq_sum_nxdn48, 30))
        self.connect((self.pfb_channelizer_nxdn48, 6), (self.iq_sum_nxdn48, 6))
        self.connect((self.pfb_channelizer_nxdn48, 17), (self.iq_sum_nxdn48, 17))
        self.connect((self.pfb_channelizer_nxdn48, 24), (self.iq_sum_nxdn48, 24))
        self.connect((self.pfb_channelizer_nxdn48, 13), (self.iq_sum_nxdn48, 13))
        self.connect((self.pfb_channelizer_nxdn48, 2), (self.iq_sum_nxdn48, 2))
        self.connect((self.pfb_channelizer_nxdn48, 25), (self.iq_sum_nxdn48, 25))
        self.connect((self.pfb_channelizer_nxdn48, 19), (self.iq_sum_nxdn48, 19))
        self.connect((self.pfb_channelizer_nxdn48, 20), (self.iq_sum_nxdn48, 20))
        self.connect((self.pfb_channelizer_nxdn48, 27), (self.iq_sum_nxdn48, 27))
        self.connect((self.pfb_channelizer_nxdn48, 23), (self.iq_sum_nxdn48, 23))
        self.connect((self.pfb_channelizer_nxdn48, 5), (self.iq_sum_nxdn48, 5))
        self.connect((self.pfb_channelizer_provoice, 4), (self.iq_sum_provoice, 4))
        self.connect((self.pfb_channelizer_provoice, 0), (self.iq_sum_provoice, 0))
        self.connect((self.pfb_channelizer_provoice, 1), (self.iq_sum_provoice, 1))
        self.connect((self.pfb_channelizer_provoice, 5), (self.iq_sum_provoice, 5))
        self.connect((self.pfb_channelizer_provoice, 7), (self.iq_sum_provoice, 7))
        self.connect((self.pfb_channelizer_provoice, 3), (self.iq_sum_provoice, 3))
        self.connect((self.pfb_channelizer_provoice, 6), (self.iq_sum_provoice, 6))
        self.connect((self.pfb_channelizer_provoice, 2), (self.iq_sum_provoice, 2))
        self.connect((self.pfb_channelizer_x2tdma, 1), (self.iq_sum_x2tdma, 1))
        self.connect((self.pfb_channelizer_x2tdma, 10), (self.iq_sum_x2tdma, 10))
        self.connect((self.pfb_channelizer_x2tdma, 6), (self.iq_sum_x2tdma, 6))
        self.connect((self.pfb_channelizer_x2tdma, 8), (self.iq_sum_x2tdma, 8))
        self.connect((self.pfb_channelizer_x2tdma, 9), (self.iq_sum_x2tdma, 9))
        self.connect((self.pfb_channelizer_x2tdma, 15), (self.iq_sum_x2tdma, 15))
        self.connect((self.pfb_channelizer_x2tdma, 12), (self.iq_sum_x2tdma, 12))
        self.connect((self.pfb_channelizer_x2tdma, 3), (self.iq_sum_x2tdma, 3))
        self.connect((self.pfb_channelizer_x2tdma, 7), (self.iq_sum_x2tdma, 7))
        self.connect((self.pfb_channelizer_x2tdma, 14), (self.iq_sum_x2tdma, 14))
        self.connect((self.pfb_channelizer_x2tdma, 2), (self.iq_sum_x2tdma, 2))
        self.connect((self.pfb_channelizer_x2tdma, 13), (self.iq_sum_x2tdma, 13))
        self.connect((self.pfb_channelizer_x2tdma, 4), (self.iq_sum_x2tdma, 4))
        self.connect((self.pfb_channelizer_x2tdma, 11), (self.iq_sum_x2tdma, 11))
        self.connect((self.pfb_channelizer_x2tdma, 0), (self.iq_sum_x2tdma, 0))
        self.connect((self.pfb_channelizer_x2tdma, 5), (self.iq_sum_x2tdma, 5))
        self.connect((self.resamp_iq_dmr, 0), (self.lpf_dmr, 0))
        self.connect((self.resamp_iq_dstar, 0), (self.lpf_dstar, 0))
        self.connect((self.resamp_iq_nxdn, 0), (self.lpf_nxdn, 0))
        self.connect((self.resamp_iq_nxdn48, 0), (self.lpf_nxdn48, 0))
        self.connect((self.resamp_iq_p25, 0), (self.lpf_p25, 0))
        self.connect((self.resamp_iq_provoice, 0), (self.lpf_provoice, 0))
        self.connect((self.resamp_iq_x2tdma, 0), (self.lpf_x2tdma, 0))
        self.connect((self.squelch_dmr, 0), (self.demod_dmr, 0))
        self.connect((self.squelch_dstar, 0), (self.demod_dstar, 0))
        self.connect((self.squelch_nxdn, 0), (self.demod_nxdn, 0))
        self.connect((self.squelch_nxdn48, 0), (self.demod_nxdn48, 0))
        self.connect((self.squelch_p25, 0), (self.demod_p25, 0))
        self.connect((self.squelch_provoice, 0), (self.demod_provoice, 0))
        self.connect((self.squelch_x2tdma, 0), (self.demod_x2tdma, 0))
        self.connect((self.tetra_decoder_block_0, 3), (self.audio_mix_tetra, 3))
        self.connect((self.tetra_decoder_block_0, 0), (self.audio_mix_tetra, 0))
        self.connect((self.tetra_decoder_block_0, 2), (self.audio_mix_tetra, 2))
        self.connect((self.tetra_decoder_block_0, 1), (self.audio_mix_tetra, 1))
        self.connect((self.tetra_decoder_block_0, 0), (self.audio_sink_tn1, 0))
        self.connect((self.tetra_decoder_block_0, 1), (self.audio_sink_tn2, 0))
        self.connect((self.tetra_decoder_block_0, 2), (self.audio_sink_tn3, 0))
        self.connect((self.tetra_decoder_block_0, 3), (self.audio_sink_tn4, 0))
        self.connect((self.vol_dmr, 0), (self.audio_sink_dmr, 0))
        self.connect((self.vol_dmr, 0), (self.bridge_zmq_dmr, 0))
        self.connect((self.vol_dmr, 0), (self.qtgui_time_sink_dnp, 0))
        self.connect((self.vol_dstar, 0), (self.audio_sink_dstar, 0))
        self.connect((self.vol_dstar, 0), (self.bridge_zmq_dstar, 0))
        self.connect((self.vol_dstar, 0), (self.qtgui_time_sink_dnp, 4))
        self.connect((self.vol_nxdn, 0), (self.audio_sink_nxdn, 0))
        self.connect((self.vol_nxdn, 0), (self.bridge_zmq_nxdn, 0))
        self.connect((self.vol_nxdn, 0), (self.qtgui_time_sink_dnp, 1))
        self.connect((self.vol_nxdn48, 0), (self.audio_sink_nxdn48, 0))
        self.connect((self.vol_nxdn48, 0), (self.bridge_zmq_nxdn48, 0))
        self.connect((self.vol_nxdn48, 0), (self.qtgui_time_sink_dnp, 3))
        self.connect((self.vol_p25, 0), (self.audio_sink_p25, 0))
        self.connect((self.vol_p25, 0), (self.bridge_zmq_p25, 0))
        self.connect((self.vol_p25, 0), (self.qtgui_time_sink_dnp, 2))
        self.connect((self.vol_provoice, 0), (self.audio_sink_provoice, 0))
        self.connect((self.vol_provoice, 0), (self.bridge_zmq_provoice, 0))
        self.connect((self.vol_provoice, 0), (self.qtgui_time_sink_dnp, 6))
        self.connect((self.vol_x2tdma, 0), (self.audio_sink_x2tdma, 0))
        self.connect((self.vol_x2tdma, 0), (self.bridge_zmq_x2tdma, 0))
        self.connect((self.vol_x2tdma, 0), (self.qtgui_time_sink_dnp, 5))


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

    def get_volume_x2tdma(self):
        return self.volume_x2tdma

    def set_volume_x2tdma(self, volume_x2tdma):
        self.volume_x2tdma = volume_x2tdma
        self.vol_x2tdma.set_k(self.volume_x2tdma)

    def get_volume_provoice(self):
        return self.volume_provoice

    def set_volume_provoice(self, volume_provoice):
        self.volume_provoice = volume_provoice
        self.vol_provoice.set_k(self.volume_provoice)

    def get_volume_p25(self):
        return self.volume_p25

    def set_volume_p25(self, volume_p25):
        self.volume_p25 = volume_p25
        self.vol_p25.set_k(self.volume_p25)

    def get_volume_nxdn48(self):
        return self.volume_nxdn48

    def set_volume_nxdn48(self, volume_nxdn48):
        self.volume_nxdn48 = volume_nxdn48
        self.vol_nxdn48.set_k(self.volume_nxdn48)

    def get_volume_nxdn(self):
        return self.volume_nxdn

    def set_volume_nxdn(self, volume_nxdn):
        self.volume_nxdn = volume_nxdn
        self.vol_nxdn.set_k(self.volume_nxdn)

    def get_volume_dstar(self):
        return self.volume_dstar

    def set_volume_dstar(self, volume_dstar):
        self.volume_dstar = volume_dstar
        self.vol_dstar.set_k(self.volume_dstar)

    def get_volume_dmr(self):
        return self.volume_dmr

    def set_volume_dmr(self, volume_dmr):
        self.volume_dmr = volume_dmr
        self.vol_dmr.set_k(self.volume_dmr)

    def get_variable_adaptive_algorithm_0(self):
        return self.variable_adaptive_algorithm_0

    def set_variable_adaptive_algorithm_0(self, variable_adaptive_algorithm_0):
        self.variable_adaptive_algorithm_0 = variable_adaptive_algorithm_0

    def get_squelch_thresh_x2tdma(self):
        return self.squelch_thresh_x2tdma

    def set_squelch_thresh_x2tdma(self, squelch_thresh_x2tdma):
        self.squelch_thresh_x2tdma = squelch_thresh_x2tdma
        self.squelch_x2tdma.set_threshold(self.squelch_thresh_x2tdma)

    def get_squelch_thresh_provoice(self):
        return self.squelch_thresh_provoice

    def set_squelch_thresh_provoice(self, squelch_thresh_provoice):
        self.squelch_thresh_provoice = squelch_thresh_provoice
        self.squelch_provoice.set_threshold(self.squelch_thresh_provoice)

    def get_squelch_thresh_p25(self):
        return self.squelch_thresh_p25

    def set_squelch_thresh_p25(self, squelch_thresh_p25):
        self.squelch_thresh_p25 = squelch_thresh_p25
        self.squelch_p25.set_threshold(self.squelch_thresh_p25)

    def get_squelch_thresh_nxdn48(self):
        return self.squelch_thresh_nxdn48

    def set_squelch_thresh_nxdn48(self, squelch_thresh_nxdn48):
        self.squelch_thresh_nxdn48 = squelch_thresh_nxdn48
        self.squelch_nxdn48.set_threshold(self.squelch_thresh_nxdn48)

    def get_squelch_thresh_nxdn(self):
        return self.squelch_thresh_nxdn

    def set_squelch_thresh_nxdn(self, squelch_thresh_nxdn):
        self.squelch_thresh_nxdn = squelch_thresh_nxdn
        self.squelch_nxdn.set_threshold(self.squelch_thresh_nxdn)

    def get_squelch_thresh_dstar(self):
        return self.squelch_thresh_dstar

    def set_squelch_thresh_dstar(self, squelch_thresh_dstar):
        self.squelch_thresh_dstar = squelch_thresh_dstar
        self.squelch_dstar.set_threshold(self.squelch_thresh_dstar)

    def get_squelch_thresh_dmr(self):
        return self.squelch_thresh_dmr

    def set_squelch_thresh_dmr(self, squelch_thresh_dmr):
        self.squelch_thresh_dmr = squelch_thresh_dmr
        self.squelch_dmr.set_threshold(self.squelch_thresh_dmr)

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
        self.qtgui_time_sink_tetra.set_samp_rate(self.samp_rate)
        self.pfb_channelizer_nxdn48.set_taps(firdes.low_pass(32.0, self.samp_rate, (self.samp_rate/32.0)/2.0, 1000))
        self.pfb_channelizer_dstar.set_taps(firdes.low_pass(16.0, self.samp_rate, (self.samp_rate/16.0)/2.0, 1000))
        self.pfb_channelizer_x2tdma.set_taps(firdes.low_pass(16.0, self.samp_rate, (self.samp_rate/16.0)/2.0, 1000))
        self.pfb_channelizer_provoice.set_taps(firdes.low_pass(8.0, self.samp_rate, (self.samp_rate/8.0)/2.0, 1000))

    def get_rrc_taps(self):
        return self.rrc_taps

    def set_rrc_taps(self, rrc_taps):
        self.rrc_taps = rrc_taps
        self.digital_pfb_clock_sync_xxx_0.update_taps(self.rrc_taps)

    def get_ppm_corr(self):
        return self.ppm_corr

    def set_ppm_corr(self, ppm_corr):
        self.ppm_corr = ppm_corr

    def get_gain_demod_x2tdma(self):
        return self.gain_demod_x2tdma

    def set_gain_demod_x2tdma(self, gain_demod_x2tdma):
        self.gain_demod_x2tdma = gain_demod_x2tdma
        self.demod_x2tdma.set_gain(self.gain_demod_x2tdma)

    def get_gain_demod_provoice(self):
        return self.gain_demod_provoice

    def set_gain_demod_provoice(self, gain_demod_provoice):
        self.gain_demod_provoice = gain_demod_provoice
        self.demod_provoice.set_gain(self.gain_demod_provoice)

    def get_gain_demod_p25(self):
        return self.gain_demod_p25

    def set_gain_demod_p25(self, gain_demod_p25):
        self.gain_demod_p25 = gain_demod_p25
        self.demod_p25.set_gain(self.gain_demod_p25)

    def get_gain_demod_nxdn48(self):
        return self.gain_demod_nxdn48

    def set_gain_demod_nxdn48(self, gain_demod_nxdn48):
        self.gain_demod_nxdn48 = gain_demod_nxdn48
        self.demod_nxdn48.set_gain(self.gain_demod_nxdn48)

    def get_gain_demod_nxdn(self):
        return self.gain_demod_nxdn

    def set_gain_demod_nxdn(self, gain_demod_nxdn):
        self.gain_demod_nxdn = gain_demod_nxdn
        self.demod_nxdn.set_gain(self.gain_demod_nxdn)

    def get_gain_demod_dstar(self):
        return self.gain_demod_dstar

    def set_gain_demod_dstar(self, gain_demod_dstar):
        self.gain_demod_dstar = gain_demod_dstar
        self.demod_dstar.set_gain(self.gain_demod_dstar)

    def get_gain_demod(self):
        return self.gain_demod

    def set_gain_demod(self, gain_demod):
        self.gain_demod = gain_demod
        self.demod_dmr.set_gain(self.gain_demod)

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
