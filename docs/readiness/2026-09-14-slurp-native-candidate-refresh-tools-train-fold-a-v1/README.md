# Held native candidate refresh and selective tools on TRAIN A

Date: 2026-09-14. Root prospective design under OWNER-CANDIDATE-COVERAGE-026.
Status: configuration and model-free preparation only. The unchanged TRAIN A
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
   Use its postseal recipe v2; never manually score it a second time.
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

This held config has no generation, ASR or fit authority and no prepared phase
supply receipt. Do not turn placeholder fields into launch evidence.

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
