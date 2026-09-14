# Held native candidate refresh and selective tools on TRAIN A

Date: 2026-09-14. Root prospective design under OWNER-CANDIDATE-COVERAGE-026.
Status: configuration, original-audio metadata export and model-free preparation only. The unchanged TRAIN A
anchor is still generating. Do not read partial task quality or launch this
successor until its complete source, first score and diagnostics are released.

## Scientific question and complete-system comparison

Compare the complete successor against the unchanged native TRAIN A anchor on
the same ordered 1,080 recordings. Keep frozen weights, preprocessed speech,
serving geometry, output allowance, released intent and slot stores and sampling.
Add one bounded candidate refresh and Reviewer-selected evidence tools.
This is a complete-system change. It does not isolate the causal contribution
of each new component. Preserve the released direct-versus-native DEV evidence;
do not rerun a broad knowledge/no-knowledge grid.

Freeze the official pooled SLURP SLU micro F1 as the primary full-task metric.
Also report exact intent, scenario, action, exact intent-plus-entities, entity
exact match, and word/character/combined SLU counts and scores. Distinguish mean
per-sample F1 from pooled micro F1. Keep malformed, failed and fallback cases in
the full denominator with their delivery status.

Report natural-mixture and equal-scenario estimates and every scenario stratum.
Use paired speaker-cluster bootstrap with 10,000 resamples and seed 20260913,
reporting CI90. Report saves and harms, output saturation, input size, observed
tool calls, cache hits, new ASR decodes and OBS/ORG/SUPPLY/USE custody. Time and
cost remain measurements, never quality-selection vetoes.

Freeze C0 at the first actual Perception response and C1 at the last actual
Perception before the delivered Solver response. Report gold coverage, actual
distinct widths, recovered/lost coverage, final intent correctness conditional
on each coverage, common-covered resolution, and correctness outside C1.
Never form a candidate union or reconstruct candidates from final answers.
The 95% coverage target is prospective engineering direction at width at most
three; it is not an achieved result, a replacement historical gate, or authority
to widen the candidate set.

On TRAIN A, a higher full-roster primary point estimate is an exploratory
candidate for disjoint evaluation; report uncertainty and all quality tradeoffs.
Stage improvements alone cannot advance a version whose full-task primary
score deteriorates. A tie is not an improvement. Root must name a component
before a revised mechanism; do not repeatedly rerun to find a passing result.
Neither exploratory point selection nor TRAIN bootstrap establishes superiority
or generalization. Keep Fold B untouched until the candidate and its selection
record are frozen.

## Actual graph and evidence authority

Use the shared OpenJiuwen Perception -> Solver -> Reviewer -> Planner workflow.
Only Reviewer has analytical tools in this version. Perception and Solver
consume source-bound knowledge and observations; Solver alone delivers answers.
Planner can accept, revise Solver, or refresh candidates once. At most one
revision is allowed; exhaustion delivers the latest Solver answer.

Reviewer has at most three model contacts per visit. Reserve the last for a
tool-free report; a noncompliant tool request on it is refused before execution.
At most two Reviewer visits allow four actual analytical actions per episode.
Provide task-contract, candidate-contract and full-utterance ASR tools. Request
ASR only for a named unresolved distinction with expected information gain.
Do not claim arbitrary cropping or alignment is implemented.

Candidate lookup returns observed TRAIN slot associations and candidate-relative
contrasts. It must not turn optional co-occurrence into a required or forbidden
field. Rich semantic activation and extraction values still come from the
separate released stores. The lookup is not a substitute for that richer value
content. Exclude both A and B at canonical utterance level before constructing
its counts; exclude all sibling recordings and bind the resulting source hash.

Repeated requests for the same original utterance use one source/inventory/
protocol/span/representation cache entry even if the stated distinction or
source response changes. Keep each analytical action in the ledger while
charging only a cold ASR forward as new neural work.

## Resource and contact envelope to bind at admission

The owner confirmed the existing power configuration is optimal. Do not
investigate or adjust the power mode further; focus on useful model work.
The unchanged decoder service has four 24,576-token slots, 98,304 total context,
max512, and no mmproj. CPU Whisper uses local large-v3, fp32, beam5, temperature0,
batch1, sample_len256. The proposed protocol assigns one audio worker, four
inference threads and one interop thread. Across other preparation jobs reserve
at most two additional CPU workers during this campaign.

One selected CPU tool releases its model slot and runs through the shared
single-worker scheduler. The next model contact reacquires a slot with complete
history. Do not add another answering service, co-resident GPU Whisper, or fixed
ASR preprocessing. CPU ASR can still cause waiting; measure actual registered
calls and reduce avoidable waiting without synthetic GPU work.

Prospective complete-roster ceilings, not execution authority or target work:
12,960 primary model contacts (12 per episode); 51,840 actual-request fit
endpoints (four per model contact); 37,015 repeated primary speech seconds;
4,320 analytical actions; 1,080 new ASR decodes and 3,085 ASR speech seconds;
zero new encoder/paid API calls; one complete official score.
Bind a flight-specific fit-inclusive GPU safety envelope at admission using
complete anchor evidence; do not reinstate a retired global study budget.

The actual graph enforces the analytical bound. Reporting metadata is not an
independent numeric debit gate. Generation and cold ASR each require their own
ExecutionPlan and exposure row. No tool, tokenizer or model contact may overlap
the active anchor's exclusive generation lease.

## Admission and preparation handoff

1. Let the current campaign seal, run its one complete official score and finalize.
   Use its postseal recipe v3, which preserves v2 single-score ownership; never manually score it a second time.
2. Release complete TRAIN A trajectories and C0 diagnostics. Record root's named
   gap and complete-system admission; no partial-result design decisions.
3. Bind the prepared fold-excluded candidate catalog and the new CPU protocol.
   Reuse original audio addresses and existing packet/vector/knowledge receipts.
4. Create final generation, actual-contact fit and cold-ASR plans, exposure rows,
   run/attempt output namespaces, scoring registration and protocol/source hashes.
5. Prepare phase supply through FlightRuntime against that final configuration.
   Warm reuse must make zero encoding/model contacts.
6. At the run boundary bind the final clean checkout and existing service identity,
   obtain the sole lease, fit actual requests and dispatch through the shared entry.
   Keep source code for both versions until scoring and analysis are complete.

A separate preparation-only config permits the shared original-audio metadata
export independently of the scientific verdict. It has no generation, ASR or fit authority and no
prepared phase supply receipt. Do not turn placeholder fields into launch evidence.

## Training-free optimization handoff

After two complete paired TRAIN A sources, use the existing group-relative
feedback projections separately for each declared task metric: within-sample
centering and population-standard-deviation scaling, zero for zero variance.
Do not silently add a scalar reward, blend pooled micro with sample F1, or apply
a cost penalty. Analyze candidate recall, covered-set choice and slots separately,
while selection stays accountable to full final task quality.

Use actual trajectories to propose compact corrective procedures with provenance,
not a memory of TRAIN examples. Validate and freeze a candidate before disjoint
Fold B evaluation. No such optimization cycle is completed by this preparation.


## Structural knowledge audit and tool wording correction

The pinned factual audit is DATA/coordination/
slurp-native-dual-store-train-fold-a-anchor-recovery-v1/
knowledge-value-structure-audit-v1.json, SHA256
49e705adeef8c2cb38b6043ccab615896cdbdcec9b1acdbfbeeb0c26f0f2016e.

There are 60 intent keys/values with exactly one explicit confusable alternative
per intent, and 54 slot keys/values with 402 intent-slot associations. Exhaustive
enumeration of all legal candidate sets of widths one, two and three finds
maximum distinct slot-card counts of 16, 23 and 28. Thus the current 16/28
limits do not omit any uniquely mapped slot card. This says nothing about
semantic adequacy or the model's use of those cards.

Reviewer prompt v2 states the actual lookup scope: observed slot-type association
comparison. It must consult the supplied rich values for activation/extraction
meaning and explicitly report a missing semantic explanation. Do not promise
that the statistical lookup supplies those explanations.

After full source release, measure own-intent-card supply separately from
C0 recall. Use the exact manifest-verified initial Perception request's
supplied_evidence qualified as intent-boundaries::intent-boundary:<intent_id>.
Use bootstrap/initial-state IDs as strict cross-checks, not proof of delivery.
Keep C0 candidate IDs from the actual Perception response. Another card can
contain a useful contrast even when the gold intent's own card is absent.
Report supplied-and-covered, supplied-but-missed, not-supplied-but-covered and
neither. These describe support and model selection; they do not establish
semantic use, causality or an upper bound imposed by the full legal label list.
This diagnostic will determine whether a later experiment should change keys,
retrieval, discriminative values or evidence acquisition. Do not enlarge all
knowledge indiscriminately or change the live experiment.


Source-export entry correction: future live-tool declarations require actual
ASR plan bindings, even before that future runtime exports metadata. Preserve
both model-free refusal logs; no output or neural contact occurred. Use the
separate source-preparation experiment over the already registered incumbent
baseline, with identical Fold A identities and original packet/audio bindings.
The prepared metadata is independent of the future role graph. Do not disable
the runtime tool guard or invent a live ASR plan to pass it.

Reproduce the metadata artifact through core.flight.cli mode
prepare-speech-observation-sources, experiment/cell
slurp-train-fold-a-speech-source-preparation-v1, and output
DATA/prepared/SAEA-SLURP-TRAIN-A-LIVE-SPEECH-SOURCES-PREPARE-V1/sources.json.
Use the normal repo/data/runtime/lock arguments and literal checkout PYTHONPATH.
This preparation-only cell permits no other execution stage and contains only
discovery-role metadata, not a complete contact ExecutionPlan.


## Completed original-audio metadata preparation

The separate source-preparation entry completed without neural contact. The
source artifact contains exactly the registered 1,080 ordered TRAIN A records
and 3,084.5284375 seconds. Its per-record audio address, audio hash, duration
and packet ID match the dataset fragment; the shared loader verifies packet
hash fields, prepared input/output hashes and split identity.

Use prepared-tools-binding-v2.json for the catalog, CPU protocol and source
inventory pins. Source artifact SHA256:
e756e7f7dfb876e856dd0e12691a2e9497260036a1721efb883cd741d4ffd9c3.
Verification receipt SHA256:
c5420aacf78eccb7948a4bb12725af24933db52ba9874848b0d6b65b0819db1e.
No audio was decoded, no ASR transcript was produced and no model, tokenizer,
encoder, ASR or scoring contact occurred. This receipt prepares future
role-selected access; it grants no fit, generation or ASR execution authority.
