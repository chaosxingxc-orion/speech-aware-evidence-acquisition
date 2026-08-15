# Rectification & optimization plan (2026-08-15, owner-directed)

Triggered by the owner's four corrections this week: (1) the ceiling-logic error (bias vs
reflection operators); (2) the three-dimension legality doctrine (gold red line / system
capability / matching direction); (3) the agentic-era task-system frame; (4) the
literature-localization compliance gap. Owners: Fable=plan/evaluate, Opus=survey/writing/ops,
Sonnet=scoped code.

## Part R — compliance (immediate; two agents in flight)

- R1 Literature backfill [Opus, IN FLIGHT]: every paper cited by the two 2026-08-14/15
  survey notes fetched via scripts/survey/sf_fulltext_fetch.py, ledger-registered
  (FETCH 即登记), receipts committed. Done = 100% of citations registered or failure-annotated.
- R2 Survey protocol hardening [DONE]: standing memory written — every future survey brief
  carries fetch-and-register + local-ledger-first dedupe (1,459 rows of prior holdings).
- R3 Compliance check script [Sonnet, low priority]: offline diff of survey-note citations
  vs the ledger, scripts/checks style.
- R4 Dataset acquisitions [Opus, IN FLIGHT]: download HALAS (3.8MB, license "unknown" —
  flagged unresolved-for-publication) + SlideASR-Bench test (10.8GB, MIT, audio+entity_list
  only); verify on-disk slurp / slue-sqa-5 / spoken-squad against recommended variants;
  datasets.lock registration + receipts + inventory check.

## Part D — research-design rectifications

- D1 Ceiling claims re-scoped [DONE, 9ea16f4]: all "ceiling" numbers bound the STATIC-BIAS
  family only; the reflection operator is unmeasured and unbounded by them.
- D2 Legality doctrine codified [Fable, this week]: (i) gold and gold-derived selection
  banned from runtime; (ii) inference-time products of system modules over legal inputs are
  LEGAL knowledge (system capability is the research object, not cheating); (iii) matching
  direction must be deployment-shaped — speech/derivatives query the KB; keying granularity
  limited to what deployment truly holds (call identity: yes; in-call term/span selection:
  must be earned by the system's own matching). Becomes the design-review standard for every
  future arm.
- D3 ConEC full-chain redesign [after D5]: ConEC per-call documents (call-keyed, legal,
  10/10 frozen-ten coverage) as the KB; pass-1 draft spans as queries (S1 band-matching);
  reflection-mode targeted delivery. The static full-list dump is demoted to a diagnostic
  control (dishonest-adjacent per doctrine (iii) + N~100 distractor cliff). Casing recovery
  needed (ConEC E-21 contexts are lowercased word lists).
- D4 Reflection R-ladder [after D5]: R1 (span audio + reference) / R2 (+ own errored draft)
  vs measured B/C anchors; MANDATORY wrong-reference control arm (MCR-BENCH text-bias
  threat: if the model copies a wrong reference, we are measuring text-following, not audio
  verification); adopt Voice Memory's Harmful Edit Rate + recoverable-information ratio;
  prompt free-axes (draft slot / provenance wording / top-1-vs-k) probed at MM-1 scale
  (<=16 requests each) before any arm.
- D5 roster-band flag source [Sonnet, NEXT DISPATCH]: S1 band-matching as a config-selectable
  flag source in obs-replay-loop (v3 harness parameters: band [0.05,0.45] low-end weighted,
  df-rarity smoothing, K=2/slice), replacing logprob flags for targeted-delivery arms.

## Part T — task-system expansion (strategic)

- T1 Leverage-probe ladder [after R4]: SLURP slot repair (user-ontology matching -> command
  success; boundary via the entity clause, owner confirmation pending); SLUE-SQA-5 with the
  deleted-pairs restoration (score answer-destroyed items as failures — the literature
  under-states entity cost by construction); SlideASR-Bench (roster machinery transfer test
  off earnings calls). All designed under doctrine (ii)/(iii): self-transcribed documents
  are legal system products; supplying gold document text is not.
- T2 Agentic task-system decision [owner, after the extended survey returns]: citation-task
  matrix confirmed the reference stack stops at transcript/answer level. Decision: new
  Stage-1 research object ("knowledge control plane under the agentic speech task system",
  audio2tool-class end-to-end success metrics) vs amending this study's boundary.
  Recommendation: new object — this study is near its qualified-candidate endpoint.
- T3 ProfASR-Bench counter-claim positioning [Opus writing task]: explicit treatment in the
  candidate narrative (their TTS audio + no held-out split vs our real-speech p=.027).

## Part I — operations infrastructure

- I1 Long campaigns (>2h) default to DETACHED Windows launch (Start-Process route,
  night_block_launch_only.sh pattern) — the harness background wrapper is a measured
  single-point-of-failure (one external kill + the lexicon agent's replicated wrapper
  deaths).
- I2 Preflight script [Sonnet]: clock-lock re-apply reminder, clean tree, no live launcher,
  no __pycache__ under frozen scoring, no watched-pattern strings in payloads.
- I3 Ops facts archived: manifests write twice (scores null then rewritten ~2min later);
  wrapper logs are 0 bytes until final summary — liveness = artifact growth + process list.

## Sequence — SUPERSEDED by the adversarial-review amendment below

~~D5 lands -> D3+D4 registration -> GPU campaign resumes.~~

## AMENDMENT (2026-08-15, adversarial review wf_c21a2756: SOUND-WITH-AMENDMENTS,
## 20 findings -> 5 surviving incl. 3 critical; full synthesis in the workflow output)

Status updates: R1 DONE (umbrella 6a42d1d, 92 papers, ledger 1642 rows); R4 DONE (umbrella
be337c5, 6 assets); D5 DONE (872c114); D2 DONE incl. the review's per-arm provenance schema
(2026-08-15-legality-doctrine.md); lever-(iv) hijack fix ALREADY LANDED at e6ac359 — D6
discharge = citing it (or omitting exemplar_bank from the arm's D2 field set) in every
splice-delivery registration.

- PHASE 0 (now): D2 doctrine+schema [done]; D6 discharge citation rule [active]; I2 gains
  the assertion: no splice-delivery arm threads a non-empty exemplar_bank into pass-1.
- PHASE 1 (<=16-request probes): D7 (NEW, gates D4) — end-to-end delivery probe through
  production obs-replay-loop with the D5 flag source; pass criteria on TRACE COUNTERS only:
  acceptance>0 with the reference verifiably in the delivered payload; delivered-reference-
  on-true-error fraction >= 0.15. Below floor -> re-tune band/K before any campaign. D4
  prompt free-axis probes (draft slot / provenance wording / top-1-vs-k / R0-bias framing
  wording) registered as shape screens with a no-directional-inference clause. Optional
  fast-3 smoke: mechanical go/no-go only, no-WER-inference clause.
- PHASE 2 (GPU night block, frozen ten n=10, ~7-9h, detached launch): the D4 ceiling block
  vs N10 anchors — arms R0-bias (span-scoped static bias, byte-identical reference, no
  verify framing), R1 (reference + verify-with-abstention), R2-ceiling (+ gold-aligned own
  errored draft), wrong-reference controls under BOTH framings. Co-primary paired Wilcoxon
  on macro AND entity ledgers; HER + recoverable-information ratio + wrong-reference copy
  counts; format-normalized secondary. PRE-REGISTERED BRANCH RULES: operator AFFIRMED iff
  (R2-R1>0) or (R1 beats R0-bias at matched entity gain with lower HER) or (copy rate
  materially lower under verify framing); taxonomy COLLAPSE iff R1~R0-bias on both ledgers
  and HER and R2~R1 — then the scope amendments are re-amended and the candidate keeps the
  targeting/small-N wording with no "different operator" language. Fast-3 B/C anchors are
  permanently disallowed for aggregate reads.
- PHASE 3 (D3 ConEC, after registered NON-GOLD casing source): oracle-flag-routing recall
  gate FIRST (if oracle routing converts but S1 forfeits most of it, invest in the flag,
  not the KB); construction ladder raw-lowercase/casing-recovered/oracle-cased; consumption
  ceiling = the Phase 2 block; then the legal-tier full chain vs zero/metadata anchors with
  per-layer recovered fractions. Casing sources (legal): metadata fields, pinned issuer
  documents, or the core's own truecasing; gold/oracle recasing is a gold derivative.
- PHASE 4 (independent, GPU gaps): T1-SLURP first (owner-go recorded; full n + read
  pre-registration, not the one-liner); SlideASR after receipt verification; SLUE-SQA-5
  deleted-pairs arm HELD pending a restoration-feasibility re-check; Audio2Tool probe:
  roster factor WITHIN-ITEM paired per query, query-level clustering (2.16
  renditions/query pseudo-replication guard), {clean,noisy} axis dropped until a noise
  source exists, NC-license + probe-scoped-claim firewall carried into the registration.
  T3 rebuttal re-anchored honestly: p=.027 is the ORACLE rung; the legal rung (12.09,
  n.s.) is currently CONSISTENT with ProfASR — the rebuttal is real speech + held-out
  discipline + the coverage decomposition, not the p-value.

MUST-NOT-FLY (explicit blocks): any R-ladder GPU arm until D6-cited + D7-passed + amended
registration committed; any splice-delivery arm without D6 citation; R2-legal / D3 full
chain until D7 + legal casing source, and no scaling past n=10 until the oracle-routing
gate shows S1 retains a usable fraction; SLUE-SQA-5 restoration until feasibility
re-check; Audio2Tool noisy cells until a noise path is registered.
