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

## Sequence

NOW (parallel): R1, R4 (both in flight) + D5 dispatch.
D5 lands -> D3+D4 registration -> GPU campaign resumes (reflection ladder + ConEC full chain).
R4 lands -> T1 registrations (SLURP needs the owner's one-line boundary confirmation).
Extended survey lands -> T2 decision session with the owner.
I1/I2 take effect from the next campaign.
