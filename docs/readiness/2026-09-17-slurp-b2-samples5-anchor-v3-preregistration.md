# Cell B2 on the sealed anchor: sample-and-aggregate commit, preregistration (v3, after E2c)

Status: **PREREGISTERED BEFORE CONTACT.** Author: the cell B2 v3 registration agent, worktree
`/home/chao/saea-worktrees/fable-b2-v3`, branch `fable/b2-v3`, base commit `36874ed4`. Authority:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 4 (Phase B, cell B2,
module M2) and its engineering items E2, E2b and **E2c**, under owner decisions 6, 7 and 8 of
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. This document grants no model
contact; all three cells stay readiness `held` until the coordinator adds the decision requirement
and flips them with `scripts/flights/repin_cell.py`.

**This package supersedes, before contact, the v2 registration**
[`2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md`](2026-09-17-slurp-b2-samples5-anchor-v2-preregistration.md),
which was written before E2c and had to register "the Reviewer reads the five raw samples" as a
second, unmeasured difference. E2c (merged at `59db0f9b`) removed that confound from the harness, so
the cell is re-registered as v3 on new run ids and new hashes. The v2 cells never flew; their six
exposure rows keep `consumed = no` and each carries a supersession note. The v2 package in turn
superseded the review-off-based v1 package, which likewise never flew.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, and the campaign in flight
was never touched.

## 1. Question

Do five sampled Solver answers, aggregated by the deterministic plurality/support commit policy,
improve official pooled SLU-F1 over the **sealed anchor** on TRAIN Fold A 1,080?

The diagnosis this answers is in the spec's section 2: byte-identical greedy prompts already flip
28 % of outputs and 5 % of intents, so sampling plus deterministic aggregation has headroom; and
entity false positives (28.8 %, with 184 of 414 empty-gold rows emitting entities) are exactly what
a support filter over independent samples can suppress.

## 2. Arms

| role | identity |
| --- | --- |
| arm | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3` / `attempt-slurp-native-samples5-anchor-train-fold-a-generation-v3`, cell `slurp-native-samples5-anchor-train-fold-a-v3`, composed config `9688e0c9e6e93e30d200469b6ecafd28f865a37f0b0a3d694a879f7749f426a3`, protocol `4e5acfad5219ef6920b881dec240ead02d06f53aaf91895e92674579f0ee0a3e` |
| twin | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V3` / `attempt-slurp-native-samples5-anchor-greedy-twin-train-fold-a-generation-v3`, cell `slurp-native-samples5-anchor-greedy-twin-train-fold-a-v3`, composed config `65c9a220f3bced4f523b5c531a8a577c539dd10db4b4b7d439c73edc9a91cc9b`, protocol `0066dd067b27aadf25c8ba3b0e03cbffb78a9d47b3be0be66f4a9f37861430df` |
| smoke | `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3` / `attempt-slurp-native-samples5-anchor-smoke-4-generation-v3`, cell `slurp-native-samples5-anchor-smoke-4-v3`, composed config `d631960a736c34b0e9a1dd85bf9cdb7370feb7ec2410260a7fcadcf3737b2142`, protocol `63034f02c67c2fe3b0dde2cab8762df68500ec1ce545ab6f321562ec58324553` |
| primary comparator | sealed bytes of the dual-store anchor, `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` / `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1`, score artifact SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` (pooled SLU-F1 48.53, intent 77.96, scenario 84.81, action 79.26, pooled span F1 29.50; projection v3: 51.99 / 79.35 / 85.46 / 80.65 / 40.30) |
| secondary comparator | sealed bytes of the released TRAIN A direct anchor, `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`, score artifact SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`, run manifest `546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e` (pooled SLU-F1 33.89, intent 73.70, scenario 82.69, action 75.09, pooled span F1 21.10; projection v3: 34.31 / 75.37 / 84.17 / 75.93 / 23.24) |

Neither comparator is ever re-flown or re-scored. Cells B0 and B0r are **not** comparators here;
they are the review-off ablation and its own-null replicate, and their only role in this
registration is that B0r's CI95 half-widths are the null margins of section 7.

The **twin is flown**, because it is not a sealed comparator but the arm's own token-matched
control: identical contacts per row, identical commit policy, identical five pinned seeds,
temperature 0 instead of 0.7. Under owner decision 8 it launches **only after the arm shows a
positive CI95 against the base**.

All arms share the roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(SHA-256 `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split
`SLURP-EVO-FOLD-A-V2`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, and the
resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never spawn).

## 3. The one factor, and what it is not

Moved, all inside `native_episode.roles.solver` — the `episode`-class switch key whose OFF arm is
the historical Solver role (`rails.config_tables.is_episode_null_arm`):

- `samples` absent (1) to **5**;
- `decoding_overrides` absent to **{temperature 0.7, seed_offset 0}** (twin: temperature 0 with the
  explicit `twin: "greedy-repeat"` marker, the one documented exception
  `rails.native_episode_config.NativeEpisodeRole` admits for temperature 0);
- `commit` absent to **{policy `saea-commit-plurality-support-v1`, min_support 3,
  similarity_threshold 0.8}**;
- `policy` `phase-native-candidates-review-revise-v1` to
  `phase-native-candidates-review-revise-samples5-v1` — the same four declared phases,
  `max_contacts` 11 to **19**. The ceiling `1 + (1+1)*(1*5 + 3 + 1) = 19` is the exact program
  maximum that `rails.native_episode_config.load_native_episode_config` resolves, not a safety
  bound, and the validator refuses any other value. The fragment itself is **unchanged from the v2
  package** — same file, same `max_contacts`;
- `native_contact_fit` resized to `1080 * 19 * (1 + 3) = 82,080` endpoints, with its own run and
  attempt id per arm;
- the speech-feature key and matcher identity strings renamed onto each arm (provenance, never
  model-visible);
- `native_episode.review_loop "on"` added: the optional E6 marker,
  a redundant checked declaration of the three role leaves the loader already requires to agree.
  The anchor carries no marker; adding it cannot change behaviour and is refused the moment it
  disagrees with reviewer 3 / planner 1 / `max_revisions` 1;
- `prepared_phase_supply` re-prepared model-free for each cell's own composed config.

Held identical to the anchor: the roster and split, the model fragment and resident geometry, the
promoted speech packets, both knowledge stores with their release and snapshot hashes, the
four-candidate supply contract, every instruction template, the review-loop role graph (reviewer
`max_iterations` 3, planner 1, `max_revisions` 1, exhaustion policy `deliver-latest-solver`), the
`phase_tools` block with the Reviewer's `saea-tool-task-contract-v1` authority — **reachable here**,
unlike on the review-off base, and exercised by the anchor 1,082 times over 1,080 rows — and the
scorers.

Five request-level differences exist and all five are the module's own channel:

1. **Rendered envelope, proven row for row.** On all 1,080 rows and all four declared phases the
   rendered request differs from the anchor's by exactly one substitution, the phase-program id
   inside the `[agent control <program>:<phase>:<sample>]` marker
   (`phase-native-candidates-review-revise-v1` to
   `phase-native-candidates-review-revise-samples5-v1`). Applying that substitution to the anchor's
   envelope reproduces this cell's byte for byte on 1080/1080 rows for every phase, for the arm and
   for the twin alike; **0 rows differ in any other way**. Receipt:
   `SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-anchor-v3/request-envelope-comparison-v1.json`,
   rendered through the production `core.flight.runtime.render_phase_prompt_envelopes` reached by
   the production `FlightRuntime._phase_prompt_payloads` assembly.
2. **The episode-limits epilogue at dispatch.** The episode runner appends a `Native episode
   limits` block whose `remaining_model_contacts` is computed against `max_contacts` 19 instead of
   11. `max_revisions` stays 1 and `available_planner_actions` stays `[ACCEPT, REVISE]`, as in the
   anchor. The block is built **once per role visit**, so all five samples of one visit receive the
   byte-identical instruction. The fake-model proof of section 9 measures this as the whole
   rendered-text difference against an anchor-shaped episode: **one character**.
3. **Decoding parameters.** The five sibling Solver requests of one visit are byte-identical to
   each other except `seed`: `fragment_seed + seed_offset + sample_index` with
   `fragment_seed = 1249110493` (`rails.runner._solver_fragment_seed` over the composed program
   id), so `1249110493 … 1249110497`, the same five seeds in the arm and in the twin. Against the
   anchor's single Solver request they differ in exactly `seed` and `temperature`; the twin's
   differ in exactly `seed`. Proven with the production composer
   `reproduction.ojw.native_request.compose_solver_sample_decoding_params`. At dispatch the five
   samples' `agent_contact_id` markers read `solver:0` … `solver:4` where the anchor's reads
   `solver:0`.
4. **The committed answer is the reviewed draft (E2c).** One grouped Solver visit takes **one step**
   and registers exactly **one** `kind=phase:solver` agent state, whose content is the commit
   policy's aggregate, in the same wire form a samples-1 (anchor) Solver state has. The Reviewer and
   the Planner therefore read **one draft exactly as they do on the anchor**, which is what makes
   this cell a one-factor cell: the v2 registration moved both "sample and aggregate the answer" and
   "review a sample set instead of a draft" at once, and had to register the second as a known
   difference it could not attribute. The five raw samples stay in custody: each keeps its own
   `AgentContactRecord`, its own `MODEL_REQUEST`/`MODEL_RESPONSE`/`COST` trace records and its own
   metered cost; all five appear in the visit's one `action_alternatives` wave with their own
   response digests; and their sample indices, seeds, temperatures, parse status and parsed answers
   stay in the sealed `solver_group` receipt that `analysis.native_commit_replay` re-aggregates
   offline. Because the group takes no step between its samples, the five sibling requests see the
   **same `QueryState`** and the same exposed history — independent draws of one draft, not a chain.
   The committed state is sealed through `seal_phase_response_state`'s own
   `state_content`/`raw_response_text` seam, so `source_response_sha256` still binds real model
   bytes from the same contact its state id is namespaced by. Where it lives:
   `rails/runner.py::_invoke_native_role_episode` (`record_solver_commit`, `capture_completion`,
   `settle`) and `reproduction/ojw/native_group_solver.py::GroupedSolverRoleNode` (`on_commit`).
   Proved model-free by
   `tests/unit/test_native_episode_runner_grouped_solver.py::test_grouped_solver_revise_resamples_and_the_reviewer_reads_the_committed_draft`,
   `::test_grouped_solver_keeps_every_raw_sample_in_custody` and
   `::test_samples_one_solver_state_is_the_raw_draft_the_reviewer_reads`, and measured on the four
   smoke rows by
   `SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-anchor-v3/e2c-rendered-proof-v1.json`.
5. **A Planner `REVISE` re-samples the whole group and re-commits.** The second Solver visit is
   another five contacts, not one, and it registers its own single committed state, which the
   second-round Reviewer and Planner read beside the first round's. That is what makes 19 rather
   than 15 the ceiling. Proved by the same
   `::test_grouped_solver_revise_resamples_and_the_reviewer_reads_the_committed_draft`, and measured
   per row in the fake-model proof: two Solver visits of five contacts each, two
   `action_alternatives` waves, two committed states, and a second-round Reviewer request carrying
   exactly two `phase:solver` states, both committed.

The prepared first-phase Perception supply was rebuilt model-free for each cell and its `output`
equals the sealed anchor preparation's `output` (SHA-256
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`) on all **1,080/1,080** rows,
and the sealed four-row smoke artifacts' `output` (SHA-256
`512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733`) on **4/4**, `output_sha256`
included, so the knowledge channel does not move either.

## 4. The commit policy, fixed here

`saea-commit-plurality-support-v1` (`core.base.COMMIT_POLICIES`, implemented and registered in
`rails.commit_policies`), with the **preregistered thresholds `s = 3` of 5 and char-F1 `0.8`**,
unchanged from the v2 registration:

- **Intent** = the plurality `(scenario, action)` over the parsed samples; ties broken by the lowest
  first-occurrence `sample_index`.
- **Entities** = same-type mentions clustered at normalized char-F1 `>= 0.8`, kept at support
  `>= 3` of 5 among non-malformed votes, the delivered filler being the cluster medoid (highest mean
  similarity to the rest of the cluster, ties to the lowest `sample_index`).
- Deterministic given the five sealed samples, and rendered in the exact format
  `reproduction.slurp_delivery` / `reproduction.slurp_scoring` already parse and score.
- Its scope on this base is the **delivered** answer of each Solver visit **and**, under E2c, the
  one `phase:solver` state that visit registers: the committed answer is the draft.

Custody is machine-enforced: `rails.native_episode_receipt.validate_solver_group_receipt` and
`core.flight.runtime` refuse to seal a declared-`samples >= 2` row without a `solver_group` carrying
all five raw samples, their seeds and temperatures, their parse status, and the delivered answer's
support and tie-break provenance.

**The offline sensitivity table is reported and never used for the verdict.**
`analysis/native_commit_replay.py` re-aggregates the sealed samples at `s` in {2, 3, 4} at char-F1
0.8, zero model contact. The verdict is read at `s = 3`, char-F1 0.8, as fixed above before any
contact.

## 5. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1. Reported beside them: per-row mean official SLU-F1 and per-row mean exact slot F1,
saves/harms/ties with the exact two-sided McNemar p against the anchor and against the twin.

**Projection v3 beside every official number.** Owner decision 7 of 2026-09-17 makes
`slurp-slu-official-projected-v3-train` the fixed post-processing of every official number. It is
reported beside every unprojected number. The symmetric-normalised number is **not evaluable** on
this roster — no symmetric TRAIN sibling scorer exists — and is reported as "not evaluable" rather
than omitted or silently replaced by the DEV sibling's value. The decision rule stays on the
unprojected numbers, exactly as cell B0r's re-decision did. The projection runs over a **copy** of
each arm's sealed outputs; sealed bytes are never opened for writing.

Per-row agreement diagnostics, mandatory in the verdict:

- the intent support-count distribution (5/5, 4/5, 3/5, 2/5, bare plurality) and the delivered
  intent accuracy within each stratum;
- entities kept and dropped by the support filter, by slot type, with the resulting false-positive
  and false-negative movement against the anchor;
- malformed sample count and the rows where fewer than five samples parsed;
- rows whose delivered answer differs from sample 0;
- the arm-versus-twin per-row sample disagreement rate — the direct measure of what temperature 0.7
  bought over batch-composition nondeterminism alone;
- **revision counts**: rows with a `REVISE` route and the delivered Solver-visit index, against the
  anchor's five executed revisions and two intent changes;
- **Reviewer task-contract tool calls**, against the anchor's 1,082.

`delta = arm minus comparator`, in percentage points; a negative delta means the arm is worse.

## 6. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence.
Sensitivity: paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries
the per-scenario table in both the natural-mixture and the equal-scenario weighting; the
equal-scenario delta is reported beside the natural-mixture point estimate and never replaces it.
Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios of 60 rows,
523 headset and 557 far-field rows).

Four contrasts are computed: arm versus anchor (primary), arm versus twin (primary, once the twin
has flown), twin versus anchor (diagnostic: what the aggregation alone buys), and arm versus the
released direct anchor (secondary).

## 7. Decision rule (fixed here)

**Null half-widths are the TRAIN A own null, measured by cell B0r** as the CI95 half-widths of
(B0r minus B0) on this same 1,080-row roster
(`analysis/SAEA-SLURP-B0-REPLICATE-PAIRED-ANALYSIS-V1/README.md`): pooled SLU micro **1.1218**,
intent **1.0051**, scenario 1.0655, action 1.0327, pooled span F1 1.5586 percentage points. The
imported DEV-1000 margins (intent 0.92, SLU micro 1.18) are **not** used: owner decision 6 of
2026-09-17 and the family rule of 2026-09-08 require the carrier's own null on the same roster, and
cell B0's HARMFUL verdict is exactly what an imported margin bought.

- **ADMITTED** if the CI95 lower bound of the primary pooled SLU delta is greater than 0 against the
  sealed anchor **and**, once the twin has flown, greater than 0 against the twin; intent is
  non-inferior within 1.0051 pp; projection v3 agrees in sign; and no scenario loses intent beyond
  the null band.
- **NEUTRAL** otherwise while non-inferior on both pooled SLU and intent; it enters the default plan
  only if it lowers cost, which at about 9 contacts per row against the anchor's 5.016 it does not.
- **HARMFUL** if an interval excludes non-inferiority on pooled SLU or on intent.

**Twin trigger.** Owner decision 8: the twin flies only after the arm's CI95 against the base is
positive. If the arm is not positive, the cell closes without the twin and the arm-versus-twin
clause is reported as not reached.

No repeat-to-pass: the verdict is read once, from the single official score of each complete
manifest. Scenario and action margins are diagnostics for the per-scenario table, not gates.

## 8. Cost reporting (mandatory in the verdict)

- actual generation contacts and contacts per row, against the anchor's 5.016 and this cell's
  19-contact ceiling;
- the realized Solver-visit count per row and the `REVISE` rate;
- actual repeated speech seconds, expected about `9.0 * 3,084.528`;
- actual FIT endpoints, 4 per realized contact;
- Reviewer task-contract tool calls, against the anchor's 1,082;
- **GPU hours** read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over each lease window, never a wall-clock guess;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the realized prompt-cache behaviour of the five same-prefix sibling requests;
- preprocess and scoring wall time.

Registered ceilings, which are bounds and not targets, per full arm: **20,520** generation calls
(19 x 1,080), **82,080** FIT endpoints, **58,607** repeated speech seconds
(`ceil(19 x 3,084.5284)`), **12.0** fit-inclusive GPU hours, **6,480** Reviewer task-contract tool
calls (2 Reviewer visits x 3 iterations x 1,080), one official complete scoring job, zero ASR,
encoder and paid-API calls. The nominal one-pass cost is 10 contacts per row
(1 Perception + 3 Reviewer + 1 Planner + 5 Solver samples) = **10,800**. For the four-row smoke:
**76** generation calls, **304** FIT endpoints, **202** repeated speech seconds, **1.0** GPU hours,
**24** tool calls, zero scoring jobs. Every one of these is the v2 registration's number, unchanged:
E2c changes which state a visit registers, never how many contacts it makes.

**The 12.0 GPU-hour ceiling is the anchor's own registered ceiling, kept unchanged, and it rests on
an assumption that is not proven here.** The anchor *realized* 3.388 GPU hours at 5,417 contacts.
The five sibling Solver requests of one visit are expected to share their cached prompt prefix on
one slot: the model fragment declares `decoding_params.id_slot "per-sample"` (resolved to one stable
slot by the sequential dispatcher) and the server runs with `--cache-prompt`, so after the first
sample the remaining four should reuse the prefill. Under E2c the five siblings additionally share
the **same `QueryState`**, so their prompts are byte-identical but for `seed`, which can only help
that reuse; the server nonetheless runs `--no-cache-idle-slots` and `--slot-prompt-similarity 0`. A
contact-proportional estimate without any prefix reuse is about 6.1 GPU hours, so 12.0 has headroom
either way. The measured GPU hours are a mandatory verdict field, and the four-row smoke is the
first place this behaviour becomes visible: record the per-contact latency of sample 0 against
samples 1 to 4 and re-price before launching the arm.

## 9. Prompt fit

Measured bound from the **anchor's own 5,417 sealed native contact-fit receipts**, which cover
exactly the four role visits this cell renders, at the same geometry and the same 24,576-token slot:

| role visit | receipts | widest required tokens | minimum margin |
| --- | ---: | ---: | ---: |
| `perception:0` | 1,080 | 4,270 | 20,306 |
| `solver:0` | 1,080 | 13,157 | 11,419 |
| `solver:1` | 5 | 13,482 | 11,094 |
| `reviewer:0` | 1,080 | 13,259 | 11,317 |
| `reviewer:1` | 1,077 | 15,037 | 9,539 |
| `reviewer:2` | 5 | 13,596 | 10,980 |
| `reviewer:3` | 5 | 15,374 | 9,202 |
| `planner:0` | 1,080 | 15,028 | 9,548 |
| `planner:1` | 5 | 15,382 | **9,194** |

Every one fits, and under E2c **the anchor's maxima apply directly**. A grouped Reviewer, Planner or
second-round Solver request carries the anchor's own form — exactly one `kind=phase:solver` state
per Solver visit — so the v2 package's "four extra states, under 2,304 extra tokens" growth term is
withdrawn. The remaining differences are the 9-byte program-id substitution and one digit in the
episode-limits epilogue.

The one state's *content* is the commit of five completions rather than one completion. Each sample
is hard-bounded by the model fragment's own `max_tokens` 512; a deliberately conservative bound of
`5 x 512 = 2,560` tokens for that single state — as if the aggregate were as long as all five
samples together, which the support filter makes impossible — still leaves **7,146** tokens of
margin at `planner:1`, the tightest measured point.

The fake-model rendered proof measures this directly on the four smoke rows: every grouped Reviewer
and Planner request renders the same number of solver-state blocks, of the same size, as an
anchor-shaped episode scripted with the same answer, and the whole rendered-text delta is 0 or 1
character. Receipts:
`SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-anchor-v3/prompt-fit-statement-v1.json` and
`.../e2c-rendered-proof-v1.json`. Every realized request is still fitted exactly by
`native_contact_fit` immediately before transmission; this is a bound, not a substitute for that
gate.

## 10. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, no change to `samples`,
`temperature`, `seed_offset`, `min_support` or `similarity_threshold`, and no silent recovery. At
most one root-diagnosed recovery re-registration; a second failure closes the flight and the fix
must be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke
stops cell B2 until the fix is proven on that same four-row roster. One cell in flight at a time:
the arm seals before the twin launches.

## 11. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed
  discovery roster.
- The offline `s` in {2,3,4} sensitivity table licenses no verdict, and no threshold may be chosen
  from it after the fact.
- No component-causal attribution beyond the one moved channel: an ADMITTED result says that
  sampling plus this aggregation pays in this configuration, not that N = 5 or `s = 3` is optimal.
- Nothing about whether reviewing a sample set rather than one committed draft helps or hurts. E2c
  **removed** that difference from this cell rather than measuring it; "the Reviewer reviews the
  sample set" is a different mechanism and would be its own registered cell.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The prompt-cache assumption behind the 12.0 GPU-hour ceiling is stated, not proven.
- A structural smoke result is never a quality result.
- The fake-model proof of section 9 is a proof of *form* — state count, re-sampling, re-commit and
  rendered volume — on a synthetic world. It is never evidence about answer quality.

## 12. Analysis recipe

`docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3/analysis-recipe-v1.json` pins the four score
artifacts, the roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the commit replay
(`analysis.native_commit_replay.replay_row`), the own-null margins, the seed, the draws, the two
interval levels, the four contrasts and the metric list. It reuses the released paired-read tooling
of the 2026-09-17 TRAIN A direct anchor release rather than a private reimplementation;
`analysis.score_compare_cli` is deliberately not the runner because it hard-codes CI90 and DEV
population names.

## 13. Branch base and hash validity

This registration is based on master at `36874ed4`, which carries E2c (merged at `59db0f9b`). The
composed and protocol hashes in section 2 are the values of the fragments **exactly as committed on
this branch**: readiness `held`, the preparation requirement pinned, `prepared_phase_supply` pinned.
`compose` hashes the whole merged four-fragment document, so the coordinator's readiness flip — and
any later master merge that touches `rails.kb_policy`, `rails.knowledge_provider`,
`rails.phase_supply`, `rails.knowledge_stores` or `core.flight.runtime`, which the prepared
artifact's identity digest pins — changes them. `scripts/flights/repin_cell.py` is the reviewed tool
that does both in one step;
`docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3/README.md` section 2 gives the exact
invocation.

The method is verified: composing the **anchor's** own four fragments on this branch reproduces the
anchor's sealed protocol hash `2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`
exactly, from its run manifest.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-anchor-v3/`, outside the repository so
no receipt can dirty the tree the scoring gate reads. The table of file names, SHA-256 values and
what each proves is in `docs/readiness/2026-09-17-slurp-b2-samples5-anchor-v3/README.md` section 8.
The three `core.flight.cli check` receipts of that table also re-derive each registered protocol
hash at runtime and report `ALLOW` for every phase.
