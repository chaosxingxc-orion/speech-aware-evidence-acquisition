# P-CORR-F percept-keyed type-corrective supply probe — FLIGHT RECEIPT (2026-08-20)

Registered probe `SAEA-PROBE-pcorrf-240`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md`. Machinery:
`rails.probes.pcorrf_flight` (landed at `5c3e0fa`), flown at study commit `1faccd8`, tree clean
throughout.

**This flight produced no read.** Every response row was written to `outputs.jsonl` for the
separately-registered one-shot read mission (`analysis.pcorrf_read`) and was never opened, scored,
or interpreted here. Everything in this directory is operational, structural, or CONSTRUCTION
metadata: request counts, corrective-entry counts, latencies, hashes, cost. No response text, no
recovery or contamination flag, no SLU-F1, no verdict.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-pcorrf-240` |
| Attempt | `attempt-20260820T151845Z-88b2a5` |
| Status | `COMPLETED` (error `None`) |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240/attempt-20260820T151845Z-88b2a5` |
| Study commit | `1faccd8`, tree clean at takeoff and at `client.close()` |
| Config hash | `abea45e994e0a73e3575c82c01eedb370469bb2885f7cf8e05e5dd3eb955ec37` |
| Protocol hash | `4f540b24df430cbb80c4e1e9dc6c0ee09f61b698d1022ca39a50a750fdd7400e` (= `binding_config_sha256`, the machinery's own `build_execution_plan` pin) |
| Config-derived protocol hash | `f198fb8eb6c9cbb109e0fb5dbd555c1e79321ba524d5cb4b421f95fc71d22cb7` (the P-SLU/P-KEY/P-TRAP formula, recorded alongside — see section 2) |
| Split identity | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` (the SAME frozen 60 SLURP devel samples the consumed P-SLU/P-KEY/P-TRAP/P-EMB probes used) |
| Trace manifest hash | `ab750515989bd8197143e5983a07d20af29521244ea2af3982e451e9c9f45f85` |
| **Corrective binding hash (tri-derivation)** | **`3a461f694acdc46eca3ef69fe3f157be058343816157037c31972ac179f6830a`** |
| Corrective binding document hash | `c2466b7e208f8ef5e2e9b76dccdeb58effa26c407a48ffaff38a74ce3cd6cb47` |
| Attempts | **one**; 240 flown, 0 replayed, 0 carried, 0 failed |

## 1. Binding phase (offline, zero model calls, zero gold)

The preregistration makes the corrective CONTENT itself derived data: every appended roster entry
is a train-mined legal `(type, value)` pair keyed by one of the core's OWN emitted fillers from the
consumed zero-supply A0 attempt. Sourcing it is therefore the registered binding step, not a result
read. Unlike its P-TRAP twin, this binding is entirely **gold-free** — "wrong" is never computed,
because a wrong-only key would be an oracle for a benefit probe (preregistration section 1,
legality audit item I1). The chain ran verbatim:

```
assert_ledger_row_consumed("SAEA-PROBE-pslu-n60")            -> consumed = yes
  -> pcorrf_flight.harvest_a0_emitted_slots(attempt-20260818T010218Z-4c97cb)
       (ALL emitted (type, filler) slots; parse_slu_response only, no gold loader)
  -> pcorrf_flight.mine_train_pool(train.jsonl ONLY) + assert_train_pool_sha256
  -> pcorrf_flight.build_corrective_binding(seed=20260807)
  -> pcorrf_flight.assert_corrective_binding_hash
```

The **tri-derivation corrective binding hash** (preregistration section 4 item 1) is a pure
function of `(per-sample A0 response sha256, train-pool sha256, seed)` and was derived at three
independent sites: the BUILDER inside `build_corrective_binding`, the standalone VALIDATOR called
by `binding.py` and again by the pre-flight, and the FLIGHT PREFLIGHT inside `run_pcorrf_flight`
before it issued any request. The launcher additionally refused to fly unless the canonical
binding-document hash equalled the reviewed one. All derivations agree at
`3a461f694acdc46eca3ef69fe3f157be058343816157037c31972ac179f6830a` — the value the machinery's own
build receipt pinned (`3a461f69…6830a`).

Structural result (`corrective-binding-stats.json`; the full corrective table carries
percept-selected supply text and stays in the attempt dir, outside Git):

| Quantity | Value |
|---|---|
| Samples | 60 |
| Train-mined pool | 4157 (type, filler) pairs / 3961 distinct values / 55 types, sha256 `fe372974…6ef6` |
| A0 emitted (type, filler) slots harvested | 95 |
| **L1 corrective entries (W1 = W3 supply)** | **61 total, mean 1.0167/sample, max 4** |
| L1 K distribution (K → n samples) | `{0: 20, 1: 25, 2: 10, 3: 4, 4: 1}` |
| **L1 K = 0 samples (untouched by construction)** | **20** |
| W2 cross-sample entries | 61 total, K distribution identical to W1 (length-matched on every sample) |
| W2 donor breadth | 30 distinct origin samples across 61 entries; 0 donor-pool shortfalls |
| **W4 = L1 ∪ L2b entries** | **120 total, mean 2.0000/sample, max 7** |
| W4 K distribution (K → n samples) | `{0: 14, 1: 11, 2: 10, 3: 14, 4: 10, 7: 1}` |
| W4 K = 0 samples | 14 |

Every figure reproduces the registration's own cited yield exactly: mean ~1.02 L1 entries (1.0167),
max 4, 20/60 at K=0, and L2b mean 2.00 (2.0000).

Binding invariants, machine-checked in the binding step, again in the pre-flight, and a third time
by `validate_pcorrf_flight_summary` over the rows actually produced:

- every W2 entry is fixed-point-free (`origin_sample_id` ≠ its target), by pool construction;
- every W2 K equals that same sample's own W1 K (length-matched; no donor shortfall anywhere);
- every L1 entry's `origin_sample_id` equals its own target (the self-percept property);
- no W4-added entry duplicates an L1 entry (dedupe by `(type, normalized value)`);
- **no gold-keyed accept/reject exists anywhere in the construction path.** A corrective entry MAY
  equal gold — that is the point of a type-repair probe — and nothing checked that equality before
  flight. The P-TRAP gold zero-overlap guard is deliberately ABSENT here: it would be an oracle.

Three legality guards, all fail-closed, all re-run explicitly in the pre-flight
(`preflight.log`) on top of their import-time firing:

1. tri-derivation corrective binding hash (above);
2. source-introspection AST guard `assert_never_references_forbidden_gold_symbols` — the flight
   module may not reference `harvest_a0_wrong_values`, `load_slurp_split`, or
   `load_gold_by_sample_id` — plus the reused `assert_never_calls_ontology_miner` (a strictly
   stronger ban that also discharges the registration's narrower
   `load_slurp_ontology(include_synthetic=True)` clause);
3. declarations `span_source="percept-keyed-type-lookup"`,
   `reference_source="slurp-train-ontology"`, `legality_tier="legal"`, resolved through
   `core.legality.assert_legality_declaration_legal` with no warning and no oracle lineage.

## 2. Flight

One `llama-server` session served all four arms — it is one model. The binary was receipt-pinned
and spawned as a CHILD of this flight's own wrapper.

| Field | Value |
|---|---|
| Arms | `W1` → `W2` → `W3` → `W4`, per sample, over the frozen 60 |
| Requests | **240 flown, 0 replayed, 0 carried, 0 failed** |
| Rows by arm | `{"W1": 60, "W2": 60, "W3": 60, "W4": 60}`; **240 distinct (arm, sample_id) pairs** |
| Per-arm K distribution in `outputs.jsonl` | identical to the binding, arm for arm (section 4) |
| Base roster | the frozen A3-form 100-entry train-only roster, reused byte-identically (W1/W2/W4; W3 has no base) |
| Mean latency | W1 1.448 s, W2 1.398 s, W3 1.136 s, W4 1.300 s |
| Flight wall | 5.4 min (325.96 s), 44.2 req/min at the end |
| Tokens | 142,917 prompt / 15,177 completion; 0 tool calls |
| llama-server argv | `-c 49152 -np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0` — the committed fragment's own, UNCHANGED, so the decode config is the consumed P-SLU flights' (the registration's "A3-form base so V1/V2/A3 are directly citable" requirement) |

**One documented divergence from the P-SLU/P-KEY/P-TRAP launcher precedent.** Those flights built
their `ExecutionPlan` by hand with
`core.config.protocol_hash(config_hash, arm, split_identity_hash)`. P-CORR-F instead uses the
machinery's OWN registered constructor `rails.probes.pcorrf_flight.build_execution_plan`, because
that is the coordinator-reviewed path: it re-resolves the execution profile through
`contracts.assert_execution_scope` and re-asserts the registered ceilings via
`assert_within_registered_ceilings` on the way through, and its `protocol_hash` is the pinned,
drift-checked `binding_config_sha256()`. The launcher additionally verifies that the machinery
plan's `split_identity_hash` equals the manifest's before flying. The precedent's
config-derived hash is NOT discarded — it is recorded as `config_protocol_hash` in both
`config-values.json` and `flight-receipt.json`, so any cross-probe comparison the read wants stays
available.

Arm-level idempotence was wired but not needed: `run_pcorrf_flight` received an
`already_completed` map (empty on this single attempt), and the launcher's own `--carry-from`
path — which copies a COMPLETE arm's rows forward verbatim and never re-fires those cells — was
therefore exercised as a no-op (`carried_arms: []`, `carried_row_count: 0`). A per-request
response cache (`responses.jsonl`, 240 lines) backs within-attempt replay and refuses any replay
whose rebuilt message sha256 disagrees with the cached one.

## 3. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls | 240 | **240** | 260 | 20 |
| Metered speech-audio seconds | 730 | **729.04** | 1000 | 270.96 |
| GPU hours (server-alive wall) | 0.15 | **0.3628** | 0.35 | **−0.0128 (OVER)** |

Prior durable spend on this run id was 0 at takeoff, so the run-total feasibility check passed with
full headroom. Calls and metered audio are both comfortably inside their ceilings and are the two
columns the attempt store durably accounts.

### The GPU-hour column overshoots on the wall-clock measure — stated plainly

`gpu_hours_this_attempt` = **0.3628**, which is **0.0128 GPU-h (46.1 s) above the registered 0.35
ceiling**. The full derivation is `gpu-accounting.log`. What happened:

| Interval | Duration | GPU doing work? |
|---|---|---|
| `spawning llama-server` → `session up` (model load) | 22 s | yes |
| `session up` → `FLIGHT START` | **959 s** | **no** |
| `FLIGHT START` → request 240 | 325.96 s | yes |

The 959-second gap is a **one-time, cold-page-cache sha256 of the 20,764,519,520 bytes of GGUF on
the `/mnt/e` 9p mount**, run by the transport/payload-binding identity verification — which the
launcher performs *after* `start_session`, so the server was alive and holding 23,449 MiB of VRAM
while the GPU did nothing. Three independent corroborations that no compute occurred in that
window:

- `flight.log` (archived verbatim) shows request 0001 only at `15:35:07Z`, sixteen minutes after
  `session up` at `15:19:07Z`;
- live `nvidia-smi` samples taken during the gap read `P5, 1200 MHz, 0–1 % utilization,
  23449 MiB`, with `clocks_event_reasons.active = 0x0` (idle clocks, no throttle);
- the launcher process sat in `D` (disk sleep) on `p9_client_rpc` with an open fd on
  `$SPEECHRL_DATA_DIR/models/.../Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf`, `/proc` `read_bytes`
  climbing to 20,777,582,592 — one full pass over both GGUF files.

Two other measures of the same attempt, both well inside the ceiling:

- **GPU-active occupancy** (model load + the 240 requests, gap excluded): 348.0 s = **0.0967 GPU-h**;
- **the registration's own measured-equivalent basis** (0.00059 GPU-h/call × 240 calls):
  **0.1416 GPU-h** — matching the registration's own cited "≈0.15".

Nothing was machine-refused: the fail-closed ceiling gate applies to the *planned* GPU hours (0.15,
checked ≤ 0.35 by `assert_within_registered_ceilings` inside `build_execution_plan`), and the
durable attempt store accounts calls and audio-seconds, not GPU-h. The overshoot is therefore a
receipt-level wall-clock artifact of an idle-server interval, not 0.36 hours of compute — but it is
recorded here as an overshoot rather than quietly reported on the flattering measure.

**Forward fix (operational finding).** Build the transport and payload binding *before*
`start_session`, or pre-warm the page cache for the data-root GGUF copies, so model-identity
hashing never runs while the server holds VRAM. On a warm cache this attempt's wall measure would
have been ≈0.10 GPU-h, in line with the P-TRAP precedent's 0.066 h for half the requests. Whether
the registered ceiling should be read as server-alive wall or as GPU-active occupancy is a
REGISTRATION question, not an implementer's to settle; both numbers are on the record above.

## 4. Corrective-entry counts actually flown (CONSTRUCTION metadata, not a result)

How much corrective supply each arm actually rendered. This is CONSTRUCTION metadata — it says how
many entries were built and sent, never what the core did with them. Read off `outputs.jsonl`'s
`arm`/`k` fields only; the `metrics` and `response_text` fields of those same rows were never
opened.

| Arm | Construction | Entries flown | Mean/sample | Max | K distribution (K → n samples) | K = 0 samples |
|---|---|---|---|---|---|---|
| **W1 CORR-SELF** | A3 100-entry roster + this sample's own L1 | **61** | 1.0167 | 4 | `{0: 20, 1: 25, 2: 10, 3: 4, 4: 1}` | **20** |
| **W2 CORR-CROSS** | A3 roster + length-matched entries from OTHER samples' L1 | **61** | 1.0167 | 4 | `{0: 20, 1: 25, 2: 10, 3: 4, 4: 1}` | **20** |
| **W3 CORR-ONLY** | L1 alone, no roster base | **61** | 1.0167 | 4 | `{0: 20, 1: 25, 2: 10, 3: 4, 4: 1}` | **20** |
| **W4 CORR-WIDE** | A3 roster + L1 ∪ L2b (`retrieve(k=3, min_score=0.70)`) | **120** | 2.0000 | 7 | `{0: 14, 1: 11, 2: 10, 3: 14, 4: 10, 7: 1}` | **14** |

Every distribution in `outputs.jsonl` matches the reviewed binding arm for arm — the flight
rendered exactly the table the binding step produced, and nothing else.

Rendered prompt shapes (pre-flight dry run, `preflight.log`): W1 and W2 each rendered
100 × 60 + 61 = 6,061 roster items; W4 rendered 100 × 60 + 120 = 6,120; W3 rendered 61 items
across 40 packets, and its **20 K = 0 samples flew true zero-supply (`supply=None`)** rather than
an empty-but-present roster block — the documented construction choice in
`_corrective_roster_packet`.

W2's cross-sample draw was length-matched to W1 on **every one of the 60 samples** (zero
donor-pool shortfalls), drawn fixed-point-free from **30 distinct origin samples** across its 61
entries.

## 5. Hygiene evidence

- **Suite**: the full suite ran once on a quiet machine before any core contact —
  **3355 passed, 9 skipped** in 68 s (`preflight-pytest.log`), including the 110 P-CORR-F tests
  (80 flight + 30 read). The flight brief cited "3354 passed / 9 skipped at `5c3e0fa`", one below
  what this machine reports. That was reconciled BEFORE takeoff rather than waved through:
  `collect-delta.log` collects both commits from read-only `git archive` extracts and gets
  **3364 tests collected at `5c3e0fa` and 3364 at `1faccd8`** — an identical collection, as it must
  be, since `1faccd8` adds one readiness `.md` and no test code (`git diff --stat` in the same
  log). 3355 + 9 = 3364. The brief's figure is one off; the suite did not change.
- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary
  sha256 `097c96ec…c68` matches the receipt pin; both GGUF files match their receipt pins on byte
  count and sha256; and — per this flight's own mission instruction — the receipt's two GGUF
  sha256 values were additionally cross-checked against the **umbrella lock**
  (`docs/datasets.lock.json`, entry `qwen3-omni-30b-a3b-instruct-gguf-q4km`, status COMPLETE), with
  the flight-composed `model_lock_key` verified equal to the receipt's (`gguf-verify.log`).
- **Feature cache**: `/home/chao/feat-cache/slurp-q4km` held **63 entries before and 63 after**,
  with an **UNCHANGED directory mtime** (`2026-08-17 21:08:20`), and the 60,948-line server log
  contains **zero** lines matching `encoding` — the campaign's standing proof that every audio
  feature was a cache hit across all four passes. The legacy `q4km` cache (34,350 entries, mtime
  2026-08-16) and the `audio2tool-q4km` cache (490 entries, mtime 2026-08-19) were both untouched.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; **zero** `__pycache__`/`*.pyc` under the
  frozen scoring package before and after.
- **Processes**: no orphan `llama-server` and no listener on 8080/8081 before the flight; the
  server was a child of this flight's own wrapper and exited with it; none running afterwards,
  ports free, GPU back to 270 MiB at idle clocks.
- **Tree**: clean at `1faccd8` at takeoff, during the flight, and at `client.close()`.
- **Zero-state check**: `runs/SAEA-PROBE-pcorrf-240` and `attempts/SAEA-PROBE-pcorrf-240` were both
  verified ABSENT in the pre-flight, so this is unambiguously a first attempt.

## 6. Exposure ledger

Row `SAEA-PROBE-pcorrf-240` keeps **`consumed = no`**. This flight spent the requests; the row is
consumed only when the single registered one-shot read (`analysis.pcorrf_read`) executes. A FLOWN
note recording this attempt, its spend and its binding hash was appended to the row's own note
cell by `launcher/update_ledger.py`, which refuses unless exactly one row carries the anchor, the
cell count is unchanged, every other cell and every other line is byte-identical, and the
`consumed` cell reads `no` both before and after.

## 7. What the read must account for

Ingredients this flight supplies, without pre-empting the pre-read reachability statement the
registration's section 3 mandates:

1. **The K = 0 population is 20/60 for W1/W2/W3 and 14/60 for W4.** Those samples are untouched by
   construction — on those samples W1 and W2 both render the bare A3 roster, so their prompts are
   byte-identical to each other, and W3 flies true zero-supply. Per-sample
   Δ₁ = SLU-F1(W1) − SLU-F1(W2) on those 20 is therefore a byte-identical resend, the case for
   which P-KEY measured |ΔF1| of exactly 0.0000 — the floor the registration cites to keep its
   equivalence branch reachable. The **common denominator for a mechanism claim is therefore 40,
   not 60** — the read must state that before reporting Q-1, and the paired cluster bootstrap
   clusters on all 60 sample ids regardless.
2. **W1 and W2 carry the identical per-sample entry count** (61 entries each, distribution
   identical arm for arm), so the control is dose-matched, not merely content-shuffled.
3. **W3's dose is 61 entries total against the cited A3's 100 entries per sample** — that is the
   ~1% dose the Q-2 dose-efficiency clause is about, and Q-2 is a **cross-session** comparison
   against the pinned constant A3 = 0.5961, so the ±0.013 drift bound travels with the verdict.
   (This receipt deliberately never writes any of the registration's verdict tokens, so the
   archive's own read guard can grep for them literally and expect zero hits.)
4. **W4 carries no clause** and is descriptive only: 120 entries, mean 2.00, max 7, 14 samples at
   K = 0. The registration makes contamination load-bearing for W4 specifically.
5. **The mandatory dual measurement still has to be computed by the read, not inferred from here.**
   This receipt reports how many corrective entries were built and sent; it reports nothing about
   which of them the core emitted. Recovery and contamination are both read-side quantities.
6. **Ceiling accounting**: calls and metered audio are inside their ceilings; the GPU-hour column
   overshoots on the server-alive wall measure by 0.0128 h for the reason set out in section 3.
   The read should carry that disclosure forward rather than restate the spend as clean.
7. **No gold entered this flight anywhere.** The corrective content is percept-keyed and
   train-mined; the AST guard, the ontology-miner ban and the tri-derivation hash all fired, and
   there is deliberately no gold zero-overlap filter — a corrective entry MAY equal gold, which is
   the whole point, and the read's recovery measurement is what turns that into a finding.

## 8. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the flight (env, binding, identity, pre-flight, launcher, post-flight, ledger update, wrappers, syntax and suite gates) |
| `session-precheck.log` | session-start environment probe (GPU, caches, orphans, ports, disk, absent run dir) |
| `preflight-pytest.log` | the full suite, run once on a quiet machine before any core contact |
| `collect-delta.log` | suite-count reconciliation between `5c3e0fa` and `1faccd8` (see section 5) |
| `binding.log` | the offline binding step's own output |
| `corrective-binding-stats.json` | STRUCTURAL binding record (per-arm K distributions, K=0 ids, donor breadth). The full corrective table carries percept-selected supply text and stays in the attempt dir, never in Git |
| `preflight.log` | pre-flight (guards, split identity, roster, media, binding invariants, packet rendering dry run, legality, ledger, plan, budgets, absent run dir) |
| `gguf-verify.log` | binary + per-file GGUF sha256 against the runtime receipt AND the umbrella lock |
| `flight.log` | operational flight log (request index, arm, latency, response LENGTH only) |
| `postflight.log` | post-flight structural verification |
| `gpu-accounting.log` | the three GPU-hour measures, their timeline, and the overshoot disclosure (section 3) |
| `flight-receipt.json` | the launcher's own receipt (identity, cost, per-arm counts, binding stats, session pins) |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle |
| `session-receipt.json` | the llama-server session receipt |
| `MANIFEST.sha256` | sha256 over every file above |
