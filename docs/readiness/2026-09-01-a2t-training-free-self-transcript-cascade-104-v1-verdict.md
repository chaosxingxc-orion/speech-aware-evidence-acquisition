# Audio2Tool training-free self-transcript cascade 104 v1 — live observation, failed delivery, no scale

Date: 2026-09-01. Status: **PROSPECTIVE DISCOVERY FAILED; DO NOT SCALE**.
Experiment: `SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1`. Committed result:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-self-transcript-cascade-104-v1/result-summary.json`.

## Verdict

The English self-transcript and retrieval path was live, but the evidence-use response surface did
not satisfy the official tool-call contract. The frozen training-free controller therefore chose
`STOP_M0` on every sample. It prevented the severe always-use loss but produced no improvement.
Promotion fails, this mechanism closes on `A2T-G1-104`, and neither a fresh support flight nor an
approximately-1,000-sample expansion is authorized. The experiment establishes neither
agent-over-single-call superiority nor a positive training-free RL contribution.

| Surface | Exact match | Tool accuracy | Slot F1 | Parse failures |
| --- | ---: | ---: | ---: | ---: |
| Frozen M0 | 29/104 (27.88%) | 62/104 (59.62%) | 43.79% | 4 |
| Matched self-transcript evidence | 0/104 | 0/104 | 0.00% | 103 |
| Same-tier shuffled evidence | 0/104 | 0/104 | 0.00% | 102 |
| Matched exact-request resend composite | 0/104 | 0/104 | 0.00% | 103 |
| Five-fold training-free policy | 29/104 (27.88%) | 62/104 (59.62%) | 43.79% | 4 |

All eight tiers had zero matched exact matches. The byte-identical-request resend control also had
zero, so the failure is far larger than the measured resend floor and cannot be attributed to
ordinary request instability.

## OBS and information accounting

The label-free OBS gate passed every clause before USE opened: 104 responses, 104 valid printable
English transcripts, 104 positive BM25 routes, 104 distinct transcripts, maximum identical mode
one, zero prohibited structures, and a valid same-tier derangement. This rules out a dead ASR or
retrieval path.

Top-5 retrieval contained every gold tool on 62/104 samples, exactly the M0 tool-correct count and
below the registered requirement of at least 65. The equal aggregate hides complementary
information: 46 samples were correct under both views, 16 were route-only, 16 were M0-only, and 26
were correct under neither. Thus the transcript route found relevant information for 16 M0
failures, but lost the same number of M0-correct tools. It did not provide the registered net
information gain and, more importantly, that candidate-set information never reached a valid final
answer.

## USE delivery failure

The USE contacts were active and emitted tool-shaped JSON, but not the frozen task contract. In the
matched surface, 102/104 outputs were fenced, the strict parser accepted one output as structurally
parseable, and zero contained a valid nonempty call. No output used the required `name` key; 44 used
`tool`, 31 used `tool_input`, two used `args`, and 70 used `arguments`. Shuffled and resend results
showed the same pattern. The prompt named a “JSON array of tool calls” but supplied no explicit
canonical `[{"name": ..., "arguments": {...}}]` envelope, so the model selected incompatible common
tool-call dialects.

This is a delivery-contract failure, not evidence that transcript retrieval was inert. It also is
not permission to normalize these exposed returns after seeing them. The preregistered terminal
rule forbids prompt, parser, BM25, top-k, evidence-budget, state-bin, support, harm, or promotion
changes on this cohort.

## Training-free control

Always using matched evidence lost all 29 M0 exact matches and all 62 M0-correct tools. The fixed
five-fold, whole-query-group memory selected `STOP_M0` on 104/104 samples: zero final contacts,
zero saves, zero harms, exact and tool net gain zero, fold gains `[0, 0, 0, 0, 0]`, and grouped
CI90 `[0.0, 0.0]`. Matched-minus-shuffled exact gain was also zero with CI90 `[0.0, 0.0]`.

The controller behaved safely, but safe rejection of a universally harmful action is not a
positive training-free RL contribution. The required both-action, save, net-gain, positive-CI,
information-gain, and matched-over-control gates all failed.

## Official-scoring efficiency

The matched, shuffled, and resend complete manifests were finalized concurrently by three outer
workers. Their summed job time was 8.216 seconds and wall time was 3.803 seconds, an effective
2.1604-times speedup. Each worker invoked the unchanged official single-process scorer once on one
complete 104-row manifest. No corpus shard was created and no shard metric was averaged.

The model-free policy formed a later dependency wave and therefore ran as one complete-manifest
score job. Its first invocation failed during argument parsing because the experiment launcher
passed an unsupported `--score` switch; no scorer ran. Commit `839cc6cf` added a failing regression
test, removed that switch, and the already-sealed policy manifest was then scored exactly once.
This command-layer incident changes no prediction or scientific metric.

## Spend, recovery, and scope

The complete campaign used 328 frozen-core contacts and 1,842.443 metered speech-audio seconds
under registered ceilings of 334 and 2,000. It used zero paid APIs, embedding contacts, or tokenizer
contacts. The recovery chain repeated no OBS, matched, or shuffled model contact; only the original
16 registered resends were newly executed in the final recovery. Six canary calls remained unused,
the server was stopped, and the receipt-pinned experiment binary remains archived recoverably.

This result opens no new sample identity and reads no G2, remaining exposed-296, unexposed
Audio2Tool population, FINAL60, test annotation, or future turn. It changes no locked engineering
baseline. A successor may use the result only as a design lesson: freeze an exact output envelope
and require a label-free full-batch structural liveness gate before expensive USE completion. Such
a successor must be a separately preregistered mechanism on a non-reused discovery cohort; this
verdict authorizes neither that flight nor any scale-up.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same sealed outputs (M0 shared with `A2T-G1-104`'s own arm1
file, 104/104 rows; the four USE/composite arms, 104/104 rows each; v1 identity confirmed to 4
decimals overall for every arm) under the registered `a2t-scorer-v2` (`analysis.a2t_v2_rescore`,
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| Surface | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| Frozen M0 | 0.2788 | 0.5962 | 0.3846 | 0.5769 | 0.5962 | 0.5362 | 0.4379 | 0.9615 |
| Matched self-transcript evidence | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0096 |
| Same-tier shuffled evidence | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0192 |
| Matched exact-request resend composite | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0096 |
| Five-fold training-free policy | 0.2788 | 0.5962 | 0.3846 | 0.5769 | 0.5962 | 0.5362 | 0.4379 | 0.9615 |

Paired contrasts vs. `Frozen M0` (v1 and v2, CI90, 10,000 replicates, tier-stratified):

| arm | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| Matched self-transcript evidence | v1 exact | -0.2788 | 0 | 29 | 75 | [-0.3365, -0.2212] |
| Matched self-transcript evidence | v2 exact | -0.3846 | 0 | 40 | 64 | [-0.4519, -0.3173] |
| Same-tier shuffled evidence | v1 exact | -0.2788 | 0 | 29 | 75 | [-0.3365, -0.2212] |
| Same-tier shuffled evidence | v2 exact | -0.3846 | 0 | 40 | 64 | [-0.4519, -0.3173] |
| Matched exact-request resend composite | v1 exact | -0.2788 | 0 | 29 | 75 | [-0.3365, -0.2212] |
| Matched exact-request resend composite | v2 exact | -0.3846 | 0 | 40 | 64 | [-0.4519, -0.3173] |
| Five-fold training-free policy | v1 exact | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |
| Five-fold training-free policy | v2 exact | +0.0000 | 0 | 0 | 104 | [0.0000, 0.0000] |

The v1-recorded scores for the three USE/composite arms were already 0.0000 across the board because
zero output rows carried a valid nonempty tool call (this doc's "USE delivery failure" section: the
model never emitted the required `name` key); registry-default stripping, type coercion, and ordered
tool accuracy under v2 have no predicted call to act on either, so the outcome is IDENTICAL under v2
(0/104 → 0/104, not 0/104 → nonzero) — v2 confirms this is a genuine delivery-contract failure, not a
scorer artifact that a more lenient v1-vs-v2 reading could have hidden. The v1 and v2 CI90s for all
three failed arms sit entirely below zero and never touch it, unchanged in direction. Not promoted
under v2 either: the verdict's decision is unchanged.
