# Rows and materialization root must complete

Item E35 registers configuration only; it adds NO exposure-ledger rows
itself (root adds them at flip time, per program convention). Nothing here
has been registered, and no contact of any kind has been made.

## 1. Materialize the two derived execution-unit artifacts (model-free)

```
python scripts/build_e21_native_window_unit_subset.py \
    --source <data-root>/analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json \
    --batch-name SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1 \
    --sample-id 4320211 --per-call-limit 4 \
    --output <data-root>/analysis/SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1/window-inventory.json

python scripts/build_e21_native_window_unit_subset.py \
    --source <data-root>/analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json \
    --batch-name SAEA-E21-NATIVE-WINDOW-SUB10-V1 \
    --sample-id 4330115 --sample-id 4365024 --sample-id 4365948 \
    --sample-id 4366429 --sample-id 4366522 --sample-id 4384964 \
    --sample-id 4385072 --sample-id 4387383 --sample-id 4389907 \
    --sample-id 4397829 \
    --output <data-root>/analysis/SAEA-E21-NATIVE-WINDOW-SUB10-V1/window-inventory.json
```

Each must print the `file_sha256` the corresponding baseline pins:

| Batch | Expected file_sha256 | unit_count |
| --- | --- | --- |
| `SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1` | `e5f3cfbcbc407fbb3a7b59469b86ab9d405f7b43963cb2d18b655790c5f4a32b` | 4 |
| `SAEA-E21-NATIVE-WINDOW-SUB10-V1` | `57ee023e4c1e38a79f99418c9e9dd5e4f87233a2162eac213ac070a73a31bba5` | 342 |

A mismatch means the shared inventory or the selection changed since this
item registered it -- refuse and re-check before flying.

## 2. Fresh exposure-ledger rows needed (root registers; none exist yet)

| Role | Kind | Run | Plan (this package) |
| --- | --- | --- | --- |
| direct | generation | `SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1` | `four-row-direct-plan-v1.json` |
| system | generation | `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1` | `four-row-system-plan-v1.json` |
| direct | generation | `SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1` | `sub10-direct-plan-v1.json` |
| system | generation | `SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1` | `sub10-system-plan-v1.json` |

Budgets (ceilings, not targets): four-row pair totals 48 model calls / 0.6
GPU-h / 360 speech-audio seconds; sub10 pair totals 4,104 model calls / 13.5
GPU-h / 30,407 speech-audio seconds; two complete official scores per pair;
zero ASR/encoder contacts beyond the pinned speech-feature packets already
materialized for the full44 roster.

## 3. Decision receipt

A root decision receipt admitting this readiness package
(`docs/readiness/2026-09-22-e21-native-window-flightruntime-e35-v1/`) before
any of the four cells above may be re-pinned and enqueued.

## 4. Queue

Enqueue through the SAEA-Batch-Driver (decision 77) once admitted; this item
queues nothing itself and makes no `serving_session`/session-attach change.
