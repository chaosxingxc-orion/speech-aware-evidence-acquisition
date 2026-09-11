# Status037: SLURP first; 2026 optimizer source review closed

Date: 2026-09-11T13:57:17.947323+00:00. Source inspected: d1ac910cfab20e4f04cff8b31b96d2e72c7dc816. Progress: owner routing updated, 2026 implementation review and saved SLURP headroom audit complete. The original goal remains active. No new GPU experiment was generated during this review.

## Current direction

Read OWNER-SLURP-FIRST-2026-RL-015 first. Lock the shared engineering baseline on SLURP, then extend to E21 and E22. Preserve OWNER014: quality, interpretable component effects and optimization headroom matter; no large present gain or cost penalty is required. E22 is a later owner-named destination, not an immediate admitted flight.

The new root-reviewed plan is docs/readiness/2026-09-11-slurp-first-system-and-training-free-rl-plan.md. It supersedes the E21-first proposal in STATUS-036. Prior system verdicts and closed attempts remain unchanged.

## Completed this boundary

- Official-source review: TF-GRPO (2025 baseline), MemRL, JitRL, ETS, EvoTool, MemQ and SkillOpt. Seven full code commits and inspection receipts are pinned by docs/readiness/2026-09-11-training-free-rl-2026-source-index.json. No upstream installation/import/execution/model contact. Root personally reviewed update and acceptance code.
- Prioritize EvoTool-style targeted module evolution as the first 2026 system-level candidate after the shared TF-GRPO baseline; MemRL is a narrow memory-utility RL comparator. MemQ is later structural credit. JitRL's released probability-plus-advantage argmax differs from the paper logit formula; SkillOpt's default slow update can bypass validation. These are not drop-in admitted packages.
- Reuse saved SLURP scores without rescoring. NEW500 retrieval wins46, declines35, ties419; mean row-F1 +1.0187pp. Retrospective per-item max-of-two is +5.3707pp above control / +4.3520pp above retrieval. This is descriptive output complementarity including generation noise, not deployable-policy headroom. Existing aggregate same-intent counts do not provide a per-row conditioning mask. Receipt DATA coordination/slurp-existing-pair-headroom-audit-v1.json SHA96ab7d24fb30e55ff771fc16e6d6f73b00ff601b8b2f2478ffd67e7f100373bf.
- Source audit found the precise missing seam: current phase_supply is static per run. Add a registered per-row supply-action policy at EvidenceAgentController.advance after current state seal, selecting existing retrieval or explicit no retrieval while always proceeding to slots. Current phase_planner only controls early exit and cannot represent this action.
- Documentation and coordination changes only; the new action seam, optimizer runtime and GPU feedback cohort are not implemented or dispatched yet.

## Prior completed cohort

All four E21/SLURP attempts are FINALIZED. Complete official scores ran once, fixed analysis and verdicts closed. See STATUS-036 and unchanged September11 result reports.

E21 PERSON23.1402% ->19.7463%; WER8.12086% ->8.07499%; insertions+5 fail the historical guard. SLURP program-matched NEW500 mean row-F1+1.0187pp CI90[-0.9059,2.8329], intent-0.2pp fails historical admission. These do not veto a useful engineering baseline under OWNER014, nor become positive superiority claims.

OWNER011's single pair remains closed; no further repeat. S4N's failed non-inferiority keeps missing exemplar encoding and a/b/c held. Existing DR/LOOP/replications are complete. E21 live review/selected observation is a later explicit gap. Summaries remain feasibility under native task metrics.

## Service and next work

Process snapshot during this boundary: wrapper35765, llama-server35780 and monitor35824 alive at approximately1h57m elapsed. Resident ID serving-slurp-live-program-matched-np4-v1, frozen source21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff, no-mmproj prepared decoder, c65536/np4/max256. This snapshot is not current endpoint qualification. No new model contact was made. Root owns service; no worker was dispatched.

Next implement the one shared supply-action seam and legal decision binding, then prepare the prospectively fixed action groups and update/validation/evaluation roles. Run model-free meaningful tests in WSL. Register exact contacts/fit/budget before the first new GPU cohort; do not recycle old attempts. Reuse the resident geometry and overlap preparation/scoring within existing global limits. Freeze policy before evaluation; never expose references or offline gold to runtime.

Lock engineering when config plus shared entry reproduces real action choices, sealed reward/update/freeze and a full feedback cycle. Do not wait for large SLURP gains or exhaustive optimizer ports before E21/E22 transfer. The goal is still active.

## Boundary verification

WSL experiment_handoff_check accepts generation37 with no errors; engineering_base_check and git diff --check pass. Root independently verified all seven source receipt hashes/JSON, all headroom input hashes, population counts and arithmetic. The initial malformed MemRL receipt remains preserved and is superseded by valid v2. These documentation/source checks do not establish a new runtime feature or permit a model contact.
