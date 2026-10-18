#!/usr/bin/env python3
"""Thinking-identity window inventories for the Earnings carriers (P3.2, model-free): re-key the registered Instruct inventories to the Thinking encoder identity.

WHY. An exact-window inventory (``analysis/<run>/window-inventory.json``, kind ``exact-window-feature-inventory-v1``) binds the ENCODER IDENTITY (runtime receipt sha256, llama.cpp
build commit, decoder GGUF sha256, mmproj sha256) and, per request and per unique audio, an ``encoding_key_sha256 = digest({encoder_identity, audio_sha256})``. The window
encoder (``core.preparation_window_encoding``) refuses an inventory whose identity differs from the actual runtime, and the Thinking mmproj audio tower differs from the
Instruct one (748 of 860 tensors), so the Instruct inventories cannot drive a Thinking encode. Nothing else in an inventory depends on the model: the request keys, payload
digests and source provenance point at the SAME slice media under ``derived/obs-slices/<source run id>`` (4.3 GB for Earnings-21, 1.2 GB for Earnings-22), so NO audio is cut
again and NO byte of derived media is duplicated.

WHAT IT DOES (pure and deterministic; reads the source inventories and the Thinking runtime receipt, writes only the two small artifacts it is asked to):

* ``rekey``: the source full inventory with the Thinking identity and re-derived encoding keys (a new artifact, canonical bytes exactly as ``prepare_artifact`` publishes);
* ``smoke``: the four-window subset of the re-keyed full inventory, by the E35 subset rule of ``scripts/build_e21_native_window_unit_subset.py`` (the first N windows of the
  smoke call), under the smoke source batch name;
* ``pins``: the ``prepared_execution_units`` pin dict of each (batch, registry run, relpath, file sha256, split identity, unit count) -> ``carrier_think_window_pins_v1.json``
  beside this module;
* ``selfcheck``: re-key the source inventories with their OWN (Instruct) identity and prove the bytes reproduce the registered file sha256 -- the proof the transform is faithful;
* ``materialize``: write the two artifacts to the data root (create-only; an existing file must have the pinned sha256).

    python -B scripts/flights/carriers/carrier_think_windows.py selfcheck [--carrier e21|e22] [--data-root DIR]
    python -B scripts/flights/carriers/carrier_think_windows.py pins       [--write] [--data-root DIR]
    python -B scripts/flights/carriers/carrier_think_windows.py materialize --carrier e21 [--data-root DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))                 # scripts/ (the E35 subset builder)

import carrier_think_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
WINDOW_CARRIERS = tuple(c for c in fam.CARRIERS if fam.CARRIER_SPEC[c]["unit_kind"] == "windows")
RUNTIME_RECEIPT = "docs/receipts/runtime-q4km-thinking-preprocess-gpu.json"
KIND = "exact-window-feature-inventory-v1"
PINS_PATH = fam.WINDOW_PINS_PATH


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def data_root(arg: str | None = None) -> Path:
    value = arg or os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR")
    if not value:
        raise SystemExit("no data root: pass --data-root or set SAEA_DATA_ROOT")
    return Path(value)


def thinking_identity(repo: Path = REPO_ROOT) -> dict[str, str]:
    """The Thinking encoder identity, exactly as ``FlightRuntime.prepare_window_inventory`` builds it from the committed preprocess runtime receipt."""

    path = Path(repo) / RUNTIME_RECEIPT
    raw = path.read_bytes()
    receipt = json.loads(raw)
    if receipt.get("role") != "preprocess" or receipt.get("model_lock_key") != "qwen3-omni-30b-a3b-thinking-gguf-q4km":
        raise SystemExit(f"{RUNTIME_RECEIPT} is not the Thinking preprocess receipt")
    decoder = [g for g in receipt["gguf_files"] if "mmproj" not in Path(str(g["path"])).name.lower()]
    mmproj = [g for g in receipt["gguf_files"] if "mmproj" in Path(str(g["path"])).name.lower()]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise SystemExit("the Thinking preprocess receipt must bind exactly one decoder and one mmproj")
    return {"runtime_receipt_sha256": sha_bytes(raw), "build_commit": receipt["llama_cpp"]["build_commit"],
            "decoder_gguf_sha256": decoder[0]["sha256"], "mmproj_sha256": mmproj[0]["sha256"]}


def artifact_of(output: Mapping[str, Any]) -> tuple[dict, bytes, str]:
    """The prepared artifact exactly as ``prepare_artifact`` / the E35 builder publishes it."""

    inputs = {"encoder_identity": output["encoder_identity"], "window_sources_sha256": digest(output["batches"])}
    artifact = {"schema": "saea-prepared-artifact-v1", "kind": KIND, "contact_class": "model-free", "inputs": inputs, "output": dict(output), "output_sha256": digest(output)}
    raw = canonical_bytes(artifact)
    return artifact, raw, sha_bytes(raw)


def rekey(source: Mapping[str, Any], identity: Mapping[str, str]) -> tuple[dict, bytes, str]:
    """Re-key a prepared window inventory to ``identity``. Only the identity and the identity-dependent encoding keys change."""

    if source.get("kind") != KIND:
        raise SystemExit(f"the source artifact is {source.get('kind')!r}, not {KIND}")
    output = copy.deepcopy(source["output"])
    output["encoder_identity"] = dict(identity)
    for batch in output["batches"]:
        for request in batch["requests"]:
            request["encoding_key_sha256"] = digest({"encoder_identity": dict(identity), "audio_sha256": request["source_provenance"]["sha256"]})
    for item in output["encoding_inputs"]:
        item["encoding_key_sha256"] = digest({"encoder_identity": dict(identity), "audio_sha256": item["audio_sha256"]})
    return artifact_of(output)


def subset(source: Mapping[str, Any], *, sample_ids: list[str], per_call_limit: int | None, batch_name: str) -> tuple[dict, bytes, str]:
    """The E35 subset rule (``scripts/build_e21_native_window_unit_subset.build_subset``), on an in-memory source artifact."""

    out = source["output"]
    wanted, seen, kept = set(sample_ids), {}, []
    for row in out["batches"][0]["requests"]:
        sid = row["source_provenance"]["sample_id"]
        if sid not in wanted:
            continue
        n = seen.get(sid, 0)
        if per_call_limit is not None and n >= per_call_limit:
            continue
        kept.append(row)
        seen[sid] = n + 1
    missing = wanted - set(seen)
    if missing:
        raise SystemExit(f"sample ids not found in the source inventory: {sorted(missing)}")
    if per_call_limit is not None:
        short = {sid: n for sid, n in seen.items() if n < per_call_limit}
        if short:
            raise SystemExit(f"calls with fewer than {per_call_limit} windows: {short}")
    by_sha = {e["audio_sha256"]: e for e in out["encoding_inputs"]}
    unique: dict[str, dict[str, Any]] = {}
    for row in kept:
        sha = row["source_provenance"]["sha256"]
        ref = {"batch": batch_name, "request_key": row["request_key"]}
        if sha in unique:
            unique[sha]["requests"].append(ref)
        else:
            unique[sha] = {"audio_sha256": sha, "audio_byte_count": by_sha[sha]["audio_byte_count"], "encoding_key_sha256": row["encoding_key_sha256"], "requests": [ref]}
    output = {"schema": out["schema"], "state": out["state"], "encoder_identity": out["encoder_identity"], "request_count": len(kept), "unique_audio_count": len(unique),
              "batches": [{"name": batch_name, "requests": kept}], "encoding_inputs": [unique[k] for k in sorted(unique)]}
    return artifact_of(output)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_bytes())


def source_pins(carrier: str, repo: Path = REPO_ROOT) -> dict[str, dict]:
    """The registered Instruct ``prepared_execution_units`` pins of a carrier's full and smoke baselines."""

    out = {}
    for kind, key in (("full", "arm"), ("smoke", "smoke")):
        name = fam.CARRIER_SPEC[carrier]["source"][key]
        exp = json.loads((Path(repo) / "configs" / "experiment" / f"{name}.json").read_text(encoding="utf-8"))
        base = json.loads((Path(repo) / "configs" / "baseline" / f"{exp['cells'][0]['baseline_fragment']}.json").read_text(encoding="utf-8"))
        out[kind] = base["prepared_execution_units"]
    return out


def smoke_selection(smoke_source: Mapping[str, Any]) -> tuple[list[str], int, str]:
    """(sample ids, windows per call, batch name) of the registered smoke inventory -- the rule the smoke was registered under, read from its own bytes."""

    batch = smoke_source["output"]["batches"][0]
    counts: dict[str, int] = {}
    for row in batch["requests"]:
        sid = row["source_provenance"]["sample_id"]
        counts[sid] = counts.get(sid, 0) + 1
    return sorted(counts), max(counts.values()), batch["name"]


def compute(carrier: str, root: Path, repo: Path = REPO_ROOT) -> dict:
    """The Thinking-identity artifacts (bytes) and pins of one carrier, from the registered source inventories under the data root."""

    p = fam.packets_spec(carrier)
    src_full_path = Path(root) / p["source_inventory"]["relpath"]
    src_smoke_path = Path(root) / p["smoke_source_inventory"]["relpath"]
    for path, want in ((src_full_path, p["source_inventory"]["sha256"]), (src_smoke_path, p["smoke_source_inventory"]["sha256"])):
        if sha_bytes(path.read_bytes()) != want:
            raise SystemExit(f"{path} does not hash to the registered {want}: the source inventory changed")
    identity = thinking_identity(repo)
    full_art, full_raw, full_sha = rekey(load(src_full_path), identity)
    ids, per_call, smoke_batch = smoke_selection(load(src_smoke_path))
    smoke_art, smoke_raw, smoke_sha = subset(full_art, sample_ids=ids, per_call_limit=per_call, batch_name=smoke_batch)
    pins_src = source_pins(carrier, repo)
    full_pin = dict(pins_src["full"], relpath=fam.window_inventory_relpath(carrier, False), sha256=full_sha)
    smoke_pin = dict(pins_src["smoke"], relpath=fam.window_inventory_relpath(carrier, True), sha256=smoke_sha)
    if full_pin["unit_count"] != full_art["output"]["request_count"] or smoke_pin["unit_count"] != smoke_art["output"]["request_count"]:
        raise SystemExit(f"{carrier}: re-keyed unit counts differ from the registered pins")
    return {"identity": identity, "full": {"raw": full_raw, "pin": full_pin, "counts": counts_of(full_art)},
            "smoke": {"raw": smoke_raw, "pin": smoke_pin, "counts": counts_of(smoke_art)},
            "smoke_selection": {"sample_ids": ids, "per_call_limit": per_call, "batch": smoke_batch}}


def counts_of(artifact: Mapping[str, Any]) -> dict:
    """Requests, UNIQUE audio inputs (the encoder's contact count) and the speech seconds of the unique inputs (the audio cap)."""

    out = artifact["output"]
    first: dict[str, float] = {}
    for batch in out["batches"]:
        for row in batch["requests"]:
            prov = row["source_provenance"]
            first.setdefault(prov["sha256"], float(prov["audio_seconds"]))
    return {"requests": out["request_count"], "unique_audio": out["unique_audio_count"], "unique_audio_seconds": round(sum(first.values()), 6)}


def selfcheck(carrier: str, root: Path) -> dict:
    """Prove the transform is faithful: re-keying the registered inventories with their OWN identity reproduces their registered file sha256."""

    p = fam.packets_spec(carrier)
    full_src = load(Path(root) / p["source_inventory"]["relpath"])
    smoke_src = load(Path(root) / p["smoke_source_inventory"]["relpath"])
    own = full_src["output"]["encoder_identity"]
    _a, _r, full_sha = rekey(full_src, own)
    if full_sha != p["source_inventory"]["sha256"]:
        raise SystemExit(f"{carrier}: the full re-key with the source identity gives {full_sha}, registered {p['source_inventory']['sha256']}")
    again, _raw, _s = rekey(full_src, own)
    ids, per_call, batch = smoke_selection(smoke_src)
    _a2, _r2, smoke_sha = subset(again, sample_ids=ids, per_call_limit=per_call, batch_name=batch)
    if smoke_sha != p["smoke_source_inventory"]["sha256"]:
        raise SystemExit(f"{carrier}: the smoke subset with the source identity gives {smoke_sha}, registered {p['smoke_source_inventory']['sha256']}")
    return {"carrier": carrier, "full_sha256": full_sha, "smoke_sha256": smoke_sha, "reproduces_registered_bytes": True}


def pins_document(root: Path, repo: Path = REPO_ROOT) -> dict:
    doc: dict[str, Any] = {"schema": "saea-carrier-think-window-pins-v1", "date": fam.DATE,
                           "note": ("The Thinking-identity window inventories of the Earnings carriers: the registered Instruct inventories re-keyed to the Thinking encoder identity "
                                    "(carrier_think_windows.py). Deterministic and model-free; materialised on the data root by the P3.2 packets chain, which refuses unless the written "
                                    "bytes hash to these pins. No slice is re-cut: the requests point at the registered Instruct slices."),
                           "identity": thinking_identity(repo)}
    for carrier in WINDOW_CARRIERS:
        res = compute(carrier, root, repo)
        doc[carrier] = {"full": res["full"]["pin"], "smoke": res["smoke"]["pin"], "smoke_selection": res["smoke_selection"],
                        "counts": {"full": res["full"]["counts"], "smoke": res["smoke"]["counts"]}}
    return doc


def materialize(carrier: str, root: Path, repo: Path = REPO_ROOT, *, dry: bool = False) -> dict:
    pins = json.loads(PINS_PATH.read_text(encoding="utf-8"))[carrier]
    res = compute(carrier, root, repo)
    out = {}
    for kind in ("full", "smoke"):
        pin, raw = pins[kind], res[kind]["raw"]
        if sha_bytes(raw) != pin["sha256"]:
            raise SystemExit(f"{carrier}/{kind}: the re-derived inventory hashes to {sha_bytes(raw)}, not the pinned {pin['sha256']}")
        target = Path(root) / pin["relpath"]
        if target.exists():
            if sha_bytes(target.read_bytes()) != pin["sha256"]:
                raise SystemExit(f"{target} exists with different bytes; refusing")
            out[kind] = "already present, hash verified"
            continue
        if not dry:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + f".tmp-{os.getpid()}")
            tmp.write_bytes(raw)
            os.replace(tmp, target)
        out[kind] = "would write" if dry else "written"
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("cmd", choices=("selfcheck", "pins", "materialize"))
    p.add_argument("--carrier", choices=WINDOW_CARRIERS)
    p.add_argument("--data-root", default=None)
    p.add_argument("--write", action="store_true", help="pins: write window-pins-v1.json into the package")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    root = data_root(a.data_root)
    if a.cmd == "selfcheck":
        print(json.dumps([selfcheck(c, root) for c in ([a.carrier] if a.carrier else WINDOW_CARRIERS)], indent=2, sort_keys=True))
    elif a.cmd == "pins":
        doc = pins_document(root)
        text = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if a.write:
            PINS_PATH.write_text(text, encoding="utf-8", newline="\n")
        print(text)
    else:
        if not a.carrier:
            p.error("materialize needs --carrier")
        print(json.dumps(materialize(a.carrier, root, dry=a.dry_run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
