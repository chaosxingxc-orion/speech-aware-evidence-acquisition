# SCOREBOARD v5 — speech-as-knowledge on a frozen local core (LIVING DOCUMENT)

Owner goal (2026-08-19, standing): find an agent-technology scheme, on the existing local frozen
model, in which speech signals are MODELED INTO knowledge and multimodal knowledge is EFFECTIVELY
CONSUMED with task-performance gains — demonstrated with CONSISTENT improvement across small-scale
explorations. This document is the running consolidation. Registration and verdict documents remain
the evidence of record; this is the index over them.

**Version 5, landed 2026-08-25.** Row `SAEA-SN-MF-SCOREBOARD-V5`, registered before any input was
opened. Zero frozen-core contacts, zero embedding-tool contacts, zero tokenizer contacts, zero HTTP
or socket requests, zero audio seconds, 0.0 GPU hours, zero gold labels opened. The offline guard
(`analysis.dev100_reviewer_audit.arm_offline_guard`, imported rather than reimplemented) was armed
before the first input was opened and recorded **0 outbound connection attempts against 0 targets**.
The resident llama-server was treated as COLD and was not started, stopped, probed, reconfigured or
contacted. No knob was changed; nothing under `configs/`, `rails/` or `core/` was written; new code
landed only under `analysis/`.

---

## 0. How to read this scoreboard

Six rules. They are the difference between this table and the one it replaces.

1. **Two axes, never merged.** These tasks decompose into **MATCHING** — pick the right intent
   (SLURP `scenario_action_exact`) or the right tool (Audio2Tool `tool_accuracy`) — and
   **EXTRACTION** — pull the structured content out (SLURP `slot_f1_exact` macro plus the official
   micro `slu_f1`; Audio2Tool `exact_match` over the name-plus-argument multiset plus the slot
   micro-F1). They get separate columns. **A cell that measured only one axis leaves the other
   empty. It never borrows its neighbour's number.**
2. **POPULATION and WHERE-DELIVERED never share a column.** Supply is delivered **only** to
   DISPATCHED trajectories; a RETAINED trajectory stops at contact 0 and is handed nothing. So the
   delivery column carries the dispatch count and rate on every row where a conditional figure
   appears — SLURP DEV-1000-NEW500 **163 / 500 = 32.60 %**, Audio2Tool A2T-G1-104
   **15 / 104 = 14.42 %** — and a conditional row says `WHERE DELIVERED` in its population cell.
   A where-delivered number is never a population effect.
3. **SECONDARY READINGS.** The SLURP DEV-1000-NEW500 (500 unexposed) is the **locked baseline's own
   population**. Every statistic computed on it after the one-shot lock read is a SECONDARY reading:
   descriptive, and it **must not be used to revise, re-tune or restate THE LOCK**, which stands
   exactly as landed at `d9fef537`. The nested DEV-500 half, the DEV-100 rounds and the whole
   A2T-G1-104 are exposed-tier and can never carry a campaign claim.
4. **Small-n cells are MECHANISM READINGS, never effect sizes.** Cells conditioned on the arms'
   matching outcome *and* on the controller's dispatch decision are conditioned on post-treatment
   variables twice over and carry selection (collider) bias. A small-n cell is a mechanism reading
   whatever its interval says.
5. **The test split is untouched.** FINAL60 is reserved. No row below reads it, names a sample in
   it, or projects against it.
6. **Provenance is one hop, and every number was re-read from its own artifact.** Each row cites a
   register key (§1). Every figure in this document is declared in
   `src/speech_aware_evidence_acquisition/analysis/scoreboard_v5_verification.py` against the
   artifact and the JSON path it came from; the module re-hashes all 53 artifacts with SHA-256 and
   refuses to return unless every declared value matches. **415 receipt-field claims, 14
   receipt-substring claims and 19 verbatim document assertions passed, 0 failed, across 48
   SHA-256-verified receipts and 5 SHA-256-verified documents, with 0 outbound connection
   attempts.** A number no artifact supports is not in this table; it is in §5.

**Two provenance tiers, kept apart.** Tier **R** is a receipt: path, digest, and the JSON field the
number lives in. Tier **D** is a landed document: path, digest, and the exact sentence asserted by
the verification module — used only where the computation's own artifact lives outside Git under
`SPEECHRL_DATA_DIR` and therefore cannot be re-read here. Tier-D rows are marked, and §5 lists what
that means for each.

**Where arithmetic appears.** A percentage of two verified counts, or a difference of two verified
means, is arithmetic over verified fields rather than a published field. Every such figure below is
marked *(arith.)*.

**What changed from v4.** Version 4 was a prose consistency ledger: one accuracy-shaped number per
mechanism, no delivery rate, no per-row provenance, no separation of the two axes, and several
figures restated from other documents' prose. It is not reproduced here — it is
`git show d9fef537:docs/readiness/2026-08-19-scheme-scoreboard.md`. One claim it carried is
**wrong** and is corrected in §6. Note also that v4's internal *scheme-statement* numbering had run
ahead of the document's own (it carried a statement labelled "v5, 2026-08-23" inside a v4
scoreboard); from here the document carries **one** version number, and this is v5.

---

## 1. Register — every artifact this scoreboard cites

Citations read `R-KEY · json/path` (tier R) or `D-KEY · verbatim sentence` (tier D). The register
carries the full path and digest once, so a citation is one hop from a hashed artifact rather than
from prose. All paths are repo-relative; receipts live under
`docs/checks/speech-aware-evidence-acquisition/` (abbreviated `…/`).

| key | tier | artifact | sha256 |
|---|---|---|---|
| **R-PSLU** | R | `…/2026-08-18-pslu-read/verdict.json` | `7bedd461e4443932bda01444af84cac65f700c45d79e7d1cc012fd22ce1a287f` |
| **R-PSLU2** | R | `…/2026-08-18-pslu-s2-read/verdict.json` | `a29e5ac1151711f8b56a41609187b65d018753369ac680cf402a2ad2fedc2fe8` |
| **R-PPHON** | R | `…/2026-08-18-pphon-decomp/verdict.json` | `0654ba1fbf242c789e6fdc6211f6de501a1a36e747fa79d8e0e466358c1f32ec` |
| **R-A2T-A0** | R | `…/2026-08-18-pa2t-a0-read/verdict.json` | `8b0e96ca6eac50b75eb07d6f1d05b245c43cc845e877b8f1dd185e4665c7ccff` |
| **R-A2T-S2** | R | `…/2026-08-18-a2t-s2-read/verdict.json` | `2377f09ac1138c2648e18fd6ac040465f5d4d11967f4f6479b39ec53bbffa8bf` |
| **R-A2T-S2B** | R | `…/2026-08-18-a2t-s2b-read/verdict.json` | `ad49af4c73e281b5094aecb917bf59b4b13cf3c7472b54e45947f895a2a86363` |
| **R-A2T-S2C** | R | `…/2026-08-18-a2t-s2c-read/verdict.json` | `904b63c1465371f6dcc5c6093cc39153001a32974d06fc83fab357c7a7f75fdc` |
| **R-A2T-LOSS** | R | `…/2026-08-18-a2t-loss-decomp/verdict.json` | `04bb9dc841bb0ce95efdd9223cee72e8cf901929d114d3cb19c9c3294b3ccb07` |
| **R-A2T-ABST** | R | `…/2026-08-19-a2t-abst-read/verdict.json` | `23eaafa9a0d6fe958722d7c0d752a866a70b7bb3f91171ae68e23ae7cc50ec49` |
| **R-A2T-POP** | R | `…/2026-08-19-a2t-pop-read/verdict.json` | `27457acaab8f193a4783cf166fdd8320dc0bd7204b038e35603074c5fbb9b73d` |
| **R-PFEW** | R | `…/2026-08-19-pfew-read/verdict.json` | `339ad933a68e97115601d8e2751e77e37b0e1643693068b6f8d1eb427878057b` |
| **R-PTRAP** | R | `…/2026-08-19-ptrap-read/verdict.json` | `41241cc197194fdde5a2a4061144c42d6a744f9fa41b1a15546689f5778635ca` |
| **R-PKEY2** | R | `…/2026-08-19-pkey2-read/verdict.json` | `429d3159fb10c1b6f0cda8567abc1a7065e2bcef0db3901d31ebe0500cdaedff` |
| **R-PEMB1** | R | `…/2026-08-19-pemb1-read/verdict.json` | `a2957d5637bb15f2502ee064df7f7e1e5477c31b5fc780c875cafac14ccc1992` |
| **R-PEMB2** | R | `…/2026-08-19-pemb2-read/verdict.json` | `3ed669178ab1ff685be136892fcaa4039c691b0a395caaf575582c127c51f76f` |
| **R-PEMB3L** | R | `…/2026-08-20-pemb3l-read/verdict.json` | `b4644d0a7c5e6db4b1415c95eea288d82872d00ec21ed5b9a5bdd0c5edde1171` |
| **R-PEMB3M** | R | `…/2026-08-20-pemb3m-read/verdict.json` | `17c3a9398003a94724e9c8a6d162407ad0abc1896c7fff5e718f97a3ee1409ce` |
| **R-PEMB4R** | R | `…/2026-08-21-pemb4r-read/verdict.json` | `f1220d7b3518a80ccbd98e0c74afd249c9ee7cb1cbae39d2a2d5a0eda2a81691` |
| **R-PCORRF** | R | `…/2026-08-20-pcorrf-read/verdict.json` | `e7ee3fda16c7dbce02559826da49b0259bb1ad27b7f0775cbfb61d8b85fc5e0c` |
| **R-E108** | R | `…/2026-08-23-e108-zcopy-read/read-verdict.json` | `e0154a4e26a839abb7a44584714442415724dd93f95996e1111b15c84a82504c` |
| **R-R0** | R | `…/2026-08-24-dev100-round0/round0-report.json` | `26f05488bb7031d1ae85710faffd2b414644729af1adc476a1002a55612fb0b6` |
| **R-R1** | R | `…/2026-08-24-dev100-round1/round1-report.json` | `559559d239103f2905d8e86e643741990ceb1023070095d1d797d8e66de4cd8d` |
| **R-R2** | R | `…/2026-08-24-dev100-round2/round2-report.json` | `c69cf3fef49a3bafb86818383953c9c0e37880518750073c6ba857f47e7b00f6` |
| **R-R3** | R | `…/2026-08-24-dev100-round3/round3-report.json` | `ac5a884febb43ede69b6401deb6e1e67e1e543c8e8082e50ad552b8358c47965` |
| **R-R4** | R | `…/2026-08-24-dev100-round4/round4-report.json` | `42fa837582f5f9e129348d4ecc8324c56db62a754728048126c319666a997f1e` |
| **R-R5** | R | `…/2026-08-24-dev100-round5/round5-report.json` | `482d33bde5fe4ff7a522f8ca5e2b4fd7f02f3a87a6113f682c6218f3256e4d71` |
| **R-KWIDEN** | R | `…/2026-08-24-dev100-kwiden-k1/kwiden-k1-report.json` | `66a340da402f97f6495f87a6a0e3abfa312b3b7771652bd3087407eafee98f9f` |
| **R-A4** | R | `…/2026-08-25-dev100-retain-override/retain-override-report.json` | `0615275e395e983c54a694a9641c06de7d1c9a9b5aa87801d33edd002d9ef92f` |
| **R-DEV500** | R | `…/2026-08-24-dev500-confirmatory-read/read-verdict.json` | `b3187fea6f23f637dfa8ac43718667b0286a5c034ea9304bfb03e7029bfc90a3` |
| **R-LOCK** | R | `…/2026-08-25-dev1000-lock-read/read-verdict.json` | `2f8e295852e1c09d737467a62123586f097f938ec353dcbe58d258dadc1ea581` |
| **R-AUDIT** | R | `…/2026-08-24-dev100-reviewer-audit/reviewer-audit.json` | `e039b5818fa23ef5568f4c6e505ea6d66e0fbb8493121f0c606994695f3bcc89` |
| **R-G1** | R | `…/2026-08-25-a2t-g1/g1-read-attempt4.json` | `cb5e56584a6d572f7b41b39542201ddb1b361755042eac66c3a70c55fd086f89` |
| **R-SWEEP** | R | `…/2026-08-25-a2t-admission-scale-sweep/sweep-report.json` | `88f606fe89eb42e675bdd4832a31b028638613eba71d712d3d4ee6cf7aa74d66` |
| **R-GOLD** | R | `…/2026-08-25-a2t-gold-absence/diagnosis-report.json` | `64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14` |
| **R-ORACLE** | R | `…/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json` | `b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723` |
| **R-XC** | R | `…/2026-08-25-cross-carrier-decomposition/decomposition-report.json` | `9a1903b35f3eff42dc7bf4caee5ba95235af855e9e0fc087ba8d9d7c0d8be5a1` |
| **R-MVE** | R | `…/2026-08-25-matching-vs-extraction/read-report.json` | `378757b5bc3292395cbdc82a19c936912edaf61725cede012bfad6b77ffd6523` |
| **R-ECD** | R | `…/2026-08-25-extraction-conditioned-on-dispatch/read-report.json` | `7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525` |
| **R-DEGEN** | R | `…/2026-08-25-query-key-degeneracy/degeneracy-report.json` | `a1a40999dfddae7642cdc3eaa6763a8fcffe1874e5488210e41618c219a6aeae` |
| **R-FIELD** | R | `…/2026-08-25-field-level-supply-accounting/accounting-report.json` | `ca973be873318deb6029f183045ac4074653dd1b5943c9113fb78d40766de4c6` |
| **R-K1GATE** | R | `…/2026-08-25-k1-hybrid-ranking-gate/gate-report.json` | `252d53f30baed2ee36a725b0df9c5a5807438713c755845c8b8376b76ff5556f` |
| **R-FUSION** | R | `…/2026-08-25-fusion-form-gate/gate-report.json` | `568a78eeebd1519fcd7bee9d0c240469ffd6cb2b640fd4d4931ea22007a69647` |
| **R-GATEAUDIT** | R | `…/2026-08-25-gate-audit/gate-audit-report.json` | `c850ace8e025071658201c3bc57f39741b8282f230fc0614f9dae9957516f8f3` |
| **R-INTENT** | R | `…/2026-08-25-slurp-intent-coverage/intent-coverage-report.json` | `de1e9778795fc6b0d02445a53c45dedf060f483978e542e0f354003545d52750` |
| **R-PRIOR** | R | `…/2026-08-25-prior-score-semantics-repair/repair-report.json` | `041de6c0868ca4324545d2a423c098d5d96218ca9443fff2ca527aa053895c05` |
| **R-FACET** | R | `…/2026-08-25-content-facet-target-audit/audit-report.json` | `ff4311fab3b61719dc5d59b6e30a2eeada899b3d34ba7f7e20b5ac891886dcd5` |
| **R-ALPHA** | R | `…/2026-08-25-alpha-trade-sizing/alpha-trade-sizing-report.json` | `4df34154a86fc7bb2f683b6f2a692819c0e4283228ccdc0bf1c796081812e2ab` |
| **R-SYNTH** | R | `…/2026-08-25-stage2a-synthesis/verification-report.json` | `561a6c020d1c58a77097e88f30e2e7d597730fa570dbeb2e15200e321d45d9a0` |
| **D-SN** | D | `docs/readiness/2026-08-21-speech-native-agent-loop-training-free-rl-plan.md` | `e7803bf07300cdcf4976b5e9404d067bcf505166d79c7819c2dc85b574fb45ba` |
| **D-E108** | D | `docs/readiness/2026-08-23-e108-verdict.md` | `1d36c557a9e780569bd8e7cbb0737c45f2ffd303daad924c795ed40286666788` |
| **D-EC** | D | `docs/readiness/2026-08-25-ec-and-retain-override-projections.md` | `6d50d2ea164567e01c0cb6c5f999e10270453577b617f20d960a7a0fdb580462` |
| **D-KWIDEN** | D | `docs/readiness/2026-08-24-kwiden-and-next-experiments-queue.md` | `e4ae3f48a128bdf67811d1a67cb436b988ed83de4bf47bc1860f98c07de2285e` |
| **D-GATES** | D | `docs/readiness/2026-08-25-gate-audit-can-it-fail.md` | `6ab241b18a924122a5c3a64712bfde7fcc23a6bc2075f7ac0c281ca83d822efa` |

*(This document carries no digest of its own verification receipt: the receipt records this
document's SHA-256, so a self-citation could never close. The receipt is
`…/2026-08-25-scoreboard-v5/verification-report.json` and its `scoreboard_document` block is the
pairing.)*

*(2026-08-26 digest repair, D-GATES only. The cell above previously carried
`da59b6e1…`, taken from the CRLF working-tree bytes of that file on the Windows checkout
(32790 bytes, 345 CRLF line endings). The Git blob is LF (32445 bytes) and hashes to
`6ab241b1…`, which is what any clean checkout — CI included — measures. Umbrella `CLAUDE.md`:
"Git blob bytes are the evidence hash authority ... not CRLF working-tree bytes". Only the
digest changed; the file's committed content is untouched. The already-landed receipt
`…/2026-08-25-scoreboard-v5/verification-report.json` still records the old value and is left
as written — check receipts are append-only and are superseded, never rewritten.)*

---

## 2. Table A — landed cells, one row per cell

Row ids are stable: a new cell appends a new id and never renumbers an existing one. `n.m.` = not
measured in this cell. Intervals are 90 % paired cluster bootstrap (`analysis.bootstrap`,
N = 10,000, seed 20260807) wherever one exists.

| id | cell | date | population (exposure) | MATCHING | EXTRACTION | delivery (dispatched) | status, and what superseded it | provenance |
|---|---|---|---|---|---|---|---|---|
| **C-01** | P-SLU — elicitation-bank supply ladder | 08-18 | SLURP-60 probe (exposed) | n.m. | `slu_f1` A0 0.1741 → A1 **0.6340**, A2 0.4686, A3 0.5961, A4 0.3087; `slot_f1_exact` A0 0.0435 → A1 **0.5246**, A3 0.5000 | not a dispatch design — every arm supplied by construction | ESTABLISHED: structure-plus-value supply converts MISSING-type extraction failures. A1 carries 1 induced substitution — the value-copy channel is live | R-PSLU · `aggregates/*/slu_f1/f1`, `slot_f1_exact/f1`, `induced_substitution_count` |
| **C-02** | P-SLU stage 2 — format floor and self-scoping | 08-18 | SLURP-60 probe (exposed) | Q-B `A1'r` non-fallback **60/60**, gain vs A0 **+0.4352** → SELF-SCOPING-WORKS | Q-A format-only arm F1 `slu_f1` **0.1356**; gap to A3 **+0.4605** → KNOWLEDGE-BEYOND-FORMAT | n.a. | ESTABLISHED: the gain is not a formatting artifact, and closed-set decode routing is the routing tier's working lever | R-PSLU2 · `qa/*`, `qb/*` |
| **C-03** | P-PHON — failure-class decomposition | 08-18 | SLURP-60 + A2T-120 (exposed) | n.m. | SLURP A1r converts **41 / 85** baseline failures = 0.4824; the MISSING class **35 / 71** | n.a. | ESTABLISHED: supply acts on MISSING, not on NEAR-MISS (0/4). A2T baseline failures 56 | R-PPHON · `slurp/a1r/table/*`, `a2t/baseline_total_failures` |
| **C-04** | P-A2T-A0 — Audio2Tool baseline anchor | 08-18 | A2T-400 parent split (exposed) | `tool_accuracy` **0.5425** | `exact_match` **0.2425**; empty-call rate 0.1025 | no supply arm | ESTABLISHED: the two axes are far apart on this carrier from the start — gap **0.3000** | R-A2T-A0 · `overall/*` |
| **C-05** | A2T stage 2 — the value-copy trap | 08-18 | A2T-120 (exposed) | n.m. | copy trap CONFIRMED: S1′ induced **34** vs EM-flips **16**; S2 induced 34 vs 11 | n.a. | ESTABLISHED: in-context concrete values are copied, not reasoned over | R-A2T-S2 · `branch_verdict/copy_trap`, `copy_trap_clauses/0/detail` |
| **C-06** | A2T stage 2b — stripping the values | 08-18 | A2T-120 (exposed) | n.m. | B1 (stripped) induced **2**, conversion **8/120** → CONFIRMED-CUT. B2 (wrong content) conversion 1/120, retention 0.8250 → INCONCLUSIVE-B | n.a. | ESTABLISHED: stripping cuts the copy channel and keeps the conversion. B2's own clause did **not** close | R-A2T-S2B · `qa_verdict/*`, `qb_verdict/*` |
| **C-07** | A2T stage 2c — form robustness and augmenting | 08-18 | A2T-120 (exposed) | n.m. | C1 conversion **10/120**, C2 9/120, induced 4 / 3 → ROBUST. C3 (augmenting) induced **22** → CHANNEL-REOPENED | n.a. | ESTABLISHED: the supply envelope is form-robust; augmenting with concrete values re-opens injection | R-A2T-S2C · `form_robustness_verdict/*`, `deploy_augment_verdict/*` |
| **C-08** | A2T loss decomposition | 08-18 | A2T-120 (exposed) | n.m. | B2 losses: DRAGGED-TO-SUPPLIED **3 / 21** = 0.1429 → DRIFT-CONFIRMED; EMPTY 6, PARSE-FAIL 6 | n.a. | ESTABLISHED: wrong-content supply is inert-with-drift, not an attractor | R-A2T-LOSS · `b2_verdict/*` |
| **C-09** | A2T abstention asymmetry | 08-19 | A2T-11 pairs (exposed) | n.m. | abstention TP-S **11 / 11**, TW-A **2 / 11**, confabulation TP-S **0 / 11** | n.a. | ASYMMETRY-REFUTED — the pre-registered direction is refuted, and refusal is evidence-gated on this carrier. **n = 11: mechanism reading** | R-A2T-ABST · `verdict/*` |
| **C-10** | A2T blind-replacement regression | 08-19 | A2T EM-correct subset (exposed) | n.m. | Δ regressions **36**, CI90 **[+28.0, +44.0]** → REGRESSION-COSTLY | n.a. | ESTABLISHED: blind replacing supply on already-correct samples costs. This is the finding percept-keying (C-19) later makes structurally unreachable | R-A2T-POP · `verdict/delta_reg`, `verdict/bootstrap/*` |
| **C-11** | P-FEW — routing few-shot gain and bias | 08-19 | SLURP-60 (exposed) | FS-NONE **0.8167**, FS-BAL **0.8167** (Δ exactly 0.0000, CI90 [−0.0667, +0.0667]), FS-SKEW 0.7500; skew capture **2 / 59** | n.m. | n.a. | **INCONCLUSIVE-FEW** — a point estimate inside the band with a CI crossing it is never an affirmative equivalence. Zero prior capture at the label level | R-PFEW · `accuracy/*`, `capture/*`, `verdict/*` |
| **C-12** | P-TRAP — self-percept resonance | 08-19 | SLURP-60, 32 usable (exposed) | n.m. | capture V1 (self-percept) **29 / 32** vs V2 (cross) **0 / 32** | n.a. | **ACOUSTIC-MEDIATED** — acoustics participate in supply USE. Founding evidence for the percept gate | R-PTRAP · `capture/*`, `verdict/overall` |
| **C-13** | P-KEY-2 — audio versus text in the supply loop | 08-19 | SLURP-60 (exposed) | n.m. | interaction I **+0.0463**, CI90 **[−0.0033, +0.0970]**; Δ_aud +0.4397, Δ_txt +0.3934; T0 macro WER 0.5359 | n.a. | **INCONCLUSIVE-KEY** — the *net value* of audio over self-transcription is unresolved; the interval crosses zero | R-PKEY2 · `interaction/*`, `ci_verdict/*`, `t0_wer/macro_wer` |
| **C-14** | P-EMB-1 — generation-core pooled states, SLURP scenario | 08-19 | SLURP-60, 18 labels (exposed) | **3 / 60 = 0.0500** (below chance) | n.m. | n.a. | **EMB-WEAK** | R-PEMB1 · `accuracy`, `n_correct`, `verdict` |
| **C-15** | P-EMB-2 — generation-core pooled states, A2T tool | 08-19 | A2T-400, headline the 183 supply-unreachable (exposed) | top-1 on 183 **0.0109** (2 recoveries), top-5 0.0273 | n.m. | n.a. | **EMB-CLOSED** | R-PEMB2 · `top1_accuracy_183`, `recoveries_183`, `verdict` |
| **C-16** | P-EMB-3L — local construction sweep | 08-20 | SLURP-60 (exposed) | all three arms **0.0500** | n.m. | n.a. | **LOCAL-EXHAUSTED** — every training-free construction the pinned build can express. Build defect found: `--pooling` is inert on the audio side | R-PEMB3L · `arms/*/accuracy`, `l3_accuracy`, `verdict` |
| **C-17** | P-EMB-3M — dedicated omni-embedder, plus the cascade | 08-20 | SLURP-60 (exposed) | M1 LCO audio **3 / 60 = 0.0500**; M2 GLAP control **8 / 60 = 0.1333**; **M4 cascade 45 / 60 = 0.7500** | n.m. | n.a. | **EMB-WEAK-SCOPED + CASCADE-ROUTES**. M1 is SCOPED by the reproduced pooling-override defect, never a model-level claim. CONTROL-ANOMALY did not fire. The cascade is **text-mediated, so not speech-native** | R-PEMB3M · `arms/*/accuracy`, `verdict/*` |
| **C-18** | P-EMB-4R — register-aligned utterance kNN | 08-21 | SLURP-60 (exposed) | audio A-GLAP **0.3167** (recall@5 0.5667), A-LCO3 0.1500, A-LCO7 0.1167; text T-QW **0.8667** (recall@5 0.9333); chance 0.0556 | n.m. | n.a. | **REGISTER-RESCUE(a-glap) + KNN-BEATS-LABEL-MATCH**. Disproves the blanket "audio content-absent" claim (`audio_content_absent` = false) and still leaves the best audio arm far under text. C-DECODE **canceled by owner before the read, zero contacts** | R-PEMB4R · `arms/*/vote_accuracy_k5`, `recall_at_5`, `verdict/*` |
| **C-19** | P-CORR-F — percept-keyed corrective supply | 08-20 | SLURP-60 (exposed) | n.m. | Δ₁ = SLU-F1(W1 self) − SLU-F1(W2 cross) **+0.0508**, CI90 **[+0.0098, +0.0968]**; arm `slu_f1` W1 0.6588 / W2 0.6080 / W3 0.4336 / W4 0.6366; `slot_f1_exact` W1 0.6032 vs W2 0.5208 | supplied by construction; W-arm dose is the variable | **CORRECTIVE-PERCEPT** (met) **+ DOSE-INSUFFICIENT** (Δ₂ −0.1625, met). The dual measurement is the caution: W1 recovers **53** gold slots while emitting **12** spurious values, W2 46 / 0 — supply precision is the whole safety margin. Guardrails clean (parse 1.0000, copy 0.0000) | R-PCORRF · `q1/*`, `guardrails/*`, `dual_measurement/*`, `q2/*` |
| **C-20** | EFFECT-C108 — speech-native decoder-joint matching | 08-22 | SLURP train-only discovery, 108 (train) | direct K0-M0 **77 / 108** → embedded K1-M1 **90 / 108**; final grounded refinement 89/108; key-text shuffle **0 / 108**; speech swap **75 / 108**; action oracle 94/108 | n.m. | n.a. — no dispatch stage in this design | Bounded DISCOVERY evidence, no validation claim. The keys are load-bearing (shuffle collapses). **The speech-sensitivity threshold FAILED**: matched-minus-swap **14 / 108** against a frozen bar of 24 — v4 of this scoreboard stated the opposite, see §6. Tier **D**: the read's own artifact is outside Git (its digest `6f7017fb…f40a` is recorded in D-SN) | D-SN · verbatim sentences |
| **C-21** | E108 / M11 — adaptive evidence-gap controller | 08-23 | SLURP train-only fresh split, 108 (train) | primary **92 / 108 = 0.8519**; final-minus-primary **0** | n.m. | factor supply fired on **108 / 108**; the adaptive boundary supply on **7 / 108 = 6.48 %** *(arith.)* | Support gate **FAILED, 6 of 8 conjuncts** (D-E108) — the controller was deferred unevaluated. The acquisitions that did fire were perfect: boundary supply **4 helpful / 0 harmful** over 7 boundary queries, on 14 action-variable trajectories. ACQUIRE-on-registered-gap is precise and starved | R-E108 · `aggregates/0/*`; D-E108 · `support_gate_passed = false` |
| **C-22** | DEV-100 round 0 — the first knowledge-conditioned DEV cell | 08-24 | SLURP DEV-100 (exposed) | M0 **48 / 100** → BLEND **63 / 100**; W→C 26, C→W 11; CI90 **[+5, +24]** (R-AUDIT) | n.m. | **100 / 100 = 100.00 %** *(arith.)* | ESTABLISHED as the ladder's base. α 0.60, τ 0.50 | R-R0 · `arms/*/correct_count`, `round0_knobs/*`; R-AUDIT · `q1_uncertainty/round0/*` |
| **C-23** | DEV-100 round 1 — τ | 08-24 | SLURP DEV-100 (exposed) | BLEND **63 / 100** (unchanged) | n.m. | 100 / 100 = 100.00 % *(arith.)* | τ proven **INERT** on [0.50, 0.65] | R-R1 · `arms/BLEND_ROUND1/correct_count`; R-R2 · `round1_citation/sealed_results` |
| **C-24** | DEV-100 round 2 — α 0.60 → 0.55 | 08-24 | SLURP DEV-100 (exposed) | BLEND **65 / 100** | n.m. | 100 / 100 = 100.00 % *(arith.)* | first live knob | R-R2 · `arms/BLEND_ROUND2/correct_count`, `round2_knobs/alpha` |
| **C-25** | DEV-100 round 3 — the dispatch rule bites | 08-24 | SLURP DEV-100 (exposed) | BLEND **67 / 100**; W→C 24, C→W 5; CI90 **[+11, +27]**, McNemar exact p **5.46e-4** | n.m. | **48 / 100 = 48.00 %** *(arith.)*, retain-primary 52 | The α-blend starts retaining; the damage channel closes (C→W 11 → 5) | R-R3 · `arms/BLEND_ROUND3/*`; R-AUDIT · `q1_uncertainty/round3/*` |
| **C-26** | DEV-100 round 4 — the frozen cell | 08-24 | SLURP DEV-100 (exposed) | BLEND **72 / 100** | n.m. | **37 / 100 = 37.00 %** *(arith.)*, retain-primary 63 | The cell that becomes the baseline form (α .45, τ .65, k 5, m 5, label-binding repair `f1060078`) | R-R4 · `arms/BLEND_ROUND4/*` |
| **C-27** | DEV-100 round 5 — exact replication | 08-24 | SLURP DEV-100 (exposed) | BLEND **72 / 100**, Δ vs round 4 **0** | n.m. | **33 / 100 = 33.00 %** *(arith.)* | ESTABLISHED: the cell replicates at Δ = 0 on the same 100 | R-R5 · `arms/BLEND_ROUND5/correct_count`, `replication_reconciliation/delta_vs_round4` |
| **C-28** | DEV-100 reviewer audit — the conservative floors | 08-24 | SLURP DEV-100 (exposed) | headline round 3 +19 samples; **adversarial-flipped floor +15, CI90 [+6, +24]**; observed-worst floor **+12, CI90 [+2, +22]**; all-unstable-charged floor **−24** | n.m. | n.a. (model-free read) | ESTABLISHED: the gain survives every floor except the one that charges *all* 36 byte-unstable samples against it. Majority-class baseline **0.0600**, uniform chance 0.0167 | R-AUDIT · `q1_uncertainty/*`, `q2_variance_channel/floors/*`, `q3_baseline_fairness/majority_class/*` |
| **C-29** | K-WIDEN K1 — retrieval width 5 → 8 | 08-25 | SLURP DEV-100 (exposed) | BLEND **71 / 100** against a sealed base of 72 (Δ **−1**); C→W vs M0 **0** | n.m. | **36 / 100 = 36.00 %** *(arith.)* | REFUSED as a lever — see X-03. The decisive number is the offline replay: supply changed on 32 trajectories and produced **0 width-attributable flips** | R-KWIDEN · `kwiden_reconciliation/*`, `stopping_rule_status/*` |
| **C-30** | DEV-100 A4 — δ retain-override dispatch variant | 08-25 | SLURP DEV-100 (exposed) | BLEND **74 / 100**, Δ vs round 4 **+2**; override-attributable flips **3** | n.m. | **41 / 100 = 41.00 %** *(arith.)*, of which **3 by override** | In-sample positive, and **falsified out of sample** at C-32 — see X-06. Branch-only replay PASS (the override changes dispatch, never supply) | R-A4 · `a4_reconciliation/*`, `blend_decisions/*`, `branch_only_replay/verdict` |
| **C-31** | DEV-500 confirmatory — four sealed arms | 08-24 | SLURP DEV-500-NEW400, **400 UNEXPOSED** | M0 **210 / 400 = 52.50 %** → BLEND **289 / 400 = 72.25 %**, **+19.75 pp**, CI90 **[+16.50, +23.00]**; W→C 81 / C→W 2; McNemar exact p **7.21e-22** | n.m. at this tier | **130 / 400 = 32.50 %** *(arith. over D-EC's flown evidence-contact count)* | CLAIM CONDITION MET. The ablations attribute the gain to the retrieval SIGNAL: BLEND − ABL-RANDRET **+15.75 pp** CI90 [+12.50, +19.00] (RANDRET 226/400), RANDRET − M0 +4.00 pp, and **RANDICL − M0 −5.50 pp** — generic exemplars actively hurt | R-DEV500 · `primary/*`, `secondaries/new400_*`; D-EC · dispatch row |
| **C-32** | **DEV-1000 BASELINE LOCK** — one-shot read | 08-25 | SLURP DEV-1000-NEW500, **500 UNEXPOSED** | M0 **278 / 500 = 55.60 %** → BLEND **379 / 500 = 75.80 %**, **+20.20 pp**, CI90 **[+17.20, +23.40]**, CI95 [+16.60, +24.00], σ̂ 1.8986; W→C **106** / C→W **5**; McNemar exact p **1.04e-25**; lock condition (CI90 low ≥ +10 pp) **MET** | population macro `slot_f1_exact` 0.170976 → 0.206414 = **+3.5438 pts**; official micro `slu_f1` 0.376674 → 0.430813 = **+5.4139 pts** *(arith.)* — **no interval is published for either extraction axis at population level** | **163 / 500 = 32.60 %** | 🔒 **LOCKED, v1.** The δ ≥ 0.14 retain-override was REMOVED: `zero_loss_property_held` = **false**. Without it the same population reads **382 / 500 = +20.80 pp**, so the lock is on the *better* configuration. Scale-stable: each tier's point estimate lies inside the other's CI90 and the intervals overlap | R-LOCK · `primary/*`, `secondaries/*`; R-MVE · `two_axis_scoreboard/0,1`; R-FIELD · `channel_cost/slurp/…/delivery/*`; R-XC · `decomposition/slurp_unexposed500/locked_v1_*` |
| **C-33** | The nested prior-exposed half | 08-25 | SLURP DEV-500 nested, **500 PRIOR-EXPOSED** | M0 **258 / 500** → BLEND **378 / 500**, **+24.00 pp**, CI90 **[+20.80, +27.20]**; W→C 123 / C→W 3 | macro 0.122248 → 0.150971 = **+2.8724 pts**; official micro 0.361130 → 0.402267 = **+4.1137 pts** *(arith.)* | **177 / 500 = 35.40 %** *(arith.)* | SECONDARY, never pooled into the lock claim. Reported because it is where the supply term does **not** replicate — see C-37 | R-LOCK · `secondaries/exposed_500_blend_vs_m0/*`; R-MVE · `two_axis_scoreboard/2,3`; R-FUSION · `populations/SLURP-EXPOSED-500/flown_dispatched` |
| **C-34** | The DISPATCHED stratum — where supply is actually delivered | 08-25 | SLURP DEV-1000-NEW500, **WHERE DELIVERED**, n = 163 | M0 **7 / 163** → BLEND **100 / 163**, **+57.0552 pp**, CI90 **[+50.3067, +63.8037]**, W→C 97 / C→W 4 | macro **+9.4391 pts**, CI90 **[+4.3558, +14.5194]**; official micro **+13.7570 pts**, CI90 **[+8.8840, +18.6695]** — both exclude zero | **163 / 500 = 32.60 %** | ESTABLISHED, conditional on delivery: the gain operates on **both** axes where evidence reaches the core. **Not a population effect.** SECONDARY READING | R-ECD · `slurp/unexposed500/strata/dispatched/*` |
| **C-35** | The RETAINED stratum — the control that received nothing | 08-25 | SLURP DEV-1000-NEW500, **NOT DELIVERED**, n = 337 | +2.3739 pp | supply-attributable term is **0** by construction; residue +0.0667 pts | **0 / 337 = 0.00 %** | The contrast that makes C-34 readable: without evidence the arms barely move | R-ECD · `slurp/unexposed500/strata/retained/*`, `three_way_decomposition_slot_f1_exact_mean/terms_points/*` |
| **C-36** | The matching-free cell — extraction with matching held fixed | 08-25 | SLURP DEV-1000-NEW500, **WHERE DELIVERED and both arms matching-WRONG**, n = 59 | held fixed by construction (both arms wrong) | macro **+6.7797 pts**, CI90 **[+1.6949, +11.8644]**; official micro **+15.2312 pts**, CI90 **[+8.2127, +22.9778]** — both exclude zero | 59 of the 163 delivered | The cleanest extraction evidence in the campaign: no matching movement can explain it. Double post-treatment conditioning — **mechanism reading**. SECONDARY READING | R-ECD · `slurp/unexposed500/eight_cell_extraction/neither_matched\|dispatched/*` |
| **C-37** | Three-way decomposition of the extraction gain | 08-25 | SLURP DEV-1000-NEW500 (unexposed) and the exposed half | matching-attributable term **+2.5438 pts** (n = 111) | supply-attributable, dispatched **+0.9333 pts** (n = 62); unsupplied residue +0.0667 pts (n = 327). On the **exposed** half the same term reads **−0.0533 pts** | delivery is the partition variable | Matching dominates (71.78 % of the aggregate, R-MVE). What is new is the split of the residual: 93.33 % of it is supply-attributable *(arith.)* — **and it does not replicate on the exposed half.** That non-replication is the strongest caution on the extraction claim | R-ECD · `*/three_way_decomposition_slot_f1_exact_mean/terms_points/*`; R-MVE · `…/ab_split/a_share_of_absolute_total` |
| **C-38** | Audio2Tool G1 — attempt 4, the first post-repair flight | 08-25 | A2T-G1-104, **104 EXPOSED** | `tool_accuracy` **62 / 104 → 63 / 104**, **+0.9615 pp**, CI90 **[−2.8846, +4.8077]** — **does NOT exclude zero**, 41.56 % of replicates at or below zero, McNemar mid-p 0.6875, W→C 3 / C→W 2 | `exact_match` **29 / 104 → 29 / 104**, **0.0000 pp**, CI90 **[−1.9231, +1.9231]**; slot micro-F1 0.437870 → 0.412088 = **−2.5782 pts**, macro slot-F1 −0.2885 pts | **15 / 104 = 14.42 %** | NOT ESTABLISHED: the population delta is not separated from zero and n = 104 is below the plan's own n ≥ 400 unexposed power floor. **The tool-accuracy line must never be reported without the exact-match line beside it.** Mechanism invariants both PASS (`retain == direct-label-recovered`; branch-only replay not vacuous). Empty-call collapse 14/104 → 3/104 is the FORM channel and is not an accuracy claim | R-G1 · `paired_tool_accuracy/*`, `paired_exact_match/*`, `mechanism/*`, `headline/*`; R-MVE · `two_axis_scoreboard/4,5` |
| **C-39** | Audio2Tool DISPATCHED stratum | 08-25 | A2T-G1-104, **WHERE DELIVERED**, n = 15 | n.m. separately | slot micro-F1 **+12.1212 pts**, CI90 **[0.0000, +23.0769]** — **does NOT exclude zero** | **15 / 104 = 14.42 %** | **MECHANISM READING at n = 15, never an effect size.** The sign is positive where evidence lands and inverts on the retained set | R-ECD · `a2t/strata/dispatched/*` |
| **C-40** | Audio2Tool RETAINED stratum | 08-25 | A2T-G1-104, **NOT DELIVERED**, n = 89 | n.m. separately | slot micro-F1 **−3.0250 pts**, CI90 **[−6.1940, −0.5941]** — excludes zero | **0 / 89 = 0.00 %** | The whole-population aggregate is the weighted blend in which these 89 dominate | R-ECD · `a2t/strata/retained/*` |
| **C-41** | Ranker admission-scale defect and its repair | 08-25 | A2T-G1-104 + SLURP DEV-1000-NEW500 | dispatch **0 → 15** post-repair; the dispatch set equals the label-free set exactly | gold-bearing supply admitted **68 / 104** | 15 / 104 = 14.42 % post-repair | ESTABLISHED as a DEFECT REPAIR, not a re-tune: on **104 / 104** trajectories zero content facets reached the top-`m` window pre-fix (`m` would have needed to be **15**), and the pre-fix gate reproduced the flown supply and dispatch **104 / 104** each. **The repair is an exact identity on the locked SLURP cell.** It supersedes the earlier reading that the A2T zero-dispatch was a paradigm boundary | R-SWEEP · `audio2tool/*`, `fix_verification/*` |
| **C-42** | Audio2Tool gold-absence diagnosis | 08-25 | A2T-G1-104 dispatched, n = 15 (11 gold-absent) | n.m. | of the 11 gold-absent: **0 BUILD defects, 11 RANKING defects**; gold-facet recall **0 / 11 at the locked k = 5**, rising to **1.000 at k = 512**; τ binds on 9, `top_l` on 2; form repaired on 11, still wrong on 9 | 15 / 104 = 14.42 % | ESTABLISHED: **a KB-construction lever has nothing to fix on this population**, and no admissible depth reaches gold (0/11 under the locked `top_l`, 2/11 under any) | R-GOLD · `q1_build_versus_ranking/*`, `q2_reachability_curve/*`, `q5_form_repair_channel/*` |
| **C-43** | Audio2Tool oracle-query upper bound | 08-25 | A2T-G1-104 dispatched, n = 15 | n.m. | O3 supplies gold to **11 / 11** gold-absent (twin-free **11 / 11**); a random same-tool sibling query delivers **1596 / 1871 = 85.30 %** *(arith.)*. The runtime-legal N1 query clears τ on **15 / 15** and supplies gold to **0 / 15** | 15 / 104 = 14.42 % | ESTABLISHED: **the cell is not the ceiling; the query is** — and the oracle encodes tool identity, so it bounds from above and names **no legal fix**. Decontamination measured: 0/104 eval units in the KB, 6/104 utterance texts appear verbatim, **0** of those among the dispatched 15 | R-ORACLE · `oracle_bound/summary/*`, `lower_constructions/summary/*`, `utterance_leak_check/*` |
| **C-44** | Cross-carrier ceiling decomposition | 08-25 | A2T-G1-104 vs SLURP unexposed 500 | reachable share **14.42 %** vs **32.00 %** (2.2187×); within-reach conversion **+13.3333 pp** vs **+59.3750 pp** (4.4531×) | n.m. | the reachable share **is** the delivery rate | ESTABLISHED: reach × conversion = **+1.9231 pp** vs **+19.0000 pp**, and **both decompositions close exactly**. Nothing is left over for "the method is weaker on Audio2Tool" as a separate hypothesis. Retain-subgroup drift differs in sign (−0.9615 vs +1.6000 pp) | R-XC · `decomposition/cross_carrier/*`, `closes_exactly*` |
| **C-45** | Cross-carrier query-key degeneracy | 08-25 | A2T-G1-104 + both SLURP halves | n.m. | A2T dead-direct distinct query vectors per trajectory **0.3333** against label-recovered 0.9438; SLURP dead-direct **0.850** (unexposed) and **0.735** (exposed) | n.a. | ESTABLISHED: **the constant retrieval key is an Audio2Tool pathology, not a general one.** The A2T control reproduced the landed diagnosis (`control_reproduced` = true). SLURP's keys repeat because short labels collide — benign, and it happens more in its *healthy* subgroup | R-DEGEN · `a2t_control/*`, `slurp/halves/*` |
| **C-46** | Field-level supply accounting — the delivery rates | 08-25 | SLURP DEV-1000-NEW500 + A2T-G1-104 | n.m. | n.m. | **SLURP 163 / 500 = 32.60 %**; **A2T 15 / 104 = 14.42 %** | ESTABLISHED and load-bearing for this whole document: "received supply" and "was dispatched" are the same set on both carriers, proved rather than assumed. Its per-field TOKEN estimates are **not** carried — see §5.4 | R-FIELD · `channel_cost/*/two_rate/delivery/*` |
| **C-47** | Matching-versus-extraction read — the population two-axis table | 08-25 | both carriers, both SLURP halves | see C-32, C-33, C-38 | see C-32, C-33, C-38 | not stated by this read | **PARTLY SUPERSEDED.** Its population two-axis table stands and is the source of the extraction columns above; its fidelity gate passed and its four-cell arithmetic closes exactly. Its **CONDITIONED verdict** — "conditioned on matching, the supply does not serve extraction" — was **SUPERSEDED by `6c6ec719`** (C-48): the conditioned cell held **3 dispatched of 273** on the unexposed half, **2 of 255** on the exposed half and **0 of 60** on Audio2Tool, so it was measured where no supply was ever delivered | R-MVE · `two_axis_scoreboard/*`, `fidelity_gate/pass`, `…/joint_decomposition_…/*` |
| **C-48** | Extraction conditioned on DISPATCH — the supersession | 08-25 | SLURP both halves + A2T | see C-34, C-35 | see C-34, C-36, C-37 | the conditioning variable itself | **THIS SUPERSEDES C-47's conditioned verdict.** It reproduces C-47's arithmetic to the digit before challenging its interpretation; the (a)-dominance finding survives untouched. The correction is to the *reading of the residual*, not to any earlier number | R-ECD · `slurp/*/cross_tabulation/cells/both_matched/dispatched_n`, `a2t/…` |
| **C-49** | Prior-score semantics repair | 08-25 | both carriers' pinned snapshots | n.m. | n.m. | n.a. | ESTABLISHED as a CORRECTNESS repair: the pinned A2T snapshot's `prior_score` supremum was **4.1** with **193** recorded range violations; post-repair 12,237 of 12,601 values move and 364 are unchanged, **the supply is byte-identical on 104 / 104 trajectories**, and every pinned artifact is unchanged. The landed fidelity gate reproduced supply and dispatch **104 / 104** each | R-PRIOR · `range_contract_on_the_pinned_snapshot/*`, `a2t_prior_before_after/*`, `corrected_prior_supply_replay/*`, `landed_fidelity_gate/*` |
| **C-50** | SLURP intent-coverage check | 08-25 | SLURP TRAIN snapshot + DEV-1000 | n.m. | n.m. | n.a. | ESTABLISHED: the KB models **60 of 60** task intents; `intent_coverage` = 1.0 landed and recomputes to 1.0, and is **1.0 by construction** (its denominator is the loaded TRAIN rows). **0** DEV-1000 samples and **0** unexposed-500 samples carry an unmodeled intent. The "91 intents" docstring was an aliasing artifact — 91 is the raw `intent` field, 60 is the scenario/action vocabulary | R-INTENT · `q2_snapshot_models/*`, `q4_coverage_denominator/*`, `q5_consequence/*` |
| **C-51** | Can-it-fail gate audit | 08-25 | the repository's own gates | n.m. | n.m. | n.a. | ESTABLISHED: **140 mutations recorded, 112 live — 69 FIRES, 23 DID-NOT-FIRE, 20 correct controls**, at 0 outbound connection attempts. At GATE granularity (tier D, D-GATES): **of the 43 gates in scope, 23 FIRE, 10 CANNOT FAIL, 9 are NARROWER THAN THEIR CLAIM, 1 is UNTESTED.** The two tallies count different things and must not be conflated | R-GATEAUDIT · `mutation_tally_live/*`, `mutations_*`; D-GATES · the 43-gate sentence |
| **C-52** | `content_facet_target` correctness audit | 08-25 | both carriers' pinned snapshots | n.m. | n.m. | n.a. | ESTABLISHED: the name asserts a content restriction the code does not apply, on both carriers; the live consequence is **two descriptive Audio2Tool numbers** and nothing that gates a decision. Diagnosis only — no repair proposed, no behaviour changed | R-FACET (digest verified; figures carried in the audit document itself) |
| **C-53** | Stage-2A matured synthesis | 08-25 | the twelve receipts it reads | n.m. | n.m. | n.a. | ESTABLISHED as the reviewer-facing synthesis: **332 receipt-field claims verified, 12 receipts SHA-256-verified, 0 outbound connection attempts.** This scoreboard and that synthesis agree by construction — both re-read the same receipts, neither restates the other | R-SYNTH · `claims_verified`, `receipts_verified`, `offline_guard/*` |
| **C-54** | α-trade decision sizing (open owner decision D1) | 08-26 | SLURP DEV-1000-NEW500 (unexposed) + A2T-G1-104 (exposed) | **PROJECTION, not a measurement.** Moving α 0.45 → 0.50 on the unexposed 500 projects **−3.4109 pp central**, band **[−3.5826, −0.0109]** against the locked cell's 382/500. The block's own rule travels with it: *"these bands are decision-sizing arithmetic, not a forecast, and no single number from this block may be quoted as an expected accuracy"* | n.m. | control **160 / 500 = 32.00 %** (locked v1) → **184 / 500 = 36.80 %** at α 0.50; on Audio2Tool the same step adds only **2** trajectories to a control of 15 | SIZES an owner decision and takes none; recommends no value of α and authorizes no change. Two measured facts do the work: at α = 0.50 the guaranteed margin `1 − 2α` is **0.0000** and the worst case is an exact tie the controller dispatches on — α is a switch, not a dial; and of the **24** newly dispatching trajectories, **20 are already correct under the locked cell** and **all 20** would receive a supply that **omits** gold, against **3** of the 24 that would receive a gold-bearing supply. Carries the X-06 adverse prior explicitly | R-ALPHA · `populations/*/by_alpha/0.50/*`, `registered_constants/control_alpha` |

---

## 3. Table B — refusals and closed directions

A direction refused at zero cost is a result. Each row names the measurement that refused it, not an
opinion. Row ids are stable and append-only.

| id | direction | what it proposed | what refused it (measured) | cost | provenance |
|---|---|---|---|---|---|
| **X-01** | **E-C** — schema-constrained contact 0 | force a legal label at contact 0 so the direct term is always live | **It is an off-switch.** Projected evidence contacts collapse **37 → 0** (DEV-100 r4), **33 → 0** (r5), **130 → 0** (NEW400): retain-primary fires on 100 % of the dead-direct set because the protect-direct constant dominates. Projected accuracy change vs sealed **−18 … −5** on r4. Conclusion as landed: "E-C should not be flown as briefed" | **zero contacts** — refused by offline projection | D-EC · the contact-collapse table and the projected-change band |
| **X-02** | **E-A** — contrast few-shot | supply contrastive exemplars around the fused top-2 to convert confusable siblings | **The briefed trigger is degenerate** (the fused top-2 margin is bimodal; every threshold in [0.10, 0.90] selects the identical set), and **E-A cannot be evaluated on DEV-100** — its whole credible band sits inside the documented ±2 byte-variance channel. Retained as a DEV-500-tier experiment with a cosine-margin trigger; never a DEV-100 round | **zero contacts** — refused by model-free pre-analysis | D-KWIDEN · the two verbatim findings |
| **X-03** | **K-WIDEN K1** — retrieval width 5 → 8 | widen recall so the deeper gold facet becomes reachable | **Width is inert.** 71/100 against a base of 72 (Δ −1, inside the ±2 channel); the offline replay changed the admitted supply on **32 / 100** trajectories and produced **0 width-attributable flips**. Structural reason: `fusion_c 2 × top_l 3 = 6` binds first and is m-invariant | flown once: 139 core contacts, 0.083 GPU-h | R-KWIDEN · `kwiden_reconciliation/width_attributable_flip_count`, `stopping_rule_status/*` |
| **X-04** | **K-WIDEN K2** — width 16 / 32 | the next rungs of the width ladder | Refused *before* flight on K1's evidence: **"K2 at 16/32 is NOT recommended as a width-only move"**, stopping rule **CONVERGED-OR-FALSIFIED for width at this tier**. The binding lever is the `c`/`top_l` supply budget, and beyond it key construction | **zero contacts** | D-KWIDEN · the K2 sentence and the stopping rule |
| **X-05** | **K1 hybrid ranking — RRF-60** | fuse a BM25 lexical channel with the dense channel by reciprocal-rank fusion | **It buys recall@5 by selling recall@1.** Gold-facet recall@5 **0.744 → 0.762** (+9 samples) while recall@1 **0.636 → 0.590** (318 → 295, −23). Under the campaign's own steeply rank-dependent conversion anchors, 23 demotions against 9 promotions does not close. The gate's own falsifier verdict is RAISED — the *hypothesis* survives, the *flight* was refused | **zero contacts** — offline gate | R-K1GATE · `recall_table/DENSE-ONLY/*`, `recall_table/RRF-60/*`, `falsifier/verdict` |
| **X-06** | **δ ≥ 0.14 retain-override** | dispatch anyway when the retrieval-preference margin is large; registered property "zero loss by construction" | **Falsified out of sample.** 14 fires on DEV-1000: on the prior-exposed half **11 fires, 11 recovered, 0 damaged**; on the unexposed half **3 fires, 0 recovered, 3 damaged**. The receipt records `zero_loss_property_held` = **false**. Removed from the locked cell; without it the same population reads **+20.80 pp** | flown at DEV-100 (C-30) and inside the DEV-1000 v2 arm | R-LOCK · `secondaries/override_subgroup/*`; R-XC · `…/locked_v1_*` |
| **X-07** | **K3** — repair the Audio2Tool answer to repair the query | improve the contact-0 answer so the retrieval key stops being a constant | **Its own carve-out preserves 1 of the 15.** Projected dispatch falls **15/104 → 3/104** (−80 % relative) on the arm that measures actual form repair. Any fix that improves the query by improving the ANSWER recovers a direct label, and the α veto then suppresses dispatch one-for-one | **zero contacts** | R-GOLD · `k3_dispatch_projection/projection_upper_bound_on_repair/flown_dispatch_count`, `projected_dispatch_count`, `projected_dispatch_rate_change_pp` |
| **X-08** | **Fusion form C1** — cosine-only facet ranking | remove the incommensurable prior and agreement terms from the ranker score | **REFUSED — NO MEASURABLE GAIN**: an exact identity on every measured quantity on every population; **0** of the 500 unexposed decisions change. Expressly *not* the same verdict as HARMFUL. Predicted in advance by the ranker's own proof that every percept-admissible content facet already outranks every prior-mass facet | **zero contacts** | R-FUSION · `verdict_by_form/C1/*` |
| **X-09** | **Fusion form C2** — prior as a multiplicative label prior | move the prior to the layer where it is already a probability (Bayes / Tip-Adapter shape) | **REFUSED — NO MEASURABLE GAIN**: exact identity, **0** unexposed decisions changed | **zero contacts** | R-FUSION · `verdict_by_form/C2/*` |
| **X-10** | **Fusion form C2B** — kNN-LM interpolation, λ ∈ {0.10, 0.25, 0.50} | interpolate the retrieval distribution against the prior distribution | **REFUSED — NO MEASURABLE GAIN** at every λ: exact identity, **0** unexposed decisions changed. It also introduces a knob that is not in the frozen table | **zero contacts** | R-FUSION · `verdict_by_form/C2B-0.25/*` (0.10 and 0.50 identical) |
| **X-11** | **Fusion form C3** — RRF across dimensions at K = 60 | the literature's third answer to incommensurability | **REFUSED on EVERY population**, failing F1, F2, F3 and F5 — and it moves **199 of the 500 unexposed decisions**, which alone bars a recommendation on offline evidence | **zero contacts** | R-FUSION · `verdict_by_form/C3/*` |
| **X-12** | **External AgentLoop controllers M5-v2 … M9, and M11** | a training-free controller choosing between retain-primary and accept-refined | Every generation missed its pre-registered bar on a near-ceiling surface, and the landed plan **"rejects the current AgentLoop controller"**. M11's own support gate then failed **6 of 8 conjuncts** and the controller was deferred unevaluated (C-21). Diagnosis: saturated surface plus sparse action support | flown (train-only discovery) | D-SN · the rejection sentence; D-E108 · the gate outcome |
| **X-13** | **P-EMB-4R C-DECODE arm** | decoder-joint speech-feature × text-key matching inside the 4R probe | **Canceled by the owner before the read; zero contacts made.** The question it would have asked was answered instead by EFFECT-C108 (C-20) | **zero contacts** | R-PEMB4R · `verdict/c_decode_status` |
| **X-14** | **Independent pooled audio embedding / kNN as the main routing method** | replace decode routing with an embedding-space nearest-neighbour lookup | Refuted at four independent cells (C-14, C-15, C-16, C-17) and only partially rescued at C-18: the best audio arm reaches **0.3167** against direct speech classification at **0.8167**. The blanket "content-absent" claim is itself disproved — the refusal is about *sufficiency*, not about absence | flown across four probes | R-PEMB1/2/3L/3M/4R · as cited in Table A |

---

## 4. Mechanism consistency — which rows support each mechanism

The consistency bar for declaring the scheme (owner's goal condition) is: each load-bearing
mechanism supported by **≥ 2 independent cells agreeing in sign**, and the composed scheme
demonstrated end-to-end on at least two carriers with positive net signed accounts.

| mechanism | consistent? | supporting rows |
|---|---|---|
| Label-space / structure supply helps | ✅ 4 cells | C-01, C-02, C-06, C-07 |
| Wrong-content supply is inert with drift, not an attractor | ✅ 3 cells | C-06 (B2), C-08, C-05 |
| The value-copy channel is cut by stripping and re-opened by augmenting | ✅ 2 cells | C-06, C-07 |
| Self-percept resonance captures the decode | ✅ 1 cell + 1 sign-flipped confirmation | C-12, C-19 |
| Blind supply regresses already-correct answers | ✅ 1 cell, superseded as a *problem* by percept-keying | C-10 → C-19 |
| Closed-set decode routing is the routing tier's working lever | ✅ 2 cells | C-02, C-11 |
| Independent pooled audio embedding is insufficient (not content-absent) | ✅ 5 cells | C-14, C-15, C-16, C-17, C-18 |
| Speech-native decoder-joint matching beats direct decode on the discovery split | ⚠️ 1 cell, and its speech-sensitivity threshold FAILED | C-20 |
| External controllers do not clear their bars on a saturated surface | ✅ 6 generations | C-21, X-12 |
| Knowledge-conditioned decode raises MATCHING at DEV tier | ✅ 4 tiers, monotone and scale-stable | C-22…C-27, C-31, C-32 |
| The gain is attributable to the retrieval SIGNAL, not to a second contact or a prompt shape | ✅ 1 four-arm ablation | C-31 |
| Where evidence is delivered, EXTRACTION moves too | ⚠️ 1 population (unexposed), and it does **not** replicate on the exposed half | C-34, C-36, C-37 |
| Retrieval width is not the lever | ✅ 2 cells | C-29, X-03 |
| The Audio2Tool ceiling is DISCRIMINATION under a degenerate query | ✅ 4 refusals by measurement | C-42, C-43, C-45, X-07 |
| Reach × conversion accounts for the whole cross-carrier gap | ✅ 1 decomposition, closes exactly on both | C-44 |

---

## 5. Could not verify — omitted rather than carried

Listed so their absence is visible rather than inferred. Each is a quantity a landed document
carries and this scoreboard declines to carry, or an empty cell above with its reason.

1. **The EFFECT-C108 read artifact itself (row C-20).** The replacement read wrote its output under
   `SPEECHRL_DATA_DIR`, outside Git; only its SHA-256 `6f7017fb…f40a` is landed, inside D-SN. This
   row's numbers are therefore **tier D** — verified as verbatim sentences of a hashed document, not
   as JSON fields. The same applies to the M5-v2 … M9 controller results (X-12).
2. **Every population-level EXTRACTION interval (rows C-32, C-33, C-38).** No receipt publishes a
   bootstrap interval for the extraction axis at population level on either carrier; the intervals
   that exist are the delivery-conditioned ones of C-34, C-36, C-39, C-40. Those population cells
   carry a point difference and no interval, and say so.
3. **The DEV-100 rounds' EXTRACTION axis (rows C-22 … C-30).** The six round reports and the two
   variant rounds publish `accuracy_scenario_action_exact` only. No slot-F1 or SLU-F1 field exists
   in them; the cells are left empty rather than back-filled from a later population's number.
4. **Every per-field-group TOKEN figure in the field-level accounting (row C-46).** They are
   estimates from a character-to-token model published under two competing models with their own
   calibration error, and that row refuses a per-group rate for collinearity. Only its delivery
   COUNTS are carried.
5. **Every campaign spend figure** — core contacts, metered audio seconds, tool contacts. These live
   in the AttemptStore outside Git; this row opened no run directory or attempt store. Nothing here
   is a spend claim.
6. **The `content_facet_target` audit's own counts (row C-52).** The receipt digest is verified and
   the row's *conclusion* is carried; the individual counts live in the audit document and are not
   re-declared here, because no other row depends on them.
7. **Any cross-carrier "the A2T deficit is N× the SLURP deficit" ratio.** Those are arithmetic over
   other fields, computed against a SLURP side quoted from a plan rather than a receipt. The
   per-group rates are carried instead, in C-45.
8. **The DEV-100 A4 and K-WIDEN K1 *extraction* effect.** Both variant rounds published only the
   matching metric, so neither X-03 nor X-06 can say what the change did to extraction. Their
   refusals rest on the matching axis and on the mechanism replay alone, and say so.
9. **Any interval on the two delivery rates themselves.** 163/500 and 15/104 are counts on one
   flight each; no receipt resamples them, and this document treats them as descriptive of those
   flights rather than as estimates of a dispatch rate.

---

## 6. Disagreements found between landed documents, and what settled each

| disagreement | settled by | outcome |
|---|---|---|
| **v4 of this scoreboard** said the EFFECT-C108 speech-swap control sat *"above the frozen 24-gap mechanism bar, so speech sensitivity is established at the weaker tier"*. | **D-SN**, verbatim: *"Matched M6 exceeds speech-swap by 14/108, below the frozen 24 threshold, and exceeds key-text-shuffle by 89/108, above the frozen 18 threshold."* | **v4 was wrong.** The speech-sensitivity threshold **FAILED** (14 < 24); only the key-shuffle threshold passed (89 ≥ 18). Row C-20 states it as measured. The key-load-bearing claim is unaffected; the speech-sensitivity claim is withdrawn to "not established at the registered bar". |
| The conditioned extraction verdict. `d4c75c7a` concluded the supply does not serve extraction; `6c6ec719` concluded it does where delivered. | **R-ECD** · `slurp/unexposed500/cross_tabulation/cells/both_matched/dispatched_n` = **3** of 273; exposed half **2** of 255; A2T **0** of 60 | Not an arithmetic conflict — R-ECD reproduces R-MVE's cell contributions exactly. The landed conditioned cell held trajectories that received no evidence at all, so it could not have shown a supply effect. C-47 carries the supersession; the superseded reading is not carried forward. |
| The Audio2Tool oracle receipt's digest. The first execution-facts paragraph in `docs/exposure-ledger.md` records `8fc0641b…`; the verdict document and the successor ledger paragraph record `b564362b…`. | **The file itself**: `…/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json` hashes to **`b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723`** | The first digest is pre-correction (`274ce62a` re-measured the decontamination claim instead of asserting it) and is stale where it stands; the ledger already carries the successor. §1 pins the live digest. |
| The gate audit's tally: the receipt publishes **69 FIRES / 23 DID-NOT-FIRE / 20 controls** over 112 live mutations; the document says **23 FIRE / 10 CANNOT FAIL / 9 NARROWER / 1 UNTESTED** over 43 gates. | Both, read at their own granularity: **R-GATEAUDIT** counts MUTATIONS, **D-GATES** counts GATES | Not a disagreement — two granularities. C-51 carries both and says which is which, so neither can be quoted as the other. |
| The SLURP knowledge builder's docstring said "91 intents"; the KB models 60. | **R-INTENT** · `docstring_claim_under_test/measured_train_intents_intent_field` = 91, `…_scenario_action` = **60** | Both numbers are real: 91 is the raw `intent` field's cardinality, 60 is the scenario/action vocabulary the task is scored on. The docstring was corrected at `aaa59792`; C-50 states both. |

---

## 7. Where the scheme stands (v5 statement)

**Established.** On SLURP slot-SLU, a knowledge-conditioned two-contact decode with an α-blend
consumption rule raises MATCHING by **+20.20 pp, CI90 [+17.20, +23.40]**, on **500 unexposed**
samples, at W→C 106 / C→W 5 (C-32). The effect is **scale-stable** across DEV-500 → DEV-1000 on
disjoint held-out data, and a four-arm ablation attributes it to the **retrieval signal** rather
than to the second contact or to any prompt shape — generic exemplars actively hurt (C-31). Where
supply is actually delivered (163 of 500), the gain operates on **both** axes, and it still moves
extraction in the matching-free cell where no matching movement can explain it (C-34, C-36).

**Not established.** The Audio2Tool population delta is **not separated from zero** on either axis
(C-38), and its dispatched-stratum extraction sign is positive but its interval touches zero at
n = 15 (C-39). The supply-attributable extraction term **does not replicate on the prior-exposed
half** of the same carrier, same policy cell, same flight (C-37) — the single strongest caution on
the extraction result. No generality claim, no superiority claim, and no cross-carrier transfer
claim follows from anything above.

**Where the limit is.** On Audio2Tool, four candidate explanations were each refused by measurement
rather than argued away: KB coverage (C-42), retrieval width and depth (C-42, X-03), the τ percept
gate (C-43), and a hand-fit dispatch override (X-06). What stands is **discrimination under a
degenerate query** (C-45), and the oracle bound shows the cell is not the ceiling while naming no
legal fix (C-43).

**Speech-native status.** The strongest speech-native evidence remains EFFECT-C108's decoder-joint
matching, **90/108 against a direct-decode 77/108** on a train-only discovery split, with the keys
proved load-bearing by a shuffle that collapses to 0/108 (C-20) — **but its registered
speech-sensitivity threshold failed** (§6), so speech sensitivity is *not* established at the bar
that was set for it. Independent pooled audio embedding is insufficient as a routing method and is
not content-absent (C-18). The cascade route is strong and **text-mediated, therefore not
speech-native** (C-17).

---

## 8. Hard stop — what this document does not do

This is a consolidation over landed evidence at **zero contacts**. It authorizes **nothing to fly**,
changes **no knob**, revises **no lock** (every SLURP unexposed-500 statistic here is a SECONDARY
reading on the locked baseline's own population and `SAEA-DEV1000-BASELINE-LOCK` stands exactly as
landed at `d9fef537`), makes **no claim** beyond the two already-read populations, opens **no new
agenda item**, makes **no test contact** (FINAL60 stays reserved), and performs **no Stage-3
activity** of any kind. `consumed` stays **no**: no seal is broken and no split is newly opened.
