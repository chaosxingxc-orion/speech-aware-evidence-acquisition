# Whisper diagnosis: predecessor-state variability dominates paired discordance

The frozen quality verdict remains EFFECTIVENESS_NOT_ESTABLISHED. This registered diagnostic identifies the component that limits action attribution; it neither retroactively admits Whisper nor claims transcript correctness.

## Root finding

Of 177 unequal final raw outputs, 158 preserve their already unequal pre-observation drafts byte for byte in both arms. Those 158 pairs contain 11 intent saves and 18 harms. Their net difference is -7 answers, compared with -9 answers for the full cohort. That portion of final discordance is inherited from independently generated predecessors, with no answer-changing revision in either arm. A fresh action-credit comparison must branch from the same source-bound current state rather than attribute independently regenerated drafts to a later observation.

The remaining effects are not explained away. Among the 833 exact equal-draft pairs, final intent has 2 saves and 4 harms. The treatment changes only 25 of its 1,000 drafts while control changes 4. This demonstrates low observed revision activity and competing paths, not a diagnosed acoustic failure or a successful corrective policy.

## Verified delivery and output health

- All 1,000 prepared transcripts are present, source-hash valid, nonempty and status ok, with no suppression, low-speech flag, output-cap flag or recorded decoder failure.
- All 1,000 treatment revision requests contain exactly the five retained knowledge items, the rendered observation and the original speech packet. The shared observation renderer matches every request and source lineage.
- Both arms have exactly three requests per sample, no recorded retry, all 6,000 wire finishes stop, maximum completion 121 tokens under the 256 cap, and all 2,000 final outputs parse.
- Mean final prompt tokens increase from 3,322.303 to 4,317.754. Evidence arrival is verified; arrival does not prove useful consumption.

## Complete transition partition

| Pre-OBS drafts | Finals | Control revised | Treatment revised | n | Intent saves | Intent harms | Ties |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| draft_equal | final_equal | control_revised_0 | whisper_revised_0 | 815 | 0 | 0 | 815 |
| draft_equal | final_equal | control_revised_1 | whisper_revised_1 | 2 | 0 | 0 | 2 |
| draft_equal | final_unequal | control_revised_0 | whisper_revised_1 | 15 | 2 | 3 | 10 |
| draft_equal | final_unequal | control_revised_1 | whisper_revised_0 | 1 | 0 | 1 | 0 |
| draft_unequal | final_equal | control_revised_0 | whisper_revised_1 | 5 | 0 | 0 | 5 |
| draft_unequal | final_equal | control_revised_1 | whisper_revised_0 | 1 | 0 | 0 | 1 |
| draft_unequal | final_unequal | control_revised_0 | whisper_revised_0 | 158 | 11 | 18 | 129 |
| draft_unequal | final_unequal | control_revised_0 | whisper_revised_1 | 3 | 1 | 1 | 1 |

## Scope and next experiment

The named component is predecessor-state generation and revision credit attribution. This is a source-bound localization of the dominant observed discordance, not proof that Whisper caused or could repair any particular error. No intermediate official score or new gold/negation annotation was used. Conditional subsets are descriptive and do not replace the full prespecified result or its intervals.

Prepare the first TRAIN-A incumbent run from the already replicated compact system. It generates legal construction trajectories for the optimizer with the existing prepared speech/query products and cohort-excluded knowledge. It introduces no new observation mechanism. Subsequent group-relative action experiments must share the same sealed predecessor and account separately for every real action/contact. A frozen candidate still needs live end-to-end evaluation on its registered separate selection/evaluation role; predecessor replay cannot establish full-system performance.

Do not automatically release Reviewer targeting, redraw evaluation rows, copy DEV errors into memory or mark fixed Whisper effective. New proposals and B selection retain their own complete configurations, registrations and quality rules.

## Sources

- Complete result and all scenario strata: docs/readiness/2026-09-12-slurp-fixed-whisper-result-v1.md.
- Diagnostic: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/slurp-speech-observation-trace-diagnostic-v1/diagnostic-v2.json.
- Diagnostic SHA-256: b48fd3c17e14e9d85794c9b498f71d2be9b61bbffa730e353ca2ed227553dd4c.
- Root component decision: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/slurp-speech-observation-component-decision-v1.json.
- The exact read scope is already covered by docs/readiness/2026-09-12-slurp-speech-observation-analysis-registration-v1.json. No new model, tokenizer, encoder, audio or scorer contact occurred.
- Preserve diagnostic.json version 1 as superseded: it compared the rendered observation block against raw transcript text. Version 2 compares the shared renderer output and corrects that representation mismatch without changing other aggregates.
