# Audio2Tool G6 design: exhaustive family-local evidence acquisition

## Decision

G6 repairs control before expanding knowledge. Freeze the G5 corpus byte-for-byte and remove the
single routed-family bottleneck. For each speech request, inspect every one of the 28 frozen
families independently, retain compact family-local applicability evidence, and let the same frozen
core resolve the final registered call set from those reports and the selected contracts.

This is deliberately an expensive ground. Its purpose is to establish whether the existing
knowledge can support at least 15/16 exact answers before retrieval, pruning, stopping, or
training-free reward-guided control is introduced. If it works, later control learns which family
inspections to skip. If it fails, the failure is evidence that the knowledge representation or
final evidence use must expand; another router is not the remedy.

## Evidence for the decision

G5 has complete model contacts but fails its ground gate: 3/16 exact, 4/16 correct tool, and
0.1702 slot micro-F1, versus frozen same-identity M0 at 6/16, 12/16, and 0.4286. The complete gold
family was actually supplied on only 4/16 rows. Those four rows were 4/4 correct tool and 3/4
exact; the other 12 were 0/12 on both metrics.

Seven PLAN responses were discarded only because they used semantic verbs instead of the literal
tag `execute`. Four of those seven had already named every needed family. The fixed fallback then
covered none of their gold family sets and scored 0/7. Even preserving every useful rejected PLAN
would raise observed full-family coverage only to 8/16, so parser tolerance alone cannot qualify
the ground.

The corpus itself has 152/152 tool coverage and 99.1987% construction-only complete tool-set
recall. The current evidence therefore points to ORG and SUPPLY control, followed by argument USE,
not missing datastore rows.

## Population and comparator

Freeze a new identity-only, tier-balanced 16-row roster, two rows per tier, from the 76 identities
remaining in `A2T-G1-104` after every G3/G4/G5 identity is removed. Selection must depend only on
the frozen identity namespace and a declared hash rule. It must not inspect task text, audio
meaning, M0 outcome, gold, score, or error class.

Every eligible identity already has a frozen G1 M0 response. Reuse those sealed bytes as the
no-contact paired comparator after the G6 roster is frozen. Do not spend 16 redundant same-model
contacts to recreate M0. Keep fresh88, test, confirmatory, future-turn, protected unexposed, and
training-free-RL evaluation surfaces closed.

## AgentLoop

The loop has two logical stages and 29 planned contacts per sample.

### FAMILY SCAN: 28 independent contacts

Each contact receives the original speech, exactly one complete frozen family bundle, and a
reference-only instruction. It returns one compact ASCII JSON report:

- whether the family is applicable;
- zero or more registered candidate tool names from that family;
- ordered speech-span evidence for each candidate;
- argument bindings copied from speech;
- unresolved required arguments; and
- correction, turn, role, and ordering evidence when applicable.

A scan may abstain. It must never emit final calls, propose a tool outside its supplied family,
copy contract defaults as task values, or treat the family inventory as an action list. Invalid
reports become an empty report for that family only; they never replace information from another
family and never trigger a retry.

All 28 scans are prospectively scheduled. They are causally independent and may use the two server
slots concurrently, but each planned contact has one attempt only.

### RESOLVE: one final contact

The same frozen core receives the original speech, the 28 bounded scan reports, and only the exact
contracts named by structurally valid reports. It returns the sole final JSON call array. Every
tool must be registered and have been named by its own family report. Every argument key must be
legal for that tool. Values must bind to speech evidence or an explicitly permitted construction
canonicalizer; unspoken optional/default fields are omitted. Call count is bounded by the frozen
construction maximum and duplicate or inventory-like enumeration is invalid.

No second answering model, trained component, repair contact, retry, resend, reward, gold label,
reference transcript, or test annotation enters runtime.

## Causal decomposition

G6 separates the four study channels:

- OBS is unchanged original speech and dialogue carriage.
- ORG is the fixed 28-way family decomposition plus compact scan reports.
- SUPPLY is exhaustive family-local access, with no retrieval, rank, top-k, or fallback.
- USE is candidate nomination, evidence binding, and final resolution.

Postflight analysis may open frozen discovery gold only after all contact and trace manifests are
sealed. It reports family-local gold nomination, retention into the resolver, complete final
supply, registered-tool validity, argument-key validity, exact conditional on complete supply, and
paired transitions against sealed M0. These are mediators, not runtime inputs.

## Context, batching, and scoring

The receipt-pinned GGUF declares 65,536 context tokens. The proven two-slot service allocates
32,768 tokens to each concurrent request; it is not the model maximum. G5's server log explicitly
reports `n_ctx_seq (32768) < n_ctx_train (65536)`. Keep two slots for G6 because a single family
scan is small and the resolver must remain bounded.

Before every contact, measure the exact fully rendered request, including current structured state,
visible knowledge, speech-feature tokens, control framing, and completion ceiling. Require at least
8,192 tokens of operational headroom. Loop step count is never used as a proxy for prompt size.
No raw scan prompt or raw response history is cumulatively appended; only validated bounded reports
enter RESOLVE. Refuse before contact rather than truncate or silently reduce completion capacity.

Model execution uses request concurrency across causally independent family scans. It does not batch
dependent SCAN and RESOLVE contacts. Official scoring remains one unchanged single-process scorer
per complete manifest. Independent complete-manifest jobs may run in an outer parallel supervisor;
dataset shards and averaged shard metrics are forbidden. Network-jitter experiments remain out of
scope.

## Gate and stopping rule

G6 qualifies only if the complete 16-row RESOLVE manifest has all of:

- parsed JSON on at least 15/16 rows;
- exact match on at least 15/16 rows;
- correct tool set on 16/16 rows;
- slot micro-F1 at least 0.90;
- at least one exact row in every tier; and
- zero out-of-registry tools, illegal key sets, inventory enumeration, parser repairs, retries,
  silent truncations, or synthetic/default task-value copies.

Any missing contact or structural failure seals a failed attempt; no sample is recontacted. If any
gate fails, keep 40/100/1,000 expansion, pruning, training-free RL, fresh88, and test closed. Use
the sealed mediator analysis to decide whether the successor needs family-description expansion,
candidate-local contrast knowledge, argument canonicalization, or final resolver repair. Make that
construction-only change on a new identity-only roster, never by tuning G6 outputs.

If G6 passes, freeze the corpus, family-scan schema, resolver, runtime budget, and decode settings.
Then run one separately preregistered disjoint 40-row discovery support gate. Only a stable result
at or above 90% exact may open a 100-row experiment. Pruning and training-free reward-guided control
remain downstream: their action space is family acquisition, acquisition order, evidence width,
and stopping, while the exhaustive G6 policy remains the no-pruning upper baseline.
