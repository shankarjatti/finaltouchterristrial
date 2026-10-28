#!/usr/bin/env python3
"""ADS-B airborne position (CPR) decoding with validation, from raw CRC-valid DF17/18 frames.

Why not gr-adsb's lat/lon: it pairs even/odd frames by whole-second wall-clock time with a 30 s
window, and its validity check (`(lat - prev) < 0.1` twice, no abs, no longitude) lets wrong
positions through. On the real London recording it placed aircraft in the Norwegian Sea, the
Atlantic, Germany and Italy.

Rules here (ICAO Doc 9871 / DO-260B, as dump1090 and pyModeS apply them):
  * global decode only from an even + odd pair received within 10 s of each other (message
    time, not wall clock) whose latitudes fall in the same NL zone;
  * a new aircraft's position is only CONFIRMED when two independent global decodes of the same
    parity (both anchored on an even frame, or both on an odd one) agree within what the
    aircraft could have flown between them;
  * after that, each frame is decoded locally against the last confirmed position and is
    accepted only if the move is physically possible (<= MAX_SPEED_KT plus a margin);
  * REJECT_LIMIT implausible frames in a row drop the reference, and the aircraft has to be
    confirmed again from scratch. Nothing is ever extrapolated or invented.
"""
import math

PAIR_WINDOW_S = 10.0       # max even/odd separation for a global decode
CONFIRM_WINDOW_S = 60.0    # two global decodes must be this close in time to confirm
REF_MAX_AGE_S = 60.0       # local decode only against a reference this recent
MAX_SPEED_KT = 1000.0      # faster than any airliner's ground speed
MARGIN_KM = 3.0
REJECT_LIMIT = 3


def cpr_nl(lat):
    """Number of longitude zones at this latitude (1..59)."""
    if lat == 0:
        return 59
    if abs(lat) == 87:
        return 2
    if abs(lat) > 87:
        return 1
    a = 1 - math.cos(math.pi / (2 * 15))
    b = math.cos(math.pi / 180 * abs(lat)) ** 2
    return int(math.floor(2 * math.pi / math.acos(1 - a / b)))


def dist_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def reachable_km(dt_s):
    return MAX_SPEED_KT * 1.852 / 3600.0 * abs(dt_s) + MARGIN_KM


def global_decode(even, odd, newest):
    """even/odd: (lat_cpr, lon_cpr) as 17-bit integers. newest: 0 even, 1 odd. -> (lat, lon) or None."""
    le, lo = even[0] / 131072.0, odd[0] / 131072.0
    ne, no = even[1] / 131072.0, odd[1] / 131072.0
    j = math.floor(59 * le - 60 * lo + 0.5)
    lat_e = 360.0 / 60 * ((j % 60) + le)
    lat_o = 360.0 / 59 * ((j % 59) + lo)
    if lat_e >= 270:
        lat_e -= 360
    if lat_o >= 270:
        lat_o -= 360
    if abs(lat_e) > 90 or abs(lat_o) > 90:
        return None
    if cpr_nl(lat_e) != cpr_nl(lat_o):
        return None                      # pair straddles a zone boundary: not decodable
    lat = lat_o if newest else lat_e
    nl = cpr_nl(lat)
    ni = max(nl - newest, 1)
    m = math.floor(ne * (nl - 1) - no * nl + 0.5)
    lon = (360.0 / ni) * ((m % ni) + (no if newest else ne))
    if lon >= 180:
        lon -= 360
    return lat, lon


def local_decode(ref_lat, ref_lon, lat_cpr, lon_cpr, odd):
    """Decode one frame against a nearby reference position (unambiguous within ~180 NM)."""
    yz, xz = lat_cpr / 131072.0, lon_cpr / 131072.0
    dlat = 360.0 / (59 if odd else 60)
    j = math.floor(ref_lat / dlat) + math.floor(0.5 + (ref_lat % dlat) / dlat - yz)
    lat = dlat * (j + yz)
    ni = max(cpr_nl(lat) - (1 if odd else 0), 1)
    dlon = 360.0 / ni
    m = math.floor(ref_lon / dlon) + math.floor(0.5 + (ref_lon % dlon) / dlon - xz)
    lon = dlon * (m + xz)
    if lon >= 180:
        lon -= 360
    return lat, lon


def bits_to_int(bits, a, n):
    v = 0
    for b in bits[a:a + n]:
        v = (v << 1) | int(b)
    return v


class CprTracker:
    """Per-aircraft CPR state. feed() returns a confirmed (lat, lon) or None."""

    def __init__(self):
        self.ac = {}

    def feed(self, icao, bits, t):
        tc = bits_to_int(bits, 32, 5)
        if not (9 <= tc <= 18 or 20 <= tc <= 22):
            return None                    # not an airborne position message
        odd = bits_to_int(bits, 53, 1)
        lat_cpr = bits_to_int(bits, 54, 17)
        lon_cpr = bits_to_int(bits, 71, 17)
        s = self.ac.setdefault(icao, {'frames': [None, None], 'cand': [None, None], 'ref': None, 'rej': 0})
        s['frames'][odd] = (lat_cpr, lon_cpr, t)

        ref = s['ref']
        if ref and t - ref[2] <= REF_MAX_AGE_S:
            lat, lon = local_decode(ref[0], ref[1], lat_cpr, lon_cpr, odd)
            if dist_km(ref[0], ref[1], lat, lon) <= reachable_km(t - ref[2]):
                s['ref'] = (lat, lon, t)
                s['rej'] = 0
                return lat, lon
            s['rej'] += 1
            if s['rej'] >= REJECT_LIMIT:   # track lost: confirm again from scratch
                s['ref'] = None
                s['cand'] = [None, None]
                s['rej'] = 0
            return None
        s['ref'] = None

        ev, od = s['frames']
        if not ev or not od or abs(ev[2] - od[2]) > PAIR_WINDOW_S:
            return None
        pos = global_decode(ev[:2], od[:2], odd)
        if pos is None:
            return None
        cand = s['cand'][odd]          # compare like with like: decodes anchored on the same parity
        if (cand and t - cand[2] <= CONFIRM_WINDOW_S and t > cand[2]
                and dist_km(cand[0], cand[1], pos[0], pos[1]) <= reachable_km(t - cand[2])):
            s['ref'] = (pos[0], pos[1], t)
            s['cand'] = [None, None]
            return pos
        s['cand'][odd] = (pos[0], pos[1], t)
        return None

    def forget(self, icao):
        self.ac.pop(icao, None)
