# Complete-source parent selection adapter

Status: MODEL_FREE_PROTOTYPE_ONLY. No current algorithm, actor or GPU activation.

prepare_qualified_parent_selection extends the existing parent-selection module.
It accepts a hash-pinned registered root request, loads the registered population,
and invokes the existing read_registered_population_sources gate for every cohort
before measuring or choosing a parent. An OPENED attempt or unsigned later cohort
prevents all quality reads and every selection write. No partial-population shortcut
is introduced. Source scope, seals, unique official scores and READ authority remain
owned by the existing reader rather than a new parallel qualification system.

Selection is cohort-local. The first declared control is the designated representative,
followed by candidates in registered order and then remaining controls. Identical bundle
replicates, including A/A, remain in the record; the first declared representative is
used regardless of which draw has the highest score. Every admitted member's complete
timing and official measurement is validated. Different cohorts are never combined
into a frontier. The entire population is freshly requalified again before writing;
only the known operational verification timestamp is excluded from identity comparison.

One create-only root record binds the request, complete source registration and identity,
projection config, target cohort, full measured candidate/replicate rows and selection.
It includes no raw sample content. No actor export, formal adoption, proposal allocation,
old acceptance change or runtime admission occurs. It does not overwrite any history.
The complete source identity remains private provenance, not a learner-facing record.

The request supplies validated usage counts and selector configuration; history-derived
usage continuity and the immutable combined experiment/planning configuration still
need prospective lifecycle integration. The reservation boundary must still enforce
spent allocations and actual proposer isolation. Optimizer experience update and an
algorithm comparison remain unimplemented. Do not mistake this adapter for a complete
training-free learning loop or execute it against a partial active experiment.

## Verification

Eleven new tests use synthetic source/reader fixtures. They retain the real all-source
join orchestration while substituting the low-level scientific evidence for fixtures.
They cover complete-population ordering, OPENED/unsigned/missing later members,
unknown target cohorts, draft requests, post-selection source/request changes,
feedback drift, create-only records and preserving a better replicate without selecting
it. Eight initial tests failed on the absent interface. A test expectation was corrected
to count both the duplicate candidate and retained A/A; no implementation relaxation.

191 related tests pass, including existing complete-source and context-reader tests.
The combined selector/planner/adapter module covers130/130 statements. This is model-free
integration evidence, not a real-data algorithm run. Zero new actor/model/scorer contacts.
Current remaining-b2 captured READ entry pins and frozen worker sources remain unchanged.
