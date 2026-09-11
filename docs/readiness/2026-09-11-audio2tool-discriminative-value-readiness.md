# Audio2Tool discriminative semantic VALUE readiness

Source checkout: /home/chao/saea-worktrees/experiment-closeout-integration, root integration base commit dc651732354676caa89a1179a4fd4c60ba4377ce. This is a model-free readiness audit. It does not register or rerun a flight.

## Closest closed comparison

The closest reusable closed card comparison is the 104-row semantic AgentLoop flight. It is below the current n >= 400 effectiveness requirement and is historical mechanism evidence only:

- Config: configs/experiment/a2t-semantic-agentloop-104-v1.json.
- Baseline: configs/baseline/a2t-semantic-agentloop-top16.json.
- Roster: A2T-AGENTLOOP-FRESH-FLIGHT, 104 rows, 13 per tier, receipt SHA 457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e, split identity 84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0.
- Card ground: g5-exhaustive-family-contracts-plus-43-qualified-compatibility-rules, with the semantic retrieval card route and a shared OpenJiuwen executor.
- Verdict: docs/readiness/2026-09-03-a2t-semantic-agentloop-104-v1-verdict.md.

The OBS query used the frozen core to emit an English transcript and a tool-name-free desired-action query; this was model-generated state, not a reference transcript.

The closed repository-diagnostic arm results were Direct M0 exact/tool/slot 0.2404/0.5096/0.3333; transcript top-16 0.2596/0.5962/0.3470; same-core query 0.2308/0.5769/0.3185; RRF fused 0.2404/0.5769/0.3495; same-tier shuffled fused 0.0385/0.0865/0.1206. The transcript-card route gained 1.9 exact points and 8.7 tool-accuracy points over M0, with exact wins/losses/ties 10/8/86 and tool wins/losses/ties 18/9/77. The matched-versus-shuffled contrast was +20.2 exact points and +49.0 tool-accuracy points with paired 90 percent intervals [12.5, 27.9] and [40.4, 57.7]. This is closed evidence that sample-specific semantic selection has value, not evidence that the current card content is sufficient or that a scale flight is authorized.

The G4 executable semantic-card fragment is a separate, more discriminative candidate but not a closed full-roster result. Its config is configs/experiment/a2t-g4-executable-microground-screen-16-v1.json. It binds builder SHA e49c5b71348efbfdcb284d17b847efb341a3a5898324ef2432ebe9e880da080e, corpus SHA 85a04fc72c49802853d0da3785f30a266a90d88275901c8292231442ef4a294f, build receipt SHA f2da2a1b77a59ff7f5d9e74c2fabe1e04c87d560f4ca066c573f3d65803680fa, and module SHA f13692bdf658286a0a018176446462258e81d76543806a0f7d569ef2c419f2ae. It is a 16-row screen with a sealed unscored predecessor identity, so it cannot be cited as an effectiveness outcome.

## Reusable discriminative content

The G4 card artifact carries choose semantics, avoid and sibling contrast semantics, role guidance, legal argument-key sets, public types and constraints, and construction-supported value-form rules. Its deterministic microground router selects up to two candidates per active action plus a sibling or schema-compatible contrast, using only task-blind observation or validated state. The implementation excludes tier, sample ID, gold, reward, prior response, and future-turn features.

The same registry and shared controller can therefore support a proposed cards-only comparison by changing the source-bound card artifact while holding roster, speech packet, prompt envelope, controller, executor, and output contract fixed. Use the transcript-vector top-16 route as the comparator and one predeclared executable choose/avoid card artifact as treatment on a governed roster of at least 400 rows, balanced across all eight tiers. Do not reopen the 104-row or 16-row screens as a new effectiveness campaign. Reuse validation must bind construction sources and exclude evaluation-derived values.

Required source bindings for that candidate are an eligible frozen roster receipt, the exact semantic-card builder and corpus hashes, the same speech-packet promotion receipt already pinned by the baseline, the same model/runtime fragments, and a new composed-config and protocol hash. Any card artifact that uses construction observations must retain its construction roster, builder receipt, registry source, and decontamination identity. No evaluation query, gold value, or scorer output may enter the card builder.

## Tier-specific VALUE hypotheses

- Tier 1 direct: choose the operation with the closest meaning and retain its legal key set; test sibling confusion and exact match.
- Tier 2 parametric: expose public argument types, constraints, and observed value forms; test parameter F1 and non-default extra-key errors.
- Tier 3 multi-intent: preserve one call per spoken action; treat ordered-call behavior as a separately declared diagnostic because official scoring is first-call based.
- Tier 4 implicit: contrast setter, getter, and transition operations by end-state meaning; test tool accuracy and exact match.
- Tier 5 needle: use target-specific choose/avoid distinctions against distractor families; test selection reachability and tool accuracy.
- Tier 6 correction: encode supersession of an earlier value or action; test corrected-row exact match without retaining the superseded argument.
- Tier 7 multiturn: carry only relevant established facts into the final request; test final-turn tool and parameter accuracy.
- Tier 8 intent blending: decompose blended intent into legal calls and values; test parse rate, tool accuracy, and exact match.

These are proposed, untested rules. They must not be treated as memory or effectiveness claims.

## Readiness gaps

The repository has the shared controller, OpenJiuwen executor, semantic retrieval/card rendering, source-bound speech packets, and closed 104-row discriminative retrieval evidence. It does not yet have a registered new cards-only exposure, a full-roster source-bound validation of the G4 corpus, a fresh prompt-fit receipt for that composition, or a root admission receipt under the current owner authorization. The native Audio2Tool benchmark also has no side-effect tool-result loop; its native quality task remains speech-to-call output scoring. That boundary does not prevent a cards-only native quality comparison.

The first comparison should use the official a2t-toolcall-official scorer as the primary metric family: tool accuracy, exact match, and macro parameter precision, recall, and F1. Repository sequence and micro slot-F1 measures may remain labeled secondary diagnostics. Report tier-stratified paired saves, harms, ties, and confidence intervals. Cost can be recorded as a diagnostic under the quality-first owner steering and is not an admission penalty.

A conditional corrective-memory comparison is a later step. It requires sealed deployment-visible state, an explicit bounded decision, and a validated downstream reward. It must keep the stable card VALUE fixed and must not inject gold, evaluation text, or scorer-derived state into runtime.

## Native population coverage already available

The repository has a separate frozen 400-row official calibration and native official population flights with 500 rows per tier: Tier 1 (500), Tiers 2/5/8 (1500), and Tiers 3/4/6/7 (2000). Their 4000 total population rows cover all eight tiers. This does not make the historical 104-row card comparison a full-population effectiveness result. The official first-call scorer is pinned to release b9d5383ca30945fbafb965a04bea40117e1e8a82; repository ordered-call and slot-F1 metrics remain secondary diagnostics.
