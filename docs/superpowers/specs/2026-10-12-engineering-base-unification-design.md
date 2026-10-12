# Engineering base unification: one model table, one feature table, one disk layout

Date: 2026-10-12. Status: DESIGN plus model-free tooling (branch `opus/engineering-base-unification`, not merged).
Authority: owner directive 2026-10-12 09:20Z (decision 274 proposed, "first unify the engineering base -- which
model is used, which features are read, from which disk they are read -- and lock experiment efficiency first");
standing rule decision 267 (hot paths on Linux-native ext4, never `/mnt/*` 9p); owner ruling 284 (2026-10-12: a
2 TB ext4 VHDX on E: is the hot root; migrate; then delete the E: originals and carve a second VHDX).

Machine-readable twin: `configs/base/engineering-base-v1.json` (the manifest). Gate:
`scripts/checks/engineering_base_locator_check.py`. Data-root authority: `scripts/lib/data_root.sh` (one line).
Migration tool: `scripts/data/migrate_data_root_ext4.sh`. Timing receipt: `scripts/checks/engineering_base_timing.py`.

Nothing in this document authorises a flight, a serving restart, a re-pin, a flip, the migration itself, or any
deletion on E:. Each of those is an owner decision listed in section 10.

## 1. Why

The measured cost of the current base (decision 267 receipts, 2026-10-12):

| Operation | on 9p (`/mnt/d`, `/mnt/e`) | on ext4 |
|---|---|---|
| `core.flight.cli` import | 38 s | 0.4 s |
| `git status` | 7.6 s | 0.4 s |
| campaign prelude of today's i3 column | 15+ min in disk-wait on the data root | (target: under 5 min) |
| `core.flight.cli check` per cell | loads a 15 MB knowledge snapshot from `/mnt/e` | |
| sequential read / write | 193 / 163 MB/s | 1.6 / 0.9 GB/s (VHDX on E:) |
| create 2,000 small files / stat+read 2,000 files | 3.45 s / 5.91 s | 0.03 s / 2.07 s (VHDX on E:) |

The VHDX numbers are the coordinator's non-destructive 20 GB test (2026-10-12). The repository and the models
already moved to ext4 (flip and flight worktrees under `/home/chao/saea-worktrees`, GGUFs under
`/home/chao/models`, packets under `/home/chao/feat-cache`). The data root is the one hot surface left on 9p.

## 2. The base at a glance

| Axis | Declared base | Where it is pinned |
|---|---|---|
| Model | Qwen3-Omni-30B-A3B Q4_K_M, Instruct (every system cell) and Thinking (266-E / 268 column) | manifest `models[]`; runtime receipts under `docs/receipts/`; umbrella `docs/datasets.lock.json` |
| Inference | llama.cpp fork `/home/chao/llama.cpp-featcache` at `04ccc72a2207347ca76161b93fd9d846dd0a8675` (E21 window geometry: `cddb000c`) | runtime receipts `llama_cpp.build_commit` |
| Features | mmproj-free decode over pre-materialised speech packets, one packet root per (core, carrier) on ext4 | manifest `packet_roots[]`; baselines `speech_packet_promotion_receipt(_sha256)` |
| Serving | five geometries, one resident session per geometry | manifest `serving_geometries[]`; `scripts/flights/batch/serving_lib.sh` |
| Disk | hot root `/home/chao/saea-data` (ext4 VHDX 1), cold root `/mnt/wsl/saea-data-2` (ext4 VHDX 2, planned) | `scripts/lib/data_root.sh`; manifest `roots` |

## 3. (a) Model table

| Core | Lock key | GGUF on ext4 | GGUF sha256 | mmproj sha256 | Runtime receipt |
|---|---|---|---|---|---|
| Instruct | `qwen3-omni-30b-a3b-instruct-gguf-q4km` | `/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf` (18,557,053,952 B) | `0751c279...f98066d` | `f0dfe825...f122883` (2,207,465,568 B) | `docs/receipts/runtime-q4km-mmproj-free.json` |
| Thinking | `qwen3-omni-30b-a3b-thinking-gguf-q4km` | `/home/chao/models/qwen3-omni-30b-a3b-thinking-gguf-q4km/Qwen3-Omni-30B-A3B-Thinking-Q4_K_M.gguf` (18,557,053,248 B) | `afdaeff6...bd9bf4835` | `57b7240f...dacceda98b38` (2,207,465,664 B) | `docs/receipts/runtime-q4km-thinking-mmproj-free.json` |

Both fragments resolve the GGUF under `model_materialization_root: /home/chao` (ext4), so no model byte is read
from the data root on the serving path. The Q8_0 Instruct copy (`/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf`,
34.7 GB) is a W1 legacy asset that no live geometry names.

Serving geometries and decode knobs (all `temperature 0`, `id_slot per-sample`, `prompt_order
speech-query-prefix-v2`, `-fa on -ngl 999 -ctk q8_0 -ctv q8_0`):

| Target | Session id | Model fragment | -c / -np | max_tokens | seed | Packet root | Other knobs |
|---|---|---|---|---|---|---|---|
| slurp-np4 | `serving-slurp-native-candidate-five-train-a-np4-v1` | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` | 98304 / 4 | 512 | 20260913 | slurp-instruct | `--cache-prompt --cache-ram 0 --no-cache-idle-slots --slot-prompt-similarity 0`, `-b 2048 -ub 512` |
| a2t-np3 | `serving-a2t-native-role-base-np3-max2048-v3` | `q4km-mmproj-free-a2t-native-role-np3-max2048-v1` | 98304 / 3 | 2048 | 20260803 | a2t native-system-4000 | as slurp-np4 |
| e21-np4 | `serving-e21-native-window-flightruntime-np4-max1024-v1` | `q4km-e21-native-window-packets-cddb000c-np4-max1024-v1` | 98304 / 4 | 1024 | 20260915 | e21 dr-full | `GGML_CUDA_DISABLE_GRAPHS=1`; build `cddb000c` |
| det-np1 | `serving-slurp-native-det-np1-nocache-v1` | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1` | 24576 / 1 | 512 | 20260913 | slurp-instruct | `--no-cache-prompt` |
| think-np4 | `serving-slurp-thinking-direct-fold-b-np4-max8192-v1` | `q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1` | 98304 / 4 | 8192 | 20260913 | slurp-thinking | `--reasoning-format deepseek`; `reasoning_content_guard` |

## 4. (b) Feature table

| Packet root (ext4) | Core / carrier | Promotion receipts pinned (sha256 prefix) | Pinned by |
|---|---|---|---|
| `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` | Instruct / SLURP | EVO-FOLDS-V2 `4f048f47`, DEV-1000 `2accbdc5`, DEV-2000-ADDED `978fc638`, STAGE3-CONSTRUCTION-R01 `a1664e34`, TEST-SAMPLE-3010 `d0a827b6`, DEVEL-REMAINDER `e7e9b516` (21 receipts in the root) | 1,273 config objects name EVO-FOLDS-V2 (the Stage-3 TF-RL family), 64 DEV-1000, 60 R01, 19 DEV-2000-ADDED, 18 TRAIN90, 5 TEST-SAMPLE-3010 |
| `/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6` | Thinking / SLURP | EVO-FOLD-B-V2 `ef409ef4` | 2 (the 266-E Thinking direct baseline and its smoke) |
| `/home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a` | Instruct / Audio2Tool | receipt lives UNDER THE DATA ROOT: `prepared/SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1/promotion.json` `720d81f6` | 22 A2T baselines, by ABSOLUTE legacy path |
| `/home/chao/feat-cache/a2t-calibration-400-packets-04ccc72a` | Instruct / Audio2Tool | A2T-CALIBRATION-400 `2b848b86` | 3 |
| `/home/chao/feat-packets/e21-cddb000c-dr-full-gpu-v1`, `.../e21-cddb000c-loop-gpu-v1` | Instruct / Earnings-21 | window-feature-packets JSON under the data root `analysis/SAEA-E21-*-GPU-ENCODING-V1/` | E21 baselines, by ABSOLUTE legacy path |

Finding: three fragments name `/home/chao/feat-packets/e22-cddb000c-dev-gpu-v1`, which does not exist on this host
(only the two E21 roots do). E22 packets must be re-materialised or the fragments retired before any E22 contact.

Packets never move in this migration (they are already ext4). One packet set per mmproj: the Instruct and
Thinking audio-encoder tensors differ, so each core has its own root and its own promotion receipt.

## 5. (c) Disk layout

### 5.1 Measured sizes (2026-10-12; du over 9p, partly by the coordinator)

| Legacy subtree (`/mnt/e/.../speechrl-data/`) | Size | Class | Destination |
|---|---|---|---|
| runs | 78 GB | hot | VHDX 1 |
| coordination | 44.4 GB | hot | VHDX 1 |
| prepared (1,955 entries) | 11.7 GB | hot | VHDX 1 |
| analysis | 4.2 GB | hot | VHDX 1 |
| serving | 3.4 GB | hot | VHDX 1 |
| knowledge | 0.58 GB | hot | VHDX 1 |
| attempts, locks | < 1 MB | hot | VHDX 1 |
| system-text-search | 31.8 GB | runtime-read | VHDX 1 |
| wire-check | 9.0 GB | runtime-read | VHDX 1 |
| vectors | 3.7 GB | runtime-read (7,458 `root: data` pins) | VHDX 1 |
| repos, environments, manifests, trace-intermediates, preparation-runs, receipts, official-evaluator-source-bundles, references, provisional | 3.3 GB together | runtime-read | VHDX 1 |
| derived | 179 GB | runtime-read (8 `root: data` pins; derived-media roots) | VHDX 1 |
| _repro, survey-*, logs, program-archives, archive, working, research, settlements, telemetry, the four `saea-slurp-*-read-*` scratch dirs, loose CSV/log files, `.saea-runtime-identity-cache.json` | about 38 GB | historical | VHDX 1 (rest pass) |
| **VHDX 1 total** | **about 407 GB** | | `E:\saea-data-1.vhdx`, 2 TB dynamic |
| datasets | 1,028 GB | raw corpora (read per row: see 5.3) | VHDX 2 |
| models | 150 GB | GGUF archive copies (the live copies are on `/home/chao/models`, 71 GB) | VHDX 2 |
| **VHDX 2 total** | **about 1,178 GB** | | `E:\saea-data-2.vhdx`, about 1.3 TB dynamic |

Elsewhere on E: `speechrl-knowledge` 121 MB, `tools` 1 MB, `chao_workspace/exploring-l4-intelligence/runs` 1 MB
(move to VHDX 2 under `e-root/` in the cold pass), and `saea-ext4-test.vhdx` (776 MB, the coordinator's test
disk -- still present at 06:00Z; delete it). Already on the WSL root ext4 (`/dev/sdd`, 1,007 GB, 481 GB free):
`/home/chao/feat-cache` 105 GB, `/home/chao/feat-packets` 18 GB, `/home/chao/models` 71 GB,
`/home/chao/saea-worktrees` 103 GB.

E: arithmetic: 3.8 TB total. Both VHDX files are dynamic: fully grown they occupy 2.0 + 1.3 = 3.3 TB and E: keeps
about 0.5 TB of NTFS headroom (ruling 284). Deleting files inside an ext4 VHDX does not shrink the file; reclaim
needs `fstrim` inside WSL plus an offline compact, so the VHDX 2 size is set once, with 10 percent headroom over
the measured 1,178 GB. VHDX 2 at 1.3 TB leaves about 120 GB; decision 281 asks whether 1.4 TB is preferred.

### 5.2 Roots

| Root | Path | Filesystem | Role |
|---|---|---|---|
| hot (data root after cut-over) | `/home/chao/saea-data` -> `/mnt/wsl/saea-data-1` | ext4, VHDX 1, attached at logon by `SAEA-Mount-Data1` | the single working copy of everything a preparation, flight, seal or read touches |
| cold | `/mnt/wsl/saea-data-2` | ext4, VHDX 2 (planned) | `datasets/`, `models/` archive, the small E: remainder |
| legacy | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data` | 9p (NTFS) | migration source; deleted after owner review; then a compatibility link (section 6.4) |
| runtime / features / worktrees | `/home/chao`, `/home/chao/feat-cache`, `/home/chao/feat-packets`, `/home/chao/saea-worktrees` | ext4 (WSL root) | unchanged |
| repo master | `/mnt/d/.../speech-aware-evidence-acquisition` | 9p | single writer, not a hot path (exempt) |

The no-duplication rule (one working copy plus one archive per dataset) holds: VHDX 1 is the working copy of the
data root, VHDX 2 is the archive of raw corpora and model files, and E: NTFS keeps neither once step 3 completes.
Both VHDX files sit on the same physical disk as before, so this layout adds speed, not redundancy; an off-disk
backup is decision 283.

### 5.3 `datasets/` and `models/` from the hot root

The runtime reads raw audio during a flight even on the packet path: `rails/core_client.py` hashes each bound
sample's audio (`audio_sha256`, line 440) and probes its sample rate (line 681) when the client is built, and the
raw-native arm hashes the media per contact. So `datasets/<carrier>/` is a per-row read and must be reachable
under the data root. The hot root reaches it through two symlinks, `datasets -> <cold>/datasets` and
`models -> <cold>/models` (`migrate_data_root_ext4.sh --link-cold`). Confinement still holds: carriers confine
media to the RESOLVED carrier directory (`core/model/paths.py::_resolve_confined_any` resolves both sides), and no
`root: data` source-receipt pin in `configs/` names `datasets/` or `models/` (measured: the 15,784 such pins name
only coordination, derived, knowledge, runs, prepared, preparation-runs and vectors). `derived/` must NOT be a
symlink: 8 `root: data` pins name `derived/slurp-kus4/...`, and a pin whose resolved path leaves the resolved data
root is refused. Until VHDX 2 exists the links point at the legacy E: directories (9p, today's speed).

## 6. Absolute-path inventory (what binds the data root's location)

Verification of the decision-270 agent's claim ("relocating the data root is a PATH change that does not touch the
identity-bound files"): TRUE for the files -- no edit to `core/flight/runtime.py`, `rails/knowledge_stores.py` or
any other implementation-hashed module is needed -- but FALSE for three identity or receipt surfaces that bind the
resolved absolute root. Full list:

| Surface | What it records | Compared by | Effect of the cut-over |
|---|---|---|---|
| Prepared supply identity (`core/preparation.py::artifact_inputs`) | `config_sha256` over the composed config + sources; knowledge snapshots by `knowledge_snapshot_relpath`, source receipts as `{root, relpath, sha256}` | `load_artifact` at flight time | none for SLURP (packet paths are `/home/chao/feat-cache/...`); A2T/E21 configs that name `/mnt/e/...` absolutely keep their identity as long as their TEXT is unchanged (they then resolve through 6.4); editing them to the new root is a re-pin |
| Serving profile identity (`runtime.py` around line 5796) | `data_root.resolve()`, `runtime_root.resolve()`, model fragment, receipt, argv | session attach | the resident session no longer matches: restart every serving session after the cut-over (planned: its directory moves anyway) |
| Fit-monitor ownership receipt (`core/flight/coordinator.py` 228/272) | `str(data_root)` | monitor reuse | restart the monitor with the session |
| Hypothesis-source artifacts (`core/bundle/hypothesis_source.py` 144/175) | `data_root.resolve()` inside `artifact_inputs` | its own load | the SLURP intent/distinct hypothesis sources must be re-prepared before reuse (historical, no live cell) |
| Semantic authoring registration (`core/semantic_authoring_support.py` 272) | registration `data_root` | `resolve()` equality | refused while the legacy directory is real; equal again once 6.4's link resolves to the hot root |
| Bundle delivery manifests (`core/bundle/delivery.py` 276/410) | `data_root.resolve()` | self-consistent re-verification | historical; readable through 6.4 |
| Runtime identity cache (`.saea-runtime-identity-cache.json`) | GGUF size + mtime + inode/device | gate fast path | every entry misses once (new inode): the first gate open pays one full GGUF hash |
| Flight lock (`locks/flight.lock`), session receipts (`serving/<sid>/session.json`) | relative to the data root; session dirs record absolute paths for the record | none across roots | none (a new session writes new receipts) |
| 22 A2T baselines (`speech_packet_promotion_receipt`), E21/E22 baselines (window-feature-packets), preparation configs (`data_root`, `*_output_path`), analysis configs | absolute `/mnt/e/...` strings | config identity | frozen; frozen text keeps working through 6.4 |
| 341 frozen files under `scripts/ src/ configs/ tests/` | the legacy literal | none | ratchet baseline `scripts/checks/engineering_base_locator_baseline.json`; new files are refused |
| Live operations scripts (24) | -- | -- | now read `scripts/lib/data_root.sh` (section 8) |

### 6.4 Compatibility link after step 3

When the owner has approved deletion of the E: originals, replace the emptied
`/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data` directory with a WSL symlink to
`/home/chao/saea-data` (created from WSL, it is an LX symlink on NTFS that only WSL follows). Every frozen absolute
path then resolves to the hot root on ext4: the path walk crosses 9p once for the link itself, and every byte comes
from the VHDX. Windows-native tools cannot follow it (the same is true of the existing earnings22 media links).
Decision 279.


### 6.5 Literal sweep (owner rulings 289 B / 290 B, 2026-10-12) -- supersedes the baseline and the compatibility link

The 341 frozen files were rewritten: configs spell `${SAEA_DATA_ROOT}` (`core/data_root_placeholder.py`; `compose()` hashes the
unexpanded text and hands consumers expanded values; the preparation, promotion and pinned-document loaders expand what they
read), shell scripts source `scripts/lib/data_root.sh` and call `saea_data_root_init`, Python scripts and tests read
`SAEA_DATA_ROOT` / `SPEECHRL_DATA_DIR`. The ratchet baseline is empty and the locator gate refuses any hard-coded data-root path
(`/mnt/e/chao_workspace`, `/mnt/e/.../speechrl-data`, the manifest's legacy root) and a non-empty baseline. No compatibility
link is created after step 3. Host mode also refuses E: free space under 500 GB (decision 291). Historical receipts under `docs/`
are immutable and keep their literals.

## 7. (d) Migration plan

### 7.1 What must not run

During the copy (steps M2-M5) and the cut-over (M6): no flight, no `core.flight.cli` campaign/worker/check, no
lease, no flip or re-pin, no serving start, swap or restart, no packet preprocess sidecar. The tool refuses
`--execute` while any of these is alive, while `locks/flight.lock` exists, while a swap is pending, or while a
llama-server listens on the GPU port (the serving session directory moves too). The migration starts only after
the flying i3 column has sealed and its ledger rows are consumed (owner, 2026-10-12).

### 7.2 Runbook (exact commands, WSL `Ubuntu-24.04`)

```
# M0  preconditions (read-only)
findmnt -T /home/chao/saea-data          # /mnt/wsl/saea-data-1 ext4
python -B scripts/checks/engineering_base_locator_check.py --host --require-hot-mounted
bash scripts/data/migrate_data_root_ext4.sh                      # dry-run: plan + preflight verdict
# M1  stop the resident serving session (serving_swap.sh / serving_session.sh stop) and the monitor; confirm
#     no driver, flip or sidecar is alive; the dry-run must print "--execute would proceed"
# M2  hot subtrees, owner order
bash scripts/data/migrate_data_root_ext4.sh --phase hot --execute
# M3  the other runtime-read subtrees
bash scripts/data/migrate_data_root_ext4.sh --phase runtime --execute
# M4  derived (179 GB)
bash scripts/data/migrate_data_root_ext4.sh --phase derived --execute
# M5  the rest of the root (historical subtrees and loose files; never datasets/ or models/)
bash scripts/data/migrate_data_root_ext4.sh --phase rest --execute
# M5b interim links to the E: corpora and model archive (9p, today's speed) until VHDX 2 exists
bash scripts/data/migrate_data_root_ext4.sh --link-cold /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data --execute
# M6  cut-over: one commit (section 7.3); then restart serving on the new root; run the gates
python -B scripts/checks/engineering_base_locator_check.py --host --require-hot-mounted
python -B scripts/checks/engineering_base_timing.py --repo /home/chao/saea-worktrees/fable-batch-flight \
    --root /home/chao/saea-data --out docs/checks/speech-aware-evidence-acquisition/2026-10-12-engineering-base-timing/post-cut-over.json
# M7  owner reads <hot>/receipts/migration-ext4/run-*/receipt.json and the per-subtree manifests
# M8  (step 3, owner GO) delete the E: originals of the migrated subtrees; create the compatibility link (6.4);
#     create VHDX 2 (1.3 TB), attach it (second logon task SAEA-Mount-Data2), then
bash scripts/data/migrate_data_root_ext4.sh --phase cold --target /mnt/wsl/saea-data-2/speechrl-data --execute
bash scripts/data/migrate_data_root_ext4.sh --link-cold /mnt/wsl/saea-data-2/speechrl-data --execute
#     owner reads the cold receipts; delete E:/.../datasets and models; E: keeps only NTFS headroom
```

Each `--execute` per subtree: `rsync -aH --numeric-ids` (idempotent), absolute symlinks into the source root
re-pointed to the target root (listed per subtree), then a sorted `relpath, size, sha256` manifest of every regular
file on BOTH sides with `--jobs` hashing workers (default 8, the campaign ceiling), byte-compared; a subtree is
VERIFIED only when the two manifests are identical. Receipts: `<target>/receipts/migration-ext4/<run-id>/receipt.json`
plus `<subtree>.source.sha256.tsv`, `.target.sha256.tsv`, `.symlinks.tsv`, `.symlinks-repointed.tsv`. The source is
never written. A re-run copies only differences; a target that holds files the source does not is reported as a
MISMATCH (exit 4), never silently deleted.

Time estimate at the measured 9p rates (193 MB/s sequential, much lower for small files): about 407 GB to VHDX 1
is 35 minutes of pure transfer, realistically 2-3 hours with the small-file subtrees (runs, coordination) plus one
more full 9p read for the source manifest; the cold pass (1.18 TB) is a further 3-5 hours. M2 alone (hot set,
about 142 GB) is the part that must finish before the next flight.

### 7.3 Cut-over diff (one commit, plus two host edits)

1. `scripts/lib/data_root.sh`: `SAEA_DATA_ROOT_DEFAULT=/mnt/e/.../speechrl-data` becomes
   `SAEA_DATA_ROOT_DEFAULT=/home/chao/saea-data`. This is the only line any live script reads.
2. `configs/base/engineering-base-v1.json`: `roots.data_root.current` becomes `/home/chao/saea-data`, `status`
   becomes `cut-over` (the gate refuses the two disagreeing).
3. Umbrella `CLAUDE.md` and `AGENTS.md`, Environment section: the line "Data/checkpoints/outputs live at
   `/mnt/e/...` (`SPEECHRL_DATA_DIR`)" becomes two lines: "Hot data root (working copy):
   `/home/chao/saea-data` (= `/mnt/wsl/saea-data-1`, ext4 VHDX `E:\saea-data-1.vhdx`, attached at logon by
   `SAEA-Mount-Data1`); `SPEECHRL_DATA_DIR` names it." and "Archive: raw `datasets/` and `models/` on
   `/mnt/wsl/saea-data-2` (ext4 VHDX on E:), reached through links under the hot root; E: NTFS holds no study data."
4. Host, outside Git: `~/.bashrc` line 2 `export SPEECHRL_DATA_DIR=...` to the hot root (otherwise every live script
   refuses with the decision-274 split-brain message, by design); the scheduled tasks need no edit (their entry
   scripts read the authority); the queue wrappers under `/home/chao/saea-queue/` were not audited by this task
   and must be checked for the legacy literal before the first post-cut-over queue run.
5. Serving: start each needed geometry fresh on the new root (its identity binds the root, section 6).

The batch driver is read by bash from master while it runs; never merge a change to `batch_driver.sh` (this branch
included) while a driver process is alive.

### 7.4 Rollback

Before step 3 the legacy root is untouched: revert the cut-over commit (the default line returns to E:), restore
`~/.bashrc`, restart serving on the legacy root. Anything written to the hot root after the cut-over must be
copied back first with the same tool (`--source /home/chao/saea-data --target <legacy>`; dry-run first). After
step 3 there is no rollback to E:; the VHDX files are the data.

## 8. (e) Efficiency gate and timing

`scripts/lib/data_root.sh` (sourced by the 24 live scripts declared in the manifest): `saea_data_root_init`
resolves `SAEA_DATA_ROOT` (an explicit value wins; otherwise the one default line), exports it and
`SPEECHRL_DATA_DIR`, refuses a split brain (the implicit default meeting an inherited `SPEECHRL_DATA_DIR` naming
another root), and runs `saea_data_root_guard`: the root must exist and, unless it is the legacy E: original,
resolve to a mounted ext4 (`findmnt -T`, falling back to `stat -f`). After the cut-over a driver, chain, flip,
preparation or serving entry therefore refuses to start when VHDX 1 is not attached (the hot-root symlink
dangles) or when someone recreated `/mnt/wsl/saea-data-1` as a plain directory on the `/mnt/wsl` tmpfs.

`scripts/checks/engineering_base_locator_check.py`:

| Rule | Mode | Refuses |
|---|---|---|
| manifest | always | a malformed manifest (exit 2) |
| authority | always | a default/hot/legacy line that disagrees with the manifest, or a status that disagrees with the current root |
| live | always | a live script that hard-codes the legacy root, does not source the authority, or (entry) never calls `saea_data_root_init` |
| ratchet | always | a NEW file under `scripts/ src/ configs/ tests/` carrying the legacy literal (341 frozen files baselined) |
| models | always | a runtime receipt or umbrella lock entry that does not pin the declared GGUF/mmproj sha256 and build commit |
| geometry | always | a model fragment or `serving_lib.sh` row that disagrees with the manifest (lock key, -c, -np, max_tokens, packet root, decoder sha, session id) |
| hot-fs | `--host` | a hot path that resolves to 9p, drvfs, tmpfs, fuse or overlay (the legacy data root is a WARN until cut-over) |
| hot-mount | `--host` | an unattached hot root (FAIL after cut-over or with `--require-hot-mounted`, WARN before) |
| assets | `--host` | a model file of the wrong size (no GGUF re-hash), a missing packet root, a promotion receipt that does not hash to its pin |

`scripts/checks/engineering_base_timing.py` writes a model-free receipt: CLI import, `git status`, one knowledge
snapshot load and a 2,000-file stat+read, per checkout and per root, against the manifest's budget (seconds):
import 2, git status 1, snapshot load 2, small files 3; flight facts (cli check 60, campaign prelude 300, seal 300)
are read from the next flight's `batch-status.jsonl`. The first receipts (pre-cut-over, 2026-10-12 ~11:00Z, while
the i3 column was flying) are committed under `docs/checks/speech-aware-evidence-acquisition/2026-10-12-engineering-base-timing/`:

| Measure | ext4 (`/home/chao/saea-worktrees/opus-base-unify`) | 9p | Budget |
|---|---|---|---|
| `core.flight.cli` import | 0.76 s | 2.89 s (master on `/mnt/d`, warm page cache; 38 s cold per decision 267) | 2 s |
| `git status` | 0.30 s | 199.3 s (master on `/mnt/d`, under campaign I/O load) | 1 s |
| knowledge snapshot load (13.9 MB, `size-pool-annotated-exemplars-minus-r01`) | -- (hot root still empty) | 0.18 s (legacy root, warm) | 2 s |
| stat + read, scaled to 2,000 files | 0.06 s (500 config files) | 78.2 s (200 files under `knowledge/` read in 7.8 s) | 3 s |

The 9p small-file rate, not the large-file rate, is what the prelude pays: a campaign prelude stats and reads
thousands of receipts, rosters and run files under `runs/`, `coordination/` and `prepared/`.

## 9. (f) The manifest as a pin

`configs/base/engineering-base-v1.json` (schema `saea-engineering-base-v1`) holds `roots`, `hot_paths`, `migration`
(subtree classes), `models`, `packet_roots` (with promotion-receipt pins), `serving_geometries`, `live_scripts`
and `timing_budget`. A future registration may pin it as a frozen source receipt
(`{"root": "repository", "relpath": "configs/base/engineering-base-v1.json", "sha256": ...}`), which makes "this
cell ran on base v1" machine-checkable. It is deliberately NOT added to any existing cell now: a new key in a
registered config moves `config_sha256` and would invalidate prepared supplies. A changed model, packet root or
disk layout is a new manifest (`engineering-base-v2.json`), never an edit in place once a cell pins v1.

Worktree hygiene (coordinator request): `git worktree list` (from WSL) shows 116 registered worktrees -- 89 on
branches already merged into master, 23 detached, 4 on unmerged codex branches -- while
`/home/chao/saea-worktrees` holds about 320 entries (103 GB). Proposed cleanup, from WSL only (never prune from
Windows: Windows git sees every WSL worktree as prunable): `git worktree remove` each merged-branch worktree except
`fable-batch-flight`, `fable-flip` and any worktree a running task names; a detached worktree only when its HEAD
is an ancestor of master and it holds no untracked files; leave the four unmerged codex branches to their owner;
list the unregistered directories for a separate owner decision. Decision 282.

## 10. Decisions for the owner

- **275 (base v1).** Adopt `configs/base/engineering-base-v1.json` as the declared engineering base (two cores, five
  geometries, the packet roots above), with the locator gate in the standard gate list. A: adopt. B: adopt the gate
  only.
- **276 (cut-over moment).** The cut-over (7.3) happens in the first idle window after the i3 column seals and M2-M5
  verify, before any new flight is queued. A: that window. B: after the next column.
- **277 (what M2 must cover before the next flight).** A: everything except datasets/models (M2-M5, about 407 GB).
  B: M2 + M3 only (hot + runtime-read, about 190 GB) and derived/rest later -- faster, but derived media reads stay
  on 9p until M4.
- **278 (raw datasets).** Datasets stay on the cold VHDX behind a symlink (5.3). A: as designed. B: put the four
  carriers' corpora (slurp, audio2tool, earnings21-22, conec) on VHDX 1 as real directories and only the rest of
  `datasets/` on VHDX 2.
- **279 (compatibility link).** After step 3, replace the E: directory by a WSL symlink to the hot root so the 341
  frozen absolute paths keep resolving (6.4). A: create it. B: re-pin instead (moves identities of the A2T/E21
  baselines).
- **280 (A2T/E21 absolute pins).** Leave the 22 A2T and the E21/E22 baselines' absolute `/mnt/e` pins frozen
  (resolved via 279) and write new carrier cells with paths relative to the data root. A: as stated. B: re-pin the
  live A2T/E21 cells to the hot root at their next registration.
- **281 (VHDX 2 size).** A: 1.3 TB (ruling 284; about 120 GB headroom over 1,178 GB measured). B: 1.4 TB (E: keeps
  about 400 GB).
- **282 (worktree cleanup).** Remove the 88 merged-branch worktrees and ancestor-of-master detached ones from WSL
  (9). A: do it now (model-free). B: after the cut-over.
- **283 (backup).** Both VHDX files and their source sit on one physical disk. A: accept for now. B: add a periodic
  copy of the sealed subtrees (runs, prepared, coordination, knowledge) to a second device.
- **284 (hot root).** Ruled 2026-10-12: a 2 TB ext4 VHDX on E: (`E:\saea-data-1.vhdx`, `/mnt/wsl/saea-data-1`,
  stable path `/home/chao/saea-data`, logon task `SAEA-Mount-Data1`); migrate; delete the E: originals only after
  the owner has read the verification manifests; then a second VHDX (about 1.3 TB) for datasets and models, leaving
  about 500 GB of NTFS headroom. Not reformatting E: (1.6 TB would have to move first and Windows would lose the
  disk). `wsl --mount` is not persistent across reboots or `wsl --shutdown`; the logon task re-attaches it and every
  live entry script refuses to start when it is absent (section 8).

## Amendment 296 (coordinator, 2026-10-12)

The hot data root is `/home/chao/saea-data/speechrl-data`, the directory inside the disk-1 mount (`/mnt/wsl/saea-data-1/speechrl-data`
behind the symlink `/home/chao/saea-data`), not the mount root: name parity with the E: layout and the umbrella's `SPEECHRL_DATA_DIR`, and
the static migration lanes already copied there. Every mention of `/home/chao/saea-data` as the data root above reads as that directory;
the locator `hot-mount` rule accepts a directory on a mounted ext4 other than the root filesystem. Migration receipts are written outside
the data root during the verification pass (the verifier compares full manifests) and copied into `<hot>/receipts/migration-ext4/` after it.
