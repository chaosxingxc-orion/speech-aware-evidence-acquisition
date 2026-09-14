# Status 094: source metadata ready while the unchanged anchor generates

Date: 2026-09-14. Continue OWNER-CANDIDATE-COVERAGE-026. Keep the owner goal active.

## Live experiment

At 08:40:40 UTC, the sole TRAIN A recovery remains OPENED with 4,520 charged
model calls, not completed samples. Service health is OK. The last monitor
sample reports 97% GPU utilization; the last ten-minute window averages 89.13%
over 52 readings. The frozen source checkout is still clean at
826a77c7bd9030ccbc25f2b74cd6fa4ed69db561. Keep its model service and campaign
running. No restart, geometry change, source edit or partial quality read
occurred. The owner closed the power question; do not investigate it further.

Progress receipt under DATA/coordination/
slurp-native-dual-store-train-fold-a-anchor-recovery-v1/:
runtime-progress-and-source-preparation-v5.json
SHA256 ae83da8e0ccea1d034b27e62b6319eef7243f096b6f18b5ffe38787a1ca91f9a.

## Completed model-free preparation

The common prepare-speech-observation-sources entry exported all 1,080 ordered
TRAIN A records and 3,084.5284375 seconds of original-audio metadata. Its
addresses, audio hashes, durations and packet IDs match the registered dataset.
Shared preparation validation checks the input/output hashes, packet-hash
grammar and split identity. No audio decoding or model/tokenizer/encoder/ASR/
scoring contact occurred. These are inputs for future Reviewer-selected tools,
not fixed ASR preprocessing.

Artifact under DATA/prepared/
SAEA-SLURP-TRAIN-A-LIVE-SPEECH-SOURCES-PREPARE-V1/:
- sources.json SHA256 e756e7f7dfb876e856dd0e12691a2e9497260036a1721efb883cd741d4ffd9c3
- verification-v1.json SHA256 c5420aacf78eccb7948a4bb12725af24933db52ba9874848b0d6b65b0819db1e

Use readiness/2026-09-14-slurp-native-candidate-refresh-tools-train-fold-a-v1/
prepared-tools-binding-v2.json for these pins plus the existing fold-excluded
catalog and local CPU protocol. Its SHA256 is
4c764ad12794c5a63844069241cfd74d2f9e6c8451e804dc1b95c4fcb1324a96.

Two earlier model-free configuration refusals produced no artifact or neural
contact. Preserve the v1/v2 export logs. Registration v2 uses a separate
preparation-only configuration over the registered incumbent baseline. It
permits only metadata export and does not bypass future live-ASR bindings.
The future system configuration remains check-only pending admission.

## Factual knowledge and tool audit

The current intent store has 60 keys/values and one explicit confusable
alternative per intent. The separate slot store has 54 values and 402
intent-slot associations. Exhaustive legal candidate sets of widths one,
two and three need at most 16, 23 and 28 unique slot cards. Current limits
therefore omit no uniquely mapped slot card; this does not prove semantic
adequacy or successful model use.

The candidate-contract tool returns observed TRAIN slot associations.
It does not return the authored activation/extraction explanations supplied
by the rich intent/slot stores. Reviewer prompt v2 now states this distinction
and requests an explicit report when semantic explanation is missing.
Historical prompt v1 and the active experiment remain unchanged.

Factual audit in the same DATA coordination directory:
knowledge-value-structure-audit-v1.json
SHA256 49e705adeef8c2cb38b6043ccab615896cdbdcec9b1acdbfbeeb0c26f0f2016e.

After complete source release, diagnose supplied intent support separately
from actual C0 gold coverage: supplied-and-covered, supplied-but-missed,
not-supplied-but-covered and neither. This helps distinguish retrieval gaps
from candidate selection gaps; it is not causal component attribution.

## Verification and next boundary

Both four-fragment configurations compose, their protocol pin matches and
engineering-base checks pass without adding exceptions. The preceding
331-test affected-code suite remains the code validation record; this
continuation changed only prompt/configuration/documents and produced metadata.

Let the active campaign seal, perform its one official full score and finalize.
Use postseal-handoff-recipe-v2.md; never score it again. Verify the exact full
1,080 source and complete-score binding before releasing task quality. Use the
pinned diagnostics checkout 8f35ae1f for the existing anchor recipe.

Root then decides the next complete system using full task quality, C0 coverage
and covered-set resolution. Bind final generation, actual-request fit, selective
ASR, scoring and phase-supply receipts only at that boundary. Reuse the same
healthy resident decoder after full identity/lease verification. Keep Fold B
untouched. A real training-free proposal/evaluation/admission cycle is still
outstanding; preparation and code tests are not such a cycle.
