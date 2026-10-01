# Historical nominees and common-selection registration

This offline extension implements the owner214 common-cohort stage without
requiring two surviving versions on each branch. It does not dispatch, score,
grant a read, choose a scientific winner or change a frozen flight. Its output
is an input to the existing registration and admission path.

## Nominate before the common cohort

Run `scripts/system_text_search.py --archive <archive> freeze-selection` with
the pinned `--protocol`, three `--update-family` specifications, a
`--member-bindings` map, `--data-root` and the integrated `--repo-root`.
Supply the family specifications for update-1, update-2 and update-3, not cached
feedback JSON. The CLI reopens the existing complete-family reader for each:
the exact root-countersigned READ, every admitted member, its seal and its
unique complete official score remain prerequisites.
Check all three specification identities before opening any result source.
Reject duplicate updates, milestone, DEV and common-selection inputs at this
metadata-only step; their separate READ authority is not optimizer authority.

Account for six prospective slots: seed, seed-aa, L-1, L-2, B-1 and B-2. Each
has its own confined run ID. Admit seed/A/A and at least one nominee per branch.
An unused second slot retains its reserved run ID but has null bundle and
configuration hashes. A used slot binds its exact archived bundle and the
coordinator's prospective composed runtime configuration hash. No prospective
run, including an unused slot, may already have artifacts.

Root explicitly nominates one or two distinct versions per branch from that
branch's verified historical retentions. The eligibility set includes all
three rounds, so an early blind-search survivor is not silently discarded in
favor of the last round. A seed fallback is eligible only when it was actually
retained on that branch. Foreign, unretained and duplicate branch nominations
are refused. Historical retention does not establish superiority: root records
the nomination reasoning as a sampling choice under the registered analysis
rules. This command neither ranks scores from different cohorts nor creates a
global frontier from them. The common cohort supplies the comparable evidence.

The create-only `stages/selection.json` binds the nominees, every prior branch
retention, all three full-feedback identities, the common roster, all reserved
run IDs, the admitted family and any unused second slots. Its trajectory cap is
400 times the admitted member count: 1,600, 2,000 or 2,400, within the existing
registered maximum. Its official score-job cap is four, five or six. Unused
slots grant no replacement proposal, extra sample or later execution budget.
Report actual work; unequal admitted counts do not support equal total compute.

Copy this registration to the future analysis recipe's `system_search_stage`,
and copy its evaluation map to `system_search_evaluation`. Register the exact
family-specific READ before any generation. The composed configurations, own
supplies, FIT, exposure budgets and root flight admissions remain separate.
Do not modify a previous recipe or worker to attach this new record.

## Preserve complete feedback and selection exposure

The shared stage validator accepts this exact prospective family. It still
requires every admitted member and every row. A runtime failure cannot become
an unused slot. Without the recipe-bound registration, the original six-slot
requirement remains. The reader rejects inconsistent recipe membership before
opening an outcome or earlier reference source.

Nominating an early policy after inspecting later feedback creates indirect
exposure even if the policy's immutable bytes never changed. Each branch's
nomination record therefore retains the cumulative sources of all three of
its historical retentions, including losing candidates and the initial
reference cohort. Check them against the common selection roster. Deleting a
policy or omitting a second nominee does not remove these sources.

After complete common scoring and root interpretation, `retain-feedback`
imports the appropriate branch's nomination ancestry into the final retention.
`freeze-finalists` consequently checks both policy ancestry and all nomination
and selection exposure against DEV. The existing TRAIN-only ancestry gate
rejects a DEV feedback source even earlier, before common-stage registration.
Neither gate is relaxed to defer the rejection. This connection does not
rewrite the runtime knowledge or expose evaluation outcomes to B's proposer.

## Validation and limits

All validation uses synthetic policies, historical feedback and temporary
archives. Tests cover one/two nominees in each combination; historical rather
than only last-round eligibility; incomplete, modified or unbound histories;
foreign and duplicate nominees; missing seed/A/A; post-contact changes;
rehashed omissions; lost exposure; prospective READ validation; and common
selection through the DEV freeze, including early indirect DEV exposure refusal.
The validation receipt records final test and coverage results.

No real proposer, construction, scorer or model call was added. No scientific
result was read. The CONTROL2 scoring-entry recovery remains pending owner216,
and live proposer budget/provider admission remains pending separately. Actual
search candidates and flight registrations can be materialized only after
those inputs exist and their relevant gates pass. This extension alone does
not complete the three-round experiment or release another carrier.
