#!/usr/bin/env python3
"""P3.2 Earnings window packets on the Thinking core: the model-free halves of one pass (the GPU encode between them is the shell wrapper's).

One pass = one Thinking-identity inventory (``smoke``: the four-window subset; ``full``: the whole roster) driven through the library's four prepared artifacts, in this order:

  1. ``preflight``   (model-free, before the swap window opens): the inventory on the data root hashes to its pin, the encode experiment and its encoder fragment compose, the runtime
                     receipt is the Thinking preprocess receipt and its GGUF pins equal the lock, the exposure row is countersigned, nothing a pass must not find exists yet;
  2. (shell)         start the Thinking GPU encoder session under the pass's session id, hold the root lease (``lease_cli --stage prepare-window-features``), run
                     ``core.flight.cli prepare-window-features`` -> ``analysis/<run>/window-encoding.json``, release the lease, stop the session normally;
  3. ``post``        (model-free): ``window-feature-cache-audit.json`` (``prepare_feature_cache_audit_from_inventory_artifact``), ``window-feature-preparation-provenance.json``
                     (``prepare_window_feature_provenance``: the runtime receipt, the session receipt, the NORMAL stop receipt, the encoding record, the audit) and
                     ``window-feature-packets.json`` (``prepare_window_feature_packets``: the formal packets promoted into the shared Thinking packet root);
  4. ``verify``      (model-free): the packets artifact loads through ``load_prepared_window_feature_packets`` against its recorded sources and prints its file sha256 -- the pin
                     ``carrier_think_derive_cells.py --require-receipts`` writes into the baseline.

    carrier_think_windows_stage.py preflight --carrier e21 --pass smoke
    carrier_think_windows_stage.py post      --carrier e21 --pass smoke
    carrier_think_windows_stage.py verify    --carrier e21 --pass full

Every artifact is create-only through the library's ``prepare_artifact`` (a warm artifact is verified, never rewritten). The 4 smoke windows are re-encoded in the full pass into its own
cache; their packets are promoted a second time and accepted only when the chunks are identical (harness item E40); a conflicting packet id is never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import carrier_think_family as fam  # noqa: E402
import carrier_think_packets_write_registration as pw  # noqa: E402
import carrier_think_windows as win  # noqa: E402

REPO = fam.REPO_ROOT
RUNTIME_RECEIPT = "docs/receipts/runtime-q4km-thinking-preprocess-gpu.json"
PACKET_ROOT = Path(fam.THINK_PACKET_ROOT)
PASSES = ("smoke", "full")


def data_root() -> Path:
    value = os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR")
    if not value:
        raise SystemExit("no data root: set SAEA_DATA_ROOT or SPEECHRL_DATA_DIR")
    return Path(value)


def sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def spec_of(carrier: str, which: str) -> dict:
    key = f"{carrier}-encode" + ("-smoke" if which == "smoke" else "")
    for s in pw.pass_specs():
        if s["key"] == key:
            return s
    raise SystemExit(f"no pass {key}")


def experiment_cell(spec: Mapping[str, Any], repo: Path = REPO) -> dict:
    doc = json.loads((Path(repo) / "configs" / "experiment" / f"{spec['experiment']}.json").read_text(encoding="utf-8"))
    return doc["cells"][0] | {"service_session_id": doc["service_session_id"], "experiment_id": doc["experiment_id"]}


def paths_of(spec: Mapping[str, Any], root: Path) -> dict[str, Path]:
    base = Path(root) / "analysis" / spec["run"]
    return {"encoding": base / "window-encoding.json", "audit": base / "window-feature-cache-audit.json",
            "provenance": base / "window-feature-preparation-provenance.json", "packets": base / "window-feature-packets.json"}


def ledger_problems(spec: Mapping[str, Any], repo: Path) -> list[str]:
    from speech_aware_evidence_acquisition.contracts.ledger import _parse_ledger_tables

    rows = [r for r in _parse_ledger_tables((Path(repo) / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")) if r.get("run/experiment id") == spec["run"]]
    if len(rows) != 1:
        return [f"{len(rows)} exposure rows for {spec['run']}, need exactly one"]
    row, problems = rows[0], []
    text = " ".join(str(v) for v in row.values())
    if "DRAFT" in text or "REGISTERED BEFORE CONTACT" not in text:
        problems.append(f"exposure row {spec['run']} is not root-countersigned")
    if str(row.get("consumed", "")).strip().lower() != "no":
        problems.append("row is consumed; a sealed preparation is never re-run")
    try:
        got = (int(row["calls"]), int(row["speech audio seconds"]), float(row["gpu hours"]))
    except (KeyError, ValueError):
        got = None
    want = (spec["contacts"], spec["audio"], float(spec["gpu"]))
    if got != want:
        problems.append(f"budgets (calls, speech audio seconds, gpu hours) {got!r}, registered {want!r}")
    return problems


def preflight(carrier: str, which: str, repo: Path = REPO, *, tolerate_unmaterialized: bool = False) -> dict:
    from speech_aware_evidence_acquisition.core.config import compose

    root = data_root()
    spec = spec_of(carrier, which)
    pins = spec["pins"]
    problems: list[str] = []
    inv = root / pins["relpath"]
    if not inv.is_file() and tolerate_unmaterialized:
        pass                       # the --check before the first window: the run materialises the inventories itself, before the card is touched
    elif not inv.is_file():
        problems.append(f"the Thinking-identity inventory {pins['relpath']} is absent (carrier_think_windows.py materialize --carrier {carrier})")
    elif sha_file(inv) != pins["sha256"]:
        problems.append(f"{pins['relpath']} does not hash to its pin {pins['sha256']}")
    cell = experiment_cell(spec, repo)
    try:
        composed = compose(Path(repo), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["experiment"])
        if composed.values["window_feature_preparation"]["inventory_sha256"] != pins["sha256"]:
            problems.append("the experiment pins a different inventory")
    except Exception as error:  # noqa: BLE001 -- reported by name
        composed = None
        problems.append(f"the encode experiment does not compose: {error}")
    receipt = json.loads((Path(repo) / RUNTIME_RECEIPT).read_text(encoding="utf-8"))
    if receipt.get("role") != "preprocess" or receipt.get("model_lock_key") != "qwen3-omni-30b-a3b-thinking-gguf-q4km":
        problems.append("the runtime receipt is not the Thinking preprocess receipt")
    problems += ledger_problems(spec, repo)
    cache = Path(spec["cache_dir"])
    if cache.is_dir() and any(cache.iterdir()):
        problems.append(f"the legacy cache {cache} already holds entries; a window pass starts from an EMPTY cache (unproven entries refuse before the first contact)")
    out = paths_of(spec, root)
    existing = [k for k, p in out.items() if p.exists()]
    if existing:
        problems.append(f"artifacts already exist for {spec['run']}: {existing}")
    session = cell["service_session_id"]
    if (root / "serving" / session / "session.json").exists():
        problems.append(f"a session record for {session} already exists")
    return {"carrier": carrier, "pass": which, "run_id": spec["run"], "attempt_id": cell["attempt_id"], "session_id": session, "experiment": spec["experiment"],
            "cell": cell["cell_id"], "model_fragment": spec["model"], "cache_dir": spec["cache_dir"], "inventory": pins["relpath"], "contacts": spec["contacts"],
            "config_hash": composed.config_hash if composed else None, "problems": problems, "ok": not problems}


def post(carrier: str, which: str, repo: Path = REPO) -> dict:
    from speech_aware_evidence_acquisition.core.preparation_feature_cache import prepare_feature_cache_audit_from_inventory_artifact
    from speech_aware_evidence_acquisition.core.preparation_feature_provenance import prepare_window_feature_provenance
    from speech_aware_evidence_acquisition.core.preparation_window_packets import prepare_window_feature_packets
    from speech_aware_evidence_acquisition.core.preparation_windows import WindowFeatureEncoderIdentity

    root = data_root()
    spec = spec_of(carrier, which)
    pins, cell = spec["pins"], experiment_cell(spec, repo)
    p = paths_of(spec, root)
    if not p["encoding"].is_file():
        raise SystemExit(f"no encoding artifact {p['encoding']}: the encode step has not run")
    inventory_path = root / pins["relpath"]
    identity = WindowFeatureEncoderIdentity(**win.thinking_identity(repo))
    audit = prepare_feature_cache_audit_from_inventory_artifact(
        p["audit"], inventory_path=inventory_path, inventory_sha256=pins["sha256"], data_root=root, encoder_identity=identity, legacy_cache_dir=Path(spec["cache_dir"]),
        expected_n_embd=2048)
    session_dir = root / "serving" / cell["service_session_id"]
    prov = prepare_window_feature_provenance(
        p["provenance"], runtime_receipt_path=Path(repo) / RUNTIME_RECEIPT, session_receipt_path=session_dir / "session.json", stop_receipt_path=session_dir / "session-stop.json",
        encoding_record_path=p["encoding"], cache_audit_path=p["audit"], expected_run_id=spec["run"], expected_attempt_id=cell["attempt_id"],
        expected_session_id=cell["service_session_id"])
    packets = prepare_window_feature_packets(
        p["packets"], inventory_path=inventory_path, inventory_sha256=pins["sha256"], cache_audit_path=p["audit"], cache_audit_sha256=sha_file(p["audit"]),
        provenance_path=p["provenance"], provenance_sha256=sha_file(p["provenance"]), data_root=root, feature_root=PACKET_ROOT, workers=8)
    return {"audit": {"path": str(p["audit"]), "sha256": sha_file(p["audit"]), "result": str(audit.get("cache", "written"))},
            "provenance": {"path": str(p["provenance"]), "sha256": sha_file(p["provenance"]), "result": str(prov.get("cache", "written"))},
            "packets": {"path": str(p["packets"]), "sha256": sha_file(p["packets"]), "result": str(packets.get("cache", "written"))}}


def verify(carrier: str, which: str, repo: Path = REPO) -> dict:
    from speech_aware_evidence_acquisition.core.preparation_window_packets import load_prepared_window_feature_packets

    root = data_root()
    spec = spec_of(carrier, which)
    path = paths_of(spec, root)["packets"]
    sha = sha_file(path)
    prepared = load_prepared_window_feature_packets(path, sha, root)
    if Path(prepared.feature_root).resolve() != PACKET_ROOT.resolve():
        raise SystemExit("the packets artifact names a different feature root")
    if prepared.request_count != spec["pins"]["unit_count"]:
        raise SystemExit(f"the packets artifact covers {prepared.request_count} requests, the pinned inventory has {spec['pins']['unit_count']}")
    return {"carrier": carrier, "pass": which, "artifact": str(path), "sha256": sha, "requests": prepared.request_count, "unique_packets": prepared.unique_packet_count}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("cmd", choices=("preflight", "post", "verify"))
    ap.add_argument("--carrier", required=True, choices=win.WINDOW_CARRIERS)
    ap.add_argument("--pass", dest="which", required=True, choices=PASSES)
    ap.add_argument("--tolerate-unmaterialized", action="store_true", help="preflight: do not require the inventory to be on the data root yet (--check before the first window)")
    a = ap.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if a.cmd == "preflight":
        result = preflight(a.carrier, a.which, tolerate_unmaterialized=a.tolerate_unmaterialized)
    else:
        result = {"post": post, "verify": verify}[a.cmd](a.carrier, a.which)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
