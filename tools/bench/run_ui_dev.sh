#!/usr/bin/env bash
# UI development environment WITHOUT the B210: real recorded IQ (tools/bench/replay_bands.py) on ports
# 7001-7008, the bridge in external-IQ mode, the decoder, and the web server. Open
#   http://127.0.0.1:8788/securecom_gui.html
#   ./tools/bench/run_ui_dev.sh          start
#   ./tools/bench/run_ui_dev.sh --stop   stop everything it started
set -u
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
RUN=/tmp/securecom_uidev
mkdir -p "$RUN"
export PATH=/usr/local/bin:/usr/bin:/bin

stop() {
  # pid files hold the REAL process (see start(): the shell exec's into it)
  for f in "$RUN"/*.pid; do
    [ -f "$f" ] || continue
    kill "$(cat "$f")" 2>/dev/null
    rm -f "$f"
  done
  sleep 1
  # allinone.py is started by the bridge: its pid is on the bridge's command list, not ours
  while read -r pid; do kill "$pid" 2>/dev/null; done < <(pgrep -f "^python3 .*allinone\.py\$" || true)   # anchored: never matches a shell that merely mentions the name
  echo "stopped"
}

[ "${1:-}" = "--stop" ] && { stop; exit 0; }
stop >/dev/null 2>&1

# start NAME DIR ENV... -- COMMAND...   (runs detached; no inherited stdout, so callers never hang on it)
start() {
  local name=$1 dir=$2; shift 2
  local envs=()
  while [ "$1" != "--" ]; do envs+=("$1"); shift; done
  shift
  setsid nohup bash -c 'echo $$ >"$0"; cd "$1"; shift; exec env "$@"' \
      "$RUN/$name.pid" "$dir" "${envs[@]}" "$@" >"$RUN/$name.log" 2>&1 </dev/null &
}

start replay "$HERE" X=1 -- python3 -u tools/bench/replay_bands.py "$RUN/replay_stats.txt"
for _ in $(seq 1 60); do grep -q "serving 8 bands" "$RUN/replay.log" 2>/dev/null && break; sleep 1; done
start bridge "$HERE/gui" SECURECOM_EXTERNAL_IQ=1 -- python3 -u bridge_server.py
start http "$HERE/gui" X=1 -- python3 http_server_nocache.py 8788 --bind 127.0.0.1
for _ in $(seq 1 30); do ss -ltn | grep -q ":8787 " && break; sleep 1; done
python3 - <<'PY'
import asyncio, json, websockets
async def m():
    async with websockets.connect('ws://127.0.0.1:8787') as ws:
        await ws.send(json.dumps({'cmd': 'start_decoder'}))
        await asyncio.sleep(2)
asyncio.run(m())
PY
echo "UI dev environment up (real recorded IQ, no B210):"
echo "  console : http://127.0.0.1:8788/securecom_gui.html"
echo "  stop    : $0 --stop"
