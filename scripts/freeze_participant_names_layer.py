#!/usr/bin/env python3
"""Deterministic D1 layer-freeze generator for ConEC's participant-names
roster (2026-08-13, ``conec-names`` gate-closure incident:
``contracts.gate_evidence_identity``'s own module docstring, "Relpath layer
routing" section).

The routing fix in ``contracts.gate_evidence_identity`` teaches the gate to
verify a ``participant_names/`` evidence relpath against a NEW D1 layer key,
``e21_participant_names`` -- but that layer's own facts (count, per-sample
byte/SHA-256 manifest, ``ids_sha256``, ``manifest_sha256``) have never been
frozen: ``docs/receipts/artifacts/d1-identity.json``'s ``carriers.conec.
layers`` today holds only ``e21_contexts``/``e21_nlp_references``/
``e21_timestamps``/``e21_wer_tags``, and ``e21_contexts``'s own
``excluded_non_layer_files`` lists ``participant_names`` as OUTSIDE it
(never D1-recorded). This script builds exactly that missing layer object,
scanning ``$SPEECHRL_DATA_DIR/datasets/conec/earnings21/contexts/
participant_names/*.names.txt`` -- the SAME per-sample directory
``core.evidence._conec_names``/``conec_names_file_relpath`` already read
from at runtime (that module's own ``_CONEC_NAMES_SUBDIR_SUFFIX``/
``_CONEC_NAMES_EXTENSION`` constants, mirrored here as ``LAYER_NAME``/
``NAMES_EXTENSION`` for the same "``contracts.*``/this script stay
independent of ``core.*`` at import time" reason ``gate_evidence_identity``'s
own module docstring gives).

Digest recipe -- reproduced EXACTLY from repo code, nothing re-derived or
guessed: this script calls ``speech_aware_evidence_acquisition.data.
identity._dir_layer`` and ``.layer_report`` directly, the SAME two functions
``e0.d1_identity.build_d1`` itself calls to build every OTHER D1 layer
(including the sibling ``e21_contexts`` layer this one sits beside) --
inspecting a few of ``d1-identity.json``'s existing layer objects and their
own digests would only let you infer the recipe; calling the actual
functions removes that inference step entirely:

- ``ids_sha256``           = ``sha256("\\n".join(sorted sample ids))``
- per-file ``bytes``/``sha256`` = ``data.identity.hash_file``'s whole-file
  streaming SHA-256 (chunked reads, matches ``e0.artifacts.sha256_file``'s
  own algorithm byte for byte -- both hash the complete file, nothing
  normalizes line endings or strips whitespace)
- ``manifest``              = ``[{"id", "bytes", "sha256"}, ...]`` sorted by
  sample id
- ``manifest_sha256``       = ``sha256("\\n".join(f"{id},{bytes},{sha256}"
  for the SAME sorted (id, fact) pairs))``
- ``total_bytes``           = sum of every file's ``bytes``
- ``excluded_non_layer_files`` = every directory entry that is not a file,
  is dot-hidden, or does not end with ``.names.txt`` -- present in the
  output only when the directory actually holds any (``data.identity.
  layer_report``'s own behaviour: absent, not an empty list, when there are
  none -- matched here for schema equality with ``e21_contexts``, whose own
  entry DOES carry this key because ``participant_names``/``pdfs`` sit
  alongside it as non-``.txt`` directory entries).

Nothing here is inferred from the shape of already-frozen digests; every one
of the facts above is read straight from ``data/identity.py``'s own
docstrings/implementation (verified in this task's own notes for exactly
which lines assert each formula) -- there was no case where the recipe
could not be reproduced exactly.

Never edits ``docs/receipts/artifacts/d1-identity.json`` itself (encoding
discipline: whoever inserts this fragment into that frozen artifact performs
a separate, explicit surgical edit -- never automated here, so a mid-freeze
crash in THIS script can never leave the real receipt half-written). Prints
the ``{"e21_participant_names": {...}}`` fragment to stdout; ``--write-
fragment PATH`` additionally saves it as its own standalone JSON file.

Usage::

    python scripts/freeze_participant_names_layer.py
    python scripts/freeze_participant_names_layer.py --write-fragment /tmp/e21_participant_names.json
    python scripts/freeze_participant_names_layer.py --data-root /custom/speechrl-data
"""

from __future__ import annotations
import os

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.identity import (  # noqa: E402
    IdentityError,
    _dir_layer,
    layer_report,
)

# Mirrors core.evidence's own conec-names constants (module docstring: this
# script, like contracts.gate_evidence_identity, stays independent of
# core.* at import time, so these are this script's own explicit facts, not
# an import).
LAYER_NAME = "e21_participant_names"
NAMES_EXTENSION = ".names.txt"

DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)
# The literal per-sample directory this layer scans -- one level below
# conec's own e21_contexts layer's directory (data.identity.conec_layers'
# own "e21 / contexts" path), matching core.evidence._conec_names'
# _CONEC_NAMES_SUBDIR_SUFFIX exactly.
_PARTICIPANT_NAMES_RELDIR = Path("datasets/conec/earnings21/contexts/participant_names")


def build_participant_names_layer(participant_names_dir: Path) -> dict[str, object]:
    """Pure function: scan ``participant_names_dir`` for ``*.names.txt``
    files and return the ``{"e21_participant_names": {...}}`` fragment,
    built via the exact same ``data.identity`` machinery the sibling
    ``e21_contexts`` layer is built with (module docstring's "Digest
    recipe" section). Deterministic: calling this twice against the same
    directory contents produces byte-identical output. Raises
    ``data.identity.IdentityError`` for every condition ``_dir_layer``
    itself already refuses on (missing directory, no layer files, duplicate
    or empty sample id) -- this script never adds a second, looser
    validation path alongside it."""

    layer = _dir_layer(LAYER_NAME, participant_names_dir, (NAMES_EXTENSION,))
    return layer_report({LAYER_NAME: layer})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help=(
            "SPEECHRL_DATA_DIR root the participant-names directory is derived "
            "from as datasets/conec/earnings21/contexts/participant_names "
            "(default: $SPEECHRL_DATA_DIR or the umbrella default path); ignored "
            "when --participant-names-dir is given"
        ),
    )
    parser.add_argument(
        "--participant-names-dir",
        type=Path,
        default=None,
        help=(
            "scan this directory directly instead of deriving it from "
            "--data-root (a tmpdir fixture in tests, or a relocated corpus)"
        ),
    )
    parser.add_argument(
        "--write-fragment",
        type=Path,
        default=None,
        help=(
            "also write the layer JSON fragment to this path; the coordinator "
            "still performs the actual d1-identity.json insertion by hand -- "
            "this script never writes to that artifact"
        ),
    )
    args = parser.parse_args(argv)

    directory = args.participant_names_dir
    if directory is None:
        directory = args.data_root / _PARTICIPANT_NAMES_RELDIR

    try:
        fragment = build_participant_names_layer(directory)
    except IdentityError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    payload = json.dumps(fragment, indent=2, sort_keys=True, ensure_ascii=False)
    print(payload)

    if args.write_fragment is not None:
        args.write_fragment.parent.mkdir(parents=True, exist_ok=True)
        args.write_fragment.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {args.write_fragment}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
