#!/usr/bin/env python3
"""Prove, with zero model contacts and zero sockets, that the SLURP logprob
probe arm differs from the sealed closed-list comparator by exactly one thing:
the declared decoding keys.

Three halves, reported separately because they fail for different reasons.

``config``
    Real ``core.config.compose`` on both cells. Reports the key-by-key diff of
    the two merged configs, the ``config_hash`` of each, and the
    ``protocol_hash`` each yields against the SAME split identity hash -- so
    any hash movement is attributable to the config alone. The expected diff is
    exactly: ``decoding_params`` (two keys added), plus the experiment
    fragment's own identity keys, which necessarily differ because this is a
    different run.

``payload``
    Real ``core.flight.FlightRuntime.wire_check`` on both smoke cells: the real
    composed fragments, the real adapter and samples, the real payload binding,
    the real hash-verified speech-feature packets, the real
    ``FrozenCoreClient``/``FrozenCoreAdapter`` stack with its D2 allowlist and
    attempt accounting. Only the gate and the transport are fakes
    (``WireCheckGate`` / ``WireCheckTransport``, which never opens a socket).
    The boundary payloads are then read back OUT OF THE REAL TRACE each run
    writes -- the ``MODEL_REQUEST`` records -- and diffed field by field. The
    expected diff is exactly ``decoding_params``.

``body``
    The payload-to-HTTP-body step belongs to ``core.model.transport.
    LlamaServerTransport``, which needs an attested live session and therefore
    cannot be constructed here. It is proved instead by the two committed unit
    tests this half names and runs, which assert that the request body carries
    no ``logprobs``/``top_logprobs``/``n_probs`` key unless the config declares
    one, and that with the keys declared the body differs from the baseline
    body by exactly those two keys.

Model-free: zero model contacts, zero servers, zero sockets, zero GPU. The
speech-feature packets ARE read and hash-verified (that is the point of the
payload half), so this runs on the machine that holds them.

Usage (WSL2)::

    python scripts/slurp_logprob_wire_check.py
    python scripts/slurp_logprob_wire_check.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-08-slurp-logprob-judge-probe-wire-check"
)

#: (label, experiment fragment, cell id). Both are FOUR-ROW smoke cells: the
#: question is request SHAPE, not the roster, and the two smokes name the same
#: four sample ids in their own fragments.
CELLS = (
    (
        "comparator",
        "slurp-dev1000-closed-list-direct-smoke-v1",
        "closed-list-direct-smoke",
    ),
    (
        "probe",
        "slurp-dev1000-closed-list-logprob-smoke-4-v1",
        "closed-list-logprob-smoke",
    ),
)

#: The full cells, composed but never flown here -- the config half runs on
#: these, so the hashes this receipt reports are the registered cells' own.
FULL_CELLS = (
    ("comparator", "slurp-dev1000-closed-list-direct-v1", "closed-list-direct"),
    ("probe", "slurp-dev1000-closed-list-logprob-v1", "closed-list-logprob"),
)

#: What the config half is allowed to see moving. `decoding_params` is the
#: probe itself; the rest are the experiment fragment's own identity, which
#: cannot be shared by two different runs.
EXPECTED_CONFIG_DIFF = {
    "decoding_params",
    "experiment_id",
    "purpose",
    "execution_plan",
    "cells",
    "budget_basis",
}

#: Keys either fragment may carry alone (documentation keys, not behaviour).
EXPECTED_CONFIG_ONLY_ONE_SIDE = {
    "closed_list_authority",
    "comparator",
    "decision_rule",
    "one_key_basis",
    "profile_basis",
    "declared_protocol_change",
    "preregistration",
    "read_script",
    "wire_check_script",
    "populations",
    "acceptance",
}

#: The decoding keys the probe is allowed to add, and nothing else.
EXPECTED_DECODING_DIFF = {"logprobs": True, "top_logprobs": 5}

#: RUN-LOCAL payload values: they differ between any two runs of the SAME
#: config, so a difference here is not a protocol difference and must not be
#: read as one. Both are named rather than tolerated silently.
#:
#: ``request_id`` is the flight's own per-request counter, assigned in dispatch
#: order; two runs of the same cell can dispatch four samples in two orders and
#: hand the same sample a different counter. ``decoding_params.id_slot`` is the
#: ``per-sample`` sentinel the batch executor resolves to whichever server slot
#: it allocated for that sample in THAT run (core.model.request_types's own
#: note on the key). Everything else about a payload must be identical.
RUN_LOCAL_PAYLOAD_FIELDS = ("request_id",)
RUN_LOCAL_DECODING_KEYS = ("id_slot",)

#: "19 passed in 4.14s" -> "19 passed". A receipt with a wall clock in it
#: does not reproduce.
_PYTEST_DURATION = re.compile(r"\s+in\s+[\d.]+s\s*$")

BODY_TESTS = (
    "tests/unit/test_llama_server_transport.py"
    "::test_the_request_body_carries_no_logprobs_key_unless_the_config_declares_one",
    "tests/unit/test_llama_server_transport.py"
    "::test_declaring_the_decoding_keys_puts_exactly_them_on_the_wire",
    "tests/unit/test_llama_server_transport.py"
    "::test_a_logprobs_choice_is_forwarded_verbatim_into_the_envelope",
    "tests/unit/test_model_logprobs_trace.py",
)


def _load_runner():
    """Import the SLURP flight runner by path.

    The shared venv ships an unrelated top-level ``scripts`` package that
    shadows this repository's namespace directory, so ``import
    scripts.flights...`` is not reliable here (same reasoning and same fix as
    ``scripts/checks/derived_media_confinement_check.py``).
    """

    path = REPO / "scripts" / "flights" / "run_slurp_closed_list_cell.py"
    spec = importlib.util.spec_from_file_location("saea_slurp_closed_list_runner", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load flight runner at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def config_half(runner) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.core.config import protocol_hash

    composed: dict[str, Any] = {}
    cells: dict[str, Mapping[str, object]] = {}
    for label, experiment, cell_id in FULL_CELLS:
        composed[label], cells[label] = _compose(runner, experiment, cell_id)

    left, right = composed["comparator"].values, composed["probe"].values
    shared = set(left) & set(right)
    moved = sorted(key for key in shared if left[key] != right[key])
    only_left = sorted(set(left) - set(right))
    only_right = sorted(set(right) - set(left))

    left_decoding = dict(left.get("decoding_params") or {})
    right_decoding = dict(right.get("decoding_params") or {})
    added = {
        key: right_decoding[key]
        for key in sorted(set(right_decoding) - set(left_decoding))
    }
    removed = sorted(set(left_decoding) - set(right_decoding))
    changed = sorted(
        key
        for key in set(left_decoding) & set(right_decoding)
        if left_decoding[key] != right_decoding[key]
    )

    # The SAME split identity hash on both sides, so protocol-hash movement is
    # attributable to the config and to nothing else.
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

    problems: list[str] = []
    unexpected_moved = sorted(set(moved) - EXPECTED_CONFIG_DIFF)
    if unexpected_moved:
        problems.append(f"config keys moved that should not have: {unexpected_moved}")
    unexpected_one_sided = sorted(
        (set(only_left) | set(only_right)) - EXPECTED_CONFIG_ONLY_ONE_SIDE
    )
    if unexpected_one_sided:
        problems.append(f"config keys present on one side only: {unexpected_one_sided}")
    if added != EXPECTED_DECODING_DIFF:
        problems.append(f"decoding_params added {added}, expected {EXPECTED_DECODING_DIFF}")
    if removed:
        problems.append(f"decoding_params dropped {removed}")
    if changed:
        problems.append(f"decoding_params changed the value of {changed}")
    if cells["comparator"]["baseline_fragment"] != cells["probe"]["baseline_fragment"]:
        problems.append("the two cells do not share one baseline fragment")
    if cells["comparator"]["dataset_fragment"] != cells["probe"]["dataset_fragment"]:
        problems.append("the two cells do not share one dataset fragment")
    if cells["comparator"]["arm"] != cells["probe"]["arm"]:
        problems.append("the two cells do not share one arm")
    if hashes["comparator"]["config_hash"] == hashes["probe"]["config_hash"]:
        problems.append("config_hash did not move: a declared decoding key must move it")
    if (
        hashes["comparator"]["protocol_hash_against_a_fixed_split"]
        == hashes["probe"]["protocol_hash_against_a_fixed_split"]
    ):
        problems.append("protocol_hash did not move")

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "shared_fragments": {
            "baseline": str(cells["comparator"]["baseline_fragment"]),
            "dataset": str(cells["comparator"]["dataset_fragment"]),
            "arm": str(cells["comparator"]["arm"]),
        },
        "model_fragments": {
            label: str(cells[label]["model_fragment"]) for label in cells
        },
        "config_keys_moved": moved,
        "config_keys_only_comparator": only_left,
        "config_keys_only_probe": only_right,
        "decoding_params_added": added,
        "decoding_params_removed": removed,
        "decoding_params_changed": changed,
        "hashes": hashes,
        "split_identity_stand_in": stand_in_split,
    }


def _trace_payloads(receipt: Mapping[str, object]) -> list[Mapping[str, object]]:
    """The boundary payloads a wire check actually sent, read back out of the
    REAL trace it wrote -- never re-derived here."""

    from speech_aware_evidence_acquisition.data.lock import data_root

    run_id = str(receipt["wire_check_run_id"])
    attempt_id = str(receipt["attempt_id"])
    path = (
        Path(data_root())
        / "wire-check"
        / run_id
        / attempt_id
        / f"{run_id}.trace.jsonl"
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
    """The payload's identity with the run-local values stripped.

    Same canonicalization the adapter itself uses for ``request_sha256``
    (``core.model.request_types._canonical``), minus ``request_id`` and
    ``decoding_params.id_slot`` -- the two values that differ between any two
    runs of the same config. What is left is exactly what "the same request"
    means across runs.
    """

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
    blob = json.dumps(
        trimmed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def payload_half(runner, *, max_workers: int) -> dict[str, Any]:
    receipts: dict[str, Mapping[str, object]] = {}
    payloads: dict[str, list[Mapping[str, object]]] = {}
    for label, experiment, cell_id in CELLS:
        experiment_doc = runner.load_experiment(experiment)
        cells = runner.load_cells(experiment)
        cell = cells[cell_id]
        dataset = str(cell["dataset_fragment"])
        runtime, _identity = runner.build_runtime(
            cell=cell,
            dataset=dataset,
            experiment=experiment,
            run_id=str(experiment_doc["experiment_id"]),
            attempt_id=f"attempt-wire-logprob-{label}",
            campaign_active=False,
            limit_sample_ids=runner.population_ids(experiment_doc, dataset),
            sealed_head=None,
        )
        receipt = dict(runtime.wire_check(seal_and_score=False, max_workers=max_workers))
        receipts[label] = receipt
        payloads[label] = _trace_payloads(receipt)

    problems: list[str] = []
    # Pair by SAMPLE ID, never by dispatch position: two runs of the same cell
    # may dispatch the same four samples in two orders, and comparing position
    # to position would then report six spurious differences (measured: it did).
    left = {str(payload["sample_id"]): payload for payload in payloads["comparator"]}
    right = {str(payload["sample_id"]): payload for payload in payloads["probe"]}
    if not left or set(left) != set(right):
        problems.append(
            f"the two arms did not send the same sample set: {sorted(set(left) ^ set(right))}"
        )

    per_request: list[dict[str, Any]] = []
    for sample_id in sorted(set(left) & set(right)):
        a, b = left[sample_id], right[sample_id]
        moved = sorted(
            key
            for key in set(a) & set(b)
            if a[key] != b[key] and key not in RUN_LOCAL_PAYLOAD_FIELDS
        )
        one_sided = sorted(set(a) ^ set(b))
        a_decoding = dict(a.get("decoding_params") or {})
        b_decoding = dict(b.get("decoding_params") or {})
        added = {
            key: b_decoding[key] for key in sorted(set(b_decoding) - set(a_decoding))
        }
        shared_decoding = set(a_decoding) & set(b_decoding)
        other = sorted(
            key
            for key in shared_decoding
            if a_decoding[key] != b_decoding[key] and key not in RUN_LOCAL_DECODING_KEYS
        )
        if one_sided:
            problems.append(f"{sample_id}: payload key sets differ: {one_sided}")
        if moved != ["decoding_params"]:
            problems.append(
                f"{sample_id}: payload fields moved beyond decoding_params: {moved}"
            )
        if added != EXPECTED_DECODING_DIFF:
            problems.append(
                f"{sample_id}: decoding_params added {added}, "
                f"expected {EXPECTED_DECODING_DIFF}"
            )
        if other:
            problems.append(f"{sample_id}: decoding_params values changed: {other}")
        per_request.append(
            {
                "sample_id": sample_id,
                "fields_moved": moved,
                "decoding_params_added": added,
                "decoding_params_changed": other,
                # The stable identity of what each arm actually sent: the
                # canonical payload with the two run-local values removed. The
                # adapter's own request_sha256 cannot serve here -- it hashes
                # the id_slot the executor happened to allocate, so it differs
                # between two runs of the SAME config and would make this
                # receipt irreproducible while proving nothing.
                "protocol_payload_sha256": {
                    "comparator": _protocol_payload_sha256(a),
                    "probe": _protocol_payload_sha256(b),
                },
                # The one field whose identity carries the whole prompt: if the
                # instruction had moved, "one key" would be false.
                "task_instruction_sha256": hashlib.sha256(
                    str(a.get("task_instruction", "")).encode("utf-8")
                ).hexdigest(),
                "task_instruction_identical": a.get("task_instruction")
                == b.get("task_instruction"),
            }
        )

    for label in ("comparator", "probe"):
        if receipts[label]["model_contacts"] != 0:
            problems.append(f"{label}: wire check reported a model contact")
        if not receipts[label]["payload_keys_equal_arm_visible_fields"]:
            problems.append(f"{label}: payload keys are not the arm's D2 field set")

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
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
                    "speech_packets_verified",
                    "model_contacts",
                )
            }
            for label in receipts
        },
        "note": (
            "protocol_payload_sha256 is the identity of the CANONICAL BOUNDARY PAYLOAD "
            "that crossed the adapter/transport seam, with the two run-local values "
            "stripped. It differs between the two arms by construction -- that is the "
            "probe -- and the field-by-field diff above is what says the difference is "
            "only the decoding keys. The flight receipts' own request_body_sha256 and "
            "id_slot are deliberately NOT mirrored here: they carry the allocated slot "
            "and would make this receipt irreproducible while proving nothing."
        ),
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
    }


def body_half(*, run_tests: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "proved_by": list(BODY_TESTS),
        "why_not_here": (
            "core.model.transport.LlamaServerTransport verifies an attested live "
            "session (pid, binary image and listening socket) at construction, so it "
            "cannot be built inside a model-free check; the committed unit tests build "
            "it against a self-attesting local process and a fake post()."
        ),
        "wire_keys": {
            "endpoint": "/v1/chat/completions (OpenAI-compatible), never /completion",
            "request": ["logprobs", "top_logprobs"],
            "response": "choices[0].logprobs.content[]",
            "server_translation": (
                "llama.cpp-featcache 04ccc72a tools/server/server-common.cpp:1525-1529 "
                "maps logprobs/top_logprobs onto the native n_probs"
            ),
        },
    }
    if not run_tests:
        result["status"] = "SKIPPED"
        return result
    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *BODY_TESTS],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    lines = [line for line in process.stdout.strip().splitlines() if line.strip()]
    # The wall-clock suffix ("19 passed in 4.14s") would make this receipt
    # irreproducible; the count is the fact, the duration is not.
    summary = _PYTEST_DURATION.sub("", lines[-1]) if lines else ""
    result["status"] = "PASS" if process.returncode == 0 else "FAIL"
    result["pytest_returncode"] = process.returncode
    result["pytest_summary"] = summary
    if process.returncode != 0:
        result["pytest_tail"] = lines[-20:]
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument(
        "--skip-payload",
        action="store_true",
        help="config and body halves only (no packet reads)",
    )
    parser.add_argument("--skip-body", action="store_true", help="do not run pytest")
    args = parser.parse_args(argv)

    runner = _load_runner()
    document: dict[str, Any] = {
        "schema": "saea-slurp-logprob-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "model_contacts": 0,
        "servers_started": 0,
        "sockets_opened": 0,
        "question": (
            "does the SLURP logprob probe arm differ from the sealed closed-list "
            "comparator by exactly the declared decoding keys, and nothing else"
        ),
        "config": config_half(runner),
        "body": body_half(run_tests=not args.skip_body),
    }
    document["payload"] = (
        {"status": "SKIPPED", "reason": "--skip-payload"}
        if args.skip_payload
        else payload_half(runner, max_workers=args.max_workers)
    )
    statuses = {half: document[half]["status"] for half in ("config", "payload", "body")}
    document["status"] = (
        "PASS" if all(value in ("PASS", "SKIPPED") for value in statuses.values()) else "FAIL"
    )
    document["halves"] = statuses

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / "wire-check.json"
        payload = json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
        path.write_text(payload, encoding="utf-8", newline="\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = OUT_DIR / "MANIFEST.sha256"
        manifest.write_text(f"{digest}  wire-check.json\n", encoding="utf-8", newline="\n")
        print(f"{digest}  {path}")
    else:
        print(json.dumps(document, indent=2, sort_keys=True, default=str))
    return 0 if document["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
