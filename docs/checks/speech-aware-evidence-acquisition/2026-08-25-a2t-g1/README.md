# Audio2Tool stage G1 — **COMPLETE: BOTH ARMS LANDED, AND THE FIRST SIGNAL IS A MECHANISM NULL**

Date: 2026-08-25. Campaign row `SAEA-A2T-G1` (`docs/exposure-ledger.md`), registered at commit
`4e25ac68` **before any flight contact**. Authority:
`docs/readiness/2026-08-25-a2t-generality-campaign-plan.md` §§3.3–3.6, §7 (Amendment 1,
`468a4d67`) and **§8 (Amendment 2, owner ruling, `bb6d22ef`)**; machine-readable contract
`configs/experiment/a2t-g1-v1.json`.

> **OUTCOME.** Every prerequisite closed and every gate passed. The **M0 arm landed complete**
> (104/104 samples) and is scored. The **BLEND arm ABORTED on the registered in-flight
> decode-rate sentinel at loop contact 26 of 208** and never completed, so **no paired
> statistic, no comparison and no first-signal read of the paradigm exists**. Per the registered
> rail — *a sentinel trip STOPS THE MISSION; no later arm flies on a sick GPU* — the mission
> stopped there. Nothing was re-flown.
>
> **SUCCESSOR ATTEMPT (2026-08-25T11:48Z) — READ §8.** BLEND was re-flown once under the same
> row with §6's four fixes. It **tripped the same sentinel again**, and this time the added
> telemetry **attributed it**: the stall is a **memory-path stall under VRAM
> oversubscription**, and **throttling is refuted**. §§1–7 below describe attempt 1 and remain
> exactly as written.
>
> **THIRD ATTEMPT (2026-08-25T12:50Z) — READ §10. THE BLEND ARM LANDED COMPLETE.** The two-pass
> redesign kept the embedder sidecar out of every decode window and the arm flew 104/104 at a
> 22.47 ms/token decode median with no sentinel trip. **The paired first signal now exists and it
> is a NULL with a mechanism: 0 of 104 trajectories dispatched, so the byte-identical v1 cell is
> STRUCTURALLY INERT on this carrier.** §§1–9 describe attempts 1 and 2 and remain exactly as
> written.

## 1. The claim this campaign carries (Amendment 2 framing, no hedging)

**The locked POLICY CELL transfers BYTE-IDENTICAL. SERVING GEOMETRY IS DERIVED PER CARRIER BY
THE FIXED §8.1 RULE.** It is not an exception, not a deviation, and not a degree of freedom of
the method — it is the output of a mechanical, pre-registered derivation from the task contract,
applied uniformly to every arm and fixed before any result was seen.

### 1.1 The derivation, with its measured inputs

| step | value | source |
|---|---|---|
| M0 contract envelope | **13,236** text tokens | resident tokenizer, real runner/transport shapes |
| BLEND worst evidence envelope | **19,047** text tokens | same, at the locked fusion budget (m 5, c 2 × top_l 3 = 6) |
| speech allowance | 514 (plan) / **364 MEASURED** | measured from the promoted packets |
| output ceiling | **1,024** | the task's output SHAPE — a JSON call list — and the value A0 registered here |
| requirement per slot | **20,437** (measured) / 20,585 (plan basis) | worst envelope + speech + output reserve |
| slot width | **32,768** = `-c 65536 / -np 2` | smallest `-np` at unchanged `-c` with real headroom |
| margin | **+12,331** | measured |
| `-np 3` (smallest that clears at all) | +1,260 only | why `-np 2` |

The decisive cross-check: the two TEXT envelopes render **byte-for-byte the same counts** the
predecessor np8 receipt measured (13,236 / 19,047). The derivation moved the SERVING geometry
and never the prompt. `text_rendering_unchanged: true` in `prompt-fit-np2.json`.

### 1.2 The policy cell

`configs/policy/kb-policy-v1-dev100.json`, sha256
`d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919` — α .45, τ .65, recall
top-k 5, fusion m 5 / c 2 / top_l 3, rrf .5/.3/.2, TRAIN priors, boundary stage not flown,
facet-side admission with value vectors sealed, the f1060078 repair live. **Not one knob was
changed for this carrier**, proved key-for-key against the cell file, the composed fragment and
the launcher's own constants. The v2 delta retain-override is deliberately **not** carried.

*Pin note, recorded rather than silently re-pinned:* the DEV-1000 launcher pinned this file's
PRE-LOCK bytes (`0d36273e…`). Lock commit `d9fef537` added two ANNOTATION keys — `STATUS` and
`locked_at` — and edited nothing inside `knobs`.

## 2. What ran, in order

| stage | row | outcome |
|---|---|---|
| GPU preflight | — | SmartFanMode **3**, enforced **100 W**, clock lock re-asserted (SM 1,192–1,200 MHz) |
| SLURP np8 service stopped | — | SIGTERM, `forced` false, stop receipt `15c25ca0…9285`. **A later mission must respawn it.** |
| A2T np2 service spawned | — | unit `saea-np2-a2t-g1`, port 8090, session `SAEA-SN-Q4KM-NP2-BASE-A2T-G1-20260825T092000Z`, receipt `ee9a4849…c79e`, **2 slots at n_ctx 32,768** verified in its own startup log |
| packet materialization | `SAEA-SN-A2T-G1-PREPROCESS` | **104/104 packets promoted**, 104 encodes, 0 failures, 0.0 GPU-h |
| KB text embedding | `SAEA-SN-TOOL-A2T-KB-TEXT-EMB-PASS` | **12,601 content-facet vectors**, 12,603 tool contacts, resident decoder untouched |
| prompt fit | `SAEA-SN-MF-A2T-G1-PROMPT-FIT-NP2` | **PASS, margin +12,331** |
| ARM M0 | `SAEA-A2T-G1` | **LANDED**, 106 core contacts, 104/104 samples |
| ARM BLEND | `SAEA-A2T-G1` | **SENTINEL ABORT** at loop contact 26 |

Two prerequisites were discovered by measurement rather than assumed, and both are registered
rather than worked around:

1. **The A2T knowledge base carried NO vectors.** G0 was registered at zero contacts, so it
   computed a *lexical* ceiling and explicitly reported that no dense ceiling existed. BLEND's
   recall is a cosine sweep over content-facet vectors, so the arm could not fly until they were
   built. Value vectors were deliberately not produced (the locked cell seals them), saving
   ~12,601 tool contacts on material no arm may read.
2. **The warm legacy feature cache was written under the OLDER build.** All 104 items were warm
   in `audio2tool-q4km`, but those bytes came from the earlier A2T flights under featcache build
   `5d9dfcb5` while G1 serves under `04ccc72a`. They were **not** promoted; the pass re-encoded
   all 104 under the serving build into a separate cache directory.

## 3. ARM M0 — landed, and scored

`arm1-m0-mechanical-report.json` (sha256 `7e5e9223c48b1bc4…`), read `g1-read-m0-only.json`
(sha256 `67e9ee44c9aa9e61…`).

| | value |
|---|---|
| samples | 104 / 104, zero failed calls |
| core contacts | 106 (2 canary + 104 loop) |
| metered audio | 590.251 s |
| canary | **11.55 / 11.25 ms per token**, gate < 300 — PASS |
| sentinel | median **21.21**, p90 26.76, max 158.42 ms/token — no trip |
| prompt reuse | **97.2 %** (declared 1,414,648 tokens, evaluated 38,624) |
| wall | 80.7 s |

Scored against gold (frozen scorer `a2t-scorer-v1`, reused not reimplemented):

| | M0 on A2T-G1-104 | A0 on the parent 400 |
|---|---|---|
| tool accuracy | **0.5962** (62/104) | 0.5425 |
| exact match | **0.2788** (29/104) | 0.2425 |
| gap | **0.3173** | 0.3000 |
| empty-call rate | **0.1346** (14/104) | 0.1025 |
| mean slot F1 | 0.3766 | — |
| unparsed | 4 | — |

**The A0 comparison is an ANCHOR, not a result**: different population (the parent 400, not this
104-item subset), different serving geometry (`-c 49152 -np 1`) and a different llama.cpp build.
It is not paired, and at n=104 one sample is ≈1 pp.

Per tier, published whole:

| tier | n | tool acc | exact | gap | empty |
|---|---|---|---|---|---|
| tier1_direct | 13 | 0.6923 | 0.0769 | 0.6154 | 0.0769 |
| tier2_parametric | 13 | 0.6154 | 0.4615 | 0.1538 | 0.0000 |
| tier3_multi_intent | 13 | 0.4615 | 0.0000 | 0.4615 | 0.0769 |
| tier4_implicit | 13 | 0.3846 | 0.0769 | 0.3077 | **0.5385** |
| tier5_needle | 13 | 0.9231 | 0.3846 | 0.5385 | 0.0769 |
| tier6_correction | 13 | 0.7692 | 0.5385 | 0.2308 | 0.0000 |
| tier7_multiturn | 13 | 0.6154 | 0.6154 | 0.0000 | 0.1538 |
| tier8_intent_blending | 13 | 0.3077 | 0.0769 | 0.2308 | 0.1538 |

**What this establishes and what it does not.** It establishes that the §8.1 derived geometry
serves this carrier's bare direct decode end to end, and where the baseline sits on this subset.
It establishes **nothing** about whether the locked policy cell transfers — that is BLEND's
question and BLEND did not complete.

## 4. ARM BLEND — sentinel abort, verbatim

`arm2-blend-sentinel-abort.json`. Everything durable was flushed before the stop: 14 canary
trace records into their own sink, **78 partial main-loop records** into the main sink, the
embedder sidecar stopped SIGTERM `forced` false with its own stop receipt, the core client
closed with its receipt, the resident decoder **left up and never stopped**.

Gates that passed before the abort: composed hash, policy-cell pin, §8.1 derivation, subset
receipt, promotion receipt, snapshot + 151 label identities, decontamination (0 overlap),
content-facet vectors `00a7ebe9…`, packet bindings, both f1060078 repair probes, the dry check,
the AttemptStore sizing guard, and the **canary — 11.85 / 13.26 ms per token, and byte-identical
to the M0 arm's recorded authority** (within-campaign continuity confirmed).

> **VERBATIM.** `in-flight decode-rate sentinel TRIPPED: rolling median 1171.24 ms/token over
> the last 8 observed generation rows exceeds the registered abort threshold 1000 ms/token;
> window [24.94, 18.9, 1503.75, 1025.45, 1494.38, 922.3, 1493.01, 1317.03]`
> (surfaced wrapped as an `ExecutionError` from `agent_contact_0`.)

**Exact BLEND spend**: **28** frozen-core contacts (2 canary + 26 loop), **73.633** metered
audio seconds, **27** embedding tool contacts, 372,659 prompt tokens, 726 completion tokens,
221.5 s of contact latency, 204.7 s wall. Attempt ceilings 220 core / 110 tool were never
approached.

### 4.1 The collapse, measured

Server-log generation rates ran **11.7 – 25.6 ms/token for the first ~24 loop contacts**, then
collapsed abruptly and did not recover:

```
...  24.94 | 18.90 | 1503.75 | 1025.45 | 1494.38 | 922.30 | 1493.01 | 1317.03
```

The interleaved *prefill* rows degraded too, but far less: from 1.3 – 1.9 ms/token to 17.9 –
21.0. **Decode slowed ≈75×; prefill ≈13×.**

### 4.2 What the evidence says, and what it does not

Measured facts:

- **VRAM occupancy.** M0 (no sidecar) 21,254 – 21,288 MiB. BLEND (sidecar up) **24,065 – 24,125
  MiB of 24,463** — 98.4–98.6 % of the card, and already at that level with 0 busy slots
  *before* the loop. After the sidecar stopped, 21,224 MiB. The three-point difference attributes
  ≈**2,841 MiB** to the CPU embedder sidecar: it runs `-ngl 0`, but it is the same CUDA-enabled
  binary and still takes a device allocation.
- **But VRAM occupancy alone does not explain it.** The landed DEV-1000 BLEND arm reached
  `peak_vram_mib` **24,129** with the same sidecar and ran 1,340 generation rows at median 54.94
  / max 202.47 ms/token without tripping. Occupancy at this level is the normal BLEND state on
  this host.
- **Throttling.** Windows `clocks_throttle_reasons.active` reads `0x4` (**SW Power Cap**) after
  the abort. SmartFanMode stayed 3 and the enforced limit stayed 100 W throughout. This arm
  followed ≈14 minutes of sustained full-host CPU load (104 encodes plus 12,601 CPU embeddings
  at 16 threads) on a 100 W-capped laptop part.
- **The asymmetry.** Memory-bound decode degrading ≈75× while compute-bound prefill degrades
  ≈13× is more consistent with a memory-path stall than with a uniform clock collapse; a pure
  clock collapse would slow both roughly proportionally.

**Two candidate mechanisms remain, and this mission does not separate them**, because the
registered rail stops the mission rather than letting it experiment on a sick GPU. The
launcher's resource sampler records memory and utilization but **not** `clocks.sm` or throttle
reasons, so the one series that would separate them was not captured. That is a concrete,
cheap gap to close.

### 4.3 One further measured fact, useful to the next mission

Of the 26 BLEND contact-0 (direct decode) responses that did fly, **22 of 26 are byte-identical
to the M0 arm's response for the same sample; 4 diverge** — at temperature 0, on one build, one
geometry, one service instance. The registered canary pair matched exactly. This is the
program's known multi-slot decode-variance channel showing up on this carrier, and it bears
directly on §6's recommendation.

## 5. Mechanics verdict, gate by gate

| gate | verdict |
|---|---|
| G0 reachability (inherited) | PASS — lexical ceiling@5 0.7925 vs A0 0.5425 |
| packet materialization | **PASS** — 104/104 promoted, re-encoded under the serving build |
| KB vectors | **PASS** — 12,601 content facets, values sealed |
| prompt fit under the derived geometry | **PASS** — margin +12,331; text envelopes unchanged |
| decode-speed canary | **PASS** both arms (11.25 – 13.26 ms/token) |
| canary hash authority | **PASS** — established by M0, matched by BLEND |
| GPU preflight | **PASS** — SmartFanMode 3, 100 W, clock lock |
| AttemptStore sizing guard | **PASS** both arms |
| trace-sink isolation | **PASS** on M0; canary sink isolated on BLEND, partial main flushed |
| M0 arm completion | **PASS** — 104/104 |
| in-flight decode-rate sentinel | **TRIPPED on BLEND** — mission stopped |
| dispatch decomposition / branch-only replay / retain == direct-label-recovered | **NOT REACHED** — they are computed at BLEND landing |
| paired first signal | **NOT REACHED** |

## 6. Recommendation for G2

**Do NOT proceed to the unexposed tier yet.** G1's mechanics half passed and its first-signal
half was never reached; entering G2 now would spend an unexposed 400-item tier on machinery whose
BLEND arm has never completed a single full loop on this carrier.

What must change first, in order:

1. **Instrument the sentinel's blind spot.** Add `clocks.sm`, `clocks.max.sm`, `power.draw` and
   `clocks_throttle_reasons.*` to the launcher's resource sampler. One line of telemetry
   separates the two candidate mechanisms in §4.2 and costs nothing.
2. **Take the CPU embedder out of the GPU loop.** BLEND's query text is the trajectory's own
   direct-decode answer, and the M0 arm has already flown and landed exactly that decode over
   exactly this population. Precompute the query vectors offline from the landed M0 texts, then
   at runtime hash the flown direct text against the precomputed one and **fail closed on
   mismatch, falling back to a live embed only for the divergent minority**. §4.3 measured that
   minority at 4 of 26 (≈15 %). This removes ~85 % of the in-loop tool contacts and ~2.8 GB of
   VRAM contention, and it is a serving change, not a policy change.
3. **Give the GPU a cold start.** Do not run a BLEND arm immediately after a sustained
   full-host CPU pass. Sequence: CPU prep → idle/settle → GPU arm.
4. **Then re-fly BLEND on THIS exposed subset**, under a fresh attempt of the same registered
   row, and only if it completes with the mechanism invariants holding does G2 open.

Nothing in this report licenses a generality claim, a superiority claim, test contact, a knob
change, or Stage-3 activity.

## 7. Artifacts

| artifact | sha256 |
|---|---|
| `prompt-fit-np2.json` | `0c77812d9439b6a7d6d3ff0227fc27924f617245d1ec9a0cbca20960f090946b` |
| `preprocess-report.json` | see the row; promotion receipt `be07c69c030f…18bc` |
| `arm1-m0-mechanical-report.json` | `7e5e9223c48b1bc457b2b02cb54050d208d717b376326ab5061da8847366ab37` |
| `g1-read-m0-only.json` | `67e9ee44c9aa9e6185179a91200e850809ae368a709097f354892ce3165bbc8c` |
| `canary-hashes.json` | this campaign's own canary authority |
| `arm2-blend-sentinel-abort.json` | the verbatim stop record |
| subset receipt `docs/receipts/a2t/A2T-G1-104.json` | `b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db` |
| KB vectors receipt `docs/receipts/knowledge/a2t-kb-size-full-embeddings.json` | npz `00a7ebe9b8325ffc2c7b8e45ac4f0c8475b2d3e76994cc0f539f7b5ad5740f45` |

Code: `launcher/launch_a2t_g1.py`, `scripts/build_a2t_g1_subset.py`,
`scripts/a2t_g1_preprocess.py`, `scripts/a2t_kb_text_embedding_pass.py`,
`scripts/a2t_g1_prompt_fit_np2.py`, `scripts/a2t_g1_read.py`.
`rails/` and `core/` are untouched: `rails/kb_policy.py`'s last commit is still `f1060078`.

---

## 8. BLEND successor attempt (attempt 2) — **SENTINEL TRIPPED AGAIN, AND THIS TIME IT IS ATTRIBUTED**

Registered under the same row `SAEA-A2T-G1` at commit `70dceb90` **before any contact of it**.
Launcher `launcher/launch_a2t_g1_blend_attempt2.py`; attempt
`attempt-20260825T114856Z-a2tg1blend`; stop record `arm2-blend-sentinel-abort-attempt2.json`
(attempt 1's record is preserved unmodified as `arm2-blend-sentinel-abort.json`); attribution
`arm2-blend-attempt2-mechanism-verdict.json`; preflight `gpu-preflight-blend-attempt2.json`.

> **VERBATIM.** `in-flight decode-rate sentinel TRIPPED: rolling median 1005.76 ms/token over
> the last 8 observed generation rows exceeds the registered abort threshold 1000 ms/token;
> window [1024.68, 965.02, 964.32, 845.64, 986.84, 1118.13, 1187.69, 1496.65]`
> (surfaced wrapped as an `ExecutionError` from `agent_contact_0`; the launcher's own re-read of
> the window at the stop was `[965.02, 964.32, 845.64, 986.84, 1118.13, 1187.69, 1496.65,
> 1230.22]`, rolling median 1052.49.)

**Exact spend**: **62** frozen-core contacts (2 canary + 60 loop), **277.177** metered audio
seconds, **99** embedding tool contacts (92 offline precompute + 7 in-loop live/jitter), 826,584
prompt tokens, 2,030 completion tokens, 459.9 s contact latency, 397.1 s wall, 253.2 GPU-seconds,
peak VRAM 24,125 MiB. Durable-first executed in full: 14 canary trace records into their own
sink, **180 partial main-loop records** flushed into the main sink, sidecar #2 stopped SIGTERM
`forced` false, core client closed with its receipt, resident decoder left up.

**Campaign cumulative**: **196 / 400** core contacts, **941.061 / 2,000** audio seconds,
**126 / 200** embedding tool contacts.

### 8.1 What the four fixes did

| fix | outcome |
|---|---|
| 1 — sampler records `clocks.sm`, `power.draw`, `clocks_throttle_reasons.*` | **WORKED.** 161 phase-tagged samples at 3 s. §8.2 exists because of it. |
| 2 — query vectors precomputed offline from M0's landed direct texts | **HIT RATE 0.9138** (53 hits / 5 misses / 58 lookups) against the registered 0.85 expectation — 53 in-loop tool contacts avoided. **Then its own fallback undid it: see §8.3.** |
| 3 — cold start before the canary | **WORKED, and eliminated its own hypothesis.** Host entered the canary at 10.18 W / 43 °C / 0 % util and the canary passed at 12.32 and 11.65 ms/token. Attempt 1's "no cold start" explanation is dead: this attempt had one and stalled anyway. |
| 4 — same row, fresh attempt, run-cumulative plan | **WORKED.** Ceilings 220 core / 170 tool; all three fail-closed guards asserted at takeoff; 134 + 220 = 354 ≤ 400, 27 + 170 = 197 ≤ 200. |

Every pre-takeoff gate passed again: composed hash `df6bf4d4…38f9`, v1 cell pinned at
`d68afd2c…a919` proved key-for-key, §8.1 derivation (32,768 per slot against 20,585 required,
margin +12,183), subset and promotion receipts, snapshot + 151 label identities, content-facet
vectors `00a7ebe9…0f45`, packet bindings for all 104, both `f1060078` repair probes, the dry
check against all 25,519 protected payloads, the frozen-core GGUF attestation (51.7 s), the
AttemptStore sizing guard, trace-sink isolation, and the **canary — 12.32 / 11.65 ms/token and
byte-identical to the M0 arm's authority on both samples**.

### 8.2 The attribution — **memory-path stall, throttling refuted**

The stall's onset coincides with exactly **one** change and nothing else. The CPU embedder
sidecar re-spawned on the first query-vector cache miss (`tier1_direct:001432`, ready
11:52:45.96Z) and, by the launcher's lazy design, **was left up for the rest of the loop**.

**VRAM stepped at that instant and stayed there:**

| | before sidecar #2 | after sidecar #2 |
|---|---|---|
| `memory.used` | 21,288 MiB | **24,125 MiB** (98.6 % of 24,463) |
| step | — | **+2,837 MiB** |
| main-loop samples at that level | — | **106 of 122** |

**Decode collapsed; prefill barely moved** (rates split at that boundary in the raw server log):

| | n | min | median | p90 | max |
|---|---|---|---|---|---|
| decode ms/token BEFORE | 46 | 11.65 | **19.54** | 25.27 | 66.56 |
| decode ms/token AFTER | 16 | 106.75 | **997.25** | 1,313.99 | 1,572.50 |
| prefill ms/token BEFORE | 46 | 1.18 | **1.56** | 1.91 | 82.35 |
| prefill ms/token AFTER | 16 | 1.41 | **3.76** | 12.19 | 18.82 |

**Decode slowed ≈51×; prefill ≈2.4×.** A clock or power collapse would slow both roughly
proportionally. Attempt 1 measured the same asymmetry (≈75× against ≈13×) and could not
attribute it.

**The GPU was not throttled while it stalled.** Through the 106 high-VRAM main-loop samples the
SM clock sat at a **2,482 MHz median — against the 2,500 MHz lock ceiling, i.e. not reduced at
all** — with median draw **45.0 W of a 100 W enforced cap**, **55 °C** median (59 °C max), GPU
utilization pinned at **100 %**, and **no hardware or thermal flag ever active**. Full clocks,
half the power budget, cool, 100 % busy, and roughly one token per second is the signature of a
device spinning on memory transfers.

**Throttling is disclosed, not hidden:** `clocks_throttle_reasons.sw_power_cap` was active on
**7 of 122** main-loop samples (5.7 %), at power excursions toward the cap (max 97.9 W). That is
a real observation and it is not the mechanism.

**A separate benign preflight finding, recorded so a later mission does not misread it.**
`nvidia-smi` reported **0 MiB used** on both the Windows host and inside WSL while the np2
service was up and healthy ~68 minutes after its last request — the host had evicted the
resident weights across the idle window. Cost: the weights re-paged during the canary's first
prompt evaluation (82.35 ms/token prefill on canary sample 1 against 3.91 on sample 2) and the
canary still passed at 12 ms/token generation. **An idle 0 MiB reading is not a dead service.**

### 8.3 The defect FIX 2 actually has

The precompute did its job: **91.4 % hit rate**, 53 in-loop tool contacts avoided, and the five
misses are the program's known multi-slot decode-variance channel (`tier1_direct:001432`,
`tier2_parametric:004826`, `tier4_implicit:001513`, `tier4_implicit:003949`,
`tier5_needle:000061`). Every spawn and stop proved bit-identical jitter numerics against the
first spawn, so live-embedded misses are provably in the same numeric space as the precomputed
vectors, and the policy read the embedding of the FLOWN text on every trajectory either way.

**But the miss path spawns the sidecar and never stops it.** One miss at loop contact ≈12 of
208 restored the exact attempt-1 VRAM condition for the entire remaining loop. **The precompute
removed 91 % of the in-loop tool contacts and 0 % of the VRAM contention**, because contention
is a function of whether the process is *resident*, not of how many contacts it serves.

### 8.4 Mechanics verdict, gate by gate (successor attempt)

| gate | verdict |
|---|---|
| composed hash / policy-cell pin / §8.1 derivation | **PASS** |
| subset, promotion, snapshot, 151 label identities, decontamination | **PASS** |
| content-facet vectors, packet bindings, both `f1060078` repair probes | **PASS** |
| frozen-core GGUF attestation | **PASS** (51.7 s) |
| AttemptStore fail-closed sizing guard | **PASS** |
| trace-sink isolation (canary sink namespaced, zero record-id overlap) | **PASS** |
| decode-speed canary + canary hash authority | **PASS** — 12.32 / 11.65 ms/token, byte-identical to M0 |
| FIX 1 telemetry | **PASS** — 161 phase-tagged samples, all ten added series present |
| FIX 2 precompute hit rate | **PASS** — 0.9138 against a registered 0.85 |
| FIX 3 cold start | **PASS** — and the hypothesis it tested is eliminated |
| FIX 4 registration, ceilings, run-cumulative plan | **PASS** |
| in-flight decode-rate sentinel | **TRIPPED** at loop contact 60 — mission stopped |
| dispatch decomposition / branch-only replay / retain == direct-label-recovered | **NOT REACHED** |
| paired first signal | **NOT REACHED** |

## 9. Recommendation for G2, revised

**Still do NOT open G2**, and the reason is now narrow and mechanical rather than open.
Attempt 1 left "why did it stall" unanswered; attempt 2 answers it. What remains is a serving
bug with a known repair, not an unexplained instability.

1. **Stop the sidecar after every live embed.** A spawn costs 5.1 s and buys back 2,837 MiB. At
   the measured 8.6 % miss rate that is ≈9 spawn/stop cycles over 104 samples — ≈46 s of added
   wall time against a 51× decode collapse. This is one line of lifecycle in the launcher's miss
   path and it changes no policy.
2. **Or better, take the sidecar out of the loop entirely with a two-pass loop.** Pass 1 flies
   all 104 direct decodes with the sidecar down; one offline embed pass then covers every miss;
   pass 2 flies the evidence contacts. Flying with an inert query vector is *not* an option — it
   changes what the policy reads — so deferral, not omission, is the correct shape. Cost: 104
   extra prompt evaluations, all of them prompt-cache hits.
3. **Keep FIX 1 armed permanently.** It converted an unattributable abort into a one-variable
   diagnosis in a single flight, at zero contact cost.
4. **Then re-fly BLEND on this same exposed 104 under a fresh attempt of the same row** — and
   note that **the budget now binds, which is the one thing a third attempt cannot discover at
   takeoff**. Spent: **196 / 400** core, **941.061 / 2,000** audio-s, **126 / 200** tool
   contacts. **204 core contacts remain.** A full BLEND arm's *worst case* is 2 canary + 208
   loop + 1 resend = **211**, which exceeds 204 — so the launcher's own fail-closed sizing guard
   would **REFUSE TAKEOFF at zero spend**, exactly as designed. Its *expected* case at a ~50 %
   dispatch rate is ≈159 and fits comfortably. The next attempt therefore needs one of two
   things decided **before** it is built: an owner decision raising the campaign core cell, or a
   lower attempt ceiling registered with its basis stated (and the arm then meters against it).
   Tool contacts are the same shape: 126 spent of 200, so a third attempt's precompute-plus-miss
   budget must fit in 74. Only if the arm completes with the three mechanism invariants holding
   does G2 open.

Nothing in this section licenses a generality claim, a superiority claim, test contact, a knob
change, or Stage-3 activity. Gold was never opened; the 180 flushed partial records and 60
partial decodes are dead spend, disclosed and never re-read as results.

---

## 10. THIRD ATTEMPT — **THE BLEND ARM LANDED COMPLETE, AND THE FIRST SIGNAL IS A MECHANISM NULL**

Registered under the same row `SAEA-A2T-G1` at commit `4fa63514` **before any contact of it**.
Launcher `launcher/launch_a2t_g1_blend_attempt3.py` (git blob sha256 `78342cd660f5a0c6…0364d`,
commit `099884e4`); attempt `attempt-20260825T125051Z-a2tg1blend`; preflight
`gpu-preflight-blend-attempt3.json`; report `arm2-blend-mechanical-report-attempt3.json`
(sha256 `56bf0a7592d2b595…c0b520`); paired read `g1-read.json` (sha256
`2536f8666d87b315…8b0f2f`). Attempts 1 and 2 and their stop records are preserved unmodified.

> **OUTCOME.** Exit 0. **104 of 104 samples, 107 core contacts, the sentinel never tripped, and
> the co-residency invariant held on all 111 checks.** The paired first signal exists for the
> first time. **It is a NULL, and the null has a mechanism: the byte-identical v1 policy cell is
> STRUCTURALLY INERT on this carrier — 0 of 104 trajectories dispatched, so no trajectory ever
> received evidence.** The −1.9 pp paired tool-accuracy difference is **not** an effect of the
> method; every scored flip is attributed to the frozen core's own multi-slot decode-variance
> channel, proved below.

### 10.1 What the two-pass redesign was for, and whether it worked

Attempt 2 attributed its stall to VRAM oversubscription and named the defect exactly: the
query-vector miss path spawned the embedder sidecar and never stopped it, so one miss restored
the bad condition for the whole loop. This attempt removed the condition structurally.

| phase | sidecar | `memory.used` | GPU util | decode |
|---|---|---|---|---|
| canary (2 contacts) | DOWN | 21,224 – 21,288 MiB | 0 – 98 % | **12.32 / 11.47 ms/token** |
| PASS A (104 contacts) | DOWN | **21,288 MiB, all 21 samples** | 92 % median | median **22.47**, p90 27.58, max 73.94 |
| offline bridge (8 embeds) | **UP ALONE** | 21,288 → **24,125** → 21,288 MiB | **0 – 2 %** | no decode in flight |
| PASS B (0 evidence contacts) | DOWN | 21,288 MiB, all 85 samples | 0 % (CPU-bound recall) | no rows |
| resend (1 contact) | DOWN | 21,288 MiB | — | — |

The bridge row is the control that proves the diagnosis rather than assuming it: **the sidecar's
≈2,837 MiB device allocation appears exactly where attempt 2 said it would, and it costs nothing
because the GPU is idle underneath it.** Decode ran at a 22.47 ms/token median across all 104
Pass-A contacts against attempt 2's 997.25 median after its sidecar re-spawned — **a 44×
difference on the same host, same build, same geometry, same policy cell.**

**The invariant was asserted, not hoped for.** `SidecarCoResidencyGuard` ran **111 checks — 107
before individual frozen-core contacts and 4 at phase boundaries — with 0 violations**, by two
independent probes (the launcher's own live sidecar handle and a TCP probe of port 8082). The
bridge additionally proved the port free AND VRAM returned to 21,288 MiB against a 22,500 MiB
ceiling before Pass B was allowed to start.

**Throttling, disclosed as before and still not the mechanism.** `sw_power_cap` was flagged in
the pre-takeoff, pass-a, pass-b and resend phases. Pass A ran at a **93.4 W median of a 100 W
cap** at 1,192 – 1,687 MHz and 44 – 62 °C, and decoded at 22 ms/token throughout. One `clocks.sm`
sample in the pass-b window reads **63,487 MHz**, which is a driver/parse artifact and not a
measurement; it is recorded rather than dropped, and the phase median is 1,192 MHz.

### 10.2 The flight, in order

| stage | outcome |
|---|---|
| GPU preflight | SmartFanMode 3, 100 W enforced, clock lock re-asserted, 21,224 MiB baseline, **sidecar not running, port 8082 refused** |
| every pre-takeoff gate | PASS (composed hash, v1 cell key-for-key, §8.1 derivation margin +12,183, receipts, 151 label identities, decontamination, facet vectors, packet bindings, both `f1060078` probes, dry check over 25,519 payloads, GGUF attestation 50.4 s, AttemptStore two-pass sizing guard) |
| durable query-vector table | **95 vectors loaded, 0 tool contacts, sidecar NOT spawned** |
| canary | **PASS 12.32 / 11.47 ms/token, byte-identical to the M0 authority on both samples** |
| PASS A | **104/104 in 62.6 s**; 93 texts byte-identical to the landed M0 text, **11 divergent** |
| offline bridge | 8 texts embedded (81 of 89 distinct already covered, coverage **0.9101** against a registered 0.9138), sidecar up 5.3 s and stopped SIGTERM `forced` false, port free, VRAM returned |
| PASS B | **104 trajectories in 272.3 s; 104 contact-0s RESUMED at zero cost, 0 evidence contacts flown** |
| resend | flown, **byte-identical** to the M0 authority |
| trace isolation | zero record-id overlap across main (416), pass-a (728), canary (14), resend (7) |

**Exact spend: 107 frozen-core contacts (2 canary + 104 Pass A + 1 resend), 591.348 metered audio
seconds, 10 embedding tool contacts (8 bridge + 2 jitter), 1,427,941 prompt tokens, 3,760
completion tokens, 105.2 s contact latency, 0.02921 GPU active hours.** Inside the 135 core and
50 tool attempt cells. Prompt reuse **99.14 %**. **Campaign cumulative: 303 / 400 core contacts,
1,532.409 / 2,000 audio seconds, 136 / 200 embedding tool contacts.**

**The replay saved the flight.** 104 Pass-B contact-0s were resumed from Pass A's durable record,
each admitted only after the sha256 of the messages document the runner built was proved equal to
the sha256 Pass A recorded for that sample — 104 of 104 matched. Without it the arm's worst case
was 213 core contacts against 204 remaining, and the launcher's own guard would have refused
takeoff at zero spend.

### 10.3 The paired first signal — BLEND against the LANDED M0 on the same 104

Frozen scorer `a2t-scorer-v1`, reused not reimplemented; gold opened once over the sealed
population.

| | M0 (landed) | BLEND (attempt 3) | paired delta |
|---|---|---|---|
| tool accuracy | 0.5962 (62/104) | **0.5769 (60/104)** | **−1.92 pp**, CI90 [−4.81, 0.00], McNemar p 0.5 |
| exact match | 0.2788 (29/104) | **0.2692 (28/104)** | **−0.96 pp**, CI90 [−2.88, 0.00], McNemar p 1.0 |
| gap | 0.3173 | 0.3077 | −0.96 pp |
| empty-call rate | 0.1346 (14/104) | **0.1346 (14/104)** | **0.00 pp** |
| W→C / C→W (tool) | — | — | **0 / 2** |
| W→C / C→W (exact) | — | — | **0 / 1** |

Per tier, published whole — **six of eight tiers are identical to the sample**:

| tier | n | M0 tool | BLEND tool | Δ pp | M0 EM | BLEND EM | Δ pp |
|---|---|---|---|---|---|---|---|
| tier1_direct | 13 | 0.6923 | 0.6154 | −7.69 | 0.0769 | 0.0769 | 0.00 |
| tier2_parametric | 13 | 0.6154 | 0.6154 | 0.00 | 0.4615 | 0.4615 | 0.00 |
| tier3_multi_intent | 13 | 0.4615 | 0.4615 | 0.00 | 0.0000 | 0.0000 | 0.00 |
| tier4_implicit | 13 | 0.3846 | 0.3846 | 0.00 | 0.0769 | 0.0769 | 0.00 |
| tier5_needle | 13 | 0.9231 | 0.9231 | 0.00 | 0.3846 | 0.3846 | 0.00 |
| tier6_correction | 13 | 0.7692 | 0.7692 | 0.00 | 0.5385 | 0.5385 | 0.00 |
| tier7_multiturn | 13 | 0.6154 | 0.6154 | 0.00 | 0.6154 | 0.6154 | 0.00 |
| tier8_intent_blending | 13 | 0.3077 | 0.2308 | −7.69 | 0.0769 | 0.0000 | −7.69 |

**THE DELTA IS NOT THE METHOD, AND THAT IS CHECKABLE RATHER THAN ASSERTED.** Dispatched
trajectories: **0**. Evidence contacts flown: **0**. The policy supplied nothing to any contact,
so the two arms can only differ where the frozen core's own decode of the same prompt differed.
**11 of 104 Pass-A texts diverged from the landed M0 text. Both tool-accuracy flips
(`tier1_direct:001631`, `tier8_intent_blending:000441`) and the single exact-match flip
(`tier8_intent_blending:000441`) fall inside those 11**, and all three flips are C→W. The paired
delta is the program's known **multi-slot decode-variance channel**, measured here at 10.6 % text
divergence and 1.9 pp of score noise on this carrier, and it must not be read as the method
helping or hurting.

### 10.4 The mechanism verdicts, including the one that failed

| invariant | verdict |
|---|---|
| dispatch decomposition closes over the population | **PASS** — 104 retained + 0 dispatched = 104; `dead_direct_dispatched` 0 equals `dispatched` 0 |
| dispatch matched the pre-registered projection | **PASS** — projected 0, flown 0 |
| branch-only replay (supply equals the flown fusion decision) | **VACUOUS, NOT PASS** — 0 trajectories branched, so it had nothing to check, and it is reported as vacuous rather than as a pass |
| **decision replay** (the retain-or-dispatch BRANCH re-derived offline per trajectory) | **PASS — 104 of 104 replayed, 0 mismatches** |
| retain == direct-label-recovered | **FALSIFIED on this carrier — 104 retained against 89 recovered** |
| co-residency (no sidecar while a decode is in flight) | **PASS — 111 checks, 0 violations** |
| replayed contact 0 is byte-identically the flown contact 0 | **PASS — 104 of 104 messages digests matched** |
| decode-speed canary + canary hash authority | **PASS** — 12.32 / 11.47 ms/token, byte-identical to M0 |
| identical-prompt resend | **PASS — byte-identical** |
| in-flight decode-rate sentinel | **NO TRIP** — 104 rates, median 22.47, max 73.94 ms/token |

The branch-only replay being vacuous is why a **decision replay** was added and run: it re-derives
each trajectory's retain-or-dispatch branch offline, from that trajectory's OWN landed query
vector and OWN flown direct text, through `rails.kb_policy`'s own pure functions, and requires it
to reproduce the controller's flown branch. It reproduced all 104 with zero mismatches, at zero
contacts, with gold never consulted.

**`retain == direct-label-recovered` IS FALSIFIED HERE, AND THE FALSIFICATION IS THE FINDING.**
The registered expectation — under the v1 cell a trajectory dispatches exactly when the normalizer
recovers no label — assumes the fuser actually selects something. On this carrier it never does,
so all 15 label-free trajectories retained instead of dispatching. The invariant was never a
theorem; it was an empirical regularity of SLURP, and Audio2Tool breaks it.

### 10.5 WHY nothing dispatched — the structural mechanism, measured

This is the payload of the attempt, and it is not a marginal miss.

| measurement over all 104 trajectories | value |
|---|---|
| recall returned nothing | **0** |
| best content-facet cosine, min / max | **0.7594 / 0.9572** |
| trajectories whose best content cosine clears tau 0.65 | **104 of 104** |
| trajectories with ZERO content facets in the top-m=5 rank window | **104 of 104** |
| fusion selected nothing | **104 of 104** |

**Content-facet RECALL is healthy — the cosines clear the admission threshold comfortably. What
never happens is ADMISSION.** The ranker scores `w_cos·cos + w_prior·prior + w_agree·agree` at
0.5 / 0.3 / 0.2, and on this knowledge base the prior-mass dimensions carry **unnormalized scores
of roughly 1.2 to 4.1** against a cosine of at most 0.96. Label and prior facets therefore occupy
the entire top-m=5 window the fuser admits over. The percept-admission gate reads **only
non-prior-mass dimensions**, and a label or prior facet has none — so `admitted()` is false for
every candidate, `admitted_facets` is empty, no value is ever selected, and every trajectory takes
the retain branch. Independently corroborated by the flown record of the two aborted attempts:
**86 BLEND trajectories, 86 direct-decode contacts, 0 evidence-decode contacts.**

**What this establishes.** The locked policy cell transfers byte-identical, and the §8.1 derived
geometry serves this carrier end to end — both were already true after M0, and this attempt adds
that the full BLEND machinery runs cleanly over 104 trajectories on this carrier. **What it also
establishes, and what G2 must not be allowed to discover the expensive way: on Audio2Tool the
cell's SUPPLY PATH NEVER FIRES.** Byte-identical transfer of the cell is not the same thing as
byte-identical transfer of the *behaviour*, and this carrier separates the two.

### 10.6 Recommendation for G2 — **do NOT open it**

Not for the previous reason. G1's mechanics half now passes completely and its first-signal half
is reached. The reason is that **G2 as scoped would spend an unexposed 400-item tier measuring a
policy that provably does nothing on this carrier**, and would return a null with wider error bars
and no more mechanism than this 104-item read already gives.

1. **The blocking question is a KNOWLEDGE-BASE / RANKER-SCALE question, not a campaign-size
   question.** The prior-mass dimensions are unnormalized relative to the cosine dimension, and on
   a knowledge base with 12,601 values and 151 tool labels that difference is large enough to
   evict every content facet from a top-m=5 window. Nothing about that is discoverable by flying
   more samples.
2. **Anything that fixes it is a KNOB CHANGE and is NOT authorized here.** Normalizing prior mass,
   raising `m`, or admitting on the content dimension separately would each make the supply path
   fire — and each would break the campaign's own central claim that the cell transfers
   byte-identical. That trade is an OWNER decision, not an implementer's.
3. **What is cheap and unauthorized-free**: this read already carries the diagnostic. A future
   owner-approved experiment can quantify the eviction directly (offline, zero contacts) by
   sweeping `m` and prior normalization against the landed vectors, and report at what setting a
   content facet first enters the admitted window.
4. **The two-pass launcher and its co-residency guard should become the default shape** for any
   arm that needs an embedder on this host. It converted a 51× decode collapse into a 22 ms/token
   flight at a cost of 104 prompt-cache-hit resumes and 7.2 s of bridge.

Nothing in this section licenses a generality claim, a superiority claim, test contact, a knob
change, or Stage-3 activity. `consumed` stays `no`. **The operational debt stands: the SLURP np8
service remains DOWN and must be respawned by a later mission before any SLURP arm flies.**

### 10.7 Artifacts

| artifact | sha256 |
|---|---|
| `launcher/launch_a2t_g1_blend_attempt3.py` (git blob) | `78342cd660f5a0c6d6886e2019d0877530dee2ddbcde23baba6338fabea0364d` |
| `dispatch-projection.json` | `c27b0be62bab33d0172a2611841ac48e9d31f98049591ace883b93bd6a9dcb36` |
| `gpu-preflight-blend-attempt3.json` | `8b28ae75ce8a8657f87bfadf611b287d6e2a9caa43139d0bd9bd4c167f19b958` |
| `arm2-blend-mechanical-report-attempt3.json` | `56bf0a7592d2b595da86dab84ad7c0ae8246d1afc150f4cb695f2c9efcc0b520` |
| `g1-read.json` (the paired read) | `2536f8666d87b3157ec909c4c43e4b318a9b8ccb7f2ea3cacb195265f98b0f2f` |
| Pass-A direct outputs (run dir) | `73e28511f419cd67b1721d829438f8c102e725e01243c9a9f000e00d92aadc9c` |
| bridge vectors (run dir) | `be63447edd56b97bdc3afa711cda9d40f8dd22b126f2f37bdbee1475b9d088a9` |
| core-client trace manifest | `94b8e63a595ba1406616c11ffcaa2e09a8d7eaa3ad9383d89f9180afc3b30165` |

Code: `launcher/launch_a2t_g1_blend_attempt3.py`, `scripts/a2t_g1_dispatch_projection.py`,
`scripts/a2t_g1_read.py`. **`rails/` and `core/` are untouched: `rails/kb_policy.py`'s last commit
is still `f1060078`**, re-verified live at takeoff.
