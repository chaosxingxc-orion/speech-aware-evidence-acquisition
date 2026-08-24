# DEV-500 confirmatory — the ONE registered read

Exposure row `SAEA-SN-MF-DEV500-CONFIRMATORY-READ` (registered before any computation,
ledger commit `405000ee`). Profile `model-free-check`. Calls 0 / metered audio-seconds 0 /
GPU-hours 0.0.

Verdict artifact: `read-verdict.json`
(sha256 `b3187fea6f23f637dfa8ac43718667b0286a5c034ea9304bfb03e7029bfc90a3`).
Read module: `src/speech_aware_evidence_acquisition/analysis/dev500_confirmatory_read.py`.

## 1. One-shot semantics

The preregistration
(`docs/readiness/2026-08-24-dev500-confirmatory-preregistration.md` §1) and its
machine-readable twin (`configs/experiment/slurp-dev500-confirmatory-campaign-v1.json`,
`dev500_confirmatory_statistic`) froze the statistic **before** the four arms flew. All four
arms flew, sealed, and landed mechanically with gold closed; this read then opened
everything together, once.

**The statistic was computed exactly once, exactly as registered.** No threshold was
changed, no parameter re-tried, no partial re-read performed, no arm re-flown — and none of
those would have been permitted whatever the outcome had been. Gold opened once, here,
scoring-side, for all 500 DEV-500 samples, and the campaign's contact phase was already
closed when it did, so no gold could reach any runtime context.

A second execution of the read module against these same pinned bytes is a reproducibility
check and can never become a second read. Every input is pinned by SHA-256 and a mismatch is
a fail-closed `ReadError`, never a warning.

## 2. Sources (all verified at load)

Committed per-arm mechanical reports, in
`docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory/`:

| arm | report sha256 |
|---|---|
| M0 | `22bd0d1a26b5f7f27200893dea67c4537e2eaad3350bfedd8e19527a22b15979` |
| BLEND | `d7a6b159b94a95e5524e02ba94076b93286fa5056cf73f397743587959cbffff` |
| ABL-RANDRET | `8a860273d00c0a932d1dd57ad71bcc09913b28a29412bdf5deb996f4763a040d` |
| ABL-RANDICL | `be3d210d9d7244e6cb799c1826b928cd877a7a359d0691a193c074b20d51a155` |

Sealed attempt-store bytes, under `$SPEECHRL_DATA_DIR/runs/SAEA-DEV500-CONFIRMATORY/`:

| attempt | outputs sha256 | per-sample mechanical sha256 |
|---|---|---|
| `attempt-20260824T203716Z-dev500m0` | `d09fbf479a5bb48b9ff69d1499e01ed5f233bbce20b4c6196ba5bbbed787629d` | `76e5dfc94b4d6de03d9fa57ebb1f9db07e47b9dc7126f42ae0baf55212d57704` |
| `attempt-20260824T205527Z-dev500blend` | `3ae9fef0c75cbceb7d008115522df8854d0a0db473cd553c1c44f4b7200efe0b` | `164210fbaf954d36459e62c14b61c927e31c5be38273aee155b96a9ae29bb52b` |
| `attempt-20260824T212928Z-dev500randret` | `aa0bab8fb606da5da0ff7a8db305b0e8a3cae77e48ea96b33dbe7b3d05015890` | `1fc2cfd7acb0a0cc36b42c78cbc36d45f61952a6671d339666dcd19842fe91ef` |
| `attempt-20260824T213948Z-dev500randicl` | `ffbfc92d15d58db694c528864a2120487ff22c2c621ed61917064fb2d2956248` | `d8417013c22c9ea99f7186c103c815c9ed6e8d177b4d1cd71188a79ff138f14f` |

Also pinned and verified: the three committed split receipts (DEV-500 `adc3e4dd…c315`,
DEV-100 `0cf5effe…20d0`, DEV-500-NEW400 `86c199b2…d95fc`), each re-derived identity hash
matching its receipt; the TRAIN knowledge snapshot
`e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57`; and the content-facet
vector NPZ `0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72`. The **value
vectors were never opened** and stay sealed.

Two independent cross-checks were required to pass before scoring: each arm's sealed
per-sample contact counts must reproduce its committed report's retain-primary/dispatched
totals, and each arm's sealed outputs must cover exactly the population its registration
named. The unexposed NEW400 population was re-derived as the deterministic set difference
DEV-500 − DEV-100 and matched against its own committed receipt, so the claim population is
proven rather than trusted.

Scoring path: `reproduction.slurp_scoring.parse_slu_response` + `score_slu`, correctness =
`scenario_action_exact` — byte-for-byte the computation
`rails.adapters.slurp.SlurpAdapter.score` performs, which is the call the sealed DEV-100
round launchers made post-seal. The read therefore cannot score differently from the
campaign it reads.

## 3. The claim condition, stated verbatim

Preregistration §1, quoted:

> **Statistic**: paired per-sample BLEND − M0 over the 400; paired cluster bootstrap
> (N=10,000, seed 20260807) 90% and 95% CIs; McNemar exact test on the discordant pairs.
> **Claim condition (preregistered): the 90% CI excludes zero.**

Computed over the 400 unexposed samples only (DEV-500 minus the nested DEV-100):

- M0 **210/400 = 52.50%**; BLEND **289/400 = 72.25%**
- paired delta **+79 samples = +19.75 pp**
- W→C **81**, C→W **2**, concordant **317**
- paired cluster bootstrap N=10,000 seed 20260807: point **+19.7500 pp**, σ̂ **2.0563 pp**
- **90% CI [+16.5000, +23.0000] pp — excludes zero**
- 95% CI [+15.7500, +23.7500] pp — excludes zero
- 0 of 10,000 replicates at or below zero
- McNemar exact two-sided **p = 7.210947e-22** (mid-p 3.692327e-22; continuity-corrected
  χ² = 73.3012, p = 1.113000e-17; odds ratio 40.5)

### CLAIM CONDITION: **MET**

The 90% CI on the paired per-sample BLEND − M0 gain over the 400 unexposed samples excludes
zero.

The registered variance prior is carried as registered: the DEV-100 round-5 replication
gave ±2 per 100 at 8-slot decode.

## 4. Registered secondary readings (reported, no claim attaches)

Every block below was registered in advance as a reading, not as a claim. Their intervals
are published for completeness and none of them is a confirmatory result.

| contrast | population | baseline | treatment | delta | 90% CI (pp) | McNemar exact p |
|---|---|---|---|---|---|---|
| BLEND − M0 | exposed 100 | 49/100 | 70/100 | +21 (+21.00 pp) | [+15.00, +28.00] | 9.536743e-07 |
| BLEND − M0 | pooled 500 (descriptive) | 259/500 | 359/500 | +100 (+20.00 pp) | [+17.00, +23.00] | 5.384962e-28 |
| BLEND − ABL-RANDRET | NEW400 | 226/400 | 289/400 | +63 (+15.75 pp) | [+12.50, +19.00] | 8.735849e-16 |
| BLEND − ABL-RANDICL | NEW400 | 188/400 | 289/400 | +101 (+25.25 pp) | [+21.00, +29.25] | 6.510103e-21 |
| ABL-RANDICL − M0 | NEW400 | 210/400 | 188/400 | −22 (−5.50 pp) | [−9.50, −1.50] | 2.976641e-02 |
| ABL-RANDRET − M0 | NEW400 | 210/400 | 226/400 | +16 (+4.00 pp) | [+2.25, +6.00] | 8.554459e-04 |

The pooled-500 row is descriptive only and is explicitly **not** the claim: it mixes the 400
unexposed samples with 100 that six sealed DEV-100 rounds already read.

Full W→C / C→W lists per comparison, per-scenario tables for both populations, per-arm
confusion tables, the retain-primary vs dispatched subgroup split, and the scenario/action
field decomposition are all in `read-verdict.json`.

## 5. The retrieval-reachability ceiling, and what it does not say

**Charter disclosure, restated wherever this number is cited.** The literature standard
(RASU's GT-prompt line) requires gold-conditioned supply at runtime, which this repository's
immutable charter forbids. The oracle arm was therefore never flown. The registered
substitute is the analytic retrieval-reachability ceiling computed here scoring-side. It
bounds what **retrieval** could have reached. **It is silent on what the frozen core would
have answered given that supply**, and no such reading may be taken from it.

Over the NEW400, gold-facet recall@k against all 11,514 landed content facets:

| k | 1 | 2 | 3 | **5** | 8 | 10 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|---|---|---|---|---|
| recall | 58.75% | 66.50% | 68.00% | **71.50%** | 74.25% | 76.25% | 78.50% | 84.25% | 88.25% | 93.00% |

At the frozen cell's own `top_k_per_dimension = 5`, recall is **286/400 = 71.50%**. A
gold-bearing facet exists in the KB for all 400 samples (0 absent); gold-facet position p10
= 1, median = 1, p90 = 82, max = 2023. The vectorised cosine was pinned to
`kb_policy._cosine` on 3,600 probes (each sample's top-8 plus its gold-bearing facet) with
zero disagreements beyond 1e-9.

## 6. Cost and the zero-contact proof

This read: **0 frozen-core contacts, 0 tool contacts, 0 metered audio-seconds, 0.0 GPU-h.**

Proof, two independent ways:

1. **Offline guard.** `analysis.dev100_reviewer_audit.arm_offline_guard` was armed before any
   input was opened, replacing `socket.socket.connect`, `connect_ex` and
   `socket.create_connection` with raisers that count attempts. Outbound connection
   attempts: **0**. An armed guard that refuses every outbound connection is a stronger
   statement than an unchanged log, because it cannot be satisfied by a contact that happens
   to log nothing.
2. **Resident service log, byte-compared.** The resident decoder (unit
   `saea-np8-dev100-r6-base`, llama-server pid 2768, port 8080) was never started, stopped,
   probed, or contacted. Its durable log measured **3,317,828 bytes / sha256
   `231e4a34c764626edb028c2689b031037d46f90b7e1c6716ef882903d35d9b62`** both before and
   after the read — byte-length identical and hash identical.

The campaign whose bytes were read (re-summed here from the four committed reports) spent,
against its registered ceilings:

| | M0 | BLEND | ABL-RANDRET | ABL-RANDICL | total | ceiling |
|---|---|---|---|---|---|---|
| frozen-core contacts | 502 | 668 | 534 | 802 | **2,506** | 3,200 |
| pinned-tool contacts | 0 | 502 | 0 | 0 | **502** | 1,000 |
| metered audio-seconds | 1,425.665 | 1,879.107 | 1,521.040 | 2,296.347 | **7,122.159** | 8,000 |
| GPU-h (GPU-active) | 0.2698 | 0.3794 | 0.3368 | 1.2322 | **2.2182** | 3.0 |

Inside every ceiling.

## 7. Scope (preregistration §5, binding)

Dev-tier confirmatory. **No test claim. No generalization claim. No controller/RL claim.**
FINAL60 and test remain untouched, and nothing in this read touches them.

This artifact reports the registered outputs only. Interpretation — including what the
positive read authorizes next under the owner ladder — belongs to the coordinator, not to
this document.
