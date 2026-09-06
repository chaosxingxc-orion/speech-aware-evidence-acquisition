# EVO-A1 round 1 — the PROPOSE step, landed model-free

Zero contacts, no GPU. Exposure row `SAEA-SN-MF-A2T-EVO-PROPOSER-R01-PLAN-V1`. Driver
`scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1`.
Authority:
`docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md` sections 5, 11
and 12.

No `MANIFEST.sha256` here yet: this directory is filled step by step across the round, and a
manifest written now would be stale the moment the proposer outputs land. The per-file digests
below are the pin until the round closes.

## What landed

| file | what it is | sha256 |
|---|---|---|
| `plan-only.json` | `--plan-only`, which writes nothing: the resumable step list, `next_step = propose` | `531cfda93139d33137de3ea683c743cca67d9ce63aef9fcf77e802dfbdeb447a` |
| `propose.json` | the round-1 PLAN receipt: 20 draws, their anchors, their exemplar ids and each contact's pinned `prompt_sha256` | `cf1b5e1766753fcf2b91c016c57f6c723f63e128afae05df2dff54215a50206a` |
| `docs/receipts/rosters/a2t-evo-a1-proposer-r01.json` | the round's own `roster_role = construction` roster, whose ITEMS ARE THE DRAWS | `ae6a1613e924c67eb84dea4516fc65b13baf40702f38cf86fc5c74d719919ba8` |
| `configs/experiment/a2t-evo-a1-proposer-r01.json` | the round's `bounded-discovery-probe` fragment, 20 cells | `6b5fa279b87904aa1586960fb8682f4a9f5a115d62766e2e67c452c82c8f63d2` |
| `docs/receipts/artifacts/d1-a2t-evo-proposer-r01.json` | the 20 anchors' additive D1 media supplement | `b6782823ca062bddac3bae543a29065fc7c5d7531d58083873c01014d9ca7f8a` |

**A correction to the tasking, recorded because it changes what a receipt means.** `--plan-only`
writes nothing — it reports which step is next and why the others are not. The artifact that carries
the round's draws, anchors and prompt digests is the PROPOSE step's own `propose.json`, produced by
running the driver *without* `--plan-only`. Both are model-free; only the second lands a receipt.

## The draws

20 contacts: five targets x three proposer slots, plus the round-1 placebo on each target
(`K_1 = 5`; the placebo is an extra slot, never a replaced proposer draw). Roster identity
`a513b0b536cbc9b27a9c13d2f3908cda9cdaebec21fca2028fc28286af1f59d8` — the value the round's plan is
bound to, and the value `configs/experiment/a2t-evo-a1-proposer-r01.json` declares.

| fact | value |
|---|---|
| draws | 20 (15 proposer, 5 placebo), 4 per target |
| distinct anchors | 20, one per draw, each from that draw's own ordered exemplars |
| anchor tiers | tier2 9, tier1 3, tier5 2, tier6 2, tier8 2, tier3 1, tier7 1 |
| anchors' audio | 84.114333 s, measured from the wav headers |
| distinct `prompt_sha256` | **20 of 20** — no two draws render the same prompt |
| prompt size | 1,633 / 6,057 / 13,013 characters (min / median / max) |
| exemplars rendered | 489 over the 15 proposer draws, 16 to 52 per draw (`M = 8` per tool, 2 to 8 tools per target) |
| placebo draws | 0 exemplars rendered, 1 construction target declared — the over-declaration of exactly one row the preregistration records as the conservative direction |

`ledger_budget` was checked against the parsed exposure rows before the fragment was emitted:
planned 80 calls and 336.457 speech seconds against the registered ceilings of 80 and 400,
`within: true`. The fragment's own `ExecutionPlan` is 20 calls / 85 s / 0.01 GPU-h for this round.

## Nothing was leaked, and it was checked rather than asserted

A proposer prompt carries construction query text and gold calls; `ProposerContact.as_json` records
identity, counts and digests only. Verified over all 231 rows the roster names (20 anchors plus 489
rendered exemplar slots over 211 distinct ids): **no query text and no parenthesised call string
appears in `propose.json`, the roster receipt or the experiment fragment**.

One measurement artefact of that check is worth recording: 36 of those 231 rows carry a DEGENERATE
released `expected_tool_call` that is the bare tool name with no argument list at all, so a naive
substring test flags them against the tool names a receipt legally records. Those 36 exemplars are
still shown to the proposer as their release states them; they simply carry no argument evidence.

## Three defects this step surfaced, all fixed at the base rather than worked around

**1. A namespaced gold call blocked the whole round.** `build_proposer_material` demanded byte
equality between an exemplar's gold-call head and its `tool_name`. The release occasionally
namespaces the call string — `smart_home.setApplianceMode(...)` against a bare `setApplianceMode` —
in 1 of the 274 rows of `A2T-EVO-EXEMPLARS-V2` and 3 of fold A's 424, and the step refused outright
on `tier5_needle:001403`. The manifest's `tool_name` is the authority the official scorer itself
compares a prediction against (`reproduction.a2t_scorer` scores
`compute_tool_accuracy(predicted, gold.tool_name)`), so the namespace is cosmetic. Both guards —
`rails.evolution.build_proposer_material` and `rails.proposer._tool_of_gold_call` — now compare the
LAST dotted segment. **The call string is still rendered verbatim; only the grouping key is
normalized**, and a genuine disagreement is still refused: the released
`tier3_multi_intent:002505` pairs `updateFirmware` with a `setTargetTemperature` call and is a fold-A
row, not an exemplar. Covered by
`tests/unit/test_flight_construction_proposer.py::test_the_material_accepts_a_namespaced_gold_call_whose_bare_name_agrees`.

**2. The proposer roster recorded media facts no D1 supplement could ever match.**
`load_carrier_material` resolved the anchors through `data.audio2tool.load_media_rows`, which
returns the manifest's three-decimal `duration` cell as `audio_seconds` and binds a tier-7 row to its
LAST chat turn. A D1 media supplement is built from wav HEADERS and refuses a disagreement above
1e-6, so the supplement the preregistration's section 12 item 5 requires could not be built at all
(`audio duration drift for tier1_direct:001179`), and the anchors could never have passed
`gate.verify_media_identity` at model-touch time. The A2T branch now uses
`analysis.a2t_evo_capacity.measured_media_facts` — the same function and the same tier-7 rule (the
FIRST user turn, which is what the official protocol serves) the two folds' flight-roster receipts
and supplements were built from — so every EVO-A1 media artifact agrees by construction. The anchors'
summed duration moved from the manifest's 83.396 s to the headers' 84.114333 s.

**3. The one D1 supplement builder could not read a `saea-roster-receipt-v1`.**
`scripts/build_a2t_semantic_agentloop_d1_supplement.py` accepted only the flight-roster shape. A
proposer roster has no flight-roster view — it is not a speech population — but its items already
carry the four media facts. The reader now accepts either shape, which keeps ONE supplement builder
for every roster in the study; nothing below the identity check differs, and a roster whose items
lack a media fact is still refused row by row.

## The I-4 gate was RUN, offline, not asserted

`contracts.gate_media_identity.verify_media_identity` for carrier `audio2tool` through a real
`FrozenCoreGate.for_study_repo` binding (the committed E0 closure receipt, the pinned
`receipts/runtime-q4km-featcache-04ccc72a.json`, this study's exposure ledger and the umbrella lock),
with `d1-a2t-evo-proposer-r01.json` configured by path and SHA-256 and all 20 anchors offered at
once: **PASS on all 20 in 0.3 s**. A NEGATIVE CONTROL — an unlisted sample id `tier1_direct:999999`
bound to a real media path — was refused with `GateClosed`, so the pass is not vacuous.

## What is still blocked, and on what

The `candidates` step waits on `proposer-outputs.jsonl`, which is a FLIGHT product: the 20 proposer
cells of `configs/experiment/a2t-evo-a1-proposer-r01.json` must actually fly under
`SAEA-A2T-EVO-A1-PROPOSER-V1`. The driver never contacts the model, and a step whose input is
missing BLOCKS rather than guesses. Before that flight the preregistration's section 12 items 9 and
10 still stand: the prompt fit under its own `bounded-discovery-probe` row (the serving tokenizer is
the only authority that may price a candidate) and a contact-free wire check on a clean committed
tree.
