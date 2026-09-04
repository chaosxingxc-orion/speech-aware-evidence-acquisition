"""``rails.adapters.earnings.Earnings21Adapter`` (C2 rails, third concrete
adapter): load/instruction/gold/score on a tiny, dedicated synthetic
Earnings21 root (mirrors the layout ``tests/unit/test_identity_and_loader.py``
/ ``tests/unit/test_splits.py``'s own ``SyntheticWorld`` builds, trimmed to
exactly what this adapter needs: one ``.mp3`` placeholder, one REAL ``.nlp``
reference with actual token rows, and the metadata CSV both
``data.splits.discovery_split`` and ``data.loader.load_earnings21`` read).
The shared ``synthetic_world`` fixture (``tests/unit/conftest.py``) is reused
for the ``"dev"`` split test, since it already materializes a full
Earnings21+Earnings22 pair -- ``load_split`` itself never reads reference
content, so that fixture's header-only ``.nlp`` files are sufficient there.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import REPO_ROOT, load_lock
from speech_aware_evidence_acquisition.rails.adapters.earnings import (
    Earnings21Adapter,
    EarningsSample,
)
from speech_aware_evidence_acquisition.rails.obs import default_obs_packet


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class EarningsWorld:
    """A tiny, dedicated Earnings21-only synthetic root."""

    SAMPLE_ID = "4000001"
    # Deliberately distinctive nonsense words (never ordinary English
    # function/content words like "the"): the gold-leak checks below search
    # for these as bare substrings, and a common word would false-positive
    # match inside the fixed instruction/contract English text itself (e.g.
    # the real r4_transcribe_nocontext.txt template legitimately contains
    # "the"). Mirrors the ZQXVBIAS-prefixed synthetic terms
    # tests/unit/conftest.py's own BiasListWorld uses for the same reason.
    REFERENCE_TOKENS = ("zqearn", "wobbleforge", "brimtide", "quarrelnest", "hallowmark")

    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "speechrl-data"
        self.lock_path = tmp_path / "datasets.lock.json"
        self.e21 = self.data_root / "datasets" / "earnings21-22" / "earnings21"

        _write(self.e21 / "media" / f"{self.SAMPLE_ID}.mp3", "fake-audio-bytes")
        _write(
            self.e21 / "transcripts" / "nlp_references" / f"{self.SAMPLE_ID}.nlp",
            "token|tags\n" + "\n".join(f"{token}|O" for token in self.REFERENCE_TOKENS) + "\n",
        )
        _write(
            self.e21 / "earnings21-file-metadata.csv",
            "file_id,audio_length,sample_rate\n" f"{self.SAMPLE_ID},100.5,16000\n",
        )
        self.lock_path.write_text(
            json.dumps(
                {
                    "datasets": [
                        {
                            "name": "earnings21-original",
                            "local_subdir": "datasets/earnings21-22/earnings21",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )


@pytest.fixture()
def earnings_world(tmp_path):
    return EarningsWorld(tmp_path)


def _adapter(world) -> Earnings21Adapter:
    lock = load_lock(world.lock_path)
    return Earnings21Adapter(lock, world.data_root)


# ---------------------------------------------------------------------------
# load_split
# ---------------------------------------------------------------------------


def test_load_split_discovery_returns_the_one_sample(earnings_world):
    samples = _adapter(earnings_world).load_split("discovery")
    assert [s.sample_id for s in samples] == [EarningsWorld.SAMPLE_ID]
    sample = samples[0]
    assert isinstance(sample, EarningsSample)
    assert sample.carrier_lock_key == "earnings21-original"
    assert sample.media_relpath.endswith(f"media/{EarningsWorld.SAMPLE_ID}.mp3")
    assert sample.audio_ref.path == sample.media_relpath
    assert len(sample.audio_ref.sha256) == 64
    assert sample.audio_seconds == 100.5


def test_load_split_unknown_split_id_raises(earnings_world):
    with pytest.raises(ValueError, match="unknown Earnings split_id"):
        _adapter(earnings_world).load_split("confirmatory")


def test_load_split_dev_returns_earnings22_subset10_samples(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    adapter = Earnings21Adapter(lock, synthetic_world.data_root)
    samples = adapter.load_split("dev")
    assert len(samples) == 10
    assert all(sample.carrier_lock_key == "earnings22-original" for sample in samples)
    assert [s.sample_id for s in samples] == sorted(s.sample_id for s in samples)
    assert all(sample.media_relpath.endswith(".mp3") for sample in samples)


# ---------------------------------------------------------------------------
# build_task_contract / instruction -- fixed, gold-free
# ---------------------------------------------------------------------------


def test_build_task_contract_is_fixed_and_gold_free(earnings_world):
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    obs = default_obs_packet(sample)
    contract = adapter.build_task_contract(sample, obs)
    assert "speech recognition" in contract.lower()
    for token in EarningsWorld.REFERENCE_TOKENS:
        assert token not in contract


def test_instruction_matches_the_real_r4_template(earnings_world):
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    expected = (REPO_ROOT / "configs" / "probes" / "r4_transcribe_nocontext.txt").read_text(
        encoding="utf-8"
    )
    assert adapter.instruction(sample) == expected
    for token in EarningsWorld.REFERENCE_TOKENS:
        assert token not in adapter.instruction(sample)


# ---------------------------------------------------------------------------
# gold / score
# ---------------------------------------------------------------------------


def test_gold_returns_the_sample_identity_not_reference_content(earnings_world):
    # gold() deliberately returns the SAMPLE itself (carrier_lock_key +
    # sample_id), never reference token content: the actual .nlp bytes are
    # read only inside score_response, through core.scorers.
    # score_asr_outputs (module docstring, reference-import isolation --
    # tests/contract/test_reference_import_isolation.py, AST-enforced).
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    gold = adapter.gold(sample)
    assert gold is sample
    assert gold.carrier_lock_key == "earnings21-original"
    assert gold.sample_id == EarningsWorld.SAMPLE_ID


def test_score_exact_transcript_is_zero_wer(earnings_world):
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    response = " ".join(EarningsWorld.REFERENCE_TOKENS)
    metrics = adapter.score(sample, response)
    assert metrics["wer"] == 0.0
    assert metrics["substitutions"] == 0
    assert metrics["deletions"] == 0
    assert metrics["insertions"] == 0
    assert metrics["reference_words"] == len(EarningsWorld.REFERENCE_TOKENS)
    assert metrics["parsed"] is True


def test_score_one_substitution_scores_partial_wer(earnings_world):
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    tokens = list(EarningsWorld.REFERENCE_TOKENS)
    tokens[-1] = "somethingelse"
    metrics = adapter.score(sample, " ".join(tokens))
    assert metrics["substitutions"] == 1
    assert metrics["deletions"] == 0
    assert metrics["insertions"] == 0
    assert metrics["wer"] == pytest.approx(1 / len(EarningsWorld.REFERENCE_TOKENS))
    assert metrics["parsed"] is True


def test_score_response_matches_score_composition(earnings_world):
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    response = " ".join(EarningsWorld.REFERENCE_TOKENS)
    assert adapter.score(sample, response) == adapter.score_response(adapter.gold(sample), response)


def test_score_response_never_imports_data_references_directly():
    # Regression guard for the reference-import isolation contract
    # (tests/contract/test_reference_import_isolation.py, AST-enforced):
    # this adapter module itself must never import data.references, not
    # even lazily -- reference reading happens exclusively inside
    # core.scorers.score_asr_outputs.
    import ast

    from speech_aware_evidence_acquisition.rails.adapters import earnings as earnings_module

    tree = ast.parse(Path(earnings_module.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.endswith("references")
            assert not any(alias.name == "references" for alias in node.names)
        if isinstance(node, ast.Import):
            assert not any("references" in alias.name for alias in node.names)


# ---------------------------------------------------------------------------
# assemble_prompt -- default shape + gold-leak guard
# ---------------------------------------------------------------------------


def test_assemble_prompt_default_shape_and_no_gold_leak(earnings_world):
    adapter = _adapter(earnings_world)
    sample = adapter.load_split("discovery")[0]
    messages = adapter.assemble_prompt(sample, None)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    user_content = messages[1]["content"]
    assert user_content == [{"type": "input_audio", "media_relpath": sample.media_relpath}]

    rendered = messages[0]["content"] + " ".join(
        part.get("text", "") for part in user_content if part.get("type") == "text"
    )
    for token in EarningsWorld.REFERENCE_TOKENS:
        assert token not in rendered.lower()


# ---------------------------------------------------------------------------
# serving_geometry / strata_of
# ---------------------------------------------------------------------------


def test_serving_geometry_and_strata_of_defaults(earnings_world):
    adapter = _adapter(earnings_world)
    assert adapter.serving_geometry() == {"slots": 8, "slot_tokens": 8192, "max_tokens": 512}
    sample = adapter.load_split("discovery")[0]
    assert adapter.strata_of(sample) == "all"
