#!/usr/bin/env python3
"""Thinking-core speech-packet preparation over TRAIN Fold B (owner decision 266-E, 2026-10-11).

Exposure row ``SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1`` (package
``docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/``). The Instruct speech packets are
decoder-ready outputs of the Instruct audio encoder; 748 of 860 mmproj tensors differ in the Thinking model, so the Thinking
arm needs its OWN packet root, prepared by an encoder pass over the same 1,080 Fold B rows.

This is the Thinking sibling of ``scripts/slurp_evo_fold_preprocess.py``. It does NOT modify that driver: it loads it as a
module and reuses its parameterised helpers verbatim (roster sample construction with per-file media re-hash, the additive
refuse-on-conflict promotion, the promotion receipt document, the create-only receipt writer), so the packet format, the
promotion receipt shape and the roster logic are the Instruct ones by construction. What is Thinking-specific and lives here:

- the model pins: the Thinking decoder and its own bf16 mmproj come from the umbrella lock entry
  ``qwen3-omni-30b-a3b-thinking-gguf-q4km`` through ``scripts/flights/direct/direct_fb_pins.py`` (local hash receipts proven
  equal to the lock text) and must equal the committed runtime receipt ``docs/receipts/runtime-q4km-thinking-preprocess.json``;
- the roots: packet root ``/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6``, legacy cache
  ``/home/chao/feat-cache/slurp-thinking-q4km``, promotion receipt ``EVO-FOLD-B-V2-promotion.json`` under the new root;
- the refusals: pins that disagree with the lock or the runtime receipt, a packet root that exists and is not empty, a missing
  exposure row, an exposure row that is not root-countersigned (``--run`` only), an already-consumed row;
- the encoder receipt ``encoder-receipt.json`` under the run directory: llama.cpp build commit, decoder and mmproj sha256, roster
  split identity, per-file hashes (packet sha256 and chunk feature sha256 for Fold B, legacy cache file sha256 for the smoke),
  worker counts and timings.

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
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-smoke-4 --run      # via direct_fb_packets.sh
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-fold-b --run       # via direct_fb_packets.sh
    python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-fold-b --promote-only --attempt-id <new>
    python -B scripts/slurp_fold_preprocess_thinking.py --check-ledger                       # exit 0 only if countersigned
    python -B scripts/slurp_fold_preprocess_thinking.py --pin-receipt [--write]              # model-free

``--dry-run`` prints the plan (rows, roots, pins, ledger state) and makes no encoder call, opens no media file and starts no
process. ``--pin-receipt`` verifies the written promotion receipt against the pins, the runtime receipt and the packets on disk
and substitutes its sha256 for the zero sentinel in the two Thinking baselines (printed only without ``--write``).

Label-free by construction: samples come from the frozen runtime view of Fold B, which carries media identity and nothing else.
No gold, transcript or model output is opened, read or printed; the one-token responses are discarded unread.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import socket
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

RUN_ID = fam.PACKETS_ROW_ID
SIDECAR_FRAGMENT = pins_mod.PREPROCESS_FRAGMENT
DATASET_FRAGMENT = fam.DATASET
BASELINE_FRAGMENT = evo.BASELINE_FRAGMENT
EXPERIMENT_FRAGMENT = "slurp-direct-fold-b-thinking-preprocess-v1"
#: Relative to ``<repo>/docs/``, as ``FrozenCoreGate.for_study_repo`` takes it; equals the sidecar fragment's ``runtime_receipt``.
RUNTIME_RECEIPT_RELPATH = pins_mod.PREPROCESS_RECEIPT.removeprefix("docs/")
PACKET_ROOT = Path(fam.THINK_PACKET_ROOT)
LEGACY_CACHE = Path(pins_mod.THINKING_LEGACY_CACHE)
PROMOTION_RECEIPT = Path(fam.THINK_PROMOTION_RECEIPT)
LEDGER_RELPATH = "docs/exposure-ledger.md"
BASELINES = (
    "configs/baseline/slurp-direct-only-fold-b-thinking-baseline-v1.json",
    "configs/baseline/slurp-direct-only-fold-b-thinking-smoke-4-baseline-v1.json",
)
ENCODER_RECEIPT_NAME = "encoder-receipt.json"
ENCODER_RECEIPT_SCHEMA = "saea-thinking-packet-encoder-receipt-v1"
PLAN_SCHEMA = "saea-thinking-packet-plan-v1"
EXECUTION_PROFILE = "bounded-discovery-probe"
#: The row's declared totals, run-cumulative across the smoke and the Fold B attempt (ceiling of 3,154.797375 audio seconds).
ROW_CALLS = fam.ROWS
ROW_SPEECH_SECONDS = 3155
SMOKE_SPEECH_SECONDS = 10
#: The row's registered gpu-hours cell. The frozen-core gate compares the plan's gpu hours with the row's, so the ledger check must too
#: (first real run, 2026-10-11 10:41Z: the row said 0.0 and the plan claimed 1.0; the gate refused after --check-ledger had passed).
ROW_GPU_HOURS = 1.0
DRAFT_TOKEN = re.compile(r"\bdraft\b", re.IGNORECASE)
COUNTERSIGNED_TOKEN = re.compile(r"root countersigned", re.IGNORECASE)


class ThinkingRoster(NamedTuple):
    key: str
    rows: int | None  # None = every row of the Fold B view
    promote: bool
    default_attempt_id: str
    plan_calls: int
    plan_speech_seconds: int
    plan_gpu_hours: float


ROSTERS: dict[str, ThinkingRoster] = {
    "thinking-smoke-4": ThinkingRoster(
        "thinking-smoke-4", fam.SMOKE_ROWS, False, "attempt-packets-thinking-smoke-4-v1",
        fam.SMOKE_ROWS, SMOKE_SPEECH_SECONDS, 1.0),
    "thinking-fold-b": ThinkingRoster(
        "thinking-fold-b", None, True, "attempt-packets-thinking-fold-b-v1", ROW_CALLS, ROW_SPEECH_SECONDS, 1.0),
}


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
        ("split_role", "discovery"),
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
    roster_doc = json.loads((repo / fam.ROSTER["arm"]).read_text(encoding="utf-8"))
    if values.get("split_identity_hash") != roster_doc.get("split_identity_hash"):
        raise SystemExit("the dataset view's split identity differs from the Fold B roster receipt's")
    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a speech-native runtime view")
    if len(items) != fam.ROWS or int(values.get("count", -1)) != fam.ROWS:
        raise SystemExit("the Fold B runtime view must carry exactly %d rows" % fam.ROWS)


def smoke_ids(repo: Path = REPO) -> list[str]:
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
    ledger_path: Path, *, split_identity_hash: str, expected_calls: int = ROW_CALLS, expected_seconds: int = ROW_SPEECH_SECONDS,
    expected_gpu_hours: float = ROW_GPU_HOURS,
) -> dict[str, object]:
    """Presence and countersignature of the packets exposure row, and every disagreement with the registration.

    The numbers compared are the gate's own: calls, speech audio seconds AND gpu hours (a plan claiming more gpu hours than the row
    pre-registers is refused by the gate, so this check must refuse it first). The expected calls and seconds are the fold's total plus
    whatever a failed attempt already spent (see ``expected_row_totals``).
    """

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
    if row.get("split role") != "discovery" or row.get("split identity hash") != split_identity_hash:
        problems.append("split role / identity differ from Fold B's")
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


# ------------------------------------------------------------------------------------------------------- attempts


class AttemptContext(NamedTuple):
    """What earlier attempts of this run id already spent. Plan budgets are run-cumulative, so a successor declares prior plus its own."""

    prior_calls: int
    prior_audio_seconds: float
    wasted_calls: int
    wasted_audio_seconds: float
    failed: tuple[str, ...]


def attempt_history(data_root: Path, run_id: str = RUN_ID) -> tuple[list[dict[str, object]], list[str]]:
    """Attempt records of the run id, and run directories that have no attempt record (read-only).

    An attempt is COMPLETED only if its run directory holds the encoder receipt this driver writes last; an attempt record with
    contacts counted and no encoder receipt is a FAILED attempt whose spend is real and whose features may be lost.
    """

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
    """The ledger row's calls and speech seconds: the fold's own total plus the spend of a failed attempt (its features were lost)."""

    fold_audio = sum(float(item["audio_seconds"]) for item in values["items"])  # type: ignore[union-attr]
    return ROW_CALLS + context.wasted_calls, math.ceil(round(fold_audio + context.wasted_audio_seconds, 6))


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


# ------------------------------------------------------------------------------------------------------- the plan


def build_plan(
    *, roster: ThinkingRoster, values: Mapping[str, object], composed_hash: str, items: Sequence[Mapping[str, object]],
    pins: Mapping[str, object], runtime_receipt: Mapping[str, object], ledger: Mapping[str, object], workers: int,
    promote_workers: int, attempt_id: str, slots: int, problems: Sequence[str], context: AttemptContext,
) -> dict[str, object]:
    audio_seconds = sum(float(item["audio_seconds"]) for item in items)
    ceiling_calls, ceiling_seconds = plan_totals(context, len(items), audio_seconds)
    row_calls, row_seconds = expected_row_totals(values, context)
    return {
        "schema": PLAN_SCHEMA,
        "mode": "dry-run",
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
                    "promote_workers": promote_workers, "gpu_offload": "-ngl 0 --no-mmproj-offload"},
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
    evo._assert_worker_fit(args.workers, slots, roster.key, SIDECAR_FRAGMENT)
    attempt_id = args.attempt_id or roster.default_attempt_id
    history, orphans = attempt_history(evo.data_root())
    context = resolve_attempt_context(history, orphans, attempt_id=attempt_id, recovery_of=getattr(args, "recovery_of", None))
    calls, seconds = expected_row_totals(values, context)
    ledger = ledger_state(ledger_path or (repo / LEDGER_RELPATH), split_identity_hash=str(values["split_identity_hash"]),
                          expected_calls=calls, expected_seconds=seconds)
    problems = root_problems(
        roster, packet_root=PACKET_ROOT, legacy_cache=LEGACY_CACHE, promotion_receipt=PROMOTION_RECEIPT,
        allow_populated_root=bool(getattr(args, "promote_only", False)))
    return composed, values, pins, runtime_receipt, ledger, items, slots, attempt_id, problems, context


def dry_run(args, *, repo: Path = REPO, lock_path: Path | None = None, ledger_path: Path | None = None) -> int:
    roster = ROSTERS[args.roster]
    composed, values, pins, runtime_receipt, ledger, items, slots, attempt_id, problems, context = _prepare(
        args, roster, repo=repo, lock_path=lock_path, ledger_path=ledger_path)
    problems = [*problems, *ledger["problems"]]  # type: ignore[misc]
    plan = build_plan(
        roster=roster, values=values, composed_hash=composed.config_hash, items=items, pins=pins, runtime_receipt=runtime_receipt,
        ledger=ledger, workers=args.workers, promote_workers=args.promote_workers, attempt_id=attempt_id, slots=slots,
        problems=problems, context=context)
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
) -> dict[str, object]:
    llama = dict(runtime_receipt["llama_cpp"])  # type: ignore[arg-type]
    return {
        "schema": ENCODER_RECEIPT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
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
    if problems:
        raise SystemExit("REFUSED: " + "; ".join(problems))

    lock = evo.load_lock(lock_path or evo.umbrella_lock_path())
    root = evo.data_root()
    samples = evo.roster_samples(view_for(values, items), root, args.promote_workers, "slurp:train:", roster.key)
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
            split_role="discovery", split_identity_hash=str(values["split_identity_hash"]), planned_model_calls=calls,
            planned_gpu_hours=roster.plan_gpu_hours, planned_speech_audio_seconds=speech, protocol_hash=composed.config_hash,
            attempt_id=attempt_id, owner_allowance=values.get("owner_allowance")).validate(source_root=repo)
        log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])
        run_dir.mkdir(parents=True, exist_ok=False)
        # The patched llama.cpp server writes legacy feature-cache entries only into a directory that already exists. Nothing else
        # creates the Thinking cache (first real run, 2026-10-11 10:52Z: four contacts counted, nothing cached). Create it empty here,
        # before the first contact, together with the packet root's parent; the packet root itself is created by the promotion.
        LEGACY_CACHE.mkdir(parents=True, exist_ok=True)
        PACKET_ROOT.parent.mkdir(parents=True, exist_ok=True)
        log("spawning the CPU-only Thinking sidecar on %d at -np %d" % (evo.SIDECAR_PORT, slots))
        session = evo.start_session(
            runtime_root=evo.RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt, host="127.0.0.1",
            port=evo.SIDECAR_PORT, session_id="%s-%s-cpu-sidecar" % (RUN_ID, attempt_id),
            extra_argv=list(values["server_args"]), extra_env=dict(values["server_env"]),
            receipt_path=run_dir / "session-preprocess.receipt.json",
            server_log_path=run_dir / "session-preprocess.server.log", role="preprocess", ready_timeout_seconds=1800.0)
        log("sidecar up: pid=%s port=%s" % (session.pid, session.port))
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
            log("sidecar stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
        session_json = {"session_id": session.session_id, "pid": session.pid, "stop": stop,
                        "session_receipt_sha256": evo.canonical_sha256(session.as_json()),
                        "stop_receipt_sha256": evo.canonical_sha256(stop)}
        if failures:
            raise SystemExit("%d encode contacts failed; refusing to promote a partial cache: %r" % (len(failures), failures[:5]))
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
    encode_seconds = time.time() - started

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
            promotion_receipt_sha256=None, mode="encode-only", context=context)
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
        promotion_receipt=PROMOTION_RECEIPT, promotion_receipt_sha256=promotion_sha256, mode=mode, context=context)
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


def pin_receipt(args, *, repo: Path = REPO, lock_path: Path | None = None, receipt_path: Path = PROMOTION_RECEIPT,
                packet_root: Path = PACKET_ROOT, expected_rows: int = fam.ROWS) -> int:
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
        raise SystemExit("the promotion receipt does not cover exactly the %d Fold B rows" % expected_rows)
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
    for relpath in BASELINES:
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
               "next": "commit the two baselines, then re-pin per the package README (direct_fb_flip.sh; never --allow-output-change)"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


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
    parser.add_argument("--workers", type=int, default=4, help="encode concurrency; refused above the sidecar fragment's -np")
    parser.add_argument("--promote-workers", type=int, default=8)
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.pin_receipt:
        return pin_receipt(args)
    if args.check_ledger:
        return check_ledger(args)
    if args.roster is None:
        raise SystemExit("--roster is required for --dry-run, --run and --promote-only")
    if args.dry_run:
        return dry_run(args)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
