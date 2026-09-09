# KV recovery: KV-0 decision (2026-09-09)

KV-0 is HARMFUL on the inherited NEW500 primary. Retain the sealed KC-S1b comparator and its example-bearing schema for KU-S3. This is a retrospective recovery decision, not a reconstructed pre-launch approval. All seven KV runs had already completed before this read; no historical attempt is changed or rescored.

| Population | N | KC-S1b mean | KV-0 mean | Delta pp | Scenario CI90 pp | Speaker CI90 pp | Equal-stratum delta pp |
|---|---:|---:|---:|---:|---|---|---:|
| NEW500 | 500 | 31.8922 | 27.2660 | -4.6263 | [-6.5361, -2.8059] | [-6.5737, -2.8145] | -4.4381 |
| DEV1000 | 1000 | 28.4533 | 25.4862 | -2.9671 | [-4.2694, -1.6875] | [-4.3813, -1.6511] | -2.7321 |
| OLD500 | 500 | 25.0143 | 23.7064 | -1.3079 | [-3.1087, 0.4582] | [-3.3146, 0.5113] | -1.3212 |

Both resamplers use the shared paired-analysis implementation, 10,000 draws and seed 20260903. The historical primary is scenario-stratified. Speaker-clustered sensitivity and the aligned null margin are explicitly retrospective for KV; they are frozen prospectively for KU-S4. NEW500 is a historical subgroup, not fresh held-out data.

The normalized NEW500 mean is 28.0630% for KV-0 versus the existing rounded KC-S1b mean 32.77%. Its sign agrees even after preserving +/-0.005 pp rounding uncertainty. The old comparator normalized per-row file was not retained, so no paired normalized CI is claimed and no scorer is rerun.

The original subtraction rule required noninferiority for neutrality. KV-0 fails even against the aligned null per-row half-width 1.382919 pp: its entire speaker CI90 is below -1.382919 pp. The historical pooled 0.8188 pp margin also fails. No interpretation of the historical one-sided/two-sided wording changes this fallback decision.

The standard complete-manifest official micro SLU-F1 for KV-0 is 41.753464%. The primary above is the mean of per-row F1; these are different estimators. The complete existing official score file retains the evaluator commit and identity check. Intent metrics in this slot-only output are not a live intent-to-slots system measurement.

Per-stratum primary results (natural-mixture sample counts; equal-stratum aggregate reported above):

| Scenario | N | KC-S1b mean % | KV-0 mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 35.4179 | 28.0907 | -7.3272 | 0 | 5 | 25 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 30.0767 | 28.0787 | -1.9980 | 1 | 2 | 30 |
| cooking | 9 | 63.0592 | 63.0592 | 0.0000 | 0 | 0 | 9 |
| datetime | 33 | 29.6552 | 32.5460 | 2.8908 | 2 | 1 | 30 |
| email | 33 | 26.8676 | 20.1611 | -6.7065 | 0 | 4 | 29 |
| general | 33 | 8.5832 | 6.5630 | -2.0202 | 0 | 1 | 32 |
| iot | 33 | 43.5625 | 39.7635 | -3.7990 | 2 | 2 | 29 |
| lists | 32 | 13.3415 | 9.8011 | -3.5403 | 1 | 2 | 29 |
| music | 23 | 12.7283 | 12.7283 | 0.0000 | 0 | 0 | 23 |
| news | 32 | 26.8768 | 26.2451 | -0.6317 | 2 | 1 | 29 |
| play | 32 | 40.7062 | 36.0886 | -4.6175 | 0 | 3 | 29 |
| qa | 32 | 46.5123 | 49.6373 | 3.1250 | 1 | 0 | 31 |
| recommendation | 32 | 56.2366 | 52.4764 | -3.7602 | 2 | 3 | 27 |
| social | 33 | 39.0681 | 23.2079 | -15.8602 | 1 | 9 | 23 |
| takeaway | 12 | 25.4596 | 11.5707 | -13.8889 | 0 | 2 | 10 |
| transport | 33 | 38.5429 | 25.8828 | -12.6601 | 3 | 6 | 24 |
| weather | 33 | 21.2268 | 12.1359 | -9.0909 | 0 | 3 | 30 |

KV-0 adds no observation or retrieval: OBS, ORG and SUPPLY match KC-S1b. The named changed component is USE-side schema rendering (removal of five example fillers and its corresponding header wording). This local contrast supports retaining that component; it does not establish a universal example effect.

Existing KV-0 cost: 1,000 model contacts, 2,884.7936875 audio seconds, 2,774,082 prompt tokens, 22,725 completion tokens, zero tool calls in the generation score record. Sum of request latencies is 1,509.267 seconds, not GPU wall time. This recovery adds zero model, encoder, tokenizer, or scorer contacts. Failure/fallback attribution and the remaining six historical cells are completed in the family successor report.

The missing historical verdict and already-completed KV-1/2/3 sequence are retained as protocol deviations. Do not claim those successors were scientifically admitted by an earlier KV-0 decision. The recovery selects the owner-approved KC-S1b fallback; actual KU-S3 launch still requires replication/closure and its own registered full-request fit.
