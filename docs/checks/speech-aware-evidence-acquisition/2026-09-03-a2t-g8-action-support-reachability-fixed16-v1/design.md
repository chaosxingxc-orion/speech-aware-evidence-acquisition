# G8 action-support reachability design

## Research question

G8 asks whether a fixed set of four complete actions contains enough per-row
capability to justify learning a training-free controller. It is a 16-row
discovery screen, not a policy evaluation. The post-score oracle may use gold
only after every branch output and trace has sealed. Its result is an
action-set ceiling and is never reported as deployable policy performance.

The direct and AgentLoop engineering baselines do not need to exceed 0.90.
The greater-than-0.90 objective applies after training-free control has been
introduced and validated on a separately frozen surface.

## Complete actions

All three new agent actions share one speech OBS and 28 speech-carrying family
EVIDENCE contacts per row. The normalized 152-tool status sheet seals once and
is reused byte-for-byte.

1. `STOP_M0` reuses the exact same-row frozen G1 M0 response with zero new
   contact.
2. `EXHAUSTIVE_G7` supplies the complete normalized execution sheet to one
   frozen-core resolver.
3. `SUPPORT_ONLY_RESOLVE` mechanically retains exact `support` rows in frozen
   registry order and supplies that sheet to one frozen-core resolver.
4. `DECOMPOSED_SELECT_BIND_RESOLVE` separates tool-name and call-order
   selection, typed argument binding, and final answer authorship across three
   frozen-core contacts. Only the final contact can author the official output.

The physical experiment makes 544 contacts: 464 shared contacts plus 80
branch-specific contacts. Logical action costs are non-additive because the
shared contacts execute once: STOP is 0, exhaustive is 480, support-only is
480, and decomposed is 512 contacts. The physical receipt records 544 once.

## Loop and context contract

The runtime has two 32,768-token model slots. This is the model-serving context
available to each request, not the operational request limit. Every request is
held to prompt plus completion at most 24,576 tokens, preserving at least
8,192 tokens of headroom.

No later Loop step inherits an earlier token estimate. Immediately before each
contact, the launcher serializes the actual messages and control record, adds
the exact row speech-feature tokens, a separate 512-token special-token
reserve, and the declared completion reserve, and refuses overflow. Serialized
text is conservatively upper-bounded by its UTF-8 byte count, so the proof
does not require a tokenizer contact and cannot underestimate ASCII text. The
precontact proof covers the largest static family
request, the complete 152-tool sheet, the maximum 32-call selection, and the
maximum accepted binding envelope. It is a capacity proof, not a substitute
for the dynamic check.

Selection accepts at most 32 ordered call occurrences and 4,096 UTF-8 bytes.
Binding accepts at most 12,288 UTF-8 bytes and exactly one legal typed argument
object per selected occurrence. Repetitions preserve their order. The
corresponding completion reserves are 4,096 and 12,288 tokens so neither
accepted response envelope is structurally truncated. Any parser,
cardinality, response-size, skeleton, type, or prompt-fit failure terminalizes
the one-shot attempt before its next contact. No retry, repair, truncation,
fallback answer, branch manifest, or score is permitted after such a failure.

## Batch and scoring efficiency

Model batching remains enabled as two sample-affine workflows, with at most two
simultaneous model requests and queue depth four. Network jitter is not an
experimental variable.

After all branches seal, an outer scheduler starts four independent official
scorer processes. Each process receives one complete 16-row manifest. No
manifest is split and no partial metrics are averaged. The opt-in detailed
mode preserves aggregate and per-sample output from the same single official
scorer invocation, so row detail never requires a repeat score.

The post-score oracle joins the four detailed results by exact sample identity,
applies the frozen exact/slot-F1/tool/tie order, materializes one complete
16-row oracle manifest from already sealed responses, and scores that new
manifest once.

## Scale and open-source training-free control

G8 opens no policy fitting. If and only if its oracle reaches at least 15/16
exact and slot micro-F1 strictly above 0.90, the next experiment freezes an
approximately 100-row randomized, propensity-logged discovery surface.
Vowpal Wabbit 9.11.2 is the primary open-source contextual-bandit controller;
MABWiser 2.7.4 is a fallback or ablation, not a repository-built replacement.

The approximately 100-row stage must show stable paired gains, positive
evidence information gain, and a real controller contribution before any
approximately 1,000-row expansion. The method freezes before validation. Test
data, confirmatory claims, parameter training, and paper-scale work remain
closed in this Stage-2 repository.
