# SLURP test split: the one-shot read protocol, v1 DRAFT

## 1. Status

**DRAFT. This document registers nothing, mints no receipt, adds no exposure-ledger row, changes no config, and authorises no
contact of any kind with the SLURP test split.** It was written model-free on 2026-09-19 from identity metadata (split names,
counts, hashes), the dataset lock, committed receipts and source code. No test audio, transcript, annotation or gold was
opened to write it.

- **Owner decision 28 of 2026-09-19** (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`): every number read
  on TRAIN Fold A, Fold B and DEV-1000 is a **development** number; the published baselines are
**test-set** numbers; "the comparison with published systems happens once, on the SLURP test split, after Stage 3
  (training-free RL, Pareto-optimal policies over the exposed exemplar / aggregation / candidate / node policies),
  under the program's split policy (test only for final reporting; one read; registered before contact)".
- **Owner decision 29**: drafted now (CPU), **frozen at the v2.0 lock**, **executed only after Stage 3**; the draft must state
  where the read may run (section 6).
- **Owner decision 30**: the lock fires on either trigger -- official SLU-F1 >= 64 and intent >= 78 on TRAIN A replicated, or
  headroom exhausted (three consecutive NEUTRAL/HARMFUL one-factor cells); what is locked is the triple
**manifest hash, scorer id, module list** (decision 19).
- **Owner decision 33**: no Stage-3 specification yet, so this protocol fixes the *shape* of the Stage-3 policy declaration
  (section 4.3), not its content.

Life cycle: DRAFT (today) -> FROZEN (at the lock; bytes hashed, no further edits) -> REGISTERED (a preregistration package
plus an exposure row, after Stage 3, in the venue of section 6) -> READ (once) -> REPORTED. A change after FROZEN is a
versioned successor, never an in-place edit.

## 2. Roster: the full official SLURP test split

### 2.1 What is read

The **entire** official SLURP test split, both microphone channels, no subsampling, no stratified draw, no filtering, no
reserve:

| Quantity | Value | Source |
|---|---|---|
| Sentence (prompt) records | **2,974** | umbrella `docs/datasets.lock.json`, `slurp` entry, `annotations.records.test` |
| Real recordings | **13,078** | `docs/receipts/knowledge/slurp-split-identity.json`, `splits.test.count` |
| Headset recordings | **6,281** | derived from the frozen receipt's ids (`-headset` suffix), model-free |
| Far-field recordings | **6,797** | same derivation |
| Distinct utterance ids | **2,974** | same derivation; agrees with the lock's record count |

Devel is 8,690 recordings and this program's development rosters are 1,080 (TRAIN Fold A) and 1,000 (DEV-1000), so **the test
read is an order of magnitude larger than any cell flown so far** -- itself an argument about venue (section 6.2). Only real
audio enters: `_AUDIO_SUBDIR_FOR_SPLIT` maps `test` to `slurp_real`, so no `train_synthetic` row can reach the roster by
construction.

### 2.2 Identity

- Carrier: umbrella `docs/datasets.lock.json`, key `slurp`, pinned revision `8eb16545762be97ace75334109d73824217311f1`,
  governed copy `datasets/slurp/metadata`, `test.jsonl` SHA-256
  `fe3449af69b42fda7163345482556066c35a80f7e552a6d67e212a0e2f0783cc`.
- Split: the frozen, committed enumeration `docs/receipts/knowledge/slurp-split-identity.json`, `splits.test.identity_hash` =
  `3f7063cb8b1e60d69c383d2215b5f244bbd7164d484010193a093a5e879389bd` (SHA-256 over the LF-joined sorted sample ids), produced
  by `rails.knowledge_build.freeze_slurp_split_identity` with the identity-only enumerator `slurp_split_sample_ids`, which
  "reads ONLY `slurp_id` and `recordings[].file` from the governed jsonl -- never
  `scenario`/`action`/`entities`/`tokens`/`sentence` (the SLU gold layer)". That is the one time a test metadata file has been
  opened here, and it produced only ids.
- At freeze, one **roster receipt** in the committed form of `docs/receipts/rosters/` (schema `saea-roster-receipt-v1`, e.g.
  `slurp-evo-fold-a-v2.json`): `roster_id` `SLURP-TEST-FULL-13078-V1`, `roster_role` `evaluation`, `carrier_lock_key` `slurp`,
  `split_role` (section 6 decides the legal value), `split_identity_hash`, `items[]` with
  `sample_id`/`headset`/`audio_seconds`, `per_stratum` by scenario and channel, `excluded_count` 0, no `seed`,
  `selection_rule` "the complete split, id-sorted; no sampling". The freeze pass is model-free and identity-only -- ids and
  durations, never `sentence`, `scenario`, `action`, `entities` or `tokens`.

### 2.3 Disjointness: true by construction, re-proved before the read

**By construction, machine-enforced.** Every knowledge store, exemplar pool and construction roster is built from the SLURP
**train** split only, and the builder is fail-closed: `rails.knowledge_build.build_knowledge_snapshot` loads the frozen
devel/test identity receipt plus the DEV-ladder receipts (`FINAL60.json`, `DEV-100.json`, `DEV-500.json`, `DEV-1000.json`) and
raises `RailsError("KB-BUILD selection intersects the frozen devel/test/FINAL60/DEV-tier decontamination roster: ...")` if one
selected sample id intersects them. The semantic stores narrow further: the 2026-09-13 exclusion binds them to "the governed
SLURP TRAIN split minus every utterance with a recording in TRAIN Fold A, Fold B or DEV-1000 ... the same 9,354 utterances the
E12 slot-audit view and the M1 exemplar pool bind" (`rails/scenario_hints.py`). Every existing SLURP roster receipt already
carries `shared_with_test_fold_a`, `shared_with_test_fold_b` and `shared_with_test_exemplars`, all **0**.

**Re-proved anyway, once, at freeze**, model-free, receipted under
`docs/checks/speech-aware-evidence-acquisition/<date>-slurp-test-roster/`:

1. **By recording id.** The test ids are intersected with every `source_sample_ids` of every knowledge snapshot the locked
   plan pins; the `train-exemplars` store; the `intent-boundaries` and `slot-contracts` support rosters
   (`docs/readiness/2026-09-13-slurp-semantic-store-release-pins-v1.json`); the scenario-hints table; every `slurp`-carrier
   receipt under `docs/receipts/rosters/` and `docs/receipts/probe-samples/`; and the DEV ladder including DEV-2000. Expected:
   empty, every pair.
2. **By utterance id** (`slurp:<split>:<id>`), because a prompt-level collision would be invisible at recording level.
3. **By text.** SLURP partitions prompts across splits, so overlap should be nil but is not machine-guaranteed. The check runs
   **inside the identity-only freeze process as a hash-only comparison**: normalised test sentences are hashed against the
   hashed construction texts, and the process emits counts and a verdict hash and **never writes, prints, caches or returns a
   test sentence**. Any non-zero overlap stops the read. Whether even this hashed pass may touch `sentence` is an open
   decision (section 9, item 3).
4. **Exposure closure.** The test identity hash appears in no consumed exposure-ledger row: the split is unread at the moment
   of registration.

## 3. Scorer

### 3.1 The number

The **unmodified official SLURP `evaluate.py`** at the pinned upstream commit, as every development number already is
(decision 23: "the program bar and every final evaluation read the OFFICIAL, unprojected SLURP `evaluate.py` number ... the
community-standard protocol"). Evaluator `SPEECHRL_DATA_DIR/repos/slurp/scripts/evaluation/evaluate.py`, pinned commit
`SLURP_OFFICIAL_COMMIT = "8eb16545762be97ace75334109d73824217311f1"`, verified by `git rev-parse HEAD` or, where git metadata
is absent, by the four pinned file SHA-256s in `reproduction.slurp_official_eval._PINNED_FILE_SHA256`; both paths fail closed.
Interpreter `~/.venvs/slurp-official-eval/bin/python` (Python 3.9.25, pinned deps), receipt
`docs/receipts/environments/slurp-official-eval.json`. Invocation, as `run_official_evaluate` builds it: `python evaluate.py
-g gold.jsonl -p predictions.jsonl --average micro --errors --table-layout csv`. Reported: **pooled SLU-F1** and **intent
(scenario_action)** as the headline pair, plus **scenario**, **action** and **span/entity** -- keys `slu_f1`,
`intent_accuracy`, `scenario_accuracy`, `action_accuracy`, `span_f1`, each block's precision/recall/F1 and tp/fp/fn retained
in `raw`. Numeric identity against this study's per-sample port is asserted at `_IDENTITY_TOLERANCE = 1e-6`; a divergence is a
hard failure, not a footnote.

### 3.2 One complete scoring job

Scored **once**, as one complete job, through `core.scoring_batch.run_score_batch`, whose contract is machine-declared in
every summary it writes: `"parallelism_boundary": "one-complete-verified-manifest-per-process"` and `"aggregation_rule": "no
dataset sharding and no averaging of shard-level official metrics"`. Completeness is enforced by `core.scoring_receipt`, which
raises `ScoreReceiptError("scorer <name> per_sample rows do not cover the complete roster exactly once")`. A non-empty output
directory is refused, so no earlier score record is overwritten. **No re-score, no second scoring configuration, no post-hoc
re-projection of delivered bytes.**

### 3.3 Diagnostics beside, never instead

Projection v3 (`slurp-slu-official-projected-v3` family) stays a fixed diagnostic beside the official number (decision 7 as
revised by 23); since module M3 was admitted, v3 already runs **inside the agent** at delivery, so the post-hoc scorer
measures only what the node did not already do, and the report says which is which. The symmetric-normalised sibling
(`slurp-slu-f1-normalized-v1`, decision 14) is likewise a diagnostic. Neither may be reported as the result or replace the
official number.

### 3.4 Engineering the test scorer id (must land before freeze)

**No registered scorer accepts a test roster, and none can be made to at call time.** Two guards refuse it:
`data.slurp.load_slurp_split` raises unless `allow_heldout=True` (`_HELD_OUT_SPLITS = frozenset({"test"})`), and
`reproduction.slurp_official_eval` refuses any `sample_id` beginning `slurp:test:` before the data root is touched.
Decisively, `core.scorers.score_bundle` calls a scorer as `scorer_fn(bundle.outputs_path, lock, root)` -- three positional
arguments -- so `split_id` and `allow_heldout` **cannot be threaded through the registered scoring path at all**. The only
legal route is a new registry entry, exactly as the `-train` siblings were added: `slurp-slu-official-test` (binding
`split_id="test", allow_heldout=True`), plus `slurp-slu-official-projected-v3-test` and `slurp-slu-f1-normalized-v1-test` for
the diagnostics; each is one registration plus a composing test, and `core.scoring_batch` needs no change.

**The one permitted deviation from the locked manifest.** The lock freezes the scorer id `slurp-slu-official-train`. The test
read necessarily substitutes the test sibling of the *same evaluator, at the same pinned commit, with the same flags*; the
registration states that substitution explicitly and it is the only difference the read carries. These ids are written at
freeze and stay inert: registering them is not authority (section 6).

## 4. System: the locked base, unchanged

### 4.1 What flies

Exactly the **locked default plan at the v2.0 lock commit**
(`configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json` as it stands there, or its lock successor),
composed from that commit's `configs/` only. Request bytes come from the lock commit; nothing is retuned, re-prompted,
re-pinned or re-geometried for the test split. The lock records manifest hash, scorer id and module list (decision 19); this
protocol adds the **git commit** and the **composed config hash**, which are what a later reader verifies. The plan's frame at
drafting: `arm` `speech-feature-query-native-tools`, `policy` `phase-native-candidates-review-revise-v1`, `evidence_source`
`none`, `serving_slots` 4 with `serving_slot_tokens` 24576 (np4 / c98304 / max512, attach-only, never spawned by the flight),
role graph Perception -> Solver -> Reviewer (x3) -> Planner -> deliver, `max_revisions` 1.

### 4.2 Per-node composition (decision 31)

The candidate is composed **per node**, each admitted module at the node it acts on. The lock freezes whatever
`docs/receipts/harness-admission.json` (schema `saea-harness-admission-v3`) and the default plan say then. As of this draft:

| Node | Module | Config key and armed value | Status | In the plan today |
|---|---|---|---|---|
| Perception / candidate supply | M4b slot store v2 | `knowledge_stores.slot-contracts` re-pinned at the v2 release/snapshot bytes | ADMITTED, replication MET 2026-09-19 | yes |
| Solver boundary | M1 speech-keyed exemplar supply, k=20 | `knowledge_stores.train-exemplars` (full store block) | ADMITTED, provisional obligation UNMET | **no, not yet** |
| Delivery | M3 delivery-time normaliser node | `native_episode.deliver_normaliser = {"normaliser": "saea-deliver-normalise-v3"}` | ADMITTED 2026-09-19 | yes |
| Every boundary | review loop (Reviewer x3 + Planner + one Solver revision) | `native_episode.review_loop = "on"` | NEUTRAL, retained | yes |
| Solver | M2 grouped sampling with deterministic commit | `native_episode.roles.solver` (samples 5, T 0.7, plurality commit) | NEUTRAL, UNMET | no |
| Harness | finite-completion retention (E13) | `native_episode.finite_completion_policy = "deliver-latest-or-abstain"` | NEUTRAL | yes |

Two rules carry into the read. **HARMFUL modules never enter the plan** -- today the tail-silence key
`observe.<phase>.tail_silence_seconds` and the decode-confidence judge `judges.<phase>.judges` are barred, and
`scripts/checks/harness_admission_check.py` enforces it. And `native_episode.finite_completion_policy` stays
`"deliver-latest-or-abstain"`: no row may be lost to the 512-token cap, because a dropped row is a filtered roster.

### 4.3 The Stage-3 policies

Stage 3 has no specification yet (decision 33); Phase C of the program design is a sketch. This protocol fixes only the
declaration form: every Stage-3 policy that flies must, at freeze, resolve to **one key in one of the four config tables**
(`rails.config_tables`) or to a run-level key on the closed allowlist `RUN_LEVEL_SWITCH_KEYS`, and be listed here by key and
frozen value. A policy that cannot be named as a key at the lock commit does not fly. The training-free RL optimisation itself
is development work on TRAIN and DEV under the existing profiles; it never touches the test split.

### 4.4 Prohibitions, absolute

No test-set tuning. No preview, pilot, smoke or sanity batch on test rows. No early stopping on a partial score. No repeat, no
second configuration, no best-of. No row filtering. No knob, threshold, prompt or pin changed between registration and read.
If the read comes out wrong, it is wrong on the record; it is not re-run.

## 5. Comparators reported beside the test number

**(a) Our own development numbers, labelled as such (decision 28).** The same locked system's **DEV-2000** number (decision
34: sealed DEV-1000 plus 1,000 further devel recordings on the same stratification, receipted as a roster, with the direct
baseline and anchor flown on the added rows so every comparison stays paired) and its **TRAIN Fold A** number, each with run
id and sealed bytes. They sit beside the test number so the gap between an optimised-on roster and a held-out one is visible,
and are never presented as beating, matching or approaching a published baseline.

**(b) The published test-set ladder, with protocol differences stated.** From the program's floor rule of 2026-09-04
(`docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md`), all on the official SLURP test split:

| System | intent (scen_act) | SLU-F1 | scenario | action | Protocol difference from ours |
|---|---|---|---|---|---|
| Google / SF-ID (weakest published trained pipeline, SLURP Tables 7-8) | 72.06 | **64.02** | 78.87 | 74.31 | commercial ASR into a trained SLU model; trained on SLURP |
| Multi-SLURP / HerMiT (strong pipeline) | 78.33 | 70.84 | -- | -- | trained on SLURP audio |
| Gold / HerMiT (gold transcripts) | 84.84 | 78.19 | 90.15 | 86.99 | oracle transcripts; an upper bound, never a peer |
| ChatGPT on oracle transcripts, 0-shot (He and Garner, arXiv:2305.13512) | 79.25 | -- | -- | -- | prompt-only but text-only; no published SLU-F1 |
| ChatGPT on Whisper ASR, 10-shot (same) | 72.89 | -- | -- | -- | cascade; its slot F1 12.03-13.35 uses a different F1 definition |

Stated every time: **every published row is a system trained on SLURP**, while ours is a frozen, zero-parameter core behind an
API-shaped boundary with a training-free control plane; and no published prompt-only SLU-F1 computed with the official
`evaluate.py` exists for any audio LLM, so there is no like-for-like target at any protocol. The comparison is **descriptive
positioning, never a significance claim** (section 8).

**(c) The frozen core's direct baseline on the same test roster, if the owner authorises it in the same read.** Form: the
`direct-only` phase program of the same shared controller through the same `FlightRuntime` and executor -- one extra contact
per row, 13,078 extra contacts -- flown in the same registered read and scored by the same scorer in the same complete job. It
is the only comparator that makes the system-over-direct delta a paired, held-out measurement instead of an import from
development. **Recommended**: without it the read has no internal contrast.

## 6. Where the read may run

### 6.1 What this repository refuses, verbatim

`src/speech_aware_evidence_acquisition/contracts/plan.py`, `ExecutionPlan.validate`:

> ```
> if self.split_role == "confirmatory":
>     raise ExecutionScopeError(
>         "confirmatory execution is not a Stage-2 authority: reading confirmatory "
>         f"results requires {PAPER_GATE_TOKEN} (independent paper repository) or a "
>         "dated owner allowance; relabeling the profile does not change this"
>     )
> ```

and, with `STAGE2_SPLIT_ROLES = frozenset({"discovery", "dev"})`, any other value raises "unknown split role ...; Stage-2
roles are ['dev', 'discovery'] (fail-closed)". `assert_execution_scope`:

> "This study repository accepts exactly the profiles in `ALLOWED_EXECUTION_PROFILES`.
> `paper-scale-confirmatory` -- and any other paper/confirmatory/production-scale profile -- is never
> accepted here: Stage-3 work requires promotion to an independent `papers/<slug>` repository under
> `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`. Unknown or forged profile strings are refused rather than
> normalized."

The consolidated execution contract
(`wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-consolidated-execution-contract.md`) says the same three
times:

> "**Information boundary** | gold, reference, test annotation, and future turns never enter runtime;
> each arm's visible fields and its prompt/config hash are recorded"
>
> "**Execution scope** | this repository accepts only the `model-free-check` /
> `baseline-reproduction` / `bounded-discovery-probe` execution profiles; `paper-scale-confirmatory`
> always fails closed (section 7)"
>
> "Until the program-level confirmatory reservation ledger exists (trigger: continuation entry 92),
> every confirmatory sample must have its split identity hash registered in the experiment ledger and
> the exposure ledger and be marked consumed before it is read; inherited exposure across studies and
> papers is monotonically non-decreasing."

The umbrella rule (`CLAUDE.md`, Repository): a study "ends at qualified paper candidates; Stage-3 (large-scale confirmatory
experiments, manuscripts, publication) lives in a separately admitted repo under `papers/<paper-slug>`, created only via
`OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`". The study `CLAUDE.md` repeats it under Prohibited, and `docs/receipts/splits.json`
states it in its own note: "any confirmatory result read requires Stage-3 authority or a dated owner allowance (consolidated
contract section 7)".

### 6.2 Remedy A -- execute in an admitted `papers/<slug>` repository (RECOMMENDED)

Requires: a qualified paper candidate frozen in this study; owner GO plus `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` for it; a
new entry in the umbrella `papers/registry.json` (schema `paper-repository-registry-v1`; it holds one carrier today,
`papers/meeting-minutes-agent`, admitted 2026-08-17, a different research object); a standalone repository with its own
contracts module admitting a final-reporting split role, its own exposure ledger, and a migration-manifest pin of whatever
code it reuses; and this protocol's frozen bytes carried across by hash.

Recommended for four reasons. (1) The read *is* what the paper gate exists for: a single held-out comparison with published
systems whose output is a final-reporting number. (2) **There is no faithful machine role for it here.** The one precedent for
a dated owner allowance in this repository -- the six Earnings-22 ESB test calls of 2026-09-04 -- worked because the owner
re-designated those calls **calibration-exposed**, and `dev` is the role that means "legal to calibrate against, never a
final-reporting split", so declaring `dev` was, in that preregistration's own words, "a faithful expression of the decision,
not a relabeling to get past a gate". This read is final reporting by definition, so `dev` would be exactly the relabeling the
guard forbids. (3) **Scale**: about 65,700 contacts and 41-42 GPU hours (section 7.3) -- more than the entire retired
first-slice budget and about twelve times any cell flown to date; contract section 7 names large-scale confirmatory campaigns
as Stage-3 work. (4) Weakening the guard here would destroy what makes every development number in this repository
trustworthy: that no cell could have peeked.

### 6.3 Remedy B -- a dated owner amendment admitting one registered confirmatory read here

Requires, all before any contact: a dated owner amendment naming the SLURP test split, the one read, and the split's
consumption afterwards; a **paired code change** admitting a machine role for it -- because no faithful role for final
reporting exists in `STAGE2_SPLIT_ROLES` and `"confirmatory"` is refused outright -- with its tests and the amendment cited in
the code; a successor split receipt in the form of `docs/receipts/splits-calibration-exposure-2026-09-04.json`, which pins the
parent bytes without rewriting them; the test scorer ids of section 3.4; and an exposure row carrying the test split identity
hash with `consumed` set before the result is read. It is cheaper and has a precedent in form, but it changes a fail-closed
guard inside the repository whose development numbers that guard protects, and it puts a final-reporting read in a carrier
whose declared endpoint is "qualified paper candidates ... not finished final paper experiments". If the owner chooses it, the
amendment should say why the read is not being promoted, and the code change should admit a role named for what it is (for
example `final-report`), never reuse `dev`.

**Recommendation: Remedy A.** Remedy B is acceptable only as an explicit, dated owner override.

## 7. Registration form at freeze

Nothing below is registered by this draft. It is the shape the freeze package takes, in the form of
`docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-preregistration.md` and its package directory (`README.md`,
`protocol-registered-v*.json`, `*-generation-plan-registered-v*.json`, `*-fit-plan-registered-v*.json`,
`analysis-recipe-v*.json`).

**7.1 Run ids.** `SAEA-SLURP-TEST-FULL-LOCKED-SYSTEM-V1` (the locked system on all 13,078 rows) and, only if section 5(c) is
authorised, `SAEA-SLURP-TEST-FULL-DIRECT-V1`. **No smoke on test rows exists**: the structural smoke runs on development rows
at the lock commit and proves request-byte identity with the locked plan; the test split never sees a rehearsal.

**7.2 ExecutionPlan fields.** One `contracts.ExecutionPlan` per arm (`schema` `saea-execution-plan-v1`), validated before
contact: `run_id`; `execution_profile` (the venue decides the legal value -- inside a paper carrier the plan is not bound by
this repository's `ALLOWED_EXECUTION_PROFILES`); `carrier_lock_key` `slurp`; `split_role` (section 6; never `dev` for a
final-reporting read); `split_identity_hash` = SHA-256 over the roster's LF-joined sorted carrier-prefixed sample ids;
`planned_model_calls`; `planned_gpu_hours`; `planned_speech_audio_seconds`; `protocol_hash` = SHA-256 of this document's
frozen bytes; `attempt_id`; `study`. Budgets are **run-cumulative across every attempt of the run id**
(`core.attempts.AttemptStore.prior_actual_usage`), and the plans carry the B7a package's `family_budget` fields (generation
and fit caps, `gpu_hours_fit_inclusive`, `repeated_speech_audio_seconds_cap`, `native_task_contract_calls_cap`,
`official_complete_scoring_jobs`, `asr_calls` 0, `encoder_calls` 0, `ceilings_are_not_targets` true).

**7.3 Budget, from the measured per-row cost.** The sealed anchor realized **5.016 contacts per row** (5,417 over 1,080) and
**3.388 GPU hours per 1,080 rows**; the B4b replicate's merged manifest realized **5.021 contacts per row**, **3.4651 GPU
hours** and **15,487.59 repeated speech seconds** against **3,084.53 s** of unique audio (mean 2.856 s per recording). A
direct arm is 1.00 contact per row. Unique test audio is therefore about 37,400 s (about 10.4 h) for either arm.

| Quantity | Locked system | Direct arm (if authorised) |
|---|---|---|
| Rows | 13,078 | 13,078 |
| `planned_model_calls` | about **65,700** (13,078 x 5.021); ceiling at 11 contacts/row 143,858 | 13,078 |
| `planned_gpu_hours` | about **41-42** (13,078 x 0.00321) | scaled from the locked direct plan's own pass |
| `planned_speech_audio_seconds` (repeated, as metered) | about **187,400** | about 37,400 |
| Official complete scoring jobs | 1 | 0 (scored in the same job) |

All plan values are **recomputed at freeze** from the locked plan's sealed per-row cost and the roster receipt's exact
`audio_seconds_total`; the table is an ex-ante estimate to inform the venue decision, not a registered value.

**7.4 Exposure-ledger row.** One row per run id, written **before any result is read**, in the repository's contract-table
form: timestamp, run id, profile, scope, runtime and serving geometry, population, split role, split identity hash,
`consumed`, planned calls, planned audio seconds, planned GPU hours, inherited exposure, plan path, notes. The
inherited-exposure cell states plainly that the test split has **zero prior exposure** and that after this row it is consumed
and can never be read again.

**7.5 Decision receipt.** A root decision receipt records the v2.0 lock commit, manifest hash, scorer id and module list; this
protocol's frozen SHA-256; the owner authorisation for the venue; the roster receipt hash; the disjointness receipt hash; and
the test scorer ids. The cell flips from `held` to live only after that receipt exists.

**7.6 Pre-read checklist** (every item receipted, all model-free): roster receipt minted and verified, count exactly 13,078,
`excluded_count` 0, both channels present; disjointness receipt clean on all four passes of section 2.3; split identity hash
recomputed from the governed `test.jsonl` and equal to the frozen receipt's; evaluator checkout verified at the pinned commit
(or by the four file hashes) and the official venv receipt re-verified; test scorer ids registered with their composing tests
green; serving geometry resident and receipted, the flight **attaching, never spawning or stopping**; locked plan composed
from the lock commit with a composed config hash equal to the lock's and a clean working tree for the whole run (a dirty tree
refuses finalize); `finite_completion_policy = "deliver-latest-or-abstain"` armed, no row filtering, every finite-completion
row retained, scored as delivered and reported as a mandatory diagnostic; and the exposure row written with `consumed` set
before the first score file is opened.

**Resume clause (owner decision 22).** If an attempt dies of an **infrastructure** failure with code and request bytes
unchanged -- never a harness or config defect -- the one allowed recovery may be a resume-recovery: every complete row of the
aborted attempt is kept without selection, every partial or unstarted row is flown under the same run id, and the merged
manifest declares the predecessor attempt with its trace hash, kept-row list and that list's hash. It changes no question,
roster, factor, comparator or decision rule, and the run-cumulative budget is re-checked because a resumed attempt and its
predecessor share one run id. A harness or config defect is **not** an infrastructure failure: it ends the read, which is not
re-registered without a fresh owner decision.

## 8. Reporting

**Written.** The official unprojected pooled SLU-F1 and intent (scenario_action), with scenario, action and span, on the full
test split; the per-scenario table (18 scenarios) and the per-channel split (headset vs far-field); the projection-v3 and
symmetric diagnostics beside them, each labelled a diagnostic; the system-over-direct paired delta if the direct arm flew; the
complete cost line (contacts, GPU hours, audio seconds, wall clock, tokens) the contract's efficiency clause requires; the
development numbers of section 5(a) **explicitly labelled as development numbers measured on rosters the program optimised
on** (decision 28); and the published ladder of section 5(b) with its protocol differences in the same table.

**Never written.** A second read, of any size, for any reason. A re-score or re-projection of the delivered bytes. A
significance claim against a published number -- those systems' per-row outputs are not available, so no paired design exists
and no confidence interval spans the comparison; the comparison is **descriptive**, and the report says so in the same
sentence that gives the number. A subgroup number promoted to headline. A development number presented as a test number, or
placed beside a published baseline without its label. Any generalisation beyond English SLURP SLU. If the test number lands
below a published baseline, that is the result, reported with the same table that would have carried the opposite outcome: the
protocol was frozen before the read, and the rule does not move.

## 9. What is not decided here

1. **Venue** (section 6): Remedy A (a `papers/<slug>` carrier) or Remedy B (a dated amendment plus a paired code change here).
   The draft recommends A.
2. **The direct arm** (section 5(c)): whether it flies on the same test roster in the same read, at one extra contact per row.
   The draft recommends yes.
3. **The text-level disjointness pass** (section 2.3, item 3): whether a hash-only comparison that touches `sentence` inside a
   sealed process is admissible under the information boundary, or whether the id-level proof is the whole proof.
4. **The split-role name** for a final-reporting read, and whether `docs/receipts/splits.json` gains a SLURP confirmatory
   entry or a successor receipt is minted beside it.
5. **Where the Stage-3 policies are declared**, and which config table each sits in (blocked on decision 33's agent base
   lock).
6. **DEV-2000** must exist and be flown by the locked system before the read, since section 5(a) reports it beside the test
   number; it is a decision-34 roster that does not yet exist.
7. **The module set at the lock**: whether M1 (ADMITTED, provisional obligation UNMET, not yet in the default plan) is inside
   the locked system, and how decision 31 resolves any node conflict.
8. **Publication scope**: whether the test number appears in a manuscript at all, and under whose authorship and venue -- a
   Stage-3 question this study never answers.
9. **Post-read status of the split**: consumed and closed permanently, which the exposure row states and which no later
   amendment may quietly reopen.
