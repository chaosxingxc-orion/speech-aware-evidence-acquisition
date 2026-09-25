# VAR-1 official-count feedback v2

Status: post-hoc descriptive read after the original family result. No new model
or official scorer contact, no new split, no revision of the original verdict.

Freeze F0 = 0.5850661976193667 from PLAN pooled official word+character counts.
Use u = 2TP - F0(2TP+FP+FN). Utility has count units, not percent or accuracy.
The generic bootstrap JSON also carries 100-scaled utility fields named pp;
those are scaled count values, not percentage-point task gains. Use the unscaled
utility/bootstrap fields for policy construction. Intent remains separate.

| Arm | pooled SLU-F1 (%) | Empty-target FP rows / 191 | Exact FP total on empty targets | Mean utility |
| --- | ---: | ---: | ---: | ---: |
| plan | 58.5066 | 114 | 134 | -0.000000 |
| planr | 60.3755 | 115 | 137 | 0.107177 |
| exk10 | 60.4440 | 113 | 134 | 0.110771 |
| exk30 | 60.4606 | 108 | 125 | 0.112727 |
| exdiv | 58.6794 | 113 | 127 | 0.009966 |
| perk16c5 | 58.6673 | 119 | 144 | 0.009377 |

| Variant | Comparator | Natural SLU-F1 delta pp [CI95] | Equal-scenario delta pp [CI95] |
| --- | --- | ---: | ---: |
| exdiv | plan | 0.1727 [-1.5031, 1.8769] | 0.3216 [-1.5831, 2.0849] |
| exdiv | planr | -1.6962 [-3.3898, -0.0611] | -1.9038 [-3.9902, 0.1059] |
| exk10 | plan | 1.9373 [0.3626, 3.5180] | 1.7370 [-0.1536, 3.4521] |
| exk10 | planr | 0.0684 [-1.4816, 1.5823] | -0.4885 [-2.4799, 1.2203] |
| exk30 | plan | 1.9540 [0.4842, 3.4500] | 2.4881 [0.6377, 4.2124] |
| exk30 | planr | 0.0851 [-1.4704, 1.5990] | 0.2627 [-1.8054, 2.0751] |
| perk16c5 | plan | 0.1607 [-1.3631, 1.6907] | 0.3047 [-1.2694, 1.8334] |
| perk16c5 | planr | -1.7082 [-3.3709, -0.0662] | -1.9207 [-3.8185, -0.0634] |

Root interpretation: the revised reward exposes empty-target hallucinations but
does not turn K10/K30 into stable improvements over PLANR. K30 reduces empty-target
FP rows by six versus PLAN, while fourteen newly harmed rows coexist with twenty
repairs. This is an action hypothesis, not an established conditional policy.
Keep all four registered VAR-2 actions to measure the matched-prefix question;
do not select a winner or filter rows from this same-roster post-hoc analysis.

The 191 empty-target rows remain in optimization. Canonical answer disagreements
retain intent and entity differences even when row-F1 is tied at zero. F10 tests
explicit empty-list knowledge representation; it must also report nonempty-target
FN changes, not reward silence alone.

## Scenario decomposition (variant minus comparator)

| Variant | Comparator | Scenario | n | pooled SLU-F1 delta pp | Empty-target exact FP delta |
| --- | --- | --- | ---: | ---: | ---: |
| exdiv | plan | alarm | 26 | -0.3713 | -1 |
| exdiv | plan | audio | 30 | 3.9550 | -3 |
| exdiv | plan | calendar | 42 | -1.2553 | -1 |
| exdiv | plan | cooking | 31 | -2.0691 | -2 |
| exdiv | plan | datetime | 39 | 2.6303 | -2 |
| exdiv | plan | email | 33 | -5.9420 | 1 |
| exdiv | plan | general | 42 | 1.3905 | -3 |
| exdiv | plan | iot | 33 | 1.9921 | 1 |
| exdiv | plan | lists | 37 | -6.7834 | 3 |
| exdiv | plan | music | 27 | 2.6087 | -3 |
| exdiv | plan | news | 36 | 3.9649 | 0 |
| exdiv | plan | play | 37 | -0.3158 | -1 |
| exdiv | plan | qa | 38 | 2.7273 | 1 |
| exdiv | plan | recommendation | 29 | 6.1424 | 0 |
| exdiv | plan | social | 35 | 0.4450 | 1 |
| exdiv | plan | takeaway | 37 | 0.0161 | 1 |
| exdiv | plan | transport | 32 | -2.5617 | 0 |
| exdiv | plan | weather | 41 | -0.7842 | 1 |
| exdiv | planr | alarm | 26 | -0.3888 | -5 |
| exdiv | planr | audio | 30 | -12.0182 | 1 |
| exdiv | planr | calendar | 42 | -5.1722 | 0 |
| exdiv | planr | cooking | 31 | 1.1064 | -4 |
| exdiv | planr | datetime | 39 | -1.7237 | 0 |
| exdiv | planr | email | 33 | -9.9521 | 3 |
| exdiv | planr | general | 42 | 4.1027 | 1 |
| exdiv | planr | iot | 33 | -3.9403 | 1 |
| exdiv | planr | lists | 37 | -1.9916 | -1 |
| exdiv | planr | music | 27 | 1.8182 | -2 |
| exdiv | planr | news | 36 | 0.4802 | 0 |
| exdiv | planr | play | 37 | -0.5885 | -3 |
| exdiv | planr | qa | 38 | -3.4842 | 0 |
| exdiv | planr | recommendation | 29 | 0.2971 | -2 |
| exdiv | planr | social | 35 | -1.3185 | 1 |
| exdiv | planr | takeaway | 37 | 0.4694 | 1 |
| exdiv | planr | transport | 32 | -2.1360 | 0 |
| exdiv | planr | weather | 41 | 0.1716 | -1 |
| exk10 | plan | alarm | 26 | 1.9820 | 0 |
| exk10 | plan | audio | 30 | 8.7208 | -4 |
| exk10 | plan | calendar | 42 | 6.0302 | -1 |
| exk10 | plan | cooking | 31 | 1.6654 | 1 |
| exk10 | plan | datetime | 39 | 1.7890 | -1 |
| exk10 | plan | email | 33 | -6.1467 | 3 |
| exk10 | plan | general | 42 | 1.3905 | -4 |
| exk10 | plan | iot | 33 | 0.7653 | 1 |
| exk10 | plan | lists | 37 | -5.3247 | 1 |
| exk10 | plan | music | 27 | 3.6613 | -3 |
| exk10 | plan | news | 36 | 6.2166 | 0 |
| exk10 | plan | play | 37 | 3.2076 | -1 |
| exk10 | plan | qa | 38 | -2.0808 | 4 |
| exk10 | plan | recommendation | 29 | 5.3606 | 1 |
| exk10 | plan | social | 35 | 4.1060 | 0 |
| exk10 | plan | takeaway | 37 | -0.0973 | 2 |
| exk10 | plan | transport | 32 | -0.2985 | 0 |
| exk10 | plan | weather | 41 | 0.3180 | 1 |
| exk10 | planr | alarm | 26 | 1.9646 | -4 |
| exk10 | planr | audio | 30 | -7.2523 | 0 |
| exk10 | planr | calendar | 42 | 2.1134 | 0 |
| exk10 | planr | cooking | 31 | 4.8410 | -1 |
| exk10 | planr | datetime | 39 | -2.5649 | 1 |
| exk10 | planr | email | 33 | -10.1568 | 5 |
| exk10 | planr | general | 42 | 4.1027 | 0 |
| exk10 | planr | iot | 33 | -5.1671 | 1 |
| exk10 | planr | lists | 37 | -0.5329 | -3 |
| exk10 | planr | music | 27 | 2.8708 | -2 |
| exk10 | planr | news | 36 | 2.7319 | 0 |
| exk10 | planr | play | 37 | 2.9350 | -3 |
| exk10 | planr | qa | 38 | -8.2923 | 3 |
| exk10 | planr | recommendation | 29 | -0.4848 | -1 |
| exk10 | planr | social | 35 | 2.3424 | 0 |
| exk10 | planr | takeaway | 37 | 0.3560 | 2 |
| exk10 | planr | transport | 32 | 0.1272 | 0 |
| exk10 | planr | weather | 41 | 1.2738 | -1 |
| exk30 | plan | alarm | 26 | -0.3639 | 0 |
| exk30 | plan | audio | 30 | 18.9721 | -6 |
| exk30 | plan | calendar | 42 | 3.8195 | -1 |
| exk30 | plan | cooking | 31 | -5.0347 | -2 |
| exk30 | plan | datetime | 39 | 2.6786 | -2 |
| exk30 | plan | email | 33 | 2.8701 | 0 |
| exk30 | plan | general | 42 | -0.3533 | 1 |
| exk30 | plan | iot | 33 | 2.4750 | 2 |
| exk30 | plan | lists | 37 | -6.6806 | 0 |
| exk30 | plan | music | 27 | 6.1381 | -5 |
| exk30 | plan | news | 36 | 5.3125 | 0 |
| exk30 | plan | play | 37 | 2.3023 | -1 |
| exk30 | plan | qa | 38 | 4.8169 | 2 |
| exk30 | plan | recommendation | 29 | 1.7257 | 2 |
| exk30 | plan | social | 35 | 3.9133 | 1 |
| exk30 | plan | takeaway | 37 | 2.6431 | 0 |
| exk30 | plan | transport | 32 | 1.3993 | -1 |
| exk30 | plan | weather | 41 | -1.8480 | 1 |
| exk30 | planr | alarm | 26 | -0.3814 | -4 |
| exk30 | planr | audio | 30 | 2.9989 | -2 |
| exk30 | planr | calendar | 42 | -0.0973 | 0 |
| exk30 | planr | cooking | 31 | -1.8592 | -4 |
| exk30 | planr | datetime | 39 | -1.6753 | 0 |
| exk30 | planr | email | 33 | -1.1400 | 2 |
| exk30 | planr | general | 42 | 2.3589 | 5 |
| exk30 | planr | iot | 33 | -3.4574 | 2 |
| exk30 | planr | lists | 37 | -1.8888 | -4 |
| exk30 | planr | music | 27 | 5.3476 | -4 |
| exk30 | planr | news | 36 | 1.8278 | 0 |
| exk30 | planr | play | 37 | 2.0297 | -3 |
| exk30 | planr | qa | 38 | -1.3946 | 1 |
| exk30 | planr | recommendation | 29 | -4.1196 | 0 |
| exk30 | planr | social | 35 | 2.1497 | 1 |
| exk30 | planr | takeaway | 37 | 3.0965 | 0 |
| exk30 | planr | transport | 32 | 1.8250 | -1 |
| exk30 | planr | weather | 41 | -0.8921 | -1 |
| perk16c5 | plan | alarm | 26 | 2.3486 | 1 |
| perk16c5 | plan | audio | 30 | 1.8896 | -1 |
| perk16c5 | plan | calendar | 42 | -0.7086 | 1 |
| perk16c5 | plan | cooking | 31 | -1.3677 | -1 |
| perk16c5 | plan | datetime | 39 | -0.2352 | -2 |
| perk16c5 | plan | email | 33 | 3.9923 | 0 |
| perk16c5 | plan | general | 42 | -5.1904 | 5 |
| perk16c5 | plan | iot | 33 | 0.5731 | 3 |
| perk16c5 | plan | lists | 37 | -2.9405 | 0 |
| perk16c5 | plan | music | 27 | 0.7905 | 0 |
| perk16c5 | plan | news | 36 | -3.5743 | 2 |
| perk16c5 | plan | play | 37 | -1.0363 | 2 |
| perk16c5 | plan | qa | 38 | 3.0365 | -2 |
| perk16c5 | plan | recommendation | 29 | 7.0871 | 1 |
| perk16c5 | plan | social | 35 | 0.1235 | 0 |
| perk16c5 | plan | takeaway | 37 | 1.7812 | 0 |
| perk16c5 | plan | transport | 32 | -0.3642 | -1 |
| perk16c5 | plan | weather | 41 | -0.7200 | 2 |
| perk16c5 | planr | alarm | 26 | 2.3312 | -3 |
| perk16c5 | planr | audio | 30 | -14.0835 | 3 |
| perk16c5 | planr | calendar | 42 | -4.6254 | 2 |
| perk16c5 | planr | cooking | 31 | 1.8079 | -3 |
| perk16c5 | planr | datetime | 39 | -4.5892 | 0 |
| perk16c5 | planr | email | 33 | -0.0178 | 2 |
| perk16c5 | planr | general | 42 | -2.4782 | 9 |
| perk16c5 | planr | iot | 33 | -5.3594 | 3 |
| perk16c5 | planr | lists | 37 | 1.8513 | -4 |
| perk16c5 | planr | music | 27 | 0.0000 | 1 |
| perk16c5 | planr | news | 36 | -7.0589 | 2 |
| perk16c5 | planr | play | 37 | -1.3089 | 0 |
| perk16c5 | planr | qa | 38 | -3.1750 | -3 |
| perk16c5 | planr | recommendation | 29 | 1.2418 | -1 |
| perk16c5 | planr | social | 35 | -1.6401 | 0 |
| perk16c5 | planr | takeaway | 37 | 2.2345 | 0 |
| perk16c5 | planr | transport | 32 | 0.0615 | -1 |
| perk16c5 | planr | weather | 41 | 0.2358 | 0 |

Source: $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-VAR1-OFFICIAL-FEEDBACK-V2/feedback.json.
SHA-256: bc670a03102dfddb4f84175e3d825237bd411cbd1d1a5ffbb616242aa66427ae. Paired utterance bootstrap: 10000 draws, seed 20260915.
All parse/fallback/format diagnostics, source hashes and CI90/CI95 are in that file.
