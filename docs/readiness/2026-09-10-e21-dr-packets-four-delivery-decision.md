# E21 DR packet-route component decision

Snapshot: 2026-09-10T20:49:47.020905+00:00. Root applied the frozen gates to all four predeclared deliveries after complete scoring and paired analysis.

Short-unit refresh is rejected. Self constrained passes the inherited discovery gates, but its very small gain does not justify replacing KC-E1f as the preferred repair component. Self free has no demonstrated corpus-WER gain. This is a component decision; the inherited fine OBS harm-stratum description remains open.

## Primary natural-mixture gains

Positive values mean improvement, in percentage points. Brackets are call-clustered CI90 with 10,000 draws, seed 20260903. Numeric matching is authoritative at whole-call level.

| Delivery | Corpus WER | PERSON WER | Non-entity WER | Numeric accuracy | Insertion rate | Decision |
|---|---:|---:|---:|---:|---:|---|
| unit_constrained | +1.073479 [+0.949786, +1.198029] | -1.782653 [-2.811114, -0.851637] | +0.028587 [-0.087616, +0.153289] | +0.143826 [-0.159362, +0.436968] | +1.065418 [+1.000907, +1.125538] | REJECTED |
| unit_free | -5.547510 [-5.981445, -5.129182] | -2.708262 [-3.622643, -1.871731] | -1.323887 [-1.563657, -1.083752] | -0.246558 [-0.606139, +0.115679] | -4.229983 [-4.601122, -3.869886] | REJECTED |
| self_constrained | +0.005559 [+0.001878, +0.009445] | +0.137127 [+0.031298, +0.282486] | +0.004272 [+0.001234, +0.007728] | -0.020547 [-0.047121, +0.000000] | +0.000556 [-0.000596, +0.001897] | ADMITTED_AS_DISCOVERY_REFRESH_IMPROVEMENT |
| self_free | +0.001668 [-0.052953, +0.087056] | +0.171409 [-0.035312, +0.378013] | +0.009529 [-0.051554, +0.107526] | +0.051366 [-0.019699, +0.126056] | -0.008617 [-0.020006, +0.001893] | NULL_NO_DEMONSTRATED_WER_GAIN |

The unit constrained arm fails PERSON, non-entity, and numeric non-inferiority. Its 1.073479-point WER gain accompanies a 1.065418-point insertion-rate gain: almost all aggregate benefit is insertion reduction, while names deteriorate. Unit free also has directional WER harm and fails the protective guards. Self free passes the natural primary guards but its WER interval includes zero; its equal-call WER point estimate has the opposite sign.

Self constrained changes WER from 8.199519 to 8.193960 percent: 20 fewer errors over 359,765 reference words. PERSON changes from 22.488858 to 22.351731 percent: four fewer errors over 2,917 mentions. Both gain intervals overlap the inherited own-null bands. Against historical KC-E1f, its PERSON gain is -3.599589 [-4.693453, -2.548259] points and its WER gain is -0.039470 [-0.054742, -0.025220]. The statistical admission is preserved, with a small-effect and protocol-mismatch limitation.

Under constrained delivery, unit minus self gains WER by 1.067919 [0.944869, 1.192272] points but loses PERSON by -1.919781 [-2.922660, -1.018453]. The draft-source attribution leg fails. The matched current-route contrast supports this conclusion without relying on historical transport equivalence.

## Weighting sensitivity

| Delivery | Metric | Equal call gain CI90 | Equal sector gain CI90 | Equal sample-rate gain CI90 |
|---|---|---:|---:|---:|
| unit_constrained | corpus_wer | +1.037345 [+0.911345, +1.163115] | +1.059140 [+0.944145, +1.164312] | +1.133971 [+0.943656, +1.299117] |
| unit_constrained | person_wer | -2.544895 [-3.742337, -1.424734] | -2.141960 [-3.164422, -1.264154] | -1.346139 [-2.593915, -0.433017] |
| unit_constrained | non_entity_wer | +0.007813 [-0.085723, +0.106941] | +0.017016 [-0.074366, +0.106984] | +0.125025 [-0.064675, +0.280326] |
| unit_constrained | numeric_accuracy | +0.212881 [-0.105472, +0.518096] | +0.133333 [-0.110395, +0.421818] | +0.069144 [-0.284226, +0.452007] |
| unit_constrained | insertion_rate | +1.052300 [+0.977024, +1.123398] | +1.062332 [+1.000509, +1.117257] | +1.039428 [+0.973005, +1.110067] |
| unit_free | corpus_wer | -5.483902 [-5.940941, -5.062888] | -5.553480 [-5.979333, -5.127737] | -5.399877 [-5.775483, -4.992601] |
| unit_free | person_wer | -3.337617 [-4.329470, -2.377629] | -3.021975 [-3.889926, -2.260340] | -2.468515 [-3.634027, -1.597154] |
| unit_free | non_entity_wer | -1.267905 [-1.510780, -1.023024] | -1.312616 [-1.540234, -1.081595] | -1.283895 [-1.480866, -1.053111] |
| unit_free | numeric_accuracy | -0.168947 [-0.641915, +0.295157] | -0.266030 [-0.620289, +0.107723] | -0.240604 [-0.692971, +0.197154] |
| unit_free | insertion_rate | -4.196898 [-4.619818, -3.790676] | -4.242742 [-4.624938, -3.856313] | -4.117293 [-4.477398, -3.762924] |
| self_constrained | corpus_wer | +0.004084 [+0.000769, +0.007608] | +0.005232 [+0.002344, +0.007696] | +0.004141 [+0.000518, +0.007403] |
| self_constrained | person_wer | +0.100406 [+0.024178, +0.207470] | +0.122835 [+0.027233, +0.235820] | +0.061491 [+0.014545, +0.117647] |
| self_constrained | non_entity_wer | +0.003386 [+0.000677, +0.006528] | +0.003769 [+0.001361, +0.006089] | +0.003567 [+0.001081, +0.006183] |
| self_constrained | numeric_accuracy | -0.021954 [-0.052876, +0.000000] | -0.021217 [-0.049548, +0.000000] | -0.023640 [-0.065880, +0.000000] |
| self_constrained | insertion_rate | +0.000334 [-0.000739, +0.001472] | +0.000537 [-0.000467, +0.001551] | +0.000241 [-0.001111, +0.001524] |
| self_free | corpus_wer | -0.006061 [-0.047379, +0.057264] | -0.005205 [-0.050442, +0.058047] | +0.046949 [-0.059236, +0.156121] |
| self_free | person_wer | +0.120030 [-0.035809, +0.280801] | +0.153559 [+0.003756, +0.298111] | +0.196494 [+0.000000, +0.398922] |
| self_free | non_entity_wer | +0.000760 [-0.043801, +0.072404] | +0.002031 [-0.047548, +0.073296] | +0.062807 [-0.056499, +0.184333] |
| self_free | numeric_accuracy | +0.046218 [-0.014929, +0.112318] | +0.047722 [-0.009381, +0.101977] | +0.067784 [-0.034449, +0.160506] |
| self_free | insertion_rate | -0.006511 [-0.017750, +0.004694] | -0.008257 [-0.016695, +0.000475] | -0.012130 [-0.026893, +0.005348] |

The inherited natural-mixture rule is primary. Equal-call and descriptive sector/sample-rate readings retain their own results; no new margins or retrospective gates are introduced.

## Descriptive strata

All values below are percentage-point gains on saved official counts. No individual stratum receives an effectiveness claim.

### sector

| Delivery | Stratum | Calls | WER | PERSON | Non-entity | Numeric | Insertions |
|---|---|---:|---:|---:|---:|---:|---:|
| unit_constrained | Basic Materials | 5 | +0.843657 | -0.915332 | -0.047482 | +0.626959 | +1.009025 |
| unit_constrained | Conglomerate | 4 | +0.966905 | -2.879581 | -0.100952 | +0.091743 | +1.077059 |
| unit_constrained | Consumer Goods | 5 | +1.020592 | -3.641457 | -0.181814 | +0.304878 | +1.186688 |
| unit_constrained | Financial | 5 | +1.013506 | -3.202847 | -0.032803 | +0.496032 | +1.072430 |
| unit_constrained | Healthcare | 5 | +1.162244 | +0.319489 | -0.116392 | -0.542888 | +1.200985 |
| unit_constrained | Industrial Goods | 5 | +1.276644 | -2.040816 | +0.469648 | +1.014832 | +0.848057 |
| unit_constrained | Services | 5 | +1.172529 | -3.465347 | -0.049332 | -0.791557 | +1.193100 |
| unit_constrained | Technology | 5 | +0.796190 | -5.813953 | -0.072501 | +0.000000 | +0.913485 |
| unit_constrained | Utilities | 5 | +1.279997 | +2.362205 | +0.284770 | +0.000000 | +1.060158 |
| unit_free | Basic Materials | 5 | -5.017097 | -2.288330 | -1.475326 | -0.731452 | -3.340994 |
| unit_free | Conglomerate | 4 | -6.261627 | -3.403141 | -1.248918 | -0.275229 | -5.081759 |
| unit_free | Consumer Goods | 5 | -5.251046 | -3.641457 | -1.282142 | -0.304878 | -3.994317 |
| unit_free | Financial | 5 | -5.487072 | -3.558719 | -1.415997 | +0.099206 | -4.101162 |
| unit_free | Healthcare | 5 | -5.465313 | -0.319489 | -1.551891 | -0.651466 | -4.029111 |
| unit_free | Industrial Goods | 5 | -4.755500 | -2.551020 | -0.993279 | +0.156128 | -3.779779 |
| unit_free | Services | 5 | -5.186752 | -5.940594 | -0.824553 | +0.087951 | -4.387434 |
| unit_free | Technology | 5 | -6.230895 | -5.232558 | -1.300751 | -0.774527 | -4.880216 |
| unit_free | Utilities | 5 | -6.326019 | -0.262467 | -1.720684 | +0.000000 | -4.589908 |
| self_constrained | Basic Materials | 5 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| self_constrained | Conglomerate | 4 | +0.004896 | +0.523560 | +0.000000 | -0.091743 | +0.002448 |
| self_constrained | Consumer Goods | 5 | +0.022013 | +0.000000 | +0.018890 | +0.000000 | +0.004002 |
| self_constrained | Financial | 5 | -0.009428 | +0.000000 | -0.005467 | -0.099206 | +0.000000 |
| self_constrained | Healthcare | 5 | +0.008302 | +0.319489 | +0.006466 | +0.000000 | +0.000000 |
| self_constrained | Industrial Goods | 5 | +0.004559 | +0.000000 | +0.008097 | +0.000000 | -0.004559 |
| self_constrained | Services | 5 | +0.014693 | +0.000000 | +0.003524 | +0.000000 | +0.002939 |
| self_constrained | Technology | 5 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| self_constrained | Utilities | 5 | +0.002055 | +0.262467 | +0.002413 | +0.000000 | +0.000000 |
| self_free | Basic Materials | 5 | -0.030831 | +0.000000 | -0.003392 | +0.000000 | -0.022423 |
| self_free | Conglomerate | 4 | -0.044061 | +0.785340 | -0.043265 | +0.000000 | -0.017135 |
| self_free | Consumer Goods | 5 | -0.026015 | +0.000000 | -0.054308 | +0.000000 | +0.020012 |
| self_free | Financial | 5 | -0.040069 | +0.000000 | -0.051938 | +0.000000 | +0.011785 |
| self_free | Healthcare | 5 | -0.008302 | +0.319489 | -0.006466 | +0.108578 | -0.008302 |
| self_free | Industrial Goods | 5 | -0.020517 | -0.510204 | -0.008097 | +0.078064 | -0.004559 |
| self_free | Services | 5 | -0.082283 | +0.000000 | -0.073998 | -0.175901 | -0.005877 |
| self_free | Technology | 5 | -0.024881 | +0.000000 | -0.029853 | +0.000000 | +0.003554 |
| self_free | Utilities | 5 | +0.230112 | +0.787402 | +0.289596 | +0.418760 | -0.051364 |
### sample_rate

| Delivery | Stratum | Calls | WER | PERSON | Non-entity | Numeric | Insertions |
|---|---|---:|---:|---:|---:|---:|---:|
| unit_constrained | 11025 | 5 | +1.318118 | -2.359882 | +0.216456 | +0.532978 | +1.114050 |
| unit_constrained | 16000 | 6 | +1.124780 | +0.000000 | +0.205304 | -0.479124 | +0.977153 |
| unit_constrained | 22050 | 5 | +1.250758 | +0.000000 | +0.420700 | -0.187617 | +0.904128 |
| unit_constrained | 24000 | 21 | +0.987504 | -2.305919 | -0.086069 | +0.292683 | +1.087520 |
| unit_constrained | 44100 | 7 | +0.988696 | -2.064897 | -0.131268 | +0.186800 | +1.114292 |
| unit_free | 11025 | 5 | -5.180851 | -4.129794 | -1.242160 | -1.132578 | -3.921038 |
| unit_free | 16000 | 6 | -5.220855 | -2.402402 | -1.417442 | +0.410678 | -3.819566 |
| unit_free | 22050 | 5 | -5.433433 | -0.375940 | -1.128707 | -0.375235 | -4.263555 |
| unit_free | 24000 | 21 | -5.862966 | -3.074558 | -1.402499 | -0.292683 | -4.463952 |
| unit_free | 44100 | 7 | -5.301282 | -2.359882 | -1.228669 | +0.186800 | -4.118351 |
| self_constrained | 11025 | 5 | +0.000000 | +0.000000 | +0.002460 | +0.000000 | +0.000000 |
| self_constrained | 16000 | 6 | +0.007030 | +0.000000 | +0.002812 | +0.000000 | +0.000000 |
| self_constrained | 22050 | 5 | +0.000000 | +0.000000 | +0.003420 | -0.093809 | +0.000000 |
| self_constrained | 24000 | 21 | +0.007833 | +0.307456 | +0.005644 | -0.024390 | +0.001205 |
| self_constrained | 44100 | 7 | +0.005842 | +0.000000 | +0.003500 | +0.000000 | +0.000000 |
| self_free | 11025 | 5 | -0.058305 | +0.000000 | -0.036896 | +0.133245 | -0.024988 |
| self_free | 16000 | 6 | -0.028120 | +0.000000 | -0.036561 | +0.000000 | +0.007030 |
| self_free | 22050 | 5 | +0.404402 | +0.751880 | +0.465164 | +0.281426 | -0.031774 |
| self_free | 24000 | 21 | -0.037958 | +0.230592 | -0.040918 | +0.048780 | -0.003615 |
| self_free | 44100 | 7 | -0.045273 | +0.000000 | -0.036755 | -0.124533 | -0.007302 |

## Construction and descriptive evaluation partitions

 Construction: 34 calls / 1,251 windows

| Arm | WER | PERSON WER | ORG WER | Non-entity WER | Insertions | Whole-call numeric accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Direct baseline | 0.084700 (24056/284014) | 0.234685 (544/2318) | 0.160070 (550/3436) | 0.049459 (11899/240582) | 8604 | 0.902244 (6756/7488) |
| Unit constrained | 0.073796 (20959/284014) | 0.254530 (590/2318) | 0.155413 (534/3436) | 0.048985 (11785/240582) | 5573 | 0.906116 (6785/7488) |
| Unit free | 0.137293 (38993/284014) | 0.261864 (607/2318) | 0.162689 (559/3436) | 0.062552 (15049/240582) | 19859 | 0.901709 (6752/7488) |
| Self constrained | 0.084647 (24041/284014) | 0.234254 (543/2318) | 0.160070 (550/3436) | 0.049405 (11886/240582) | 8603 | 0.902244 (6756/7488) |
| Self free | 0.084630 (24036/284014) | 0.233822 (542/2318) | 0.160361 (551/3436) | 0.049264 (11852/240582) | 8636 | 0.902911 (6761/7488) |

## Evaluation: 10 calls / 342 windows

| Arm | WER | PERSON WER | ORG WER | Non-entity WER | Insertions | Whole-call numeric accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Direct baseline | 0.071854 (5443/75751) | 0.186978 (112/599) | 0.216828 (201/927) | 0.039169 (2497/63749) | 2096 | 0.924310 (2076/2246) |
| Unit constrained | 0.061755 (4678/75751) | 0.196995 (118/599) | 0.187702 (174/927) | 0.039593 (2524/63749) | 1294 | 0.917631 (2061/2246) |
| Unit free | 0.138137 (10464/75751) | 0.213689 (128/599) | 0.212513 (197/927) | 0.052958 (3376/63749) | 6059 | 0.915405 (2056/2246) |
| Self constrained | 0.071788 (5438/75751) | 0.181970 (109/599) | 0.214671 (199/927) | 0.039169 (2497/63749) | 2095 | 0.923419 (2074/2246) |
| Self free | 0.072039 (5457/75751) | 0.181970 (109/599) | 0.214671 (199/927) | 0.039452 (2515/63749) | 2095 | 0.924310 (2076/2246) |

## Scope and saved metadata limits

- The evaluation table intentionally has no interval, hypothesis test, guard comparison, or effectiveness interpretation.
- Numeric accuracy is whole-call bag-matched saved scoring; it is not reconstructed from windows.
- The saved call and window metadata expose only `reporting_partition`, cluster/sample identity, sector, sample rate, and fixed-window timing. They do not contain inherited OBS harm strata for unit duration, boundary mode, or end-cut. Those strata therefore cannot be reported from this analysis directory without a separately pinned saved metadata source.
- The four generation inputs contain 1,593 scored fixed-window rows and 44 saved per-call numeric rows each. The historical direct baseline supplies 44 saved per-call scorer rows; fixed-window counts come from the pinned historical roster metadata.


## Source and cost custody

Each parent generated 1,593 contacts and 44 calls. Both constrained/free derivatives were built and scored once. Both parent attempts are FINALIZED with their original manifest hashes and actual calls/audio unchanged. GPU generation integrals were 1.1691855692 hours for unit and 1.1568545341 hours for self, each below 1.2; separate encoding, resident time and scoring costs remain in their receipts. Inline unavailable GPU fields were not replaced.

Preserve the protocol limitation: historical comparators used raw audio and another runtime identity. The shared four-window bridge does not establish full quality equivalence. No new matching control is needed merely to settle an effect this small when it cannot change the current G6 choice.

Root decision receipt: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/e21-dr-packets-root-decision-v1.json
SHA-256: d32462fcadb581b6e2e80e938f42ca06cbdab17a0567a317f6a8ade8fa9b3943

| Analysis | SHA-256 |
|---|---|
| call-error | 31029922a2652d830407e262f7e04814268fe2f86277feac4e190fee0d4f47ce |
| call-numeric | fc3575925ffb96cc3057f3f2db1990cb3cf51b251bb56ef8764deb8163dc6719 |
| window | e97b09f00cec1f834e3f4a1ce179d64929378e99b9ee78e194ca3102e3ee6c4a |
