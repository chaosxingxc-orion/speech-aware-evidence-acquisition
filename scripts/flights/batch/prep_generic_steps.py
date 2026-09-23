#!/usr/bin/env python3
"""Model-free helper steps for the GENERIC preparation runbooks.

The roster-parameterised generalisation of
``scripts/flights/batch/r01_prep23_steps.py`` and
``scripts/flights/batch/r01_prep2_runtime_config.py``, written for owner
decision 107 of 2026-09-23 (the expanded DEV side). The two R01 files are left
exactly as they are: their outputs are sealed and their byte-for-byte
reproducibility is part of the record.

Five subcommands, each pure Python over already-sealed bytes: no model,
encoder, tokenizer, scorer, GPU or network contact, and no gold, answer,
transcript or score is opened.

``roster-facts``
    Print the ``PREPROCESS_ROSTERS`` registration of one packet-promotion
    roster as ``KEY=value`` lines a shell runbook sources, so a task entry
    never has to repeat the run id, the sidecar fragment or the slot count in
    prose.

``runtime-config``
    Mint the step-2b speech-query runtime config under the data root and print
    its sha256 plus the exact launch line. It cannot be a committed file:
    ``core.speech_preparation_runtime.main`` refuses unless its ``study_head``
    equals the HEAD of the clean checkout the launch runs from.

``materialise``
    Verify the sealed step-2b receipt, hash its ``queries.jsonl`` and its own
    ``receipt.json``, and turn the committed alias TEMPLATE into the runnable
    copy ``core.preparation_vectors`` accepts (the template carries a
    ``how_to_fill`` key and two ``PENDING_STEP_2B_*`` placeholders and is never
    handed to the contract or edited in place).

``alias-receipt``
    Read the zero-contact 2c receipt and re-hash the segment export it declares.

``report``
    Print every output path with its sha256 and the values a consumer binds.

The state file is a ``KEY=value`` env file the shell runbook sources between
steps.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

REPO_DEFAULT = Path(__file__).resolve().parents[3]
DEFAULT_UMBRELLA_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
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


class PreparationSet(NamedTuple):
    """One roster's speech-query preparation chain, named once."""

    name: str
    run_id: str
    attempt: str
    alias_run_id: str
    export_row: str
    protocol_relpath: str
    alias_template_relpath: str
    roster_relpath: str
    dataset_relpath: str
    inventory_relpath: str
    inventory_sha256: str
    vector_dir: str
    coordination_dir: str
    session_id: str
    rows: int
    vector_width: int
    split_identity_hash: str
    split_role: str
    planned_speech_audio_seconds: int
    planned_gpu_hours: float

    @property
    def queries_relpath(self) -> str:
        return "prepared/%s/queries.jsonl" % self.run_id

    @property
    def encode_receipt_relpath(self) -> str:
        return "preparation-runs/%s/%s/receipt.json" % (self.run_id, self.attempt)

    @property
    def alias_receipt_relpath(self) -> str:
        return "prepared/%s/query-dimension-alias.json" % self.alias_run_id

    @property
    def segments_relpath(self) -> str:
        return self.vector_dir + "/query-vectors-speech-segments.jsonl"

    @property
    def content_relpath(self) -> str:
        return self.vector_dir + "/query-vectors-speech-content-v1.jsonl"

    @property
    def provenance_relpath(self) -> str:
        return self.vector_dir + "/query-vectors-speech-content-v1.provenance.json"

    @property
    def runtime_config_relpath(self) -> str:
        return self.coordination_dir + "/runtime-config-v1.json"

    @property
    def alias_runnable_relpath(self) -> str:
        return self.coordination_dir + "/query-alias-v1.json"

    @property
    def state_relpath(self) -> str:
        return self.coordination_dir + "/prep23-state.env"


#: Every registered preparation chain. Owner decision 107's DEVEL-REMAINDER is
#: the first; a later roster adds one entry rather than a second copy of this
#: file.
PREPARATION_SETS: dict[str, PreparationSet] = {
    "devel-remainder": PreparationSet(
        name="devel-remainder",
        run_id="SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1",
        attempt="encode-v1",
        alias_run_id="SAEA-SLURP-DEVEL-REMAINDER-ALIAS-V1",
        export_row="SAEA-SLURP-DEVEL-REMAINDER-QUERY-VECTOR-EXPORT-V1",
        # The roster-bound relpaths and hashes are V2's: the coordinator ruling of
        # 2026-09-23 (provisional decision 109) carved the 60 FINAL60 and the 60
        # historic probe-60 recordings out of the remainder. The run id, the
        # attempt, the vector directory and the coordination directory are
        # UNCHANGED, because no contact has been made under any of them yet.
        protocol_relpath=(
            "configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v2.json"
        ),
        alias_template_relpath="configs/preparation/slurp-devel-remainder-query-alias-v2.json",
        roster_relpath="docs/receipts/rosters/slurp-devel-remainder-v2.json",
        dataset_relpath="configs/dataset/slurp-speech-native-devel-remainder-v2.json",
        inventory_relpath=(
            "coordination/slurp-devel-remainder-speech-query-source-inventory-v2.json"
        ),
        inventory_sha256="d8ca6915864d4b08f99157d990b52543f6b705184686546a5922acea6dda9aae",
        vector_dir="vectors/slurp-devel-remainder-v1",
        coordination_dir="coordination/slurp-devel-remainder-query-encoding-v1",
        session_id="local-nemotron-slurp-devel-remainder-query-v1",
        rows=6570,
        vector_width=2048,
        split_identity_hash=(
            "f8af142bec49755d70364b665b31e3963972084fb73a568c9921f53b41fd341a"
        ),
        split_role="dev",
        planned_speech_audio_seconds=18612,
        planned_gpu_hours=2.0,
    ),
}


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


def resolve_set(name: str) -> PreparationSet:
    if name not in PREPARATION_SETS:
        raise PreparationRunbookError(
            "unknown preparation set %r; registered: %s"
            % (name, ", ".join(sorted(PREPARATION_SETS)))
        )
    return PREPARATION_SETS[name]


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


def git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def load_preprocess_driver(repo_root: Path):
    """Import scripts/slurp_evo_fold_preprocess.py by path.

    The driver is the single source of truth for a roster's run id, sidecar
    fragment and plan; a runbook reads it instead of repeating it.
    """

    path = Path(repo_root) / "scripts" / "slurp_evo_fold_preprocess.py"
    spec = importlib.util.spec_from_file_location("slurp_evo_fold_preprocess_runbook", path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreadable checkout
        raise PreparationRunbookError("cannot import %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def step_roster_facts(args) -> int:
    repo = Path(args.repo_root)
    driver = load_preprocess_driver(repo)
    if args.roster not in driver.PREPROCESS_ROSTERS:
        raise PreparationRunbookError(
            "unknown preprocess roster %r; registered: %s"
            % (args.roster, ", ".join(sorted(driver.PREPROCESS_ROSTERS)))
        )
    spec = driver.PREPROCESS_ROSTERS[args.roster]
    values = driver.compose(
        repo, spec.sidecar_fragment, spec.dataset_fragment,
        driver.BASELINE_FRAGMENT, spec.experiment_fragment,
    ).values
    slots = driver._server_slots(values, spec.sidecar_fragment)
    pairs = [
        ("PREP_RUN_ID", spec.run_id),
        ("PREP_ATTEMPT_ID", spec.default_attempt_id),
        ("PREP_SIDECAR_FRAGMENT_REGISTERED", spec.sidecar_fragment),
        ("PREP_DATASET_FRAGMENT", spec.dataset_fragment),
        ("PREP_EXPERIMENT_FRAGMENT", spec.experiment_fragment),
        ("PREP_SLOTS", str(slots)),
        ("PREP_PLAN_CALLS", str(spec.plan_calls)),
        ("PREP_PLAN_SPEECH_SECONDS", str(spec.plan_speech_seconds)),
        ("PREP_ROWS", str(int(values["count"]))),
        ("PREP_PROMOTION_RECEIPT", spec.promotion_receipt_name or ""),
        ("PREP_IS_EQUIVALENCE", "1" if spec.equivalence is not None else "0"),
    ]
    if args.expect_sidecar_fragment and args.expect_sidecar_fragment != spec.sidecar_fragment:
        raise PreparationRunbookError(
            "PREP_SIDECAR_FRAGMENT=%r disagrees with the registered %r for roster %r; the "
            "fragment enters the composed config hash, so it is changed in the roster table "
            "and re-registered, never overridden at launch"
            % (args.expect_sidecar_fragment, spec.sidecar_fragment, args.roster)
        )
    if args.expect_workers is not None and args.expect_workers > slots:
        raise PreparationRunbookError(
            "PREP_WORKERS=%d exceeds the %d slots %r serves"
            % (args.expect_workers, slots, spec.sidecar_fragment)
        )
    for key, value in pairs:
        print("%s=%s" % (key, value))
    return 0


def build_runtime_config(
    preparation: PreparationSet, *, study_head: str, protocol_sha256: str,
    umbrella_lock: str, umbrella_lock_sha256: str,
) -> dict:
    """The exact document ``core.speech_preparation_runtime`` consumes."""

    return {
        "plan": {
            "attempt_id": preparation.attempt,
            "carrier_lock_key": "slurp",
            "execution_profile": "bounded-discovery-probe",
            "planned_gpu_hours": preparation.planned_gpu_hours,
            "planned_model_calls": preparation.rows,
            "planned_speech_audio_seconds": preparation.planned_speech_audio_seconds,
            "protocol_hash": protocol_sha256,
            "run_id": preparation.run_id,
            "schema": "saea-execution-plan-v1",
            "split_identity_hash": preparation.split_identity_hash,
            "split_role": preparation.split_role,
            "study": "speech-aware-evidence-acquisition",
        },
        "protocol": {"path": preparation.protocol_relpath, "sha256": protocol_sha256},
        "session_id": preparation.session_id,
        "study_head": study_head,
        "umbrella_lock": {"path": umbrella_lock, "sha256": umbrella_lock_sha256},
    }


def step_runtime_config(args) -> int:
    preparation = resolve_set(args.set)
    repo_root, data_root = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    dirt = [
        line for line in git(repo_root, "status", "--porcelain").splitlines()
        if not line.startswith("??")
    ]
    if dirt and not args.allow_dirty:
        raise PreparationRunbookError(
            "%d tracked change(s) in %s; the launch binds a clean study_head"
            % (len(dirt), repo_root)
        )
    study_head = git(repo_root, "rev-parse", "HEAD")
    protocol_sha256 = sha256_of(repo_root / preparation.protocol_relpath)
    umbrella_lock = Path(args.umbrella_lock)
    document = build_runtime_config(
        preparation,
        study_head=study_head,
        protocol_sha256=protocol_sha256,
        umbrella_lock=str(umbrella_lock),
        umbrella_lock_sha256=sha256_of(umbrella_lock),
    )
    raw = json.dumps(document, indent=2, sort_keys=True) + "\n"
    out = data_root / preparation.runtime_config_relpath
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.read_text(encoding="utf-8") != raw:
        raise PreparationRunbookError(
            "%s already exists with different bytes; delete it deliberately if a fresh "
            "registration is truly intended" % out
        )
    with io.open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    config_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    print("PREP_RUNTIME_CONFIG=%s" % out)
    print("PREP_RUNTIME_CONFIG_SHA256=%s" % config_sha256)
    print("PREP_STUDY_HEAD=%s" % study_head)
    print("PREP_PROTOCOL_SHA256=%s" % protocol_sha256)
    print(
        "# plan %d calls / %d speech seconds / %.1f GPU hours / split_role %s"
        % (
            preparation.rows,
            preparation.planned_speech_audio_seconds,
            preparation.planned_gpu_hours,
            preparation.split_role,
        )
    )
    return 0


def materialise_alias_config(template: dict, *, queries_sha256: str, receipt_sha256: str) -> dict:
    """Strip the template annotation and bind both step-2b digests.

    Pure and side-effect free so a unit test can exercise exactly the transform
    the runbook performs.
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
    if "PENDING_" in json.dumps(config):
        raise PreparationRunbookError(
            "materialised alias config still carries a PENDING_ placeholder"
        )
    return config


def step_materialise(args) -> int:
    preparation = resolve_set(args.set)
    repo, data = Path(args.repo_root), Path(args.data_root)
    receipt_path = data / preparation.encode_receipt_relpath
    if not receipt_path.is_file():
        raise PreparationRunbookError(
            "step 2b has not sealed its receipt yet: %s" % receipt_path
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    protocol_sha256 = sha256_of(repo / preparation.protocol_relpath)
    for field, expected in (
        ("schema", "saea-speech-query-preparation-receipt-v1"),
        ("status", "SEALED"),
        ("run_id", preparation.run_id),
        ("attempt_id", preparation.attempt),
        ("protocol_sha256", protocol_sha256),
        ("logical_encoder_contacts", preparation.rows),
        ("source_inventory_sha256", preparation.inventory_sha256),
    ):
        require(receipt, field, expected, "step-2b receipt")
    queries_sha256 = sha256_of(data / preparation.queries_relpath)
    if queries_sha256 != receipt["query_rows_sha256"]:
        raise PreparationRunbookError(
            "queries.jsonl hashes to %s, not the receipt's %s"
            % (queries_sha256, receipt["query_rows_sha256"])
        )
    receipt_sha256 = sha256_of(receipt_path)

    template = json.loads(
        (repo / preparation.alias_template_relpath).read_text(encoding="utf-8")
    )
    config = materialise_alias_config(
        template, queries_sha256=queries_sha256, receipt_sha256=receipt_sha256
    )
    raw = json.dumps(config, indent=2) + "\n"
    runnable = data / preparation.alias_runnable_relpath
    runnable.parent.mkdir(parents=True, exist_ok=True)
    if runnable.exists() and runnable.read_text(encoding="utf-8") != raw:
        raise PreparationRunbookError("refusing to change an existing %s" % runnable)
    with io.open(runnable, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    alias_config_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    state = data / preparation.state_relpath
    state.parent.mkdir(parents=True, exist_ok=True)
    with io.open(state, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("")
    append_state(
        state,
        (
            ("QUERIES_RELPATH", preparation.queries_relpath),
            ("QUERIES_SHA256", queries_sha256),
            ("ENCODE_RECEIPT_RELPATH", preparation.encode_receipt_relpath),
            ("ENCODE_RECEIPT_SHA256", receipt_sha256),
            ("PROTOCOL_SHA256", protocol_sha256),
            ("ALIAS_CONFIG", str(runnable)),
            ("ALIAS_CONFIG_SHA256", alias_config_sha256),
            ("SEGMENTS_RELPATH", preparation.segments_relpath),
            ("CONTENT_NAME", Path(preparation.content_relpath).name),
            ("VECTOR_DIR", preparation.vector_dir),
            ("EXPORT_ROW", preparation.export_row),
            ("STATE", str(state)),
        ),
    )
    print("PREP_STATE=%s" % state)
    print("A  step-2b receipt SEALED, %d encoder contacts, protocol %s"
          % (preparation.rows, protocol_sha256))
    print("A  %s sha256 %s" % (preparation.queries_relpath, queries_sha256))
    print("A  %s sha256 %s" % (preparation.encode_receipt_relpath, receipt_sha256))
    print("A  materialised %s sha256 %s" % (runnable, alias_config_sha256))
    return 0


def step_alias_receipt(args) -> int:
    preparation = resolve_set(args.set)
    data = Path(args.data_root)
    state = data / preparation.state_relpath
    path = data / preparation.alias_receipt_relpath
    if not path.is_file():
        raise PreparationRunbookError("step 2c has not written %s" % path)
    output = json.loads(path.read_text(encoding="utf-8"))["output"]
    for field, expected in (
        ("schema", "saea-sealed-segment-vector-dimension-alias-v1"),
        ("row_count", preparation.rows),
        ("segment_count", preparation.rows),
        ("vector_width", preparation.vector_width),
        ("source_dimension", "content"),
        ("target_dimension", "intent-boundary"),
        ("values_unchanged", True),
        ("max_absolute_delta", 0.0),
        ("encoder_contacts", 0),
        ("tokenizer_contacts", 0),
        ("model_contacts", 0),
        ("output_relpath", preparation.segments_relpath),
    ):
        require(output, field, expected, "alias receipt")
    segments_sha256 = output["output_sha256"]
    measured = sha256_of(data / preparation.segments_relpath)
    if measured != segments_sha256:
        raise PreparationRunbookError(
            "segment export hashes to %s, not the receipt's %s" % (measured, segments_sha256)
        )
    append_state(
        state,
        (
            ("SEGMENTS_SHA256", segments_sha256),
            ("ALIAS_RECEIPT_RELPATH", preparation.alias_receipt_relpath),
            ("ALIAS_RECEIPT_SHA256", sha256_of(path)),
        ),
    )
    print("C  %s sha256 %s (%d rows, %d segments, 0 contacts)"
          % (preparation.segments_relpath, segments_sha256, preparation.rows, preparation.rows))
    return 0


def step_report(args) -> int:
    preparation = resolve_set(args.set)
    data = Path(args.data_root)
    values = read_state(data / preparation.state_relpath)
    content_sha256 = sha256_of(data / preparation.content_relpath)
    provenance_sha256 = sha256_of(data / preparation.provenance_relpath)
    provenance = json.loads(
        (data / preparation.provenance_relpath).read_text(encoding="utf-8")
    )
    for field, expected in (
        ("schema", "saea-slurp-exemplar-query-vectors-provenance-v1"),
        ("row_count", preparation.rows),
        ("sha256", content_sha256),
        ("execution_profile", "model-free-check"),
        ("parent_relpath", preparation.segments_relpath),
        ("parent_sha256", values["SEGMENTS_SHA256"]),
        ("source_dimension", "intent-boundary"),
        ("target_dimension", "content"),
        ("exposure_ledger_row", preparation.export_row),
    ):
        require(provenance, field, expected, "preparation-3 provenance")

    print()
    print("=== OUTPUTS (relative to SPEECHRL_DATA_DIR) ===")
    for relpath, digest in (
        (values["QUERIES_RELPATH"], values["QUERIES_SHA256"]),
        (values["ENCODE_RECEIPT_RELPATH"], values["ENCODE_RECEIPT_SHA256"]),
        (values["ALIAS_RECEIPT_RELPATH"], values["ALIAS_RECEIPT_SHA256"]),
        (preparation.segments_relpath, values["SEGMENTS_SHA256"]),
        (preparation.content_relpath, content_sha256),
        (preparation.provenance_relpath, provenance_sha256),
    ):
        print("  %-92s %s" % (relpath, digest))

    print()
    print("=== WHAT A CONSUMING CELL BINDS (nothing is pinned by this runbook) ===")
    print("perception query_source")
    print("  kind                     sealed-segment-vectors")
    print("  relpath                  %s" % preparation.segments_relpath)
    print("  sha256                   %s" % values["SEGMENTS_SHA256"])
    print("  tool_contact_ledger_row  %s" % preparation.run_id)
    print("solver query_source")
    print("  kind                     sealed-vectors")
    print("  relpath                  %s" % preparation.content_relpath)
    print("  sha256                   %s" % content_sha256)
    print("  tool_contact_ledger_row  %s" % preparation.export_row)
    print("preparation source receipts (root=data)")
    print("  %s  %s" % (values["ENCODE_RECEIPT_RELPATH"], values["ENCODE_RECEIPT_SHA256"]))
    print("  %s  %s" % (values["ALIAS_RECEIPT_RELPATH"], values["ALIAS_RECEIPT_SHA256"]))
    print("  %s  %s" % (preparation.provenance_relpath, provenance_sha256))
    print("roster receipt (root=repository)")
    print("  %s  %s" % (preparation.roster_relpath, args.roster_sha256 or "(re-hash at pin time)"))
    print()
    print("Zero model, encoder, tokenizer, scorer, GPU and network contacts in steps 2c and 3.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="step", required=True)

    facts = subparsers.add_parser("roster-facts")
    facts.add_argument("--repo-root", default=str(REPO_DEFAULT))
    facts.add_argument("--roster", required=True)
    facts.add_argument("--expect-sidecar-fragment", default=None)
    facts.add_argument("--expect-workers", type=int, default=None)
    facts.set_defaults(handler=step_roster_facts)

    runtime_config = subparsers.add_parser("runtime-config")
    runtime_config.add_argument("--set", required=True)
    runtime_config.add_argument("--repo-root", default=".")
    runtime_config.add_argument("--data-root", required=True)
    runtime_config.add_argument("--umbrella-lock", default=DEFAULT_UMBRELLA_LOCK)
    runtime_config.add_argument("--allow-dirty", action="store_true")
    runtime_config.set_defaults(handler=step_runtime_config)

    materialise = subparsers.add_parser("materialise")
    materialise.add_argument("--set", required=True)
    materialise.add_argument("--repo-root", required=True)
    materialise.add_argument("--data-root", required=True)
    materialise.set_defaults(handler=step_materialise)

    alias = subparsers.add_parser("alias-receipt")
    alias.add_argument("--set", required=True)
    alias.add_argument("--data-root", required=True)
    alias.set_defaults(handler=step_alias_receipt)

    report = subparsers.add_parser("report")
    report.add_argument("--set", required=True)
    report.add_argument("--data-root", required=True)
    report.add_argument("--roster-sha256", default=None)
    report.set_defaults(handler=step_report)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except PreparationRunbookError as error:
        print("REFUSED: %s" % error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
