# VAR-2 matched-prefix supply action preregistration

Execute the owner-approved four-action construction experiment on all 625 R01C
TRAIN utterances after closing VAR-1 and VERIFY-1. VERIFY-1 task benefit was not
established; VAR-2 addresses an independent knowledge-supply action question.

Use the shared controller and OpenJiuwen runtime, prepared speech packets, the
existing decoder-only no-mmproj service, four 24,576-token slots and 512 output
tokens. No new encoder, ASR, outside model, fresh DEV or test data is admitted.

Keep each Solver visit's pre-state identical across exk10, exk30, exdiv and plan,
in that fixed order. Only plan continues through Reviewer and Planner. Preserve
every raw response and trace. Use first Solver visits as the primary comparison;
revision visits are conditional on the plan path and remain separate. Fixed arm
order is a limitation, not canceled by an earlier repeat experiment.

Run the four-row form proof first, then full625. Four rows establish custody and
control-flow validity, never efficacy. Use the same runtime actual-request fit
check for every branch on the complete roster and for revisions. The preliminary
supply estimate (9600 base + 120 per item + 512 output) is not a measured maximum
or a substitute for actual fits. Historical K30 fit context is descriptive only.

Generation caps: smoke68, full10625. Fit endpoint caps: smoke272, full42500
(maximum 17 model contacts per row, four fit endpoint calls per contact). The
full flight cap is 8 GPU hours including fit; this is a ceiling, not a target.
Stop on failure; at most one named diagnosed recovery, never automatic replay.

Score the complete terminal output once through core.scoring_batch. Render four
complete first-visit columns from the sealed trace and score each once through
the same shared scoring module. Malformed answers become explicit canonical-empty
derived fallbacks; completed no-Solver abstentions remain in every arm. Reject
partial/misbound groups. Keep raw artifacts unchanged. Preserve first-visit arm
order provenance; final visit custody binds declared knobs, while earlier contact
positions follow the pinned runtime order and are not independent arm-name records.

Report pooled official word+char SLU-F1, intent, empty-target false positives,
malformation, input volume, actual calls and all scenario strata with natural and
equal-scenario summaries. Paired utterance bootstrap: 10000 draws, seed20260915.
Use frozen VAR1 PLAN F0 for the declared count utility; keep intent separate.
No local branch result qualifies a complete system or constitutes RL return.
Validate useful actions through the complete four-node system before policy learning.
