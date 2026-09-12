"""Pinned speech-embedding recipe: original spans, masks and bounded inputs."""

from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from speech_aware_evidence_acquisition.core.speech_embedding import (
    SpeechEmbeddingError,
    read_audio_span,
    render,
    encode,
)


def test_audio_span_covers_exact_original_frames_before_resampling(tmp_path):
    path = tmp_path / "synthetic.wav"
    waveform = np.linspace(-0.5, 0.5, 2400, dtype="float32")
    sf.write(path, waveform, 24000, subtype="FLOAT")
    source = {
        "media_path": str(path),
        "start_frame": 300,
        "end_frame": 2100,
        "source_frames": 2400,
        "source_sample_rate_hz": 24000,
    }
    actual = read_audio_span(source)
    import librosa

    expected = librosa.resample(waveform[300:2100], orig_sr=24000, target_sr=16000)
    assert actual.dtype == np.float32
    assert np.array_equal(actual, expected)
    source["source_frames"] = 2500
    with pytest.raises(SpeechEmbeddingError, match="geometry"):
        read_audio_span(source)


def test_chat_template_keeps_the_shipped_query_message():
    recorded = []
    processor = SimpleNamespace(
        apply_chat_template=lambda *a, **kw: recorded.append((a, kw)) or "rendered"
    )
    content = [{"type": "text", "text": "query: "}, {"type": "audio"}]
    assert render(processor, "pinned-template", content) == "rendered"
    assert recorded == [
        (
            ([{"role": "user", "content": content}],),
            {
                "chat_template": "pinned-template",
                "tokenize": False,
                "add_generation_prompt": False,
            },
        )
    ]


def test_attention_mask_mean_pooling_and_l2_normalization_use_real_cpu_tensors():
    import torch

    class Processor:
        def __call__(self, **kwargs):
            assert kwargs == {
                "text": ["one", "two"],
                "return_tensors": "pt",
                "padding": True,
            }
            return {"attention_mask": torch.tensor([[1, 1, 0], [1, 0, 0]])}

    class Model:
        def __call__(self, **kwargs):
            assert kwargs["output_hidden_states"] is True
            return SimpleNamespace(
                hidden_states=[
                    torch.tensor(
                        [
                            [[3.0, 0.0], [0.0, 4.0], [100.0, 100.0]],
                            [[0.0, 2.0], [100.0, 100.0], [100.0, 100.0]],
                        ]
                    )
                ]
            )

    assert np.allclose(
        encode(Processor(), Model(), ["one", "two"], None, device="cpu"),
        [[0.6, 0.8], [0.0, 1.0]],
    )


@pytest.mark.parametrize(
    "audio",
    [
        [np.zeros(16001, dtype="float32")],
        [np.array([float("nan")], dtype="float32")],
        [np.zeros((2, 2), dtype="float32")],
        [np.zeros(1, dtype="float32"), np.zeros(1, dtype="float32")],
    ],
)
def test_invalid_audio_refuses_before_processor_or_forward(audio):
    def fail(**_):
        pytest.fail("invalid audio reached the model")

    with pytest.raises(SpeechEmbeddingError):
        encode(fail, fail, ["query"], audio, device="cpu", max_audio_samples=16000)


def test_historical_entry_reexports_the_common_recipe():
    import runpy
    from pathlib import Path
    from speech_aware_evidence_acquisition.core import speech_embedding

    repo = Path(__file__).resolve().parents[2]
    namespace = runpy.run_path(
        str(repo / "scripts/slurp_mf7b_nemotron_embedding_pass.py")
    )
    for name in ["load_stack", "render", "encode"]:
        assert namespace[name] is getattr(speech_embedding, name)


def test_local_stack_reuses_pinned_loader_template_and_pooling(tmp_path, monkeypatch):
    import json
    import sys
    from speech_aware_evidence_acquisition.core.speech_embedding import load_stack

    (tmp_path / "additional_chat_templates").mkdir()
    (tmp_path / "additional_chat_templates/sentence_transformers.jinja").write_text(
        "pinned"
    )
    (tmp_path / "1_Pooling").mkdir()
    (tmp_path / "1_Pooling/config.json").write_text(
        json.dumps(
            {
                "pooling_mode": "mean",
                "include_prompt": True,
                "embedding_dimension": 2048,
            }
        )
    )
    calls = []

    class Model:
        def to(self, device):
            assert device == "cuda"
            return self

        def eval(self):
            return self

    processor = object()
    model = Model()

    def processor_load(path, **kwargs):
        calls.append(("processor", path, kwargs))
        return processor

    def model_load(path, **kwargs):
        calls.append(("model", path, kwargs))
        return model

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoProcessor=SimpleNamespace(from_pretrained=processor_load),
            AutoModel=SimpleNamespace(from_pretrained=model_load),
        ),
    )
    assert load_stack(tmp_path, local_files_only=True) == (processor, model, "pinned")
    assert all(call[2]["local_files_only"] is True for call in calls)
    assert calls[1][2]["attn_implementation"] == "sdpa"


@pytest.mark.parametrize(
    "audio_frames,token_count,error",
    [
        (3, 4, "complete frame coverage"),
        (4, 5, "token bound"),
        (4, 4, None),
    ],
)
def test_audio_frontend_coverage_and_token_bound_are_checked_before_forward(
    audio_frames, token_count, error
):
    import torch

    class Processor:
        feature_extractor = SimpleNamespace(hop_length=160)

        def __call__(self, **kwargs):
            assert kwargs["sampling_rate"] == 16000
            assert kwargs["audio_kwargs"] == {"max_length": 1000, "truncation": False}
            return {
                "feature_attention_mask": torch.ones((1, audio_frames)),
                "attention_mask": torch.ones((1, token_count)),
            }

    calls = []

    def model(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(hidden_states=[torch.ones((1, token_count, 2))])

    args = (Processor(), model, ["query"], [np.zeros(640, dtype="float32")])
    forward_events = []
    options = dict(
        forward_event=forward_events.append,
        device="cpu",
        max_audio_samples=1000,
        require_complete_audio=True,
        max_sequence_tokens=4,
    )
    if error:
        with pytest.raises(SpeechEmbeddingError, match=error):
            encode(*args, **options)
        assert not calls
        assert forward_events == []
    else:
        assert np.allclose(encode(*args, **options), [[2**-0.5, 2**-0.5]])
        assert len(calls) == 1
        assert forward_events == ["encoder_forward_started", "encoder_forward_finished"]
