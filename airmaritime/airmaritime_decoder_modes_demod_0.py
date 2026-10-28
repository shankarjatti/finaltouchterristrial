"""Mode-S / ADS-B demodulator: preamble test against the measured noise floor, half-bit
integration, timing search, CRC-24 (DF17/18). The code lives in modes_demod.py next to this
flowgraph; it replaces gr-adsb's framer + demod (32 of 173 frames passed CRC on a real
recording, 155 with this block)."""
import os
import sys
try:
    from modes_demod import modes_demod
except ImportError:
    sys.path.insert(0, '/home/shankar/Downloads/tutorials/delhi_testing/coupled/secuecom/COUPLING/version1/airmaritime')
    from modes_demod import modes_demod


class blk(modes_demod):
    """Mode-S demod (modes_demod.py)"""
    def __init__(self, fs=6e6, snr_db=6.0):
        modes_demod.__init__(self, fs=fs, snr_db=snr_db)
