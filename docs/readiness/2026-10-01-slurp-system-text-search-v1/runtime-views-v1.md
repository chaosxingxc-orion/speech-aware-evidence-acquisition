# Exact TRAIN runtime views for the system-text search

Owner214's three update rounds and common selection now have native runtime
dataset fragments for their exact registered cohorts. Preparation uses the
existing `data.runtime_subset` builder and `data.slurp.load_slurp_engineering_gate`.
It adds no alternate loader, executor, model contact or scientific read.

| Stage | Parent | Hash-ordered positions | Rows | Speech seconds |
| --- | --- | --- | ---: | ---: |
| update-1 | TRAIN Fold A | 1-400 | 400 | 1133.6675000 |
| update-2 | TRAIN Fold A | 401-800 | 400 | 1159.3476875 |
| update-3 | TRAIN Fold B | 1-400 | 400 | 1186.2393750 |
| selection | TRAIN Fold B | 401-800 | 400 | 1155.5011875 |

The order is the existing `SHA256("20261001:<sample_id>")` ascending rule,
with sample ID as tie-breaker. These are the same 1,600 distinct inputs already
registered, not extra trajectories or a new draw. Initial R01C and DEV keep
their existing views. Historical exposure remains acknowledged.

## Source and media verification

[The machine receipt](runtime-views-v1.json) pins the CONTROL-V2 protocol,
original roster receipts, parent runtime files, seed and its ancestor, and all
eight new runtime/selection files. Each runtime file retains only the existing
six media-identity fields. No labels, transcripts, task answers or scores were
read. The existing native loader verified both complete parent views and all
four selected views against live TRAIN audio bytes, duration and sample rate.
The D1 media supplement pins remain inherited from their own parent views.

The registered cohorts match exactly in order and identity. The protocol's
source-roster validation preserves utterance-level separation, and the pinned
seed's cumulative sources are disjoint from all four prospective cohorts.
This is an initial-seed check only: every actual candidate still needs the
compile/admission checks against its accumulated proposal, construction,
feedback and selection sources.

Nonzero offsets use a `saea-runtime-subset-receipt-v2` carrying `slice_start`.
The default zero offset keeps v1 bytes and identity, including the already
registered R01C400 view. Existing records are not rewritten.

## Reproduction and corrected-seed ancestry

Run the following in the isolated checkout with the speechrl environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B \
  scripts/prepare_system_text_runtime_views.py \
  --repo-root "$PWD" \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --protocol "$PWD/docs/readiness/2026-10-01-slurp-system-text-search-v1/protocol-control-v2.json" \
  --parent-protocol "$PWD/docs/readiness/2026-10-01-slurp-system-text-search-v1/protocol.json" \
  --workers 4
```

Preparation validates all sources, complete lineage, selected media and existing
destination bytes before publishing anything. Identical reruns are allowed;
different destination bytes are refused. Workers are bounded at eight. A later
protocol change requires explicit reconciliation of this pinned receipt, never
an overwrite of its bytes.

CONTROL-V2's seed is a successor of the original seed. `import-seed` now loads
and verifies the complete parent chain already held by the same search archive.
Import the original `prepared/SAEA-SLURP-SYSTEM-TEXT-SEARCH-V1/seed-policy.json`
first, then the corrected
`prepared/SAEA-SLURP-SYSTEM-TEXT-SEARCH-CONTROL-V2/seed-policy.json`, separately
into each isolated branch archive. Keep the latter ID as the protocol's seed.
Missing parents or removed cumulative exposure are refused before storage.
The correction changes no policy text and grants no proposer permission.

## Remaining runtime work

Use `configs/dataset/slurp-speech-native-system-text-<stage>-400-v1.json` as the
evaluation roster for candidate compilation and as that stage's dataset fragment.
The subset receipt is metadata evidence; it is not an exposure row. Each actual
member still needs its own TRAIN query/agreement and prepared supply bindings,
configuration, FIT, generation plan, official score identity, complete-family
READ recipe and coordinator admission. No held cell or queue was changed.

Owner216 scoring-entry recovery and the proposer output-budget decision remain
pending. Preserve CONTROL2's frozen worker, caches, failed scoring job, complete
generation and STOP. This preparation cannot make the initial feedback readable.
Independent milestone outputs remain excluded from the optimizer.

Validation is recorded in
[the continuation receipt](../../receipts/continuation/2026-10-01-system-text-runtime-views.json).
