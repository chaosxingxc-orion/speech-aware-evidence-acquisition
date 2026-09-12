# STATUS-066: Audio2Tool sealed; frozen analysis running

Snapshot UTC: 2026-09-12T18:22:42.032878+00:00. This turn closed a real metadata-interface mismatch and
advanced the complete Audio2Tool recovery into its registered saved-score analysis.
The broad system goal remains active.

## Completed generation and scoring

DIRECT, STAGE-CONTROL and KNOWLEDGE are all FINALIZED with COMPLETED manifests and
hash-bound first complete scores. Counts are 4000, 8000 and 8000 generation calls on the
same 4000-row roster. Campaign PID 2179 exited successfully. No restart or rescoring
was used. The root Qwen service PID 620 and 10-second monitor PID 678 remain resident.

The last generation contact count reached 8000 before final packing. The trace file
continued growing during I/O sealing; this was live progress, not a dead process.
Record this seal tail separately from model generation.

## Metadata repair and registered analysis

Original outcome-free metadata f4eeb0f5c548b15ab65e8137d134ee4b17bcebfa402eb71dcda6aa64198a5c70
stored integer query_idx values, but frozen pooled_ratio_compare requires text.
A prospectively registered derivative changes only those integers to exact decimal
text. All 4000 IDs, 2097 cluster memberships and eight tiers of 500 remain identical.
The frozen shared interface accepted the full derivative with synthetic constant
score fields. Original metadata and estimator bytes remain unchanged.

New metadata: DATA prepared/SAEA-A2T-NATIVE-SYSTEM-ANALYSIS-METADATA-TEXT-V1/metadata.json,
SHA256 f9afc5b715ead7ec809a6ec2844605b8ebf7eeae2f614d60b146c5d7d3b7e1fa.

Actual read registration is committed at 7e51daf96f801b5f54d65060e15ffe202bfa8f4c.
The bound config SHA256 is 81287fc2864bbd4ad894d90c25c44735e79cb1f48cdf2a7e21efc1f7fcb52835.
Only metadata/input bindings were added to the original statistical recipe.
Its old prospective status string remains historical; the committed registration
and root release establish present read authority.

Analysis PID 28696 runs frozen source 5f79d399dc15016aaeedccac347aebffddfc61ca.
All-source bundle verification completed before its five bootstrap workers began.
Two primary-contrast workers have completed their assigned computation; the three
multi-metric comparison workers remain active. The final output is not yet sealed.
Do not change this live source, rerun scorers or report unfinished intervals.

## Checked points; final interval verdict pending

Root checked 90 native/equal-tier/tier arithmetic points against first-score
aggregates and the independent per-sample calculation. No mismatch exceeded 1e-9 pp.

| Metric | Direct | Stage control | Knowledge | Published equal-tier reference |
|---|---:|---:|---:|---:|
| Official exact match percent | 18.900 | 17.950 | 18.600 | 29.675 |
| Tool accuracy percent | 62.025 | 60.525 | 58.550 | 69.1875 |
| Macro parameter F1 percent | 30.290774 | 29.117917 | 30.719464 | Not in the pinned reference row |
| Parse failures | 24 | 22 | 77 | Not in the pinned reference row |

Published references are the unweighted means of eight Table 3 rows in the frozen
a2t_v2_rescore.PAPER_TIER_ROW. They are context, not a matched model/population
control or proof of the cause of a reproduction gap.

Natural and equal-tier points coincide on this balanced roster. Knowledge-minus-
direct exact match is -0.300 pp; knowledge-minus-stage-control is +0.650 pp.
Keep complete tier/domain tables in the independent receipt. These points do not
supply unfinished confidence intervals or a positive mechanism claim.

The system-promise declaration and knowledge-contribution declaration are separate.
The former requires the knowledge-minus-direct exact-match threshold and tool/F1
point guards; it does not require the stage-control contrast to pass. Do not add
the whole-system point guards to the separate knowledge-contribution rule.

## Source-backed delivery diagnostic

Compared with stage control, knowledge has 67 new parse failures and 12 recovered
parses, giving 55 net additional failures. There are 178 tool-correctness harms and
99 saves. Of those harms, 44 move from correct to unparsed and 134 remain parsed
but wrong. Parse-associated rows account for 44 of 79 net lost tool-correct rows;
the remaining net 35 are parser-recognized choices. This is an accounting partition,
not a causal proof or permission to revise sealed outputs.

All final outputs are nonempty, admitted and end with stop; no final length
saturation is recorded. Retry count and finer causes are unsupported by retained
fields, not established as zero. The analysis uses allowlisted scored fields and
legal output metadata; saved score bytes contain other reference-derived fields,
so do not claim those files themselves are gold-free.

## GPU and next dispatch

At resident idle the GPU reports 0 percent utilization, roughly 5.6 W and 180 MHz SM,
with the software power-cap reason inactive. Under load that reason had been
active. This narrows the condition to load but does not identify its root cause.
No power, driver or performance settings were changed.

Wait for the original full analysis, write the root scientific decision and then
follow the frozen Whisper preparation registration. No actual Whisper forward
or answering-pair generation has begun. Keep the registered 1000-source catalog
preparation and matched SLURP plan/solve/revise pair as the next queue.

Evidence index: docs/readiness/2026-09-12-a2t-native-system-postseal-progress-v1.json.
