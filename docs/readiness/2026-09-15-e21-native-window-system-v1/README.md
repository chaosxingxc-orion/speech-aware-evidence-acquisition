# E21 native window system: complete held configuration

This is a CPU preparation checkpoint, not a GPU registration or task-quality verdict.
The owner holds all new GPU work after the current Audio2Tool task stops. Do not launch,
restart, fit, encode or recover a GPU task until the owner explicitly resumes. Preserve
resident model memory. SLURP retains scheduling priority when eligible work resumes.

## Actual comparison

Compare a new direct frozen-core transcript against the complete native agent on the same
44 historically exposed discovery calls and 1,593 source-bound speech windows. Both arms
use the same shared controller, FlightRuntime, OpenJiuwen executor, packet request builder,
delivery and complete official scoring. Both use the same task contract and expose the
window's source-derived duration with a zero-based local time coordinate. Historical
non-window requests keep their existing contract.

The direct arm performs one direct contact per window. Its required knowledge snapshot
binds real public source provenance, but its direct-only phase exposes no facets or values,
and it declares no tool or supply routes. Do not describe an internally loaded provenance
snapshot as evidence consumed by the model.

The system uses Perception, Solver, Reviewer and Planner through the existing native role
episode. Perception records uncertain linguistic evidence. Solver receives two independently
pinned call-scoped ConEC stores: participant names/explicit roles and a source-form lexical
list. The source context contains token/count rows, not financial prose. Neither store proves
a term was spoken; no reference transcript, gold annotation or future turn enters runtime.

Reviewer may request local Whisper for a concrete suspected defect, selecting at most a
30-second span within the current window. The audio tool is invoked during the episode;
it does not run during preprocessing or provider construction. ASR disagreement is uncertain
evidence, not an instruction to overwrite the transcript. Planner emits a registered JSON
ACCEPT or REVISE decision, and at most one Solver revision is allowed. Solver alone supplies
the final transcript. Perception and Solver have no analytical tool authority; Planner has
no tool exposed in this initial version.

The generic JSON Planner program is shared and task-independent. It avoids coupling E21
to the Audio2Tool-specific Perception response schema. Role prompts, allowed tools and
bounds live in configurations, with no experiment-specific controller or executor.

## Serving and contact envelope

Use the existing source-bound cddb000c formal feature packets and their decoder-only
runtime receipt. Do not load the projector on the GPU or encode the speech again.
The proposed geometry is total context 98,304, four slots of 24,576, output cap 1,024,
temperature zero and the same fixed seed in both arms. The model fragment keeps the
existing decoder/build/feature-root identity and CUDA graph environment setting.

This geometry is a candidate, not a capacity or VRAM qualification. Direct fitting uses
the real shared request constructor over the complete roster. Native fitting checks each
actual rendered role request, including accumulated knowledge, prior responses and selected
tool evidence, before that request is sent. Keep the output limit and geometry fixed within
the comparison; a refusal stops the flight rather than silently reducing the cap.

| Contact family | Maximum | Basis |
|---|---:|---|
| Direct core generation | 1,593 | One per source window |
| Direct static fit endpoints | 4,780 | One props plus three endpoints per actual request |
| System core generation | 17,523 | 1,593 times eleven; minimum four roles per window |
| System live fit endpoints | 70,092 | Maximum core contacts times four endpoints |
| Reviewer-selected CPU ASR | 6,372 | At most two tool turns per review visit, two visits |
| ASR selected audio seconds | 190,257 | Ceiling of four times min(30 seconds, each window duration) |

The eleven-contact bound is Perception once, plus two possible rounds of Solver one,
Reviewer three and Planner one. Reviewer reserves its final iteration for reporting.
A local ASR wait yields the model slot. CPU ASR uses one worker, four inference threads
and one interop thread; respect the shared CPU budget for all background work.

These are ceilings, not contact targets. The ASR ExecutionPlan uses a positive 0.001
GPU-hour schema ceiling while its pinned protocol enforces CPU execution; report actual
GPU work separately and do not attribute a concurrent core service to the ASR tool.
There is no contact authority in these files. Both experiment cells admit only the
check stage, and shared campaign admission refuses worker, campaign, tokenizer-fit and
feature-preparation modes. The public check still needs its ordinary preflight gates:
this CPU source validation is not a claim that public preflight or launch admission passed.

## Analysis fixed before new results

The adjacent analysis-plan.json is pinned by both experiments. Evaluate the dataset's
native transcription, PERSON, other-entity, non-entity, numeric and semantic-impact metrics.
Do not introduce meeting-minutes or summary scoring.

Use pooled word-error ratios as the natural-mixture result, paired call resampling with
10,000 draws and seed 20260915, equal-call/equal-sector views, and complete sector and
sample-rate tables. Windows are not independent calls. Show CI95 for the two priority
gains, overall WER and PERSON; their simultaneous coverage is at least 90% by Bonferroni.
CI90 remains descriptive for comparison with historical reports.

A promising candidate has nonnegative point gains on both priority endpoints, a positive
CI95 lower bound on at least one, and a positive equal-call gain on that supporting endpoint.
This decides whether a matched replication merits consideration, not a stable-gain claim.
A priority tradeoff receives a named review. Small insertion increases are reported and
analyzed separately without automatic rejection, following the owner's prospective ruling.
All old verdicts, including the strict insertion-rule failure, remain unchanged.

Score each complete manifest once and preserve sufficient per-call statistics and alignments
on the first run. Register the paired analysis before opening quality-bearing artifacts,
and release neither arm until both seal or a formal terminal closure ends the comparison.
Use the shared bundle/score validators and paired resampler. Legacy hard-coded historical
verdict scripts are not the executable analysis for this new pair.

Postseal native window reconstruction is now implemented in the shared saved-score reader
and verified through the six configured synthetic lifecycle variants. The reader replays the
recorded unit delivery using the same pure stitch implementation, validates native Solver
selection or abstention, binds original source windows and request/response/USE records,
and reconstructs the scored parent text exactly. Normal acceptance, terminal last-Solver
delivery, finite fallback, abstention, saturation and empty windows remain distinguishable.
It never treats a later Reviewer or Planner response as the final transcript.

The shared saved-score entry consumes first-score alignments without invoking the official
scorer or reference loader again. Window statistics preserve the authoritative call totals
and whole-prefix normalization, including numeric words split across window boundaries.
Their alignment allocation is a diagnostic convention, not reference-audio timing or a
causal attribution to a selected tool. Whole-call metrics and call-cluster intervals remain
the scientific authority. Source-byte validation remains the earlier runtime/preparation
evidence; this replay verifies sealed custody rather than reopening audio.

Attribute actual evidence supply, tool selection, valid spans, returned evidence consumption,
Planner routes, first/final Solver changes, saturation, fallback, abstention and contact
exhaustion. Tool-selected subsets are observational; these diagnostics do not establish a
causal tool benefit. Report all component costs even though offline task quality is primary.
A stable task gain and trajectory-sampling optimization remain unproven. Root-authored
prompts and engineering fixes are not a training-free RL algorithm.

## Verified preparation

The model-free full-config validator resolved the real four-fragment configuration, 44
source calls, all 1,593 original window/packet bindings, exact role material, both context
stores and the local Whisper checkpoint/source/package inventory. It did not open an
attempt gate, load a model or contact ASR, a tokenizer, an encoder or a GPU service.

The original source-validation receipt predates the added analysis-plan pin. The successor
config audit proves that removing only that metadata pin exactly reproduces each prior
validated composed hash. It does not pretend to repeat the source-byte validation.

The final focused regression passed 509 tests with three existing dependency warnings.
It includes six configured synthetic lifecycle variants through the real shared
OpenJiuwen path, current-window duration in actual rendered requests, native JSON actions,
context/tool/revision composition, exact role authority and held-stage refusal. Mocked
boundaries include real model responses, neural ASR, capacity endpoints and final
bundle/scoring handoff. Passing tests prove these engineering contracts, not real task gains.

The full configuration exposed noncanonical governed-component registrations and missing
exact registry-inventory expectations. Root moved builder, provider, rank and fuse
registration to the existing canonical shared sites and made named-store consumption resolve
the registered provider. No exception was added to the engineering checker. Preserve the
initial failing check logs; the final regression, Ruff, engineering-base and diff checks pass.

Evidence under SPEECHRL_DATA_DIR:

- coordination/e21-native-window-bridge-v1/full-config-model-free-validation-v1.json;
  SHA256 b9e167dc9b993d37adcd4803f586aab1884445d80b45a2ea983601994f7839bc.
- coordination/e21-native-window-bridge-v1/full-config-analysis-binding-v2.json;
  SHA256 e019d8f2a6973b8378a0d3018439d93353d108442fef4f0cb6d633e6a5bce0d7.
- coordination/e21-native-window-bridge-v1/root-native-config-regression-v3.log;
  SHA256 44ab7544cf3b9e92ed342d0784b5c17ebbadf2a207bf2d774c69ccc796819453.
- coordination/e21-native-window-bridge-v1/root-native-config-engineering-v3.log;
  SHA256 613643e59993d175182a9ef3f2f7c74c4a14444ed4067d2031c456c53f2d0bd0.

## Remaining finite work

1. Reconcile and analyze Audio2Tool when authoritative terminal evidence arrives; obey the
   owner's hold on every subsequent GPU contact. Keep active flight worktrees frozen.
2. Integrate this reviewed shared source at an allowed flight boundary. Native saved-score
   window reconstruction is CPU-verified; preserve its exact receipt/trace and score pins
   when instantiating a future registered postseal analysis.
3. Preserve the prepared SLURP and E21 configurations. After explicit owner resume and
   scientific eligibility, complete exposure bindings, serving identity, actual fits and
   full paired execution. Do not infer authorization from this readiness note.
4. Diagnose task quality personally, then choose only a justified matched replication or
   named component change. Define algorithmic trajectory-sampling factors after the base
   exhibits reproducible benefit.


## Window-reader closure

The focused window/delivery/score/native regression passed 263 tests with three existing
dependency warnings. Ruff, engineering-base and diff checks passed. These checks overlap
the earlier configuration suite and their counts must not be added as independent coverage.
The configured lifecycle still mocks neural responses, capacity and final bundle creation;
the synthetic saved-score entry substitutes already-verified bundle/score receipt boundaries.
No real core, ASR, tokenizer, encoder, official scorer or reference loader was invoked.

Source changes are confined to shared analysis modules and tests. Historical WindowSpan
serialization remains unchanged when no explicit execution unit is present; the new path
adds unit identity, delivery kind and skip status. Rehashed parent output, altered source
geometry, missing responses, order/hash drift and Planner-as-answer substitutions refuse.

Evidence under SPEECHRL_DATA_DIR:

- coordination/e21-native-window-bridge-v1/root-native-window-analysis-regression-v1.log;
  SHA256 8bb93f9b7e53698e57c381e4727b16884d579a12b8427853a454f8e5062a7bfd.
- coordination/e21-native-window-bridge-v1/root-native-window-analysis-engineering-v1.log;
  SHA256 613643e59993d175182a9ef3f2f7c74c4a14444ed4067d2031c456c53f2d0bd0.
