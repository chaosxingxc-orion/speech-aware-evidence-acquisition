# Live whole-roster phase fitting

Status: engineering bridge implemented; live system flights remain held.

The shared EvidenceAgentController must retain its actual prior answer and acquisition transition when an intent phase feeds a supplied slots phase. The former per-phase wrapper discarded that controller trajectory. The continuous wrapper retained it but could not stop the whole roster before the next phase.

The explicit whole_roster_wave_barrier option executes one complete active roster wave through the same OpenJiuwen executor, preserves every controller and query state, then prepares the exact next requests. Direct and supplied arms use this same path. Defaults remain unchanged.

A live_phase_fit declaration names a distinct tokenizer run, attempt and total contact cap. Its ExecutionPlan derives the actual generation protocol, split and resource ceilings; it changes only its own identities and metadata-contact cap. The committed exposure gate checks it before first contact. One root generation lease covers both tokenizer work and generation. No second service starts.

For the current two-phase,1000-row SLURP setting, register6002tokenizer endpoints separately from2000generation requests: each phase has one props query,1000template calls and2000tokenizations. The same PreparedCoreRequest objects are fitted and dispatched. Phase2 is checked only after real phase1 responses exist; a synthetic predecessor or duration estimate never certifies it.

Every phase writes a source-bound fit artifact and an append-only contact journal. A capacity refusal, tokenizer exception or interrupted fit retains evidence and refuses a same-identity retry. A failed second-phase check sends no second-phase generation. Partial first-phase traces are flushed through the normal client. The wire-check path records only synthetic request identities and explicitly reports capacity_verified=false.

Validation covers real shared request construction, whole-roster ordering, retained prior state, exact prepared dispatch, missing/invalid opt-in, distinct metadata plans, complete roster/cap accounting, non-fit and tokenizer-failure persistence, and zero retry contacts. Existing runtime/preparation/supply/fit suites passed220tests; live/staged/phase suites passed41tests. The engineering-base check passed without extending its exception list.

Remaining scientific work: freeze the plain and supplied live configurations, register their full-stage budgets and actual metadata contacts, verify config wiring, and run/score the inherited discovery roster. This engineering evidence is not a system quality or cost result. E21 live selection remains a separate bounded task.
