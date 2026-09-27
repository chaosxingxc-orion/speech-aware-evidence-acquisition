# Cell KPROBE: the centroid key's conversion from delivery to correctness

Registered before contact 2026-09-27 at study commit `08fd493c` (owner decision 145);
the cell is **held**. Nothing here authorises a flight, a flip or an admission entry.

**The finding this probe follows.** [`docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md`](../../results/2026-09-27-slurp-boundary-key-construction-diagnostic.md) found the
boundary channel's written one-line descriptions to be its weak link: a key built as the intent's mean
construction-TRAIN utterance vector -- the same 2048-d space as the flown keys, zero encoder contacts --
puts the gold intent inside the delivered eight on **71.2 / 64.7 / 66.8 %** of the intent-wrong rows
(Fold A / ROLL-1 / DEV-2000, held-out pools) against **45.0 / 44.6 / 35.8 %** for the written key, at zero
token cost, because the delivered body is unchanged. That is DELIVERY. Whether the Solver then answers
correctly with the entry in front of it is the missing quantity, and this cell measures it exactly as
cell CONV measured the agreement term's ([`docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1`](../2026-09-26-slurp-stage3-conv-fold-a-70-v1/README.md), read
[`docs/results/2026-09-27-slurp-conv-probe-read.md`](../../results/2026-09-27-slurp-conv-probe-read.md): m = 32 of 70).

**The treatment key file.** `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` (sha256 `16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532`, 60 rows), cut by
`scripts/build_slurp_intent_boundary_centroid_keys.py` from the pinned pool key vectors (`vectors/slurp-kus3/facet-vectors.jsonl`) and the
R01-excluded pool snapshot (`size-pool-annotated-exemplars-minus-r01`, 8,554 utterances), so that ONE file is
held out on Fold A, ROLL-1 and DEV-2000 alike. The arithmetic is the diagnostic's own (`unit_rows`, imported
byte-unchanged): unit-normalise each member, mean, unit-normalise; the label is each pool value's frozen
build-time `task_target`, a store property. `intent-boundary:cooking_query` has no
utterance in that pool and keeps its written key byte for byte. A centroid has no text source, so the file
carries a new receipt kind, `saea-centroid-key-receipt-v1` / `centroid-over-pinned-utterance-vectors-v1` (sha256 `d5fa43dfb9cfe71402e256c015e5f0a1ce66e97b3ec5355a664eb9f69f8cdf0a`; repository copy
`centroid-keys-receipt-v1.json`), which pins per facet the construction, the member count, the member-id
digest and the vector digest. Only this cell's derived baseline pins the file; **the 211 committed configs
are not re-pinned** (decision 145).

**Three proofs before an id was taken** ([`roster-derivation-v1.json`](roster-derivation-v1.json), by
`scripts/analysis/slurp_boundary_centroid_conversion_roster.py`): (A) the diagnostic's own arithmetic, imported byte-unchanged, reproduces every
`written` / `centroid` cell of its committed note on all three rosters and the written-key recall equals every
sealed delivered set (0 differences); (B) the pinned FILE, read through `rails.phase_supply.load_sealed_vectors`
and run through `rails.kb_policy.multidim_segment_recall`, equals the diagnostic's R01-excluded centroid
(max abs diff 0.0e+00) and reproduces the note's
ROLL-1 centroid cells exactly (64.7 % wrong-row delivery); on Fold A the
file delivers gold on **136 of 191** intent-wrong rows
(71.2 %) against 86 (45.0 %) for the written key;
(C) the production constructor (`provider.candidates` + `provider.fuse` at the flown k 8 / 8-1-8) reproduces the
sealed delivered set on 1,080 / 1,080 rows under the written key and derives the same population under the
centroid pin as the recall does.

**The roster.** 55 ids, id-list sha256 `ad433b1fc3f21765af15d3aed4012264125d9f17fdd4cef837d67bcf50ddde02`, split identity
`d5fa899db921562b3e98a0c2aba72d8edab1c1885969f0332dce67a623527b31`: the intent-wrong Fold A rows whose gold entry the centroid key newly delivers --
54 of the bank's `INTENT-UNCOVERED` rows and
1 of its `INTENT-COVERED` rows, both intent-wrong in the sealed comparator. Net
delivery on the 191 intent-wrong rows is +50
= 55 newly delivered - 5 newly lost, the note's 191 x (0.712 - 0.450) = 50. **Selected using gold, offline** -- legitimate for a
*conditional* estimate on a TRAIN roster and for nothing else. **No pooled or roster-level claim may ever be
made from this cell.** It also cannot see harm: rows the comparator already gets right, and rows that LOSE
their gold entry under the centroid key (3 CORRECT, 3 ENTITY-MIXED, 5 INTENT-WRONG over all 1,080 rows), are
outside this roster and remain a construction cell's question.

**One pin, proven.** The derived baseline is `slurp-native-default-plan-lock-baseline-v1` with
`knowledge_stores.intent-boundaries.phase_supply.perception.facet_source` moved to the centroid file; the
composed-config diff against the locked PLAN cell (`registered-facts-v1.json`,
`composed_config_diff_against_the_locked_plan_cell`) is that pin plus bookkeeping only: this cell's own FIT
identities and cap, no committed `prepared_phase_supply`, the receipt appended to
`preparation_source_receipts`, and `what_this_is`. `k` 8, `fuse_coverage` 8-1-8, the rank weights, the store
snapshot and release, every other store, the model fragment, geometry, session, program, templates,
normaliser and scorers are byte-identical. `tests/unit/test_kprobe_config.py` re-proves it.

**Why intent, not SLU-F1.** The within-flight null (docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md) measured 0 intent flips out of 200 request-identical rows, so an intent flip is ATTRIBUTABLE rather than noise and a per-row intent read is legible at this size; cell CONV read the same quantity the same way at n = 70 (docs/results/2026-09-27-slurp-conv-probe-read.md). Pooled SLU-F1 is not legible here: its own measured noise would swamp the roster, and the official SLU-F1 is entity-only while this mechanism acts on the intent. The official scorer still produces the number -- the read takes its per-sample scenario_action_exact field and nothing else -- so the standard-scoring rule is intact.

**The deliverable.** `P(correct | newly delivered)` = m / 55 with a Wilson CI95 and the exact
Clopper-Pearson beside it; the reverse count (zero by construction, a limit not a result); the four-way
transition split (wrong to gold, gold to wrong, same wrong intent, different wrong intent) and the stay-wrong
split; and **the delivery gate**: the read refuses to produce a number unless the gold entry was delivered on
all 55 rows. Re-declaration rule, stated and not applied: a later 1,080-row construction cell declares
m x 0.092615 pp intent accuracy (owner decision 133; m x 0.041615 pp SLU-F1 for the guard),
clearing the 2.5 pp intent bar only if **m >= 27**.

**`stage3_measurement`.** 55 rows is under the instrument's `MIN_BENEFIT_ROWS`, so the design is
`form-proof`, `claims_benefit` **false**, `expected_effect_pp` **0.0**; the note states the conditional-rate
purpose and the re-declaration rule. **No `admission` mode is declared.**

**`stage3_algorithm`.** `none`: no rollout, no per-sample scoring, no credit assignment, no update
operator, no evolving store; a single key file is not a policy search.

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-kprobe-fold-a-55-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `roster-derivation-v1.json` | the 55 ids and the three proofs |
| `centroid-keys-receipt-v1.json` | the repository copy of the key file's receipt (new kind) |
| `registered-facts-v1.json` | every model-free fact, the one-pin diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the cell's two plans |
| `analysis-recipe-v1.json` | how the conditional rate is read offline, step by step (`scripts/analysis/slurp_kprobe_read.py`) |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/kprobe/kprobe_mint_receipt.py` |

**Budgets, as arithmetic (CONV's).** 605 generation contacts (55 x 11,
run-cumulative), 2420 FIT endpoints (4 x), 330 native
task-contract calls (55 x 6), 1405 repeated speech seconds
(ceil(127.701375 x 11)), 1.0 GPU hour, one official complete score.
Expected spend: about 276 contacts and about
0.19 GPU hours at the sealed arm's own realized rate.

**No committed `prepared_phase_supply`, and an empty requirements list.** The flip mints this cell's own
first-phase supply under its own run id (item E16); `core.flight.repin._set_preparation_requirement` rewrites
every `kind == "preparation"` entry, so a second requirement would be silently clobbered, and
`--allow-output-change` must never be passed. The key file stays pinned where the loader verifies it:
`facet_source.sha256` in the baseline, plus its receipt in `preparation_source_receipts`.

**Mint, flip, queue (CONV's sequence with names changed).** Root countersigns the three DRAFT exposure rows
(`SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-V1`, `SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-FIT-V1`, `SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1`), mints
`coordination/slurp-stage3-kprobe-fold-a-55-v1/root-admission-v1.json` from the draft with `scripts/flights/kprobe/kprobe_mint_receipt.py`
(decision id `slurp-stage3-kprobe-fold-a-55-admission-v1`, the two eligible run ids and this cell's caps), flips with
`scripts/flights/kprobe/kprobe_flip.sh` (the generic re-pin loop over `kprobe_repin_arm.sh`; one cell, no
smoke -- 55 rows is itself a form proof and the treatment form is the locked plan's), then queues
`scripts/flights/kprobe/batch_chain_kprobe.sh` behind whatever occupies the np4 session (decision 77).
After the seal: `python scripts/analysis/slurp_kprobe_read.py --data-root "$SPEECHRL_DATA_DIR"`.

**Not authorised by this package.** No flight before the receipt is minted and the cell is flipped; no contact by
this registration; no re-flying of the comparator; no test-split, Fold B or DEV read; no second factor; no store
rebuild or release; no re-pin of the committed configs; no pooled claim; no admission entry.
