# Cell CONV: the conversion from delivery to correctness

Registered before contact 2026-09-26 at study commit `c6ced983`; the cell is **held**.
Nothing here authorises a flight, a flip or an admission entry.

**The one unmeasured quantity.** Cell AGREE's declared expectation of
1.363 pp SLU-F1 is a product: a **measured** delivery gain -- 70 newly delivered
`INTENT-UNCOVERED` rows of TRAIN Fold A, 0 lost -- times a conversion of 0.467895, which is
itself a measured `P(correct | covered)` of 0.935789 times an **unmeasured persuasion
factor of 0.5**, the midpoint of `[0, 1]` and nothing more. Even at a perfect conversion the
arm's ceiling is 2.9131 pp against a 2.5 pp admission bar at n = 1,080, so it needs a
conversion of at least 0.8582. This cell measures that factor directly, on exactly the
rows the gain lands on, for about a quarter of a GPU hour instead of the roughly seven the arm
plus its in-chain A/A would spend learning it as a by-product. The parent package names this
option itself.

**No new mechanism, no comparator flown.** Every knob is the registered AGREE arm's
(`w_agree` 1.0, `w_cos` 1.0, `w_prior` 0.0, `k` 60, `tau` 0.0, `fuse_coverage` m 8 / c 1 / top_l 8,
the same pinned agreement table, the same model fragment, geometry, session, program, stores,
role graph, templates, normaliser and scorers). Exactly two things differ, and both are roster
arithmetic: the population is the 70 derived ids, and every ceiling is rescaled to 70 rows. The
sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` already holds these rows' answers and is
intent-**wrong** on every one of them, so the probe flies the **treatment only**.

**The roster, and the one thing that had to be checked first.** The committed replication receipt
`docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/production-replication-v1.json`
(sha256 `7cd1f6d338731ea7b6eef34408e5d37453c852670900319445968ddc2a1dc624`) records the **count** -- 70 newly delivered of 130
`INTENT-UNCOVERED`, 0 lost -- and carries **no row ids**: its own text discipline emits "an id, a
count, a rate or a hash" and it chose counts. The roster therefore cannot be read off the receipt.
It is **reconstructed** by importing that receipt's own recipe byte-unchanged
(`scripts/analysis/slurp_intent_agreement_production_replication.py`, sha256
`62c175d5fda67ca8a3743a25a309e433941607f13be648d997f245c8901cd17d`)
and calling its own functions with its own parameters, and the reconstruction is **proven** before a
single id is taken: the whole delivery block, both boundary-channel pin blocks, the bank digest, the
builder digest, the sealed phase-artefact digest, the split identity and the roster row count all
reproduce **exactly** (0 differences). Receipt:
[`roster-derivation-v1.json`](readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json) --
70 ids, id-list sha256 `5920bd6c99d1d5935881c0ca85c8454c7ec8eed096d950b7242c0ec7d8fbf73b`,
split identity `57c6f278d8ab35dafa0f1183938c13b6084a4f3d9d9438cfb3e55bbf73ff335c`.

**The roster is selected using gold, offline.** That is legitimate for a *conditional* estimate on a
TRAIN roster and for nothing else. **No pooled or roster-level claim may ever be made from this
cell**, because its population was chosen by the mechanism's own effect. Gold reaches no query, no
key, no weight, no selector and no runtime. The cell also **cannot see harm**: every row here is
already intent-wrong in the comparator, so the rows where the mechanism could cost a correct intent
are outside this roster and remain the AGREE arm's own question.

**Why it reads intent, not SLU-F1.** The within-flight null
[`docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`](results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md)
measured **0 intent flips out of 200** request-identical rows, so an intent flip is attributable
rather than noise. Pooled SLU-F1's own noise would swamp 70 rows, and the official SLU-F1 is
entity-only while this mechanism acts on the intent. The official scorer still produces the number;
the read takes its per-sample `scenario_action_exact` and nothing else.

**The deliverable.** `P(correct | newly delivered)` = m / 70 with a binomial CI95, plus the reverse
count -- which is **zero by construction** on this population, reported as a limit of the cell and
not as a result. Multiplying the rate by the class's registered per-row headroom gives the AGREE
arm's re-declared expectation: m x 0.041615 pp SLU-F1 and m x 0.092615 pp intent
accuracy. The arm clears its own bar only if **m >= 61**.

**`stage3_measurement`.** 70 rows is under the measurement instrument's `MIN_BENEFIT_ROWS`, so the
design is `form-proof`, `claims_benefit` is **false** and `expected_effect_pp` is **0.0**; the note
says the cell measures a conditional rate and makes no effectiveness claim. **No `admission` mode is
declared**: that field is for a base item being admitted, and this cell is not asking for admission.

**`stage3_algorithm`.** `none`, with the parent's own reason: no rollout, no per-sample scoring, no
credit assignment, no update operator, no evolving store. A measurement of a factor is even less of
a policy search than the one-weight change it measures.

| file | what it holds |
| --- | --- |
| `../2026-09-26-slurp-stage3-conv-fold-a-70-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `roster-derivation-v1.json` | the 70 ids, and the proof they reproduce the committed receipt |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the cell's two plans |
| `analysis-recipe-v1.json` | how the conditional rate is read offline, step by step |

**Budgets, as arithmetic.** 770 generation contacts (70 x the program's own
11-contact ceiling, run-cumulative), 3080 FIT endpoints (4 x),
420 native task-contract calls (70 x 6),
1899 repeated speech seconds
(ceil(172.605125 x 11)), 1.0 GPU hour, one official
complete score. Expected spend: about 352 contacts and about
0.24 GPU hours at the sealed arm's own realized rate.

**No committed `prepared_phase_supply`, and an empty requirements list.** The agreement merge moved
the implementation sha256 of `rails.kb_policy`, `rails.knowledge_provider` and `rails.phase_supply`,
which `FlightRuntime._phase_seed_inputs` binds, so **every `prepared_phase_supply` pin in the
repository is invalidated** and any cell awaiting a flip must be re-pinned. This cell carries no pin:
the flip mints its own under its own run id (item E16) and `--allow-output-change` must never be
passed. The requirements list is empty for a second reason --
`core.flight.repin._set_preparation_requirement` rewrites **every** `kind == "preparation"` entry to
the freshly minted supply pin, so a second requirement would be silently clobbered. The agreement
table stays pinned where the loader verifies it: `agreement_source.sha256` in the baseline, plus its
build receipt in `preparation_source_receipts`.

**Mint, flip, queue.** Root mints the admission receipt with this cell's two eligible run ids
(`SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1`, `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1`) and this cell's caps, countersigns both
exposure rows, then re-pins with `scripts/flights/repin_cell.py --set-ready`.

**Not authorised by this package.** No flight before the receipt is minted and the cell is flipped;
no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV read;
no second factor; no pooled claim; no admission entry.
