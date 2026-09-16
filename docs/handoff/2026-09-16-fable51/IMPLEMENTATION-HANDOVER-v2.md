# Implementation handover v2: candidate-bound slot views

Date: 2026-09-16. Root acceptance: model-free implementation accepted; live proof and task
effectiveness remain untested. This is an information-use successor on the older useful
dual-store agent, not a recovery of the closed typed-context flight.

## Exact source and status

- Canonical integrated commit: 7ca75217ae52da5bd0b81fc569005d5c5fdcefa1 on master.
- Isolated implementation commit: edae8bfaf67fe7b350fc6788af8e76e53ca80d57.
- Branch: codex/candidate-bound-slot-view-v1.
- WSL checkout: /home/chao/saea-worktrees/candidate-bound-slot-view-v1.
- Base: 923a0360972cb125ca1671cdd036cd72d6e30418.
- The isolated checkout was clean after its commit; canonical integration preserves the
  old failed frozen source and historical configs. No remote push was performed.

No delegate work remains running for this bounded implementation. Root reviewed scientific
scope, fallback semantics, source identity, registry integration and acceptance evidence.
Mechanical subagent checks alone were not treated as scientific acceptance.

## Changes and shared extension points

| Surface | Responsibility |
| --- | --- |
| rails/slot_binding_view.py | Bind released structured slot rows, snapshots/releases/authored source and legal intent catalog; derive runtime scope; emit full or projected card with receipt |
| core/model/native_slot_binding_view.py | Register native-candidate-slot-view-v1; project exact base/tool bodies only; label derived content; preserve original source and native groups |
| core/model/native_evidence_projection.py | Share ordered local-result document validation with the existing reference policy |
| core/model/native_framework_history.py | Validate bound context and pass it through the same framework projection boundary |
| core/model/transport.py | Bind full composed config once, forward context to raw/feature rendering, share FIT/dispatch body and pre-POST ORG receipt |
| scripts/checks/engineering_base_check.py | Discover the new canonical registered policy; no new exception |
| Three new unit/integration test files plus checker import | Scope, source conflicts, fallback, wire invariants, fake-dispatch equality, registry and error boundary |

Paths in the table are under src/speech_aware_evidence_acquisition unless beginning scripts/.
No new TaskAdapter, controller, private launcher or experiment execution framework was added.
The old reference policy remains separate. Historical/default requests keep their prior path.

The registered policy declares Python-only bind_config and validate_context hooks.
The transport refuses missing/wrong context and orphan config parameters. Only known
ValueError failures are normalized; arbitrary projector TypeError is not caught and retried.
No context object is serialized into the model request.

## Semantics that must survive continuation

1. Rebuild and verify the released authored source before using its structured relations.
   The real config binds 54 slot values, 402 intent bindings and 60 legal intent IDs.
2. Scope initial Solver by all normalized current candidates. Scope Reviewer/revision by
   that set plus the latest valid Solver intent, even when outside the candidate set.
   Preserve explicit source-bound lookup targets when present; the held experiment does
   not add a new lookup tool.
3. Exclude intermediate tool-source states when selecting the latest answer draft.
   Missing/malformed Perception or latest draft preserves full knowledge; do not reuse an
   older valid draft to conceal a malformed latest state. First Solver may have no draft.
4. Preserve every global extraction/format/omission/ambiguity/limitation/support field.
   A card with no applicable observed binding remains full. Do not infer slot illegality.
5. Exact value ID, source URI and full canonical content must match. Retain canonical
   snapshots, QueryState, dispatcher results and raw responses; derive wire content separately.
6. Record context/payload/message/view/request hashes, candidate/draft source identities,
   selected/excluded bindings and actual retained/omitted field addresses.
   Full fallback reports zero omitted fields. Derived content never impersonates full source.
7. FIT and actual dispatch use render_request_with_receipt; tests prove fake POST body equality
   and one pre-POST ORG record. This is not yet evidence from the real model service.

Root review caught and resolved an ID-to-row swap validation hole, unused draft-schema
configuration, overly broad exception handling, missing source diagnostics and ambiguous
fallback omission accounting before accepting the code.

## Verification evidence

The durable [model-free validation receipt](../../readiness/2026-09-16-candidate-slot-view-implementation-validation-v1.json)
contains config/source pins, actual source binding, counts, smoke details and limitations.

- Root affected WSL suite: 248 passed, one Windows-only skip, five third-party warnings.
- Combined statement/branch coverage for the two new production modules: 83%;
  semantic binding 81%, wire projection 92%.
- Engineering-base executable: PASS, zero new offenders.
- Ruff and staged diff checks: PASS. Seven semantic tests also passed after test formatting.
- Real composed HELD config loaded actual released source; all 54 cards were projected or
  conservatively retained under synthetic legal candidate state, without changing sources.
- Actual-source smoke was not a campaign replay. It used alarm_query/alarm_remove/alarm_set,
  all cards rather than selected runtime cards, and did not read any answer/reference.
- Raw/feature/fake-dispatch tests use pinned miniature fixtures, not live audio/model service.

No model, tokenizer, encoder, ASR or official-scoring contact occurred. No task quality was read.

Focused test entry, from the isolated WSL checkout with its absolute src on PYTHONPATH:
    /home/chao/.venvs/speechrl/bin/python -B -m pytest -q tests/unit/test_slot_binding_view.py tests/unit/test_native_slot_binding_view.py tests/unit/test_native_slot_view_transport.py

Do not repeatedly rerun the whole repository unless new changes justify it. Revalidate
changed paths and source bindings, then move toward the already selected proof.

## Held engineering configuration: ready to finish, not ready to launch

- configs/baseline/slurp-candidate-slot-view-proof4-v1.json
- configs/experiment/slurp-candidate-slot-view-proof4-v1.json

They preserve the older slurp-native-dual-store-train-fold-a-anchor-recovery-v1 role program
and intentionally retain its native episode identity. Only the candidate-bound wire view
is the scientific intervention. Both source knowledge stores stay fixed.
Projection params are store_id=slot-contracts and consumer_roles=[solver, reviewer].

The cell is HELD, with check/prepare-supply only. Fresh preparation, readiness bindings,
protocol, ExecutionPlans, exposure registration and scientific/engineering admission are
not complete. There is no model launch in this handoff.

Draft proof envelope: four already exposed engineering rows; 44 generation contacts,
176 FIT endpoints, 16 analytical actions, 117 repeated speech seconds and one
FIT-inclusive GPU hour; zero ASR/encoding/official-score jobs. Ceilings are not targets.
The first execution failure stops this proof. Verify bounds against final source/program;
do not copy a previous proof's plan or attempt identity.

Next concrete deliverables:
1. Source-frozen proof protocol and exposure bindings with independent new identities.
2. Fresh run-bound supply preparation and complete service/source readiness receipt.
3. Engineering-only live four-row FIT/generation result and structural finalization.
4. A prospective full TRAIN A fixed-agent versus view comparison and compatible direct
   anchor decision, with exact contacts, metrics, advancement and replica rule.

Do not read the closed pair's direct score, add its replica or rename its old attempt.
Do not claim the exhaustive 42.5421% ideal-body reduction is actual wire/token savings.
Do not claim engineering success proves the new view preserves or improves task quality.
