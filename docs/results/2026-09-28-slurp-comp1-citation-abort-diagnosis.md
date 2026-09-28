# SLURP COMP-1 arm abort: the Solver citation contract refused a repeated id

Status: **DIAGNOSIS AND FIX PROPOSAL. NOTHING REGISTERED.** Written with zero model, tokenizer,
encoder, scorer and server contacts. The run directories, attempt records, driver log and queue log
were read read-only. Serving, queues, the batch driver and the flight worktree were not touched.
This note contains no utterance text, transcript, gold label or model output. It reports only ids,
counts, field names, hashes and exception text.

## 1. What failed, and what completed before it

The chain `COMP-1 + G5` ran at flight commit `cb628f59` (driver log
`/home/chao/batch-campaign-1-comp1-20260928T004655Z.log`, queue log `/home/chao/queue-e41-comp1.out`).
The campaign plan `configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json` lists two cells:
step 0 is `slurp-native-stage3-comp1-aa-fold-a-v1`, the shared A/A, and step 1 is
`slurp-native-stage3-comp1-fold-a-v1`, the arm. The queue log says "arm failed on step 1 (campaign rc 1,
inspect rc 3)", so the ARM is the cell that failed.

| run id | attempt state | manifest | calls | rows |
| --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1` | OPENED (normal for a smoke; it is not scored) | run and generation manifests COMPLETED at `cb628f59` | 16 | 4 of 4 |
| `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` (shared A/A) | **FINALIZED** | COMPLETED at `cb628f59`, scored | 4,435 | 1,080 of 1,080 |
| `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` (arm) | **ABORTED** | none (no seal stage; `flight-receipts.json` stages are preflight, preprocess and serve) | 1,913 | see below |

The ABORTED arm attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1` recorded
`actual = {calls: 1913, audio_seconds: 5171.3779375}`. Its trace has 10,035 records: 1,913 each of
`MODEL_REQUEST`, `MODEL_RESPONSE`, `MODEL_WIRE_RESPONSE` and `COST`, plus 2,383 `USE`. It is
132,650,912 bytes with SHA-256 `029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997`.
The arm contacted **472** rows. **471** of them carry a settled `/native-episode` receipt, so they
are COMPLETE in the `core.flight.resume` sense. **1** row is INCOMPLETE, and it is the failing row.
**608** rows were never started. No row was sealed to `outputs.jsonl`, and no score exists or may
be read.

## 2. The code path that raised

The failure is verbatim in the attempt record and the driver log:
`NativeEpisodeError: native episode node failed: [100054] component 'solver_0_role' execute 'invoke'
error, reason='cited-answer contract refused: intent citations must be unique non-blank ids'`.

1. `rails/solver_citation.py:322` (master) is in `parse_cited_answer`. It raised
   `SolverCitationError("intent citations must be unique non-blank ids")` when
   `len(set(intent_ids)) != len(intent_ids)` or an id was blank. `:317` raised the entity
   analogue, "an entity citation repeats an evidence id".
2. It is called from `bind_cited_completion` (`solver_citation.py:398`) on every Solver completion
   with `finish_reason == "stop"`.
3. `rails/runner.py:2979-2986` (`capture_completion`, the completion sink of every native contact)
   converted the error into `RailsRunnerError("cited-answer contract refused: ...")`.
4. The error surfaced through the OpenJiuwen node, and then through
   `reproduction/ojw/native_episode.py:1775-1812` (`invoke_direct`). That handler maps only two
   error classes to a per-row terminal outcome. The first is a context-fit error under
   `compact-or-abstain`. The second is a *finite* error (a `length` or `content_filter` finish)
   under `deliver-latest-or-abstain`. Any other error becomes
   `NativeEpisodeError("native episode node failed")`.
5. `reproduction/ojw/runner.py:627-648` records the row failure and re-raises it after the drain,
   which aborts the whole arm.

**The failing input shape.** This is a model-free replay of the sealed trace
(`MODEL_REQUEST.decoding_params.response_format` gives the supplied ids and `MODEL_RESPONSE.text`
gives the response):

- contact `flight-1854`, sample-id SHA-256 prefix `7a8f353a32d6`, response-text SHA-256 prefix
  `6bb70bf95b5e`;
- `finish_reason = "stop"`, and the envelope is grammar-valid;
- the **intent citation list has 3 items and 1 distinct id**, so one supplied id is repeated three
  times;
- the list has no blank id and no unsupplied id (43 ids were supplied), and the entity citations
  are valid.

It is the only one of the arm's 482 cited Solver responses with a repeat. No response in the arm had
an entity repeat or a blank id.

**Root cause.** The per-contact grammar (`envelope_schema`, `_id_array`) enumerates the supplied ids
but carries no `uniqueItems`. This is deliberate: `test_solver_citation.py` asserts that
`uniqueItems` is absent, and llama.cpp's schema-to-grammar has no uniqueness constraint anyway. So
constrained decoding can legally emit a repeated id, while the parser treated a repeat as a
contract breach. The `bind_cited_completion` docstring assumed that a stop-finished envelope
"satisfies the contract by construction". That holds for enum membership and bounds, but not for
uniqueness.

**Why a row failure became an arm abort.** Neither disposition policy covers this error.
`finite_completion_policy = deliver-latest-or-abstain` (E13) covers only a completion that the
core ended before authoritative delivery (`length` or `content_filter`; see
`rails/config_tables.py:373-384`). `react_exhaustion_policy = continue-without-answer` (E22) covers
only ReAct exhaustion. A grammar-valid `stop` completion that the seal refuses has no per-row
disposition. The programme rule is that a malformed row abstains and never aborts the arm, so the
defect is a missing containment. It is the same failure class as the B7a and B8b-anchor aborts,
where a parser default of `raise` killed the arm.

## 3. Did the smoke exercise the citation path?

Yes. The smoke exercised the path, but not the failing shape. All 4 smoke rows produced one cited
Solver response each. Each response had `finish_reason = stop`, each parsed `ok`, and each intent
list had exactly 1 id. So the smoke proved the form (grammar, seal and I7n unwrap) but could not
exercise a repeat.

The repeat rate is 1 in 482 cited contacts. Greedy decoding is not bitwise reproducible across
llama-server runs, so re-flying the failing sample is not guaranteed to reproduce the repeat either.
A 4-row dry run can therefore prove only that the fixed tree still flies the cited path end to end.
It cannot prove the repeat disposition. That proof is model-free and is done here:

- the unit test `test_bind_seals_the_comp1_abort_shape_and_records_the_collapse` reproduces the
  exact shape (3 intent items, 1 distinct, cited entities, `stop`);
- the replay below re-binds every sealed cited response under both the master code and the fixed
  code.

| trace | cited Solver contacts | identical capture (state bytes, cited ids, record) | refused by master and sealed by the fix | regressions |
| --- | --- | --- | --- | --- |
| smoke | 4 | 4 | 0 | 0 |
| arm | 482 | 481 | 1 (`flight-1854`; the intent list collapses from 3 to 1; `duplicate_citation_ids_dropped = 2`; the supplied-id check passes) | 0 |

The recommended 4-row dry run should therefore be a form proof of the fixed tree, the same as the
smoke. It must be recorded together with this replay as the fix's proof, not as a proof on its own.

## 4. The smallest fix (branch `fable/comp1rec`)

The fix touches one file, `src/speech_aware_evidence_acquisition/rails/solver_citation.py`:

- `parse_cited_answer` (`:303`) treats each citation list as a set. It collapses a repeated id to
  its first occurrence (`:334`, `:341`) and counts the drops in `CitedAnswer.duplicate_ids_dropped`.
- A BLANK id is still refused (`:333`), because the enum grammar cannot emit one, so a blank id
  means the server did not honour the grammar. An UNSUPPLIED id is still refused by
  `validate_citations_supplied`, never dropped.
- `bind_cited_completion` (`:380`) adds `duplicate_citation_ids_dropped` to the row's
  `solver_citations` record only when the count is nonzero (`:426`). Every record without a repeat
  is therefore byte-identical to its prior self, and the replay confirms 481 of 481.
- The answer bytes, `cited_value_ids`, the request bytes and the rendered response format are
  unchanged. The I7n unwrap normaliser shares the parser, so delivery and seal agree.

**Identity.** `solver_citation.py` is **not** in the prepared-supply identity set.
`core/flight/runtime.py:7504-7554` (`_phase_seed_inputs`) hashes `kb_policy`, `knowledge_provider`,
`phase_supply` and `runtime.py`, and conditionally `knowledge_stores`, `candidate_semantic_supply`,
`slurp_candidate_proposal` and `released_target_index`. `solver_citation.py` is also absent from the
packet and preparation implementation hashes (`runtime.py:7185-7254`). The COMP-1 registration lists
it only under `authority_relpaths`, which is not hashed. Merging the fix therefore does not move any
ready cell's prepared identity. It moves only the flight commit.

This is a containment, not an abstention. The design choice was between collapsing the repeat and
abstaining the row. Collapsing changes nothing observable except a count, while abstaining would
discard a valid answer. Wiring a generic "seal refusal abstains the row" disposition into
`native_episode.invoke_direct` would be the broader fix. It is not needed for this shape, and it
would touch the episode's terminal custody.

**Tests.** `tests/unit/test_solver_citation.py` gains five tests:

- `test_the_specialised_grammar_admits_a_repeated_id` (root cause; passes on master too);
- `test_a_repeated_intent_id_is_collapsed_and_counted_not_refused`;
- `test_a_repeated_entity_id_is_collapsed_and_counted_not_refused`;
- `test_bind_seals_the_comp1_abort_shape_and_records_the_collapse`;
- `test_the_unwrap_delivers_the_comp1_abort_shape_like_the_seal`.

The two old "repeat is refused" parametrised cases were replaced with blank-id cases. On master the
four behaviour tests fail. On the branch, `test_solver_citation.py` and
`test_native_episode_runner_solver_citation.py` pass 45 of 45.

## 5. Recovery route

**Resume-recovery (E10, `core/flight/resume.py`; precedent
`docs/readiness/2026-09-18-slurp-b4b-replicate-v2-resume-v1.md`) is mechanically available.** A
recovery cell under the SAME run id `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1`, with a new attempt id,
declares:

```
resume_from = {attempt_id: "attempt-slurp-native-stage3-comp1-fold-a-generation-v1",
               trace_sha256: "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"}
```

It is validated at `core/flight/campaign.py:69-85` and `runtime.py:1426-1442`. The recovery keeps the
471 COMPLETE rows by trace replay and seal merge, and it flies the other 609 rows (608 never started
plus the 1 incomplete row). That spends roughly 2,500 more contacts instead of re-spending 1,913.
The caps are run-cumulative, and 1,913 plus about 2,500 is far inside the arm's 11,880 generation
cap.

**The precondition problem.** Owner decision 22 limits resume-recovery to "code and request bytes
unchanged: an infrastructure failure, never a harness defect" (`resume.py:3-6`). This abort is a
harness defect, and the fix changes code. The request bytes are unchanged, and every kept row's seal
is byte-identical under the fix (the replay shows 481 of 481 identical captures). The kept rows are
re-verified by `core.bundle.verify_bundle` against the predecessor trace, so the letter of the rule
is broken but not its purpose. The owner must decide whether that byte-identity proof admits a
resume.

**Fallback.** If the owner declines, the fallback is an ordinary recovery re-registration (precedent
`docs/readiness/2026-09-18-slurp-b5e-combination-v1-recovery-v1.md`). It would use a new `-REC`
run id over the full 1,080 rows, re-spend the 1,913 contacts, and mark the aborted run's exposure
row `consumed = yes`.

**Either route needs the following:**

1. Merge `fable/comp1rec`. The ready cells' identities do not move, but the flight commit does.
2. Write one addendum under `docs/readiness/` that cites this note, the root cause, the replay
   table and the trace SHA-256.
3. Add an exposure-ledger row before any contact.
4. Run the 4-row dry run of the fixed tree as the form proof.
5. Fly the recovery cell. The shared A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` is FINALIZED and
   is **not** re-flown.

This is the flight's single permitted recovery re-registration. A second failure stops the flight.

**Same hazard elsewhere.** The COMP-1 DEV-2000-ADDED pair
(`configs/experiment/slurp-native-stage3-comp1-dev2000-added-*.json`) arms the same contract and
would hit the same refusal at about the same rate (1 in 482 contacts) until the fix is merged.
