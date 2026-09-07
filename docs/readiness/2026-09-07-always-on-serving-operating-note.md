# Always-on serving — operating note (E7)

Owner rule, 2026-09-07: the model may stay always on, provided monitoring numbers come back, so
that GPU time is reused across agents instead of being paid for again by every flight. This note
is the procedure. It changes no research claim and no scoring path; it changes who owns the
llama-server process and what every attempt has to report about the card.

Study `CLAUDE.md` already carried the pipeline half of the same rule: *one resident server per
serving geometry; ready flights are queued by geometry so the GPU never idles; official scoring
overlaps the next flight.* What was missing was a resident server that outlives a single flight
process, and a number proving the card was busy.

## The division of labour

| Who | Does | Never does |
|---|---|---|
| Coordinator | starts ONE serving session per geometry, in a background live wrapper; starts the monitor beside it; queues agents' tasks by geometry; stops the session only to switch geometry or at end of day | runs a flight inside the wrapper |
| Agent (flight) | attaches to the resident session; runs its phases; seals; reports the monitor summary in its final message | starts a server, stops a server, or kills anything on port 8080 |

A detached WSL job dies with the shell that spawned it. That is why `start` stays in the
foreground and why the coordinator — a live session — must be the one holding it. An agent's
session ends when its task ends; a server it owned would go with it.

## Coordinator procedure

1. **Start the session for the next geometry**, as a background live wrapper:

   ```bash
   bash scripts/serving_session.sh start q4km-hbmfree-np16 > /tmp/serving.log 2>&1 &
   ```

   `start` refuses if a `session.json` without a `session-stop.json` is already recorded, or if
   anything is already listening on the port. It writes
   `$SPEECHRL_DATA_DIR/serving/<session-id>/session.json`: the fragment id and its hash, the
   runtime receipt relpath and sha256, the binary path and re-hashed sha256, the receipt-pinned
   GGUF set (main shard and mmproj), the session role, the model root, the full command line, host
   and port, the pid, `started_at`, and a `GET /props` snapshot.

2. **Start the monitor beside it** (its samples are what every agent reports from):

   ```bash
   python scripts/serving_monitor.py sample --session-id <session-id> --interval 10 &
   ```

3. **Queue by geometry.** Every ready cell that wants the resident geometry runs before any cell
   that would need a different one. A cell of a different geometry waits for the switch; it does
   not get a second server.

4. **Switch geometry, or end the day:**

   ```bash
   bash scripts/serving_session.sh stop
   ```

   This writes `session-stop.json` with the stop receipt and the whole session's monitor summary,
   which is the day's GPU accounting for that geometry.

   A server that is already gone or `<defunct>` is recorded stopped instead of signalled: a plain
   `stop` takes that path automatically, and `stop --stale` asks for it explicitly. It refuses
   unless all three conditions hold — the pid is `defunct`/`gone`, nothing is listening on the
   session's port, and `nvidia-smi` reports an empty card — and it names every condition that
   failed. The record it writes carries `stale: true`, the whole observation, and the zombie's
   advisory exit status.

5. **Check on it any time:**

   ```bash
   bash scripts/serving_session.sh status
   python scripts/serving_monitor.py summarize --session-id <id> [--from T0] [--to T1]
   ```

   `status` reports `process_state` (`running` / `defunct` / `gone`) beside the older `pid_alive`
   flag, plus the port and card readings. `pid_alive` says "alive" for a zombie; `process_state`
   is the one to read.

6. **Never let a script kill llama-server blindly.** `scripts/serving_session.sh resident` exits 0
   when a session is resident, 3 when none is, and 2 when it cannot tell. `scripts/
   run_arm_sequence.sh` — the one launcher in this repository that runs `pkill -9 -f llama-server`
   — now asks first and refuses the arm on anything but 3.

## What an agent does

Nothing new. `core.flight.FlightRuntime.serve` looks for the resident session before it spawns
anything:

- **A matching session** → it attaches (`core.session.attach_session`, which independently
  re-verifies loopback, the runtime-receipt-pinned binary and GGUF identity, that the pid is alive
  right now, that the pid's real process image is the pinned binary, and that the pid owns the
  listening socket), sets `session_reused: true` in its serve receipt, and **never stops it**:
  `stop_serving()` is a no-op for a flight that did not start the server, and refuses outright if
  a flight ever claims to own a session it attached to (two guards, see the E7b section below).
- **A session serving something else** → `FlightServingSessionMismatchError`, naming every
  differing field. It never falls back to a second spawn: two 18.5 GB servers do not fit in this
  host's VRAM, so the correct action is always the coordinator's (stop the session, start the
  other geometry).
- **No session at all** → today's behaviour exactly: spawn, own, stop.

The reuse predicate compares the identity `session.json` records — `model_fragment`,
`model_fragment_sha256`, `runtime_receipt_relpath`, `runtime_receipt_sha256`, `binary_path`,
`binary_sha256`, `model_files` (main shard + mmproj, by sha256), `session_role`, `model_root`,
`server_argv` (diffed flag by flag, so a wrong `-c` is reported as `server_argv[-c]`), `server_env`,
`host`, `port`, and the two `GET /props` facts a flight can derive (`total_slots`, per-slot
`n_ctx`). `props_identity.build_info` is recorded but not compared: a flight has no independent way
to derive it, and the binary sha256 plus the runtime receipt already pin the build.

Both sides build the command line through the SAME function
(`core.session.build_server_command` over `core.session.serving.merge_server_args`). A second
argument builder would make this predicate compare two dialects instead of two servers.

## Geometry table

Which cells use which resident geometry. The SESSION's geometry is the fragment's own `-c`/`-np`
— that is literally what llama-server is handed — so `resolve_serving_profile` derives
`slots = -np` and `slot_tokens = -c / -np` from `server_args`. Most fragments (the whole hbmfree
family) declare no `serving_geometry` key at all; a fragment that does declare one is cross-checked
against its own flags and refused on a disagreement, exactly as the flight launchers already do.
On the flight side `FlightRuntime.serve` derives `-np`/`-c` from the ADAPTER geometry, so a cell
whose adapter disagrees with the resident session is refused at `server_argv[-c]`/`[-np]` rather
than served at the wrong window.

| Model fragment | `-np` | `-c` | slot tokens | Used by |
|---|---|---|---|---|
| `q4km-featcache-a2t-official-np2-04ccc72a` | 2 | 49152 | 24576 | Audio2Tool official-protocol cells on the tier-1 official population (the 654.6 s release row forces two slots) |
| `q4km-featcache-a2t-official-04ccc72a` | 3 | 49152 | 16384 | Audio2Tool official-protocol cells on the frozen 400 |
| `q4km-hbmfree-np16` | 16 | 32768 | 2048 | SLURP wide-fan cells (short fixed-shape JSON answers); declares no `serving_geometry` key — the geometry is derived from these two flags |
| `q4km-e22-dev-esb-mmproj-gpu-04ccc72a-np8-c40960` | 8 | 40960 | 5120 | Earnings-22 DEV ESB utterance cells (78.36 s worst row) |
| `q4km-e21-buf90-mmproj-gpu-04ccc72a` / `-np6` | 8 / 6 | 49152 / 36864 | 6144 | Earnings-21 buf90 window cells |
| `q8-e22-dev1500-esb-mmproj-gpu-04ccc72a-np8-c40960`, `q8-featcache-a2t-official-04ccc72a` | 8 / 3 | 40960 / 49152 | 5120 / 16384 | Q8 re-promotion cells only; Q8 is ~4.17x slower, so it never shares a session with a Q4 cell |

Two fragments that differ only in `max_tokens` can share one session: `max_tokens` is a request
parameter, so it is recorded in `session.json` but deliberately not part of the compared identity.
Anything that changes the command line or the model bytes cannot.

## Reporting fields

**Every agent's final message reports the monitor summary for its own contact window.** It is in
the seal receipt (`serving_monitor_summary`) and in
`<run_dir>/<run_id>-<attempt_id>.session-attach-receipt.json`, computed in-process by
`core.session.serving.summarize_monitor_file` over the session's `monitor.jsonl` between the first
and last contact of `run_phases`:

| Field | Meaning |
|---|---|
| `window.from` / `window.to` | the attempt's own contact window (epoch seconds) |
| `sample_count`, `first_sample_at`, `last_sample_at` | how much of the window the monitor actually covered |
| `wall_seconds` | seconds between the first and last sample in the window |
| `parked_seconds` | seconds with EVERY slot idle AND `utilization.gpu` < 5 % |
| `active_seconds` | the rest; `parked + active == wall` exactly |
| `parked_fraction` | `parked_seconds / wall_seconds` — the number the owner rule is about |
| `requests_delta` | requests the session served in the window (lower bound at the sampling interval) |
| `tokens_delta` | `tokens_predicted_total` delta; `null` unless the server was started with `--metrics` |
| `mean_power_watts`, `peak_power_watts` | the owner's own idle signal is power draw; read it beside the utilization figure |
| `mean_utilization_percent` | mean `utilization.gpu` over the window |

The serve receipt additionally carries `session_reused`, `session_source`
(`attached-serving-session` / `in-process-reuse` / `spawned`), `session_id`,
`serving_session_dir`, `monitor_path`, and `session_attach_receipt_path`.

## The first day, measured (2026-09-07)

Two sessions ran, back to back, one Earnings-22 ESB cell each. Their own monitor files, summarized
over the window up to each session's last answering sample
(`python scripts/serving_monitor.py summarize --session-id <id> --to <last-ok epoch>`):

| Session | Geometry | Wall | Active | Parked | Requests | Mean / peak power |
|---|---|---|---|---|---|---|
| `e22-dev-np8-c40960-20260907` | `-np 8 -c 40960` | 7,378 s | 1,630 s (22.1 %) | 5,749 s (77.9 %) | 1,195 | 26.1 W / 94.4 W |
| `e22-test-np8-c32768-20260907` | `-np 8 -c 32768` | 5,270 s | 799 s (15.2 %) | 4,471 s (84.8 %) | 596 | 19.4 W / 91.3 W |

**The card was parked for four fifths of both sessions, and most of that was one gap, not many.**
The dev session's last busy sample is 09:49:01Z and its server was stopped at 10:16:39Z; the test
session's last busy sample is 11:19:56Z and its server was stopped at 11:47:25Z. Each session
therefore ended with roughly 27½ minutes of a resident 18.5 GB server serving nothing at all,
while the next cell was still being registered.

**Rule: register the next cell while the current flight is still flying.** Preprocessing, the
exposure-ledger row, the plan and the roster all cost nothing on the GPU (CLAUDE.md's pipeline
rule: CPU packet preprocessing runs in parallel, ready flights are queued by geometry so the GPU
never idles). A cell that is ready the moment the previous one seals turns those 27 minutes into
work; a cell that starts being prepared after the previous one finishes parks the card twice a
day. Same-geometry cells attach to the SAME session — no restart, no reload — so the only thing
that has to be ready in advance is the registration.

## Three things that will bite

- **`--metrics` is not enabled on the pinned fragments, on purpose.** Adding the flag changes the
  argv and therefore the serving identity every flight compares, so it would have to be added to
  the fragment (and re-preregistered), not to the session script. Until then `tokens_delta` is
  `null` and `requests_delta` — derived by the monitor from `/slots` task-id changes — is the
  throughput number. `/slots` is on by default in this build; `/props` GET likewise.
- **A session whose process died without a stop record is still reported as resident.** That is
  deliberate: `attach_session` refusing a dead pid is a far better signal than a flight silently
  spawning a second 18.5 GB server. `scripts/serving_session.sh stop` now records the stop for
  such a session itself (see step 4), so this no longer needs a hand-written record — but it is
  still a state you have to clear before the next geometry can start.
- **A summary window that extends past the server's death counts those seconds as ACTIVE.** A
  sample the server did not answer has no slot reading, so it is not "every slot idle" and the
  parked test fails. Summarize to the last sample with `server_ok: true` (that is how the table
  above is computed) or read `parked_fraction` knowing the tail is in it.

## The wrapper's own lifecycle (E7b, 2026-09-07)

The wrapper is the server's PARENT, and the first day proved it was not behaving like one. Both
sessions ended with llama-server `<defunct>`: exited, never reaped. A zombie answers
`kill(pid, 0)`, so the old liveness check said "alive", while `/proc/<pid>/exe` no longer
resolves, so every I5 identity check refused it. `stop` refused ("cannot resolve executable image
for pid ... via /proc/<pid>/exe"), no `session-stop.json` was written, `start` refused the next
geometry as "already recorded as resident", and the coordinator wrote both stop records by hand.

- The `start` loop now **reaps** the child, writes `session-stop.json` with a `server_exit` block
  (reason, whether it reaped, and the decoded exit code or signal), prints ONE line to stderr, and
  **exits 1**. Exit 0 means, and only means, that the operator asked it to stop. Watch the
  wrapper's exit status: it is now the signal that a session ended unasked.
- There is deliberately **no `--restart-on-exit`**. An unrequested exit — an OOM, a crash, a stray
  signal — is exactly what has to be looked at, and a silent restart would hide it.
- `stop` treats a defunct pid as exited rather than waiting out its timeout and then failing the
  force path on a process that no longer has an executable image.

**An attached flight cannot do this to you.** The suspicion on 2026-09-07 was that the test
session's flight had killed the server on the way out; its own records say otherwise. That flight
wrote its receipts at 11:20:08Z; the server logged `all slots are idle` for 27 more minutes, the
monitor still saw eight idle slots at 11:47:19Z, and the last line of `server.log` is llama.cpp's
graceful signal-handler shutdown at ~11:47:25Z — the coordinator's own first `stop`. A flight that
attached sets `_owns_session = False` and records the session directory it bound to; `stop_serving`
returns `None` on the first and now refuses outright on the second, and there is no `atexit`, no
`killpg`, no `terminate` and no HTTP shutdown anywhere in the flight path. A regression test drives
a whole flight process — attach, phases, seal, `stop_serving`, interpreter exit — past a fake
server that records every signal it receives, and requires that it records none.

## Checks

`scripts/checks/engineering_base_check.py` enumerates modules and config values, not scripts, so
the two new scripts need no allowlist entry; the check passes unchanged. Coverage lives in
`tests/unit/test_serving_session.py`, `tests/unit/test_serving_monitor.py`, and the E7 section of
`tests/unit/test_flight_runtime.py` — no model contact, no GPU, no network in any of them. The
E7b tests drive real processes (an unreaped child for the zombie states, a signal-recording fake
server for the teardown) but never a model.

## Host memory (E7c)

**The incident (2026-09-07).** The WSL VM was allowed 56 GB of a 63.4 GB host. The serving
session's `llama-server` holds an ~18.5 GB resident footprint through a 20 GB GGUF `mmap` plus the
page cache behind it; that footprint filled the VM's own budget, Windows itself ran out of
headroom around the VM, and the Claude Code host watchdog killed the serving wrapper and its
`llama-server` child — not the VM, the wrapper process the coordinator was running. The in-flight
KC-E1 attempt aborted at 42 of 44 calls with no seal. Neither side alone would have shown this
coming: the VM side (`/proc/meminfo`) never ran low, because the VM itself had headroom; nothing
before E7c read the WINDOWS side at all.

**The `.wslconfig` change.** The owner lowered the WSL VM's memory allowance from 56 GB to
`memory=44GB` (host RAM is 63.4 GB), with `[experimental] autoMemoryReclaim=gradual` added so the
VM hands idle page cache back to Windows instead of holding everything it has ever touched. The
prior file is kept as `.wslconfig.bak-20260907`. 44 GB keeps ~19 GB of host headroom at the VM's
own ceiling, comfortably above the 12 GB `--min-host-free-gb` floor below, where the 56 GB cap left
only ~7 GB.

**The new fields.** `core.session.serving.read_host_memory()` answers both sides of the question in
one probe: ONE `powershell.exe` interop call (`Get-CimInstance Win32_OperatingSystem` for the
Windows host's own total/free memory, `Get-Process vmmem*` for the WSL VM's working set on the
host, both via `ConvertTo-Json` in a single 8-second-capped call) for the Windows side, and
`/proc/meminfo`'s own `MemTotal`/`MemAvailable` for the VM side. Each side fails soft to `None`
independently (no `powershell.exe`, a non-zero exit, or an unreadable `/proc/meminfo` each degrade
only their own side), and `host_memory_source` names which side(s) actually answered
(`"windows+vm"` / `"windows-only"` / `"vm-only"` / `"unavailable"`) so an all-`None` reading is
distinguishable from interop simply being switched off.

Every `scripts/serving_monitor.py sample` line now carries a `host_memory` object with
`host_total_gb`, `host_free_gb`, `vmmem_ws_gb`, `vm_total_gb`, `vm_available_gb` and
`host_memory_source`. `summarize_monitor_samples` folds the window's reading beside the existing
parked/active accounting: `host_free_gb_min` (with `host_free_gb_min_at`, the epoch of that
minimum) and `host_free_gb_last` track the Windows host's own free memory — the number the
watchdog acted on — while `vm_available_gb_min` and `vmmem_ws_gb_max` are the VM-side and
VM-footprint-on-host companions; `host_memory_samples` counts only samples carrying a non-null
`host_free_gb` reading, so a run entirely on a host with interop off reports `0` rather than a
misleadingly present minimum.

**The thresholds.**

| Threshold | Default | Where | Effect |
|---|---|---|---|
| `--host-free-warn-gb` | 6.0 GB | `scripts/serving_monitor.py sample` | a sample whose host free GB drops below this writes one `WARN host-memory` line to the monitor's own log (`monitor.log`, beside `monitor.jsonl` in the same session directory — never stdout), at most once per minute |
| `--min-host-free-gb` | 12.0 GB | `scripts/serving_session.sh start` (`core.session.serving._start`) | refuses to start a new resident server when the host's free memory is below this, naming the reading in the refusal; fails OPEN (never blocks) when the reading itself is unavailable |

`scripts/serving_session.sh status` prints the CURRENT `host_memory` reading beside the session
document — the same question `start` asks before it would spawn.

**The rule.** A serving wrapper is a host-watchdog target: the process the coordinator runs to hold
`llama-server` open is exactly the kind of long-lived, memory-heavy background process a host
watchdog kills first when Windows itself runs short, and it takes the resident server down with it
with no seal for whatever flight was mid-call. So the running `.wslconfig` cap must always leave
>= 12 GB free for Windows (matching `--min-host-free-gb`'s default) — lowering the VM's cap further
is always the correct response to a repeat of this incident, not raising the threshold to match a
tighter cap.
