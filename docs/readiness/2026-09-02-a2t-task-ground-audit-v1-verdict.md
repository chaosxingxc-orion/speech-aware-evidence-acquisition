# A2T Task-Wide Knowledge Ground V1 Audit Verdict

## Decision

The current knowledge surface is not a usable task ground. Expand task-wide executable knowledge
before candidate pruning or training-free controller optimization. No fresh flight, support cohort,
approximately-1,000 expansion, baseline change, test access, or Stage-3 claim is open yet.

## Why the current surface cannot qualify

The knowledge inventory is complete in the narrow datastore sense: the frozen registry contains
152 tools, the construction knowledge covers all 151 tools used by the task, and it covers all 354
observed argument-pattern families and all 85 argument keys. Full lexical reachability can reach
0.985 at `k=128`. The failure is therefore not evidence that another tool family must simply be
added to the datastore.

The frozen core cannot yet use this inventory as executable knowledge:

| surface | tool/coverage | exact or conversion | relevant failure |
|---|---:|---:|---|
| full 152-row registry, A0, `n=400` | tool 0.5425 | exact 0.2425 | directory presence is insufficient |
| current top-5 matched, `n=104` | gold-tool coverage 0.6827; tool 0.7019 | exact 0.3846 | ORG reach and USE both bind |
| perfect post-contact M0/matched arbiter | — | exact 46/104 = 0.4423 | current answer surface has a hard low ceiling |
| highlighted correct registry row, headroom `n=120` | retention 0.9333 | conversion 0.1333 | correct identity does not supply execution semantics |
| values-stripped correct row | — | conversion 0.0667 | removing unsafe values alone is not enough |
| full registry plus stripped correct row | retention 0.9417 | conversion 0.0583 | full registry reopens the value-copy channel |

The highlighted correct row generated 34 registered literal-default substitutions. Stripping its
defaults reduced that count to two, but appending the stripped row to the unchanged full registry
raised it again to 22 because the registry body still exposed the same literal values. Literal
defaults must not be part of the successor ground.

The matched surface passes only the parse gate: exact 0.3846, tool 0.7019, slot micro F1 0.4091,
and parse rate 1.0. It misses the frozen minimums of 0.90 exact, 0.95 tool, and 0.90 slot F1 by wide
margins. Perfect arbitration over M0 and matched still reaches only 44.23% exact, so a controller
cannot repair this surface into the requested 90%–95% regime.

## Required successor

The next candidate is a full executable handbook, not a smaller candidate list. Every query sees
the same frozen task-wide knowledge. The handbook must retain all tools but replace raw registry
rows with:

- values-stripped signatures and constraints;
- required and optional argument-pattern families with typed placeholders;
- an explicit rule to copy argument values only from the spoken request and never from handbook
  examples or defaults;
- positive selection criteria and contrastive boundaries among sibling tools;
- multi-call, correction, and intent-blending composition rules;
- a single strict JSON output envelope.

Construction may use only the governed, block-disjoint construction partition and registry. No
evaluation/test label, reference transcript, annotation, or future turn may enter runtime.

The next approximately-104 flight must score a complete ground manifest through the unchanged
official scorer. Ground qualification requires exact at least 0.90, tool at least 0.95, slot micro
F1 at least 0.90, and parse rate at least 0.99; exact at least 0.95 is the target. If tool accuracy
binds, expand intent and contrast knowledge. If tool passes but exact or slot quality binds, expand
argument execution knowledge. If parse binds, repair the USE/output contract. If speech observation
binds, improve OBS rather than the ground. Candidate pruning and training-free RL resume only after
the full ground qualifies.

## Integrity and engineering scope

The audit read only SHA-256-pinned aggregate verdicts, coverage receipts, and the frozen registry.
It opened no per-sample output or annotation, fit no policy, and recorded zero outbound attempts and
zero model, retriever, embedding, tokenizer, network, audio, or GPU contact. External result
SHA-256: `fd0ff9fbd971b1f11a5b6b2b63e28aee3fae9d284f8680d127cbc376c576029f`.

Complete-manifest outer parallelism around the unchanged single-process official scorer remains the
evaluation baseline. Network-jitter, packet-loss, latency-injection, and network-retry tests remain
out of scope.
