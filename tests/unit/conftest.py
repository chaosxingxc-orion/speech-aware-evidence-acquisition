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
