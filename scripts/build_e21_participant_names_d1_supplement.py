#!/usr/bin/env python3
"""Build the additive D1 EVIDENCE-layer supplement for ConEC's participant-names
roster (``e21_participant_names``), the hard gate KC-E1 cannot fly without.

Why a supplement and not an edit
--------------------------------
``docs/receipts/artifacts/d1-identity.json`` is the immutable E0 D1 artifact. It
records four ConEC layers -- ``e21_contexts``, ``e21_nlp_references``,
``e21_timestamps``, ``e21_wer_tags`` -- and ``e21_contexts``'s own
``excluded_non_layer_files`` lists ``participant_names`` as OUTSIDE it. Meanwhile
``contracts.gate_evidence_identity._route_evidence_layer_key`` has always been
able to NAME the missing layer and never able to RESOLVE it, so every run whose
evidence source reads a call's participant roster (``core.evidence._conec_names``,
and through it ``conec-class-lists``) fails closed at the evidence-identity rail.
This script closes that by writing an ADDITIVE successor document
(``contracts.gate_evidence_identity.EVIDENCE_SUPPLEMENT_SCHEMA``,
``saea-d1-evidence-supplement-v1``) rather than by rewriting a frozen artifact.

Digest recipe -- called, never re-derived
-----------------------------------------
The layer's own facts come from
``scripts.freeze_participant_names_layer.build_participant_names_layer``, which
calls ``data.identity._dir_layer`` and ``.layer_report`` -- the SAME two functions
``e0.d1_identity.build_d1`` calls to build every other D1 layer, including the
sibling ``e21_contexts`` layer this one sits beside. So ``ids_sha256``,
``manifest``, ``manifest_sha256``, ``total_bytes`` and
``excluded_non_layer_files`` are produced by the production code path, and the
gate recomputes both digests from the manifest it reads
(``gate_evidence_identity._layer_ids_sha256`` / ``_layer_manifest_sha256``)
rather than trusting the claim.

Bindings the gate re-checks
---------------------------
* ``parent_d1_sha256`` -- the live SHA-256 of ``docs/receipts/artifacts/d1-identity.json``.
  A supplement built against a different D1 is refused.
* ``source_binding_sha256`` -- the base D1 ``conec.layers.e21_contexts.ids_sha256``,
  i.e. the carrier's already-frozen 44-sample universe. The supplement's own
  ``ids_sha256`` must equal it, so this layer can never quietly widen the split.
* ``d1_layer_key`` -- exactly one layer per supplement, and it may not be one the
  base D1 already carries (a supplement ADDS, never shadows).

Zero contacts of every kind: a directory scan, a byte hasher and a JSON writer.
Only ConEC CONTEXT bytes are opened (the participant rosters, classified
``runtime-legal-input`` by
``docs/readiness/2026-09-03-information-audit-earnings21-conec.md``); no reference
transcript, timestamp file, ``wer_tags`` sidecar or bias list is read, and no
transcript or roster CONTENT is written to the output -- sample ids, byte sizes
and digests only.

Usage::

    python scripts/build_e21_participant_names_d1_supplement.py
    python scripts/build_e21_participant_names_d1_supplement.py --data-root /custom/speechrl-data
    python scripts/build_e21_participant_names_d1_supplement.py --output /tmp/supplement.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from freeze_participant_names_layer import (  # noqa: E402
    LAYER_NAME,
    build_participant_names_layer,
)
from speech_aware_evidence_acquisition.data.identity import IdentityError  # noqa: E402

STUDY_SLUG = "speech-aware-evidence-acquisition"
SUPPLEMENT_SCHEMA = "saea-d1-evidence-supplement-v1"
CARRIER_LOCK_KEY = "conec"
#: The carrier's own default evidence layer -- the frozen sample universe the
#: supplement must cover exactly (module docstring, "Bindings the gate
#: re-checks"). Mirrors ``data.carriers``' EARNINGS21 descriptor's
#: ``EvidenceLayout.d1_layer_key``; stated here rather than imported for the
#: same import-time independence ``freeze_participant_names_layer`` documents.
DEFAULT_EVIDENCE_LAYER_KEY = "e21_contexts"

DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)
_PARTICIPANT_NAMES_RELDIR = Path("datasets/conec/earnings21/contexts/participant_names")
DEFAULT_PARENT_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-identity.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs/receipts/artifacts/d1-e21-participant-names.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return document


def base_carrier_facts(parent: Mapping[str, Any]) -> tuple[str, frozenset[str]]:
    """The base D1's own ``conec`` sample universe: the default evidence layer's
    ``ids_sha256`` (the supplement's ``source_binding_sha256``) and the set of
    layer keys it already carries (nothing here may shadow one)."""

    carriers = parent.get("carriers")
    carrier = carriers.get(CARRIER_LOCK_KEY) if isinstance(carriers, Mapping) else None
    layers = carrier.get("layers") if isinstance(carrier, Mapping) else None
    if not isinstance(layers, Mapping) or not layers:
        raise ValueError(f"parent D1 has no {CARRIER_LOCK_KEY!r} layers")
    default_layer = layers.get(DEFAULT_EVIDENCE_LAYER_KEY)
    universe = default_layer.get("ids_sha256") if isinstance(default_layer, Mapping) else None
    if not isinstance(universe, str) or len(universe) != 64:
        raise ValueError(
            f"parent D1 {CARRIER_LOCK_KEY}.layers.{DEFAULT_EVIDENCE_LAYER_KEY} has no "
            "usable ids_sha256"
        )
    return universe, frozenset(layers)


def build_supplement(
    *, participant_names_dir: Path, parent_d1_path: Path
) -> dict[str, object]:
    """The complete ``saea-d1-evidence-supplement-v1`` document.

    Deterministic: the same directory contents and the same parent D1 always
    produce byte-identical output. Fails closed on every condition ``_dir_layer``
    already refuses (missing directory, no layer files, duplicate or empty sample
    id) plus the three bindings of the module docstring.
    """

    parent = _load_object(parent_d1_path, "parent D1 identity artifact")
    universe, base_layer_keys = base_carrier_facts(parent)
    if LAYER_NAME in base_layer_keys:
        raise ValueError(
            f"parent D1 already records layer {LAYER_NAME!r}; a supplement may only ADD "
            "a layer, never shadow one"
        )

    fragment = build_participant_names_layer(participant_names_dir)
    layer = fragment[LAYER_NAME]
    ids_sha256 = layer["ids_sha256"]
    if ids_sha256 != universe:
        raise ValueError(
            f"the {LAYER_NAME!r} layer covers a different sample set than the carrier's "
            f"own {DEFAULT_EVIDENCE_LAYER_KEY!r} layer ({ids_sha256} vs {universe}); a "
            "supplement may not widen or narrow the frozen sample universe"
        )
    return {
        "schema": SUPPLEMENT_SCHEMA,
        "study": STUDY_SLUG,
        "carrier_lock_key": CARRIER_LOCK_KEY,
        "d1_layer_key": LAYER_NAME,
        "parent_d1_sha256": sha256_file(parent_d1_path),
        "source_binding_sha256": universe,
        "count": layer["count"],
        "ids_sha256": ids_sha256,
        "manifest": layer["manifest"],
        "manifest_sha256": layer["manifest_sha256"],
        "total_bytes": layer["total_bytes"],
        "excluded_non_layer_files": list(layer.get("excluded_non_layer_files", ())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--participant-names-dir",
        type=Path,
        default=None,
        help="scan this directory instead of deriving it from --data-root",
    )
    parser.add_argument("--parent-d1", type=Path, default=DEFAULT_PARENT_D1)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    directory = args.participant_names_dir
    if directory is None:
        directory = args.data_root / _PARTICIPANT_NAMES_RELDIR

    try:
        document = build_supplement(
            participant_names_dir=directory, parent_d1_path=args.parent_d1
        )
    except (IdentityError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "d1_layer_key": document["d1_layer_key"],
                "count": document["count"],
                "ids_sha256": document["ids_sha256"],
                "manifest_sha256": document["manifest_sha256"],
                "total_bytes": document["total_bytes"],
                "parent_d1_sha256": document["parent_d1_sha256"],
                "source_binding_sha256": document["source_binding_sha256"],
                "excluded_non_layer_files": document["excluded_non_layer_files"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
