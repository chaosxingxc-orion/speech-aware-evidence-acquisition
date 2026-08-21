"""Synthetic carrier world: real layer layouts, fake bytes, a minimal umbrella lock.

The directory shapes mirror the real materialized carriers exactly (media, metadata
CSVs, nlp_references, wer_tags, normalizations, force-aligned references, subset10,
ConEC contexts/timestamps/participant_names) so identity and loader code paths are
exercised without any real data or network access.
"""

import json
from pathlib import Path

import pytest

E21_IDS = ("4000001", "4000002", "4000003")
E22_IDS = tuple(f"50000{index:02d}" for index in range(12))
SUBSET10_IDS = E22_IDS[:10]
# D1's bounded-discovery-probe carriers (2026-08-15 owner amendment):
# SLURP's one devel-split sentence/recording and Audio2Tool's one frozen
# receipt item, materialized directly under SyntheticWorld's own data_root/
# lock (data.identity.slurp_layers/audio2tool_layers own docstrings).
SLURP_D1_SLURP_ID = 9001
SLURP_D1_SAMPLE_ID = f"slurp:devel:{SLURP_D1_SLURP_ID:06d}:audio-{SLURP_D1_SLURP_ID}"
AUDIO2TOOL_D1_SAMPLE_ID = "tier1_direct:000001"
AUDIO2TOOL_D1_RECEIPT_NAME = "d1-test-audio2tool-sample"


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SyntheticWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "speechrl-data"
        self.lock_path = tmp_path / "datasets.lock.json"
        self.repo_root = tmp_path / "repo"
        self.e21 = self.data_root / "datasets" / "earnings21-22" / "earnings21"
        self.e22 = self.data_root / "datasets" / "earnings21-22" / "earnings22"
        self.conec = self.data_root / "datasets" / "conec"
        self.slurp_audio_root = self.data_root / "datasets" / "slurp"
        self.slurp_metadata_dir = self.slurp_audio_root / "metadata"
        self.audio2tool_dir = self.data_root / "datasets" / "audio2tool"
        self.audio2tool_public = self.audio2tool_dir / "public"
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
                self.conec
                / "earnings21"
                / "contexts"
                / "participant_names"
                / f"{sample_id}.names.txt",
                "Jane Doe - CEO\n",
            )
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
        self._materialize_slurp()
        self._materialize_audio2tool()

    def _materialize_slurp(self) -> None:
        """One devel-split (sentence, recording) sample -- just enough for
        ``data.identity.slurp_layers``'s ``devel``-only D1 read; the other
        three splits' jsonl files are never opened by that call path (module
        docstring: only the requested split's metadata file is read)."""

        devel = [
            {
                "slurp_id": SLURP_D1_SLURP_ID,
                "sentence": "turn on the kitchen lights",
                "sentence_annotation": "turn on the [house_place : kitchen] lights",
                "intent": "iot_hue_lighton",
                "scenario": "iot",
                "action": "hue_lighton",
                "tokens": _tokens("turn", "on", "the", "kitchen", "lights"),
                "entities": [{"span": [3], "type": "house_place"}],
                "recordings": [
                    {
                        "file": f"audio-{SLURP_D1_SLURP_ID}.flac",
                        "wer": 0.0,
                        "ent_wer": 0.0,
                        "status": "correct",
                    }
                ],
            }
        ]
        self.slurp_metadata_dir.mkdir(parents=True, exist_ok=True)
        (self.slurp_metadata_dir / "devel.jsonl").write_text(
            "\n".join(json.dumps(record) for record in devel) + "\n", encoding="utf-8"
        )
        _write_flac(self.slurp_audio_root / "slurp_real" / f"audio-{SLURP_D1_SLURP_ID}.flac")

    def _materialize_audio2tool(self) -> None:
        """One frozen-receipt tier1 item -- the same shape ``Audio2ToolWorld``
        uses, materialized under THIS world's own ``data_root``/``repo_root``
        so ``data.identity.audio2tool_layers`` (default-scoped, ``devel``-only
        SLURP aside) resolves without touching the real 400-item receipt."""

        manifest = [
            {
                "id": 1,
                "tier": "tier1_direct",
                "query_idx": 9100,
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
            }
        ]
        manifest_path = self.audio2tool_public / "tier1_direct_data" / "tier1_direct.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        _write_wav(
            self.audio2tool_public / "tier1_direct_audios" / "query_00001" / "turn.wav",
            sample_rate_hz=16000,
        )
        _touch(
            self.audio2tool_dir / "tools_registry.csv",
            "tool_id,domain,category,tool_name,signature,description,"
            "argument_defaults,argument_constraints\n"
            '2,smart_home,lighting,setLighting,"setLighting(deviceId: String)",'
            '"Turns a light on.","deviceId=\'light_1\'",""\n',
        )
        from speech_aware_evidence_acquisition.reproduction.sampling import (
            split_identity_hash as compute_hash,
        )

        items = [
            {"id": 1, "key": f"audio2tool:{AUDIO2TOOL_D1_SAMPLE_ID}", "query_idx": 9100, "tier": "tier1_direct"}
        ]
        receipt_payload = {
            "probe": "D1-audio2tool-test",
            "carrier": "audio2tool",
            "seed": 1,
            "design": "synthetic D1-closure test receipt",
            "pool_size": 1,
            "strata_counts": {},
            "items": items,
            "split_identity_hash": compute_hash([item["key"] for item in items]),
            "split_role": "discovery",
        }
        receipt_path = (
            self.repo_root
            / "docs"
            / "receipts"
            / "probe-samples"
            / f"{AUDIO2TOOL_D1_RECEIPT_NAME}.json"
        )
        _touch(receipt_path, json.dumps(receipt_payload, indent=2, sort_keys=True))

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
                {
                    "name": "slurp",
                    "kind": "dataset",
                    "local_subdir": "repos/slurp/scripts/audio",
                    "license": "mixed: textual part CC BY 4.0, audio part CC BY-NC 4.0",
                    "lifecycle": "SECONDARY_CARRIER",
                    "profiles": ["speech-aware-secondary"],
                    "annotations": {"governed_copy": "datasets/slurp/metadata"},
                },
                {
                    "name": "audio2tool",
                    "kind": "dataset",
                    "local_subdir": "datasets/audio2tool",
                    "license": "cc-by-nc-4.0",
                    "lifecycle": "LOCAL_CANDIDATE",
                    "profiles": ["speech-aware-secondary"],
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


# ---------------------------------------------------------------------------
# B-2a bias-list world (docs/readiness/2026-08-09-exploration-plan.md section
# 3b): a richer earnings21-original + conec pairing than SyntheticWorld's
# trivial "ctx" content (deliberately NOT changed above -- test_core_
# components.py/test_driver.py assert on it byte-for-byte), so extraction can
# actually be exercised through all four candidate categories
# (core.bias_lists._TERM_PATTERN's own docstring), plus a small, obviously-
# synthetic (ZQXVBIAS-prefixed, guaranteed not to collide with any realistic
# proper noun elsewhere in this fixture) oracle/distractor bias-list pair for
# the set-difference source.
# ---------------------------------------------------------------------------

BIAS_WORLD_SAMPLE_ID = "4900001"
BIAS_WORLD_ORACLE_TERMS = ("ZQXVBIAS ALPHA", "ZQXVBIAS BRAVO", "ZQXVBIAS CHARLIE")
BIAS_WORLD_DISTRACTOR_ONLY_TERMS = ("ZQXVBIAS DELTA", "ZQXVBIAS ECHO")
BIAS_WORLD_CONEC_CONTEXT_TEXT = (
    "Maureen Mulholland - Senior Vice President, General Counsel\n"
    "Brett Ponton - President and CEO\n"
    "Goldman Sachs & Co is acting as advisor\n"
    "danaher 1\n"
    "corporation 1\n"
    "ponton 1\n"
    "nyse 1\n"
    "IBM reported strong quarterly results\n"
)


class BiasListWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "bias-data"
        self.lock_path = tmp_path / "bias-lock.json"
        self.e21 = self.data_root / "datasets" / "earnings21-22" / "earnings21"
        self.conec = self.data_root / "datasets" / "conec"
        self.sample_id = BIAS_WORLD_SAMPLE_ID
        self._materialize()
        self._write_lock()

    def _materialize(self) -> None:
        _touch(
            self.conec / "earnings21" / "contexts" / f"{self.sample_id}.txt",
            BIAS_WORLD_CONEC_CONTEXT_TEXT,
        )
        distractor_terms = list(BIAS_WORLD_ORACLE_TERMS) + list(BIAS_WORLD_DISTRACTOR_ONLY_TERMS)
        _touch(self.e21 / "bias_lists" / "oracle_list.txt", "\n".join(BIAS_WORLD_ORACLE_TERMS) + "\n")
        _touch(self.e21 / "bias_lists" / "distractor_list.txt", "\n".join(distractor_terms) + "\n")

    def _write_lock(self) -> None:
        document = {
            "datasets": [
                {
                    "name": "earnings21-original",
                    "local_subdir": "datasets/earnings21-22/earnings21",
                },
                {"name": "conec", "local_subdir": "datasets/conec"},
            ]
        }
        self.lock_path.write_text(json.dumps(document), encoding="utf-8")


@pytest.fixture()
def bias_list_world(tmp_path):
    return BiasListWorld(tmp_path)


# ---------------------------------------------------------------------------
# Synthetic SLURP carrier world: mirrors the real governed-metadata layout
# exactly -- ``datasets/slurp/metadata/{devel,test,train,train_synthetic}.jsonl``
# plus ``datasets/slurp/{slurp_real,slurp_synth}/*.flac`` siblings, with a
# lock entry carrying the SAME ``local_subdir``/``annotations.governed_copy``
# shape the real umbrella ``docs/datasets.lock.json`` ``slurp`` entry has
# (data.slurp module docstring) -- fake but structurally-real flac bytes
# (tiny, silent, written via ``soundfile`` so ``data.slurp._audio_seconds``
# exercises the real flac-header code path, not a stub).
# ---------------------------------------------------------------------------


def _write_flac(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 0.5) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate_hz * seconds)
    sf.write(str(path), np.zeros(frames, dtype="float32"), sample_rate_hz, format="FLAC")


def _tokens(*surfaces: str) -> list[dict]:
    return [{"surface": surface, "id": index, "lemma": surface, "pos": "NN"} for index, surface in enumerate(surfaces)]


class SlurpWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "slurp-data"
        self.lock_path = tmp_path / "slurp-lock.json"
        self.audio_root = self.data_root / "datasets" / "slurp"
        self.metadata_dir = self.audio_root / "metadata"
        self._materialize()
        self._write_lock()

    def _materialize(self) -> None:
        devel = [
            {
                "slurp_id": 101,
                "sentence": "turn on the kitchen lights",
                "sentence_annotation": "turn on the [house_place : kitchen] lights",
                "intent": "iot_hue_lighton",
                "scenario": "iot",
                "action": "hue_lighton",
                "tokens": _tokens("turn", "on", "the", "kitchen", "lights"),
                "entities": [{"span": [3], "type": "house_place"}],
                "recordings": [
                    {"file": "audio-101-headset.flac", "wer": 0.0, "ent_wer": 0.0, "status": "correct"},
                    {"file": "audio-101.flac", "wer": 0.0, "ent_wer": 0.0, "status": "correct"},
                ],
            },
            {
                "slurp_id": 102,
                "sentence": "how many unread emails do i have",
                "sentence_annotation": "how many unread emails do i have",
                "intent": "email_query",
                "scenario": "email",
                "action": "query",
                "tokens": _tokens("how", "many", "unread", "emails", "do", "i", "have"),
                "entities": [],
                "recordings": [
                    {"file": "audio-102.flac", "wer": 0.0, "ent_wer": None, "status": "correct"},
                ],
            },
        ]
        test = [
            {
                "slurp_id": 201,
                "sentence": "set an alarm",
                "sentence_annotation": "set an alarm",
                "intent": "alarm_set",
                "scenario": "alarm",
                "action": "set",
                "tokens": _tokens("set", "an", "alarm"),
                "entities": [],
                "recordings": [
                    {"file": "audio-201.flac", "wer": 0.0, "ent_wer": None, "status": "correct"},
                ],
            }
        ]
        train = [
            {
                "slurp_id": 301,
                "sentence": "dim the lights in the kitchen",
                "sentence_annotation": "dim the lights in the [house_place : kitchen]",
                "intent": "iot_hue_lightdim",
                "scenario": "iot",
                "action": "hue_lightdim",
                "tokens": _tokens("dim", "the", "lights", "in", "the", "kitchen"),
                "entities": [{"span": [5], "type": "house_place"}],
                "recordings": [
                    {"file": "audio-301.flac", "wer": 0.0, "ent_wer": 0.0, "status": "correct"},
                ],
            },
            {
                "slurp_id": 302,
                "sentence": "what is the weather",
                "sentence_annotation": "what is the weather",
                "intent": "weather_query",
                "scenario": "weather",
                "action": "query",
                "tokens": _tokens("what", "is", "the", "weather"),
                "entities": [],
                "recordings": [
                    {"file": "audio-302.flac", "wer": 0.0, "ent_wer": None, "status": "correct"},
                ],
            },
        ]
        train_synthetic = [
            {
                "slurp_id": 401,
                "sentence": "wake me at six",
                "sentence_annotation": "wake me at [time : six]",
                "intent": "alarm_set",
                "scenario": "alarm",
                "action": "set",
                "tokens": _tokens("wake", "me", "at", "six"),
                "entities": [{"span": [3], "type": "time"}],
                "recordings": [
                    {"file": "audio-401-synth.flac", "wer": 0.0, "ent_wer": 0.0, "status": "synthetic"},
                ],
            }
        ]
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        for name, records in (
            ("devel.jsonl", devel),
            ("test.jsonl", test),
            ("train.jsonl", train),
            ("train_synthetic.jsonl", train_synthetic),
        ):
            (self.metadata_dir / name).write_text(
                "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
            )
        speaker_by_file = {
            "audio-101-headset.flac": "speaker-devel-a",
            "audio-101.flac": "speaker-devel-a",
            "audio-102.flac": "speaker-devel-b",
            "audio-201.flac": "speaker-test-a",
            "audio-301.flac": "speaker-train-a",
            "audio-302.flac": "speaker-train-b",
            "audio-401-synth.flac": "speaker-synthetic-a",
        }
        metadata = {
            str(index): {
                "recordings": {
                    filename: {"usrid": speaker_id, "status": "correct"}
                }
            }
            for index, (filename, speaker_id) in enumerate(speaker_by_file.items())
        }
        (self.metadata_dir / "metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )
        real_dir = self.audio_root / "slurp_real"
        for filename in ("audio-101-headset.flac", "audio-101.flac", "audio-102.flac", "audio-201.flac", "audio-301.flac", "audio-302.flac"):
            _write_flac(real_dir / filename)
        synth_dir = self.audio_root / "slurp_synth"
        _write_flac(synth_dir / "audio-401-synth.flac")

    def _write_lock(self) -> None:
        document = {
            "datasets": [
                {
                    "name": "slurp",
                    "kind": "dataset",
                    "local_subdir": "repos/slurp/scripts/audio",
                    "license": (
                        "mixed: textual part CC BY 4.0, audio part CC BY-NC 4.0"
                    ),
                    "lifecycle": "SECONDARY_CARRIER",
                    "profiles": ["speech-aware-secondary"],
                    "annotations": {
                        "governed_copy": "datasets/slurp/metadata",
                    },
                }
            ],
            "models": [],
        }
        self.lock_path.write_text(json.dumps(document), encoding="utf-8")


@pytest.fixture()
def slurp_world(tmp_path):
    return SlurpWorld(tmp_path)
