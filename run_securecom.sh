#!/usr/bin/env bash
# =============================================================================
#  SecureCOM — COUPLING Console, version1 : one-shot launcher
#
#  Brings the whole chain up in order and verifies each stage before moving on:
#
#    1. preflight        deps, files, USRP present
#    2. cleanup          kill stale processes / free ports  (this matters: a
#                        leftover decoder holding ZMQ 9101 silently stops the
#                        new one's audio taps from binding, and the console
#                        still reports "RUNNING")
#    3. build            module1 (C++/UHD) if the binary is missing or stale
#    4. bridge           bridge_server.py           -> ws://127.0.0.1:8787
#    5. web server       python3 -m http.server     -> http://127.0.0.1:8788
#    6. hardware         securecom_module1  (C++ tuner + burst scheduling)
#    7. decoder          allinone.py        (GNU Radio, 1 chain each DMR/NXDN/P25 + TETRA)
#    8. GUI              open the console in a browser
#
#  Steps 6 and 7 are driven through the bridge's WebSocket rather than started
#  directly. The bridge owns those two processes, so launching them behind its
#  back would leave the console's Start/Stop buttons, status tiles and schedule
#  Apply out of sync with reality.
#
#  Usage:
#     ./run_securecom.sh                        # defaults, opens browser
#     ./run_securecom.sh --dwell-dmr 15         # 15 s DMR dwell
#     ./run_securecom.sh --gain 30              # RX gain 30 dB
#     ./run_securecom.sh --no-browser           # headless / remote X
#     ./run_securecom.sh --stop                 # shut everything down, exit
#
#  Ctrl-C shuts the whole stack down cleanly.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_DIR="$HERE/gui"
M1_DIR="$HERE/module1"
M1_BIN="$M1_DIR/build/securecom_module1"
M2_PY="$HERE/allinone.py"
WS_URL="ws://127.0.0.1:8787"
HTTP_PORT=8788
CONSOLE_URL="http://127.0.0.1:$HTTP_PORT/securecom_gui.html"
LOG_DIR="${TMPDIR:-/tmp}/securecom_v1"

DWELL_DMR=""; DWELL_NXDN=""; DWELL_P25=""; DWELL_TETRA=""
RX_GAIN=""; OPEN_BROWSER=1; STOP_ONLY=0

if [ -t 1 ]; then
  B=$'\e[1m'; DIM=$'\e[2m'; GRN=$'\e[32m'; RED=$'\e[31m'; YEL=$'\e[33m'; RST=$'\e[0m'
else
  B=""; DIM=""; GRN=""; RED=""; YEL=""; RST=""
fi
step(){ echo; echo "${B}[$1/8] $2${RST}"; }
ok(){   echo "   ${GRN}OK${RST}  $*"; }
warn(){ echo "   ${YEL}!${RST}   $*"; }
die(){  echo "   ${RED}FAIL${RST} $*" >&2; exit 1; }
info(){ echo "   ${DIM}$*${RST}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dwell-dmr)   DWELL_DMR="${2:?}";   shift 2;;
    --dwell-nxdn)  DWELL_NXDN="${2:?}";  shift 2;;
    --dwell-p25)   DWELL_P25="${2:?}";   shift 2;;
    --dwell-tetra) DWELL_TETRA="${2:?}"; shift 2;;
    --gain)        RX_GAIN="${2:?}";     shift 2;;
    --no-browser)  OPEN_BROWSER=0;       shift;;
    --stop)        STOP_ONLY=1;          shift;;
    -h|--help)     sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) die "unknown option: $1  (try --help)";;
  esac
done

mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------- helpers

port_busy(){ ss -tln 2>/dev/null | grep -q ":$1 "; }

wait_for_port(){ # port, seconds, label
  local p="$1" limit="$2" label="$3" i=0
  while [ "$i" -lt "$((limit*4))" ]; do
    port_busy "$p" && { ok "$label listening on :$p"; return 0; }
    sleep 0.25; i=$((i+1))
  done
  return 1
}

count_ports(){ ss -tln 2>/dev/null | grep -cE "$1"; }

ws_send(){ # json payload -> bridge
  python3 - "$1" <<'PY' 2>/dev/null
import asyncio, json, sys
try:
    import websockets
except ImportError:
    sys.exit(3)
payload = sys.argv[1]
async def main():
    async with websockets.connect('ws://127.0.0.1:8787', open_timeout=8) as ws:
        await ws.send(payload)
        await asyncio.sleep(0.6)          # let the bridge act before we drop
asyncio.run(main())
PY
}

kill_stack(){
  pkill -9 -f "$HERE/allinone.py"      2>/dev/null
  pkill -9 -f "allinone.py"            2>/dev/null
  pkill -9 -f "securecom_module1"      2>/dev/null
  pkill -9 -f "bridge_server.py"       2>/dev/null
  pkill -9 -f "http.server $HTTP_PORT" 2>/dev/null
  sleep 1.5
}

cleanup(){
  echo; echo "${B}shutting down…${RST}"
  ws_send '{"cmd":"stop_decoder"}' || true
  ws_send '{"cmd":"stop"}'         || true
  sleep 1
  kill_stack
  ok "stack stopped"
}

if [ "$STOP_ONLY" = "1" ]; then
  echo "${B}SecureCOM COUPLING — stopping${RST}"; cleanup; exit 0
fi
trap 'cleanup; exit 0' INT TERM

echo "${B}SecureCOM — COUPLING Console, version1${RST}"
info "$HERE"
info "logs: $LOG_DIR"

# ---------------------------------------------------------------- 1. preflight
step 1 "Preflight"
command -v python3 >/dev/null || die "python3 not found"
for f in "$GUI_DIR/bridge_server.py" "$GUI_DIR/securecom_gui.html" "$M2_PY" "$M1_DIR/CMakeLists.txt"; do
  [ -f "$f" ] || die "missing: $f"
done
ok "project files present"

python3 - <<'PY' || die "missing python deps — need: numpy websockets pyzmq, plus GNU Radio (gnuradio, pmt, dsd)"
import importlib, sys
missing=[m for m in ('numpy','websockets','zmq','pmt','dsd') if not importlib.util.find_spec(m)]
if missing:
    print('   missing modules:', ', '.join(missing)); sys.exit(1)
PY
ok "python deps present (numpy, websockets, pyzmq, pmt, dsd)"

# ---------------------------------------------------------------- 2. cleanup
step 2 "Clearing stale processes and ports"
kill_stack
for p in 8787 "$HTTP_PORT" 7001 7002 7003 7004 9101 9102 9103 9104 9105; do
  port_busy "$p" && warn "port $p still busy (something outside this script owns it)"
done
ok "ports clear"

if command -v uhd_find_devices >/dev/null; then
  if timeout 20 uhd_find_devices 2>&1 | grep -q "B210\|type: b200"; then
    ok "USRP B210 detected"
    # Read the B210's OWN negotiated speed. Grepping `lsusb -t` for "5000M" matched
    # unrelated USB 3 devices (e.g. an Ethernet adapter) and hid a USB 2.0 B210.
    b210_speed=""
    for d in /sys/bus/usb/devices/*; do
      [ -f "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = "2500" ] && b210_speed="$(cat "$d/speed" 2>/dev/null)" && break
    done
    case "$b210_speed" in
      5000|10000|20000) ok "USB 3.x link (B210 at ${b210_speed} Mbps)";;
      "")  warn "could not read the B210's USB speed";;
      *)   warn "B210 is on USB 2.0 (${b210_speed} Mbps) — long dwells can fail with LIBUSB_TRANSFER_ERROR. Use a blue USB 3 port and a short USB 3 cable, directly on the PC (no hub)";;
    esac
  else
    die "no USRP found. Reseat USB (prefer a direct port over a hub), then: uhd_find_devices"
  fi
else
  warn "uhd_find_devices not on PATH — skipping radio check"
fi


# ---------------------------------------------------------------- 3. build
step 3 "Module 1 (C++/UHD) build"
NEED_BUILD=0
if [ ! -x "$M1_BIN" ]; then NEED_BUILD=1; info "binary not built yet"
else
  for s in "$M1_DIR"/src/*; do [ "$s" -nt "$M1_BIN" ] && { NEED_BUILD=1; info "source newer than binary: $(basename "$s")"; break; }; done
fi
if [ "$NEED_BUILD" = "1" ]; then
  command -v cmake >/dev/null || die "cmake not found (needed to build module1)"
  mkdir -p "$M1_DIR/build"
  ( cd "$M1_DIR/build" && cmake .. && make ) > "$LOG_DIR/build.log" 2>&1 \
    || { tail -25 "$LOG_DIR/build.log"; die "build failed — see $LOG_DIR/build.log"; }
  ok "built securecom_module1"
else
  ok "binary up to date"
fi

# ---------------------------------------------------------------- 4. bridge
step 4 "Bridge (process control + real IQ/audio -> WebSocket)"
# Schedule/gain are exported here, not pushed over the WebSocket after the fact:
# the bridge seeds current_dwell/current_rx_gain_db from its own environment, so
# the values are already in place when it builds module1's child env. Pushing
# them post-launch raced the start and silently left dwell at the 1 s default.
[ -n "$DWELL_DMR" ]   && export SECURECOM_DMR_DWELL_SEC="$DWELL_DMR"
[ -n "$DWELL_NXDN" ]  && export SECURECOM_NXDN_DWELL_SEC="$DWELL_NXDN"
[ -n "$DWELL_P25" ]   && export SECURECOM_P25_DWELL_SEC="$DWELL_P25"
[ -n "$DWELL_TETRA" ] && export SECURECOM_TETRA_DWELL_SEC="$DWELL_TETRA"
[ -n "$RX_GAIN" ]     && export SECURECOM_RX_GAIN_DB="$RX_GAIN"
( cd "$GUI_DIR" && setsid nohup python3 -u bridge_server.py >"$LOG_DIR/bridge.log" 2>&1 </dev/null & )
wait_for_port 8787 15 "bridge" || { tail -20 "$LOG_DIR/bridge.log"; die "bridge did not start — see $LOG_DIR/bridge.log"; }

# ---------------------------------------------------------------- 5. web server
step 5 "Web server for the console"
( cd "$GUI_DIR" && setsid nohup python3 -m http.server "$HTTP_PORT" --bind 127.0.0.1 >"$LOG_DIR/http.log" 2>&1 </dev/null & )
wait_for_port "$HTTP_PORT" 10 "web server" || die "web server did not start"
info "serve over http:// — opening the .html as file:// breaks the WebSocket and .wav playback"

# ---------------------------------------------------------------- 6. hardware
step 6 "Hardware: securecom_module1 (tuning + burst scheduling)"
for kv in "DMR:$DWELL_DMR" "NXDN:$DWELL_NXDN" "P25:$DWELL_P25" "TETRA:$DWELL_TETRA"; do
  n="${kv%%:*}"; v="${kv#*:}"; [ -n "$v" ] && ok "dwell $n = ${v}s"
done
[ -n "$RX_GAIN" ] && ok "RX gain = ${RX_GAIN} dB"

ws_send '{"cmd":"start"}' || die "bridge refused start (is it still up? $LOG_DIR/bridge.log)"
for i in $(seq 1 40); do
  [ "$(count_ports '0.0.0.0:700[1-4] ')" -ge 4 ] && break
  sleep 0.5
done
IQ_N="$(count_ports '0.0.0.0:700[1-4] ')"
[ "$IQ_N" -ge 4 ] || { tail -20 "$LOG_DIR/bridge.log"; die "only $IQ_N/4 IQ ports open — module1 did not come up"; }
ok "module1 running, 4/4 IQ ports open (7001-7004)"

# ---------------------------------------------------------------- 7. decoder
step 7 "Decoder: allinone.py (GNU Radio)"
ws_send '{"cmd":"start_decoder"}' || die "bridge refused start_decoder"
info "GNU Radio builds the DMR/NXDN/P25 chains + TETRA — this takes a few seconds"
for i in $(seq 1 60); do
  [ "$(count_ports '127.0.0.1:910[1-5] ')" -ge 5 ] && break
  sleep 0.5
done
ZMQ_N="$(count_ports '127.0.0.1:910[1-5] ')"
if [ "$ZMQ_N" -ge 5 ]; then
  ok "decoder running, 5/5 audio+event taps bound (9101-9105)"
else
  warn "only $ZMQ_N/5 ZMQ taps bound — audio/recording may not work"
  warn "check $LOG_DIR/bridge.log; usually a stale allinone.py still holds a port"
fi

# ---------------------------------------------------------------- 8. GUI
step 8 "Console"
if [ "$OPEN_BROWSER" = "1" ] && command -v xdg-open >/dev/null && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  xdg-open "$CONSOLE_URL" >/dev/null 2>&1 &
  ok "opened $CONSOLE_URL"
else
  ok "open this in a browser:  $CONSOLE_URL"
fi

cat <<EOF

${B}Running.${RST}
  console : $CONSOLE_URL
  header  : should read "LIVE — real IQ + real decode/audio"

  Key up your radio; watch the Signals tab for DECODING and the Recordings tab
  for .wav files (whole-dwell capture, labelled with whether decode happened).

  Recordings : $GUI_DIR/recordings
  Logs       : $LOG_DIR/{bridge,http,build}.log

  Ctrl-C here stops everything.  Or from another shell:
      $0 --stop
EOF

# Hold the foreground so Ctrl-C reaches the trap; surface it if the bridge dies.
while pgrep -f bridge_server.py >/dev/null; do sleep 2; done
warn "bridge exited unexpectedly — see $LOG_DIR/bridge.log"
cleanup
