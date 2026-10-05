# Complete multi-cohort source qualification for abstract feedback

The existing abstract projection supports arbitrary configured cohort sizes, including the actual8/4/4 continuation. This adapter adds the missing private source boundary: every configured source scope, exact root READ and attempt must pass before any source seal/score qualification, and all families must qualify before opening any quality feedback. Reuse the existing complete-family reader and source-bound feedback reader. No alternative scorer, runtime or optimizer is introduced.

## Source registration

Prospectively pin a `saea-abstract-population-source-registration-v1` document with status `ROOT_REGISTERED`, scope `abstract-feedback-source-join-only`, runtime_admission false, projection_config and an ordered families list. Each family binds cohort_id, exact original recipe, frozen-check receipt and saved complete family metadata by hash. The projection config describes the join and does not rewrite historical execution configs. Derive cohort membership, input order and sizes from that config. Each source still satisfies its own original runtime registration and exact full-family READ.

`analysis.abstract_population_sources.read_registered_population_sources` checks all source attempts before calling a bundle verifier or feedback reader. It then qualifies every seal and unique successful complete score using the existing reader. Recheck source/config/attempt/job/manifest pins and every READ authority before and after private feedback reads. A failure returns no partial join. The result remains private source evidence; it is not a learner payload or permission to create proposals.

## Learner connection still required

After actual remaining-b2 completion and root review, pin the exact real source join covering completed original K8A plus both K4 cohorts. Requalify that join, map each candidate's source-bound node traces through the existing numeric abstract_episode projection, then pass all cohorts to abstract_partitioned_population_feedback. Retain complete templates, anonymous structural outputs, measured timing/token costs and numeric official terminal counts. Keep raw content, IDs, source addresses and knowledge in backend custody. Normalize only within each cohort; do not flatten the original population into a fictional concurrent K16 rollout. Preserve control summaries and source identities privately.

A new actor/update/trial requires its own pinned config, prospective allocation and exact admission. No actual feedback export, proposer call, learning update or GPU dispatch occurred in this preparation. This is not evidence of learning benefit. Other-carrier holds and human-before8x400 remain.

## Verification

The new adapter has24 tests covering successful all-source ordering, incomplete/unsigned/changed sources, wrong roster/membership, confinement, ambiguous contracts, qualification refusal, source/authority mutation, and real shared-reader import.96 related tests pass. Adapter73/73 statements and14/14 branches are covered. Engineering-base check passes. The operational complete-join path remains unexecuted because remaining-b2 is not complete. Preserve that distinction.
