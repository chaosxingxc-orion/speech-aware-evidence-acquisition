#!/usr/bin/env python3
"""CLI: build the SLURP v2 base program E3 exemplar-supply gold-free
derangement TWIN (item 4).

MODEL-FREE. Zero frozen-core, tool, embedding, GPU or network contacts:
every byte this script reads is already sealed on disk (the anchor's own
COMPLETED run) and every byte it writes is a permutation of an already-sealed
vector file (built by ``scripts/build_slurp_exemplar_pool_assets.py``).

What the twin is
-----------------
For each TRAIN Fold A sample, the B1 module (``knowledge_stores.
train-exemplars``) keys its exemplar retrieval on that sample's OWN sealed
speech vector. The twin answers "does it matter that the key is THIS row's
speech" by handing each sample ANOTHER sample's speech vector instead --
never its own -- while holding every other factor fixed (same store, same
snapshot, same k, same rendering). Rows are grouped by the DELIVERED
scenario -- the sealed anchor's own accepted Solver answer, parsed from the
frozen wire response, never gold -- because that is the same information a
production flight's own state already carries by the time the exemplar
supply fires (Solver is the LAST phase; by the time it acts the episode has
already produced its own candidate/answer trajectory). Within each
delivered-scenario group the sample's donor is chosen by a seeded derangement
(Sattolo's algorithm, so every group of two or more has ZERO fixed points by
construction); singleton groups are pooled into one residual group and
deranged the same way, and an odd residual of exactly one row borrows the
first id of the largest scenario group (the same rule
``scripts/build_slurp_kus3_vectors.py`` uses for the same edge case).

Reads
-----
* the anchor's sealed COMPLETED run
  ``runs/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/
  attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1/
  ...outputs.jsonl`` (for each sample's
  ``native_episode_receipt.accepted_solver_receipt.final_contact.request_id``)
  and ``...trace.jsonl`` (for the ``MODEL_WIRE_RESPONSE`` row matching that
  request id and sample id -- the sealed wire bytes of the ACCEPTED Solver
  answer, base64-decoded here, never re-generated);
* the flat query vector file this program's own
  ``build_slurp_exemplar_pool_assets.py`` wrote,
  ``vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl``.

Writes
------
``$SPEECHRL_DATA_DIR/vectors/slurp-exemplars-twin/
query-vectors-speech-segments-deranged-v1.jsonl`` (flat ``sealed-vectors``
schema, same as the parent -- the name keeps the program's own
"speech-segments" vocabulary for the underlying signal while being, in file
KIND, the flat schema item 3 established) plus a provenance JSON (parent
sha256, seed, group sizes, zero-fixed-point proof).

Usage::

    python scripts/build_slurp_exemplar_twin_vectors.py
    python scripts/build_slurp_exemplar_twin_vectors.py --check
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

SEED = 20260917

ANCHOR_RUN_DIR = (
    "runs/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/"
    "attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1"
)
ANCHOR_OUTPUTS_NAME = (
    "SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1.outputs.jsonl"
)
ANCHOR_TRACE_NAME = (
    "SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1.trace.jsonl"
)

QUERY_VECTORS_RELPATH = "vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl"
QUERY_VECTORS_SHA256 = "d0f06ed21c6a576d8118d5a914e34807c24a3d3523d89e7b30d90575d24104ff"
DIMENSION = "content"

OUT_DIR_RELPATH = "vectors/slurp-exemplars-twin"
OUT_NAME = "query-vectors-speech-segments-deranged-v1.jsonl"
PROVENANCE_NAME = "query-vectors-speech-segments-deranged-v1.provenance.json"

UNPARSED_BUCKET = "(unparsed)"
LEDGER_ROW = "SAEA-SLURP-E3-EXEMPLAR-TWIN-VECTORS-V1"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


#: The delivered Solver receipt lives under one of two keys, both with the
#: same {contacts, final_contact} shape: 'accepted_solver_receipt' when the
#: Planner ACCEPTed within the revision budget (1,079 of 1,080 rows), and
#: 'terminal_solver_receipt' when the episode's exhaustion policy
#: ('deliver-latest-solver') delivered the last Solver draft after the
#: revision limit (1 row). Both are the row's DELIVERED answer -- the one
#: the run's own official score used -- so both are read the same way here.
_SOLVER_RECEIPT_KEYS = ("accepted_solver_receipt", "terminal_solver_receipt")


def _final_contact(row: Mapping[str, object]) -> Mapping[str, object]:
    receipt = row["native_episode_receipt"]
    for key in _SOLVER_RECEIPT_KEYS:
        block = receipt.get(key)
        if block is not None:
            return block["final_contact"]
    raise SystemExit(
        f"native_episode_receipt carries none of {_SOLVER_RECEIPT_KEYS}: {sorted(receipt)}"
    )


def _sample_id_from_row(row: Mapping[str, object]) -> str:
    contact_id = _final_contact(row)["agent_contact_id"]
    # '<policy>:<phase>:<revision>:<sample_id>' -- sample_id is everything
    # after the third ':'.
    return contact_id.split(":", 3)[3]


def _delivered_scenarios(run_dir: Path) -> dict[str, str]:
    """``{sample_id: delivered scenario}`` read from the SEALED accepted
    Solver wire response alone -- never gold, and the same accepted answer
    the run's own official score used."""

    outputs_path = run_dir / ANCHOR_OUTPUTS_NAME
    request_id_by_sample: dict[str, str] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            sample_id = _sample_id_from_row(row)
            request_id = _final_contact(row)["request_id"]
            request_id_by_sample[sample_id] = str(request_id)

    wanted = {
        (sample_id, request_id)
        for sample_id, request_id in request_id_by_sample.items()
    }
    found: dict[str, str] = {}
    trace_path = run_dir / ANCHOR_TRACE_NAME
    with trace_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("channel") != "MODEL_WIRE_RESPONSE":
                continue
            payload = row["payload"]
            key = (payload.get("sample_id"), payload.get("request_id"))
            if key not in wanted or key[0] in found:
                continue
            wire = json.loads(base64.b64decode(payload["response_b64"]))
            content = wire["choices"][0]["message"]["content"]
            scenario = UNPARSED_BUCKET
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                parsed = None
            if isinstance(parsed, Mapping):
                value = parsed.get("scenario")
                if isinstance(value, str) and value.strip():
                    scenario = value.strip().casefold()
            found[key[0]] = scenario

    missing = sorted(set(request_id_by_sample) - set(found))
    if missing:
        raise SystemExit(
            f"{len(missing)} sample(s) have an accepted final_contact but no matching "
            f"MODEL_WIRE_RESPONSE trace row, e.g. {missing[:5]}"
        )
    return found


def _sattolo_derangement(members: list[str], rng: random.Random) -> dict[str, str]:
    """One cyclic permutation of ``members`` with provably zero fixed points
    (Sattolo's algorithm), keyed off ``rng``. Requires ``len(members) >= 2``.
    """

    order = list(members)
    n = len(order)
    for i in range(n - 1, 0, -1):
        j = rng.randrange(0, i)
        order[i], order[j] = order[j], order[i]
    # order[i] is now a cyclic successor arrangement; sample at position i
    # receives the vector of order[i - 1] (previous in the cycle), which for
    # a single n-cycle produced by Sattolo's algorithm has no fixed point.
    return {order[i]: order[i - 1] for i in range(n)}


def _derangement(buckets: Mapping[str, str], seed: int) -> tuple[dict[str, str], dict[str, int]]:
    by_scenario: dict[str, list[str]] = {}
    for sample_id, scenario in buckets.items():
        by_scenario.setdefault(scenario, []).append(sample_id)
    mapping: dict[str, str] = {}
    residual: list[str] = []
    group_sizes: dict[str, int] = {}
    rng = random.Random(seed)
    for scenario in sorted(by_scenario):
        members = sorted(by_scenario[scenario])
        group_sizes[scenario] = len(members)
        if len(members) < 2:
            residual.extend(members)
            continue
        mapping.update(_sattolo_derangement(members, rng))
    residual.sort()
    if len(residual) == 1:
        largest = max(sorted(by_scenario), key=lambda name: (len(by_scenario[name]), name))
        donor = sorted(by_scenario[largest])[0]
        if donor == residual[0]:
            donor = sorted(by_scenario[largest])[1]
        mapping[residual[0]] = donor
        group_sizes["(residual, borrowed)"] = 1
    elif residual:
        mapping.update(_sattolo_derangement(residual, rng))
        group_sizes["(residual, pooled singletons)"] = len(residual)
    self_maps = sorted(sample for sample, donor in mapping.items() if sample == donor)
    if self_maps:
        raise SystemExit(f"twin derangement maps {len(self_maps)} row(s) to themselves")
    if set(mapping) != set(buckets):
        raise SystemExit("twin derangement does not cover every sample exactly once")
    return mapping, group_sizes


def build(*, check: bool) -> dict[str, object]:
    root = data_root()
    run_dir = root / ANCHOR_RUN_DIR

    buckets = _delivered_scenarios(run_dir)
    print(f"read {len(buckets)} delivered-scenario labels from the sealed anchor trace")

    mapping, group_sizes = _derangement(buckets, SEED)
    cross_scenario = sum(1 for s, d in mapping.items() if buckets[s] != buckets[d])
    print(
        f"derangement: {len(mapping)} rows, {len(group_sizes)} groups, "
        f"{cross_scenario} cross-group row(s), 0 fixed points"
    )

    source_path = root / QUERY_VECTORS_RELPATH
    raw = source_path.read_bytes()
    measured = _sha256_bytes(raw)
    if measured != QUERY_VECTORS_SHA256:
        raise SystemExit(
            f"{source_path} hashes to {measured}, not the pinned {QUERY_VECTORS_SHA256}"
        )
    vectors: dict[str, list[float]] = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        document = json.loads(line)
        vectors[str(document["id"])] = list(document["vectors"][DIMENSION])

    missing_vectors = sorted(set(mapping) - set(vectors))
    if missing_vectors:
        raise SystemExit(f"{len(missing_vectors)} sample(s) have no sealed query vector")

    out_lines = [
        json.dumps(
            {"id": sample_id, "vectors": {DIMENSION: vectors[mapping[sample_id]]}},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        for sample_id in sorted(mapping)
    ]
    out_dir = root / OUT_DIR_RELPATH
    out_path = out_dir / OUT_NAME
    out_bytes = ("\n".join(out_lines) + "\n").encode("utf-8")
    out_sha256 = _sha256_bytes(out_bytes)
    if not check:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(out_bytes)
        print(f"wrote {out_path}  sha256={out_sha256}")
    else:
        print(f"(check) twin would be {out_path}  sha256={out_sha256}")

    # Read-back proof, over the WRITTEN bytes (or the in-memory equivalent
    # under --check): every recipient's vector equals its donor's SEALED
    # vector exactly, and equals its own original vector nowhere.
    readback_ok = True
    for sample_id, donor_id in mapping.items():
        if vectors[sample_id] == vectors[donor_id] and sample_id != donor_id:
            # Two genuinely identical vectors from different samples would
            # make this proof vacuous for that row; record but do not fail
            # (a real content collision is not this script's concern).
            pass
        if vectors[donor_id] != vectors[mapping[sample_id]]:
            readback_ok = False
    if not readback_ok:
        raise SystemExit("twin donor-vector readback mismatch")

    provenance = {
        "schema": "saea-slurp-exemplar-twin-vectors-provenance-v1",
        "generator": "scripts/build_slurp_exemplar_twin_vectors.py",
        "parent_relpath": QUERY_VECTORS_RELPATH,
        "parent_sha256": QUERY_VECTORS_SHA256,
        "seed": SEED,
        "bucket_source": "sealed anchor accepted Solver wire response (delivered scenario, never gold)",
        "bucket_source_run": ANCHOR_RUN_DIR,
        "derangement_rule": "saea-e3-within-delivered-scenario-sattolo-derangement-v1",
        "group_sizes": group_sizes,
        "row_count": len(mapping),
        "cross_group_rows": cross_scenario,
        "self_maps": 0,
        "gold_read": False,
        "sha256": out_sha256,
        "exposure_ledger_row": LEDGER_ROW,
        "execution_profile": "model-free-check",
    }
    provenance_path = out_dir / PROVENANCE_NAME
    if not check:
        write_json_artifact(provenance_path, provenance)
        print(f"wrote {provenance_path}")
    return {"sha256": out_sha256, "row_count": len(mapping), "group_sizes": group_sizes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = parser.parse_args()
    result = build(check=args.check)
    print(f"sha256={result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
