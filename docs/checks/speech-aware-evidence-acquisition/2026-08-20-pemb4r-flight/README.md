# P-EMB-4R multi-model kNN retrieval routing — FLIGHT RECEIPT (2026-08-20)

Registered probe `SAEA-PROBE-pemb4r-4100`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md`. Machinery:
`rails.probes.pemb4r_flight` (landed at `a407d03`), flown at study commit
`1eeea14`, tree clean throughout.

**All seven embedding arms and the retrieval plan flew. C-DECODE did NOT** — it was refused
fail-closed because it would have breached the registered metered-audio ceiling. Zero
frozen-core contacts were made. See §6 for the arithmetic and the proof.

**This flight produced no read.** Every vector and the retrieval plan
were written to the data root for the separately-registered one-shot read mission
(`analysis.pemb4r_read`) and were never scored here. Everything in this directory is
operational, structural, or CONSTRUCTION metadata: contact counts, dims, per-vector sha256,
latencies, session pins, budget totals, candidate-set SIZES and the gold-free winner proxy the
registration itself requires be disclosed. No accuracy, no recall, no vote, no gold comparison.
The frozen 60's devel gold was never loaded — machine-checked at every entry point by
`rails.probes.pemb4r_flight.assert_never_accesses_frozen_60_gold`, an AST guard scoped to
`.scenario`/`.action`/`.entities`/`.intent`.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-pemb4r-4100` |
| Attempt | `attempt-20260820T181837Z-3e6c8f` |
| Status | `COMPLETED-EMBEDDING-ARMS-C-DECODE-CEILING-BLOCKED` |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb4r-4100/attempt-20260820T181837Z-3e6c8f` |
| Study commit | `1eeea14`, tree clean at takeoff and at landing |
| Config hash | `3a46eb469d82b46481c501e1293d740fcd2e83c318e94c122d5f279a8bfbecd4` |
| Protocol hash | `3a46eb469d82b46481c501e1293d740fcd2e83c318e94c122d5f279a8bfbecd4` (= this run's config hash) |
| Binding config sha256 | `a193f63422ae4c990911752f3d14f37400c57d73cc4908af84d698dd3ccce17a` (pinned `a193f634…ce17a`) |
| Bank manifest sha256 | `5f48895107d715a7eae2954fe56f833455d33df3d6527e3643a0b0c924f5b112` (pinned `5f488951…f5b112`) |
| Split identity | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |
| Umbrella lock sha256 | `9064bde89d4248fd80c9c2f93c2a9c276a454eadbb1aa7d529671118961371b1` |
| Attempts | **one**; 4031 contacts spent |

## 1. Spend against the registered ceilings

| Basis | Actual | Registered ceiling | Headroom |
|---|---|---|---|
| Model/tool calls | **4031** | 4500 | 469 |
| Metered speech audio-seconds | **560.778** | 700 | 139.222 |
| GPU-h — per-call measured-equivalent | **0.1737** | 0.5 | 0.3263 |
| GPU-h — GPU-active occupancy | **0.2566** | 0.5 | 0.2434 |
| GPU-h — server-alive wall | 0.3448 | *recorded, never gates* | — |

The GPU accounting basis is the P-CORR-F section-8 pre-read adjudication ruling, carried
forward verbatim by `rails.probes.pemb4r_flight.assert_gpu_hours_within_ceiling`: the ceiling is
checked against **per-call measured-equivalent** and **GPU-active occupancy**; server-alive wall
is recorded but never gates. That ruling's own FORWARD RULE was applied literally — see §6.

## 2. Arms flown

Each model embeds its own 900-row key bank exactly ONCE; the two arms of a model share it.

| Arm | Model | Query | Dim | Bank contacts | Query contacts | Mean latency (s) |
|---|---|---|---|---|---|---|
| A-LCO3 | lco3 | audio | 2048 | 900 | 60 | 0.2544 |
| T-LCO3 | lco3 | T0 transcript | 2048 | (shared) | 60 | 0.0161 |
| A-LCO7 | lco7 | audio | 3584 | 900 | 60 | 0.6247 |
| T-LCO7 | lco7 | T0 transcript | 3584 | (shared) | 60 | 0.0222 |
| A-GLAP | glap | audio | 1024 | 900 | 60 | 0.0145 |
| T-GLAP | glap | T0 transcript | 1024 | (shared) | 60 | 0.4599 |
| T-QW | qw | T0 transcript | 1024 | 900 | 60 | 0.0114 |

Per-model bank vector sets (sha256-verified on every load):

| Model | Bank vectors | Dim | Distinct vector sha256 |
|---|---|---|---|
| glap | 900 | 1024 | 900 |
| lco3 | 900 | 2048 | 900 |
| lco7 | 900 | 3584 | 900 |
| qw | 900 | 1024 | 900 |

## 3. Gates

| Gate | Outcome |
|---|---|
| (a) LCO-7B server sanity | `OK` — measured dim **3584**, GGUF-declared 3584, agree = True |
| (b) GLAP import + audio-path sanity | `OK` — text+audio sanity succeeded (text dim 1024, audio dim 1024) |
| (c) POOLING-DIFFER [lco3] | `pooling_override_present = True` — 2 boots, 2 contacts, dim 2048; scope tag applies to ['a-lco3', 't-lco3'] |
| (c) POOLING-DIFFER [lco7] | `pooling_override_present = True` — 2 boots, 2 contacts, dim 3584; scope tag applies to ['a-lco7', 't-lco7'] |
| (d) encode-only machine check | `PASS` over 4 pinned modules, including `rails.probes.pemb4r_flight` |
| (e) cascade/T0 source | `COMPLETE` — 60/60 T0 transcripts, registry sha256 `f8f6426aeb0eb84c…` |

## 4. Determinism samples (sha256 equality only)

| Session | Kind | Dim | Byte-identical | Contacts |
|---|---|---|---|---|
| lco3-last | audio | 2048 | **True** | 1 |
| lco7-last | audio | 3584 | **True** | 1 |
| qw | text | 1024 | **False** | 2 |

Every jitter vector pair is persisted on the data root (`<model>-jitter-vectors.json` in the run
dir) so `analysis.pemb4r_read` can derive the measured repeat-δ the registration's own
argmax-stability statement needs. This flight evaluated no tolerance. Two facts the read must
carry: GLAP is in-process with no server session at all, so registration section 6's
per-server-session rule does not reach it — **GLAP has no measured repeat-δ, and `t-glap` is the
winner arm**; and the planned C-DECODE identical-prompt resend at `-np 4` was never flown,
because C-DECODE was never flown (§6), so this flight contributes **no** generation-side
determinism evidence and the P-CORR-F resend-divergence finding stands unre-tested here.

## 5. Retrieval plan (flight-side, gold-free)

- Written to `$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb4r-4100/retrieval-plan/retrieval_plan.json`
- **sha256 `7150c6b3410de4cc883da7f5ef0798dd80e4beaf253037594e99ff8cf5cea768`**, schema `saea-pemb4r-retrieval-plan-v1`, K primary 5
- **Winner arm: `t-glap`** — selected by the GOLD-FREE proxy the machinery
  documents as a judgment call: *max mean_top1_cosine across all flown kNN arms (gold-free proxy; documented judgment call, ties broken by sorted arm_id)*

Retrieval is a PURE function of already-flown vectors plus the bank's own TRAIN-split VALUE
metadata, so it runs flight-side by the machinery's own design (registration section 3 item 8).
`analysis.pemb4r_read.verify_retrieval_plan_document` independently RE-DERIVES the same
retrieval from the same vectors and compares it field-by-field rather than trusting this
artifact.

Per-sample candidate-set SIZE distribution — construction metadata (how many DISTINCT labels
each retrieved set carries), never which label is right:

| Arm | mean top-1 cosine | K=5 sizes | K=3 sizes |
|---|---|---|---|
| a-glap | 0.128000 | 2→3, 3→18, 4→26, 5→13 | 1→2, 2→23, 3→35 |
| a-lco3 | 0.169990 | 2→2, 3→25, 4→24, 5→9 | 2→21, 3→39 |
| a-lco7 | 0.275342 | 2→38, 3→21, 5→1 | 1→13, 2→44, 3→3 |
| t-glap **(winner)** | 0.890102 | 2→3, 3→13, 4→24, 5→20 | 1→3, 2→16, 3→41 |
| t-lco3 | 0.670924 | 1→6, 2→5, 3→23, 4→14, 5→12 | 1→10, 2→22, 3→28 |
| t-lco7 | 0.596432 | 1→11, 2→13, 3→25, 4→10, 5→1 | 1→18, 2→31, 3→11 |
| t-qw | 0.758009 | 1→39, 2→10, 3→8, 4→3 | 1→47, 2→12, 3→1 |

## 6. C-DECODE — NOT FLOWN, registered ceiling would have been breached

**Status: `NOT-FLOWN-CEILING-BLOCKED`. Contacts made: 0.**

The seven embedding arms and the retrieval plan are complete. C-DECODE is not, and was
refused fail-closed rather than flown over the registered metered-audio ceiling.

**Why the transcript modality does not help.** `rails.core_client.FrozenCoreClient.complete()`
resolves `audio_seconds` from the payload BINDING for the named sample — including on the
text-only branch (`audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]`) —
and `core.model.adapter` charges exactly that per request, before the request leaves the
process. A C-DECODE pass over the frozen 60 therefore meters a **full corpus audio pass on
either modality**: the request is still, honestly, about that bound sample's `speech_ref`.
Neither the coordinator-ratified budget-forced text fallback nor the winner arm happening to
be a text arm (it is, `t-glap`) can reduce it.

| Quantity | Seconds |
|---|---|
| Already spent (7 arms + 12 gate contacts) | 560.778 |
| C-DECODE, 60 requests | 182.259 |
| C-DECODE determinism resend, 1 request | 3.038 |
| **Total if C-DECODE flew** | **746.075** |
| Registered ceiling | 700 |
| **Over by** | **46.075** |
| Headroom remaining | 139.222 |
| Requests affordable | 45 of 60 |

**Registration gap.** Registration section 5 reads 'Ceilings: <=4,500 calls; <=700 metered audio-seconds (3x182.26 planned); <=0.5 GPU-h.' 3x182.26 = 546.78 s is exactly the THREE audio embedding arms. The cost line never budgeted a metered pass for C-DECODE's own 60 frozen-core requests, which the machinery's accounting charges as a fourth pass. The ceiling and the arm set are therefore jointly unsatisfiable once all three audio arms fly -- a registration defect that can only surface at contact time.

**Action taken.** REFUSED to fly, fail-closed. No partial C-DECODE was attempted: 45 of 60 requests would fit the headroom, but a truncated closed-set decode is a different experiment than the one registered and would poison the paired comparison. Everything else this flight owes -- all seven embedding arms, all four banks, and the gold-free retrieval plan -- is complete and landed.

**What would unblock it.** An owner/coordinator amendment raising the registered metered-audio ceiling to >= 747 s (4 x 182.259 + 14 s of synthetic non-corpus gate clips = 746.08 s), or an explicit re-registration of how a frozen-core text-only request meters speech audio. On the calls and GPU axes there is ample room: 4031/4500 calls and well under 0.5 GPU-h. C-DECODE would then fly as a follow-on against a FRESH sibling attempt id (which the FrozenCoreAdapter requires in any case), reusing this attempt's own retrieval plan by hash.

**Proof that zero frozen-core contacts were made:**

- c-decode-responses.jsonl absent from the run dir
- c-decode-outputs.jsonl absent from the run dir
- no 'c_decode' block in this flight state
- the refusal came from FrozenCoreClient.__init__ (core.model.lifecycle._open_gate_and_attempt), strictly BEFORE any request could be built
- `session-q4km-core.server.log` carries **0** `POST /v1/chat/completions` lines across its
  49 lines: the session loaded the pinned q4km GGUF set, sat idle, and was torn down.

The q4km session was spawned before the refusal surfaced (the refusal comes from
`FrozenCoreClient.__init__`, which runs after `start_session`), so its receipt and log are
landed here in full. It is torn down, its port is free, and the GPU is idle — see
`postflight.log`.

**The P-CORR-F §8 forward rule was applied and is worth recording on its own.** The FULL
frozen-core gate — `assert_model_touch_allowed(plan, full_hash=True)`, including the q4km
GGUF attestation — ran BEFORE any server was spawned, together with the payload binding and
the whole `load_split("devel")` media pass. It completed in **83.2 s**
(`ran_before_spawn: true`), and the q4km session that followed loaded in **3.8 s** and was
resident for ~2 s. P-CORR-F's own attempt paid 959 s of cold GGUF hashing *while the server
held VRAM idle*, which is what put its Measure A over ceiling. Ordering the work this way
kept server-alive wall for the core session to seconds instead of minutes.

### 6a. Coordinator pre-contact ruling, recorded verbatim

Recorded in this attempt's flight state at `2026-08-20T19:09:12.462881+00:00`, when zero C-DECODE
generation contacts existed. The `cdecode` stage refuses fail-closed unless this block is
present and matches verbatim, so its presence is the flight-side record that the ruling
preceded the contacts.

> Coordinator pre-contact ruling 2026-08-20: if budget_forced fires, the registration's C-DECODE HELPS/HURTS clauses are NOT evaluable at the read (modality confound against the audio-modality FS-NONE comparator); C-DECODE then reports descriptively only. If the winner is a text arm, clauses evaluate as registered.

The condition it keys on (`budget_forced`) **did not fire**: the gold-free winner proxy chose
`t-glap`, a text arm, so the intended modality was already the transcript one. A separate,
unconditional fact is recorded in `c_decode_modality_decision`: the consumed P-FEW FS-NONE
comparator is **audio**-modality, so any transcript-modality C-DECODE mixes the
retrieval-shrunk label space with an observation change — independent of `budget_forced`.

## 6b. Corrections to the landed evidence

A defect that had already written a false number into this receipt, repaired in place and
disclosed rather than left standing. The launcher source archived under `launcher/` carries
the fix; its module docstring additionally lists two further defects the (unexercised)
C-DECODE path still has, so a follow-on fixes them deliberately.

- **`sessions[server_key='q4km-core'].contacts`**: recorded `61` → corrected to `0`.
  The cdecode stage's teardown block passed extra={'contacts': QUERY_N + 1} -- a HARDCODED expectation of the full C-DECODE pass plus its determinism resend -- rather than the proxy's own measured `flown`, and that teardown runs in a `finally`, so the value was written even though the stage refused at FrozenCoreClient construction and issued ZERO requests. Corrected to the measured truth. Independently corroborated by session-q4km-core.server.log, which carries 0 'POST /v1/chat/completions' lines, and by the absence of c-decode-responses.jsonl / c-decode-outputs.jsonl.
  *Scope:* recorded METADATA only -- no contact, vector, hash, budget total or durable spend is touched; the durable attempt store never counted these 61 (actual calls stay 4031).

## 7. Documented deviations

1. **POOLING-DIFFER ran sequentially, not concurrently.** The machinery's own
   `run_pooling_differ_gate` takes a LIVE `last_client` and a LIVE `mean_client` at the same
   instant — two resident llama-server sessions over the same weights. For LCO-7B that is
   2 × ~12.6 GB against 23.1 GB of free VRAM on this host: an OOM, not a gate. The archived
   P-EMB-3M precedent was carried instead (boot `last`, embed the synthetic clip, tear down,
   boot `mean`, embed the SAME clip, tear down, byte-compare the persisted vectors). The
   computation is identical — `last_vector.values == mean_vector.values`, the machinery's own
   one-line verdict — and the machinery was not modified; only the concurrency was.
2. **`planned_speech_audio_seconds` was declared at the registered ceiling (700), not at the
   machinery's own 547 default.** 547 is exactly three metered passes and admits no fourth;
   whether C-DECODE needed a fourth was not knowable until the gold-free winner resolved, and
   the launcher must not pre-empt that. Declaring the registered cell let the decision be made
   on measured remaining budget. It never authorized more than the registration already did —
   and in the event the ceiling refused anyway (§6).
3. **LCO-7B's `expected_dim` came from its GGUF header, read offline.** `EmbeddingClient`
   enforces a strict dim equality and LCO-7B has no proven-dim probe in this codebase, so the
   header's `qwen2vl.embedding_length = 3584` was read model-free in preflight purely to
   construct the client. The gate's verdict still came from the LIVE sanity embed's returned
   vector, which measured **3584** — agreement recorded in gate (a).
4. **No process-wide `SAEA_FEAT_CACHE_DIR`.** This flight runs two different audio encoders over
   the same 60 clips, so each session was handed its own `LLAMA_MTMD_FEAT_CACHE_DIR`
   (`slurp-lco3b`, warm from P-EMB-3M; `slurp-lco7b`, cold; `slurp-q4km` for the core). The
   launcher refuses to start if a process-wide override is set.

## 8. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the flight (env, identity, GLAP loader, launcher, wrappers, gates) |
| `preflight-pytest.log` | the full suite, run once on a quiet machine before any contact |
| `preflight-bank-binding-check.log` | bank double-derivation + binding/registry/ledger pins, model-free |
| `preflight-syntax-check.log` | instrument syntax + dry composition, zero contact |
| `preflight-rehearsal.log` | full launcher rehearsal against a TEMP root and MOCK clients |
| `takeoff-state.log` | takeoff environment probe (GPU, caches, ports, absent run dir, assets) |
| `flight.log` | operational flight log (contact index, kind, id, latency, dim, response LENGTH) |
| `flight-receipt.json` | the launcher's own receipt |
| `flight-state.json` | the staged flight state every stage extended |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config-values bundle |
| `attempt-state.json` | the durable attempt record |
| `session-*.receipt.json` / `session-*.server.log` | every llama-server session's pins and own log |
| `vector-manifest-summary.json` | per-model bank and per-arm query manifests: counts, dims, per-vector sha256 — never a component |
| `retrieval-plan-summary.json` | the plan's hash, winner, rule and candidate-set SIZE distributions |
| `c-decode-summary.json` | C-DECODE row/format counts — no response body (absent: C-DECODE not flown) |
| `c-decode-ceiling-arithmetic.log` | the model-free arithmetic that refused C-DECODE (§6) |
| `postflight.log` | post-flight structural verification |
| `MANIFEST.sha256` | sha256 over every file above |

Vectors, the retrieval plan body, and every C-DECODE response stay on the data root
(`$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb4r-4100/` and the run dir), per the
registration's own "vectors/bank manifests on the data root, hashes only in Git".

