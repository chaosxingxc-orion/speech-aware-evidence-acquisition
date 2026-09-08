# WAVE W1 of the openJiuwen convergence: the Reviewer seat (2026-09-08, v1)

**Status: LANDED, model-free, zero model contacts, no GPU.** Branch `wt/ojw-w1` from master
`979a730e`. Authority: owner Decision 11-B (items #1 and #2 of the ordered change list in
`docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md` §5.2) and owner Decision
11-C (the Reviewer is criticism only). Nothing here is a preregistration, an admission, or a
flight; no cell is flyable on the strength of this note.

The assessment's verdict was that the openJiuwen agent layer already carries three of the four
agents and the loop that connects them, and that the missing Reviewer seat is *an additive change
inside existing signatures* — a fourth injected callable on the controller, a config seam beside
`phase_supply`, and a registry beside the ones `core.base` already holds. That is exactly what
landed: **no graph node, no new class outside the bases, no `rails/probes/` module, no
`docs/checks/*/launcher/` directory, and not one line changed in `rails/runner.py`,
`rails/knowledge.py` or `reproduction/ojw/`** (the files W2 and W3 own).

---

## 1. What landed

| commit | what |
|---|---|
| `e7ea1cfa` | the read-only assessment, placed in the study repository verbatim |
| `fb49e351` | `core.base.JUDGES`, the `Judge` protocol, the criticism-only verdict types, the `REVIEW` trace channel, the `judges` rule in the engineering-base gate, and the Decision 11-C amendment to the design note |
| `da44e757` | the six judges that already existed, registered from `core/policies.py` |
| `d9d70f80` | the Reviewer seam on `EvidenceAgentController`, the `phase_review` config block, the `REVIEW` records and the run-outcome summary |

### 1.1 The registry and the protocol

`core.base.JUDGES` is a `JudgeRegistry`, the same one-`Registry` mechanism every other pluggable
dimension uses, with one difference: **it checks entries at the door.** `register` refuses an entry
that is not callable, that carries no `id`/`version`, that declares an `id` different from its
registry name, or that does not declare `criticism_only=True`.

The protocol is `judge(draft, material, state) -> JudgeVerdict`, with `id` and `version` as
receipt-able identity. Judges are stateless and deterministic.

### 1.2 Decision 11-C, made structural

The owner rule — *the Reviewer scores and flags, it never proposes a revision; revisions belong to
the Solver under the system's constraints* — is enforced by the verdict type, not by convention:

* `JudgeVerdict` carries `judge_id`, `version`, an optional `score` in `[0, 1]`, `flags` and
  `reasons`. `JudgeFlag` carries `code`, `severity`, `reason`, an optional `field_ref` (a
  structured location such as `entities[2].type`) and an optional `span` (a half-open word index
  pair, the convention `core.replay_signals.flag_spans` and `core.flag_sources` already use). Both
  point *into* the draft; neither carries content.
* `core.base.assert_criticism_only`, asserted on both types at import, walks their declared fields
  and refuses any field that could carry a replacement: a field may name a scalar, a tuple of
  scalars, or a type already proven criticism-only. **A `Mapping`/`object`/`Any` field is refused
  outright**, because a mapping can smuggle a whole rewritten answer under any key.
* every text-bearing field is capped at `MAX_JUDGE_TEXT_CHARS` = 240. A reason is a sentence; 240
  characters cannot carry a replacement transcript, a repaired tool call or a re-answered slot
  frame.

Adding a leaky field later fails at import time rather than in a review comment. The design note
(`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`) is amended in place: the
section-2 Reviewer row and a dated paragraph in section 4 now state Decision 11-C and supersede the
earlier condition-3(c) reading that let a core-as-critic phase "flag **and propose**".

### 1.3 The seam

`EvidenceAgentController.__init__` gains one keyword-only `review_for_phase`, default `None`,
beside `material_for_phase` / `supply_for_phase` / `stop_policy`. It is called **once per phase**,
after that phase's response is sealed as an `AgentStateArtifact` and before the stop decision, with
the same "as of the answer just sealed" synthetic context `supply_for_phase` already receives (that
construction is now one helper, `_review_context`, used by both). What it returns is type-checked
as a sequence of `core.base.JudgeVerdict` and recorded on `controller.review_verdicts` —
observability only, exactly like `sealed_states`.

`rails/phase_review.py` is the config seam, parsed fail-closed against the program the way
`rails/phase_supply.py` is:

```json
"phase_review": {
  "draft": {
    "judges": ["earnings-numeric-format-flag-v1", "e21-substitution-alignment-flag-v1"],
    "on_flag": "record",
    "params": {"e21-substitution-alignment-flag-v1": {"max_span_tokens": 4}}
  }
}
```

Refused, before any contact: a non-object; a phase the program does not declare; an unknown key; an
empty or repeating `judges` list; a judge id resolving in no `core.base.JUDGES` entry; an `on_flag`
outside the vocabulary; `params` naming a judge the phase does not review; and a `phase_review`
block on a `policy: "fixed"` arm (dead config — a direct arm runs no phase program and would review
nothing; the same rule and the same reason as `phase_supply`).

`core.flight.FlightRuntime` resolves the block into the callable, threads it through both dispatch
shapes (`run_program`'s per-phase whole-roster waves and `run_continuous_program`'s single
trajectory), names the reviewed phases in the dispatch record, and carries the summary as
`phase_review` in the `run_phases` and `wire_check` outcomes: rows reviewed, rows flagged, and per
judge the version, rows flagged, flag count and counts by severity.
`bind_phase_review_material` injects the carrier material a judge reads and no fragment can hold
(a legal-label inventory, a per-intent slot block, a candidate roster) — never the judge's
identity, which still has to resolve in the registry. A config `param` wins a key collision,
because config is what rides the config hash.

### 1.4 The `REVIEW` trace record

`contracts.boundary` gains a sixth research-axis channel, `REVIEW` with the `review_` prefix, for
the same reason `REPLAY` is a fifth: a review verdict is neither an observation, an organization, a
supply nor a use, and folding it into one of those namespaces would make two authorities for one
decision. One record per reviewed row:

```
channel REVIEW, id "<sample_id>/<phase>/review"
review_schema, review_phase, review_sample_id, review_on_flag, review_judge_ids,
review_response_sha256, review_verdicts[], review_flags_total
```

hashed by `TraceRecord.content_hash` like every other record. The records are **collected per row
while the roster flies and written once, in sorted order, after the wave settles** by
`rails/phase_runner.py` — the buffer-then-flush-deterministically discipline `rails.runner` and
`core.tracing` already use, and the reason `rails/phase_review.py` never touches the sink from
inside a trajectory. `review_verdicts` is rendered through `JudgeVerdict.as_json`, so a REVIEW
record cannot carry a proposed revision either.

### 1.5 The gate

`scripts/checks/engineering_base_check.py` now resolves every `judges` value in `configs/` against
`core.base.JUDGES`, matched at **any depth** (a `judges` list is declared per phase inside
`phase_review`, so the parent object name cannot be hard-coded — the same reason `NESTED_ID_KEYS`
is an any-depth search). An unregistered judge id is the same defect class as an unregistered
policy id: a config that reads as if it reviews and does not. The gate PASSes; the ratchet baseline
is unchanged.

---

## 2. The byte-identity proof

The claim: **a reviewed cell sends exactly the bytes an unreviewed cell sends.** It has to hold for
two different reasons — the paired contrast a judge's admission receipt needs is one config key
against its null arm (owner rule of 2026-09-03, "one base, thin derivations"; design note §8), and
Decision 11-C says criticism does not steer.

It holds in three layers, weakest to strongest:

1. **Default.** `review_for_phase=None` is the constructor default. Every existing caller —
   `rails.phase_runner.run_agent_phase` / `run_program` / `run_continuous_program`,
   `core.flight.FlightRuntime`, `rails.controllers.default_controller_factory` — reaches the same
   code it reached before. The whole pre-existing controller suite
   (`tests/unit/test_rails_controllers.py`, 54 tests) and phase-runner suite
   (`tests/unit/test_rails_phase_runner.py`, 22 tests) are green **unchanged**: not one existing
   test was edited for this wave.
2. **Structural.** The review call happens *after* the response is sealed and its result is stored
   in a dict nothing else reads. `advance` computes `is_last`, the stop decision, the supply
   decision, the transition, the successor `QueryState` and the next contact from exactly the
   inputs it did before. There is no branch on a verdict anywhere in `rails/controllers.py`.
3. **Measured.** `tests/unit/test_phase_review.py::
   test_a_reviewed_trajectory_sends_byte_identical_waves_to_an_unreviewed_one` runs the same
   two-phase program twice over the same responses — once with no reviewer, once with a real
   registered judge that really does flag both phases — and asserts equality of a JSON fingerprint
   covering the dispatched contact (`AgentContactPlan.as_json`, which includes the instruction),
   the transition, the successor `QueryState` content hash, the next contact, the sealed agent
   states and the final-response contact id. It then asserts that the review actually happened on
   both phases with non-empty flags, so the test cannot pass by reviewing nothing.

`on_flag: "record"` is the only accepted value today, so layer 3 covers every legal configuration.

---

## 3. The judge inventory

Six judges, each a thin adapter over a **frozen** function that already shipped. No logic was added
or changed; the adapter calls the function, turns what it returns into a verdict, and carries a
version.

| id | version | wraps, unchanged | fires on | severity |
|---|---|---|---|---|
| `slurp-legal-label-flag-v1` | 1.0.0 | `reproduction.slurp_scoring.parse_slu_response`, `LegalIntentInventory` | unparsed response; missing label; scenario outside the closed space; action not one this scenario carries | block |
| `slurp-slot-schema-conformance-v1` | 1.0.0 | `reproduction.slurp_scoring.parse_slu_response` + the row's own block | unparsed; a type the row's own block did not list; a repeated type (MF-9 §5.1, verbatim) | block / warn |
| `earnings-numeric-format-flag-v1` | 1.0.0 | `reproduction.numeric_value_accuracy.whisper_words` / `is_numeric_value` / `numeric_kind` | a digit-bearing normalized token classified `other` — carries digits, matches no well-formed numeric shape | warn |
| `e21-substitution-alignment-flag-v1` | 1.0.0 | `core.repair_alignment.accept_entity_repair` | each of `REFUSAL_REASONS` as `refused:<reason>`; each non-zero `REJECTION_CLASSES` count as `rejected_<class>` | block / warn |
| `replay-logprob-flag-v1` | 1.0.0 | `core.replay_signals.flag_spans` | a contiguous run of words below the configured decode-confidence floor | warn |
| `roster-band-flag-v1` | 1.0.0 | `core.flag_sources.roster_band_flags` | a 1–2 word draft span band-matching a candidate term at weighted grapheme distance in `[0.05, 0.45]` | warn |

Registration is from `core/policies.py`, the canonical `core.base` site the engineering-base gate
reads, so the ids resolve the way `policy` and `evidence_source` do. Heavy modules are imported
inside each call, so importing `core.policies` stays as light as it was.

### 3.1 Two judgement calls that Decision 11-C forced, recorded rather than left implicit

* **The legal-label judge does not name the nearest legal pair.** The frozen projection it sits
  beside computes exactly that; naming it in a flag's reason would be handing over the
  replacement. The judge says only that the pair is outside the closed space. Asserted by
  `test_legal_label_judge_never_names_the_nearest_legal_pair`.
* **The roster-band judge does not name the candidate it matched.** The matched roster term *is*
  what a repair would substitute. The Solver gets the roster through its own traced knowledge
  supply and the Observer re-listens to the span; what the judge contributes is where to look.
  Asserted by `test_roster_band_judge_never_names_the_candidate_it_matched`.

Both are the conservative reading. If a later owner ruling says a judge may name the target it
matched, that is a change to these two adapters and to two tests — not to the protocol.

### 3.2 What is deliberately NOT a judge

`SCORERS` entries stay scorers. `numeric-value-accuracy-v1`, the SLURP official scorer and the
`a2t-toolcall` scorer are evaluation instruments and are gold-bound; the study rule that a scorer
never runs inside the loop is unchanged, and
`earnings-numeric-format-flag-v1` exists precisely because the gold-free half of the numeric
question is a different object from the scorer.

`slurp-legal-label-projection-v1` and `e21-entity-repair-substitutions-v1` stay a scoring-side
post-processor and a registered response post-processor. Each has a judge beside it that flags
what it repairs; neither was moved, wrapped or changed.

---

## 4. What W2 and W4 still need

### 4.1 `on_flag: "loop"` — refused by name, with the two rails that block it

A flagged row spending another contact on the same phase is not a change to `phase_review` or to
`EvidenceAgentController`. It is a change to two invariants in `rails/runner.py`, which this wave
does not own:

* `_validate_new_agent_states` refuses an `AgentStateArtifact` whose `state_id` already exists, and
  the controller's state id is `f"{phase}:{sample_id}"`. A phase cannot seal twice for one sample
  without a per-attempt id scheme.
* `schedule_wave` refuses a reused `contact_id`, and a phase's contact id comes from its
  `PhaseMaterial`. A re-ask needs a per-attempt contact identity too.

Both are deliberate rails. `rails.phase_review.LOOP_REFUSAL_REASON` names both, and a fragment
declaring `on_flag: "loop"` gets that message before any contact rather than a half-wired loop that
silently records instead. `tests/unit/test_phase_review.py::
test_on_flag_loop_is_refused_by_name_with_the_two_runner_rails_that_block_it` pins the message
content so the seam cannot be quietly widened.

### 4.2 The Observer seam consuming flags (assessment changes #3 and #4)

The flags this wave produces are already the right shape for the selective re-listen the design
names: a half-open word span plus a field reference, per row, in a `REVIEW` record hashed beside
the run's own trace. What is missing is downstream and belongs to W2:

* **#3, the observation invariant.** `rails.knowledge.assert_agent_step_binding`'s
  `stable_query_fields` freeze `speech_packet_id`/`speech_packet_sha256`, so no step may re-listen.
  Relaxing that to "identical, or a registered `SliceRegistry` derivation of the trajectory's
  parent media, carrying the derivation record", while keeping `query_sample_id`,
  `use_split_identity_hash`, `use_partition_role` and `query_source` immutable, is what makes a
  re-listen expressible at all.
* **#4, `observe_for_phase`.** A fifth injected callable that takes the *verdicts this wave already
  returns* plus the next phase, cuts the flagged span with context through `core.span_surgery.
  cut_span` + `core.model.SliceRegistry`, and returns the derived packet id/sha. The verdicts are
  available to it two ways with no further change: as the return value of `review_for_phase`, and
  on `controller.review_verdicts` keyed by phase.

Concretely, what W2 needs from this wave and now has: a typed flag with a span, a per-row
collection keyed by `(phase, sample_id)`, and a refusal that says exactly which two runner rails
have to move first.

### 4.3 The `judges` config table with a null arm (assessment change #6)

Change #6 wants `observe: {...}`, `judges: [...]` and `toolkits: {...}` as composed-config objects
beside `phase_material`/`phase_supply`, every entry nullable, `null`/`[]` byte-identical to today.
Half of that is done: `phase_review` is the object, `judges: []` is refused (an empty list reads as
"reviewed by nobody", which is a config defect, not a null arm), and the null arm is **omitting the
block**, which is byte-identical by §2. The engineering-base gate already resolves a `judges` list
at any depth, so a future top-level `judges` key needs no second rule. What change #6 still adds on
top is the `observe`/`toolkits` siblings and `PhaseSpec.knowledge: "optional"`, neither of which
this wave touches.

No `configs/` fragment declares `phase_review` yet. That is deliberate: a judge enters a default
plan only through the admission gate below, and the first fragment to declare one should be the
cell that carries its receipt.

---

## 5. The model-free admission plan, per judge

Design note §8's admission gate applies to a judge like any other harness module: module ON versus
module OFF, same harness, same roster, `n >= 400`, cluster bootstrap, CI90, non-inferiority with
the margin from the carrier's own null, status ADMITTED / NEUTRAL / HARMFUL. But a judge under
`on_flag: "record"` changes no bytes, so **its own admission question is different and cheaper**:
not "does it help the score" but **"when it fires, is the row actually wrong"** — precision — and
**"of the rows that are wrong, how many does it catch"** — recall.

Both are measurable **model-free, on outputs this repository has already sealed**, at zero
contacts: replay the sealed responses through the judge and join against the sealed scoring.

| judge | carrier | sealed population to replay | already measured | still to measure |
|---|---|---|---|---|
| `slurp-slot-schema-conformance-v1` | SLURP | KC-S1b's own 1,000-row flight | **precision 72.09 %** on **86 flagged rows (8.6 % of the roster)**, 62 of which carry an unmatched gold mention, reaching **88** unmatched gold mentions (MF-9 §5.1) | recall against the 527 unmatched gold mentions: 88/527 = **16.7 %** as MF-9 reports it; per-intent breakdown not yet done |
| `slurp-legal-label-flag-v1` | SLURP | the closed-list re-lock's sealed rows | fires on **39 of 997 eligible rows** on CLOSED-LIST (the rows the projection legalised), 37/996 on KU-S1c revise, 38/456 on KC-S1b (projection re-lock verdict §4) | precision is 1.0 **by construction** (a pair outside the closed space is illegal, not suspected); the useful quantity is the share of flagged rows whose gold intent differs — **2 of 39** landed on gold after projection, so the flag marks a genuinely wrong row far more often than it marks a recoverable one. Report it as "flagged rows that are gold-wrong", not as a detector's precision |
| `e21-substitution-alignment-flag-v1` | Earnings-21 | KC-E1f's sealed 1,593 windows, both arms | the refusal counts are already in the verdict: **82 refused** (content arm) and **72** (form arm) of 1,593 windows; 447 / 498 delivered unchanged without a refusal | whether a refused window carries a real entity error, joined against the ConEC entity-WER mirror — the join is model-free and the rows are sealed |
| `roster-band-flag-v1` | Earnings-21 | the P1 flag-eval slices | **proper-name P@1 = 0.252**, against the production logprob flags' **0/17** entity hits (`2026-08-14-p1-ceiling-verdict.md` finding 1) | recall on the same slices, and precision on the OBS-E1 speaker-turn units once those seal |
| `replay-logprob-flag-v1` | Earnings-21 | the same P1 slices | the negative result is the measurement: **0 of 17** real entity errors flagged | its value is not entity targeting; measure it instead on the E22 semantic-error taxonomy, where the failure mode is clip-boundary bleed rather than a name |
| `earnings-numeric-format-flag-v1` | Earnings-21/22 | the full-44 direct baseline and the E22 DEV arms | **nothing** | the base rate of `other`-classified numeric tokens, and whether a flagged token co-occurs with a numeric-accuracy miss. Expected to be small and precise; report the base rate before proposing any use |

Three rules for those measurements, so a judge's number means what it says:

1. **A judge's precision is a property of a roster, not of a judge.** Every figure above is
   reported with the sealed run it was measured on and its row count.
2. **A judge that fires on almost nothing is not thereby good.** MF-9 already makes the point: the
   `silent` judge flags 39.4 % of rows at 39.34 % precision and is the trap; the `schema` judge
   flags 8.6 % at 72.09 % and is the sharp one. Report flagged-share beside precision, always.
3. **A judge's admission is not a mechanism's admission.** Measuring a judge model-free costs zero
   contacts and settles only whether the flag is trustworthy. Whether *acting* on the flag helps is
   a separate, contact-spending cell that cannot be run until §4.1 and §4.2 land.

---

## 6. Gates, and what is not green

* `ruff` clean on every file this wave touched. (Four pre-existing `F401`s remain in
  `analysis/a2t_scorer_v2_study.py`, `analysis/information_audit.py` and
  `reproduction/audio2tool_official/metrics.py` — untouched here.)
* `python scripts/checks/engineering_base_check.py` — **PASS**, ratchet baseline unchanged.
* Targeted suites green: `test_rails_controllers` (54), `test_rails_phase_runner` (22),
  `test_phase_review` (38, new), `test_core_judges` (44, new), `test_judge_registry` (20, new), plus two new
  `judges`-rule cases in `test_engineering_base_check`,
  `test_engineering_base_check`, `test_phase_supply`, `test_phase_supply_cells`,
  `test_phase_material`, `test_policies`, `test_scorers`, `test_flag_sources`,
  `test_replay_signals`, `test_e21_repair_alignment`, `test_legality` — **692 passed**.
* Whole suite, on a clean tree: **8,442 passed**, 14 skipped. Sixteen failures and one collection
  error remain, all pre-existing and none in a file this wave touched:
  * eight `a2t_*_preprocess` tests hard-require `PYTHONPATH` to contain the literal main checkout
    path `.../studies/speech-aware-evidence-acquisition/src`, so they cannot pass from any
    worktree;
  * `test_cross_carrier_tail2s_fragments` (2) and `test_a2t_canonical_family_secondary_roster` (1)
    depend on `SPEECHRL_DATA_DIR` packet roots and committed receipt content;
  * `test_pemb3m_flight` (2) and `test_pemb4r_flight` (2) fail on umbrella-lock content drift
    against a pinned binding sha256;
  * `test_engineering_base_check::test_regex_extraction_agrees_with_package_import` fails **only
    under a whole-suite run**, on `EVIDENCE_SOURCES` — another test module registers extra
    evidence sources into the global registry, so the import side outgrows the source scan. The
    `JUDGES` entry agrees in both directions; the test passes in isolation and in every targeted
    group above;
  * `test_build_a2t_g6_family_sweep` cannot import `scripts.build_a2t_g6_family_sweep` because
    `verl` installs a top-level regular `scripts` package into the shared venv, which shadows the
    repository's namespace `scripts/` regardless of `PYTHONPATH` order.

## 7. What this wave deliberately did not do

* No `configs/` fragment declares `phase_review`, and no cell is preregistered.
* No judge was added, and no wrapped function was changed. The novelty is entirely that a check
  which existed can now be **declared, versioned, traced and counted**.
* `on_flag: "loop"` is refused, not stubbed.
* `rails/runner.py`, `rails/knowledge.py`, `reproduction/ojw/*` and `rails/tools.py` were not
  touched: those are W2's and W3's, and this wave's design was chosen so that none of them had to
  move.
