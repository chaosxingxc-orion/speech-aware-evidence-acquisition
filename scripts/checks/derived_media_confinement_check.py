#!/usr/bin/env python3
"""Model-free proof that a declared derived media root actually binds.

The 2026-09-07 defect: ``core.model._enforce_payload_binding`` confined every
payload's ``media_relpath`` to the CARRIER root alone, so every row of a
derived media population -- whose files live under
``$SPEECHRL_DATA_DIR/derived/<variant>/`` and whose dataset fragment declares
that root plus its hash-pinned D1 media supplement -- was refused the moment a
real request was built. Neither preflight nor the zero-socket wire checks ever
build a payload, so both passed while nothing could fly.

This check closes that observation gap for the fragments the repair exists for.
For each named dataset fragment it:

1. reads the committed fragment and records its SHA-256;
2. resolves the declared derived media roots through
   ``core.base.declared_derived_media_roots`` -- the same call the three
   binding construction sites make;
3. loads ONE real row through that carrier's own flight-script roster loader
   (real media file, real bytes re-hashed against the roster's record);
4. builds a real ``core.base.PayloadBindingContext`` through
   ``rails.core_client.build_payload_binding``;
5. drives the production ``_enforce_payload_binding`` with a payload carrying
   exactly the binding's own verified facts for that row, and records whether
   it binds.

Three controls run beside the positive case, all against the same real row:

* NO-DECLARATION: the identical binding with ``derived_media_roots=()`` -- what
  the code did before the repair -- must still be refused ("escapes its
  confined root"). This reproduces the defect against real bytes.
* DECOY: a payload naming a DIFFERENT real file under the same declared root
  must be refused by the I4 exact-relpath check.
* FOREIGN-DECLARATION: the same real row bound against ANOTHER fragment's
  declared derived root instead of its own must be refused, so one variant's
  declaration never legalizes another's media. (For a carrier-rooted
  comparator the row still binds under the carrier root, as it must.)

Zero model contacts, zero sockets, zero GPU: no transport is constructed, no
attempt is opened, nothing is written outside the receipt this check emits.

Usage::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/checks/derived_media_confinement_check.py --output <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[2]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "")
    != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
):
    raise SystemExit("package resolves to %s, not this checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    declared_derived_media_roots,
)
from speech_aware_evidence_acquisition.core.model import FrozenCoreError  # noqa: E402
from speech_aware_evidence_acquisition.core.model.binding import (  # noqa: E402
    _PayloadBindingMixin,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    build_payload_binding,
)

SCHEMA = "saea-derived-media-confinement-receipt-v1"

#: (dataset fragment, roster loader) for every fragment this check proves.
#: ``slurp`` reads its rows from the runtime view itself; ``a2t`` reads them
#: from the fragment's own hash-pinned calibration roster receipt.
FRAGMENTS: tuple[tuple[str, str], ...] = (
    ("slurp-speech-native-dev1000-tail2s", "slurp"),
    ("audio2tool-calibration-400-tail2s", "a2t"),
    ("audio2tool-calibration-400-16k", "a2t"),
    ("audio2tool-calibration-400-16k-tail2s", "a2t"),
    # The comparator: a carrier-rooted fragment that declares no derived root
    # and must therefore behave exactly as it always did.
    ("slurp-speech-native-dev1000", "slurp"),
    # The Audio2Tool paired-400 roster (A2T-PAIRED-400-V1) every HELD A2T cell and
    # the module ALL-OFF arm run on: carrier-rooted like the SLURP comparator
    # (declares no derived root), so the row must bind from the carrier root
    # and the decoy must still be refused.
    ("audio2tool-paired-400", "a2t"),
)


class _BindingProbe(_PayloadBindingMixin):
    """The production ``_enforce_payload_binding``, bound to a real binding
    context and a real plan.

    Deliberately NOT a ``FrozenCoreAdapter``: constructing one opens a durable
    attempt against the shared data root and checks a live transport session,
    neither of which a model-free check may do. The method under proof is the
    unmodified mixin function the adapter itself inherits, so the code path is
    the real one; only the attempt/transport lifecycle around it is absent.
    """

    def __init__(self, binding: object, plan: ExecutionPlan) -> None:
        self._binding = binding
        self._plan = plan
        self._slice_registry = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_flight_module(name: str):
    """Import a flight script by path -- the shared venv ships an unrelated
    top-level ``scripts`` package that shadows this repository's namespace
    directory, so ``import scripts.flights...`` is not reliable here."""

    path = REPO / "scripts" / "flights" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_saea_flight_{name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load flight module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fragment_values(dataset: str) -> tuple[Mapping[str, object], str]:
    path = REPO / "configs" / "dataset" / f"{dataset}.json"
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def _rows(dataset: str, loader: str, values: Mapping[str, object], root: Path, count: int):
    """The first ``count`` real rows of this fragment, through the carrier's own
    roster loader (media re-hashed against the roster's recorded identity)."""

    if loader == "slurp":
        module = _load_flight_module("run_slurp_closed_list_cell")
        ids = [str(item["sample_id"]) for item in values["items"][:count]]
        return module.roster_samples(values, root, limit_sample_ids=ids, workers=4)
    module = _load_flight_module("run_calibration_cell")
    roster_path = REPO / str(values["a2t_calibration_subset_receipt"])
    receipt = json.loads(roster_path.read_text(encoding="utf-8"))
    ids = [str(item["sample_id"]) for item in receipt["items"][:count]]
    return module.roster_samples(
        roster_path,
        str(values["a2t_calibration_subset_receipt_sha256"]),
        root,
        limit_sample_ids=ids,
        media_prefix=str(values.get("a2t_calibration_derived_subdir", "")) or None,
    )


def _plan(carrier_lock_key: str) -> ExecutionPlan:
    """A structurally valid plan whose ONLY role here is to carry the
    carrier_lock_key ``_enforce_payload_binding`` compares the payload against.

    No gate is opened, no attempt is reserved and no transport exists in this
    process, so the planned figures below are never spent -- an ExecutionPlan
    simply refuses to validate with a non-positive budget, and a check may not
    ship an unvalidated one.
    """

    return ExecutionPlan(
        run_id="SAEA-MF-DERIVED-MEDIA-CONFINEMENT-V1",
        execution_profile="model-free-check",
        carrier_lock_key=carrier_lock_key,
        split_role="dev",
        split_identity_hash="0" * 64,
        planned_model_calls=1,
        planned_gpu_hours=0.1,
        planned_speech_audio_seconds=1,
        protocol_hash="0" * 64,
        attempt_id="attempt-0001",
    ).validate()


def _payload(binding, sample_id: str, media_relpath: str) -> dict[str, object]:
    """Exactly the fields ``_enforce_payload_binding`` reads, filled from the
    binding's own verified facts -- never from anything invented here."""

    audio_seconds, sample_rate_hz = binding.sample_facts[sample_id]
    return {
        "carrier_lock_key": binding.carrier_lock_key,
        "sample_id": sample_id,
        "speech_ref": f"{binding.carrier_lock_key}/{sample_id}",
        "media_relpath": media_relpath,
        "audio_seconds": audio_seconds,
        "sample_rate_hz": sample_rate_hz,
    }


def _enforce(binding, plan, sample_id: str, media_relpath: str) -> str | None:
    """``None`` when the payload binds; the refusal message when it does not."""

    payload = _payload(binding, sample_id, media_relpath)
    try:
        _BindingProbe(binding, plan)._enforce_payload_binding(
            payload, payload["audio_seconds"]
        )
    except FrozenCoreError as error:
        return str(error)
    return None


def check_fragment(
    dataset: str, loader: str, root: Path, lock: Mapping[str, object], foreign_root: Path
) -> dict[str, object]:
    values, fragment_sha256 = _fragment_values(dataset)
    carrier_lock_key = str(values["carrier_lock_key"])
    roots = declared_derived_media_roots(values, root)
    samples = _rows(dataset, loader, values, root, 2)
    sample, decoy = samples[0], samples[1]
    plan = _plan(carrier_lock_key)
    carrier_root = asset_dir(lock, carrier_lock_key, root)
    binding = build_payload_binding(
        carrier_lock_key=carrier_lock_key,
        samples=[sample],
        data_root=root,
        carrier_root=carrier_root,
        derived_media_roots=roots,
    )
    bound = _enforce(binding, plan, sample.sample_id, sample.media_relpath)
    # NO-DECLARATION control: the pre-repair binding, same row, same bytes.
    undeclared = build_payload_binding(
        carrier_lock_key=carrier_lock_key,
        samples=[sample],
        data_root=root,
        carrier_root=carrier_root,
    )
    without = _enforce(undeclared, plan, sample.sample_id, sample.media_relpath)
    decoy_refusal = _enforce(binding, plan, sample.sample_id, decoy.media_relpath)
    # FOREIGN-DECLARATION control: another variant's real declared root, in
    # place of this fragment's own.
    foreign = build_payload_binding(
        carrier_lock_key=carrier_lock_key,
        samples=[sample],
        data_root=root,
        carrier_root=carrier_root,
        derived_media_roots=(foreign_root,),
    )
    foreign_refusal = _enforce(foreign, plan, sample.sample_id, sample.media_relpath)
    return {
        "dataset_fragment": dataset,
        "dataset_fragment_sha256": fragment_sha256,
        "carrier_lock_key": carrier_lock_key,
        "carrier_root": str(carrier_root),
        "declared_derived_media_roots": [str(path) for path in roots],
        "d1_media_supplement": (
            values.get("d1_media_supplement")
            or values.get("a2t_calibration_d1_media_supplement")
        ),
        "row": {
            "sample_id": sample.sample_id,
            "media_relpath": sample.media_relpath,
            "audio_sha256": sample.audio_ref.sha256,
            "audio_seconds": float(sample.audio_seconds),
            "sample_rate_hz": binding.sample_facts[sample.sample_id][1],
        },
        "binds": bound is None,
        "binding_refusal": bound,
        "control_without_declaration": {
            "refused": without is not None,
            "message": without,
        },
        "control_decoy_same_root": {
            "media_relpath": decoy.media_relpath,
            "refused": decoy_refusal is not None,
            "message": decoy_refusal,
        },
        "control_foreign_declaration": {
            "declared_root": str(foreign_root),
            "refused": foreign_refusal is not None,
            "message": foreign_refusal,
        },
    }


def verdict(result: Mapping[str, object]) -> str:
    """PASS when the row binds and every control lands where it must.

    For a fragment that DECLARES a derived root, both the no-declaration and
    the foreign-declaration controls must be refused -- the first reproduces
    the defect, the second shows a declaration is variant-local. A carrier-
    rooted comparator declares none, so both controls are simply the carrier
    root doing its unchanged job and the row must still bind. The decoy is
    refused either way: only the verified relpath is ever sendable.
    """

    declares = bool(result["declared_derived_media_roots"])
    without_refused = bool(result["control_without_declaration"]["refused"])
    foreign_refused = bool(result["control_foreign_declaration"]["refused"])
    ok = (
        bool(result["binds"])
        and bool(result["control_decoy_same_root"]["refused"])
        and (without_refused if declares else not without_refused)
        and (foreign_refused if declares else not foreign_refused)
    )
    return "PASS" if ok else "FAIL"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(
            REPO
            / "docs"
            / "checks"
            / "speech-aware-evidence-acquisition"
            / "2026-09-07-derived-media-confinement"
        ),
        help="directory the receipt and its MANIFEST.sha256 are written to",
    )
    parser.add_argument("--data-root", default=None)
    args = parser.parse_args(argv)

    root = Path(args.data_root).resolve() if args.data_root else data_root()
    lock = load_lock(umbrella_lock_path())
    # A real declared derived root belonging to a DIFFERENT variant (the
    # Earnings-22 ESB dev1500 tail-silence cuts), used by the
    # FOREIGN-DECLARATION control below.
    foreign_values, _ = _fragment_values("earnings22-esb-dev1500-tail2s")
    foreign_root = declared_derived_media_roots(foreign_values, root)[0]

    results = []
    for dataset, loader in FRAGMENTS:
        result = check_fragment(dataset, loader, root, lock, foreign_root)
        result["verdict"] = verdict(result)
        print(
            "%-40s %s  roots=%d  binds=%s"
            % (
                dataset,
                result["verdict"],
                len(result["declared_derived_media_roots"]),
                result["binds"],
            ),
            flush=True,
        )
        results.append(result)

    document = {
        "schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "study_commit": os.environ.get("SAEA_STUDY_COMMIT", ""),
        "data_root": str(root),
        "model_contacts": 0,
        "sockets_opened": 0,
        "fragments": results,
        "verdict": "PASS" if all(r["verdict"] == "PASS" for r in results) else "FAIL",
    }
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = out_dir / "derived-media-confinement.json"
    receipt.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = out_dir / "MANIFEST.sha256"
    lines = [
        "%s *%s" % (sha256_file(path), path.name)
        for path in sorted(out_dir.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("receipt %s: %s" % (receipt, document["verdict"]))
    return 0 if document["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
