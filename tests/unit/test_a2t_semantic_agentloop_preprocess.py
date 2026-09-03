"""Receipt-only preprocessing profile for the fresh semantic AgentLoop roster."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.core.config import compose


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/a2t_g1_preprocess.py"
ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-fresh-agentloop-roster"
    / "flight-roster-receipt.json"
)
D1_SUPPLEMENT = REPO / "docs/receipts/artifacts/d1-a2t-semantic-agentloop-104.json"
D1_SUPPLEMENT_SHA256 = (
    "774f3a9afdcb36a81e35032cf424b8d46d30c17fdc82402eb7ea4d3873fc9e0f"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("a2t_g1_preprocess_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_semantic_agentloop_identity_is_exactly_receipt_and_output_bound() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--semantic-agentloop", "--emit-identity"],
        cwd=REPO,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(REPO / "src"),
        },
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    identity = json.loads(completed.stdout)
    assert identity["run_id"] == ("SAEA-SN-A2T-SEMANTIC-AGENTLOOP-104-PREPROCESS-V2")
    assert identity["subset_receipt_sha256"] == (
        "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
    )
    assert identity["split_identity_hash"] == (
        "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0"
    )
    assert identity["count"] == 104
    assert identity["audio_seconds_total"] == 554.255707
    assert identity["prompt_fit_speech_token_ceiling"] is None
    assert identity["inference_prompt_fit_policy"] == (
        "exact-current-request-required-window"
    )
    assert identity["d1_media_supplement"] == (
        "receipts/artifacts/d1-a2t-semantic-agentloop-104.json"
    )
    assert identity["d1_media_supplement_sha256"] == D1_SUPPLEMENT_SHA256
    assert identity["packet_root"] == (
        "/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a"
    )
    assert identity["promotion_receipt"].endswith(
        "/A2T-SEMANTIC-AGENTLOOP-104-V1-promotion.json"
    )
    assert identity["fragments"] == {
        "baseline": "speech-native-preprocess",
        "dataset": "audio2tool-semantic-agentloop-104-v2",
        "experiment": "a2t-semantic-agentloop-preprocess-v2",
        "model": "q4km-preprocess-featcache-cpu-sidecar-a2t",
    }


def test_semantic_agentloop_fragments_compose_as_cpu_only_and_label_free() -> None:
    composed = compose(
        REPO,
        "q4km-preprocess-featcache-cpu-sidecar-a2t",
        "audio2tool-semantic-agentloop-104-v2",
        "speech-native-preprocess",
        "a2t-semantic-agentloop-preprocess-v2",
    )
    values = composed.values
    assert values["experiment_id"] == (
        "SAEA-SN-A2T-SEMANTIC-AGENTLOOP-104-PREPROCESS-V2"
    )
    assert values["a2t_semantic_agentloop_subset_receipt_sha256"] == (
        "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
    )
    assert values["a2t_semantic_agentloop_split_identity_hash"] == (
        "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0"
    )
    args = list(values["server_args"])
    assert args[args.index("-ngl") + 1] == "0"
    assert "--no-mmproj-offload" in args
    assert values["runtime_receipt"] == "receipts/runtime-q4km-preprocess.json"
    assert values["d1_media_supplement"] == (
        "receipts/artifacts/d1-a2t-semantic-agentloop-104.json"
    )
    assert values["d1_media_supplement_sha256"] == D1_SUPPLEMENT_SHA256
    assert values["task_instruction"] == (
        "Observe the complete speech signal for deterministic feature "
        "preprocessing. Respond with OK."
    )
    assert values["decoding_params"] == {
        "temperature": 0,
        "seed": 20260803,
        "max_tokens": 1,
    }
    scope = values["a2t_semantic_agentloop_preprocess_scope"]
    assert scope["count"] == 104
    assert scope["audio_seconds_total"] == 554.255707
    assert scope["packet_id_convention"] == "sample_id with ':' replaced by '/'"
    assert scope["packet_root"] == (
        "/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a"
    )
    boundary = values["a2t_semantic_agentloop_preprocess_boundary"]
    assert boundary["gold"] == "never loaded"
    assert boundary["model_contacts_in_identity_or_preflight"] == 0
    assert boundary["network_contacts_in_identity_or_preflight"] == 0


def test_receipt_builder_derives_packet_ids_without_loading_task_text(
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    media = tmp_path / "datasets/audio2tool/public/tier1/query.wav"
    media.parent.mkdir(parents=True)
    audio_bytes = b"speech-carrier-bytes"
    media.write_bytes(audio_bytes)
    digest = hashlib.sha256(audio_bytes).hexdigest()
    receipt = {
        "items": [
            {
                "sample_id": "tier1_direct:000597",
                "media_relpath": "datasets/audio2tool/public/tier1/query.wav",
                "audio_sha256": digest,
                "audio_seconds": 1.5,
                "task_text": "must never be consumed",
                "gold": {"must": "remain sealed"},
            }
        ]
    }

    samples = module.build_receipt_bound_samples(receipt, tmp_path)

    assert len(samples) == 1
    assert samples[0].sample_id == "tier1_direct:000597"
    assert samples[0].media_relpath == "datasets/audio2tool/public/tier1/query.wav"
    assert samples[0].audio_ref.sha256 == digest
    assert samples[0].audio_seconds == 1.5
    assert module.receipt_packet_id(receipt["items"][0]) == "tier1_direct/000597"


@pytest.mark.parametrize(
    "media_relpath,audio_sha256",
    [
        ("../outside.wav", hashlib.sha256(b"speech-carrier-bytes").hexdigest()),
        ("datasets/audio2tool/public/tier1/query.wav", "0" * 64),
    ],
)
def test_receipt_builder_refuses_escape_or_audio_hash_drift(
    tmp_path: Path, media_relpath: str, audio_sha256: str
) -> None:
    module = _load_script_module()
    media = tmp_path / "datasets/audio2tool/public/tier1/query.wav"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"speech-carrier-bytes")
    receipt = {
        "items": [
            {
                "sample_id": "tier1_direct:000597",
                "media_relpath": media_relpath,
                "audio_sha256": audio_sha256,
                "audio_seconds": 1.5,
            }
        ]
    }

    with pytest.raises(ValueError):
        module.build_receipt_bound_samples(receipt, tmp_path)


def test_committed_roster_bytes_match_the_registered_receipt_hash() -> None:
    assert hashlib.sha256(ROSTER.read_bytes()).hexdigest() == (
        "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
    )


def test_committed_d1_successor_is_exactly_roster_bound() -> None:
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    supplement = json.loads(D1_SUPPLEMENT.read_text(encoding="utf-8"))
    assert hashlib.sha256(D1_SUPPLEMENT.read_bytes()).hexdigest() == (
        D1_SUPPLEMENT_SHA256
    )
    assert supplement["carrier_lock_key"] == "audio2tool"
    assert (
        supplement["source_binding_sha256"]
        == hashlib.sha256(ROSTER.read_bytes()).hexdigest()
    )
    assert supplement["count"] == roster["count"] == 104
    assert [item["id"] for item in supplement["manifest"]] == sorted(
        item["sample_id"] for item in roster["items"]
    )
    canonical = json.dumps(
        supplement["manifest"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert supplement["manifest_sha256"] == hashlib.sha256(canonical).hexdigest()
