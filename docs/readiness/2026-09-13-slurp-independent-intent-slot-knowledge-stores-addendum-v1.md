# SLURP independent intent and slot knowledge stores: readiness addendum

## Purpose and boundary

This addendum extends the prospective Top-3 commitment design with a separate
knowledge-store design. It is a readiness contract for a later, model-free
construction and consumption study. It does not change the current
HARD_FIRST versus CLOSED_JOINT Top-3 component proof, its prompts, its
candidate rule, its provider bytes, or its analysis recipe. It grants no model,
fit, tool, scorer, or data contact.

The stores answer different questions. An intent store describes when a legal
intent is activated, excluded, or contrasted against a nearby intent. A slot
store describes what a field means, how its value is extracted, who owns the
field, and how a correction is represented. Neither store is an answer key, a
transcript, a source of current-sample values, or an authorization to admit
experience memory.

The stores are independently constructed, independently versioned, and
independently evaluated. A later consumer may read either store, both stores,
or neither store on a given decision. The design must not turn the two stores
into a rigid intent-then-slots cascade: slot evidence may revise the intent
hypothesis, and intent evidence may change which slot interpretation is
relevant.

## Existing shared seams and their limits

The current shared implementation provides the following reusable seams:

- core.base.KNOWLEDGE_BUILDERS, KNOWLEDGE_RANKERS,
  KNOWLEDGE_FUSERS, KNOWLEDGE_PROVIDERS, and PHASE_STATE_VIEWS are the named
  registry surfaces for future preparation and consumption.
- rails.knowledge.KnowledgeSnapshot, KeyFacet, and ValueBundle provide
  hashable snapshot, facet, value, source-sample, provenance, and task-target
  structure. A future store should use this validated carrier rather than
  inventing another snapshot shape.
- rails.slurp_candidate_contracts.SlurpCandidateContractProvider builds one
  immutable catalog through data.slurp.load_slurp_intent_slot_schema from the
  fixed TRAIN source. build_slurp_candidate_contract_provider retains counts
  and observed slot-type shares with examples_per_type=0; it carries no filler
  examples.
- rails.slurp_intent_hypotheses validates the typed, source-bound, ranked
  mutually exclusive alternatives emitted by the existing hypothesis phase.
- rails.slurp_hypothesis_candidate_contract_view validates a pinned candidate
  source and projects the provider result into ordered, filler-free candidate
  IDs, schemas, and observed-profile contrasts. CandidateContractLookupResult
  remains the provenance-bearing native result with evidence status
  task-contract.
- rails.experience_memory.ExperienceMemoryCatalog and
  rails.experience_memory_runtime are a separate admission and selection path
  for offline validated experience records. They are not a knowledge store
  and must not be used to smuggle either store into runtime.

The legal intent inventory used by the hypothesis parser is only a closed
spelling and membership boundary. The TRAIN candidate catalog is only an
observed association and contrast projection. Neither is a mature intent
knowledge base, and neither is a semantic slot knowledge base. In particular,
the current catalog does not establish exhaustive activation conditions,
reliable exclusion conditions, semantic role explanations, extraction
procedures, ownership rules, or correction rules.

## Canonical linkage

Every intent value exposes a canonical intent_id in the legal SLURP inventory.
A slot value may define a reusable slot concept; a separate intent-slot binding
states its role in each operation. Reuse a common definition only when its
semantics agree. For example, a shared time concept does not make a reminder
time and a query time range interchangeable. Join an intent to its applicable
slot bindings through canonical intent_id, and retain stable slot/value IDs,
both store versions, and all content hashes. The linkage is not itself a
semantic claim.

A store release must carry four separately checked contracts:

1. **Construction contract.** Pin the source split and construction roster,
   selection method, source identities, loader/schema revision, and any
   TRAIN-only filters. The construction contract records what evidence was
   eligible and what was excluded. It must not read evaluation gold,
   reference transcripts, or current DEV rows.
2. **Version contract.** Pin the store schema, builder policy, value ordering,
   normalization, canonical serialization, and predecessor/successor
   relationship. A changed meaning, boundary, or source selection creates a
   new store version and hash.
3. **Evaluation contract.** Pin a disjoint source/evaluation roster, the
   requested metrics and strata, and the release rule. Store evaluation tests
   whether the declared contract is useful and safe; it does not silently
   revise the construction bytes.
4. **Content contract.** Specify each retained value, its canonical
   intent_id, content hash, provenance references, and permitted runtime
   projection. The contract must state which fields are visible to the model
   and which remain provenance. Raw fillers, references, transcripts, and
   current-sample gold stay out of the model projection.

An intent-store record and a slot-store record may be joined only through the
canonical intent_id and explicitly declared slot identity. A join must
preserve both store hashes and versions. A missing counterpart is an absent
value, not permission to synthesize one from the other store.

## Intent store contract

An intent value represents a task operation boundary. Its content should be
small, contrastive, and falsifiable:

- **Activation boundary:** observable speech conditions that support selecting
  this intent, expressed as semantic cues or roles rather than memorized
  utterances.
- **Exclusion boundary:** nearby operations or cues that should move the
  hypothesis away from this intent, including polarity, target, and operation
  distinctions where the evidence supports them.
- **Contrast boundary:** the minimal difference from named neighboring
  intent_id values. It must describe the distinction without claiming that the
  distinction was heard in the current sample.
- **Scope and uncertainty:** domains, conditional cases, and unresolved
  distinctions. An absence of a value is not a prohibition unless the content
  contract explicitly says so.

Intent values are task knowledge. They do not select the final answer, assign
confidence, or override the main model's validated response contract. The
runtime may present several independently ranked intent values together, but
the store itself must not collapse Top-N hypotheses into one authority.

## Slot store contract

A slot value has a stable semantic slot identity. Its intent-specific binding
adds canonical intent_id and any conditional role or extraction overrides.
This avoids duplicating compatible definitions without treating different
roles with the same surface name as identical. Its contract has four parts:

- **Semantic contract:** what role the slot plays in the operation and how it
  differs from similarly named or neighboring roles.
- **Extraction contract:** how to recognize and normalize a value expressed in
  speech, including boundaries and ambiguity classes. It describes
  extraction behavior without supplying a value for the current sample.
- **Value contract:** accepted value shape, legal vocabulary or open-text
  behavior, normalization, and conditionality. It must not copy TRAIN filler
  examples into a runtime prompt unless a separately approved view explicitly
  permits them.
- **Ownership and correction contract:** which intent or operation owns the
  field, when ownership changes under a revised intent, and how a model
  correction is represented without mutating the original evidence.

Slot values may state that a field is observed for an intent. They must not
turn observed association into a mandatory field, a forbidden field, or a
default value without an independently constructed and evaluated rule. A
correction changes a hypothesis or extraction interpretation; it does not
rewrite the source speech or claim that a value was present.

## Consumption without a fixed cascade

A joint Top-N consumer receives the same ordered intent hypotheses and the
same candidate-contract bytes for every compared branch. It may use the intent
store to inspect activation, exclusion, and contrast boundaries, and it may
use the slot store to inspect semantic and extraction roles. It then resolves
intent and slots jointly from the available speech evidence.

Slot evidence can revise the rank-one intent when a role, ownership rule, or
operation distinction supports another candidate. Intent evidence can revise
which slot interpretation is applicable. The runtime must retain the
pre-revision hypotheses, the selected intent, slot decisions, and each
knowledge view identity in provenance. A branch that receives both stores
must not be described as a mandatory cascade, and a branch that receives one
store must not be treated as having received the other.

The current Top-3 proof remains a controlled shared-contract comparison:
both branches receive identical ordered candidates and candidate contracts;
only their registered final-delivery authority differs. Adding either
independent store is a later component study and must use a separately named
view, content hash, and analysis binding.

## Minimal subsequent ablations

After a separate construction receipt exists for each store, the smallest
useful component matrix is:

| Cell | Intent store | Slot store | Purpose |
| --- | --- | --- | --- |
| matched-null | absent | absent | Same Top-N source and joint executor without either value store |
| intent-only | present | absent | Test intent boundary knowledge |
| slot-only | absent | present | Test semantic and extraction role knowledge |
| joint | present | present | Test joint revision with both stores |

These four cells isolate value consumption at a common joint decision. Every
cell preserves the same Top-N source, candidate order, speech, model-contact
ceiling, and output contract. The historical one-contact direct baseline is a
separate system reference, not the matched-null cell.

Candidate construction is a second question. After the consumption comparison
is closed, separately test whether intent boundary knowledge improves the
first-stage candidate source. A fixed shared Top-N source cannot establish
that effect. Report true-intent inclusion, conditional selection quality when
included, and entity quality separately; better parameter extraction cannot
recover an intent excluded by a closed shortlist.
The intent-only and slot-only cells must use the same harness and state
bookkeeping. Report zero-tool direct paths, store-view calls, revisions,
unchanged intent decisions, slot ownership errors, correction attempts, and
format failures separately. A store-view call is an input condition and a
cost, not a reward or a success by itself.

The first follow-up should be a four-row engineering proof covering source
hash, value ordering, per-sample state binding, and joint revision
bookkeeping. A full DEV evaluation, store-width sweep, new source selection,
or efficacy claim requires its own frozen construction/evaluation bindings,
registered plan, and root admission within the existing owner-authorized scope. These ablations are proposed design
cells only; this addendum does not authorize them.

## Separation from experience memory

Knowledge stores describe stable task semantics and boundaries that are
prepared before the evaluation contact. Experience memory describes a
validated diagnosis or guidance record derived from a finalized TRAIN
trajectory and its first complete official score. The memory path has its own
ExperienceSource, construction roster, supporting/contradicting references,
validation binding, admission status, and immutable record hash.

A knowledge value must not be admitted as an experience record merely because
it has a source hash. An experience record must not be used as a substitute
for an intent or slot semantic contract. In particular:

- store construction does not create provisional or admitted memory;
- memory selection does not alter store content or candidate ordering;
- store values do not carry reward, score, diagnosis, or optimization guidance;
- memory guidance may suggest a validated diagnostic or extraction strategy,
  but must not silently redefine legal IDs or the released task schema;
- a stable general rule distilled from experience may be promoted to knowledge
  only through an explicit, source-bound successor release and separate
  validation; it is not copied into both stores with conflicting authority;
- any future composition retains both independent hashes and makes the
  composition explicit in runtime provenance.

This separation keeps task knowledge, source-bound hypothesis state, and
reward-derived experience auditable as different artifacts with different
admission rules.

## Authorization state

This addendum is a design and readiness artifact only. It does not authorize
construction on a new roster, a store release, a model contact, a fit,
a scorer invocation, a width sweep, or a change to the current Top-3
comparison. Root must review and freeze the construction, version,
evaluation, content, and runtime bindings before any subsequent ablation.

## Root implementation direction

Use two logical stores with independent builders, snapshots, value contracts,
and retrieval namespaces. Share the embedding backend, persistent storage,
serialization, preparation cache, and registry interfaces where appropriate.
Do not require two database processes or duplicate the engineering base.

Expose distinct configured acquisition operations for intent boundaries and
slot contracts. The main model chooses which operation to request during an
agent episode, and may request both for an unresolved candidate set. Reviewer
flags evidence gaps; Planner controls the bounded continuation; the frozen core
retains the final answer. A deterministic component comparison may supply
fixed views to isolate their effects, but must be labeled as such. It does not
establish autonomous acquisition quality.

Evaluate content construction and consumption together. A retrieved value is
useful only if it supplies a needed distinction or extraction constraint and
the solver uses it correctly. Record source coverage, retrieved-value
relevance, consumed evidence, corrected errors and newly introduced errors.
Select content granularity and any retrieval adaptation on the allowed
construction/discovery partitions, not by repeatedly reading evaluation
outcomes. Keep the current legal inventory and statistical slot profiles
honestly labeled as initial assets.

The same separation applies to Audio2Tool operation selection versus parameter
contracts. Do not force this taxonomy onto Earnings transcription: its
knowledge should instead follow the native task, such as entity identity and
surface-form disambiguation. Reuse the control plane across carriers while
allowing their value schemas to differ.
