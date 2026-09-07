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

5. **Check on it any time:**

   ```bash
   bash scripts/serving_session.sh status
   python scripts/serving_monitor.py summarize --session-id <id> [--from T0] [--to T1]
   ```

## What an agent does

Nothing new. `core.flight.FlightRuntime.serve` looks for the resident session before it spawns
anything:

- **A matching session** → it attaches (`core.session.attach_session`, which independently
  re-verifies loopback, the runtime-receipt-pinned binary and GGUF identity, that the pid is alive
  right now, that the pid's real process image is the pinned binary, and that the pid owns the
  listening socket), sets `session_reused: true` in its serve receipt, and **never stops it**:
  `stop_serving()` is a no-op for a flight that did not start the server.
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

## Two things that will bite

- **`--metrics` is not enabled on the pinned fragments, on purpose.** Adding the flag changes the
  argv and therefore the serving identity every flight compares, so it would have to be added to
  the fragment (and re-preregistered), not to the session script. Until then `tokens_delta` is
  `null` and `requests_delta` — derived by the monitor from `/slots` task-id changes — is the
  throughput number. `/slots` is on by default in this build; `/props` GET likewise.
- **A session whose process died without a stop record is still reported as resident.** That is
  deliberate: `attach_session` refusing a dead pid is a far better signal than a flight silently
  spawning a second 18.5 GB server. Clean it up with `scripts/serving_session.sh stop`, or delete
  the stale session directory once the pid is confirmed gone.

## Checks

`scripts/checks/engineering_base_check.py` enumerates modules and config values, not scripts, so
the two new scripts need no allowlist entry; the check passes unchanged. Coverage lives in
`tests/unit/test_serving_session.py`, `tests/unit/test_serving_monitor.py`, and the E7 section of
`tests/unit/test_flight_runtime.py` — no model contact, no GPU, no network in any of them.
