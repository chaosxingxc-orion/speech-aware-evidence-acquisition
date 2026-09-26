#!/usr/bin/env python3
"""Audit pinned TRAIN assets for complete-system rounds; never contact a model."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.model.speech_features import load_speech_feature_packet  # noqa: E402
from speech_aware_evidence_acquisition.core.roster import verify_roster  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding  # noqa: E402


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_pin(pin, repo, data):
    roots = {"repository": repo, "data": data}
    if pin["root"] == "absolute":
        path = Path(pin["path"])
        require(path.is_absolute(), "absolute pin must use an absolute path")
    else:
        root = roots[pin["root"]].resolve()
        path = (root / pin["path"]).resolve()
        require(path.is_relative_to(root), "pin escapes its declared root")
    require(sha(path) == pin["sha256"], f"pin mismatch: {path}")
    return path


def utterance(sample):
    parts = sample.split(":")
    require(len(parts) == 4 and parts[:2] == ["slurp", "train"], "only SLURP TRAIN sample IDs are allowed")
    return ":".join(parts[:3])


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [row["id"] for row in rows]
    require(len(ids) == len(set(ids)), "duplicate vector IDs")
    return {row["id"]: row for row in rows}


def audit(config, *, repo, data, workers):
    require(config["schema"] == "saea-slurp-system-round-assets-v1", "wrong audit schema")
    require(1 <= workers <= 20, "worker count must be between one and twenty")
    baseline = read_pin(config["knowledge_baseline"], repo, data)
    values = json.loads(baseline.read_text())
    binding = load_knowledge_store_binding(values, data_root=data)
    require(binding is not None, "no released knowledge stores")
    cohorts, populations = [], {}
    for spec in config["cohorts"]:
        roster_path = read_pin(spec["roster"], repo, data)
        roster = json.loads(roster_path.read_text())
        verify_roster(roster)
        ids = [row["sample_id"] for row in roster["items"]]
        require(len(ids) == len(set(ids)) == spec["count"], "roster count or uniqueness differs")
        require(roster["carrier_lock_key"] == "slurp" and roster["split_role"] == "discovery", "roster scope differs")
        for row in roster["items"]:
            require(row["utterance_id"] == utterance(row["sample_id"]), "utterance metadata differs")
        require(spec["name"] not in populations, "duplicate cohort name")
        populations[spec["name"]] = set(ids)
        segments = read_rows(read_pin(spec["segment_vectors"], repo, data))
        content = read_rows(read_pin(spec["content_vectors"], repo, data))
        require(set(segments) == set(content) == set(ids), "vector coverage differs from full roster")
        for sid in ids:
            row = segments[sid]
            require(len(row["segments"]) == 1, "content derivative requires one complete segment")
            segment = row["segments"][0]
            require(segment["start_frame"] == 0 and segment["end_frame"] == row["source_frames"],
                    "segment does not cover the original full utterance")
            require(set(segment["vectors"]) == {"intent-boundary"} and set(content[sid]["vectors"]) == {"content"},
                    "vector dimensions differ")
            require(content[sid]["vectors"]["content"] == segment["vectors"]["intent-boundary"],
                    "content derivative changed vector values")
        promotion_path = read_pin(spec["promotion"], repo, data)
        promotion = json.loads(promotion_path.read_text())
        require(promotion["schema"] == "saea-speech-packet-promotion-receipt-v1", "promotion schema differs")
        entries = promotion["packets"]
        require(len({e["packet_id"] for e in entries}) == len(entries) == promotion["count"],
                "promotion population is malformed")
        packets = {e["packet_id"]: e for e in entries}
        feature_root = Path(promotion["feature_root"])

        def verify_packet(sid):
            packet_id = sid.replace(":", "/")
            entry = packets[packet_id]
            packet = load_speech_feature_packet(
                feature_root, packet_id, expected_sha256=entry["packet_sha256"],
                expected_decoder_gguf_sha256=entry["decoder_gguf_sha256"])
            require(packet.audio_sha256 == entry["audio_sha256"] == segments[sid]["audio_sha256"],
                    "feature/query audio identity differs")
            require(packet.mmproj_sha256 == entry["mmproj_sha256"], "encoder identity differs")
            return packet

        with ThreadPoolExecutor(max_workers=workers) as pool:
            verified = list(pool.map(verify_packet, ids))
        tokens = [sum(c.n_tokens for c in p.chunks) for p in verified]
        cohorts.append({"name": spec["name"], "count": len(ids), "pins": spec,
                        "utterances": len({utterance(s) for s in ids}),
                        "feature_packets_verified": len(verified), "content_vectors_equal_parent": True,
                        "audio_seconds": sum(row["source_frames"] / row["source_sample_rate_hz"] for row in segments.values()),
                        "feature_tokens_total": sum(tokens), "feature_tokens_max": max(tokens),
                        "decoder_gguf_sha256s": sorted({p.decoder_gguf_sha256 for p in verified}),
                        "mmproj_sha256s": sorted({p.mmproj_sha256 for p in verified})})
    pairs = []
    names = list(populations)
    for i, name in enumerate(names):
        for other in names[i + 1:]:
            a, b = populations[name], populations[other]
            overlap = {"samples": len(a & b), "utterances": len({utterance(s) for s in a} & {utterance(s) for s in b})}
            require(not any(overlap.values()), "construction/evaluation cohorts overlap")
            pairs.append({"first": name, "second": other, **overlap})
    stores = []
    for name, store in binding.stores.items():
        snapshot = store.snapshot
        scopes = {"snapshot": set(snapshot.source_sample_ids),
                  "facets": {s for f in snapshot.facets for s in f.source_sample_ids},
                  "values": {s for v in snapshot.values for s in v.source_sample_ids}}
        overlaps = {}
        for scope, sources in scopes.items():
            overlaps[scope] = {"source_samples": len(sources), "cohorts": {}}
            for cohort, ids in populations.items():
                counts = {"samples": len(sources & ids),
                          "utterances": len({utterance(s) for s in sources} & {utterance(s) for s in ids})}
                require(not any(counts.values()), f"knowledge source overlap: {name}/{scope}/{cohort}")
                overlaps[scope]["cohorts"][cohort] = counts
        stores.append({"store": name, "values": len(snapshot.values), "facets": len(snapshot.facets),
                       "release": dict(store.release_pin), "source": dict(store.source_pin),
                       "snapshot_content_sha256": snapshot.content_hash(),
                       "snapshot_file_sha256": sha(data / store.snapshot_pin["relpath"]),
                       "source_partition_role": snapshot.source_partition_role, "overlaps": overlaps})
    return {"schema": "saea-slurp-system-round-assets-audit-v1",
            "checked_at": datetime.now(timezone.utc).isoformat(), "implementation_sha256": sha(__file__),
            "knowledge_baseline": config["knowledge_baseline"], "cohorts": cohorts,
            "pairwise": pairs, "stores": stores, "status": "verified-assets-only",
            "limits": ["No outcomes, reference labels or new DEV/test read.",
                       "Feature bytes and positions are verified with the production loader; no encoding or inference.",
                       "Promotion file pins and contained packets are verified; a final execution must independently bind its runtime and dataset view.",
                       "Source disjointness does not turn historically exposed TRAIN lists into independent holdout.",
                       "No real request capacity, complete executable cell or prospective generation authority is established."],
            "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "network": 0},
            "launch_authority": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    require(not args.output.exists(), "refuse to overwrite an audit")
    result = audit(json.loads(args.config.read_text()), repo=REPO_ROOT, data=args.data_root, workers=args.workers)
    result["config_sha256"] = sha(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        out.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "cohorts": [
        {"name": c["name"], "verified": c["feature_packets_verified"]} for c in result["cohorts"]],
        "launch_authority": False}))


if __name__ == "__main__":
    main()
