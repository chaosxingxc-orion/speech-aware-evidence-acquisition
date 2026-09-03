"""Receipt-only preprocessing profile for the SELECT/FILL discovery roster."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from speech_aware_evidence_acquisition.core.config import compose


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/a2t_g1_preprocess.py"
ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-select-fill-fresh-roster-v1"
    / "flight-roster-receipt.json"
)
D1_SUPPLEMENT = (
    REPO
    / "docs/receipts/artifacts"
    / "d1-a2t-semantic-agentloop-select-fill-104.json"
)
ROSTER_SHA256 = "dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f"
D1_SHA256 = "52c870f04200b21e3a86dd315085f0ccf44c3e13388b7c1a0f62e04233411a21"
SPLIT_SHA256 = "bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3"


def test_select_fill_profile_identity_is_exactly_bound() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--semantic-agentloop-select-fill",
            "--emit-identity",
        ],
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
    assert identity["run_id"] == (
        "SAEA-SN-A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-PREPROCESS-V1"
    )
    assert identity["subset_receipt_sha256"] == ROSTER_SHA256
    assert identity["split_identity_hash"] == SPLIT_SHA256
    assert identity["count"] == 104
    assert identity["audio_seconds_total"] == 549.489916
    assert identity["prompt_fit_speech_token_ceiling"] is None
    assert identity["inference_prompt_fit_policy"] == (
        "exact-current-request-required-window"
    )
    assert identity["d1_media_supplement"] == (
        "receipts/artifacts/d1-a2t-semantic-agentloop-select-fill-104.json"
    )
    assert identity["d1_media_supplement_sha256"] == D1_SHA256
    assert identity["packet_root"] == (
        "/home/chao/feat-cache/"
        "a2t-semantic-agentloop-select-fill-v1-packets-04ccc72a"
    )
    assert identity["promotion_receipt"].endswith(
        "/A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-V1-promotion.json"
    )
    assert identity["fragments"] == {
        "baseline": "speech-native-preprocess",
        "dataset": "audio2tool-semantic-agentloop-select-fill-104-v1",
        "experiment": "a2t-semantic-agentloop-select-fill-preprocess-v1",
        "model": "q4km-preprocess-featcache-cpu-sidecar-a2t",
    }


def test_select_fill_fragments_are_cpu_only_and_label_free() -> None:
    composed = compose(
        REPO,
        "q4km-preprocess-featcache-cpu-sidecar-a2t",
        "audio2tool-semantic-agentloop-select-fill-104-v1",
        "speech-native-preprocess",
        "a2t-semantic-agentloop-select-fill-preprocess-v1",
    )
    values = composed.values
    assert values["experiment_id"] == (
        "SAEA-SN-A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-PREPROCESS-V1"
    )
    assert values["a2t_semantic_agentloop_select_fill_subset_receipt_sha256"] == (
        ROSTER_SHA256
    )
    assert values["a2t_semantic_agentloop_select_fill_split_identity_hash"] == (
        SPLIT_SHA256
    )
    assert values["d1_media_supplement_sha256"] == D1_SHA256
    assert values["runtime_receipt"] == "receipts/runtime-q4km-preprocess.json"
    args = list(values["server_args"])
    assert args[args.index("-ngl") + 1] == "0"
    assert "--no-mmproj-offload" in args
    scope = values["a2t_semantic_agentloop_select_fill_preprocess_scope"]
    assert scope["count"] == 104
    assert scope["audio_seconds_total"] == 549.489916
    assert scope["packet_id_convention"] == "sample_id with ':' replaced by '/'"
    boundary = values["a2t_semantic_agentloop_select_fill_preprocess_boundary"]
    assert boundary["gold"] == "never loaded"
    assert boundary["model_contacts_in_identity_or_preflight"] == 0
    assert boundary["network_contacts_in_identity_or_preflight"] == 0


def test_select_fill_d1_is_exactly_roster_bound() -> None:
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    supplement = json.loads(D1_SUPPLEMENT.read_text(encoding="utf-8"))
    assert hashlib.sha256(ROSTER.read_bytes()).hexdigest() == ROSTER_SHA256
    assert hashlib.sha256(D1_SUPPLEMENT.read_bytes()).hexdigest() == D1_SHA256
    assert supplement["source_binding_sha256"] == ROSTER_SHA256
    assert supplement["count"] == roster["count"] == 104
    assert [item["id"] for item in supplement["manifest"]] == sorted(
        item["sample_id"] for item in roster["items"]
    )


def test_preprocess_profiles_are_mutually_exclusive() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--semantic-agentloop",
            "--semantic-agentloop-select-fill",
            "--emit-identity",
        ],
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
    assert completed.returncode != 0
    assert "select at most one" in completed.stderr
