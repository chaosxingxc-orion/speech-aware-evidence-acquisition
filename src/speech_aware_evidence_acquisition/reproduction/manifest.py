"""Probe-protocol manifest (P0.C): frozen prompt templates + probe specs.

``PROBES`` is the declarative record of each sampled reproduction probe
(plan R1–R5): its arms, which template files each arm uses, the scorer that
reads its outputs, and the pre-registered sampling design. ``build_manifest``
hashes every referenced template byte-exactly; an ExecutionPlan's protocol
hash binds to the SHA-256 of the generated ``manifest.json`` blob. Editing a
template after its probe has run is forbidden — add a new file and a new
probe entry instead.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROBE_MANIFEST_VERSION = "probe-manifest-v1"

_SEED = 20260807

PROBES: dict[str, dict] = {
    "R1-audio2tool-direct": {
        "arms": {"direct": ["r1_audio2tool_direct.txt"]},
        "scorer": "a2t-scorer-v1 (toolcall_scoring)",
        "sampling": {"seed": _SEED, "design": "50 per tier x 8 tiers = 400 items"},
        "sample_receipt": "r1-audio2tool-sample.json",
        "success": "tier rank order preserved; per-tier |delta| <= 5pp vs published Qwen-3-Omni-30B row",
        "profile": "baseline-reproduction",
    },
    "R2-bba-cascade-vs-direct": {
        "arms": {
            "direct": ["r2_bba_direct.txt"],
            "self_cascade": ["shared_transcribe.txt", "r2_bba_cascade_answer.txt"],
        },
        "scorer": "deterministic: normalized match of text after final 'Answer:' vs official_answer",
        "sampling": {"seed": _SEED, "design": "50 x 4 BBH categories = 200 items, paired arms"},
        "sample_receipt": "r2-bba-sample.json",
        "success": "cascade > direct, paired-significant (McNemar)",
        "profile": "bounded-discovery-probe",
    },
    "R3-airbench-slurp-ic": {
        "arms": {
            "direct": ["r3_airbench_ic_direct.txt"],
            "self_cascade": ["shared_transcribe.txt", "r3_airbench_ic_cascade_answer.txt"],
        },
        "scorer": "deterministic: choice-letter match against gold choice",
        "sampling": {"seed": _SEED, "design": "200 of the AIR-Bench 1k SLURP-IC items, paired arms"},
        "success": "cascade > direct; absolute rows recorded to baseline wiki",
        "profile": "bounded-discovery-probe",
        "status": "BLOCKED: AIR-Bench data not on disk; acquisition needs the umbrella lock path",
    },
    "R4-context-dose": {
        "arms": {
            "no_context": ["r4_transcribe_nocontext.txt"],
            "matched_context": ["r4_transcribe_with_context.txt"],
            "mismatched_context": ["r4_transcribe_with_context.txt"],
        },
        "runtime_binding": (
            "2026-08-08 Route-1 retarget: under the R0 core driver the arm instructions are the "
            "task_instruction fields of configs/baseline/{bare-core,fixed-legal-context,"
            "mismatched-evidence}.json (bound into protocol_hash via config_hash); the r4_*.txt "
            "templates above are the design-time reference, not runtime-wired. The mismatched arm's "
            "instruction was equalized to the matched arm's on 2026-08-08 (a design-leak fix: the "
            "negative-control explanation must never reach the model)."
        ),
        "scorer": "frozen scoring stack (asr-wer + cost); per-entity-class WER deferred until an owner-pinned wer_tags adapter exists",
        "sampling": {
            "seed": _SEED,
            "design": "Route 1 (2026-08-08): frozen earnings21-discovery split, 44 samples per arm — e22 dev subset10 has no registered ConEC evidence layer (per-call PDFs, not per-sample txt); e22 evidence layer remains an owner-level decision",
        },
        "success": "WER monotone in evidence quality (Siskos direction): matched < no-context and matched < mismatched",
        "profile": "bounded-discovery-probe",
        "note": "matched arm uses the call's own ConEC contexts layer; mismatched arm uses the deterministic rotation derangement; oracle/gold evidence hard-raises on the runtime path",
    },
    "R5-vab-oneshot": {
        "arms": {
            "zero_shot": ["r5_vab_zeroshot.txt"],
            "one_shot": ["r5_vab_oneshot.txt"],
        },
        "scorer": "a2t-scorer-v1 components (tool selection / structure); semantic PF only via pinned local judge if unavoidable",
        "sampling": {"seed": _SEED, "design": "50 per EN complex stratum (parallel/seqdep/multi-turn); strata under 50 taken whole = 140 items, paired arms"},
        "sample_receipt": "r5-vab-sample.json",
        "success": "one-shot > zero-shot; magnitude compared to published +10-17pp",
        "profile": "bounded-discovery-probe",
    },
}

SAMPLING_POLICY = (
    "Each carrier is sampled exactly once, by scripts/build_probe_samples.py "
    "(seeded, order-independent, metadata-only); the receipt under "
    "docs/receipts/probe-samples/ is frozen and every later experiment on that "
    "carrier resolves its items through the binding in this manifest — never "
    "through a fresh draw. Adding a carrier means adding a new receipt through "
    "the same script and regenerating this manifest; changing an existing "
    "receipt requires owner approval and a new probe entry. R4 draws from the "
    "already-frozen dev subset10 split receipt (docs/receipts/splits.json); "
    "R3 has no sample yet (data acquisition blocked)."
)

DECODE_DISCIPLINE = {
    "temperature": 0,
    "note": "greedy decoding for all scoring arms; sampling-based arms (R7 n-best) get their own entry when designed",
}


def _load_verified_receipt(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"sample receipt missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    from .sampling import split_identity_hash

    recomputed = split_identity_hash([item["key"] for item in payload["items"]])
    if recomputed != payload["split_identity_hash"]:
        raise ValueError(
            f"split_identity_hash mismatch in {path.name}: receipt says "
            f"{payload['split_identity_hash'][:16]}…, items hash to {recomputed[:16]}…"
        )
    return payload


def build_manifest(templates_dir: Path, receipts_dir: Path) -> dict:
    referenced = sorted(
        {
            template
            for probe in PROBES.values()
            for templates in probe["arms"].values()
            for template in templates
        }
    )
    hashes: dict[str, dict[str, str]] = {}
    for name in referenced:
        path = templates_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"referenced template missing: {path}")
        hashes[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    samples: dict[str, dict] = {}
    for probe_name, probe in PROBES.items():
        receipt_name = probe.get("sample_receipt")
        if receipt_name is None:
            continue
        payload = _load_verified_receipt(receipts_dir / receipt_name)
        samples[probe_name] = {
            "receipt": receipt_name,
            "split_identity_hash": payload["split_identity_hash"],
            "n_items": len(payload["items"]),
            "seed": payload["seed"],
            "split_role": payload["split_role"],
        }

    return {
        "manifest_version": PROBE_MANIFEST_VERSION,
        "decode": DECODE_DISCIPLINE,
        "sampling_policy": SAMPLING_POLICY,
        "templates": hashes,
        "samples": samples,
        "probes": PROBES,
    }


def write_manifest(templates_dir: Path, receipts_dir: Path, out_path: Path) -> dict:
    manifest = build_manifest(templates_dir, receipts_dir)
    out_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest
