# Frozen analysis recipe identity compatibility

Owner scope:214. Repair an offline reader mismatch before the active update finishes. No frozen recipe, scientific criterion, source worker, scoring job, queue or READ authorization changes.

## Named defect

The admitted update1 analysis recipe uses stage and members and binds the complete immutable system_search_stage and system_search_evaluation. The generic family reader expected family_id and expected_members; the new update statistics entry made the same assumption. Therefore the exact deployed recipe could not pass either entry after normal qualification. Synthetic recipes had used the reader's spelling and missed the mismatch.

The shared recipe_family_identity resolver now accepts the registered spelling only when its schema, complete stage registration, registration hash, member map and evaluation map agree. Redundant aliases must agree; initial-family aliases cannot be attached to this update form. Earlier initial and explicit family_id recipes retain their existing route. The resolver returns identities and never rewrites the pinned recipe. The family reader still requires the exact root READ, every complete member, verified seals and unique official scores; statistical analysis still checks protocol, source/configuration identity and all cohort rows.

## Proof

Fifteen new tests use the actual frozen recipe metadata with synthetic ledger authority and synthetic terminal counts. They reproduce three failures before the repair and pass after it. Conflict cases cover wrong family/member aliases, stage, missing or changed members, missing registration, changed registration hash, evaluation drift, wrong schema and ambiguous initial identities. The actual unsigned READ is also checked without opening any task result: it now reaches and correctly fails the countersignature gate instead of failing on the spelling mismatch. The recipe bytes remain unchanged.

All248 related tests pass. Scoped statement coverage is100% for stage/identity resolution and update analysis,93% for the lifecycle CLI,96% combined. Ruff, engineering-base and harness-admission checks pass. Source custody, full-family verification and score-result tests remain part of the reused test coverage; no live quality or answer is used by this proof. No model, tokenizer, tool or scorer contact is added.

## Runtime boundary

At06:50:50Z the frozen update1 process remained live. L-parent, L-parent-AA and B-parent were FINALIZED with400 rows each, one successful official score each and zero failures. B-parent-AA had1571 contacts; B-candidate-2 had not started. STOP was absent. Windows free memory was10.67GiB. Contacts are not completed rows.

The full-family READ remains unsigned. Keep waiting for the last two members; do not read partial feedback or preselect a learning parent. The already prepared update2 blind configs remain HELD. Additional CPU supply preparation is deferred while memory is close to the10GiB reserve: its pinned serialized inputs alone total approximately664.7MiB, without object and working-memory overhead. No power or host setting is inspected or changed.
