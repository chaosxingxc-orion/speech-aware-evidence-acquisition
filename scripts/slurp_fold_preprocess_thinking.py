#!/usr/bin/env python3
"""Thinking-core speech-packet preparation over TRAIN Fold B (owner decision 266-E, 2026-10-11).

LIVE exposure row ``SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1`` (package
``docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/``), a GPU encoder pass. The Instruct speech packets are
decoder-ready outputs of the Instruct audio encoder; 748 of 860 mmproj tensors differ in the Thinking model (the audio-encoder tensors:
475 of 522 ``a.`` tensors and all 8 ``mm.`` projector tensors by data hash), so the Thinking arm needs its OWN packet root, prepared by an
encoder pass over the same 1,080 Fold B rows.

SUPERSEDED geometry (``--geometry cpu --allow-cpu``, kept for the record): the first pass ran the encoder on a CPU sidecar
(``-np 4 -ngl 0 --no-mmproj-offload``) at 16-19 s per row; the owner stopped it after 50 of 1,076 Fold B rows (run id
``SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1``, attempt ``attempt-packets-thinking-fold-b-v1``, its one recovery already spent on the
smoke). The GPU pass is a re-registration under a NEW run id with its OWN packet root and legacy cache, because CPU- and GPU-made encoder
outputs are not bit-identical and must never mix.

This is the Thinking sibling of ``scripts/slurp_evo_fold_preprocess.py``. It does NOT modify that driver: it loads it as a
module and reuses its parameterised helpers verbatim (roster sample construction with per-file media re-hash, the additive
refuse-on-conflict promotion, the promotion receipt document, the create-only receipt writer), so the packet format, the
promotion receipt shape and the roster logic are the Instruct ones by construction. What is Thinking-specific and lives here:

- the model pins: the Thinking decoder and its own bf16 mmproj come from the umbrella lock entry
  ``qwen3-omni-30b-a3b-thinking-gguf-q4km`` through ``scripts/flights/direct/direct_fb_pins.py`` (local hash receipts proven
  equal to the lock text) and must equal the committed runtime receipt of the active geometry
  (``docs/receipts/runtime-q4km-thinking-preprocess-gpu.json``);
- the roots: packet root ``/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6``, legacy cache
  ``/home/chao/feat-cache/slurp-thinking-gpu-q4km``, promotion receipt ``EVO-FOLD-B-V2-promotion.json`` under the new root;
- the refusals: pins that disagree with the lock or the runtime receipt, a packet root that exists and is not empty, a missing
  exposure row, an exposure row that is not root-countersigned (``--run`` only), an already-consumed row, the CPU geometry without
  ``--allow-cpu``, and (``--run`` on the GPU geometry only) ANY resident serving session, a listener on the serving port, or GPU memory
  in use: the card holds one core, so the GPU encoder server starts only inside a serving-swap window with the card empty;
- the encoder receipt ``encoder-receipt.json`` under the run directory: the device (``gpu`` / ``cpu``), llama.cpp build commit, decoder and
  mmproj sha256, roster split identity, per-file hashes (packet sha256 and chunk feature sha256 for Fold B, legacy cache file sha256 for the
  smoke), worker counts, timings and seconds per row.

Two rosters, one run id (the plan budget is run-cumulative):

``thinking-smoke-4``  the first four Fold B rows (the prefix the 266-E smoke flies; checked against the committed smoke roster
                      receipt) encoded into the legacy cache ONLY. No packet is materialised and no promotion receipt is
                      written, so the packet root stays empty. It proves the Thinking sidecar loads and encodes, and measures
                      rows per minute.
``thinking-fold-b``   the 1,080 Fold B rows. Rows already warm in the legacy cache (the smoke's four) are NOT contacted again,
                      so the run makes exactly 1,080 contacts across both attempts, the row's declared total. After a verified
                      normal sidecar stop all 1,080 are promoted into the empty packet root and the promotion receipt is
                      written (create-only).

Modes::

    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-smoke-4 --dry-run
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-fold-b --dry-run
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-smoke-4 --run      # via direct_fb_packets_gpu.sh (--geometry gpu)
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-fold-b --run       # via direct_fb_packets_gpu.sh (--geometry gpu)
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-fold-b --promote-only --attempt-id <new>
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-dev2000-added --dry-run       # P3.1: the DEV-2000-ADDED Thinking packets
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-dev2000-added --run           # via direct_fb_packets_gpu.sh --stage dev2000-added
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-dev2000-added --check-ledger  # exit 0 only if countersigned
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-dev2000-added --pin-receipt   # verification only (DEV cells pin the sha at derive time)
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-test-sample-3010 --dry-run       # successor 3: the sample Thinking packets (contacts nothing)
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-test-sample-3010 --run           # via direct_fb_packets_gpu.sh --stage test-sample-3010
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-test-sample-3010 --check-ledger  # exit 0 only if countersigned
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-test-sample-3010 --pin-receipt   # verification only (the successor-3 cells pin the sha at derive time)
    python -B scripts/slurp_fold_preprocess_thinking.py --check-ledger                       # exit 0 only if countersigned
    python -B scripts/slurp_fold_preprocess_thinking.py --smoke-rate                        # exit 0 only if the measured rate fits the cap
    python -B scripts/slurp_fold_preprocess_thinking.py --pin-receipt [--write]              # model-free

``--geometry`` is ``gpu`` (default; one worker at the server's own ``-np 1`` batching) or ``cpu`` (superseded; refused without ``--allow-cpu``).
``--dry-run`` prints the plan (rows, roots, pins, ledger state, serving/GPU state as information) and makes no encoder call, opens no media
file and starts no process; it never refuses over a resident serving session (the pre-window check runs it while the card is occupied). ``--pin-receipt`` verifies the written promotion receipt against the pins, the runtime receipt and the packets on disk
and substitutes its sha256 for the zero sentinel in the two Thinking baselines (printed only without ``--write``).

``thinking-dev2000-added`` (P3.1, registry "P3 programme under decision 299 A") is the DEV-2000-ADDED roster: 1,000 ``slurp:devel:`` rows with
``split_role="dev"``, encoded on the GPU into its OWN legacy cache and promoted ADDITIVELY into the existing Thinking packet root under the NEW
receipt ``DEV-2000-ADDED-promotion.json`` (the Fold B receipt and packets are never touched; the packet root may already be populated by Fold B).
Its run id, sidecar fragment (own cache dir), experiment fragment and row totals are :data:`DEV_SPEC`; the Fold B rosters are unchanged.

``thinking-test-sample-3010`` (successor 3, the Thinking system on the signed SLURP test sample) is the DEV form on the 3,010 ``slurp:test:`` rows of
``SLURP-TEST-SAMPLE-3010-V1`` (:data:`SAMPLE_SPEC`): run id ``SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1``, its own legacy cache, ADDITIVE
promotion into the existing Thinking packet root under the NEW receipt ``TEST-SAMPLE-3010-promotion.json`` (Fold B and DEV receipts are never touched). Its
split role is ``final-report``, so ``contracts.plan.require_owner_split_allowance`` gates it exactly as it gates the Instruct sample pass
(``scripts/slurp_evo_fold_preprocess.py --roster test-sample-3010``): the experiment fragment pins ``owner_allowance`` and the dry-run and every
media-reading mode refuse unless the pinned allowance is ``authorised`` and lists this run id in ``preparation_run_ids``. The guard is never weakened.
The pass is label-free: it opens media and media identity only, never a transcript, label or model output.

Label-free by construction: samples come from the frozen runtime view of Fold B, which carries media identity and nothing else.
No gold, transcript or model output is opened, read or printed; the one-token responses are discarded unread.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, NamedTuple, Sequence

REPO = Path(__file__).resolve().parent.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreadable checkout
        raise SystemExit("cannot import %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The Instruct driver (unchanged) enforces PYTHONDONTWRITEBYTECODE=1 and the literal PYTHONPATH on import, exactly as it does
# for its own callers, and refuses a package that resolves outside this checkout.
evo = _load("slurp_evo_fold_preprocess_instruct_driver", REPO / "scripts" / "slurp_evo_fold_preprocess.py")
fam = _load("direct_fb_family_for_packets", REPO / "scripts" / "flights" / "direct" / "direct_fb_family.py")
pins_mod = _load("direct_fb_pins_for_packets", REPO / "scripts" / "flights" / "direct" / "direct_fb_pins.py")

from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables  # noqa: E402
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    PROMOTION_MODE_ENCODE_AND_PROMOTE, PROMOTION_MODE_PROMOTE_ONLY, inspect_legacy_cached_speech_feature_cache,
    load_speech_feature_packet, load_speech_packet_promotion_receipt)

DATASET_FRAGMENT = fam.DATASET
BASELINE_FRAGMENT = evo.BASELINE_FRAGMENT
LOCK_KEY = pins_mod.LOCK_KEY


class Geometry(NamedTuple):
    """One encoder geometry of the Thinking packet preparation: its run id, fragments, receipt, roots and ledger arithmetic."""

    key: str
    device: str                      # "gpu" | "cpu": recorded in the encoder receipt
    run_id: str
    sidecar_fragment: str
    experiment_fragment: str
    runtime_receipt_relpath: str     # relative to <repo>/docs/, as FrozenCoreGate.for_study_repo takes it
    packet_root: Path
    legacy_cache: Path
    promotion_receipt: Path
    row_calls: int                   # the ledger row's call ceiling before any failed-attempt spend
    smoke_in_row: bool               # True: the row's calls / speech seconds also carry the 4-row smoke (the re-registration's 1,084 / 3,165)
    smoke_attempt: str
    fold_attempt: str
    default_workers: int
    session_tag: str
    offload: str


ROW_CALLS = fam.ROWS
#: The CPU row's registered speech-seconds total (kept for the record; the GPU row derives its total from the roster).
ROW_SPEECH_SECONDS = 3155
SMOKE_SPEECH_SECONDS = 10
#: The row's registered gpu-hours cell. The frozen-core gate compares the plan's gpu hours with the row's, so the ledger check must too
#: (first real run, 2026-10-11 10:41Z: the row said 0.0 and the plan claimed 1.0; the gate refused after --check-ledger had passed).
ROW_GPU_HOURS = 1.0

GEOMETRIES: dict[str, Geometry] = {
    "gpu": Geometry(
        key="gpu", device="gpu", run_id=fam.PACKETS_ROW_ID, sidecar_fragment=pins_mod.PREPROCESS_FRAGMENT,
        experiment_fragment="slurp-direct-fold-b-thinking-preprocess-gpu-v1",
        runtime_receipt_relpath=pins_mod.PREPROCESS_RECEIPT.removeprefix("docs/"),
        packet_root=Path(fam.THINK_PACKET_ROOT), legacy_cache=Path(pins_mod.THINKING_LEGACY_CACHE),
        promotion_receipt=Path(fam.THINK_PROMOTION_RECEIPT), row_calls=ROW_CALLS + fam.SMOKE_ROWS, smoke_in_row=True,
        smoke_attempt="attempt-packets-thinking-gpu-smoke-4-v1", fold_attempt="attempt-packets-thinking-gpu-fold-b-v1",
        default_workers=1, session_tag="gpu-encoder", offload="-ngl 999 (decoder and bf16 mmproj on the GPU), -np 1"),
    "cpu": Geometry(
        key="cpu", device="cpu", run_id=fam.CPU_PACKETS_ROW_ID, sidecar_fragment=pins_mod.PREPROCESS_FRAGMENT_CPU,
        experiment_fragment="slurp-direct-fold-b-thinking-preprocess-v1",
        runtime_receipt_relpath=pins_mod.PREPROCESS_RECEIPT_CPU.removeprefix("docs/"),
        packet_root=Path(fam.CPU_THINK_PACKET_ROOT), legacy_cache=Path(pins_mod.CPU_THINKING_LEGACY_CACHE),
        promotion_receipt=Path(fam.CPU_THINK_PROMOTION_RECEIPT), row_calls=ROW_CALLS, smoke_in_row=False,
        smoke_attempt="attempt-packets-thinking-smoke-4-v1", fold_attempt="attempt-packets-thinking-fold-b-v1",
        default_workers=4, session_tag="cpu-sidecar", offload="-ngl 0 --no-mmproj-offload"),
}
#: The ACTIVE geometry's values, rebound by ``apply_geometry`` (the GPU geometry is the default at import).
GEOMETRY = GEOMETRIES["gpu"]
RUN_ID = GEOMETRY.run_id
SIDECAR_FRAGMENT = GEOMETRY.sidecar_fragment
EXPERIMENT_FRAGMENT = GEOMETRY.experiment_fragment
#: Relative to ``<repo>/docs/``, as ``FrozenCoreGate.for_study_repo`` takes it; equals the sidecar fragment's ``runtime_receipt``.
RUNTIME_RECEIPT_RELPATH = GEOMETRY.runtime_receipt_relpath
PACKET_ROOT = GEOMETRY.packet_root
LEGACY_CACHE = GEOMETRY.legacy_cache
PROMOTION_RECEIPT = GEOMETRY.promotion_receipt
LEDGER_RELPATH = "docs/exposure-ledger.md"
BASELINES = (
    "configs/baseline/slurp-direct-only-fold-b-thinking-baseline-v1.json",
    "configs/baseline/slurp-direct-only-fold-b-thinking-smoke-4-baseline-v1.json",
)
ENCODER_RECEIPT_NAME = "encoder-receipt.json"
ENCODER_RECEIPT_SCHEMA = "saea-thinking-packet-encoder-receipt-v2"
PLAN_SCHEMA = "saea-thinking-packet-plan-v1"
EXECUTION_PROFILE = "bounded-discovery-probe"
DRAFT_TOKEN = re.compile(r"\bdraft\b", re.IGNORECASE)
COUNTERSIGNED_TOKEN = re.compile(r"root countersigned", re.IGNORECASE)


class DevSpec(NamedTuple):
    """What a DEV-style Thinking roster changes against the Fold B one: its own run id, fragments, cache, receipt and row totals (P3.1)."""

    run_id: str
    sidecar_fragment: str
    experiment_fragment: str
    dataset_fragment: str
    sample_id_prefix: str
    split_role: str
    packet_root: Path          # the EXISTING Thinking packet root (additive promotion)
    legacy_cache: Path         # its OWN legacy cache: a Fold B cache entry would be a foreign entry for this roster
    promotion_receipt: Path    # NEW receipt under the existing root
    roster_receipt: str        # repo-relative roster receipt whose split identity the view must carry
    expected_rows: int
    row_calls: int             # the ledger row total of calls before any failed-attempt spend
    row_speech_seconds: int
    label: str = "DEV-2000-ADDED"   # the roster's name in messages


#: Mirrors ``scripts/flights/direct/thinking_system_dev_family`` (a test asserts the equality).
DEV_SPEC = DevSpec(
    run_id="SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1",
    sidecar_fragment="q4km-thinking-feature-preprocess-gpu-np1-dev2000-added-v1",
    experiment_fragment="slurp-dev2000-added-thinking-preprocess-gpu-v1",
    dataset_fragment="slurp-speech-native-dev2000-added",
    sample_id_prefix="slurp:devel:",
    split_role="dev",
    packet_root=Path(fam.THINK_PACKET_ROOT),
    legacy_cache=Path("/home/chao/feat-cache/slurp-thinking-gpu-q4km-dev2000-added"),
    promotion_receipt=Path(fam.THINK_PACKET_ROOT) / "DEV-2000-ADDED-promotion.json",
    roster_receipt="docs/receipts/rosters/slurp-dev-2000-added-v1.json",
    expected_rows=1000, row_calls=1000, row_speech_seconds=2984,
)
DEV_ROSTER_KEY = "thinking-dev2000-added"

#: Successor 3 (the Thinking system on the signed SLURP test sample, allowance ``docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json``):
#: the DEV form on the 3,010 ``slurp:test:`` rows. The split role is ``final-report``: the composed config carries ``owner_allowance`` and EVERY
#: mode that can reach the media (``--run``, ``--promote-only``) and the dry-run refuse unless ``contracts.plan.require_owner_split_allowance`` accepts
#: it for THIS run id (the successor-1 packets pass, ``SAEA-SN-TEST-SAMPLE-3010-PREPROCESS``, passed the same guard through its allowance's
#: ``preparation_run_ids``). Mirrors ``scripts/flights/nx/successor3_thinking_family`` (a test asserts the equality).
SAMPLE_SPEC = DevSpec(
    run_id="SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1",
    sidecar_fragment="q4km-thinking-feature-preprocess-gpu-np1-test-sample-3010-v1",
    experiment_fragment="slurp-test-sample-3010-thinking-preprocess-gpu-v1",
    dataset_fragment="slurp-speech-native-test-sample-3010",
    sample_id_prefix="slurp:test:",
    split_role="final-report",
    packet_root=Path(fam.THINK_PACKET_ROOT),
    legacy_cache=Path("/home/chao/feat-cache/slurp-thinking-gpu-q4km-test-sample-3010"),
    promotion_receipt=Path(fam.THINK_PACKET_ROOT) / "TEST-SAMPLE-3010-promotion.json",
    roster_receipt="docs/receipts/rosters/slurp-test-sample-3010-v1.json",
    expected_rows=3010, row_calls=3010, row_speech_seconds=8207,
    label="TEST-SAMPLE-3010",
)
SAMPLE_ROSTER_KEY = "thinking-test-sample-3010"
FINAL_REPORT_ROLE = "final-report"
#: The active DEV spec, set by ``apply_roster`` (None for the Fold B rosters, whose behaviour is unchanged).
ACTIVE_DEV: DevSpec | None = None


class ThinkingRoster(NamedTuple):
    key: str
    rows: int | None  # None = every row of the Fold B view
    promote: bool
    default_attempt_id: str
    plan_calls: int
    plan_speech_seconds: int
    plan_gpu_hours: float
    dev: DevSpec | None = None


def _rosters(geometry: Geometry) -> dict[str, ThinkingRoster]:
    rosters = {
        "thinking-smoke-4": ThinkingRoster(
            "thinking-smoke-4", fam.SMOKE_ROWS, False, geometry.smoke_attempt, fam.SMOKE_ROWS, SMOKE_SPEECH_SECONDS, 1.0),
        "thinking-fold-b": ThinkingRoster(
            "thinking-fold-b", None, True, geometry.fold_attempt, ROW_CALLS, ROW_SPEECH_SECONDS, 1.0),
    }
    if geometry.key == "gpu":   # the DEV roster exists on the GPU geometry only
        rosters[DEV_ROSTER_KEY] = ThinkingRoster(
            DEV_ROSTER_KEY, None, True, "attempt-packets-thinking-gpu-dev2000-added-v1", DEV_SPEC.row_calls, DEV_SPEC.row_speech_seconds, 1.0, DEV_SPEC)
        rosters[SAMPLE_ROSTER_KEY] = ThinkingRoster(
            SAMPLE_ROSTER_KEY, None, True, "attempt-packets-thinking-gpu-test-sample-3010-v1", SAMPLE_SPEC.row_calls, SAMPLE_SPEC.row_speech_seconds, 1.0,
            SAMPLE_SPEC)
    return rosters


ROSTERS: dict[str, ThinkingRoster] = _rosters(GEOMETRY)


def apply_geometry(key: str, *, allow_cpu: bool = False) -> Geometry:
    """Rebind the module's active geometry (run id, fragments, receipt, roots, rosters). The CPU geometry is refused without ``allow_cpu``."""

    global GEOMETRY, RUN_ID, SIDECAR_FRAGMENT, EXPERIMENT_FRAGMENT, RUNTIME_RECEIPT_RELPATH, PACKET_ROOT, LEGACY_CACHE, PROMOTION_RECEIPT
    if key not in GEOMETRIES:
        raise SystemExit("unknown geometry %r (gpu | cpu)" % key)
    if key == "cpu" and not allow_cpu:
        raise SystemExit(
            "REFUSED: the CPU sidecar geometry is SUPERSEDED (16-19 s per row; the owner stopped the pass after 50 rows and ruled the rate "
            "unacceptable); the live pass is the GPU geometry inside a serving-swap window. Pass --allow-cpu to run it for the record.")
    geometry = GEOMETRIES[key]
    GEOMETRY, RUN_ID, SIDECAR_FRAGMENT = geometry, geometry.run_id, geometry.sidecar_fragment
    EXPERIMENT_FRAGMENT, RUNTIME_RECEIPT_RELPATH = geometry.experiment_fragment, geometry.runtime_receipt_relpath
    PACKET_ROOT, LEGACY_CACHE, PROMOTION_RECEIPT = geometry.packet_root, geometry.legacy_cache, geometry.promotion_receipt
    ROSTERS.update(_rosters(geometry))
    return geometry


def apply_roster(key: str | None) -> DevSpec | None:
    """Rebind the module run bindings for a DEV roster (run id, fragments, roots, receipt); a Fold B roster restores the geometry values."""

    global ACTIVE_DEV, RUN_ID, SIDECAR_FRAGMENT, EXPERIMENT_FRAGMENT, DATASET_FRAGMENT, PACKET_ROOT, LEGACY_CACHE, PROMOTION_RECEIPT
    roster = ROSTERS.get(key) if key else None
    dev = roster.dev if roster is not None else None
    if dev is not None and GEOMETRY.key != "gpu":
        raise SystemExit("REFUSED: the DEV roster exists on the GPU geometry only")
    ACTIVE_DEV = dev
    if dev is None:
        RUN_ID, SIDECAR_FRAGMENT, EXPERIMENT_FRAGMENT = GEOMETRY.run_id, GEOMETRY.sidecar_fragment, GEOMETRY.experiment_fragment
        DATASET_FRAGMENT = fam.DATASET
        PACKET_ROOT, LEGACY_CACHE, PROMOTION_RECEIPT = GEOMETRY.packet_root, GEOMETRY.legacy_cache, GEOMETRY.promotion_receipt
    else:
        RUN_ID, SIDECAR_FRAGMENT, EXPERIMENT_FRAGMENT, DATASET_FRAGMENT = dev.run_id, dev.sidecar_fragment, dev.experiment_fragment, dev.dataset_fragment
        PACKET_ROOT, LEGACY_CACHE, PROMOTION_RECEIPT = dev.packet_root, dev.legacy_cache, dev.promotion_receipt
    return dev


def log(message: str) -> None:
    evo.log(message)


# ----------------------------------------------------------------------------------------------------- configuration


def compose_values(repo: Path = REPO):
    composed = evo.compose(repo, SIDECAR_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT)
    return composed, composed.values


def check_config_identity(values: Mapping[str, object], repo: Path = REPO) -> None:
    """The composed config must be the registered Thinking one in every identity field; drift refuses."""

    expectations = (
        ("experiment_id", RUN_ID),
        ("model_lock_key", pins_mod.LOCK_KEY),
        ("runtime_receipt", RUNTIME_RECEIPT_RELPATH),
        ("feature_root", str(PACKET_ROOT)),
        ("legacy_cache_dir", str(LEGACY_CACHE)),
        ("promotion_receipt", str(PROMOTION_RECEIPT)),
        ("split_role", ACTIVE_DEV.split_role if ACTIVE_DEV is not None else "discovery"),
        ("execution_profile", EXECUTION_PROFILE),
    )
    for key, expected in expectations:
        if values.get(key) != expected:
            raise SystemExit("composed config %s is %r, registered %r" % (key, values.get(key), expected))
    served = dict(values.get("server_env", {})).get("LLAMA_MTMD_FEAT_CACHE_DIR")
    if served != str(LEGACY_CACHE):
        raise SystemExit("the sidecar fragment writes its feature cache to %r, not %s" % (served, LEGACY_CACHE))
    if PACKET_ROOT == evo.DEFAULT_FEATURE_ROOT or LEGACY_CACHE == evo.DEFAULT_LEGACY_CACHE_DIR:
        raise SystemExit("the Thinking roots may not be the Instruct roots")
    expected_rows = ACTIVE_DEV.expected_rows if ACTIVE_DEV is not None else fam.ROWS
    roster_path = ACTIVE_DEV.roster_receipt if ACTIVE_DEV is not None else fam.ROSTER["arm"]
    label = ACTIVE_DEV.label if ACTIVE_DEV is not None else "Fold B"
    if ACTIVE_DEV is not None and ACTIVE_DEV.split_role == FINAL_REPORT_ROLE and not isinstance(values.get("owner_allowance"), Mapping):
        raise SystemExit("a final-report roster's composed config must pin owner_allowance={path, sha256}")
    roster_doc = json.loads((repo / roster_path).read_text(encoding="utf-8"))
    if values.get("split_identity_hash") != roster_doc.get("split_identity_hash"):
        raise SystemExit("the dataset view split identity differs from the %s roster receipt" % label)
    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a speech-native runtime view")
    if len(items) != expected_rows or int(values.get("count", -1)) != expected_rows:
        raise SystemExit("the %s runtime view must carry exactly %d rows" % (label, expected_rows))


def smoke_ids(repo: Path = REPO) -> list[str]:
    if ACTIVE_DEV is not None:        # the DEV roster has no smoke prefix: the Fold B smoke rows are not its rows
        return []
    path = repo / fam.ROSTER["smoke"]
    document = json.loads(path.read_text(encoding="utf-8"))
    return [str(item["sample_id"]) for item in document["items"]]


def select_items(values: Mapping[str, object], roster: ThinkingRoster, prefix_ids: Sequence[str]) -> list[Mapping[str, object]]:
    """The roster's rows in view order. The first four rows of the view must be the registered smoke rows, in order."""

    items = list(values["items"])  # type: ignore[arg-type]
    head = [str(item["sample_id"]) for item in items[: len(prefix_ids)]]
    if head != list(prefix_ids):
        raise SystemExit("the first %d rows of the Fold B view are not the registered smoke rows in order" % len(prefix_ids))
    return items if roster.rows is None else items[: roster.rows]


def view_for(values: Mapping[str, object], items: Sequence[Mapping[str, object]]) -> dict[str, object]:
    return {**values, "items": list(items), "count": len(items)}


# ---------------------------------------------------------------------------------------------------------- pins


def verify_pins(
    *, repo: Path = REPO, lock_path: Path, main_receipt: Path | None = None,
    mmproj_receipt: Path | None = None, runtime_receipt_path: Path | None = None,
) -> tuple[dict, dict]:
    """The Thinking pins: local hash receipts proven equal to the umbrella lock text, then equal to the committed runtime receipt."""

    pins = pins_mod.resolve_pins(
        lock_path=lock_path, main_receipt=main_receipt or pins_mod.LOCAL_MAIN_RECEIPT,
        mmproj_receipt=mmproj_receipt or pins_mod.LOCAL_MMPROJ_RECEIPT)
    path = runtime_receipt_path or (repo / "docs" / RUNTIME_RECEIPT_RELPATH)
    receipt = json.loads(Path(path).read_text(encoding="utf-8"))
    if receipt.get("model_lock_key") != pins_mod.LOCK_KEY:
        raise SystemExit("runtime receipt %s names model %r, not %s" % (path, receipt.get("model_lock_key"), pins_mod.LOCK_KEY))
    if receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    if receipt.get("gguf_files") != [pins["main"], pins["mmproj"]]:
        raise SystemExit(
            "runtime receipt gguf_files differ from the lock-verified Thinking pins (decoder and mmproj path, bytes, sha256); "
            "refusing to prepare packets under a receipt that does not bind the pinned files")
    return pins, receipt


# --------------------------------------------------------------------------------------------------------- ledger


def ledger_state(
    ledger_path: Path, *, split_identity_hash: str, expected_calls: int | None = None, expected_seconds: int | None = None,
    expected_gpu_hours: float = ROW_GPU_HOURS,
) -> dict[str, object]:
    """Presence and countersignature of the packets exposure row, and every disagreement with the registration.

    The numbers compared are the gate's own: calls, speech audio seconds AND gpu hours (a plan claiming more gpu hours than the row
    pre-registers is refused by the gate, so this check must refuse it first). The expected calls and seconds are the fold's total plus
    whatever a failed attempt already spent (see ``expected_row_totals``).
    """

    if expected_calls is None:
        expected_calls = ACTIVE_DEV.row_calls if ACTIVE_DEV is not None else GEOMETRY.row_calls
    if expected_seconds is None:
        expected_seconds = (ACTIVE_DEV.row_speech_seconds if ACTIVE_DEV is not None
                            else ROW_SPEECH_SECONDS + (SMOKE_SPEECH_SECONDS if GEOMETRY.smoke_in_row else 0))
    rows = _parse_ledger_tables(Path(ledger_path).read_text(encoding="utf-8"))
    matched = [row for row in rows if row.get("run/experiment id") == RUN_ID]
    problems: list[str] = []
    state: dict[str, object] = {"row": RUN_ID, "present": len(matched) == 1, "countersigned": False, "problems": problems}
    if len(matched) != 1:
        problems.append("%d exposure rows for %s, need exactly one" % (len(matched), RUN_ID))
        return state
    row = matched[0]
    if row.get("execution profile") != EXECUTION_PROFILE:
        problems.append("execution profile %r, registered %r" % (row.get("execution profile"), EXECUTION_PROFILE))
    expected_role = ACTIVE_DEV.split_role if ACTIVE_DEV is not None else "discovery"
    if row.get("split role") != expected_role or row.get("split identity hash") != split_identity_hash:
        problems.append("split role / identity differ from the %s roster" % (ACTIVE_DEV.label if ACTIVE_DEV is not None else "Fold B"))
    try:
        numbers = (int(row["calls"]), int(row["speech audio seconds"]), float(row["gpu hours"]))
    except (KeyError, ValueError):
        numbers = None
    if numbers != (expected_calls, expected_seconds, float(expected_gpu_hours)):
        problems.append("budgets (calls, speech audio seconds, gpu hours) %r, registered %r" % (
            numbers, (expected_calls, expected_seconds, float(expected_gpu_hours))))
    if str(row.get("consumed", "")).strip().lower() != "no":
        problems.append("row is consumed; a sealed preparation is never re-run")
    text = " ".join(str(value) for value in row.values())
    draft = bool(DRAFT_TOKEN.search(text))
    state["draft"] = draft
    state["countersigned"] = (not draft) and bool(COUNTERSIGNED_TOKEN.search(text)) and not problems
    return state


def allowance_problems(values: Mapping[str, object], *, repo: Path = REPO) -> list[str]:
    """For a ``final-report`` roster: the refusal of ``contracts.plan.require_owner_split_allowance`` for THIS run id, else ``[]``.

    The guard is the contract's own (the same call the Instruct sample driver makes in every mode); it is never weakened or bypassed here: the pinned
    allowance must exist at its pinned bytes, read ``authorised``, name the sample's carrier and split identity, and list this run id in
    ``permitted_run_ids``. Every other roster returns ``[]`` (their split roles are not owner-allowance-gated).
    """

    if ACTIVE_DEV is None or ACTIVE_DEV.split_role != FINAL_REPORT_ROLE:
        return []
    try:
        evo.require_owner_split_allowance(
            run_id=RUN_ID, execution_profile=str(values["execution_profile"]), carrier_lock_key=evo.SLURP_LOCK_KEY,
            split_identity_hash=str(values["split_identity_hash"]), owner_allowance=values.get("owner_allowance"), source_root=repo)
    except Exception as error:  # noqa: BLE001 -- ExecutionScopeError and malformed pins alike are reported verbatim as refusals
        return ["owner allowance guard (contracts.plan.require_owner_split_allowance): %s" % error]
    return []


# ------------------------------------------------------------------------------------------------------- attempts


class AttemptContext(NamedTuple):
    """What earlier attempts of this run id already spent. Plan budgets are run-cumulative, so a successor declares prior plus its own."""

    prior_calls: int
    prior_audio_seconds: float
    wasted_calls: int
    wasted_audio_seconds: float
    failed: tuple[str, ...]


def attempt_history(data_root: Path, run_id: str | None = None) -> tuple[list[dict[str, object]], list[str]]:
    """Attempt records of the run id, and run directories that have no attempt record (read-only).

    An attempt is COMPLETED only if its run directory holds the encoder receipt this driver writes last; an attempt record with
    contacts counted and no encoder receipt is a FAILED attempt whose spend is real and whose features may be lost.
    """

    run_id = run_id or RUN_ID
    attempts_dir, runs_dir = Path(data_root) / "attempts" / run_id, Path(data_root) / "runs" / run_id
    history: list[dict[str, object]] = []
    seen: set[str] = set()
    if attempts_dir.is_dir():
        for path in sorted(attempts_dir.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            attempt_id = str(document["attempt_id"])
            seen.add(attempt_id)
            actual = document.get("actual") or {}
            history.append({
                "attempt_id": attempt_id, "state": document.get("state"), "calls": int(actual.get("calls", 0)),
                "audio_seconds": float(actual.get("audio_seconds", 0.0)),
                "completed": (runs_dir / attempt_id / ENCODER_RECEIPT_NAME).is_file()})
    orphans = sorted(entry.name for entry in runs_dir.iterdir() if entry.is_dir() and entry.name not in seen) if runs_dir.is_dir() else []
    return history, orphans


def resolve_attempt_context(
    history: Sequence[Mapping[str, object]], orphans: Sequence[str], *, attempt_id: str, recovery_of: str | None,
) -> AttemptContext:
    """Refuse every ambiguous start; never silently reuse an attempt id or an unexplained spend.

    - a run directory without an attempt record, or an attempt id already used: refused;
    - an earlier attempt that spent contacts and has no encoder receipt (a FAILED start): the next start must name it with
      ``--recovery-of`` AND use a new attempt id; it is the flight's one recovery re-registration, and a second failed attempt stops the flight.
    """

    if orphans:
        raise SystemExit("REFUSED: run directories without an attempt record under %s: %s; the state is ambiguous, inspect them first" % (
            RUN_ID, ", ".join(orphans)))
    used = {str(entry["attempt_id"]): entry for entry in history}
    if attempt_id in used:
        entry = used[attempt_id]
        raise SystemExit("REFUSED: attempt id %s is already used (state %s, %d calls counted, encoder receipt %s); use a NEW --attempt-id "
                         "(the plan budget is run-cumulative; a reused id would hide that spend)" % (
                             attempt_id, entry["state"], entry["calls"], "present" if entry["completed"] else "ABSENT"))
    failed = [entry for entry in history if not entry["completed"]]
    named = sorted(token for token in (recovery_of or "").split(",") if token)
    if len(failed) > 1:
        raise SystemExit("REFUSED: %d failed attempts (%s) without an encoder receipt; the single recovery re-registration is spent, "
                         "stop and re-register" % (len(failed), ", ".join(str(e["attempt_id"]) for e in failed)))
    if failed and named != [str(failed[0]["attempt_id"])]:
        entry = failed[0]
        raise SystemExit("REFUSED: attempt %s (state %s) counted %d calls / %.4f speech seconds and wrote NO encoder receipt: a failed start whose "
                         "spend is real and whose features may be lost. This start is ambiguous; name it with --recovery-of %s and a NEW "
                         "--attempt-id (the one recovery re-registration), after the ledger row carries the extra spend" % (
                             entry["attempt_id"], entry["state"], entry["calls"], entry["audio_seconds"], entry["attempt_id"]))
    if not failed and named:
        raise SystemExit("REFUSED: --recovery-of names %s but no failed attempt exists under %s" % (", ".join(named), RUN_ID))
    return summarize_history(history)


def summarize_history(history: Sequence[Mapping[str, object]]) -> AttemptContext:
    failed = [entry for entry in history if not entry["completed"]]
    return AttemptContext(
        prior_calls=sum(int(e["calls"]) for e in history), prior_audio_seconds=sum(float(e["audio_seconds"]) for e in history),
        wasted_calls=sum(int(e["calls"]) for e in failed), wasted_audio_seconds=sum(float(e["audio_seconds"]) for e in failed),
        failed=tuple(str(e["attempt_id"]) for e in failed))


def expected_row_totals(values: Mapping[str, object], context: AttemptContext) -> tuple[int, int]:
    """The ledger row's calls and speech seconds: the fold's own total plus the spend of a failed attempt (its features were lost).

    The GPU re-registration's row also carries the 4-row smoke (1,084 calls, 3,165 speech seconds): the smoke is a distinct attempt whose
    contacts the Fold B attempt does not repeat (warm rows are skipped), so the ceiling has four calls of slack by registration.
    """

    items = list(values["items"])  # type: ignore[arg-type]
    fold_audio = sum(float(item["audio_seconds"]) for item in items)
    if ACTIVE_DEV is not None:        # no smoke attempt in the DEV row: its total is the roster own
        return (ACTIVE_DEV.row_calls + context.wasted_calls, math.ceil(round(fold_audio + context.wasted_audio_seconds, 6)))
    smoke_audio = sum(float(item["audio_seconds"]) for item in items[: fam.SMOKE_ROWS]) if GEOMETRY.smoke_in_row else 0.0
    return (GEOMETRY.row_calls + context.wasted_calls,
            math.ceil(round(fold_audio + smoke_audio + context.wasted_audio_seconds, 6)))


def plan_totals(context: AttemptContext, cold_rows: int, cold_audio_seconds: float) -> tuple[int, int]:
    """Cumulative calls and speech seconds this attempt declares: all prior spend plus its own worst case."""

    return context.prior_calls + cold_rows, math.ceil(round(context.prior_audio_seconds + cold_audio_seconds, 6))


# ---------------------------------------------------------------------------------------------------------- roots


def root_problems(
    roster: ThinkingRoster, *, packet_root: Path, legacy_cache: Path, promotion_receipt: Path, allow_populated_root: bool = False,
) -> list[str]:
    problems: list[str] = []
    if promotion_receipt.exists():
        problems.append("promotion receipt already exists: %s" % promotion_receipt)
    if packet_root.exists() and not allow_populated_root:
        if not packet_root.is_dir() or any(packet_root.iterdir()):
            problems.append("packet root %s exists and is not empty" % packet_root)
    if roster.key == "thinking-smoke-4" and legacy_cache.exists() and any(legacy_cache.iterdir()):
        problems.append("the smoke starts from an empty legacy cache; %s is not empty" % legacy_cache)
    return problems


def legacy_cache_findings(legacy_cache: Path, root: Path, roster_items: Sequence[Mapping[str, object]]) -> tuple[set[str], list[str]]:
    """Warm roster sample ids, and any cache file whose key is not a roster row's (a stale foreign entry)."""

    keys = {
        evo.legacy_audio_feature_cache_key((root / str(item["media_relpath"])).read_bytes()): str(item["sample_id"])
        for item in roster_items
    }
    warm: set[str] = set()
    foreign: list[str] = []
    if legacy_cache.is_dir():
        for path in sorted(legacy_cache.iterdir()):
            key = path.name.split("_o", 1)[0]
            if path.suffix == ".feat" and key in keys:
                warm.add(keys[key])
            else:
                foreign.append(path.name)
    return warm, foreign


# ------------------------------------------------------------------------------------------- serving and GPU state

GPU_FREE_MAX_MIB = 3072     # a desktop session may hold a GB or two; a resident core holds about 22 GB
SERVING_PORT = evo.INFERENCE_PORT


def _find_pid(document: object) -> int | None:
    if isinstance(document, Mapping):
        value = document.get("pid")
        if isinstance(value, int) and value > 0:
            return value
        for nested in document.values():
            found = _find_pid(nested)
            if found is not None:
                return found
    return None


def pid_alive(pid: int) -> bool:
    """True when ``/proc/<pid>`` exists and its command line names a llama-server (a recycled pid of another program does not count)."""

    try:
        raw = Path("/proc/%d/cmdline" % pid).read_bytes()
    except OSError:
        return False
    return b"llama-server" in raw


def resident_sessions(data_root: Path) -> list[str]:
    """Serving sessions recorded resident: ``session.json`` without ``session-stop.json`` AND a live llama-server pid (or no pid recorded)."""

    serving = Path(data_root) / "serving"
    found: list[str] = []
    if not serving.is_dir():
        return found
    for entry in sorted(serving.iterdir()):
        record = entry / "session.json"
        if not record.is_file() or (entry / "session-stop.json").exists():
            continue
        try:
            pid = _find_pid(json.loads(record.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pid = None
        if pid is None or pid_alive(pid):
            found.append(entry.name)
    return found


def port_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def gpu_memory_used_mib() -> int | None:
    """Largest ``memory.used`` over the visible GPUs, or None when nvidia-smi cannot be read (unknown is not a refusal)."""

    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    values = [int(line.strip()) for line in out.stdout.splitlines() if line.strip().isdecimal()]
    return max(values) if values else None


def gpu_state(data_root: Path) -> dict[str, object]:
    """Everything the GPU encoder pass needs to be true: no resident session, nothing on the serving port, an (almost) empty card."""

    sessions = resident_sessions(data_root)
    listening = port_listening(SERVING_PORT)
    used = gpu_memory_used_mib()
    findings: list[str] = []
    if sessions:
        findings.append("serving session(s) recorded resident: %s (stop them first; the card holds one core)" % ", ".join(sessions))
    if listening:
        findings.append("something listens on the serving port %d" % SERVING_PORT)
    if used is not None and used > GPU_FREE_MAX_MIB:
        findings.append("GPU memory in use is %d MiB (> %d MiB): the card is not free" % (used, GPU_FREE_MAX_MIB))
    return {"resident_sessions": sessions, "serving_port_listening": listening, "gpu_memory_used_mib": used,
            "gpu_free": not findings, "findings": findings}


# ------------------------------------------------------------------------------------------------------- the plan


def build_plan(
    *, roster: ThinkingRoster, values: Mapping[str, object], composed_hash: str, items: Sequence[Mapping[str, object]],
    pins: Mapping[str, object], runtime_receipt: Mapping[str, object], ledger: Mapping[str, object], workers: int,
    promote_workers: int, attempt_id: str, slots: int, problems: Sequence[str], context: AttemptContext,
    serving_state: Mapping[str, object] | None = None,
) -> dict[str, object]:
    audio_seconds = sum(float(item["audio_seconds"]) for item in items)
    ceiling_calls, ceiling_seconds = plan_totals(context, len(items), audio_seconds)
    row_calls, row_seconds = expected_row_totals(values, context)
    return {
        "schema": PLAN_SCHEMA,
        "mode": "dry-run",
        "geometry": GEOMETRY.key,
        "device": GEOMETRY.device,
        "roster": roster.key,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "rows": len(items),
        "first_row": str(items[0]["sample_id"]),
        "last_row": str(items[-1]["sample_id"]),
        "audio_seconds": round(audio_seconds, 6),
        "declared_plan": {"calls_ceiling": ceiling_calls, "speech_audio_seconds_ceiling": ceiling_seconds,
                          "gpu_hours": roster.plan_gpu_hours,
                          "basis": "run-cumulative: prior spend of every earlier attempt plus this roster's rows (a warm row is not contacted)"},
        "row_total": {"calls": row_calls, "speech_audio_seconds": row_seconds, "gpu_hours": ROW_GPU_HOURS},
        "serving_state": dict(serving_state) if serving_state is not None else None,
        "attempts": {"prior_calls": context.prior_calls, "prior_audio_seconds": round(context.prior_audio_seconds, 6),
                     "failed_attempts": list(context.failed), "recovery_of": list(context.failed)},
        "promotes": roster.promote,
        "roots": {"packet_root": str(PACKET_ROOT), "legacy_cache_dir": str(LEGACY_CACHE),
                  "promotion_receipt": str(PROMOTION_RECEIPT) if roster.promote else None},
        "pins": {"lock_key": pins_mod.LOCK_KEY, "decoder": dict(pins["main"]), "mmproj": dict(pins["mmproj"]),  # type: ignore[arg-type]
                 "runtime_receipt": "docs/" + RUNTIME_RECEIPT_RELPATH,
                 "runtime_receipt_sha256": evo.canonical_sha256(runtime_receipt),
                 "llama_cpp_build_commit": dict(runtime_receipt["llama_cpp"])["build_commit"]},  # type: ignore[arg-type]
        "sidecar": {"fragment": SIDECAR_FRAGMENT, "port": evo.SIDECAR_PORT, "slots": slots, "encode_workers": workers,
                    "promote_workers": promote_workers, "gpu_offload": GEOMETRY.offload, "server_args": list(values["server_args"])},  # type: ignore[call-overload]
        "config_fragments": {"model": SIDECAR_FRAGMENT, "dataset": DATASET_FRAGMENT, "baseline": BASELINE_FRAGMENT,
                             "experiment": EXPERIMENT_FRAGMENT},
        "config_hash": composed_hash,
        "split_identity_hash": str(values["split_identity_hash"]),
        "ledger": dict(ledger),
        "refusals": list(problems),
        "encoder_calls": 0,
        "contacts": 0,
    }


def _prepare(args, roster: ThinkingRoster, *, repo: Path, lock_path: Path | None, ledger_path: Path | None):
    """Everything both modes share, with no media read: composed config, pins, ledger, roots, worker fit."""

    composed, values = compose_values(repo)
    check_config_identity(values, repo)
    lock = lock_path or evo.umbrella_lock_path()
    pins, runtime_receipt = verify_pins(repo=repo, lock_path=lock)
    items = select_items(values, roster, smoke_ids(repo))
    slots = evo._server_slots(values, SIDECAR_FRAGMENT)
    if getattr(args, "workers", None) is None:
        args.workers = GEOMETRY.default_workers
    evo._assert_worker_fit(args.workers, slots, roster.key, SIDECAR_FRAGMENT)
    attempt_id = args.attempt_id or roster.default_attempt_id
    history, orphans = attempt_history(evo.data_root())
    context = resolve_attempt_context(history, orphans, attempt_id=attempt_id, recovery_of=getattr(args, "recovery_of", None))
    calls, seconds = expected_row_totals(values, context)
    ledger = ledger_state(ledger_path or (repo / LEDGER_RELPATH), split_identity_hash=str(values["split_identity_hash"]),
                          expected_calls=calls, expected_seconds=seconds)
    problems = root_problems(
        roster, packet_root=PACKET_ROOT, legacy_cache=LEGACY_CACHE, promotion_receipt=PROMOTION_RECEIPT,
        allow_populated_root=bool(getattr(args, "promote_only", False)) or ACTIVE_DEV is not None)   # the DEV promotion is ADDITIVE on the Fold B root
    # A final-report roster (the test sample) is refused HERE, before any media is opened, unless the pinned owner allowance accepts this run id.
    problems.extend(allowance_problems(values, repo=repo))
    return composed, values, pins, runtime_receipt, ledger, items, slots, attempt_id, problems, context


def dry_run(args, *, repo: Path = REPO, lock_path: Path | None = None, ledger_path: Path | None = None) -> int:
    roster = ROSTERS[args.roster]
    composed, values, pins, runtime_receipt, ledger, items, slots, attempt_id, problems, context = _prepare(
        args, roster, repo=repo, lock_path=lock_path, ledger_path=ledger_path)
    problems = [*problems, *ledger["problems"]]  # type: ignore[misc]
    plan = build_plan(
        roster=roster, values=values, composed_hash=composed.config_hash, items=items, pins=pins, runtime_receipt=runtime_receipt,
        ledger=ledger, workers=args.workers, promote_workers=args.promote_workers, attempt_id=attempt_id, slots=slots,
        problems=problems, context=context,
        serving_state=gpu_state(evo.data_root()) if GEOMETRY.device == "gpu" else None)
    evo._emit(args, plan)
    if problems:
        log("DRY-RUN REFUSES: %s" % "; ".join(problems))
        return 3
    log("DRY-RUN PASS: plan printed, zero encoder calls, no media opened, no process started")
    return 0


# ------------------------------------------------------------------------------------------- receipts (pure builders)


def encoder_receipt_document(
    *, roster: ThinkingRoster, attempt_id: str, runtime_receipt: Mapping[str, object], decoder: Mapping[str, object],
    mmproj: Mapping[str, object], values: Mapping[str, object], config_hash: str, rows: int, audio_seconds: float,
    contacts: int, skipped_warm: int, encode_workers: int, promote_workers: int | None, encode_seconds: float,
    session: Mapping[str, object], files: Sequence[Mapping[str, object]], promotion_receipt: Path | None,
    promotion_receipt_sha256: str | None, mode: str, context: AttemptContext | None = None,
    device: str | None = None, server_args: Sequence[str] = (), server_env: Mapping[str, str] | None = None,
    gpu_memory_before_mib: int | None = None,
) -> dict[str, object]:
    llama = dict(runtime_receipt["llama_cpp"])  # type: ignore[arg-type]
    return {
        "schema": ENCODER_RECEIPT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "device": device or GEOMETRY.device,
        "geometry": GEOMETRY.key,
        "sidecar_fragment": SIDECAR_FRAGMENT,
        "server_args": list(server_args),
        "server_env_keys": sorted(server_env or {}),
        "gpu_memory_before_mib": gpu_memory_before_mib,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "roster": roster.key,
        "mode": mode,
        "recovery_of": list(context.failed) if context is not None else [],
        "prior_calls": context.prior_calls if context is not None else 0,
        "llama_cpp": {"build_commit": llama["build_commit"], "binary_sha256": llama.get("binary_sha256"),
                      "reported_build": llama.get("reported_build")},
        "runtime_receipt": "docs/" + RUNTIME_RECEIPT_RELPATH,
        "runtime_receipt_sha256": evo.canonical_sha256(runtime_receipt),
        "model_lock_key": pins_mod.LOCK_KEY,
        "decoder_gguf_sha256": str(decoder["sha256"]),
        "mmproj_sha256": str(mmproj["sha256"]),
        "split_identity_hash": str(values["split_identity_hash"]),
        "split_role": str(values["split_role"]),
        "dataset_runtime_view_sha256": str(values["runtime_view_sha256"]),
        "config_hash": config_hash,
        "rows": rows,
        "audio_seconds": round(audio_seconds, 6),
        "contacts": contacts,
        "skipped_warm_rows": skipped_warm,
        "encode_workers": encode_workers,
        "promote_workers": promote_workers,
        "encode_seconds": round(encode_seconds, 3),
        "encode_rows_per_second": round(contacts / max(encode_seconds, 1e-9), 4),
        "seconds_per_row": round(encode_seconds / contacts, 4) if contacts else None,
        "packet_root": str(PACKET_ROOT) if roster.promote else None,
        "legacy_cache_dir": str(LEGACY_CACHE),
        "promotion_receipt": str(promotion_receipt) if promotion_receipt is not None else None,
        "promotion_receipt_sha256": promotion_receipt_sha256,
        "session": dict(session),
        "file_count": len(files),
        "files": [dict(entry) for entry in files],
    }


def packet_file_entries(packets) -> list[dict[str, object]]:
    return [
        {"kind": "packet", "packet_id": packet.packet_id, "packet_sha256": packet.packet_sha256,
         "audio_sha256": packet.audio_sha256,
         "chunks": [{"ordinal": chunk.ordinal, "n_tokens": chunk.n_tokens, "feature_sha256": chunk.feature_sha256}
                    for chunk in packet.chunks]}
        for packet in sorted(packets, key=lambda entry: entry.packet_id)
    ]


def legacy_file_entries(samples, root: Path, legacy_cache: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for sample in samples:
        inspection = inspect_legacy_cached_speech_feature_cache(
            audio_path=root / sample.media_relpath, legacy_cache_dir=legacy_cache, expected_n_embd=evo.EXPECTED_N_EMBD)
        entries.append({
            "kind": "legacy-cache-entry", "sample_id": sample.sample_id, "audio_sha256": inspection.audio_sha256,
            "cache_key": inspection.cache_key,
            "chunks": [{"ordinal": chunk.ordinal, "filename": chunk.relative_filename, "file_sha256": chunk.file_sha256,
                        "file_size": chunk.file_size, "n_tokens": chunk.n_tokens} for chunk in inspection.chunks]})
    return sorted(entries, key=lambda entry: str(entry["sample_id"]))


def write_create_only(path: Path, document: Mapping[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")
    except FileExistsError as error:
        raise SystemExit("receipt already exists: %s" % path) from error
    return evo.sha256_file(path)


# ----------------------------------------------------------------------------------------------------------- run


def run(args, *, repo: Path = REPO, lock_path: Path | None = None, ledger_path: Path | None = None) -> int:
    roster = ROSTERS[args.roster]
    promote_only = bool(getattr(args, "promote_only", False))
    if promote_only and not roster.promote:
        raise SystemExit("--promote-only is meaningless for %s: it promotes nothing" % roster.key)
    if promote_only and args.attempt_id is None:
        raise SystemExit("--promote-only requires an explicit --attempt-id (a NEW attempt)")
    composed, values, pins, runtime_receipt, ledger, items, slots, attempt_id, problems, context = _prepare(
        args, roster, repo=repo, lock_path=lock_path, ledger_path=ledger_path)
    problems = [*problems, *ledger["problems"]]  # type: ignore[misc]
    if not ledger["countersigned"] and not ledger["problems"]:
        problems.append("exposure row %s is not root-countersigned" % RUN_ID)
    state: dict[str, object] = {}
    if GEOMETRY.device == "gpu" and not promote_only:
        state = gpu_state(evo.data_root())
        problems.extend(str(finding) for finding in state["findings"])  # type: ignore[union-attr]
    if problems:
        raise SystemExit("REFUSED: " + "; ".join(problems))

    lock = evo.load_lock(lock_path or evo.umbrella_lock_path())
    root = evo.data_root()
    samples = evo.roster_samples(view_for(values, items), root, args.promote_workers,
                                 ACTIVE_DEV.sample_id_prefix if ACTIVE_DEV is not None else "slurp:train:", roster.key)
    audio_seconds = sum(float(sample.audio_seconds) for sample in samples)
    log("roster %s: %d samples, %.6f audio-s, config %s" % (roster.key, len(samples), audio_seconds, composed.config_hash[:16]))

    warm_ids, foreign = legacy_cache_findings(LEGACY_CACHE, root, items)
    if foreign:
        raise SystemExit("REFUSED: the legacy cache %s holds %d entries that are not roster rows (e.g. %s); a stale or foreign "
                         "entry could be promoted as this roster's features" % (LEGACY_CACHE, len(foreign), foreign[0]))
    cold = [sample for sample in samples if sample.sample_id not in warm_ids]
    log("artifact preflight: %d/%d warm, %d cold (only cold rows are contacted)" % (len(warm_ids), len(samples), len(cold)))
    decoder, mmproj = evo._decoder_and_mmproj(runtime_receipt)
    if promote_only:
        evo._require_fully_warm(len(warm_ids), len(samples), roster.key)

    binding = evo.build_payload_binding(
        carrier_lock_key=evo.SLURP_LOCK_KEY, samples=samples, data_root=root,
        carrier_root=evo.asset_dir(lock, evo.SLURP_LOCK_KEY, root))
    media_facts = {sid: (binding.media_relpaths[sid], binding.sample_facts[sid][0]) for sid in sorted(binding.allowed_sample_ids)}
    gate = evo.FrozenCoreGate.for_study_repo(
        repo, root, evo.RUNTIME_ROOT, runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
        d1_media_supplement_relpath=evo.d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=evo.d1_media_supplement_sha256(values))
    gate.verify_media_identity(evo.SLURP_LOCK_KEY, media_facts)
    log("D1 media identity PASS for %d samples" % len(media_facts))

    run_dir = root / "runs" / RUN_ID / attempt_id
    contacts, failures, started = 0, [], time.time()
    session_json: dict[str, object] = {"session_id": None}
    if not promote_only:
        try:
            with socket.create_connection(("127.0.0.1", evo.SIDECAR_PORT), timeout=1.0):
                raise SystemExit("something already listens on the sidecar port %d" % evo.SIDECAR_PORT)
        except OSError:
            pass
        cold_calls, cold_speech = plan_totals(context, len(cold), sum(float(s.audio_seconds) for s in cold))
        calls = args.plan_calls if args.plan_calls is not None else cold_calls
        speech = args.plan_speech_seconds if args.plan_speech_seconds is not None else cold_speech
        plan = evo.ExecutionPlan(
            run_id=RUN_ID, execution_profile=str(values["execution_profile"]), carrier_lock_key=evo.SLURP_LOCK_KEY,
            split_role=ACTIVE_DEV.split_role if ACTIVE_DEV is not None else "discovery", split_identity_hash=str(values["split_identity_hash"]), planned_model_calls=calls,
            planned_gpu_hours=roster.plan_gpu_hours, planned_speech_audio_seconds=speech, protocol_hash=composed.config_hash,
            attempt_id=attempt_id, owner_allowance=values.get("owner_allowance")).validate(source_root=repo)
        log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])
        run_dir.mkdir(parents=True, exist_ok=False)
        # The patched llama.cpp server writes legacy feature-cache entries only into a directory that already exists. Nothing else
        # creates the Thinking cache (first real run, 2026-10-11 10:52Z: four contacts counted, nothing cached). Create it empty here,
        # before the first contact, together with the packet root's parent; the packet root itself is created by the promotion.
        LEGACY_CACHE.mkdir(parents=True, exist_ok=True)
        PACKET_ROOT.parent.mkdir(parents=True, exist_ok=True)
        log("spawning the %s Thinking encoder server on %d at -np %d (%s)" % (GEOMETRY.device.upper(), evo.SIDECAR_PORT, slots, GEOMETRY.offload))
        session = evo.start_session(
            runtime_root=evo.RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt, host="127.0.0.1",
            port=evo.SIDECAR_PORT, session_id="%s-%s-%s" % (RUN_ID, attempt_id, GEOMETRY.session_tag),
            extra_argv=list(values["server_args"]), extra_env=dict(values["server_env"]),
            receipt_path=run_dir / "session-preprocess.receipt.json",
            server_log_path=run_dir / "session-preprocess.server.log", role="preprocess", ready_timeout_seconds=1800.0)
        log("encoder server up: pid=%s port=%s" % (session.pid, session.port))
        started = time.time()          # encode timing excludes the gate's full GGUF hash and the model load
        try:
            transport = evo.TRANSPORTS.resolve(str(values["transport"]))(
                values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=evo.RUNTIME_ROOT)
            client = evo.FrozenCoreClient(plan=plan, gate=gate, transport=transport, run_dir=run_dir, binding=binding,
                                          request_id_prefix="slurpthinkprep")

            def encode(sample) -> str | None:
                messages = (
                    {"role": "system", "content": evo.PREPROCESS_INSTRUCTION},
                    {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
                )
                try:
                    client.complete(messages, decoding_params=evo.DECODING_PARAMS)
                    return None
                except Exception as error:  # noqa: BLE001 -- reported, never masked
                    return "%s: %r" % (sample.sample_id, error)

            with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
                for index, problem in enumerate(pool.map(encode, cold), start=1):
                    if problem is None:
                        contacts += 1
                    else:
                        failures.append(problem)
                        log("contact FAILED %s" % problem)
                    if index % 50 == 0 or index == len(cold):
                        log("encode %d/%d (%d ok, %d failed, %.1fs)" % (index, len(cold), contacts, len(failures), time.time() - started))
            client.close()
        finally:
            stop = evo.stop_session(session, runtime_receipt=runtime_receipt, runtime_root=evo.RUNTIME_ROOT,
                                    receipt_path=run_dir / "session-preprocess.stop-receipt.json", force_after_timeout=True)
            log("encoder server stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
        session_json = {"session_id": session.session_id, "pid": session.pid, "stop": stop,
                        "session_receipt_sha256": evo.canonical_sha256(session.as_json()),
                        "stop_receipt_sha256": evo.canonical_sha256(stop)}
        if failures:
            raise SystemExit("%d encode contacts failed; refusing to promote a partial cache: %r" % (len(failures), failures[:5]))
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
    encode_seconds = time.time() - started
    if contacts:
        log("measured %.3f s per row over %d contacts (%.2f rows per minute, %d worker(s), device %s)" % (
            encode_seconds / contacts, contacts, 60.0 * contacts / max(encode_seconds, 1e-9), args.workers, GEOMETRY.device))

    if not promote_only:
        warm_after, _ = legacy_cache_findings(LEGACY_CACHE, root, items)
        missing = [sample.sample_id for sample in samples if sample.sample_id not in warm_after]
        if missing:
            raise SystemExit(
                "the sidecar answered %d contacts but the legacy cache %s holds no entry for %d of %d rows (e.g. %s): the contacts are "
                "counted and the features are lost; this attempt is FAILED (no encoder receipt is written) and the next start is the "
                "recovery re-registration" % (contacts, LEGACY_CACHE, len(missing), len(samples), missing[0]))

    if not roster.promote:
        files = legacy_file_entries(samples, root, LEGACY_CACHE)
        document = encoder_receipt_document(
            roster=roster, attempt_id=attempt_id, runtime_receipt=runtime_receipt, decoder=decoder, mmproj=mmproj, values=values,
            config_hash=composed.config_hash, rows=len(samples), audio_seconds=audio_seconds, contacts=contacts,
            skipped_warm=len(samples) - len(cold), encode_workers=args.workers, promote_workers=None,
            encode_seconds=encode_seconds, session=session_json, files=files, promotion_receipt=None,
            promotion_receipt_sha256=None, mode="encode-only", context=context, device=GEOMETRY.device,
            server_args=list(values["server_args"]), server_env=dict(values["server_env"]),  # type: ignore[call-overload]
            gpu_memory_before_mib=state.get("gpu_memory_used_mib"))  # type: ignore[arg-type]
        write_create_only(run_dir / ENCODER_RECEIPT_NAME, document)
        evo._emit(args, document)
        log("SMOKE PASS: %d contacts, %.2f rows per minute, no packet written" % (contacts, 60.0 * contacts / max(encode_seconds, 1e-9)))
        return 0

    promote_started = time.time()
    packets, shared = evo._promote_roster(
        samples=samples, root=root, packet_root=PACKET_ROOT, legacy_cache=LEGACY_CACHE, runtime_receipt=runtime_receipt,
        decoder=decoder, mmproj=mmproj, workers=args.promote_workers)
    promote_seconds = time.time() - promote_started
    mode = PROMOTION_MODE_PROMOTE_ONLY if promote_only else PROMOTION_MODE_ENCODE_AND_PROMOTE
    receipt = evo._promotion_receipt_document(
        packets=packets, shared=shared, values=values, packet_root=PACKET_ROOT, legacy_cache=LEGACY_CACHE, decoder=decoder,
        mmproj=mmproj, runtime_receipt=runtime_receipt, mode=mode, encode_contacts=contacts,
        session_id=("promote-only:%s:%s" % (RUN_ID, attempt_id)) if promote_only else str(session_json["session_id"]),
        session_receipt_sha256=None if promote_only else str(session_json["session_receipt_sha256"]),
        stop_receipt_sha256=None if promote_only else str(session_json["stop_receipt_sha256"]))
    promotion_sha256 = evo._write_promotion_receipt(PROMOTION_RECEIPT, receipt)
    log("promotion receipt %s (sha256 %s, %d shared, %.1fs)" % (PROMOTION_RECEIPT, promotion_sha256[:16], len(shared), promote_seconds))
    document = encoder_receipt_document(
        roster=roster, attempt_id=attempt_id, runtime_receipt=runtime_receipt, decoder=decoder, mmproj=mmproj, values=values,
        config_hash=composed.config_hash, rows=len(samples), audio_seconds=audio_seconds, contacts=contacts,
        skipped_warm=len(samples) - len(cold), encode_workers=args.workers, promote_workers=args.promote_workers,
        encode_seconds=encode_seconds, session=session_json, files=packet_file_entries(packets),
        promotion_receipt=PROMOTION_RECEIPT, promotion_receipt_sha256=promotion_sha256, mode=mode, context=context,
        device=GEOMETRY.device, server_args=list(values["server_args"]), server_env=dict(values["server_env"]),  # type: ignore[call-overload]
        gpu_memory_before_mib=state.get("gpu_memory_used_mib"))  # type: ignore[arg-type]
    write_create_only(run_dir / ENCODER_RECEIPT_NAME, document)
    evo._emit(args, document)
    log("FOLD-B PASS: %d packets promoted; next: python -B scripts/slurp_fold_preprocess_thinking.py --pin-receipt" % len(packets))
    return 0


# ------------------------------------------------------------------------------------------------------- pin step


def baseline_substitution(text: str, receipt_path: str, sha256: str) -> tuple[str, bool]:
    """Replace the zero sentinel by the receipt's sha256 exactly once. Returns (new text, changed)."""

    zero = fam.UNPINNED_SHA
    path_line = '"speech_packet_promotion_receipt": "%s"' % receipt_path
    if text.count(path_line) != 1:
        raise SystemExit("baseline does not name the Thinking promotion receipt %s exactly once" % receipt_path)
    key = '"speech_packet_promotion_receipt_sha256": "'
    if text.count(key) != 1:
        raise SystemExit("baseline carries %d speech_packet_promotion_receipt_sha256 fields, need exactly one" % text.count(key))
    start = text.index(key) + len(key)
    current = text[start:start + 64]
    if current == sha256:
        return text, False
    if current != zero:
        raise SystemExit("baseline is already pinned to a different receipt (%s...); refusing to overwrite" % current[:12])
    return text[:start] + sha256 + text[start + 64:], True


def pin_receipt(args, *, repo: Path = REPO, lock_path: Path | None = None, receipt_path: Path | None = None,
                packet_root: Path | None = None, expected_rows: int = fam.ROWS) -> int:
    receipt_path = receipt_path or PROMOTION_RECEIPT
    packet_root = packet_root or PACKET_ROOT
    if ACTIVE_DEV is not None and expected_rows == fam.ROWS:
        expected_rows = ACTIVE_DEV.expected_rows
    composed, values = compose_values(repo)
    check_config_identity(values, repo)
    pins, runtime_receipt = verify_pins(repo=repo, lock_path=lock_path or evo.umbrella_lock_path())
    sha256 = evo.sha256_file(receipt_path)
    document = load_speech_packet_promotion_receipt(
        receipt_path, expected_sha256=sha256, expected_feature_root=packet_root,
        expected_dataset_runtime_view_sha256=values["runtime_view_sha256"])
    expected_ids = {str(item["sample_id"]).replace(":", "/") for item in values["items"]}  # type: ignore[union-attr]
    packets = list(document["packets"])  # type: ignore[arg-type]
    if document["count"] != expected_rows or {str(p["packet_id"]) for p in packets} != expected_ids:
        raise SystemExit("the promotion receipt does not cover exactly the %d %s rows" % (expected_rows, ACTIVE_DEV.label if ACTIVE_DEV is not None else "Fold B"))
    if document["runtime_receipt_sha256"] != evo.canonical_sha256(runtime_receipt):
        raise SystemExit("the promotion receipt was produced under a different runtime receipt than the committed Thinking one")
    for packet in packets:
        if packet["decoder_gguf_sha256"] != pins["main"]["sha256"] or packet["mmproj_sha256"] != pins["mmproj"]["sha256"]:
            raise SystemExit("packet %s is bound to a decoder or mmproj other than the lock-verified Thinking pins" % packet["packet_id"])
    for packet in packets:  # the packets on disk, independently of the receipt
        loaded = load_speech_feature_packet(
            packet_root, packet["packet_id"], expected_sha256=packet["packet_sha256"],
            expected_decoder_gguf_sha256=pins["main"]["sha256"], expected_n_embd=evo.EXPECTED_N_EMBD)
        if loaded.mmproj_sha256 != pins["mmproj"]["sha256"] or loaded.audio_sha256 != packet["audio_sha256"]:
            raise SystemExit("packet %s on disk disagrees with the receipt" % packet["packet_id"])
    changed: list[str] = []
    for relpath in (() if ACTIVE_DEV is not None else BASELINES):   # the DEV cells pin the sha at derive time (thinking_system_dev_derive_cells.py)
        path = repo / relpath
        text = path.read_text(encoding="utf-8")
        new_text, did = baseline_substitution(text, str(receipt_path), sha256)
        if did:
            changed.append(relpath)
            if args.write:
                with path.open("w", encoding="utf-8", newline="") as handle:
                    handle.write(new_text)
    summary = {"promotion_receipt": str(receipt_path), "promotion_receipt_sha256": sha256, "packets": len(packets),
               "baselines_changed": changed, "written": bool(args.write and changed),
               "next": (("re-run scripts/flights/nx/successor3_thinking_derive_cells.py --require-receipt and the successor-3 package writer, then commit"
                         if ACTIVE_DEV.split_role == FINAL_REPORT_ROLE else
                         "re-run scripts/flights/direct/thinking_system_dev_derive_cells.py --require-receipt and the DEV package writer, then commit")
                        if ACTIVE_DEV is not None else
                        "commit the two baselines, then re-pin per the package README (direct_fb_flip.sh; never --allow-output-change)")}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def smoke_rate(args, *, data_root: Path | None = None) -> int:
    """Read the 4-row smoke's encoder receipt: seconds per row and the projected Fold B encode time (model-free, reads one small file).

    Exit 0 when the receipt is for the active device and the projection (seconds per row times the rows Fold B still has to encode) stays
    within ``--max-fold-seconds``; exit 5 when it does not (the window must stop and restore the serving geometry); exit 6 when the receipt
    is absent or unusable.
    """

    if ACTIVE_DEV is not None:
        print(json.dumps({"usable": False, "reason": "the DEV roster has no smoke: the Fold B smoke proved the GPU encoder form"}, sort_keys=True))
        return 6
    root = Path(data_root) if data_root is not None else evo.data_root()
    attempt_id = args.attempt_id or ROSTERS["thinking-smoke-4"].default_attempt_id
    path = root / "runs" / RUN_ID / attempt_id / ENCODER_RECEIPT_NAME
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        per_row = float(document["seconds_per_row"])
        device = str(document["device"])
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"receipt": str(path), "usable": False}, sort_keys=True))
        return 6
    cold = fam.ROWS - fam.SMOKE_ROWS
    projected = per_row * cold
    verdict = {"receipt": str(path), "device": device, "seconds_per_row": round(per_row, 4), "cold_fold_b_rows": cold,
               "projected_fold_b_encode_seconds": round(projected, 1), "max_fold_seconds": args.max_fold_seconds,
               "within_cap": projected <= args.max_fold_seconds and device == GEOMETRY.device}
    print(json.dumps(verdict, sort_keys=True))
    return 0 if verdict["within_cap"] else 5


def check_ledger(args, *, repo: Path = REPO, ledger_path: Path | None = None) -> int:
    _, values = compose_values(repo)
    history, orphans = attempt_history(evo.data_root())
    if orphans:
        raise SystemExit("REFUSED: run directories without an attempt record: %s" % ", ".join(orphans))
    context = summarize_history(history)
    calls, seconds = expected_row_totals(values, context)
    state = ledger_state(ledger_path or (repo / LEDGER_RELPATH), split_identity_hash=str(values["split_identity_hash"]),
                         expected_calls=calls, expected_seconds=seconds)
    state["expected"] = {"calls": calls, "speech_audio_seconds": seconds, "gpu_hours": ROW_GPU_HOURS, "failed_attempts": list(context.failed)}
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0 if state["countersigned"] else 4


# --------------------------------------------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--roster", choices=sorted(ROSTERS), default=None)
    parser.add_argument("--geometry", choices=sorted(GEOMETRIES), default="gpu",
                        help="gpu (live: GPU encoder server, one worker) or cpu (SUPERSEDED, record only; needs --allow-cpu)")
    parser.add_argument("--allow-cpu", action="store_true", help="permit the superseded CPU sidecar geometry (kept for the record)")
    parser.add_argument("--workers", type=int, default=None,
                        help="encode concurrency; default 1 on gpu (the server's own batching at -np 1) and 4 on cpu; refused above the fragment's -np")
    parser.add_argument("--promote-workers", type=int, default=8)
    parser.add_argument("--max-fold-seconds", type=float, default=3000.0,
                        help="with --smoke-rate: the cap on the projected Fold B encode time (default 3000 s, so the window stays under 1 GPU-h)")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--recovery-of", default=None,
                        help="the failed attempt id (no encoder receipt, spend counted) this start recovers; required, with a NEW "
                             "--attempt-id, whenever such an attempt exists; refused when none does")
    parser.add_argument("--plan-calls", type=int, default=None, help="cumulative call ceiling this attempt declares")
    parser.add_argument("--plan-speech-seconds", type=int, default=None, help="cumulative speech-second ceiling this attempt declares")
    parser.add_argument("--write", action="store_true", help="with --pin-receipt: write the two baselines (default prints only)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--promote-only", action="store_true")
    mode.add_argument("--pin-receipt", action="store_true")
    mode.add_argument("--check-ledger", action="store_true")
    mode.add_argument("--smoke-rate", action="store_true", help="read the smoke's encoder receipt and project the Fold B encode time")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    apply_geometry(args.geometry, allow_cpu=args.allow_cpu)
    apply_roster(args.roster)
    if args.pin_receipt:
        return pin_receipt(args)
    if args.check_ledger:
        return check_ledger(args)
    if args.smoke_rate:
        return smoke_rate(args)
    if args.roster is None:
        raise SystemExit("--roster is required for --dry-run, --run and --promote-only")
    if args.dry_run:
        return dry_run(args)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
