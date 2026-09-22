#!/usr/bin/env python3
"""Model-free helper steps for ``scripts/flights/batch/r01_prep23.sh``.

Three subcommands, each pure Python over already-sealed bytes: no model,
encoder, tokenizer, scorer, GPU or network contact, and no gold, answer,
transcript or score is opened.

``materialise``
    Verify the sealed step-2b receipt of
    ``SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1``, hash its
    ``queries.jsonl`` and its own ``receipt.json``, and turn the committed alias
    TEMPLATE into the runnable copy ``core.preparation_vectors`` accepts. The
    template carries a ``how_to_fill`` key and the placeholders
    ``PENDING_STEP_2B_QUERIES_SHA256`` / ``PENDING_STEP_2B_RECEIPT_SHA256``;
    ``prepare_vector_dimension_alias`` requires exactly the eight contract keys,
    so the template is never handed to it and the committed file is never
    edited in place.

``alias-receipt``
    Read the zero-contact 2c receipt and re-hash the segment export it declares.

``report``
    Print every output path with its sha256 and the values that fill the ROLL-1
    ``stage3_pending_placeholders`` entries.

The state file is a ``KEY=value`` env file the shell runbook sources between
steps.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

RUN = "SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1"
EXPORT_ROW = "SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1"
PROTOCOL_RELPATH = (
    "configs/preparation/slurp-stage3-construction-r01-speech-query-encoding-protocol-v1.json"
)
ROSTER_RECEIPT_SHA256 = "fdb6521a0863b5f11f7ccea9fba5a1e598d65c5eb05b13a68d1198d5e01ba5f0"
VECTOR_DIR = "vectors/slurp-stage3-construction-r01-v1"
SEGMENTS_RELPATH = VECTOR_DIR + "/query-vectors-speech-segments.jsonl"
CONTENT_RELPATH = VECTOR_DIR + "/query-vectors-speech-content-v1.jsonl"
PROVENANCE_RELPATH = VECTOR_DIR + "/query-vectors-speech-content-v1.provenance.json"
ENCODE_RECEIPT_RELPATH = "preparation-runs/%s/encode-v1/receipt.json" % RUN
QUERIES_RELPATH = "prepared/%s/queries.jsonl" % RUN
ALIAS_RECEIPT_RELPATH = (
    "prepared/SAEA-SLURP-STAGE3-CONSTRUCTION-R01-ALIAS-V1/query-dimension-alias.json"
)
ALIAS_CONFIG_FIELDS = frozenset(
    {
        "schema",
        "source",
        "target_dimension",
        "expected_rows",
        "vector_width",
        "output_relpath",
        "receipt_relpath",
        "source_receipts",
    }
)


class PreparationRunbookError(RuntimeError):
    """Refuse a step whose inputs are missing, partial or drifting."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(document, field, expected, label):
    actual = document.get(field)
    if actual != expected:
        raise PreparationRunbookError(
            "%s %s is %r, expected %r" % (label, field, actual, expected)
        )
    return actual


def read_state(state: Path) -> dict[str, str]:
    values = {}
    for line in Path(state).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def append_state(state: Path, pairs) -> None:
    with io.open(state, "a", encoding="utf-8", newline="\n") as handle:
        for key, value in pairs:
            handle.write("%s=%s\n" % (key, value))


def materialise_alias_config(template: dict, *, queries_sha256: str, receipt_sha256: str) -> dict:
    """Strip the template annotation and bind both step-2b digests.

    Pure and side-effect free so the unit tests can exercise exactly the
    transform the runbook performs.
    """

    config = json.loads(json.dumps(template))
    config.pop("how_to_fill", None)
    config["source"]["sha256"] = queries_sha256
    config["source_receipts"][0]["sha256"] = receipt_sha256
    if set(config) != ALIAS_CONFIG_FIELDS:
        raise PreparationRunbookError(
            "materialised alias config fields %s differ from the "
            "core.preparation_vectors contract" % sorted(config)
        )
    raw = json.dumps(config, indent=2) + "\n"
    if "PENDING_" in raw:
        raise PreparationRunbookError(
            "materialised alias config still carries a PENDING_ placeholder"
        )
    return config


def step_materialise(args) -> int:
    repo, data = Path(args.repo_root), Path(args.data_root)
    receipt_path = data / ENCODE_RECEIPT_RELPATH
    if not receipt_path.is_file():
        raise PreparationRunbookError(
            "step 2b has not sealed its receipt yet: %s" % receipt_path
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    protocol_sha256 = sha256_of(repo / PROTOCOL_RELPATH)
    for field, expected in (
        ("schema", "saea-speech-query-preparation-receipt-v1"),
        ("status", "SEALED"),
        ("run_id", RUN),
        ("attempt_id", "encode-v1"),
        ("protocol_sha256", protocol_sha256),
        ("logical_encoder_contacts", 800),
        ("source_inventory_sha256",
         "a4ed13ad67441f5ceaf8be14ef52e3516a6c5f86d1155c6fb754a8ef6b2f771b"),
    ):
        require(receipt, field, expected, "step-2b receipt")
    queries_sha256 = sha256_of(data / QUERIES_RELPATH)
    if queries_sha256 != receipt["query_rows_sha256"]:
        raise PreparationRunbookError(
            "queries.jsonl hashes to %s, not the receipt's %s"
            % (queries_sha256, receipt["query_rows_sha256"])
        )
    receipt_sha256 = sha256_of(receipt_path)

    template = json.loads((repo / args.template).read_text(encoding="utf-8"))
    config = materialise_alias_config(
        template, queries_sha256=queries_sha256, receipt_sha256=receipt_sha256
    )
    raw = json.dumps(config, indent=2) + "\n"
    runnable = Path(args.runnable)
    runnable.parent.mkdir(parents=True, exist_ok=True)
    if runnable.exists() and runnable.read_text(encoding="utf-8") != raw:
        raise PreparationRunbookError("refusing to change an existing %s" % runnable)
    with io.open(runnable, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    alias_config_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    state = Path(args.state)
    state.parent.mkdir(parents=True, exist_ok=True)
    with io.open(state, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("")
    append_state(
        state,
        (
            ("QUERIES_RELPATH", QUERIES_RELPATH),
            ("QUERIES_SHA256", queries_sha256),
            ("ENCODE_RECEIPT_RELPATH", ENCODE_RECEIPT_RELPATH),
            ("ENCODE_RECEIPT_SHA256", receipt_sha256),
            ("PROTOCOL_SHA256", protocol_sha256),
            ("ALIAS_CONFIG_SHA256", alias_config_sha256),
        ),
    )
    print("A  step-2b receipt SEALED, 800 encoder contacts, protocol %s" % protocol_sha256)
    print("A  %s sha256 %s" % (QUERIES_RELPATH, queries_sha256))
    print("A  %s sha256 %s" % (ENCODE_RECEIPT_RELPATH, receipt_sha256))
    print("A  materialised %s sha256 %s" % (runnable, alias_config_sha256))
    return 0


def step_alias_receipt(args) -> int:
    data, state = Path(args.data_root), Path(args.state)
    path = data / ALIAS_RECEIPT_RELPATH
    if not path.is_file():
        raise PreparationRunbookError("step 2c has not written %s" % path)
    output = json.loads(path.read_text(encoding="utf-8"))["output"]
    for field, expected in (
        ("schema", "saea-sealed-segment-vector-dimension-alias-v1"),
        ("row_count", 800),
        ("segment_count", 800),
        ("vector_width", 2048),
        ("source_dimension", "content"),
        ("target_dimension", "intent-boundary"),
        ("values_unchanged", True),
        ("max_absolute_delta", 0.0),
        ("encoder_contacts", 0),
        ("tokenizer_contacts", 0),
        ("model_contacts", 0),
        ("output_relpath", SEGMENTS_RELPATH),
    ):
        require(output, field, expected, "alias receipt")
    segments_sha256 = output["output_sha256"]
    measured = sha256_of(data / SEGMENTS_RELPATH)
    if measured != segments_sha256:
        raise PreparationRunbookError(
            "segment export hashes to %s, not the receipt's %s" % (measured, segments_sha256)
        )
    append_state(
        state,
        (
            ("SEGMENTS_SHA256", segments_sha256),
            ("ALIAS_RECEIPT_RELPATH", ALIAS_RECEIPT_RELPATH),
            ("ALIAS_RECEIPT_SHA256", sha256_of(path)),
        ),
    )
    print("C  %s sha256 %s (800 rows, 800 segments, 0 contacts)" % (SEGMENTS_RELPATH, segments_sha256))
    return 0


def step_report(args) -> int:
    data, values = Path(args.data_root), read_state(Path(args.state))
    content_sha256 = sha256_of(data / CONTENT_RELPATH)
    provenance_sha256 = sha256_of(data / PROVENANCE_RELPATH)
    provenance = json.loads((data / PROVENANCE_RELPATH).read_text(encoding="utf-8"))
    for field, expected in (
        ("schema", "saea-slurp-exemplar-query-vectors-provenance-v1"),
        ("row_count", 800),
        ("sha256", content_sha256),
        ("execution_profile", "model-free-check"),
        ("parent_relpath", SEGMENTS_RELPATH),
        ("parent_sha256", values["SEGMENTS_SHA256"]),
        ("source_dimension", "intent-boundary"),
        ("target_dimension", "content"),
        ("exposure_ledger_row", EXPORT_ROW),
    ):
        require(provenance, field, expected, "preparation-3 provenance")

    print()
    print("=== OUTPUTS (relative to SPEECHRL_DATA_DIR) ===")
    for relpath, digest in (
        (values["QUERIES_RELPATH"], values["QUERIES_SHA256"]),
        (values["ENCODE_RECEIPT_RELPATH"], values["ENCODE_RECEIPT_SHA256"]),
        (values["ALIAS_RECEIPT_RELPATH"], values["ALIAS_RECEIPT_SHA256"]),
        (SEGMENTS_RELPATH, values["SEGMENTS_SHA256"]),
        (CONTENT_RELPATH, content_sha256),
        (PROVENANCE_RELPATH, provenance_sha256),
    ):
        print("  %-92s %s" % (relpath, digest))

    print()
    print("=== ROLL-1 FILL VALUES (configs/baseline/slurp-native-stage3-rollout-baseline-v1.json) ===")
    print("knowledge_stores.intent-boundaries.phase_supply.perception.query_source")
    print("  kind                     sealed-segment-vectors")
    print("  relpath                  %s" % SEGMENTS_RELPATH)
    print("  sha256                   %s" % values["SEGMENTS_SHA256"])
    print("  tool_contact_ledger_row  %s" % RUN)
    print("knowledge_stores.train-exemplars.phase_supply.solver.query_source")
    print("  kind                     sealed-vectors")
    print("  relpath                  %s" % CONTENT_RELPATH)
    print("  sha256                   %s" % content_sha256)
    print("  tool_contact_ledger_row  %s" % EXPORT_ROW)
    print("preparation_source_receipts[6].sha256  %s" % ROSTER_RECEIPT_SHA256)
    print("preparation_source_receipts[7]  root=data")
    print("  relpath %s" % values["ENCODE_RECEIPT_RELPATH"])
    print("  sha256  %s" % values["ENCODE_RECEIPT_SHA256"])
    print("preparation_source_receipts[8]  root=data -- READ BEFORE PINNING:")
    print("  the preparation note section 4 assigns [8] to preparation 3's own receipt")
    print("    relpath %s" % PROVENANCE_RELPATH)
    print("    sha256  %s" % provenance_sha256)
    print("  the DEV-2000-ADDED precedent (slurp-native-default-plan-dev2000-added-baseline-v1.json")
    print("  index 5) instead pins the 2c alias receipt and never pins the content provenance")
    print("    relpath %s" % values["ALIAS_RECEIPT_RELPATH"])
    print("    sha256  %s" % values["ALIAS_RECEIPT_SHA256"])
    print("  pin one; if the re-pin follows the precedent, append the other rather than dropping it")
    print()
    print("Zero model, encoder, tokenizer, scorer, GPU and network contacts in steps 2c and 3.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="step", required=True)

    materialise = subparsers.add_parser("materialise")
    materialise.add_argument("--repo-root", required=True)
    materialise.add_argument("--data-root", required=True)
    materialise.add_argument("--template", required=True)
    materialise.add_argument("--runnable", required=True)
    materialise.add_argument("--state", required=True)
    materialise.set_defaults(handler=step_materialise)

    alias = subparsers.add_parser("alias-receipt")
    alias.add_argument("--data-root", required=True)
    alias.add_argument("--state", required=True)
    alias.set_defaults(handler=step_alias_receipt)

    report = subparsers.add_parser("report")
    report.add_argument("--data-root", required=True)
    report.add_argument("--state", required=True)
    report.set_defaults(handler=step_report)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except PreparationRunbookError as error:
        print("REFUSED: %s" % error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
