#!/usr/bin/env python3
"""Contact-free wire check for the LP-2 confirmation cell.

The cell is ``SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-REPLICATE-V1``, a FRESH
REPLICATE of ``SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1``. Its whole claim is
that **nothing functional moved**: the predecessor's own baseline, model and
dataset fragments, the same decoding parameters including ``logprobs`` and
``top_logprobs``, the same packets, the same geometry, flown again so a
threshold fitted to the predecessor's rows can be read on rows it was not
fitted to. A replicate that quietly changed anything would answer a different
question, so the claim is checked mechanically rather than asserted.

Three stages, reported separately because they fail for different reasons.

``request``
    Composes both FULL cells with the real ``core.config.compose`` and diffs
    them key by key; asserts that **every key that moved belongs to an
    experiment fragment** and that the composed values with those keys removed
    are EQUAL on both sides -- the crisp form of "no model, dataset or
    baseline key moved". Then drives the real request path on both SMOKE cells
    through ``FlightRuntime.wire_check`` (fake gate, fake transport, zero
    contacts, zero sockets) and pairs the bound boundary payloads BY SAMPLE ID
    for the rows the two smokes share, asserting the only differences are the
    two values any two runs of one config differ in.

``payload_binding``
    The mandatory ``rails.core_client.payload_binding_stage`` on the
    replicate's own real roster rows -- every row of the eight-row smoke, and
    the first and last of the 1,000-row cell -- through the REAL carrier root
    and this fragment's declared derived media roots.

``media_identity``
    The speech-feature packets the two arms verified, compared sha256 by
    sha256 on the rows they share, plus the packet root and the pinned speech
    decoder hash both model fragments declare. The replicate must read the
    SAME bytes off the same featcache the predecessor read, or its "replicate"
    is a different observation.

**Zero model contacts, zero servers, zero sockets.** The packets ARE read and
hash-verified, so this runs on the machine that holds ``SPEECHRL_DATA_DIR``.

Usage (WSL2)::

    python scripts/slurp_label_token_logprob_wire_check.py
    python scripts/slurp_label_token_logprob_wire_check.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-09-slurp-label-token-logprob-replicate-wire-check"
)

#: The FULL cells, composed but never flown here.
FULL_CELLS = (
    ("predecessor", "slurp-dev1000-closed-list-logprob-v1", "closed-list-logprob"),
    (
        "replicate",
        "slurp-dev1000-closed-list-logprob-replicate-v1",
        "closed-list-logprob-replicate",
    ),
)

#: The SMOKE cells the request stage actually drives. The replicate's smoke
#: names eight ids and the predecessor's four; the four are a prefix of the
#: eight, and the payload pairing runs on exactly that intersection.
SMOKE_CELLS = (
    (
        "predecessor",
        "slurp-dev1000-closed-list-logprob-smoke-4-v1",
        "closed-list-logprob-smoke",
    ),
    (
        "replicate",
        "slurp-dev1000-closed-list-logprob-replicate-smoke8-v1",
        "closed-list-logprob-replicate-smoke",
    ),
)

#: RUN-LOCAL payload values: they differ between any two runs of the SAME
#: config, so a difference here is not a protocol difference. ``request_id``
#: is the flight's dispatch-order counter; ``decoding_params.id_slot`` is the
#: ``per-sample`` sentinel resolved to whichever server slot the executor
#: allocated in that run. Each is named rather than tolerated silently.
RUN_LOCAL_PAYLOAD_FIELDS = ("request_id",)
RUN_LOCAL_DECODING_KEYS = ("id_slot",)

#: The model-fragment keys the media stage insists both arms share verbatim.
MEDIA_MODEL_KEYS = ("speech_feature_root", "server_env")


def _load_module(relpath: str, name: str):
    """Import a repository script BY PATH.

    The shared venv ships an unrelated top-level ``scripts`` package (verl)
    that shadows this repository's namespace directory, so ``import
    scripts...`` is not reliable here.
    """

    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_sha256(values: Mapping[str, object]) -> str:
    """The same canonicalization ``core.config`` hashes with, restated here so
    this receipt never depends on a private name."""

    blob = json.dumps(
        values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _experiment_keys(names: Sequence[str]) -> set[str]:
    keys: set[str] = set()
    for name in names:
        doc = json.loads(
            (REPO / "configs" / "experiment" / f"{name}.json").read_text(encoding="utf-8")
        )
        keys |= set(doc)
    return keys


def _compose(runner, experiment: str, cell_id: str) -> tuple[Any, Mapping[str, object]]:
    from speech_aware_evidence_acquisition.core.config import compose

    cells = runner.load_cells(experiment)
    if cell_id not in cells:
        raise SystemExit(f"unknown cell {cell_id!r} in {experiment!r}: {sorted(cells)}")
    cell = cells[cell_id]
    composed = compose(
        REPO,
        str(cell["model_fragment"]),
        str(cell["dataset_fragment"]),
        str(cell["baseline_fragment"]),
        experiment,
    )
    return composed, cell


def _trace_payloads(receipt: Mapping[str, object]) -> list[Mapping[str, object]]:
    """The boundary payloads the wire check actually bound, read back out of
    the REAL trace it wrote -- never re-derived here."""

    from speech_aware_evidence_acquisition.data.lock import data_root

    run_id = str(receipt["wire_check_run_id"])
    attempt_id = str(receipt["attempt_id"])
    path = (
        Path(data_root()) / "wire-check" / run_id / attempt_id / f"{run_id}.trace.jsonl"
    )
    if not path.exists():
        raise SystemExit(f"wire-check trace not found at {path}")
    payloads: list[tuple[str, Mapping[str, object]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("channel") == "MODEL_REQUEST":
            payloads.append((record["record_id"], record["payload"]["payload"]))
    payloads.sort(key=lambda item: item[0])
    return [payload for _, payload in payloads]


def _protocol_payload_sha256(payload: Mapping[str, object]) -> str:
    trimmed = {
        key: value
        for key, value in payload.items()
        if key not in RUN_LOCAL_PAYLOAD_FIELDS
    }
    decoding = trimmed.get("decoding_params")
    if isinstance(decoding, Mapping):
        trimmed["decoding_params"] = {
            key: value
            for key, value in decoding.items()
            if key not in RUN_LOCAL_DECODING_KEYS
        }
    return _canonical_sha256(trimmed)


def request_stage(runner, *, max_workers: int) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.core.config import protocol_hash

    problems: list[str] = []

    composed: dict[str, Any] = {}
    cells: dict[str, Mapping[str, object]] = {}
    for label, experiment, cell_id in FULL_CELLS:
        composed[label], cells[label] = _compose(runner, experiment, cell_id)
    left, right = composed["predecessor"].values, composed["replicate"].values

    experiment_keys = _experiment_keys([entry[1] for entry in FULL_CELLS])
    shared = set(left) & set(right)
    moved = sorted(key for key in shared if left[key] != right[key])
    only_left = sorted(set(left) - set(right))
    only_right = sorted(set(right) - set(left))

    # THE claim: every key that differs at all belongs to an experiment
    # fragment, so no model, dataset or baseline key moved.
    non_experiment = sorted(
        key for key in set(moved) | set(only_left) | set(only_right)
        if key not in experiment_keys
    )
    if non_experiment:
        problems.append(
            f"keys outside the experiment fragments differ: {non_experiment}"
        )

    # ... and the crisp form of the same claim: strip the experiment
    # fragments' own keys and the two composed configs are EQUAL.
    functional = {
        label: {
            key: value
            for key, value in composed[label].values.items()
            if key not in experiment_keys
        }
        for label in composed
    }
    if functional["predecessor"] != functional["replicate"]:
        problems.append("the composed configs differ outside the experiment fragments")
    functional_hash = {
        label: _canonical_sha256(values) for label, values in functional.items()
    }

    left_decoding = dict(left.get("decoding_params") or {})
    right_decoding = dict(right.get("decoding_params") or {})
    if left_decoding != right_decoding:
        problems.append(
            "decoding_params moved; a replicate must carry the predecessor's own "
            f"decoding parameters: {left_decoding} vs {right_decoding}"
        )
    for key in ("baseline_fragment", "dataset_fragment", "model_fragment", "arm"):
        if cells["predecessor"][key] != cells["replicate"][key]:
            problems.append(f"the two cells do not share one {key}")

    stand_in_split = "0" * 64
    hashes = {
        label: {
            "config_hash": composed[label].config_hash,
            "protocol_hash_against_a_fixed_split": protocol_hash(
                composed[label].config_hash, str(cells[label]["arm"]), stand_in_split
            ),
            "fragments": dict(composed[label].fragments),
        }
        for label in composed
    }
    if hashes["predecessor"]["config_hash"] == hashes["replicate"]["config_hash"]:
        problems.append(
            "config_hash did not move: two runs cannot share an experiment identity"
        )

    # -- the real request path, on both smokes ------------------------------
    receipts: dict[str, Mapping[str, object]] = {}
    payloads: dict[str, list[Mapping[str, object]]] = {}
    for label, experiment, cell_id in SMOKE_CELLS:
        experiment_doc = runner.load_experiment(experiment)
        smoke_cells = runner.load_cells(experiment)
        cell = smoke_cells[cell_id]
        dataset = str(cell["dataset_fragment"])
        runtime, _identity = runner.build_runtime(
            cell=cell,
            dataset=dataset,
            experiment=experiment,
            run_id=str(experiment_doc["experiment_id"]),
            attempt_id=f"attempt-wire-lp2-{label}",
            campaign_active=False,
            limit_sample_ids=runner.population_ids(experiment_doc, dataset),
            sealed_head=None,
        )
        receipts[label] = dict(
            runtime.wire_check(seal_and_score=False, max_workers=max_workers)
        )
        payloads[label] = _trace_payloads(receipts[label])

    bound = {
        label: {str(payload["sample_id"]): payload for payload in payloads[label]}
        for label in payloads
    }
    shared_ids = sorted(set(bound["predecessor"]) & set(bound["replicate"]))
    if not shared_ids:
        problems.append("the two smokes share no sample id, so nothing can be paired")
    if not set(bound["predecessor"]) <= set(bound["replicate"]):
        problems.append(
            "the predecessor smoke's rows are not a subset of the replicate smoke's"
        )

    per_request: list[dict[str, Any]] = []
    for sample_id in shared_ids:
        a, b = bound["predecessor"][sample_id], bound["replicate"][sample_id]
        one_sided = sorted(set(a) ^ set(b))
        field_moved = sorted(
            key
            for key in set(a) & set(b)
            if a[key] != b[key] and key not in RUN_LOCAL_PAYLOAD_FIELDS
        )
        a_decoding = dict(a.get("decoding_params") or {})
        b_decoding = dict(b.get("decoding_params") or {})
        decoding_moved = sorted(
            key
            for key in set(a_decoding) | set(b_decoding)
            if key not in RUN_LOCAL_DECODING_KEYS
            and a_decoding.get(key) != b_decoding.get(key)
        )
        if one_sided:
            problems.append(f"{sample_id}: payload key sets differ: {one_sided}")
        if field_moved not in ([], ["decoding_params"]):
            problems.append(f"{sample_id}: payload fields moved: {field_moved}")
        if decoding_moved:
            problems.append(f"{sample_id}: decoding_params moved: {decoding_moved}")
        digests = {
            "predecessor": _protocol_payload_sha256(a),
            "replicate": _protocol_payload_sha256(b),
        }
        if digests["predecessor"] != digests["replicate"]:
            problems.append(
                f"{sample_id}: the canonical boundary payloads are not identical"
            )
        per_request.append(
            {
                "sample_id": sample_id,
                "payload_fields_moved": field_moved,
                "decoding_params_moved": decoding_moved,
                "protocol_payload_sha256": digests,
                "task_instruction_sha256": hashlib.sha256(
                    str(a.get("task_instruction", "")).encode("utf-8")
                ).hexdigest(),
                "task_instruction_identical": a.get("task_instruction")
                == b.get("task_instruction"),
            }
        )

    for label in receipts:
        if receipts[label]["model_contacts"] != 0:
            problems.append(f"{label}: the wire check reported a model contact")
        if not receipts[label]["payload_keys_equal_arm_visible_fields"]:
            problems.append(f"{label}: payload keys are not the arm's D2 field set")

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "shared_fragments": {
            key: str(cells["predecessor"][key])
            for key in ("baseline_fragment", "dataset_fragment", "model_fragment", "arm")
        },
        "config_keys_moved": moved,
        "config_keys_only_predecessor": only_left,
        "config_keys_only_replicate": only_right,
        "keys_outside_the_experiment_fragments_that_differ": non_experiment,
        "decoding_params": {
            "predecessor": left_decoding,
            "replicate": right_decoding,
            "identical": left_decoding == right_decoding,
        },
        "functional_config_equal_outside_experiment_keys": (
            functional["predecessor"] == functional["replicate"]
        ),
        "functional_config_sha256": functional_hash,
        "hashes": hashes,
        "split_identity_stand_in": stand_in_split,
        "smoke_rows": {label: sorted(bound[label]) for label in bound},
        "paired_rows": shared_ids,
        "requests": per_request,
        "receipts": {
            label: {
                key: receipts[label][key]
                for key in (
                    "arm",
                    "config_hash",
                    "protocol_hash",
                    "split_id",
                    "split_identity_hash",
                    "sample_count",
                    "contact_count",
                    "payload_keys",
                    "max_tokens",
                    "model_contacts",
                )
            }
            for label in receipts
        },
        "run_local_exemptions": {
            "payload_fields": list(RUN_LOCAL_PAYLOAD_FIELDS),
            "decoding_keys": list(RUN_LOCAL_DECODING_KEYS),
            "why": (
                "both differ between any two runs of the SAME config -- request_id is "
                "the flight's dispatch-order counter and id_slot is the per-sample "
                "server slot the batch executor allocated in that run -- so a "
                "difference in either is not a protocol difference. Each is reported "
                "per request rather than hidden."
            ),
        },
        "_packets": {
            label: dict(receipts[label]["speech_packets_verified"] or {})
            for label in receipts
        },
    }


def payload_binding_stage_for(experiment: str, cell_id: str) -> dict[str, Any]:
    """``rails.core_client.payload_binding_stage`` on one cell's own real rows.

    Loads ONLY the rows the stage will check -- every row of an eight-row
    smoke, else the first and last of the fragment's declared order -- through
    the SLURP flight script's own roster loader (real media, re-hashed against
    the roster's own record), and drives the binding through the REAL carrier
    root plus this fragment's declared derived media roots.
    """

    from speech_aware_evidence_acquisition.core.base import declared_derived_media_roots
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.core_client import (
        PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT,
        payload_binding_stage,
    )

    module = _load_module(
        "scripts/flights/run_slurp_closed_list_cell.py", "saea_slurp_closed_list_runner"
    )
    experiment_doc = json.loads(
        (REPO / "configs" / "experiment" / f"{experiment}.json").read_text(
            encoding="utf-8"
        )
    )
    cell = module.load_cells(experiment)[cell_id]
    dataset = str(cell["dataset_fragment"])
    values = json.loads(
        (REPO / "configs" / "dataset" / f"{dataset}.json").read_text(encoding="utf-8")
    )
    carrier_lock_key = str(values["carrier_lock_key"])
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    carrier_root = asset_dir(lock, carrier_lock_key, root)
    derived_media_roots = declared_derived_media_roots(values, root)

    all_ids = module.population_ids(experiment_doc, dataset) or [
        str(item["sample_id"]) for item in values["items"]
    ]
    wanted = (
        list(all_ids)
        if len(all_ids) <= PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT
        else [all_ids[0], all_ids[-1]]
    )
    samples = module.roster_samples(values, root, limit_sample_ids=wanted, workers=4)
    result = payload_binding_stage(
        dataset_fragment=dataset,
        carrier_lock_key=carrier_lock_key,
        samples=samples,
        data_root=root,
        carrier_root=carrier_root,
        derived_media_roots=derived_media_roots,
    )
    receipt = dict(result.as_receipt())
    receipt["experiment"] = experiment
    receipt["cell"] = cell_id
    receipt["fragment_row_count"] = len(all_ids)
    receipt["checked_every_row"] = len(all_ids) <= len(result.rows_checked)
    return receipt


def payload_binding_stage_half() -> dict[str, Any]:
    problems: list[str] = []
    stages = {
        "replicate_smoke8": payload_binding_stage_for(
            "slurp-dev1000-closed-list-logprob-replicate-smoke8-v1",
            "closed-list-logprob-replicate-smoke",
        ),
        "replicate_dev1000": payload_binding_stage_for(
            "slurp-dev1000-closed-list-logprob-replicate-v1",
            "closed-list-logprob-replicate",
        ),
    }
    for label, stage in stages.items():
        # The stage's own receipt reports ``bound`` and a ``failures`` map, not
        # a status string: it is the production binding rail's own shape, and
        # reading it for a key it never carries would make a green receipt out
        # of a stage that never ran.
        if stage.get("bound") is not True:
            problems.append(f"{label}: the payload binding stage did not bind")
        if stage.get("failures"):
            problems.append(f"{label}: binding failures {sorted(stage['failures'])}")
        if stage.get("model_contacts") != 0 or stage.get("sockets_opened") != 0:
            problems.append(f"{label}: the binding stage reported a contact or a socket")
    if not stages["replicate_smoke8"]["checked_every_row"]:
        problems.append("the eight-row smoke did not have every row checked")
    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "stages": stages,
    }


def media_identity_stage(
    packets: Mapping[str, Mapping[str, str]], runner
) -> dict[str, Any]:
    """The packets the two arms verified, and the roots they were read from.

    A replicate that read different bytes off a different featcache is a
    different observation wearing the same config, so the identity is checked
    rather than assumed.
    """

    problems: list[str] = []
    predecessor = dict(packets.get("predecessor") or {})
    replicate = dict(packets.get("replicate") or {})
    shared = sorted(set(predecessor) & set(replicate))
    if not shared:
        problems.append("the two arms verified no packet in common")
    mismatched = sorted(
        sample_id for sample_id in shared if predecessor[sample_id] != replicate[sample_id]
    )
    if mismatched:
        problems.append(f"packet sha256 differ on {len(mismatched)} row(s): {mismatched}")

    fragments = {}
    for label, experiment, cell_id in FULL_CELLS:
        cell = runner.load_cells(experiment)[cell_id]
        doc = json.loads(
            (REPO / "configs" / "model" / f"{cell['model_fragment']}.json").read_text(
                encoding="utf-8"
            )
        )
        fragments[label] = {key: doc.get(key) for key in MEDIA_MODEL_KEYS}
        fragments[label]["model_fragment"] = str(cell["model_fragment"])
    if fragments["predecessor"] != fragments["replicate"]:
        problems.append("the two arms declare different packet roots or server env")

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "packets_verified": {
            "predecessor": len(predecessor),
            "replicate": len(replicate),
            "shared_rows": len(shared),
            "identical_sha256_on_shared_rows": not mismatched,
        },
        "packet_sha256_on_shared_rows": {
            sample_id: predecessor[sample_id] for sample_id in shared
        },
        "declared_media_identity": fragments,
    }


def _write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt")
    parser.add_argument("--max-workers", type=int, default=1)
    args = parser.parse_args(argv)

    runner = _load_module(
        "scripts/flights/run_slurp_closed_list_cell.py", "saea_slurp_closed_list_runner"
    )
    request = request_stage(runner, max_workers=args.max_workers)
    packets = request.pop("_packets")
    document: dict[str, Any] = {
        "schema": "saea-slurp-label-token-logprob-replicate-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "question": (
            "does the LP-2 confirmation cell send the predecessor's own request, so "
            "that a threshold fitted to the predecessor's rows is read on a fresh "
            "observation of the SAME configuration rather than on a different cell"
        ),
        "model_contacts": 0,
        "servers_started": 0,
        "sockets_opened": 0,
        "request": request,
        "payload_binding": payload_binding_stage_half(),
        "media_identity": media_identity_stage(packets, runner),
    }
    statuses = {
        stage: document[stage]["status"]
        for stage in ("request", "payload_binding", "media_identity")
    }
    document["stages"] = statuses
    document["status"] = (
        "PASS" if all(value == "PASS" for value in statuses.values()) else "FAIL"
    )

    payload = json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
    if not args.write:
        print(payload)
        return 0 if document["status"] == "PASS" else 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "wire-check.json").write_text(payload, encoding="utf-8", newline="\n")
    _write_manifest(OUT_DIR)
    print(f"{document['status']}  {statuses}")
    print((OUT_DIR / "MANIFEST.sha256").read_text(encoding="utf-8"))
    return 0 if document["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
