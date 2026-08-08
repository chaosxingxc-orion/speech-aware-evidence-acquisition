"""Synthetic carrier world: real layer layouts, fake bytes, a minimal umbrella lock.

The directory shapes mirror the real materialized carriers exactly (media, metadata
CSVs, nlp_references, wer_tags, normalizations, force-aligned references, subset10,
ConEC contexts/timestamps) so identity and loader code paths are exercised without
any real data or network access.
"""

import json
from pathlib import Path

import pytest

E21_IDS = ("4000001", "4000002", "4000003")
E22_IDS = tuple(f"50000{index:02d}" for index in range(12))
SUBSET10_IDS = E22_IDS[:10]


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SyntheticWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "speechrl-data"
        self.lock_path = tmp_path / "datasets.lock.json"
        self.e21 = self.data_root / "datasets" / "earnings21-22" / "earnings21"
        self.e22 = self.data_root / "datasets" / "earnings21-22" / "earnings22"
        self.conec = self.data_root / "datasets" / "conec"
        self._materialize()
        self._write_lock()

    def _materialize(self) -> None:
        for sample_id in E21_IDS:
            _touch(self.e21 / "media" / f"{sample_id}.mp3", f"fake-audio-{sample_id}")
            _touch(
                self.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp",
                "token|tags\n",
            )
            _touch(
                self.e21 / "transcripts" / "wer_tags" / f"{sample_id}.wer_tag.json", "{}"
            )
            _touch(
                self.e21 / "transcripts" / "normalizations" / f"{sample_id}.norm.json", "{}"
            )
            _touch(self.conec / "earnings21" / "contexts" / f"{sample_id}.txt", "ctx")
            _touch(
                self.conec / "earnings21" / "transcripts" / "nlp_references" / f"{sample_id}.nlp",
                "token|tags\n",
            )
            _touch(
                self.conec / "earnings21" / "transcripts" / "timestamps" / f"{sample_id}.nlp",
                "token|ts\n",
            )
            _touch(
                self.conec
                / "earnings21"
                / "transcripts"
                / "wer_tags"
                / f"{sample_id}.wer_tag.json",
                "{}",
            )
        _touch(
            self.e21 / "earnings21-file-metadata.csv",
            # Mirrors the real earnings21-file-metadata.csv header exactly (verified
            # against the materialized asset); loader/identity code reads columns by
            # name, so the trailing columns are inert placeholders here.
            "file_id,audio_length,sample_rate,company_name,financial_quarter,sector,"
            "speaker_switches,unique_speakers,curator_id\n"
            + "\n".join(
                f"{sample_id},100.5,16000,Acme Corp,Q1 2020,Technology,10,3,curator-1"
                for sample_id in E21_IDS
            )
            + "\n",
        )

        for sample_id in E22_IDS:
            _touch(self.e22 / "media" / f"{sample_id}.mp3", f"fake-audio-{sample_id}")
            _touch(
                self.e22 / "transcripts" / "nlp_references" / f"{sample_id}.nlp",
                "token|tags\n",
            )
            _touch(
                self.e22
                / "transcripts"
                / "force_aligned_nlp_references"
                / f"{sample_id}.aligned.nlp",
                "token|ts\n",
            )
        for sample_id in SUBSET10_IDS:
            _touch(self.e22 / "subset10" / "media" / f"{sample_id}.mp3", "subset-marker")
        _touch(
            self.e22 / "metadata.csv",
            "File ID,File Length (seconds),Sampling Rate (Hz)\n"
            + "\n".join(f"{sample_id},1200,16000" for sample_id in E22_IDS)
            + "\n",
        )
        _touch(
            self.conec / "earnings22" / "contexts" / "pdfs" / f"{E22_IDS[0]}.pdf", "pdf"
        )
        _touch(
            self.conec / "earnings22" / "contexts" / "pdfs" / f"{E22_IDS[0]}_2.pdf", "pdf"
        )

    def _write_lock(self) -> None:
        document = {
            "datasets": [
                {
                    "name": "earnings21-original",
                    "kind": "dataset",
                    "local_subdir": "datasets/earnings21-22/earnings21",
                    "license": "CC-BY-SA-4.0",
                    "lifecycle": "STAGE2_CORE",
                    "profiles": ["speech-aware-core"],
                    "verification": {
                        "main_audio_files": len(E21_IDS),
                        "metadata_rows": len(E21_IDS),
                    },
                },
                {
                    "name": "earnings22-original",
                    "kind": "dataset",
                    "local_subdir": "datasets/earnings21-22/earnings22",
                    "license": "CC-BY-SA-4.0",
                    "lifecycle": "STAGE2_CORE",
                    "profiles": ["speech-aware-core"],
                    "verification": {
                        "main_audio_files": len(E22_IDS),
                        "metadata_rows": len(E22_IDS),
                    },
                },
                {
                    "name": "conec",
                    "kind": "dataset",
                    "local_subdir": "datasets/conec",
                    "license": "paper CC-BY-NC-4.0",
                    "lifecycle": "STAGE2_CORE",
                    "profiles": ["speech-aware-core"],
                },
                {"name": "fsd50k", "kind": "dataset", "profiles": ["retained-cross-domain"]},
                {
                    "name": "audioset-metadata-features",
                    "kind": "dataset",
                    "profiles": ["retained-cross-domain"],
                },
                {"name": "esc-50", "kind": "dataset", "profiles": ["retained-cross-domain"]},
            ],
            "models": [],
        }
        self.lock_path.write_text(json.dumps(document), encoding="utf-8")


@pytest.fixture()
def synthetic_world(tmp_path):
    return SyntheticWorld(tmp_path)


# ---------------------------------------------------------------------------
# Synthetic Audio2Tool carrier world (P1 scaffold): mirrors the real on-disk
# layout exactly — per-tier JSON manifests under public/tier*_data/, per-query
# wav directories under public/tier*_audios/, tools_registry.csv at the
# carrier root, and a frozen probe-sample receipt in the (synthetic) study
# repo — with fake but structurally-real gold shapes observed in the actual
# tier manifests (tier1 call-string, tier3 bare name + concatenated
# additional calls, tier7 chat_history with no top-level path/duration).
# ---------------------------------------------------------------------------

A2T_RECEIPT_NAME = "r1-a2t-test"


def _write_wav(path: Path, *, sample_rate_hz: int, frames: int = 160) -> None:
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(b"\x00\x00" * frames)


class Audio2ToolWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "a2t-data"
        self.repo_root = tmp_path / "a2t-repo"
        self.lock_path = tmp_path / "a2t-lock.json"
        self.carrier_dir = self.data_root / "datasets" / "audio2tool"
        self.public = self.carrier_dir / "public"
        self.receipt_name = A2T_RECEIPT_NAME
        self.receipt_path = (
            self.repo_root / "docs" / "receipts" / "probe-samples" / f"{A2T_RECEIPT_NAME}.json"
        )
        self.template_relpath = "probes/test_a2t_direct.txt"
        self._materialize()
        self._write_lock()

    # -- carrier layout ----------------------------------------------------
    def _materialize(self) -> None:
        tier1 = [
            {
                "id": 1,
                "tier": "tier1_direct",
                "query_idx": 2100,
                "query": "turn on the lights",
                "domain": "smart_home",
                "category": "lighting",
                "tool_id": 2,
                "tool_name": "setLighting",
                "expected_tool_call": "setLighting()",
                "extracted_params": {},
                "additional_tool_calls": None,
                "path": "tier1_direct_audios/query_00001/turn.wav",
                "duration": 0.5,
            },
            {
                # NOT in the receipt: its wav deliberately does not exist, so a
                # loader that touches non-receipt items fails loudly in tests.
                "id": 2,
                "tier": "tier1_direct",
                "query_idx": 2101,
                "query": "unused",
                "domain": "smart_home",
                "category": "lighting",
                "tool_id": 2,
                "tool_name": "setLighting",
                "expected_tool_call": "setLighting()",
                "extracted_params": {},
                "additional_tool_calls": None,
                "path": "tier1_direct_audios/query_00002/turn.wav",
                "duration": 0.5,
            },
        ]
        tier3 = [
            {
                "id": 4,
                "tier": "tier3_multi_intent",
                "query_idx": 300,
                "query": "arm the house and warm it up",
                "domain": "smart_home",
                "category": "security",
                "tool_id": 10,
                "tool_name": "setSecurityMode",
                "expected_tool_call": "setSecurityMode",
                "extracted_params": {"mode": "Armed_Away", "level": "2"},
                "additional_tool_calls": [
                    "setTargetTemperature(temperature=68.0)setColor(color='blue')",
                    "calibrateThermostat",
                ],
                "path": "tier3_multi_intent_audios/query_00004/turn.wav",
                "duration": 1.25,
            }
        ]
        tier7 = [
            {
                # Real tier7 rows carry NO top-level path/duration/additional
                # keys at all; audio lives per turn inside chat_history.
                "id": 9,
                "tier": "tier7_multiturn",
                "query_idx": 2108,
                "query": "USER: ...\nAGENT: ...\nUSER: set my gym alarm",
                "domain": "wearables",
                "category": "alarms",
                "tool_id": 30,
                "tool_name": "setAlarm",
                "expected_tool_call": "setAlarm(time='06:30', repeat=['Weekdays'])",
                "extracted_params": {"time": "06:30", "repeat": '["Weekdays"]'},
                "chat_history": [
                    {
                        "role": "user",
                        "content": "first ask",
                        "path": "tier7_multiturn_audios/query_00009/turn_00_user.wav",
                        "duration": 4.617,
                    },
                    {
                        "role": "agent",
                        "content": "which alarm?",
                        "path": "tier7_multiturn_audios/query_00009/turn_01_agent.wav",
                        "duration": 2.0,
                    },
                    {
                        "role": "user",
                        "content": "the gym one",
                        "path": "tier7_multiturn_audios/query_00009/turn_02_user.wav",
                        "duration": 6.7,
                    },
                ],
            }
        ]
        for tier_name, entries in (
            ("tier1_direct", tier1),
            ("tier3_multi_intent", tier3),
            ("tier7_multiturn", tier7),
        ):
            manifest = self.public / f"{tier_name}_data" / f"{tier_name}.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(entries), encoding="utf-8")
        _write_wav(
            self.public / "tier1_direct_audios" / "query_00001" / "turn.wav",
            sample_rate_hz=16000,
        )
        _write_wav(
            self.public / "tier3_multi_intent_audios" / "query_00004" / "turn.wav",
            sample_rate_hz=22050,
        )
        _write_wav(
            self.public / "tier7_multiturn_audios" / "query_00009" / "turn_00_user.wav",
            sample_rate_hz=16000,
        )
        # turn_01_agent.wav deliberately absent: only the FINAL user turn's
        # media is loaded by the P1 scaffold.
        _write_wav(
            self.public / "tier7_multiturn_audios" / "query_00009" / "turn_02_user.wav",
            sample_rate_hz=16000,
        )
        _touch(
            self.carrier_dir / "tools_registry.csv",
            "tool_id,domain,category,tool_name,signature,description,"
            "argument_defaults,argument_constraints\n"
            '10,smart_home,security,setSecurityMode,"setSecurityMode(mode: Mode)",'
            '"Sets the security mode.","mode=\'Home\'","mode: [Home, Armed_Away]"\n'
            '2,smart_home,lighting,setLighting,"setLighting(deviceId: String)",'
            '"Turns a light on.","deviceId=\'light_1\'",""\n',
        )
        self.write_receipt()
        _touch(
            self.repo_root / "configs" / self.template_relpath,
            "You control tools.\n\nAvailable tools:\n{tool_schemas}\n\n"
            'Respond with ONLY a JSON array like [{"name": "x", "arguments": {}}].\n',
        )

    # -- frozen probe-sample receipt ----------------------------------------
    def receipt_items(self) -> list[dict]:
        return [
            {"id": 1, "key": "audio2tool:tier1_direct:000001", "query_idx": 2100, "tier": "tier1_direct"},
            {"id": 4, "key": "audio2tool:tier3_multi_intent:000004", "query_idx": 300, "tier": "tier3_multi_intent"},
            {"id": 9, "key": "audio2tool:tier7_multiturn:000009", "query_idx": 2108, "tier": "tier7_multiturn"},
        ]

    def write_receipt(self, *, items: list[dict] | None = None, split_identity_hash: str | None = None, split_role: str = "discovery") -> None:
        from speech_aware_evidence_acquisition.reproduction.sampling import (
            split_identity_hash as compute_hash,
        )

        items = self.receipt_items() if items is None else items
        payload = {
            "probe": "R1-audio2tool-direct-test",
            "carrier": "audio2tool",
            "seed": 1,
            "design": "synthetic test receipt",
            "pool_size": 4,
            "strata_counts": {},
            "items": items,
            "split_identity_hash": (
                compute_hash([item["key"] for item in items])
                if split_identity_hash is None
                else split_identity_hash
            ),
            "split_role": split_role,
        }
        _touch(self.receipt_path, json.dumps(payload, indent=2, sort_keys=True))

    def _write_lock(self) -> None:
        document = {
            "asset_catalog": [
                {
                    "name": "audio2tool",
                    "kind": "dataset",
                    "local_subdir": "datasets/audio2tool",
                    "license": "CC-BY-NC-4.0 (disk README; paper says CC-BY-4.0 — owner decision pending)",
                    "lifecycle": "STAGE2_CANDIDATE",
                    "profiles": ["speech-aware-secondary"],
                }
            ],
            "models": [],
        }
        self.lock_path.write_text(json.dumps(document), encoding="utf-8")


@pytest.fixture()
def audio2tool_world(tmp_path):
    return Audio2ToolWorld(tmp_path)
