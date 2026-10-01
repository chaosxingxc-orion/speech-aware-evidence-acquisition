# Whole-family selection custody and frozen finalists

This offline correction implements the owner214 search lifecycle. It adds no
flight, recovery, scientific-read, proposer or adoption authority. The initial
CONTROL2 family remains stopped pending the separately requested scoring-entry
recovery; no initial-family quality was read for this work.

## Corrected connections

The legacy archive `retain` function accepts numeric rows supplied by its caller.
Its records did not bind later proposal inputs. Use the new `retain-feedback`
entry for this search: it reopens the registered complete-family reader, verifies
the exact countersigned READ recipe, and derives measurements from saved official
feedback and attributed contact counts. The recipe must prospectively contain a
`system_search_evaluation` object with this shape:

```json
{
  "schema": "saea-system-search-evaluation-binding-v1",
  "stage": "update-1",
  "protocol_sha256": "<canonical frozen protocol hash>",
  "member_bindings": {
    "<every admitted member slot>": {
      "bundle_id": "<archived policy identity>",
      "run_id": "<registered generation run>",
      "config_hash": "<frozen runtime configuration identity>"
    }
  }
}
```

Bind the map during future round registration, before contact. Do not add it to
an already frozen recipe in place. The reader checks every member's actual run
and configuration identity, its archived policy and cumulative source isolation.
Both A/A members bind the same policy; B's update comparator remains the seed.

After personally applying the registered own-A/A intent guard and tie-breaks,
root supplies the quality-parent bundle first with `--selected-id`, followed by
at most one complementary bundle. This command is a custody operation, not a
statistical-analysis implementation: it does not calculate confidence intervals,
declare the guard passed, or promote a scientific result. Use `--retain-parent`
only for the registered no-qualified-candidate fallback; it permits only the
measured parent. Record the substantive guard analysis in the stage's root report.

Retain all measurements and the entire true same-cohort frontier. Repeated runs
of one identical bundle remain visible as replicates. Use the designated
comparator, then fixed member-slot order as the bundle's representative; never
select its most favorable repeat. Never combine different cohorts' point scores.

## Next-round and DEV handoffs

Later L `proposal-input` and `proposal-capsule` operations require the preceding
recorded retention, the same freshly verified family and protocol, the recorded
quality parent, and only retained complementary versions. Include every admitted
L member and its comparator/A/A in feedback. Omitting a losing candidate is
refused. B inputs remain seed-only and never receive evaluator selections.

Selection ancestry includes the cohort, frozen reference and all considered
own-branch policies, including losing or unused versions. It propagates through
later proposal records without changing existing policy bytes. A related bug
is corrected: iterating earlier learning-history records no longer replaces the
current proposal record used for its source hash.

After both branch choices on the common TRAIN selection cohort, run
`freeze-finalists` with that family's specification and protocol. It revalidates
the full family, checks both retained choices against the same feedback, and
writes one create-only `finalists.json`: seed/A/A plus exact L/B bundle IDs,
DEV roster identity and cumulative selection exposure. It refuses overlap with
the next roster and cannot overwrite a freeze. Use this record when preparing
the later DEV registration; it is not a dispatch receipt. The existing shared
executor, runtime knowledge and Omni answer authority are unchanged.

## Validation and limits

All new evidence is synthetic and all checks are model-free. The validation
receipt records the final test counts and coverage. Tests include wrong run or
configuration bindings, missing members, modified cohorts, foreign parents,
source overlap, duplicate records, blind-context contamination, partial-feedback
selection, fallback, and immutable finalist publication.

Dynamic round flight registrations, real proposal/provider admission, official
own-null analysis, and the complete experimental sequence remain outstanding.
Neither pending owner decision is answered by this implementation. Do not modify
the stopped worker, caches, failed score job, queue controls or initial READ.
