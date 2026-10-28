#!/usr/bin/env bash
# =============================================================================
#  SecureCOM — Air & Maritime (AIS + ADS-B) : standalone launcher
#
#  A separate subsystem from the terrestrial COUPLING/version1 stack. It has its
#  OWN Module 1 (dwelling only on AIS 162.025 MHz / port 7009 and ADS-B
#  1090 MHz / port 7010, each at its own hardware sample rate), its own decoder,
#  bridge and map console. ONE B210, ONE Module 1 at a time: run this OR the
#  terrestrial run_securecom.sh, never both (they both open the radio).
#
#  Stages:
#    1. preflight     python deps, gr-adsb / gr-ais, USRP present
#    2. cleanup       kill stale air/maritime processes, free ports
#    3. build         module1 (C++/UHD) if the binary is missing or stale
#    4. hardware      securecom_module1  -> IQ on TCP 7009 (AIS) / 7010 (ADS-B)
#    5. bridge        airmaritime_bridge.py          -> ws://127.0.0.1:8887
#    6. decoder       airmaritime_decoder_live.py    (started via the bridge)
#    7. map tiles     mbtiles_server.py              -> http://127.0.0.1:8080
#    8. web server    gui/ console                   -> http://127.0.0.1:8790
#
#  Flags: --no-browser, --stop, --gain N, --dwell-ais N, --dwell-adsb N
#  Run with a clean PATH so UHD 4.10 (/usr/local) is used, e.g.:
#     env PATH=/usr/local/bin:/usr/bin:/bin ./run_airmaritime.sh
# =============================================================================
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_DIR="$HERE/gui"
M1_BIN="$HERE/module1/build/securecom_module1"
WS_PORT=8887
HTTP_PORT=8790
TILE_PORT=8080
CONSOLE_URL="http://127.0.0.1:$HTTP_PORT/airmaritime_console.html"
LOG_DIR="${TMPDIR:-/tmp}/securecom_airmaritime"
OPEN_BROWSER=1; STOP_ONLY=0
RX_GAIN=""; DWELL_AIS=""; DWELL_ADSB=""

while [ $# -gt 0 ]; do
  case "$1" in
    --no-browser)  OPEN_BROWSER=0; shift;;
    --stop)        STOP_ONLY=1; shift;;
    --gain)        RX_GAIN="${2:?}"; shift 2;;
    --dwell-ais)   DWELL_AIS="${2:?}"; shift 2;;
    --dwell-adsb)  DWELL_ADSB="${2:?}"; shift 2;;
    *) echo "unknown arg: $1"; exit 2;;
  esac
done
mkdir -p "$LOG_DIR"
if [ -t 1 ]; then B=$'\e[1m'; GRN=$'\e[32m'; RED=$'\e[31m'; YEL=$'\e[33m'; RST=$'\e[0m'; else B=""; GRN=""; RED=""; YEL=""; RST=""; fi
step(){ echo; echo "${B}[$1/8] $2${RST}"; }
ok(){   echo "   ${GRN}OK${RST}  $*"; }
warn(){ echo "   ${YEL}!${RST}   $*"; }
die(){  echo "   ${RED}FAIL${RST} $*" >&2; exit 1; }

count_ports(){ ss -ltn 2>/dev/null | grep -cE "127.0.0.1:$1 |0.0.0.0:$1 "; }
wait_for_port(){ for _ in $(seq 1 "${2:-20}"); do [ "$(count_ports "$1")" -ge 1 ] && return 0; sleep 0.5; done; return 1; }

kill_air(){
  for pat in "airmaritime_decoder_live.py" "airmaritime_bridge.py" "mbtiles_server.py" \
             "http.server $HTTP_PORT" "securecom_modul"; do
    pkill -9 -f "$pat" 2>/dev/null
  done
}

if [ "$STOP_ONLY" = 1 ]; then echo "Air & Maritime — stopping"; kill_air; sleep 1; ok "stopped"; exit 0; fi

echo "${B}SecureCOM — Air & Maritime (AIS + ADS-B)${RST}"
echo "   $HERE"; echo "   logs: $LOG_DIR"

step 1 Preflight
python3 -c "import numpy, zmq, websockets, pmt" 2>/dev/null && ok "python deps present" || die "missing python deps (numpy/pyzmq/websockets/pmt)"
python3 -c "import gnuradio.adsb" 2>/dev/null && ok "gr-adsb present" || die "gr-adsb not importable (gnuradio.adsb)"
python3 -c "import gnuradio.ais"  2>/dev/null && ok "gr-ais present"  || die "gr-ais not importable (gnuradio.ais)"
if command -v uhd_find_devices >/dev/null && timeout 20 uhd_find_devices 2>&1 | grep -q "B210\|type: b200"; then
  ok "USRP B210 detected"
else
  die "no USRP found (run with PATH=/usr/local/bin:... so UHD 4.10 is used; stop the terrestrial stack first)"
fi

step 2 "Clearing stale processes and ports"
kill_air; sleep 1
for p in 7009 7010 9201 9202 "$WS_PORT" "$HTTP_PORT" "$TILE_PORT"; do
  [ "$(count_ports "$p")" -ge 1 ] && warn "port $p still busy"
done
ok "ports clear"

step 3 "Module 1 (C++/UHD) build"
if [ ! -x "$M1_BIN" ] || [ -n "$(find "$HERE/module1/src" -newer "$M1_BIN" 2>/dev/null)" ]; then
  ( cd "$HERE/module1" && mkdir -p build && cd build && cmake .. >"$LOG_DIR/build.log" 2>&1 && make -j"$(nproc)" >>"$LOG_DIR/build.log" 2>&1 ) \
    && ok "built securecom_module1" || { tail -15 "$LOG_DIR/build.log"; die "module1 build failed"; }
else ok "binary up to date"; fi

step 4 "Hardware: securecom_module1 (AIS + ADS-B dwell)"
[ -n "$RX_GAIN" ]    && export SECURECOM_RX_GAIN_DB="$RX_GAIN"
[ -n "$DWELL_AIS" ]  && export SECURECOM_AIS_DWELL_SEC="$DWELL_AIS"
[ -n "$DWELL_ADSB" ] && export SECURECOM_ADSB_DWELL_SEC="$DWELL_ADSB"
( setsid nohup "$M1_BIN" >"$LOG_DIR/module1.log" 2>&1 </dev/null & )
# Module 1 opens its TCP servers immediately, then waits for the decoder to
# connect before it starts the radio.
wait_for_port 7009 20 && wait_for_port 7010 20 && ok "module1 up, IQ ports 7009/7010 open" \
  || { tail -15 "$LOG_DIR/module1.log"; die "module1 did not open its IQ ports"; }

step 5 "Air & Maritime bridge"
( cd "$HERE" && setsid nohup python3 -u airmaritime_bridge.py >"$LOG_DIR/bridge.log" 2>&1 </dev/null & )
wait_for_port "$WS_PORT" 15 && ok "bridge on ws://127.0.0.1:$WS_PORT" \
  || { tail -15 "$LOG_DIR/bridge.log"; die "bridge did not start"; }

step 6 "Decoder (airmaritime_decoder_live.py, via the bridge)"
python3 - "$WS_PORT" <<'PY' || warn "could not send start_flowgraph (start it from the console instead)"
import asyncio, json, sys, websockets
async def main():
    async with websockets.connect(f"ws://127.0.0.1:{sys.argv[1]}") as ws:
        await ws.send(json.dumps({"cmd": "start_flowgraph"})); await asyncio.sleep(1)
asyncio.run(main())
PY
wait_for_port 9201 20 && ok "decoder running, message taps 9201/9202 bound" \
  || warn "message taps not up yet — check $LOG_DIR/bridge.log (decoder is Qt; needs DISPLAY)"

step 7 "Map tile server"
( cd "$HERE" && setsid nohup python3 -u mbtiles_server.py >"$LOG_DIR/mbtiles.log" 2>&1 </dev/null & )
wait_for_port "$TILE_PORT" 10 && ok "tiles on http://127.0.0.1:$TILE_PORT" || warn "tile server not up — see $LOG_DIR/mbtiles.log"

step 8 "Web server for the console"
( cd "$GUI_DIR" && setsid nohup python3 -m http.server "$HTTP_PORT" --bind 127.0.0.1 >"$LOG_DIR/http.log" 2>&1 </dev/null & )
wait_for_port "$HTTP_PORT" 10 && ok "console at $CONSOLE_URL" || warn "web server not up"

[ "$OPEN_BROWSER" = 1 ] && command -v xdg-open >/dev/null && setsid xdg-open "$CONSOLE_URL" >/dev/null 2>&1 &
echo; echo "${B}Running.${RST}  console: $CONSOLE_URL"
echo "  map tiles : http://127.0.0.1:$TILE_PORT   bridge: ws://127.0.0.1:$WS_PORT"
echo "  stop with : ./run_airmaritime.sh --stop"
