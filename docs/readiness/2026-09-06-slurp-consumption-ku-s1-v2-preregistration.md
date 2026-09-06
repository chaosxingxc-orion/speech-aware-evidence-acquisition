# SLURP consumption cell KU-S1 (BLEND-CL) — preregistration v2 (2026-09-06)

Supersedes section 6 of `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md`,
which **refused KU-S1 before registration** on three measured blockers. Enabler E6 removed all
three. This note registers the cell's roster, budget, comparator, analysis and decision rule, and
records the one thing that is still open — the retrieval query's signal — so that when MF-7 reports,
the only change to the cell is one pinned hash and one declared modality string.

| item | value |
|---|---|
| run id | `SAEA-SLURP-KU-S1-BLEND-CL-DEV1000-V1` |
| profile | `bounded-discovery-probe` |
| fragments | `configs/experiment/slurp-consumption-ku-s1-v2.json`, `configs/baseline/slurp-phase-blend-cl-v1.json`, `configs/policy/phase-direct-evidence-alpha-blend-v1.json`, `configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json`, `configs/dataset/slurp-speech-native-dev1000.json` |
| status | **REGISTERED, NOT FLYABLE.** `phase_supply.evidence.query_source.sha256` is the 64-f placeholder and `rails.phase_supply.load_sealed_vectors` will refuse it at preflight until MF-7 fixes the query embedder (section 3) |
| decision population | the unexposed **NEW500** |

## 1. The owner rule in force (2026-09-06), verbatim

> the retrieval QUERY must contain the speech signal. It may be speech plus an agent intermediate
> state (for example the speech plus the draft answer), but it can never be text-only.

Two consequences, both already executed:

1. **In code.** `rails.phase_supply` now refuses a text-only retrieval query. A `query_source`
   DECLARES its modality as the first token of `embedded_signal`, from the fixed vocabulary
   `QUERY_SIGNAL_MODALITIES = ("speech", "speech+state")`, followed by `:` and the free English
   description. `PhaseSupplySpec.validate` refuses anything else before a vector file is opened,
   and `FlightRuntime._assert_phase_supply_is_legal_for` applies
   `assert_phase_supply_queries_carry_speech` to the raw fragment inside the flight preflight,
   before the phase program is even resolved. The KEY (facet) side is unconstrained: a key is
   knowledge text by construction. No inference is attempted over the prose — no regex can decide
   whether a vector file carries speech, so the fragment declares it.
2. **In this cell's identity.** The declared `embedded_signal` is a config value, so it enters the
   composed `config_hash` alongside the pinned `sha256`. **The query's signal is part of what KU-S1
   IS.** Changing `speech+state:` to `speech:`, or swapping the embedder, produces a different
   config hash and therefore a different cell; the change is registered, never slipped in.

The rule also re-reads the past. The DEV-1000 BLEND lock recalled on the trajectory's own
direct-decode **response text** — a text-only key. Its numbers stay a reference, and this cell
cannot be "the lock re-flown" even in principle.

## 2. What E6 changed, and the containment proof

The v1 refusal turned on three measurements. Each is now closed, and the closure is a committed
mechanism rather than a promise.

**(a) There was no config seam that could supply a phase.** `_default_phase_program_binding`
returned `supply_for_phase: None` unconditionally and the hook had no caller anywhere in `src/` or
`scripts/`. `rails/phase_supply.py` is that seam: a baseline fragment declares, per phase,
`provider` / `rank_policy` / `fuse_policy` / `k` / `tau` / `dimensions` / `query_source` (plus
`facet_source`, `rank_weights`, `fuse_coverage`, `alpha`, `expose_facets`); every component id
resolves in a `core.base` registry and every vector file is pinned by sha256 and re-hashed at
preflight. Only the `sealed-vectors` kind ships; `embedding-server` is declared and refused by name.

**(b) The containment rule refused the supply itself, on 100 % of rows.**
`EvidenceAgentController._dispatch` folded a `SupplyPacket`'s text into the next phase's
`AgentContactPlan.instruction`, which `rails.runner._assert_agent_control_excludes_knowledge_payloads`
reads verbatim — and 11,514 of 11,514 SLURP values are at or over the 8-character protected-material
floor. **That fold is gone, with no fallback.** `supply_for_phase` now returns a `PhaseSupply` — a
hash-bound `RankResult`/`FusionDecision` pair, never prompt text — for the NEXT phase, taken on the
wave that just completed, because that is the only wave whose transition can carry it. The
controller emits `action_kind="acquire"` with `new_value_ids` exactly the fusion's selection and
advances the successor `QueryState`, so `rails.runner._agent_messages` renders the values as typed
content blocks carrying `evidence_id`, `source_uri` and `knowledge_role`, validated by
`assert_knowledge_use_binding`. **A supplied phase's control-turn bytes are identical to the same
phase's unsupplied bytes**, and a test asserts that directly.

**(c) The substrate collided with 7.8 % of phase-2 control turns.** That was KU-S1c's problem, not
this cell's: KU-S1c appended its own draft response to phase 2's control turn, and 78 of those 1,000
appended responses collided with the content dimension. **This cell appends nothing per sample to
either control turn** — both phases declare `predecessor_binding: "none"` — so the only text the
containment rule reads is two static directives. Measured on 2026-09-06 against the real
`slurp-kb-size-full` snapshot (content hash `e27b2745…a51b57`, 23,267 protected payloads):

| control turn | chars | sha256 | collisions against 23,267 payloads |
|---|---|---|---|
| `probes/slurp_phase_direct.txt` (phase `direct`) | 262 | `d02f194c…f9d50` | **0** |
| `probes/slurp_phase_evidence.txt` (phase `evidence`) | 475 | `f7af111e…560224` | **0** |

That is why this cell binds the FULL `slurp-kb-size-full` snapshot — the BLEND lock's own substrate,
content dimension included — where KU-S1c had to fall back to the label/prior/speaker snapshot. The
measurement is re-run by
`tests/unit/test_phase_supply_cells.py::test_ku_s1_control_turns_pass_containment_against_the_full_snapshot`
against the real snapshot whenever `SPEECHRL_DATA_DIR` has it.

**Dispatch and the retain-prior rule.** Because the supplied phase is not the first, `FlightRuntime`
dispatches this program through `rails.phase_runner.run_continuous_program` — ONE trajectory per
sample rather than `run_program`'s two whole-roster waves — since a traced acquire transition can
only be emitted on the advance of the phase before the supplied one. Neither phase declares a
barrier, so nothing is given up, and the `run_phases` receipt says which dispatch ran.

A spec declaring `alpha` re-ranks the fused evidence's label distribution against the completed
phase's answer as `alpha * kb + (1 - alpha) * [label == prior]`; when the prior answer's label is the
**unique** winner, `PhaseSupply.retain_prior` stops the trajectory on that answer and spends no
second contact. That is `rails.kb_policy.KbAlphaBlendController`'s own retain-primary shortcut,
computed by its own `_fused_label_scores` / `_blend_scores` / `_argmax_labels` rather than
reimplemented. A tie that merely includes the prior label is dispatched, so the supplied contact can
break it. The v2 delta retain-override is **not** carried: it was falsified out of sample
(`docs/readiness/2026-08-25-baseline-lock-verdict.md` section 3).

Knobs are the lock's, unchanged: alpha 0.45, tau 0.65, k 5, rank weights 0.5 / 0.3 / 0.2, fusion
m = 5 / c = 2 / top_l = 3.

## 3. The query vector: provenance, deviation, and what is still open

### 3.1 The facet (KEY) side is closed

`vectors/slurp-ku-s1/facet-vectors.jsonl`, 11,514 × 1,024, 262,190,415 bytes, sha256
`922e8e9f…f8fad`, pinned in the fragment. It is a **pure format conversion** of the already sealed
`vectors-content-facets.npz` (sha256 `0bcb955a…c1c72`), which the registered pass
`SAEA-SN-TOOL-KB-TEXT-EMB-PASS` produced on 2026-08-24 at 23,030 embedding tool contacts and 0
frozen-core contacts. The conversion itself spent **zero contacts of any kind** under ledger row
`SAEA-SLURP-MF-KU-S1-FACET-VECTORS-V1` (`model-free-check`), verified the npz against the receipt's
pin, asserted its `ids` array equals the snapshot's content facet ids in order, and read the written
file back through the flight's own reader at max |delta| 0.0. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-ku-s1-vectors/facet-vectors.json`.
Value vectors stay sealed and are never loaded (owner Q-K-V ruling, 2026-08-23).

### 3.2 The query side is NOT closed, and why

`phase_supply.evidence.query_source.sha256` is the 64-f placeholder. The fragment's
`before_this_flies` carries the requirement in the owner's own words:

> query vectors must be produced by a speech-containing embedder chosen by MF-7 (GLAP /
> LCO-Embedding-Omni / Omni-Embed-Nemotron, speech alone or speech + draft state); owner rule
> 2026-09-06

**MF-7's decision table fixes three things**: which embedder; whether the query is `speech` or
`speech+state`; and, if fused, how the two components are combined. Each choice is legal under
`QUERY_SIGNAL_MODALITIES`, each produces a different `config_hash`, and the chosen one is pinned
here before takeoff.

### 3.3 What was produced instead, and what it is now for

Ledger row `SAEA-SLURP-KU-S1-QUERY-EMBEDDING-V1` (`bounded-discovery-probe`, attempt
`attempt-20260906T070727Z-kus1qemb`) ran to completion on 2026-09-06: **1,002 embedding tool
contacts** (1,000 query texts + 2 jitter probes) against a registered ceiling of 1,050, 0
frozen-core contacts, 0 speech audio seconds, 0 GPU hours, 0 gold reads, 0 paid spend. It embedded
the 1,000 phase-1 (`draft`) response texts of the sealed KU-S1c run
`SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` (run manifest sha256 `1b5143aa…11a74d`, phases file
sha256 `f6ed3c14…264e63`, both verified before any text was read), producing
`vectors/slurp-ku-s1/query-vectors.jsonl`, 1,000 × 1,024, sha256 `c194adfb…ff4c6`. Receipt:
`.../2026-09-06-slurp-ku-s1-vectors/query-vectors.json`.

Those vectors are **text-only** and are therefore **not this cell's query**. They keep their path and
their receipt for two other jobs:

1. the **Q-draft** arm of the MF-7 retrieval-key audit — the text-only baseline every
   speech-carrying key is measured against (worktree `wt-mf7` reads this exact path);
2. the **state half** of a future `speech+state` fusion, if MF-7 picks the fused form: the state
   component is the row's own draft answer, which is exactly what was embedded.

**The provenance deviation, stated here so the verdict restates it.** Whatever MF-7 chooses, the
query vector is embedded **before the flight** and therefore **cannot see this flight's own phase-1
answer**. The DEV-1000 lock embedded in flight, one contact per row, on that trajectory's own
answer. A pre-flight file is what makes a supplied cell hash-pinned and reproducible; that is the
price, and it is the price whether the state half comes from KU-S1c's sealed drafts or from anywhere
else.

**The alternative considered and not chosen** for the state half: the sealed one-contact closed-list
direct baseline's responses (`SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, run manifest sha256
`f908ff4c…ebc94c`). Rejected because that arm is `policy: "fixed"` and its request carries no phase
control turn at all, and the KU-S1c verdict measured that the control turn is worth **+1.2 of the
+1.5** intent points that arm gained — the two answer populations are measurably different. KU-S1c's
draft phase is the same program path, the same byte-identical system message and the same static
directive (`probes/slurp_phase_direct.txt`) KU-S1's phase 1 will send.

**One honest deviation in the pass itself.** The jitter pair — the same text embedded at session
start and at session end — was **not bit-identical**: cosine `0.9997014083444208`, where the
2026-08-24 KB pass on the same CPU-only geometry was bit-identical. A second CPU embedder (another
agent's, pid 4602, port 8092, same GGUF, same `-t 6`) was resident for part of the pass and is the
obvious candidate cause, but the cause is not established. Any consumer needing bit-exactness must
re-measure rather than inherit the 2026-08-24 claim. That process was never contacted or signalled:
the script contains no `pkill`, `core.session.stop_session` targets only the receipt-bound pid
(7738) after re-verifying its identity, and pid 4602 exited on its own.

## 4. Roster, populations and exposure

The whole frozen DEV-1000 runtime view, id for id, split identity hash
`8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, receipt
`docs/receipts/probe-samples/DEV-1000.json`. **No new draw, no new exposure**: this is the roster the
sealed 2026-08-25 lock campaign, the 2026-09-05 closed-list direct baseline, KC-S1a/b and KU-S1c
already read.

| population | n | receipt | role |
|---|---|---|---|
| DEV-1000-NEW500 (unexposed at the lock tier) | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` | **the decision population**; reported first |
| DEV-1000 (pooled) | 1000 | `docs/receipts/probe-samples/DEV-1000.json` | reported |
| DEV-500 (prior-exposed) | 500 | `docs/receipts/probe-samples/DEV-500.json` | reported separately, never pooled into a decision |

Inherited exposure: the DEV-100 campaign rounds 0–5, K-WIDEN K1, A4, the DEV-500 confirmatory
campaign, the DEV-1000 baseline lock, `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, `SAEA-SLURP-KC-S1A-…`,
`SAEA-SLURP-KC-S1B-…`, `SAEA-SLURP-KU-S1C-…`, and the two 2026-09-06 vector rows above. Gold never
enters the flight process: samples are built label-free from the runtime view and the adapter's
`gold()` refuses outright; gold opens once, scoring-side, at the single registered read. The held-out
test split is never named, loaded or scored.

## 5. Budget and ceilings

Run-cumulative across every attempt of the run id, enforced by `core.model.adapter` against a fresh
sibling read of durable attempt actuals. At most **one** recovery re-registration; a second failure
stops the flight and the fix is proven on a 4-row dry run.

| run id | calls (registered ceiling) | speech seconds (ceiling) | GPU-h (ceiling) | tool | embedding | paid |
|---|---|---|---|---|---|---|
| `SAEA-SLURP-KU-S1-PROMPT-FIT-V1` | 0 generated (4) | 0 (60) | ~0.05 (0.3) | 0 | 0 | 0 |
| `SAEA-SLURP-KU-S1-SMOKE-4-V1` | 8 (24) | 30.022 (120) | ~0.05 (0.3) | 0 | 0 | 0 |
| `SAEA-SLURP-KU-S1-BLEND-CL-DEV1000-V1` | 2,000 + 8 canaries (**2,100**) | 5,769.5874 (**6,000**) | ~0.4 (**1.0**) | 0 | 0 | 0 |

The registered call figure is the **worst case** — two contacts on every row — because the realised
count is data-dependent (section 6). The roster's own audio is 2,884.7937 s and the worst case makes
two passes over it. Tool and embedding contacts are 0 **in flight**: both vector files are produced
before takeoff under their own rows.

## 6. Realised contacts: an expectation, not a prediction

The `retain_prior` rule makes the contact count a function of the data. Under the sealed DEV-1000
lock's own (text-only) key the realised split was:

| | retained after 1 contact | dispatched to 2 contacts | total loop contacts |
|---|---|---|---|
| lock's BLEND arm, **with** the v2 delta retain-override | 660 | 340 | 1,340 |
| the same arm with the override removed — **this cell's form** | 674 | 326 | ~1,326 |

So the expectation is roughly **1.33 contacts per row**. It is an expectation and not a prediction:
this cell will recall on a **speech-carrying** key, and a different key changes which rows the blend
retains. The flight reports the realised count from the `run_phases` receipt and the verdict carries
gain per extra contact.

## 7. Analysis and decision rule (frozen before the read)

`analysis.paired.paired_contrast`, delta = arm minus comparator on per-sample official scores,
stratified bootstrap **N = 10,000**, strata = the gold scenario, **seed 20260903**, **CI90**, exact
sign test. Metrics: intent (scen_act), scenario, action, per-sample slot F1 (exact type+filler),
per-sample SLU-F1, slot precision, slot recall. Both weightings reported: natural mixture and
equal-stratum. Per-stratum table with the published column beside it.

**Comparators, fixed in advance.**

* **The comparator** is the sealed closed-list direct baseline `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`
  (run manifest sha256 `f908ff4c…ebc94c`): scenario 81.00 / action 73.90 / **intent 71.40** /
  entities strict 21.91 / Word-F1 33.69 / Char-F1 38.20 / **SLU-F1 35.80**. Paired against the sealed
  rows, row for row.
* **The equal-contact control** is KU-S1c (`SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1`): 81.50 /
  75.20 / **72.90** / 23.26 / 33.99 / 38.07 / **35.92**. This cell's delta is additionally stated net
  of it. Its own draft-phase row (81.40 / 74.90 / 72.60 / 35.51) is the control-turn-matched,
  one-contact view.
* **Reported beside, never as comparators**: KC-S1b (81.00 / 73.90 / 71.40 / **44.35**), the sealed
  DEV-1000 BLEND cell (83.90 / 77.60 / **75.70** / **41.69**), the sealed DEV-1000 M0 arm (70.00 /
  61.50 / 53.60 / 36.90), and the published brackets — Google/SF-ID weakest pipeline intent 72.06 /
  SLU-F1 64.02 and Multi-SLURP/HerMiT intent 78.33 / SLU-F1 70.84, both on the official **test** split
  and a natural mixture. This is a scenario-stratified **dev** roster and no published prompt-only
  SLU-F1 computed with this script exists for any audio LLM, so no like-for-like target is available
  and none is claimed.

**Decision rule — unchanged from the v1 preregistration, which registered it for the day the enabler
landed.**

* **ADMITTED** iff the intent (scen_act) **CI90 lower bound is above 0** against the closed-list
  baseline **on NEW500** AND its **delta net of KU-S1c keeps a CI90 lower bound above 0**.
* **NULL** if either interval includes 0 — in which case the direct form stays the reference and
  retrieval on SLURP is re-scoped to slots with KC-S1b as the base.
* **HARMFUL** if the upper bound is below 0.

Scoring is the dataset's standard scorer: the real, unmodified official `evaluate.py` at pinned
commit `8eb16545762be97ace75334109d73824217311f1`, `--average micro`, run **once over the complete
manifest** through `core.scoring_batch`, never sharded, with the official-vs-port identity check.

## 8. Reporting obligations

Every verdict on this cell carries, without exception:

1. the **per-stratum table**, both weightings, published column beside the repo column;
2. the **realised contacts per row** and the **gain per extra contact**, from the `run_phases`
   receipt, never assumed;
3. the **token distribution of the supplied knowledge blocks** — min / median / p95 / max — as a
   **covariate**. Per the owner ruling of 2026-09-06, token caps here are **advisory**, not gates:
   the form twin for this cell is KU-S1c, and the supplied block volume is reported so a reader can
   see whether an effect tracks prompt length rather than retrieval;
4. the **declared query-signal modality and the pinned query-vector sha256**, because both are part
   of the config hash and therefore part of what this cell is;
5. the statement that the pre-flight query vector **cannot see this flight's own phase-1 answer**;
6. the statement that the sealed BLEND cell is a **reference, not a comparator**, and that its
   realised contact split was measured under a text-only key this cell does not use.

## 9. What the flight agent must do on master

None of this happens in the worktree, and none of it happens before MF-7 reports. In order:

0. **Wait for MF-7.** Pin the chosen embedder's query vectors into
   `configs/baseline/slurp-phase-blend-cl-v1.json` (`sha256` + a `speech:` / `speech+state:`
   `embedded_signal` + the producing pass's `tool_contact_ledger_row`), and re-run the containment
   measurement. The cell is refused at preflight until this is done, by design.
1. **Prompt fit**, zero generated tokens, through the resident server's `/apply-template` +
   `/tokenize`: **both phases, all 1,000 rows, with the WORST-CASE supply** — the k = 5 longest
   values in the frozen snapshot, which is exactly what
   `FlightRuntime._phase_supply_prompt_bound` returns as a true ceiling. Report the worst envelope
   against the 8,192-token slot; a negative margin STOPS the mission. `FlightRuntime`'s own
   pre-flight budget estimator is not evidence for this cell on its own (KC-S1 deviation 3), which is
   why a pinned `prompt_fit_receipt` + `prompt_fit_receipt_sha256` pair must be added to the fragment
   before takeoff, as KU-S1c's was.
2. **Wire check** (`--wire-check`) **on a clean committed tree**: the whole request path against a
   fake gate and a fake transport, zero sockets and zero model contacts. Assert the per-request typed
   content-block count is non-zero on the `evidence` phase and zero on `direct`, and that the
   seal-and-score step is not REFUSED.
3. **Exposure rows written** for the prompt-fit, smoke and flight run ids, before any contact.
4. **Dry run** (`--dry-run`): preflight only, no server, no contact — this is where a stale vector
   hash or a text-only `embedded_signal` fails loudly and cheaply.
5. **4-row smoke** on four DEV-1000 rows fixed in a smoke fragment before they are read (the four the sealed closed-list wiring proof, the MF-5 SLURP phase smoke and the KU-S1c smoke all flew), proving on real rows: the
   continuous-program dispatch, the acquire transition carrying the fusion's `RankResult` /
   `FusionDecision`, the typed content blocks with `evidence_id` / `source_uri` / `knowledge_role`,
   the `retain_prior` early exit on at least one row if the data offers one, the `-np 8` geometry,
   and sealing exactly one outputs row per sample. Its responses are a wiring proof and enter no
   verdict.
6. **Flight**, one attempt, one seal, on a clean tree for the whole run (a COMPLETED manifest reads
   `study_commit` at finalize and refuses a dirty tree).
7. **`core.scoring_batch`**, one job per complete manifest, never sharded, with the
   official-vs-port identity check.
8. **One registered read**, then the verdict
   `docs/readiness/2026-09-06-slurp-consumption-ku-s1-v2-verdict.md` and its `result-summary.json`,
   carrying every obligation in section 8.

## 10. What this authorizes, and what it forbids

**Authorizes**: nothing to fly today. It fixes the roster, budget, comparator, analysis, decision
rule and reporting obligations so that MF-7's report changes exactly one hash and one declared
modality.

**Forbids**, as always: any test-split contact; any superiority or generalization claim; any
Stage-3 or paper-scale activity; any knob change or re-fly on the strength of a number; treating the
sealed BLEND figures as this cell's comparator; and any statement about what retrieval adds under
the closed-list instruction drawn from a cell that has not flown.
