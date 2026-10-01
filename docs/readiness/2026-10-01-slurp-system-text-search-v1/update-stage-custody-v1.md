# Prospective membership for text-policy update rounds

This model-free implementation closes a mismatch in the owner214 lifecycle:
an invalid proposal must consume its opportunity without entering a flight,
but the earlier feedback check required all eight nominal members regardless
of proposal disposition. Freeze the actual complete family before its first
run. Never remove a member after contact or use a task result to decide which
members belong to the family.

## Freeze the proposed family

Use `scripts/system_text_search.py --archive <archive> freeze-update` with
`--protocol`, `--round 1|2|3`, `--member-bindings` and `--data-root`. The command
creates `stages/update-N.json` in the external archive. It is create-only and
does not prepare a supply, launch a model, score, countersign or admit a run.

The input map must account for all eight prospective slots:
`L-parent`, `L-parent-aa`, `L-candidate-1`, `L-candidate-2`, and the corresponding
four B slots. Give each a distinct confined run ID. For a valid candidate or
comparator, include its archived `bundle_id` and prospective runtime
`config_hash`. An invalid candidate retains its reserved run ID, with both
other fields null. An existing run directory, including an excluded member's
directory, prevents the freeze.

Every round consumes four proposal opportunities. Retain each exact input,
raw response and import disposition. Recheck the response against its frozen
allocation, identity, schema, parent set and token limits. Recheck sequence-wide
model identity and session separation. An edited `invalid` flag cannot exclude
an otherwise valid proposal. Valid no-change and duplicate proposals stay in
the family; they do not earn a replacement proposal. A compiler failure without
a recorded, objectively invalid import remains a blocking preparation failure,
not an automatically excluded member.

Each successful compilation now writes `compilations/<branch>-<round>-<slot>.json`.
It binds the bundle, proposal input, exact import and compiler configuration.
The bundle retains the proposal and cumulative exposure identities. The final
runtime configuration hash supplied to the freeze is the coordinator's
prospective composed configuration identity, not independently recomputed by
this command. Supply preparation, configuration verification, FIT, exposure
registration and root admission remain mandatory in the existing flight path.

Keep both parent/A/A pairs even when all four candidates are invalid. The
admitted trajectory cap is 400 times the admitted member count, at most 3,200;
the official score-job cap is that count. No unused candidate allocation moves
to another slot or round. Both first-round parents and every B parent remain
the seed. In rounds two and three, both L proposal inputs must bind the exact
preceding recorded retention and its first selected parent. Recheck cumulative
source isolation for every admitted bundle against the current full roster.

## Carry membership through the read gate

Copy the frozen registration into the prospective analysis recipe's
`system_search_stage`. Its `expected_members` must equal the recipe's exact
family mapping, and its `evaluation` must equal `system_search_evaluation`.
Register the family-specific READ row before launch. Its later root
countersignature still requires every admitted member independently finalized,
sealed and scored exactly once. No existing recipe is rewritten by this tool.

The complete feedback reader checks these bindings before opening any outcome
or reference source. Subsequent stage validation uses the frozen admitted
members rather than the nominal eight slots. Without a valid recipe-bound
stage registration, the original full-slot requirement remains. Missing an
admitted member, changing the roster, or relabeling a post-contact failure as
a proposal exclusion is refused.

Project L's feedback only after whole-family qualification. Its read-authority
record keeps an opaque hash of the complete stage registration, not B's
proposal dispositions or allocation details. Apply the same projection to the
retention record included in later L inputs. Preserve the full record for the
root evaluator. B's proposer still receives no feedback or evaluator selection.

## Evidence and remaining work

Tests use synthetic proposals, policies, receipts, complete feedback and
temporary archives. They cover zero, one and four invalid candidates; malformed
or over-budget responses; forged exclusions; missing compilation; existing run
artifacts; changed inputs or responses; later-round parent substitution; mixed
model or reused-session history; exact READ binding; and branch projection.
The accompanying validation receipt records final counts and coverage.

Only update rounds one through three are covered by this membership freezer.
Actual candidate flight cells, their supplies and admissions have not been
materialized. The common-selection stage still needs its separate prospective
membership binding when fewer than two active versions survive per branch.
This correction adds neither a second dispatcher nor a scientific verdict.

The CONTROL2 A/A scoring-entry recovery remains pending owner216. Its frozen
worker, caches, generation, failed scoring job and STOP are preserved. The
proposer budget decision and exact live transport admission are also pending.
No initial-family result, independent milestone feedback, live model response or
official score was opened or generated for this implementation.
