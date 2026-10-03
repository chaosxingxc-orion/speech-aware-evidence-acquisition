# Fixed400 context20 recovery: root complete-system read

Recorded: 2026-10-03T02:46:05.070976+00:00

Status: EXPLORATORY-FIXED-POOL-NO-ADOPTION. All four independently finalized20 rows with verified seals, exactly one successful complete official score each and zero failed score jobs. Root countersigned the exact new READ before loading scientific feedback. The driver completed normally; no recovery, regeneration or score replay occurred. The malformed prior family remains preserved and unread.

| Member | Official SLU-F1 | Intent | Reliable completion | Model contacts | Tool calls |
|---|---:|---:|---:|---:|---:|
| Seed | 58.3942% | 70.00% | 100.00% | 125 | 0 |
| Seed A/A | 55.1724% | 70.00% | 100.00% | 131 | 0 |
| Planner text | 60.9298% | 70.00% | 100.00% | 128 | 0 |
| Solver text | 57.0846% | 70.00% | 100.00% | 131 | 0 |

| Complete-system contrast | SLU-F1 difference, pp | Paired95% interval, pp |
|---|---:|---:|
| same-request-null | -3.2217 | [-10.2564, +0.0000] |
| candidate-1-minus-parent | +2.5356 | [-0.1701, +9.0435] |
| candidate-1-minus-aa | +5.7574 | [+0.0000, +16.5778] |
| candidate-2-minus-parent | -1.3096 | [-10.8803, +9.5238] |
| candidate-2-minus-aa | +1.9122 | [-8.3413, +14.0333] |

All twenty utterance clusters are paired in10,000 bootstrap draws, seed20261001. These small-sample intervals describe this retained-exposure panel. Planner improves the point estimate by2.5356pp over seed, but that interval includes zero. Its13-stratum table shows a difference only in the single social-stratum case; no new whole-answer exact repair occurs. Solver is1.3096pp below seed and exchanges one exact repair for one damaged previously correct answer. All four deliver8/20 whole-answer exact cases. No result establishes stable benefit or feedback-learning advantage.

| Member | Solver visits | Non-strict raw task JSON | Text tool markers | Valid Reviewer handoffs | Non-slot findings / all findings | Handoffs visible in next Planner | Extra revisions | Changed first-to-last text |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Seed | 35 | 2 | 2 | 35/35 | 2/45 | 35/35 | 15 | 2 |
| Seed A/A | 37 | 3 | 3 | 37/37 | 2/55 | 37/37 | 17 | 5 |
| Planner text | 36 | 4 | 4 | 36/36 | 6/52 | 36/36 | 16 | 4 |
| Solver text | 37 | 8 | 3 | 37/37 | 2/44 | 37/37 | 17 | 6 |

All145 valid handoffs are visible in actual next Planner context, reproducing the prior complete-pilot transmission finding. Correct transmission and syntax do not establish correct criticism or semantic use. Twelve of196 findings contain non-slot identifiers. The Solver candidate has3 textual tool-call markers and5 Markdown-fenced raw replies; seed has2 textual markers. These are non-strict intermediate responses under the existing task contract, not executed tools or proof that every final output failed. Existing finite completion and answer normalization remain unchanged. No historical textual call is executed or reinterpreted.

The Planner candidate adds3 contacts over seed and the Solver candidate adds6. Prompt/completion token counts below come from role-level request traces. Duration is unmeasured in this derivative and must not be inferred from serving totals. Context/token costs and repeated revisions are optimization targets, but no node causal credit is claimed.

| Member | Prompt tokens | Completion tokens | Solver / Reviewer / Planner visits |
|---|---:|---:|---|
| Seed | 1,245,271 | 9,254 | 35 / 35 / 35 |
| Seed A/A | 1,256,315 | 9,822 | 37 / 37 / 37 |
| Planner text | 1,265,262 | 9,974 | 36 / 36 / 36 |
| Solver text | 1,280,501 | 9,063 | 37 / 37 / 37 |

Every stratum is retained below. Entries are official SLU-F1 / intent percent. Tiny supports are descriptive. The macro averages13 within-stratum values and does not replace the pooled official score.

| Stratum | n | Seed | A/A | Planner text | Solver text |
|---|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 40.00 / 100.00 |
| qa | 2 | 58.54 / 100.00 | 58.54 / 100.00 | 58.54 / 100.00 | 58.54 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 0.00 / 0.00 | 0.00 / 0.00 | 51.85 / 0.00 | 41.79 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |
| Equal-stratum macro | 13 | 41.68 / 70.51 | 41.68 / 70.51 | 45.67 / 70.51 | 42.85 / 70.51 |

Root next-stage disposition: keep seed as the formal parent; keep seed and Planner on this same-cohort descriptive quality/contact-cost frontier. Do not combine earlier pilot or later-scale scores into this frontier. Retain all other history, including the losing Solver variant. The major raw-output and criticism-targeting defects remain, so stay at20 for prospective repairs before registering50. The prepared8x50/8x100/8x200 bases are ready but remain HELD. Each new stage needs actual policy freeze, complete-family registration, request FIT and structural proof, then root review. No automatic8x400.

Prepare any extra proposal allocations prospectively under owner223, without replacing the original twelve spent allocations. Use the admitted exact GPT6 provider, independently auditable branch inputs and unchanged proposal budgets. L may consume separately qualified L-only feedback; B must start independently from the original seed and receive no scores, selected winner or root diagnosis. This four-member comparison does not grant optimizer export. Preserve cumulative exposure in the same400 pool; this is optimization, not independent validation.

Preserve existing knowledge, media, packets, query vectors, votes, tools, scorer and Omni answer authority. Text revisions should address useful concrete criticism, role-local output instructions and explicit revision handoff. A decoder/schema or new post-call normalization mechanism must be separately specified, registered and structurally verified before contact; do not silently alter this frozen comparison or interpret formatting gains as task gains. Other carriers retain their holds.

Evidence: [operational qualification](../receipts/continuation/2026-10-03-owner225-context20-family-qualified.json), [scientific receipt](../receipts/continuation/2026-10-03-owner225-context20-scientific-read.json), and external `analysis/SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-RECOVERY1-READ-V1/` under the data root. No raw answers or traces are committed.
