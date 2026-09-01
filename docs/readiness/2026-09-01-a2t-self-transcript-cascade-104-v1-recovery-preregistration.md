# Audio2Tool self-transcript cascade v1 — bounded recovery registration

Date: 2026-09-01. Status: **RECOVERY REGISTERED; NO RECOVERY MODEL CONTACT YET**.
Experiment: `SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1`.

## Incident and exposure state

The first flight crossed every pre-contact gate and completed all 104 registered
`OBS_SELF_TRANSCRIPT` contacts. The observation attempt then aborted while constructing its
non-scoreable bundle because the launcher failed to close the authoritative phase `TraceSink` and
passed the empty adapter-owned fallback trace hash to `build_manifest`. The exception was:
`run manifest status is COMPLETED but lacks a usable trace manifest entry`.

This was a launcher packaging defect after model execution. It was not a model, prompt, dataset,
route, liveness, or scorer failure. The attempt is durably `ABORTED`; actual use is 104 calls and
587.017 speech-audio seconds. No matched, shuffled-evidence, resend, gold, or official-scorer
attempt opened. The local inference service stopped. A retry may never reuse the aborted attempt
identity or repeat its 104 contacts.

## Fixed recovery source

Recovery accepts exactly the following source and refuses every sibling attempt or byte drift:

| Artifact | SHA-256 |
|---|---|
| Observation outputs | `b37f5d2b92404a41c4b9f0ca8516fff612d44befeb2be6428eacf73a6b694544` |
| Authoritative raw trace | `d4161541fc0d438ca6f5d01b0775e6337124275f4d715f066812789e02eca4de` |
| Observation execution plan | `c6b0202a24708f3b91b5edfc9c87a42a235598cde18df8efecc99afaa3d73e37` |
| Flight failure receipt | `92f8ec2f59fbad661af6175abf50e17bd9f152c3ca734540d27e0d773406b2cb` |
| Durable attempt record | `780ec2a2d5924e020b4360b0a7d5dc53f681ffcd600e4d6ff3c984c85d733c04` |

The source attempt is `attempt-20260901t203803z-selftxobs`. Recovery independently requires its
state to be `ABORTED`, its actual call count to be 104, its audio use to be 587.017 seconds, and
the run attempt directory to contain no sibling spend. Every output row must bind its sample,
request hash, response hash, response-text hash, and text to the fixed raw trace.

## Label-free result opened before this amendment

Only the preregistered label-free liveness read was performed. It produced 104 responses, 104
valid transcripts, 104 positive BM25 routes, 104 distinct normalized transcripts, a largest mode
of one, zero prohibited structures, and a valid same-tier derangement. Every tier contributed
13 valid transcripts and 13 positive routes. All frozen liveness conjuncts passed. No gold,
reference transcript, expected tool, task correctness, reward, or official score was opened.

## Authorized recovery

The repaired launcher must first close the authoritative phase trace and use that hash in each
bundle; the adapter-owned fallback sink closes second and remains an independent accounting
receipt. Capability tests lock this order. A recovery invocation uses
`--recover-sealed-observation`, verifies every fixed source binding, reconstructs the original
deterministic transcripts, routes, matched material, shuffled material, and resend roster, and
makes zero new observation contacts.

Only fresh matched, shuffled-evidence, and resend attempt identities may open. Prompts, speech
packets, M0 bytes, BM25 settings, evidence budgets, same-tier shuffle, policy state, folds,
thresholds, resends, metrics, bootstrap, promotion gates, scorer, and complete-manifest outer
parallelism remain unchanged. This recovery changes no scientific protocol and keeps the original
protocol hash `7c4518d2e2c7a25fa2106a54e9f2398717586af197f7cf98e39ac7ef49e1bc8d`.

The cumulative experiment ceiling remains 334 calls and 2,000 speech-audio seconds. After the
104-call OBS abort, at most 230 calls remain: 104 matched, 104 shuffled-evidence, 16 resends, and
the original six unused canary allowances. The row-level attempt store must count the aborted OBS
spend before every new request. No additional allowance is created.

Before recovery contact, the red-then-green launcher tests, all affected regression tests, lint,
a clean committed tree, and `--preflight-only --recover-sealed-observation` must pass. A source
binding failure, liveness disagreement, budget disagreement, dirty tree, or runtime drift stops
before model contact. A later scientific-gate failure retains the original terminal consequence:
close this mechanism and make no fresh-sample contact. A pass permits only the separately
preregistered block-disjoint approximately-104 support proposal already defined by the parent
registration.

## Second packaging abort and final bounded recovery

The first recovery obeyed the zero-OBS rule. It completed and sealed 104 matched and 104
shuffled-evidence contacts, then aborted before the first resend request. The resend extractor was
given the complete matched trace but incorrectly required every trace row to be a `MODEL_REQUEST`;
it stopped on trace row two, a normal non-request record. Both USE attempts are durably `ABORTED`
because the outer flight failed after their complete manifests sealed. No resend, gold, or scorer
contact occurred. Cumulative model use is now 312 calls and 1,761.051 speech-audio seconds.

The final recovery fixes the extractor under a mixed-trace capability test and accepts only the
following additional bytes:

| Artifact | SHA-256 |
|---|---|
| Matched complete run manifest | `f553c1ac684ebcb85e95622be751a630369eeb734d2a5007f139c51568903c50` |
| Shuffled complete run manifest | `060e54b07f3c82ae09e2577283535884928c6098f58da406cd33611329b6ee92` |
| Matched aborted attempt record | `171bde8c2d7c4e8da0bcb464aeca1998d53a67000ee5c301bcca6e52d9017e59` |
| Shuffled aborted attempt record | `76eec7326174f0f211e300a3a1a6ee7c770a31ac0552ecd05c188340637d2781` |
| Second flight failure receipt | `71223984c545dd19a84b3f06d38b6b706d381a04a8d0157dafcad38212b1f91e` |

Each fixed run manifest must independently verify as a complete 104-row `COMPLETED` bundle whose
durable attempt is `ABORTED`, whose actual usage is 104 calls and 587.017 seconds, and whose
outputs, raw trace, trace manifest, session receipt, plan, split, protocol, and source provenance
match the hashes embedded in that fixed manifest.

The recovery makes zero new matched or shuffled contacts. It opens two fresh zero-call derivative
attempts, emits complete 104-row manifests whose every row binds the corresponding fixed source
output artifact and SHA-256, and finalizes those derivatives rather than mutating or reopening the
aborted attempts. It then replays only the original 16 hash-selected matched request payloads from
the fixed full trace under one fresh resend attempt. The matched and shuffled derivatives and the
resend manifest remain three independent complete-manifest jobs for the original three-worker
outer parallel finalizer. The policy derivative still binds the newly finalized matched derivative.

Only 22 calls remain under the unchanged 334-call ceiling: 16 registered resends and six unused
canaries. No canary is planned. Source validation or derivative-manifest failure stops before the
resend model contact. This amendment changes no prompt, response byte, route, evidence, action,
metric, scorer, promotion rule, sample, or scientific protocol.
