"""Mint a cell's first-phase supply model-free on the tree under test and compare
its OUTPUT with the cell's registered pin. Zero sockets: every INET connect in
this process is refused."""
import argparse
import json
import os
import socket
import time
from pathlib import Path

REPO = Path(os.environ["WT"])
DATA = Path(os.environ["SPEECHRL_DATA_DIR"])
LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")


def forbid_sockets():
    original = socket.socket.connect

    def refuse(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(f"network contact refused: {address}")
        return original(self, address)

    socket.socket.connect = refuse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    forbid_sockets()
    import speech_aware_evidence_acquisition as pkg

    assert pkg.__file__.startswith(str(REPO)), pkg.__file__
    import dataclasses

    from speech_aware_evidence_acquisition.core.flight import runtime as rt
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

    # Exactly as the slot-fill bench mints (item E16): the committed pin binds
    # the implementation files of its own flip commit, so this tree composes
    # WITHOUT it and mints its own first-phase supply from the sealed vectors.
    original_compose = rt.compose

    def compose_without_pin(*a, **k):
        composed = original_compose(*a, **k)
        values = {key: v for key, v in composed.values.items() if key != "prepared_phase_supply"}
        return dataclasses.replace(composed, values=values)

    rt.compose = compose_without_pin

    fragment = json.loads((REPO / "configs" / "experiment" / f"{args.experiment}.json").read_text(encoding="utf-8"))
    cell = fragment["cells"][0]
    baseline = json.loads((REPO / "configs" / "baseline" / f"{cell['baseline_fragment']}.json").read_text(encoding="utf-8"))
    pin = baseline["prepared_phase_supply"]
    pinned = json.loads((DATA / pin["relpath"]).read_text(encoding="utf-8"))
    runtime = build_flight_runtime(
        REPO, DATA, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=args.experiment,
        run_id=cell["run_id"], attempt_id=cell["attempt_id"],
        runtime_root=Path("/tmp/fastrecall-runtime"), lock_path=LOCK, campaign_active=False,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    t = time.perf_counter()
    receipt = runtime.prepare_phase_supply(out, max_workers=args.workers)
    seconds = time.perf_counter() - t
    minted = json.loads(out.read_text(encoding="utf-8"))
    result = {
        "experiment": args.experiment,
        "pinned_relpath": pin["relpath"],
        "pinned_artifact_sha256": pin["sha256"],
        "pinned_output_sha256": pinned["output_sha256"],
        "minted_artifact_sha256": receipt.get("sha256"),
        "minted_output_sha256": minted["output_sha256"],
        "output_sha256_equal": minted["output_sha256"] == pinned["output_sha256"],
        "output_block_equal": minted["output"] == pinned["output"],
        "rows": len(minted["output"].get("values", {})) if isinstance(minted["output"], dict) else None,
        "mint_seconds": round(seconds, 1),
    }
    print(json.dumps(result, indent=1))
    Path(str(out) + ".compare.json").write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
