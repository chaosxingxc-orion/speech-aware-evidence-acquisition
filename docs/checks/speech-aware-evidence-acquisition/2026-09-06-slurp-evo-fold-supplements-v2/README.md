# EVO-S1 V2 folds — the flight products, and the one thing that still needs a model contact

Model-free, zero contacts. Exposure row `SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2`. Builder
`scripts/build_slurp_evo_fold_flight_products.py`; build rules
`src/speech_aware_evidence_acquisition/analysis/slurp_evo_flight_products.py`; tests
`tests/unit/test_slurp_evo_flight_products.py`. Receipts `products.json` (what was built) and
`verify.json` (what the production checks say about it, reproduced by `verify.py`).

A frozen roster receipt is an identity statement; a fold cannot be flown from one. Three artifacts
per fold turn it into a hydratable population, and all three come out of the **same single
measurement pass**, so they cannot disagree with each other:

| | fold A | fold B |
|---|---|---|
| roster | `SLURP-EVO-FOLD-A-V2` | `SLURP-EVO-FOLD-B-V2` |
| rows | 1,080 | 1,080 |
| speech seconds | 3,084.528438 | 3,154.797375 |
| channel mix | 523 headset / 557 far-field (48.43 %) | 527 / 553 (48.80 %) |
| dataset fragment | `configs/dataset/slurp-speech-native-evo-fold-a-1080.json` | `configs/dataset/slurp-speech-native-evo-fold-b-1080.json` |
| `runtime_view_sha256` | `f423fd59bee4ff73833f49187fde22071b4d5ea7a39243e55f728f0ccbf67918` | `fdb6ccdca1a4ea69f029d80af504bae631aac7f469fe5330e726d77dc81e469d` |
| probe-sample view | `docs/receipts/probe-samples/SLURP-EVO-FOLD-A-V2.json` | `docs/receipts/probe-samples/SLURP-EVO-FOLD-B-V2.json` |
| D1 media supplement | `docs/receipts/artifacts/d1-slurp-evo-fold-a-v2.json` | `docs/receipts/artifacts/d1-slurp-evo-fold-b-v2.json` |
| supplement artifact sha256 | `2b3d22993cfbefa5eee54b883cee23477b9e445e3b74a5e95ed86a327eba8397` | `c543067ece11f707cd6bb3fa297ffa515e596b7cbd3d445b55cce6411d49bd32` |
| supplement `manifest_sha256` | `c770b5d4ab5e00393c8eadce8ad95d40a5de7b4ec11a5ee1e1544c7794b7db74` | `eaae7bd790ee781a7a5ea3d87b6c988a6a9976487500c8f9fe0c5f5f3a5dcffc` |
| media bytes covered | 58,339,950 | 59,382,544 |
| run identity (`load_split` / `ExecutionPlan`) | `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` | `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a` |
| receipt identity (probe-split integrity) | `c0eb013d8561f924a9dd04400f7733f0b43594c93f02fdfa602142c8633e5354` | `5872e60e9f87905128dbfd01c2fc79c3da8d8161ff30f8ace9e061b83f6682b2` |

**Why the D1 supplement is not optional.** The immutable D1 identity artifact
(`docs/receipts/artifacts/d1-identity.json`, sha256 `9c10fad1…d35e3`) closes over the SLURP **devel**
split only — 8,690 recordings, **zero** `slurp:train:` ids — so without an additive media receipt
`contracts.gate_media_identity.verify_media_identity` refuses the model touch on every fold row.
This is the `TRAIN90` precedent, the only TRAIN roster this study has ever flown.

## What was verified, and by what

`verify.py` re-opens the committed artifacts and asks the **production** checks, not a
re-implementation of them:

| check | what it proves | result |
|---|---|---|
| `core.roster.read_roster` | each roster receipt's `split_identity_hash` recomputes from its own items | PASS, both folds |
| `contracts.gate.FrozenCoreGate.verify_media_identity` | all 2,160 flac files re-hashed on disk against the supplement's recorded bytes and durations, with D1 resolved **through the E0 closure receipt** exactly as a real model touch resolves it | PASS, both folds |
| `reproduction.probe_split.load_verified_probe_split` | the probe-sample view parses, its receipt-integrity hash recomputes, and the run identity it derives equals the dataset fragment's | PASS, both folds |
| item-set cross-check | roster, dataset fragment and probe view name the same 1,080 ids, and the fragment's `source_binding_sha256` is the canonical hash of that roster receipt | PASS, both folds |

The two identity conventions are kept distinct on purpose and both are recorded above: the
**run-identity** hash (`data.splits`, slash-prefixed `slurp/<sample_id>`) is what an `ExecutionPlan`
and `core.bundle.verify_bundle` carry and what the dataset fragment republishes; the
**receipt-integrity** hash (colon-keyed `slurp:<sample_id>`) is what `load_verified_probe_split`
recomputes fail-closed. They are two serializations of one frozen id set, and either pins the other.

## Contact surface

Each flac is re-hashed byte for byte and only its container header is read for duration and sample
rate. The SLURP loader is consulted for `media_relpath` and for nothing else — no sentence,
transcript, scenario, action, intent, entity, gold or score is opened, and none reaches any artifact
here. Zero model, GPU, network, tokenizer and scorer contacts. TRAIN sentence text appears in no
receipt and no document.

## Throughput (mandated deliverable)

| | rows | wall s | rows/s | workers |
|---|---:|---:|---:|---:|
| fold A measurement pass | 1,080 | 13.890 | 77.76 | 8 |
| fold B measurement pass | 1,080 | 13.291 | 81.26 | 8 |

Eight workers, the owner's standing ceiling while a GPU campaign may be flying. The dominant cost of
the run is not this pass but the SLURP `train` loader, which resolves and header-verifies all 50,628
recordings once before either fold is measured.

## What is NOT here: the featcache packets

**`SAEA-SLURP-EVO-FOLD-PACKETS-V2` was not run, and this row could not run it.** Packet promotion is
not CPU-only bookkeeping: it starts a llama.cpp sidecar with the frozen decoder **and the mmproj
encoder** loaded and issues **one contact per row** at `max_tokens: 1`, which is a model contact
under a `bounded-discovery-probe` profile (`SAEA-SN-DEV1000-PREPROCESS`, 2026-08-24, is the
precedent this would copy). This row is `model-free-check` with zero contacts, so it stops here and
leaves the promotion to the flight agent.

What the flight agent needs, measured rather than assumed (`products.json`, `packet_coverage`):

* **2,160 of 2,160 fold rows have no packet.** 0/1,080 present in `slurp-q4km-packets`,
  0/1,080 in `slurp-q4km-packets-04ccc72a` (the resident root) and 0/1,080 in
  `slurp-q4km-packets-x108-04ccc72a`, for both folds. That is expected and is a property of the
  draw: every TRAIN utterance this study has already touched was excluded before any of the three
  rosters was drawn, and a touched utterance is exactly the kind that would already have a packet.
* **The scope is therefore the whole of both fold fragments** — no set difference is needed, and no
  derived "NEW" receipt has to be cut, unlike DEV-1000 where 500 of 1,000 packets already existed.
* **Two preprocess sessions**, one per fold, composing `q4km-preprocess-featcache-cpu-sidecar` +
  `slurp-speech-native-evo-fold-{a,b}-1080` + `speech-native-preprocess` + a new
  `slurp-evo-fold-{a,b}-preprocess` experiment fragment, on the same `04ccc72a` preprocess runtime
  receipt, producing `EVO-FOLD-A-V2-promotion.json` and `EVO-FOLD-B-V2-promotion.json` under
  `~/feat-cache/slurp-q4km-packets-04ccc72a/`.
* **Registered budget**: 2,160 calls and 6,239.33 speech seconds across the two sessions (1,080 /
  3,084.528438 and 1,080 / 3,154.797375). Own GPU offload zero — the sidecar runs `-ngl 0` — but the
  contacts are real and must be pre-registered before results are read.
