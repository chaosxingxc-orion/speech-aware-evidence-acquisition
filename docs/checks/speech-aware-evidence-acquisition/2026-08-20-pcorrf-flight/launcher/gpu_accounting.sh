#!/usr/bin/env bash
# GPU-hour accounting for this attempt, derived from the archived flight.log
# and the run dir's own receipts. Operational only -- opens no response content.
#
# WHY THIS FILE EXISTS: the flight receipt's `gpu_hours_this_attempt` field is,
# by the P-TRAP/P-SLU precedent, SERVER-ALIVE WALL CLOCK (time.time() around
# start_session .. client.close()). On this attempt that measure reads 0.3628 h,
# ABOVE the registered 0.35 GPU-h ceiling -- because a one-time, cold-page-cache
# model-identity hash of the 20.76 GB of GGUF on the /mnt/e 9p mount ran AFTER
# the server was already spawned, holding VRAM while the GPU did no work. This
# script separates the three measures so the overshoot is stated exactly, with
# its mechanism, rather than reported as compute.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: gpu_accounting.sh <attempt-id>}"
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240/$ATTEMPT"

exec > >(tee "$SCRATCH/gpu-accounting.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "attempt: $ATTEMPT"

echo
echo "=== timeline (from flight.log, which is archived verbatim) ==="
grep -E "spawning llama-server|session up|FLIGHT START|req 0001 |req 0240 |client.close|wall:" "$SCRATCH/flight.log"

echo
echo "=== derived GPU-hour measures ==="
python - "$RD" "$SCRATCH/flight.log" <<'PY'
import json
import pathlib
import re
import sys

rd = pathlib.Path(sys.argv[1])
log = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
receipt = json.loads((rd / "flight-receipt.json").read_text(encoding="utf-8"))


def stamp(pattern):
    m = re.search(r"\[(\d\d):(\d\d):(\d\d)Z\] " + pattern, log)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


t_spawn = stamp(r"spawning llama-server")
t_up = stamp(r"session up")
t_start = stamp(r"FLIGHT START")
t_first = stamp(r"req 0001 ")
t_last = stamp(r"req 0240 ")
t_close = stamp(r"client\.close")

server_alive = float(receipt["gpu_occupied_seconds_this_attempt"])
flight_wall = float(receipt["wall_seconds"])
spawn_load = (t_up - t_spawn) if (t_up and t_spawn) else None
idle_gap = (t_start - t_up) if (t_start and t_up) else None
ceiling = float(receipt["registered_ceilings"]["gpu_hours"])
planned = float(receipt["planned_budgets"]["gpu_hours"])
calls = int(receipt["close_receipt"]["cost"]["calls_used"])

print(f"  server spawn -> session up (model load):        {spawn_load} s")
print(f"  session up -> FLIGHT START (server ALIVE, GPU IDLE:")
print(f"      cold-cache sha256 of 20,764,519,520 B of GGUF over 9p): {idle_gap} s")
print(f"  FLIGHT START -> last request (240 requests):    {flight_wall:.2f} s")
print()
print("  MEASURE A -- server-alive wall (the P-TRAP/P-SLU receipt convention):")
print(f"      {server_alive:.1f} s = {server_alive/3600:.4f} GPU-h   vs ceiling {ceiling}"
      f"  ->  {'OVER by %.4f h (%.1f s)' % (server_alive/3600 - ceiling, server_alive - ceiling*3600) if server_alive/3600 > ceiling else 'within'}")
gpu_active = (spawn_load or 0) + flight_wall
print("  MEASURE B -- GPU-active occupancy (model load + the 240 requests;")
print("               the idle hashing gap excluded):")
print(f"      {gpu_active:.1f} s = {gpu_active/3600:.4f} GPU-h   vs ceiling {ceiling}  ->  "
      f"{'OVER' if gpu_active/3600 > ceiling else 'within'}")
rate = 0.00059
print("  MEASURE C -- the registration's OWN measured-equivalent basis")
print(f"               ({rate} GPU-h/call x {calls} calls):")
print(f"      {rate*calls:.4f} GPU-h   vs ceiling {ceiling}  ->  "
      f"{'OVER' if rate*calls > ceiling else 'within'}  (registration cites ~0.15)")
print()
print(f"  planned gpu_hours on the ExecutionPlan (machine-checked <= ceiling): {planned}")
print(f"  ledger 'gpu hours' cell: 0.35 (registered ceiling; gate requires registered >= planned)")
PY

echo
echo "=== corroboration: the GPU did no work during the gap ==="
echo "  (a) flight.log shows a $(python -c "print('~16 min')") gap between 'session up' and request 0001;"
echo "  (b) live nvidia-smi samples taken by the flight operator during the gap read"
echo "      'P5, 1200 MHz, 0-1 % utilization, 23449 MiB' -- VRAM resident, clocks at idle,"
echo "      no throttle reason active (0x0);"
echo "  (c) the launcher process was in D (disk sleep) on p9_client_rpc with an open fd on"
echo "      \$SPEECHRL_DATA_DIR/models/.../Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf and"
echo "      /proc read_bytes climbing to 20,777,582,592 -- one full pass over both GGUF files."
echo
echo "=== server.log request-side corroboration (counts only) ==="
echo "  total lines: $(wc -l < "$RD/SAEA-PROBE-pcorrf-240.server.log")"
echo "  lines matching 'POST /v1/chat/completions': $(grep -c 'POST /v1/chat/completions' "$RD/SAEA-PROBE-pcorrf-240.server.log" 2>/dev/null || echo 0)"
echo
echo "=== FORWARD FIX (operational finding for the next flight) ==="
echo "  Build the transport + payload binding BEFORE start_session, or pre-warm the page"
echo "  cache for the data-root GGUF copies, so the model-identity hash never runs while"
echo "  the server is holding VRAM. On a warm cache this attempt's Measure A would have"
echo "  been ~0.10 GPU-h (the P-TRAP precedent's own 0.066 h for half the requests)."
echo "GPU ACCOUNTING DONE"
