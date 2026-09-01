# Audio2Tool training-free schema-risk memory v1 — preregistration

Date: 2026-09-01. Status: **REGISTERED BEFORE SCHEMA-RISK/RETURN REPLAY**.
Experiment: `SAEA-A2T-MF-TFRL-SCHEMA-RISK-MEMORY-V1`. Machine contract:
`configs/experiment/a2t-training-free-schema-risk-memory-v1.json`.

## Why this successor is admissible

The prospective self-consistency experiment produced a live observation but no usable targeting
signal. Re-observation saved zero exact matches and harmed six. Eligible evidence supply saved four
and harmed ten. Both registered cross-fitted policies consequently returned frozen M0 on all 104
samples.

That experiment compared call-list structure, predicted-tool relations, key signatures, and
literal value agreement. It did not validate the calls against the deployment registry's typed
signature or explicit enum/range constraints. This screen introduces exactly that information
variable and changes nothing else. It is not another domain/category split and does not relax a
threshold.

An earlier SLURP correction study established that the frozen core is not a safe filter over a menu
of supplied candidates: keyed candidates are emitted rather than reliably adjudicated. Therefore
the proposed same-core candidate-arbitration successor is rejected before implementation. This
screen instead performs deterministic external schema validation and retains the core's existing
single evidence-conditioned response as final-answer authority.

## Frozen schema-risk state

The parser accepts the registry's pseudo-signature form `toolName(name: Type, optional: Type?)`.
Parameters with a terminal question mark are optional; all others are required. Boolean, integer,
float, list, and map declarations are checked against their corresponding JSON types. Other
declared types require a JSON string. Boolean is never accepted as an integer or float.

Constraints are checked only when the registry clause is unambiguous: an exact enum list or one
inclusive numeric range, including decimal, negative, whitespace-separated, and zero-padded forms.
Compound or malformed clauses become `uncheckable`; they never become violations by guesswork.
Missing required keys, unknown keys, type violations, and explicit constraint violations are
separate signals.

Each of M0 and `REOBSERVE_DIRECT` receives an order- and duplicate-invariant risk class. The paired
state records whether M0 has lower risk, the observation has lower risk, their risk is equal,
incomparable, or unresolved. `schema-risk-coarse-v1` uses M0 risk plus the relation.
`schema-risk-detailed-v1` adds the observation risk and bucketed violation counts. Tool identity,
domain/category, literal argument values, transcript, tier, sample/group identity, gold,
correctness, supply response, reward, and future turns cannot enter a state key.

The implementation must prove invariance to gold mutation, registry order, tool-call order,
duplicate calls, and consistent tool renaming. Ambiguous schemas must fail closed to an explicit
unresolved state.

## Unchanged policy and pass condition

The source outcomes, supply availability, five whole-query-group folds, seed, exact-match reward,
10,000 grouped bootstrap replicates, and policy thresholds are inherited unchanged. A candidate
supplies only when the matching other-fold state cell has support at least four, at least two
saves, and zero harms. Otherwise it returns M0. No counterfactual return is imputed.

Promotion is conjunctive: both actions; 5–52 supplies; at least three saves; at most one harm;
at least two net exact matches; grouped CI90 lower bound strictly positive; nonnegative tool
accuracy; nonnegative gain in every fold and positive gain in at least two; at least 80% avoidance
of the ten always-supply harms; at least 50% retention of the four always-supply saves; and live
non-dominant state support. Candidate selection and tie-breaking remain frozen.

A pass can only freeze one proposal for a separately preregistered fresh approximately-100-sample
support flight on the still-exposed discovery population. A failure closes schema-risk targeting
for this supply action. It cannot be followed by a threshold relaxation or another state category
on these returns; the next design must change information acquisition or evidence generation.

## Exposure and execution

This is a one-shot model-free replay over the already-exposed `A2T-G1-104` cohort. It binds the
external result SHA-256
`8527282e110cd11a9d87f0d65d06d55f266e0a27a9bb95d7f7eff3b103266d39`, all three response hashes,
both official score hashes, the predecessor state and decision identities, and the cohort receipt.
The evaluator must arm the outbound-network guard before opening inputs and require a clean study
tree. The artifact is self-hashed and records all state supports and signed returns.

This row authorizes zero frozen-core, embedding, tokenizer, HTTP, socket, audio, or GPU contact. It
opens no remaining exposed-296 sample, unexposed Audio2Tool data, G2, FINAL60, test annotation, or
future turn.
