# Sequential execution with independently optimized node contexts

Status: offline engineering design; no new runtime admission or policy activation.

## Owner direction and interpretation

Apply the [direct sequential/progressive-context amendment](../../receipts/owner/2026-10-04-sequential-progressive-context.json).
Keep the original sequential trajectory schedule. Preserve independent node instructions and permit
node-specific evidence organization. Cache reuse is a cost measurement, not a policy-edit boundary.
Keep learning HELD, the heartbeat PAUSED, root-only work and the human review before8x400.

A reused prefix is still available to attention. The 344 newly evaluated Reviewer tokens are an
observed mean of computational work, not the amount of evidence visible to the Reviewer or the
number of tokens that may be optimized. Appended instructions can change subsequent processing,
but do not retroactively encode earlier evidence under a different early instruction. Treat
suffix-only and early role-conditioned context designs as different hypotheses; do not assume
equal quality.

## Evidence from the already qualified family

The [source-pinned audit](../../receipts/continuation/2026-10-04-sequential-context-footprint.json)
covers all1033 contacts in eight sequential members of the complete sixteen-member family.
It verifies each wire artifact and joins each request to its own role and the prior qualified
measurements. It adds zero model, tokenizer or scorer contacts and exports no optimizer feedback.

For the legacy sequential layout, the148 Reviewer contacts average:

| Measurement | Mean |
| --- | ---: |
| Visible input tokens | 10983.061 |
| Reused input tokens | 10638.845 |
| Newly evaluated input tokens | 344.216 |
| Prefill time | 244.736 ms |
| Output generation time | 7970.045 ms |
| Generated output tokens | 154.365 |
| Client transport time | 8336.844 ms |

Decoded text values, excluding speech features and wire framing, average:

| Existing section | Characters |
| --- | ---: |
| System contract | 8118.00 |
| Intent knowledge | 6539.74 |
| Training exemplars | 3582.45 |
| Slot knowledge | 27707.29 |
| Node history | 1510.64 |
| Reviewer query | 1154.95 |

Slot knowledge is about57% of these text characters and node history about3%.
Character fractions are not token fractions, attention importance or causal prefill attribution.
No full text part repeats exactly within these requests; semantic or internal duplication is not
excluded. The large cached context is therefore not synonymous with a large chain of generated
node facts. Refer to the existing complete-family report for quality, all strata, repeated-input
and scheduling limitations; this audit adds no efficacy verdict.

## Proposed context contract

Separate the following responsibilities without adding an answering model:

1. Keep canonical source artifacts immutable and addressable. Preserve full speech custody,
   retrieved knowledge, role outputs, revisions and cumulative exposure in the existing trace store.
2. Compile a node-visible working view from allowed current sources. Include the current draft,
   candidate alternatives, evidence support, uncertainty, negation, conflicts and relevant review
   findings. Preserve distinctions between evidence, model hypotheses and model criticism.
3. Make any omitted detail explicitly recoverable by a validated expansion path, tied to the
   same sample, source version and permitted runtime scope. An identifier or disk address alone
   is not a working expansion mechanism.

Do not require all nodes to use an identical view or instruction. Do not force edits into the
344-token suffix. Permit a prospective Reviewer-specific evidence order, filtering policy and
instruction placement even when the edit invalidates a longer cached suffix. Keep unchanged
sections byte-stable when that does not compromise the intended role behavior.

Reuse the existing context compiler, source binding and native tool execution. Existing
knowledge-reference projection only removes duplicate full content already visible in the same
request; it is not lazy loading. Existing latest-Solver history selection is not a guarantee that
omitted facts are recoverable. Existing structured boundary compilation and bounded Reviewer
handoff are useful bases; do not introduce a parallel controller or silently activate historical
closed policies.

Begin with deterministic source-bound views and explicit omission/reconstruction checks.
A model-generated summary is a separate optional factor, not a mandatory new node: charge its
entire call, FIT, output, downstream expansion and error handling to the same sample. Keep Omni
answer authority and register any new expansion interface before model contact. Do not claim
lossless compression for a semantic summary.

## Next engineering comparison

First prove source custody, default-off request equivalence, current-state selection, conflicts
and corrections, expansion authorization, full output reserves and failure handling offline.
Verify the actual maximum legal requests and a separately registered structural proof before
a complete small-panel comparison. The reference stays sequential with the existing full view;
compare a compact view and only then a genuinely wired progressive expansion variant.

Keep independent role optimization open at three levels: what evidence is visible, how the
Reviewer is instructed to judge it, and what bounded actionable findings it hands off. Check
saves and harms, missed evidence, unnecessary revisions, finite delivery and abstention.

Anchor decisions on original per-sample wall time, first and non-first means, official SLU-F1,
intent and reliability. Also report per-role input/reuse/evaluated tokens, prefill, output length,
decode time and expansion rate. Count compression/preparation and extra round trips; do not
optimize cache hit rate in isolation. A small panel can establish plumbing and descriptive cost,
not stable quality benefit or learned improvement. Continue to50/100/200 only after root review.

## Deferred engine constraint

The current engine at04ccc72a2207347ca76161b93fd9d846dd0a8675 is decoder-only but accepts speech
feature chunks. Its disk slot-save path calls server_tokens.get_tokens(), which asserts that
has_mtmd is false, while speech chunk insertion sets has_mtmd true. The no-mmproj guard checks
mctx, so it does not establish safe disk saving of these speech slots. Do not exercise this path
on the live service. RAM cloning uses a different path that preserves chunk metadata; no runtime
bank fidelity or speed is established. This offline finding does not authorize service changes.
Prioritize sequential context engineering, not a KV-bank deployment.
