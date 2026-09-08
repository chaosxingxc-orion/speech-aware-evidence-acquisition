# KV knowledge-view preparation — receipt (2026-09-08)

Row `SAEA-SLURP-MF-KV-VIEWS-PREP-V1`, profile `model-free-check`.
Producer: `scripts/slurp_kv_views_prep.py`. Preregistration:
`docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md`.

**Zero frozen-core, tokeniser, embedder, retriever, judge, network, GPU, audio-decode and
paid-API contacts.** `CUDA_VISIBLE_DEVICES` empty throughout. Reads TRAIN only, plus the frozen
TRAIN knowledge snapshot the KC-S1b fragment already binds and the committed probe template. **No
devel or test record is loaded, hashed or scored, and no gold annotation is opened** — unlike MF-9
and MF-10 this pass runs no scorer at all.

**Every token figure is a STATED PROXY** — whitespace tokens × 1.3, rounded up
(`analysis.slurp_slot_vocabulary.token_proxy`). No tokeniser was called. A cell that flies a view
measures its own envelope through the serving `/apply-template` + `/tokenize` seam, as KC-S1b did.

## MF-10 identity anchors, re-derived rather than quoted

The family is built on MF-10's measurement, so MF-10's own card figures are re-derived here from
the same TRAIN bytes through the same library. All six reproduce exactly; the pass raises rather
than reports if one stops reproducing.

| anchor | published | reproduced |
|---|---|---|
| CLOSED types | 18 | **18** |
| card surface forms | 842 | **842** |
| per-intent card cost, median proxy tokens | 1,432 | **1,432** |
| worst intent's card cost | 2,010 (`social_query`) | **2,010 (`social_query`)** |
| intents whose card twin rotates in place at zero delta | 39 | **39** |
| intents that cannot rotate in place | 14 | **14** |
| the bound snapshot's protected payloads (KC-S1b's own fragment note) | 11,863 | **11,863** |

The bound snapshot is loaded through `rails.knowledge.KnowledgeSnapshot.from_frozen_json` and its
`content_hash()` re-checked against the `07f94807…9ffa65` the KC-S1b fragment pins — the identity a
fragment names is the content hash, not the file's sha256, and the pass refuses to continue if they
disagree. The payload tuple is then reduced by `rails.runner._protected_knowledge_material` itself,
so the fold this receipt reports is the fold the flight runs.

## What each view costs, per intent, on the proxy

The comparator column is the **admitted KC-S1b block**, measured through the same proxy so the
numbers are comparable. KV-0 is *cheaper* than the admitted block, because removing the five
example fillers per type is a subtraction.

| view | cell | block min / median / max | the view's own share, min / median / max | full-schema fallback block |
|---|---|---|---|---|
| KC-S1b (admitted, five examples per type) | — | 110 / 177 / 251 | — | 5,353 |
| `examples-free` | **KV-0** | **102 / 138 / 175** | 0 / 0 / 0 | 3,158 |
| `descriptions` | **KV-1** | 231 / 436 / 650 | 129 / 298 / 476 | 5,585 |
| `cards` | **KV-2** | 102 / 1,542 / 2,148 | 0 / **1,432** / **2,010** | 6,471 |
| `fewshot` | **KV-3** | 192 / 250 / 328 | 90 / 117 / 181 | 3,308 |

Seven of the sixty intents list no CLOSED type at all, so KV-2 sends them the KV-0 block alone;
that count is a reported covariate, not a defect. KC-S1b's own measured worst *envelope* was
10,006 real tokens in a 16,384-token slot at `-np 4`, so the worst KV-2 block fits with room to
spare — but the proxy is not that measurement and the flight makes it.

## The twins

| view | matched by | intents with a block | matching to the character | cannot rotate in place | max abs char delta (all / rotating only) |
|---|---|---|---|---|---|
| `descriptions` | construction (per-intent rotation) | 60 | **55** | 5 | 46 / **0** |
| `cards` | construction (MF-10's own derangement) | 53 | **39** | 14 | 4,891 / **0** |
| `fewshot` | measurement (a donor intent's sentences are other sentences) | 60 | 0 | — | 327 / 327 |

**Every intent that can rotate in place matches its twin to the character.** The intents that
cannot are the ones listing exactly one carded/described type: any twin of a single vocabulary is
a different vocabulary of a different size. They are pooled and rotated among themselves — MF-10's
and KU-S3's own resolution for singleton buckets — and the preregistration reads the twin contrast
twice for that reason: once on the whole roster and once on the rows whose predicted intent
rotates in place, a stratum fixed by construction before any flight.

KV-3's twin is the one matched by measurement rather than construction: mean absolute character
delta **95.1** on a block whose median is about 800 characters, max 327. The volume covariate is
reported beside every KV-3 number.

## Containment

| fold | what it asks | result |
|---|---|---|
| **C1** | does a view payload occur inside the arm's own DIRECTIVE? | **0** on all seven arms (1,240 payloads checked) |
| **C2** | does a protected payload of the BOUND TRAIN snapshot occur inside the instruction? — the fold `rails.runner._assert_agent_control_excludes_knowledge_payloads` applies at contact time | **0** on all seven arms, over all 61 renderable blocks each, and **0** on the admitted KC-S1b block through the identical fold |
| **C3** | do a view's own payloads occur inside the instruction that carries them? | **100 % by construction** for KV-1/2/3, and reported rather than hidden: these views ARE the instruction-side block. **0** is the number KU-S3 (KV-4) must keep, because its values are traced supply |

C2's other half — the bound snapshot against the 1,000 **sealed** closed-list states — is cited
from KC-S1b's own committed number (78 facet-representation hits, 0 value hits, on a snapshot
whose content dimension no KV cell binds) and is **not** recomputed: this row opens no sealed DEV
output.

## KV-3's material

| quantity | value |
|---|---|
| k, seed | 3, 20260903 |
| TRAIN utterances per intent, min / median / max | 4 / 130 / 810 |
| intents with fewer than k | **0** |
| share of an intent's listed types the k = 3 cover reaches, mean | **0.9648** (arm) vs **0.6477** (twin) |
| intents whose listed types are fully covered | **51 of 60** (arm) vs **19 of 60** (twin) |
| donor intents crossing a scenario | 2 of 60 (`news_query`, `weather_query` — the two single-intent scenarios) |
| donor equal to the intent itself | **never** |

The arm/twin gap in type coverage is the KV-3 factor stated as a construction number: the twin
supplies the same k worked examples in the same shape, from the same scenario, carrying the wrong
slot structure.

## Files

* `views.json` — the whole measurement, including one worked `alarm_set` example per view, arm and
  twin, and the admitted KC-S1b block beside them.
* `MANIFEST.sha256` — sha256 over every other file here.

The pass also writes `docs/receipts/knowledge/slurp-kv-slot-type-classes-v1.json`, the hash-pinned
CLOSED/MIXED/OPEN table `rails.phase_material._kv_class_table` loads. Its content is MF-10's,
copied after MF-10's own receipt is re-hashed against its `MANIFEST.sha256`; nothing about the
classification is recomputed here.
