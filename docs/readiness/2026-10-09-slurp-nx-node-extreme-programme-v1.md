# NX node-extreme programme v1 (SLURP, Stage 3): audit of 2026-09-30 -> 10-09 and the next-stage design

Status: the owner approved this programme as the plan of record on 2026-10-09 (chat, Chinese; English
rendering in section F). Owner ruling 2026-10-09: "Decision 228: A; 229-234: agreed, go with what you recommend" -- rows 228-234
are RULED as recommended (base = the COMP-1b lock); 235/236 withdrawn. GPU rounds may now be registered once
E1 and E3 land. Model-free work (E1-E4, R0.x) starts at once.
Registry: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` (section "Decisions 228-236").


Author: Fable 5.1 (root planner), 2026-10-09. Chat in Chinese; this document in English.
Owner premise (2026-10-09, translated): "system-level optimisation presupposes that every local point is
optimised to its limit." This plan audits the past nine days of experiments against that premise, names the
weak points, and designs the next stage so that each node is pushed to its measured limit BEFORE any joint
optimisation. Nothing here is executed yet; it is a plan for owner approval. Open owner decisions are rows
228-234 (section D).

Sources read: `docs/handoff/HANDOFF-TO-FABLE51.md` (9,335 lines; all 2026-10-01 .. 10-09 entries), decision
registry rows 212-227, every `docs/results/2026-10-0*` note, the readiness packages of the system-text search,
the fixed400 context line, the simple-consumption line, the local K4 Solver/Reviewer line and the joint N100
decision, plus the code map of the node contracts (`rails/supply_variants.py`, `rails/consumption_module.py`,
`rails/review_handoff.py`, `rails/delivery_normalisers.py`, `reproduction/slurp_scoring.py`,
`analysis/slurp_process_metrics.py`). Three read-only audit agents extracted the numbers; every number below
carries its file.

---

## A. What happened 2026-09-30 -> 10-09 (facts)

### A1. The SLURP test-sample milestone (decision 213 successor) -- the one real result
`docs/results/2026-10-01-slurp-milestone-successor1-read.md`: PLAN vs COMP-1b, 3,010 rows each, 682 clusters,
paired cluster bootstrap 10,000 draws, post-stratified over 58 intents.

| weighting | intent delta pp [CI95] | SLU-F1 delta pp [CI95] |
| --- | ---: | ---: |
| natural mixture (primary) | **+5.80 [+4.04, +7.42]** | +0.79 [-0.44, +2.02] |
| equal intent strata | +3.02 [+1.03, +4.82] | +0.91 [-0.38, +2.42] |

Levels: intent 77.02 -> 82.82 %; SLU-F1 64.18 -> 64.98 %; 235 intent saves vs 87 harms; entity TP 1401 -> 1437,
FP 1320 -> 1325, FN 1084 -> 1048; on the 1,255 zero-gold rows false entities 504 -> 511. DEV replicate was
+4.60 [+2.58, +6.73] (`docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md`). Verdict on file: "HELD;
intent gain retained, slot gain unproven". Cost +5.4 % GPU-h (4.685 -> 4.939). Caveats the note itself states:
COMP-1b is a bundle (agreement vote + centroid keys + k60 pool) so no component gets credit; the SLU guard
margin was borrowed from the DEV null; no multiplicity correction per intent.

**Reading under decision 209-C:** the INTENT gain is stable and replicated (DEV CI-LB +2.58, test CI-LB +4.04,
same sign, same magnitude). The SLOT gain is not. Decision 210 ("what counts as replicated") was never ruled;
section D proposes the rule and the consequent partial lock.

### A2. The decision-214 "joint system-text search" (10-01 -> 10-03)
Design (`docs/readiness/2026-10-01-slurp-system-text-search-v1/README.md`): one pinned GPT-6 proposer rewrites
knowledge-construction text + Solver/Reviewer/Planner texts jointly; L (sees its own feedback) vs B (blind)
branches; utility per trajectory u = 2TP - F_ref(2TP+FP+FN); planned 16,800 trajectories.
Outcomes (`docs/results/2026-10-02-slurp-system-text-update1-feedback.md`, `...-root-diagnosis.md`,
`...-pilot20-root-feedback.md`, `2026-10-03-slurp-round5-n20-root-read.md`):

| round | n | result | why nothing was learned |
| --- | ---: | --- | --- |
| update 1 | 400 x 5 | B-cand2 -2.33 [-4.53, -0.17] rejected; L had NO valid candidate (3/4 proposals invalid) | Reviewer channel 100 % invalid (3,987/3,987 fenced JSON), 3,982 REVISE vs 5 ACCEPT, 0 lookups; 13,968 contacts spent on a defective system |
| pilot20 | 20 x 8 | both L candidates = no-change; A/A gaps -5.42 [-17.1, +4.5] and +3.04 | n = 20 |
| context20 | 20 x 4 | Planner-text +2.54 [-0.17, +9.04] | n = 20, single stratum |
| round 5 | 20 x 8 | both L proposals no-change again; A/A offsets -3.01 / +3.67 | n = 20 |

The L branch never produced one learned change. The knowledge tool was never called in any family.

### A3. The template-population learner (10-04 -> 10-06): K16, updates 2-6, all rejected
Reward = sum over 16 x 20 trajectories of u; acceptance = strict population sum > the single stale "before"
(-56.16 measured once on 10-05); proposer input progressively abstracted to K aggregate records with node
quality = null (owner receipts of 10-04/10-06). Results (`docs/results/2026-10-06-slurp-update{3,4,5,6}-*`,
`docs/receipts/continuation/2026-10-06-historical-selection-diagnostic.json`):

| update | utility after | children beating own parent |
| --- | ---: | ---: |
| 3 | -59.59 | 9 / 16 |
| 4 | -66.32 | 5 / 16 |
| 5 | -69.33 | 6 / 16 |
| 6 | -66.72 | n/a |

Noise floor at n = 20 (19 same-flight A/A pairs): gap range -12.30 .. +8.15, RMS 5.21 F1 points; the SAME seed
across flights 55.39 .. 66.47 (SD 3.47); unchanged branch-15 moved 53.3 .. 60.2 across updates
(`docs/results/2026-10-06-update6-original-a-repeatability-audit.md`). Candidate effects -10 .. +2. Win counts
9/5/6 of 16 are what a coin gives. Of ~72 h, GPU science ~23 %; 599 receipts in three days, ~100 incident-type.

### A4. Simple consumption and the local K4 line (10-07 -> 10-09) -- the owner's "local first" order
Roster: TRAIN, the first 100 of the UPDATE2 fixed400 pool (`configs/experiments/slurp-simple-consumption-
architecture-n100-v1.json`), repeatedly exposed, 34/100 empty-gold.

N100 family (`docs/results/2026-10-08-simple-consumption-n100-complete-family.md`):

| system | SLU-F1 | intent | calls | mean s | first raw parse | false fill /34 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| seed | 62.44 | 83 | 610 | 32.8 | 87/100 | 11 |
| seed A/A | 62.75 | 86 | 592 | 31.8 | 90/100 | 10 |
| review-off | 60.96 | 87 | 200 | 17.2 | 100/100 | 10 |
| solver-lookup | 57.62 | 84 | 216+16 | 22.8 | 100/100 | 12 |

review-off minus seed -1.48 [-5.33, +2.72]; lookup minus A/A -5.13 [-9.49, -1.04]. Reviewer process (seed):
detection 32/44, false alarms 17/43, correct entity after a true alarm 1/32, raw model entity repair 0 (13
unknown); deterministic post-processing repairs 3/54.

Local K4 Solver update 3 (review-off base, `docs/readiness/2026-10-09-slurp-local-solver-k4-update3-complete-
analysis-v1/README.md`): raw entity exact control 47 / A/A 46 / c4 **50**; F1 c4 - control +1.23 [-2.06, +4.52];
selected c4 (bundle `3fed5090...`). Local K4 Reviewer update 2 (`...-reviewer-k4-update2-...`): net raw repair
control 0 / c1 **+1** / others 0 or -1; detection c1 26/46, false alarms 5/37; F1 c1 0.6177 vs control 0.6209;
selected c1 (bundle `1a3a9ea4...`). Joint N100 five-policy composition prepared and HELD
(`docs/readiness/2026-10-09-slurp-local-to-joint-n100-v1/root-decision-v1.json`). Code-map finding: the
selected Solver donor has NO revision paragraph (it was authored on review-off); the joint members would run it
inside the full Reviewer graph.

Live state (09 Oct, read-only): GPU idle, llama-server resident (`-c 98304 -np 4`, q8 KV); no flight running;
a CPU registration process of the joint composition was live in `codex-local-k4-capacity-caption-v2`; master
`b8e9dd744` clean.

---

## B. Diagnosis: why nine days produced one result and no local optimum

**W1. Every optimisation ran below the instrument's own resolution.** The binding law of 2026-09-26
(`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`) says: < 200 rows = form proof; same-flight
paired floor ~0.7 pp at n = 200; cross-flight needs an in-chain A/A and ~2.5 pp at n = 1,080. The 10-02 .. 10-09
lines ran at n = 20 (CI +-15) and n = 100 (CI +-4.5) while hunting 1-3 pp effects. Selections (Solver c4, Reviewer
c1, Planner-text) are therefore draws from noise. "Optimised to the limit" cannot be claimed at n = 100.

**W2. The reward was a terminal scalar with no credit assignment.** One number per trajectory, four node texts
rewritten at once, the proposer blind to per-input content and to node quality (null). The process diagnostics
already show where the mass is (W3) but the learner could not see it. The local K4 line fixed the credit problem
(one node, a node-local primary) but kept W1.

**W3. The nodes have large, measured, unaddressed local defects** (all from the N100 and Fold-A diagnostics):
- Solver: first raw parse 87-90/100 on the full graph vs 100/100 on review-off (a contract defect on the revision
  path, root cause unknown); empty-gold false fill 10/34 (29 %); non-empty exact 24-25/66 (37 %); of 407 delivered
  gold-side errors 107 had the value IN the supply (consumption, 8.98 pp oracle; re-plan v6 S3).
- Reviewer -> Solver loop: raw repair 0/100, repair after a true alarm 1/32, false alarms 38 %, every alarm
  revises; costs 3x calls and 2x latency; review-off loses only -1.48 [-5.33, +2.72]. Deterministic
  post-processing repairs more than the model's revision does.
- Planner / tools: 0 lookups in 289 opportunities with tool_choice = auto (`docs/results/2026-10-03-slurp-postcall-
  source-audit.md`); the forced-lookup form harms (-5.13). The model-initiated tool (decision 206) is dead today.
- Perception: gold-on-list 92.1 %, initial candidate coverage 93/100; the intent residual is 8 % off-list plus
  rank-2/3 conversion 29.5 % (re-plan v6 section 1).
- Post-processing: the entity support filter (s = 3) read +1.40 [+0.55, +2.29] offline on sealed samples
  (`docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`) -- one of only two Stage-3 effects that
  ever cleared its floor -- and is NOT in the lock (normaliser v3 has "no support filter",
  `docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md`).

**W4. Baseline fragmentation and exposure.** Two baselines now coexist: the replicated COMP-1b lock (v2.1 +
agree-vote + centroid key, Fold A / DEV / test) and the ChatGPT "seed" bundle `ba18a4a8...` on the
slot-review-contract graph (TRAIN N100). The local line optimised the second. All of 10-02 .. 10-09 reused the
same 20/100 TRAIN inputs with no held-out set; Fold B / Fold A / DEV discipline was dropped.

**W5. Throughput.** ~6-7 h per update for 2.5 GPU-h of science; ~200 worktrees; monitors, observers, memory
floors, precontact refusals consumed ~25 % of wall time and ceremony another ~50 %. A local-optimum search needs
tens of candidate evaluations per node; at the current cadence that is months.

**W6. Governance drift.** Decision 210 unruled, so the milestone's replicated intent gain never became a lock;
decision 211 (carriers after the lock) is therefore stuck; the joint N100 (n = 100, defective donor) is about to
spend GPU on a contrast it cannot resolve.

---

## C. The next stage: node-extreme programme (NX)

### C0. Principles (each fixes a named weakness)
1. **Measure at the node (W2).** Each node gets a node-local primary metric computable per row against offline
   TRAIN/DEV gold under the governed loaders, plus an "exchange rate" to the official metric estimated once from
   sealed trajectories (how much delivered SLU-F1 / intent one unit of node metric buys).
2. **Replay, do not re-fly (W1, W5).** The node under test is re-generated over the SAME sealed predecessor state
   with K template variants interleaved in ONE flight, the delivering arm being the locked template (the exact
   form of `rails/supply_variants.py`, item E42, with the varied axis moved from SUPPLY to the node's
   INSTRUCTION TEMPLATE). Paired per-row, no flight offset, n >= 1,080.
3. **Offline first (W1).** Anything computable over sealed outputs (post-processing, support filter, parse
   robustness, selection rules) is optimised at 0 GPU and 0.67 pp resolution before any contact.
4. **One node per round, the rest frozen; plateau rule; byte-pinned locks (owner 10-08 order).** Two evaluated
   rounds without a CI-LB > 0 node gain -> lock the best and move on. Every lock is a pinned template or rule in
   the module `saea-evidence-consumption-module-v1`.
5. **Diagnosis-driven candidates (W2).** Candidates (K <= 6 per round) are written from the failure-class contrast
   tables of the node (aggregate counts and anonymised structural features; never utterance text), by the
   proposer or by hand; both are allowed, both are labelled.
6. **Exposure discipline (W4).** TRAIN Fold B (1,080) selects; TRAIN Fold A (1,080) confirms once per lock;
   DEV-2000-ADDED reads the composed system; the test sample only under a new owner allowance.
7. **One base (W4).** All NX rounds run on ONE declared base. Recommended: the COMP-1b lock as flown in the
   milestone (the only replicated system), with the Reviewer loop treated as a component under test (R2).

### C1. Engineering deliverables (model-free; Sonnet builds, Fable reviews, Opus audits)
- **E1 Node-template variant arms.** Extend the E42 arm mechanism with an `instruction_template` override kind
  at ONE node (Solver first, then Reviewer, Planner): K arms over the same `QueryState`, delivering arm = locked
  template, every arm's request/response sealed under its arm id; refuse any other knob (same fail-closed style).
  Files: `rails/supply_variants.py` (new arm kind + knob tail), `rails/runner.py` (arm fan-out at the node),
  `core/bundle/outputs.py` (arm columns in sealed outputs), `rails/consumption_module.py` (a `columns` entry of
  kind `template`), `scripts/checks/finite_completion_policy_check.py` / `stage3_effect_floor_check.py`
  (declare design = same-flight node column). Proof: 4-row dry run, byte identity of the delivering arm with the
  plan's request (I7 unchanged).
- **E2 Node-local readers.** One reader per node over sealed arm columns: Solver (raw parse validity, raw
  entity exact-set, empty-gold false fill, non-empty exact, value-in-supply conversion), Reviewer (detection,
  false alarm, revision, raw repair/harm), Planner (offer / call / precision), Perception (gold-on-list, rank);
  paired per-row Wilson / cluster bootstrap; reuse `analysis/slurp_process_metrics.py`,
  `analysis/review_findings.py`, `analysis/slurp_solver_stage_attribution.py`.
- **E3 Exchange-rate script (0 GPU).** From the sealed COMP-1b Fold A and A2 DEV bytes: delivered-F1 change per
  raw-exact entity gained / per false fill removed / per repaired draft; intent change per rank-1 gain. Output:
  the per-node conversion table that every R-round's declared effect must cite (decision 192 form).
- **E4 Post-processing v4 search harness (0 GPU).** Offline rule search over sealed pools (A2 DEV 1,000; Fold A
  1,080): normaliser v3 + support filter (s = 2/3/4) + scope rule + explicit-empty handling; read at 0.67 pp;
  select on A2, confirm on Fold A.
- **E5 Round cadence contract.** One registered cell per round (K arms in one campaign), one countersign, one
  read; monitors only at launch; no per-member ceremony. Target: <= 3 h wall per round at ~2 GPU-h.

### C2. Rounds -- detailed experiment designs

| round | node / object | GPU-h | n, design | primary metric (guard) | candidates | acceptance / lock |
| --- | --- | ---: | --- | --- | --- | --- |
| **R0.1** | base unification | 0 | byte-diff seed `ba18a4a8...` vs the COMP-1b lock (phase program, templates, knowledge, k) | -- | -- | owner picks the ONE base (row 228) |
| **R0.2** | exchange rates (E3) | 0 | sealed COMP-1b Fold A + A2 DEV | -- | -- | table on file; sets every R-round's predicted pp |
| **R0.3** | Solver parse root cause | 0 | sealed N100 seed vs review-off bytes: where the 13 unparsed first drafts come from (revision history? format?) | parse validity | -- | fix is a candidate in R1 |
| **R0.4** | post-processing v4 (E4) | 0 | offline over A2 DEV 1,000 (select) then Fold A 1,080 (confirm) | pooled SLU-F1 at 0.67 pp (intent 0 rows differ) | normaliser v3 + support filter s in {2,3,4} + scope rule + explicit-empty | lock v4 if Fold-A CI-LB > 0; predicted +1.0..+1.4 (support filter alone +1.40) |
| **R1** | Solver (slot extraction; owner focus) | ~2.5 per round, 2 rounds + 1 confirm = ~7 | E1 Solver template column, K = 6 arms, Fold B 1,080, same-flight paired | raw entity exact-set per row; secondaries empty-gold false fill, non-empty exact, value-in-supply conversion, parse validity (intent rows differing <= 0.65 pp) | from R0.3 and the N100 contrast tables: explicit `entities: []` legality (199), value-in-supply citation, spoken-order walk, the c4 donor with a revision paragraph, one-pass type inventory, hand-written contract tightening | select the arm with CI-LB > 0 on the primary AND no secondary loss; confirm once on Fold A as a 2-arm column; lock the template. Declared effect via E3 (target >= 1.5 pp delivered SLU, source: 107/407 value-in-supply errors) |
| **R2** | Reviewer -> Solver repair loop: fix or drop | ~2.5 + ~2.5 | (a) Reviewer replay column over sealed Solver drafts, K = 5, Fold B; node metric against offline "draft wrong?" labels; (b) two-node replay (finding -> Solver revision) for the top 2 | (a) detection precision/recall, false-alarm rate; (b) net raw repairs per 100 true-error drafts, harms (SLU no loss) | verifier-with-evidence-in-view, single-finding max, nonempty-only review, the c1 donor, Reviewer on the R1-locked Solver | if after two rounds net repair CI-LB <= 0 at the measured cost: DROP the loop (review-off locked; calls 610 -> 200, latency halved); else lock the pair |
| **R3** | Planner / model-initiated tool (206) | ~2 | Planner offer column, K = 4 offer phrasings, Fold B; sealed states where the draft is wrong and the value is available vs where it is right | call rate; call precision P(call \| draft wrong & value available) vs P(call \| draft right); row-206 three-part gate | offer phrasings, lookup / missing-slot proposal (S2 contract) as the offered tool | if no phrasing clears the 206 gate: tool line CLOSED for this core (no system-default call); else lock the offer |
| **R4** | Perception (intent) | ~2.2 | P-SV-4 as already registered (decision 208), on the E1-era harness | gold-on-list, rank-1 share; intent | K6p key-source column | NOMINATED -> DEV replicate before module entry (re-plan v6 section 4) |
| **R5** | composition (owner's stage 2) | ~5 | module v3 = base + R0.4 + R1 + R2 (+ R3, R4 if locked) vs base, DEV-2000-ADDED 1,000, in-chain A/A | official intent + SLU-F1, cross-flight bar 2.5 pp (or same-flight module column if E1 reaches all nodes) | one composed candidate | NOMINATED -> owner allowance for a second test-sample read (row 233); that read decides the SLURP full lock |

Total GPU ~25 h over ~2-3 weeks; R0 is zero-GPU and starts immediately. **Amended by section F (owner
2026-10-09): R2 is removed; the base graph is review-off; the supply rounds (Stage S) follow R1; R3 stays only
if the owner keeps a tool line.** R4 is independent and may interleave in the queue if the GPU would otherwise
idle (owner standing rule). The joint N100 (ChatGPT) is NOT flown; its Solver donor becomes an R1 candidate at
n = 1,080; its Reviewer donor is retired with the loop.

### C3. Candidate authoring protocol (for the proposer or a hand author)
Input = node contrast table from the sealed base: for each failure class (SPURIOUS / MISSING / WRONG-TYPE /
BOUNDARY / NEAR / WRONG-VALUE / FORMAT; empty-gold fill; parse fail) the count, the per-slot-type split, whether
the value was in the supply, and the structural features of the request (token counts, supply item counts,
history length). Output = K templates, each with a one-line mechanism hypothesis and the failure class it
targets. Never utterance text, transcripts, gold values or model outputs. Both proposer-written and hand-written
candidates are labelled as such in the read.

### C4. Verification of the stage itself
- E1 proof: 4-row dry run; delivering-arm bytes identical to the locked plan request; `stage3_effect_floor_check`
  accepts the cell as a same-flight node column; `finite_completion_policy_check` passes.
- Every round's read: paired per-row CI; the declared effect (from E3) on file BEFORE flight (decision 192);
  the plateau rule applied mechanically; locks are byte-pinned in the module config with their read id.
- Replication: each lock confirmed once on Fold A; the composition once on DEV-2000-ADDED with an A/A; the
  test sample only under a signed allowance, one attempt, aggregate-only.

---

## D. Owner decisions requested (registry rows 228-234)
- **228 One base for NX.** A: the COMP-1b lock as flown in the milestone (recommended: replicated on the test
  sample); B: the ChatGPT seed bundle `ba18a4a8...` (TRAIN N100 incumbent). R0.1 byte-diff is run either way.
- **229 Decision 210 rule + partial lock.** "Replicated" = CI-LB > 0 on DEV-2000-ADDED AND on the signed test
  sample for the same metric. Under it, SLURP **intent is LOCKED** at COMP-1b (DEV +4.60, test +5.80); SLU-F1 is
  OPEN (the NX slot line). Decision 211: does the intent lock reopen the Audio2Tool / Earnings-21 ALL-OFF A/A
  cells (model-free A2T proof already on file; E21 needs ~4 GPU-h), or do carriers wait for the full lock?
  Recommended: wait for R5, keep model-free carrier prep going.
- **230 Do not fly the joint N100.** Fold its two donors into R1/R2 at n = 1,080. (n = 100 cannot resolve the
  +1.23 / +1 effects it would test; the Solver donor lacks a revision paragraph.)
- **231 Measurement floor for every NX round.** No read below n = 1,080 same-flight paired (form proofs at 4
  rows only). Supersedes the 20/50/100/200 ladder of decisions 220/223 for SLURP node work.
- **232 Reviewer loop fix-or-drop rule** as in R2: two rounds, net repair CI-LB <= 0 at measured cost -> drop.
- **233 Second test-sample allowance** (successor-2) for the R5 read, drafted after R5 reads NOMINATED on DEV;
  same terms as v2 (one attempt per id, aggregate-only, no smoke, no re-fly).
- **234 Cadence.** One registration/countersign/read per round (K arms in one cell); job-scoped monitor at launch
  only; the ChatGPT root keeps the N100 custody but no new N20/N100 GPU families during NX.

---

## F. Owner clarifications of 2026-10-09 (three points) and the resulting amendments

**F1. Critical path = template-based learning from statistics, two stages: knowledge USE first, then knowledge
SUPPLY.** Adopted. The NX rounds are re-grouped:
- Stage U (use): R0.4 post-processing v4 (offline), R1 Solver template (the model's use of the supplied
  knowledge), R3 only if the owner keeps a tool line. Learning signal = node-local aggregate statistics per
  failure class (section C3), never per-sample review. The proposer (or a hand author) sees contrast TABLES
  (counts per failure class x slot type x value-in-supply x request structure) and writes K templates; the
  column read at n = 1,080 returns the same tables per arm; the plateau rule closes the node.
- Stage S (supply): after the Solver template is locked, the SAME harness varies the supply at the Solver node
  (the existing E42 supply-variant arms): exemplar count / selection (M1 k), slot-store release, key source
  (K6p), explicit-empty signal (N1), card selection (K8). Candidates come from the locked Solver's residual
  tables ("value not in supply" vs "in supply, not used"). Each round ~2.5 GPU-h, Fold B select, Fold A confirm.
- Stage J (joint): R5 as before (composition read on DEV, then the second test-sample allowance).

**F2. The Reviewer-class capability is beyond a 30B-A3B core.** Agreed, and the record supports it: raw model
repair 0/100, correct entity after a true alarm 1/32, false alarms 38 %, every alarm revises, 3x calls; the
Planner never called a tool in 289 offers (0/289) and the forced lookup harmed (-5.13). Amendment: R2 is
REMOVED as an optimisation round. The base graph for NX is review-off: Perception -> Solver -> deterministic
post-processing (Planner iterations 0, max_revisions 0, the compiled `phase-native-module-v1-c2` program). The
"review" function moves to deterministic verification (support filter, scope rule, explicit-empty handling in
R0.4) and to knowledge supply (Stage S). The only residual check: the review-off vs full-graph contrast is read
ONCE at n = 1,080 as a column of the first R1 cell (two delivering-path twins), so the -1.48 [-5.33, +2.72]
N100 number is replaced by a resolved one; if the full graph wins by > 1.49 pp SLU with CI-LB > 0 the drop is
revisited, otherwise review-off is locked (calls 610 -> 200 per 100 rows, latency ~2x faster).

**F3. Can the new Qwen ASR model replace the Omni core locally?** Facts found (web, 2026-10-09):
- Qwen3-ASR (open weights, Apache 2.0, released 2026-01-30; 0.6B and 1.7B; AuT encoder 180M/300M + Qwen3
  0.6B/1.7B decoder; 52 languages; transformers + vLLM via `pip install qwen-asr[vllm]`; FLEURS-en WER
  4.90 % avg over 12 languages for 1.7B; GGUF conversions exist but upstream llama.cpp support is not
  confirmed -- the Renesas GGUF targets a proprietary runner). Sources: https://arxiv.org/pdf/2601.21337 ,
  https://github.com/QwenLM/Qwen3-ASR , https://qwen.ai/blog?id=qwen3asr ,
  https://huggingface.co/Renesas/Qwen3-ASR-1.7B-GGUF
- Qwen-Audio-3.0-ASR (technical report 2026-09-09, arXiv 2609.07549): MoE LLM decoder, SenseVoice-style
  encoder + CTC, instruction-controlled context / hotwords / polishing, LibriSpeech-clean 1.19 % vs
  Whisper-large-v3 1.86 %, FLEURS-en 4.17 %. The report states NO open weights, licence or HuggingFace release;
  until weights appear it is API-only and therefore excluded by the paid-API = 0 rule.
  Source: https://arxiv.org/html/2609.07549v2
- Verdict on "replace": an ASR model alone cannot replace the Omni core, because the carriers need decisions,
  not text (SLURP intent + slots, Audio2Tool tool calls); only Earnings-21/22 (WER) would be served directly.
  The real alternative is a CASCADE: Qwen3-ASR -> transcript -> a frozen TEXT LLM (Qwen3 text, same knowledge
  supply and templates). That is exactly the "ASR + LLM" configuration decision 206 warned about and it changes
  the thesis object (frozen speech/omni multimodal LLM, `wiki/Project-Thesis.md`); it is an owner-level thesis
  decision, not an engineering swap. Two measured risks: Whisper-large-v3 transcripts contained only 0.7513 of
  the gold slot spans on Fold A (E5-1 stop at 0.80), and transcripts in the Omni prompt cost intent -0.90 pp on
  DEV; SLURP audio is far-field/noisy, so published clean-speech WER does not transfer.
- What CAN be done now at 0 core contacts (proposed as **E6, the ASR capability probe**): one pinned
  Qwen3-ASR-1.7B pass over the Fold A and Fold B rosters as a logged tool contact of the E5-0 class (same
  catalog format, decoding config pinned), then the E5-1 oracle re-run: WER against the reference transcripts
  and gold-span containment vs Whisper's 0.7513 / 0.7606. Decision rule: containment >= 0.90 reopens the
  missing-slot proposal tool (S2 / decision 212 condition "an ASR recovering nearly all 28 misses") and
  qualifies Qwen3-ASR as the pinned tool; containment >= 0.85 additionally justifies ONE cascade probe on
  DEV-2000-ADDED (ASR text + Qwen3 text LLM, same supply, vs COMP-1b 81.5 % DEV intent) as evidence for the
  thesis decision; below 0.85 the core stays. Cost: `qwen-asr` install in the WSL venv (owner authorisation;
  no pip without it), ~4 GB VRAM beside the resident server (22.9 GB used of 32 GB) or CPU, minutes of
  runtime per 1,080 rows; for Earnings-21/22 the same pass yields a WER reference point for the carrier later.

Decisions 235 (E6 probe) and 236 (cascade thesis question) were proposed here and then **WITHDRAWN / closed by
the owner on 2026-10-09** ("Cancel the Qwen3-ASR exploration; there is no need to explore the engineering scheme
and implementation path for that mode. Return to focusing on the gains the agent system and the learning algorithm
can bring."). E6 is not run; the core stays the frozen Qwen3-Omni; the S2 missing-slot tool line stays closed at
the Whisper containment (decision 212 record). F3 remains as the factual answer to the question.

## E. Execution order and roles
1. (today, 0 GPU) Fable: this plan -> registry rows 228-234 proposed, handoff refresh (both handoff files).
   Opus: R0.2 exchange rates, R0.3 parse root cause, R0.4 post-processing v4 search. Sonnet: E1 + E2 + E4 in a
   worktree under `/home/chao/saea-worktrees/` (first action `git -C master status --porcelain`, must be empty).
2. (after rows 228/230/231) Fable registers R1 (cell + preregistration with the E3-derived declared effect);
   queue via the batch driver; Opus monitors; Fable reads by script.
3. R2 -> (R3, R4 interleaved) -> R5 -> row 233 -> test read -> full SLURP lock -> carriers (211).
Standing constraints unchanged: SLURP-only GPU (187), tools model-initiated (206), empty is legal (199), gold
never at runtime, Fold B tunes / Fold A evaluates, test closed except under a signed allowance, paid API 0,
worktrees only from WSL, flights only through the batch driver, 12-h serving restart rule.
