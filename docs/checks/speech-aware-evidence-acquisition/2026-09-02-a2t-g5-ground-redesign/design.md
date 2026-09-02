# Audio2Tool G5 ground redesign: exhaustive family contracts before control

## Decision

Do not tune, widen, or otherwise reuse G4's ranked candidate admission. G5 should first test a
model-usable ground: a deterministic exhaustive family-contract packet and a two-contact,
same-frozen-core PLAN then EXECUTE protocol. The compiler may dispatch to an action family but
must not rank or prune tools inside that family. It supplies every construction-compatible tool
contract, exact call skeleton, and canonicalization rule for the family.

This is a bounded discovery ground screen, not retrieval optimization, training-free RL,
confirmation, scale, or a paper result. Its qualification target is at least 15/16 exact (93.75%)
before any pruning or reward-guided control is considered.

## Why candidate retrieval is the wrong immediate abstraction

G3's matched broad ground put the gold tool in detailed cards for 37/40 samples and 52/55 gold
calls, yet achieved only 8/40 exact. Thirty of 32 non-exact samples already had their gold tool
in the packet. Eighteen selected the correct tool but failed argument realization; nine received
the gold card but selected a wrong tool or omitted an intent. Card existence therefore is not the
dominant deficit. Its construction-aware reachability ceiling was 33/40, rising to 37/40 with
training-supported compatibility conventions, so a qualified ground is possible only if those
conventions are executable.

G4 then applied faceted BM25 top-two admission plus a sibling contrast or schema-compatible
alternative, yielding two to eight cards. Its current official aggregates are worse: sealed C is
2/16 exact and 11/16 correct-tool, while E and SE are both 1/16 exact and 6/16 correct-tool.
The matching decline in E and SE does not establish that state is harmful. It does establish that
ranking candidate tools before the model has executable contracts is unsafe: a wrong top family
can remove the right tool, and the ranker is asked to resolve both intent meaning and schema
compatibility from task-blind evidence.

The independent task-ground audit agrees: registry coverage is 152/152 tools and construction
coverage is all 354 argument-pattern families, but lexical gold-tool coverage is 0.7925 at top-5
and only 0.94 at top-32. Candidate optimization is therefore downstream of knowledge expansion.
The failed 49,704-token monolithic handbook is also not the answer; G5 packets must be compact and
per family.

Evidence: G3 analysis, the task-ground audit, and the G4 preregistration under the 2026-09-02
speech-aware-evidence-acquisition check and readiness paths.

## G5 evidence supply

Build an English-only, construction-only family-contract corpus. Each contract has a stable ID,
registered tool name, ordered complete call skeleton, required, optional, conditional, and
forbidden keys, JSON types, construction-stable defaults, omission rules, and canonicalizers for
Boolean, null, URLs, entities, lists, periods, and nested schedules. It also carries
construction-supported compatibility variants and correction, multi-intent-order, and
role-preserving dialogue rules. It must contain no evaluation source text, reference transcript,
sample ID, output, reward, score, or concrete task value.

A deterministic compiler maps a closed PLAN family tag to the full compatible family bundle. It may
remove a contract only for a declared syntax-level incompatibility; it must never use BM25 rank,
similarity, top-k, sample/tier ID, gold, outcome, reward, or a model-selected candidate name.
Ambiguous family tags receive the fixed union of compatible families, subject to a fixed complete
packet limit, rather than an arbitrary top-ranked tool. Thus routing is family coverage, while the
frozen core sees every legal execution contract inside that family.

## Same-core protocol

One frozen core makes exactly two sequential contacts per sample.

1. **PLAN, non-final.** Original speech plus a closed family taxonomy produces strict English JSON:
   ordered family and operation tags, target/value span labels, correction/supersession flags, and
   dialogue role/turn references. It returns no tool names, calls, answer text, metadata, or
   example-derived values. A fixed parser validates but never repairs or re-asks.
2. **COMPILE, deterministic and contact-free.** Validate PLAN and render every compatible family
   contract. Invalid or unrecognized plans take a declared fixed fallback union; there is no retry
   or invented plan.
3. **EXECUTE, final.** The same frozen core receives original speech, parsed plan, and the complete
   bundle, then returns only the JSON call array. It chooses a contract, preserves plan order unless
   its correction rule says otherwise, and copies values only from speech or bounded span labels.

PLAN is intermediate evidence, not a second answerer. EXECUTE is the sole final answer, and the
frozen core remains the only answer authority. There is no trained component, retriever/judge,
repair model, or output-selection controller.

## What is knowable before contact

| Surface | Model-free proof before contact | Deferred question |
| --- | --- | --- |
| Knowledge coverage | Deterministic rebuild; every registry tool and construction-supported skeleton/compatibility rule has a contract; no evaluation values or forbidden fields. | Does the frozen core follow a supplied contract? |
| Family routing recall | Every plan tag maps to a nonempty exhaustive bundle; construction-only heldout actions remain covered. Do not use fixed16 labels to measure or tune it. | Does PLAN recognize the spoken family? |
| Tool selection | Every contract compatible with a plan remains in the packet; no rank/top-k exclusion is possible. | Does PLAN plus EXECUTE choose the intended registered tool? |
| Argument realization | Skeleton round trips, canonicalizer tests, legal-key checks, packet bounds, and literal-copy exclusion. | Does EXECUTE bind speech values and serialize exactly? |

Structural success is not a substitute for official exact match. A failed screen cannot be repaired
post hoc by changing the compiler.

## Fixed16 prospective experiment

### Population

Before any audio, task text, label, output, route, score, or reward is read, select a new
identity-only, tier-balanced fixed16 from already exposed discovery entries that have no G3/G4
contact and no query-block overlap with construction sources. Publish the SHA-256 namespace and
sample-ID ordering. Exclude all G3/G4 rows, G4 remainder24, fresh88, test, future turns, and all
TFRL evaluation surfaces. This memo names no roster, creates no config, inspects no G4 per-row
output, and authorizes no contact.

### Arms, comparator, and contacts

| Arm | New contacts | Role |
| --- | ---: | --- |
| P16 exhaustive-family PLAN/EXECUTE | 32: 16 PLAN plus 16 EXECUTE | Only G5 arm; establishes absolute ground capability. |
| Sealed G4 C/E/SE | 0 | Historical mechanism context only; not pooled or statistically compared because P16 uses a new roster. |
| Executor-only ablation | 0 in G5 | Deferred; it would turn the smallest screen into 48 contacts and is unnecessary to qualify the ground. |

Fix temperature, seed, runtime hashes, slot count, request bytes, and decoding limits before
contact. Each contact gets one attempt only: no repair, retry, resend, jitter experiment,
score-driven re-run, or adaptive packet change.

### Prompt and context envelope

The future zero-contact prompt-fit receipt must prove each exact message fits the 32,768-token
per-slot runtime budget with measured audio reserve and a 1,024-token final completion reserve.
Fail closed until it does. Design bounds are: PLAN at most 6,000 text tokens and 256 completion
tokens; parsed plan at most 4,096 ASCII bytes with no silent truncation; compiler bundle at most
18,432 ASCII bytes with no partial trimming; EXECUTE at most 12,000 text tokens before measured
audio/special-token reserves and 1,024 completion tokens. No cumulative history, example-call
literals, source utterances, or evaluation-derived values are permitted.

### Gate and decision

Seal both complete 16-row contact manifests before the unchanged whole-manifest official scorer
opens. P16 passes only if it has parse at least 15/16, exact at least 15/16, correct-tool 16/16,
slot micro-F1 at least 0.90, zero out-of-registry names, zero illegal key sets, zero synthetic
literal copies, zero parser repairs, and at least one exact row in every two-row tier.

The exact gate is deliberately 93.75%, inside the required 90--95% ground objective. Structural
checks never replace it. Score one complete manifest in one unchanged scorer process; do not shard
or average shards.

**Stop:** If any P16 gate fails, keep further discovery, remainder24, fresh88, test, candidate
pruning, TFRL, and scale closed. Freeze attribution at knowledge coverage, family routing recall,
tool selection, and argument realization. A successor may change construction-only representation
after a new model-free audit and a new fixed16, never P16 labels or outputs to tune a rule,
threshold, ranker, or roster.

**Expand:** Only after P16 passes, freeze its exact corpus/compiler/parser/prompt and run one
separately preregistered, identity-selected, disjoint 40-row discovery qualification cohort. It
must reach at least 36/40 exact, 38/40 correct-tool, 0.90 slot micro-F1, 39/40 parse, and 4/5
exact in every tier. Only then may a separate design test pruning or training-free control. It
does not open fresh88 or test.

## Recommendation

Run P16, not another ranked-retrieval variant: 32 same-core contacts that transform a closed plan
into an exhaustive compatible contract bundle and then a final execution. This is the smallest
falsifiable route to a 90--95% usable ground because it directly removes candidate exclusion and
makes argument defaults, types, ordering, and canonicalization executable. The 15/16 gate ensures
that a plausible packet does not get mistaken for a qualified ground.

