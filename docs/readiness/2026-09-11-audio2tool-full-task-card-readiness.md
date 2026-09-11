# Audio2Tool all-eight-tier G4 semantic-card readiness (model-free)

## Scope

This is a preparation handoff for a possible future Audio2Tool semantic-card arm. It does not register an exposure, authorize a contact, rebuild data, or reopen a closed G4 flight.

## Established population and source pins

The established official population is three carrier-specific discovery fragments, totaling 4,000 samples across all eight tiers:

| Population | Samples | dataset fragment SHA-256 | carrier FlightRuntime split identity |
|---|---:|---|---|
| A2T-TIER1-OFFICIAL-POP-500 | 500 | becc9f383e9fab4f3638fc783032fd2a50ef1311248523ddc2c1abd4828c7c7b | 4d22744c503882d4274bca4bd5bc3c77abde4711831c976b83c3354586eee54f |
| A2T-TIER258-OFFICIAL-POP-1500 | 1,500 | f88bc85c5383a81038ff358a178c748748e8d0279c1913a5293f0dfac1a12d7b | adb1cee2081192760a37bf9f2447f7bc5da7135bf3a397ddad3828a79f578882 |
| A2T-TIER3467-OFFICIAL-POP-2000 | 2,000 | 3b5c9bcacbd37ea6d6fe808b0236e518ba73e938935ced6ec739fdd3ada25476 | bdd28d4231a678db2cafe3da8d006cd6a042f6d325d64079deb32a6b9c74b317 |

Source fragments are `configs/dataset/audio2tool-tier1-official-population-500.json`, `configs/dataset/audio2tool-tier258-official-population-1500.json`, and `configs/dataset/audio2tool-tier3467-official-population-2000.json`. Their existing baseline experiment fragments are `configs/experiment/a2t-tier1-official-population-v1.json` (SHA-256 84dbc6615f79e5ac1c9f5278b53b4fb736604f94a9f0b070fff2ebf594345cca), `a2t-tier258-official-population-v1.json` (3f7c49d5d22e89dab0d60ebb1f09928d82bd15ddf9cd8cb02ee7953e510e9eb9), and `a2t-tier3467-official-population-v1.json` (9c86fc579aaefc89b75b5d6dccfb653a11256f964bff566506300d16399fdb22).

Each fragment pins an official roster receipt and D1 supplement. The FlightRuntime identity is the carrier-prefixed identity in the fragment, rather than its separate key-receipt identity.

## Existing G4 semantic-card assets

The registered reusable card source is `knowledge/audio2tool/g4-executable-semantic-cards-v1/corpus.txt` (SHA-256 85a04fc72c49802853d0da3785f30a266a90d88275901c8292231442ef4a294f). Its construction receipt is `docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-g4-semantic-cards-build-v1/build-receipt.json` (SHA-256 f2da2a1b77a59ff7f5d9e74c2fabe1e04c87d560f4ca066c573f3d65803680fa). That receipt records construction identity 86bfc6f36fb6a562ad1134cd11d60a2ad6bb94668195d76eada97edd2ce0ce16, registry SHA-256 7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4, 22,951 construction samples, 12,601 units, and a historical 400-sample proposed evaluation decontamination check.

The renderer/router is already shared and registered:
- `rails/a2t_executable_semantic_cards.py`
- `rails/a2t_semantic_microground.py`
- registered tool `saea-tool-a2t-executable-semantic-cards-v1` in `rails/tools.py`
- representation `a2t-g4-executable-semantic-cards-v1`
- matcher `a2t-g4-structured-action-bm25-k2-8-v1`.

It selects structured choose/avoid, role, tool, and category facets with a sibling contrast and task cards. The historical screen configuration that pins these assets is `configs/experiment/a2t-g4-executable-microground-screen-16-v1.json`.

## Readiness and blockers

The all-tier baseline population is raw-audio bf16-projector geometry. No all-4,000 packet-promotion receipt was found. The old 104-row semantic AgentLoop promotion is not reusable as all-tier packet evidence. A future raw-audio arm therefore does not require packet promotion; a packet arm needs a newly source-bound promotion.

The historic G4 policy is deliberately fixed to a 16-row screen in `rails/probes/a2t_g4_microground_flight.py` and cannot truthfully be relabeled as the all-tier route. A replay comparison can consume source-bound per-sample routed cards, but a complete live agent must generate its own current observation before routing. The minimum shared seam is the current phase output -> existing organizer/router -> second-phase evidence binding inside FlightRuntime/OpenJiuwen, with exact sample, source, state and route hashes. Reuse the current Audio2Tool adapter and phase/tool abstractions; do not add a private executor or parallel evidence-supply framework.

Before a future admission, rebuild or explicitly revalidate card construction/decontamination against the selected all-tier roster and current exposed union; the historical 400-row decontamination receipt is not a current 4,000-row proof. Bind a new ExecutionPlan, exposure row, source/corpus/registry identities, prompt-fit receipt, and serving geometry. These are uncompleted prerequisites, not evidence of an approved successor.

## Packet and operational status

No service, tokenizer, encoder, scorer, model, data rebuild, or quality result was accessed for this handoff. This plan relies only on repository configuration and scalar receipt metadata.

## Root-reviewed query qualification: G4 routed-card query inputs

The existing G4 route has two input forms. route_semantic_microground accepts either a task-blind English observation or a validated structured state; it refuses both or neither. For a structured state it ranks each active_actions action phrase, target phrase, role, surface, and normalized value. If there are no active actions, it queries only current_request.normalized, falling back to current_request.surface (rails/a2t_semantic_microground.py, _action_queries and route_semantic_microground).

Both forms are guarded against gold, reference transcript, sample identity, tier, reward, prior outcome, and test fields. The state renderer also requires the current request and active actions to originate in chronological user turns (rails/a2t_structured_dialogue_state.py, _validate_document). Thus the legal evidence is a current, source-bound English OBS or a deterministic state derived from it, plus the frozen card corpus. It is not an offline reference query.

Historical G4 did not generate that state live: its E arm reused sealed G3 task-blind observations, and SE called organize_sealed_observation on those sealed observations before routing (docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-g4-executable-microground-se16/launcher/launch_a2t_g4_se16.py, _organize_selected and _route_selected). Its adapter is therefore a historical sealed-predecessor/replay path, not a complete live agent.

For a future fixed direct Audio2Tool comparison, a query-dependent routed card cannot be produced before its sole answer contact: the raw speech has no text query at the router boundary. It would need a query-independent card packet or a different, explicitly defined current observable.

For a complete live agent, the lawful route is an initial frozen-core OBS or selection/state phase over the original speech, followed by a sealed stage barrier that binds its actual English output to the same sample and then invokes the existing organizer/router for the second answer phase. Existing a2t-phase-select-then-fill-v1 demonstrates a current two-phase FlightRuntime/OpenJiuwen barrier, but it does not presently bind its first-phase output through the G4 observation-state organizer and semantic-card router. That current-output-to-organizer-to-route binding, including state/route hashes and second-phase cost/prompt fit, is the concrete missing shared seam.

No reference, gold, or historical sealed predecessor should be substituted for that live first phase in a complete-system claim. The historic sealed G3 artifact remains usable only for an explicitly declared fixed-predecessor/replay comparison.

## Review and provenance

Root corrected the preliminary single-contact wording after checking the historical query provenance. Existing population fragments do not authorize a new G4 arm. Sources: DATA coordination/audio2tool-g4-all8tier-readiness-v1.md, SHA256 a4cf0a6bdb7c4d5bf56891e4301a4558b31a53869d0b2b32b50b8519f83f51c5; successor query qualification SHA256 7c45ba3926d8b8f93a61c4c0cbed1f4d4c16b5dd2cfa57b631ca6b6ffeb4a99a.
