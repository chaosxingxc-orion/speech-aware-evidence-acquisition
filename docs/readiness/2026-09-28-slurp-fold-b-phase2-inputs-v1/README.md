# TRAIN Fold B as the phase-2 read roster: model-free inputs

Prepared 2026-09-28 at study commit `83abd475` on branch `fable/foldb`, model-free. Answers open question O2 of
`docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md` (branch
`fable/svphase2`; coordinator ruling O2: Fold B is the read roster, artifacts first). Cites owner decision 180
(E1-E6 adopted; sub-floor reads go to the same-flight instrument) and 168 (Fold B used for the filler).
Nothing here registers a cell, reserves a contact or authorises a flight.

**Correction to O2.** O2 states that no held-out TRAIN roster has an agreement table and speech query vectors.
Fold B already had both on 2026-09-27: the filler family's model-free preparation
(`SAEA-SLURP-STAGE3-FILLER-FOLD-B-PREPARE-V1`) built `prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1`,
and the Fold B speech vectors were sealed on 2026-09-12 by `SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1`.
No encoder pass is needed.

## Roster identity

| item | value |
| --- | --- |
| roster | `docs/receipts/rosters/slurp-evo-fold-b-v2.json` (`SLURP-EVO-FOLD-B-V2`, file sha256 `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8`) |
| rows | 1,080 ids, 1,080 distinct utterances, 60 per gold scenario, 3,154.797375 s |
| split identity | `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`, split role `discovery` |
| same ids as | `docs/receipts/rosters/slurp-stage3-filler-fold-b-v1.json` (file sha256 `ddbdf5f499b406965ee47688b1fa3e50b67b0aeba9e39eac1c74ed4517b15e15`), set-equal, same split identity |

## Vector coverage (measured over the roster's 1,080 ids)

| file (under `SPEECHRL_DATA_DIR`) | sha256 | rows covered | notes |
| --- | --- | --- | --- |
| `prepared/SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1/queries.jsonl` | `9f095cee1ee9a138092d4549d9afa648a2dc158e33c24b858859c62d5a5a9a89` | 1,080 / 1,080 | the sealed encoder output (ledger row of the same id; encode receipt `preparation-runs/.../encode-v1/receipt.json` sha256 `583d37669b3a8275be6a244454e21ebd7b5fbe1fd90af2b73f251d86bf7d00eb`) |
| `vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl` | `83c5da6190fb2a65edf98a8f9ef35ff2cb310eb4e4b94eba9e04f9eedce9f299` | 1,080 / 1,080 | boundary-channel query: one full-utterance segment per row, `intent-boundary` width 2,048; model-free alias receipt `prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-B-ALIAS-V1/query-dimension-alias.json` sha256 `78de8aa2d30afab442d286b1a14919e1dfc031f79b007f62b3eebd747a9d0ea0` |
| `vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.jsonl` | `573a8a37a63d790d6b849c11676b9463de28c92eeb92ab3e99177181a947c67f` | 1,080 / 1,080 | exemplar-channel (`content`) query, width 2,048; provenance sha256 `6a6d0d0ff8312abb6ccd2de8e1ecce9355e8bd0b5d0f1abc5c7ce89b47f4802c` |
| `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` | `16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532` | row-independent | the 60 boundary keys (59 centroids + 1 written fallback), as KPROBE pins them |

Every row has a speech vector and a boundary-query vector; no row is missing and no file carries an extra id.
Known recall property, not a vector gap: the W2 offline replay (`docs/results/2026-09-27-slurp-w2-agree-guard-offline.md`)
recalled no written-key boundary candidate on 2 of 1,080 Fold B rows (DEV-2000-ADDED: 1 of 1,000).

## The agreement table

`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl`, sha256
`06990a86d20469c668ac4231990b49e5926d4771c9af8fbb13ae634b3ec21911`; receipt `.../receipt.json` sha256
`90e127de43fb2d7db54de969363ce380b2804ea8d678582e144cd41b726e4844`. Built by
`scripts/build_slurp_intent_exemplar_agreement.py` (builder sha256 `61808ae88f5db02c205480ea5375459dbe5810a761504249d989241b751e53f3`, the DEV and Fold A
builder), 4 workers, the DEV parameters: vote store `train-exemplars` (snapshot `4c498dc0...`), vote phase `solver`
(k 20, fuse 20/20/20, pure cosine, tau 0.0), target store `intent-boundaries` (snapshot `5520b844...`, 60 facets),
template `intent-boundary:{key}`. Source cell: the committed, never-flown FILLER BASE
`slurp-native-stage3-filler-fold-b-base-v1` (the only Fold B cell that declares no `agreement_source`).
Implementation digests equal the DEV table's (`kb_policy` `b0d8d9d4...`, `phase_supply` `5cf42534...`).

Measured: 1,080 rows, every row 20 votes, **0 self-excluded exemplars** (0 rows with one), **0 rows without a
vote**, 0 pool values without a build-time target, 60 facets ever voted for. The bytes are **identical** to
`SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/agreement.jsonl` (built at `bf483458` under the
pre-decision-176 `kb_policy` digest), so the re-pin of decision 176 did not move the vote. Either id pins the same
sha256; a phase-2 cell should pin this one. Ledger row `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1`
(model-free-check, DRAFT).

## Disjointness (measured by utterance identity, the first three id fields)

| against | shared with Fold B |
| --- | --- |
| Fold A `SLURP-EVO-FOLD-A-V2` (1,080; split `61b0f062...`) | 0 ids, 0 utterances |
| vote / exemplar pool `size-pool-annotated-exemplars` (9,354 TRAIN utterances) | 0 |
| centroid construction pool `size-pool-annotated-exemplars-minus-r01` (8,554) | 0 |
| `intent-boundaries-v1` source ids (474) | 0 |
| `slot-contracts-v2` source ids (803) | 0 |
| every SLURP evaluation roster, devel and test | 0 (roster receipt `disjointness_proof`; filler family README) |

Not checked here: a contrast-pair pool, because `top2-contrast-v1` has no released store yet; its registration must
prove the same disjointness.

## Construction status of Fold B

What the receipts show:

- **Contacts so far.** `SAEA-SLURP-EVO-FOLD-PACKETS-V2` (packets), `SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2`,
  `SAEA-SLURP-EVO-S1-FOLD-B-V2` (8,640 contacts, 2026-09-06; the EVO-S1 confirmation fold, round REJECTED, nothing
  adopted) and the encoder pass `SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1`. Model-free reads:
  `SAEA-SLURP-STAGE3-W2-AGREE-GUARD-OFFLINE-V1` tuned a position-1 guard on the agreement term against Fold B gold
  offline (STOP; nothing registered).
- **Filler (decision 168).** Six chunks and the smoke are registered, all rows `consumed: no`; no run directory
  exists. When flown they are sealed five-sample ROLLOUT pools of the current system, descriptive
  (`claims_benefit: false`); none of them is a knowledge source or a tuning input of a phase-2 cell.

Assessment: using Fold B as the phase-2 READ roster does not conflict with the filler as registered, because a
rollout is not construction of the phase-2 branch values (those are tuned on Fold A). It becomes a conflict the
moment anything read in a phase-2 cell was built from Fold B rollouts -- a sealed-credit TF-RL update, a store,
a card, a threshold. Two caveats for the coordinator: (1) W2 already looked at the agreement term against Fold B
gold (a delivery-model curve, not a measured accuracy), which touches P-SV-1's optional branch C; (2) decision
168's words "construction-exposed" should be ruled to mean "rollout-exposed only" for as long as Fold B is a read
roster.
