#!/bin/bash
# Run the real decoder (allinone.py) against replay_module1.py, headless and with
# the speaker sent to ALSA's null device, and report what each tap produced.
#   tools/bench/run_decoder_offline.sh <secs> [replay_module1.py args...]
#   tools/bench/run_decoder_offline.sh 110 --tetra "/path/TETRA IQ.wav" --dwell 10
set -u
B="$(cd "$(dirname "$0")" && pwd)"; V="$(cd "$B/../.." && pwd)"; SECS=$1; shift
LOG=$(mktemp -d); DEC="$V/.bench_decoder.py"
sed "s/audio.sink(\([0-9]*\), '',/audio.sink(\1, 'null',/" "$V/allinone.py" > "$DEC"   # no sound out loud
python3 "$B/replay_module1.py" --secs "$SECS" "$@" > "$LOG/replay.log" 2>&1 & RP=$!
sleep 2
QT_QPA_PLATFORM=offscreen python3 "$DEC" > "$LOG/dec.log" 2>&1 & DP=$!
until grep -q "clients connected" "$LOG/replay.log" 2>/dev/null || ! kill -0 $RP 2>/dev/null; do sleep 0.5; done
for p in 9101 9102 9103 9104; do python3 "$B/tap_audio.py" $p $((SECS - 3)) > "$LOG/tap$p.log" 2>&1 & done
python3 "$B/tetra_events.py" $((SECS - 3)) > "$LOG/events.log" 2>&1 &
c0=$(awk '{print $14+$15}' /proc/$DP/stat 2>/dev/null); t0=$(date +%s)
wait $RP; c1=$(awk '{print $14+$15}' /proc/$DP/stat 2>/dev/null); t1=$(date +%s); sleep 4
sed 's/^/  /' "$LOG/replay.log"; cat "$LOG"/tap*.log | sed 's/^/  /'; sed 's/^/  /' "$LOG/events.log"
echo "  decoder CPU $(( (c1 - c0) / (t1 - t0 > 0 ? t1 - t0 : 1) ))% of one core"
grep -E "TOTALS|Traceback|Error" "$LOG/dec.log" | tail -4 | sed 's/^/  DEC: /'
kill -9 $DP 2>/dev/null; rm -rf "$LOG" "$DEC"
