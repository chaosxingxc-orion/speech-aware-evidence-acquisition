"""``rails.encode_only_check``: the charter-mandated structural encode-only
machine check (embedder-charter adjudication section 2). This suite IS the
"run directly as a pytest" half of the check's own "importable + run as a
pytest" duality (module docstring); the other half runs inside ``rails.
probes.pemb3m_flight``'s own pre-flight gate (d).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingClient, MockEmbeddingClient
from speech_aware_evidence_acquisition.rails.encode_only_check import (
    FORBIDDEN_PAYLOAD_KEYS,
    PINNED_ENCODE_ONLY_MODULE_NAMES,
    EncodeOnlyCheckError,
    assert_client_surface_is_encode_only,
    assert_module_never_imports_generation_client,
    assert_payload_has_no_forbidden_keys,
    assert_source_has_no_forbidden_endpoint_strings,
    run_encode_only_machine_check,
)
from speech_aware_evidence_acquisition.rails.local_encoder_client import MockLocalEncoderClient
from speech_aware_evidence_acquisition.rails.probes import pemb3m_flight, pemb4r_flight


# ---------------------------------------------------------------------------
# Guard 1 -- IMPORT.
# ---------------------------------------------------------------------------


def test_assert_module_never_imports_generation_client_passes_on_a_clean_module(tmp_path):
    source = "from __future__ import annotations\n\nimport json\n"
    path = tmp_path / "clean.py"
    path.write_text(source, encoding="utf-8")
    assert_module_never_imports_generation_client(path, source=source)  # does not raise


def test_assert_module_never_imports_generation_client_refuses_a_core_client_import(tmp_path):
    source = "from speech_aware_evidence_acquisition.rails.core_client import CoreClient\n"
    path = tmp_path / "dirty.py"
    with pytest.raises(EncodeOnlyCheckError, match="core_client"):
        assert_module_never_imports_generation_client(path, source=source)


def test_assert_module_never_imports_generation_client_refuses_a_direct_frozencore_import(tmp_path):
    source = "from foo.bar import FrozenCoreClient\n"
    path = tmp_path / "dirty2.py"
    with pytest.raises(EncodeOnlyCheckError, match="FrozenCoreClient"):
        assert_module_never_imports_generation_client(path, source=source)


def test_assert_module_never_imports_generation_client_ignores_a_duck_typed_core_client_parameter(tmp_path):
    # rails.probes.pslu_flight's own established pattern: a function
    # parameter literally named core_client, used via attribute access,
    # must NEVER trip the import guard -- only an actual import statement
    # does.
    source = textwrap.dedent(
        """
        def run_supplement(*, core_client, samples):
            for sample in samples:
                core_client.complete(sample)
        """
    )
    path = tmp_path / "duck_typed.py"
    assert_module_never_imports_generation_client(path, source=source)  # does not raise


def test_pinned_modules_never_import_the_generation_client():
    for module_name in PINNED_ENCODE_ONLY_MODULE_NAMES:
        import importlib

        module = importlib.import_module(module_name)
        assert_module_never_imports_generation_client(Path(module.__file__))


# ---------------------------------------------------------------------------
# Guard 2 -- ENDPOINT STRING.
# ---------------------------------------------------------------------------


def test_assert_source_has_no_forbidden_endpoint_strings_passes_on_embedding_path(tmp_path):
    source = 'ENDPOINT = "/embedding"\n'
    path = tmp_path / "clean.py"
    assert_source_has_no_forbidden_endpoint_strings(path, source=source)  # does not raise


@pytest.mark.parametrize(
    "endpoint",
    ["/completion", "/chat/completions", "/v1/chat", "/generate", "/infill"],
)
def test_assert_source_has_no_forbidden_endpoint_strings_refuses_each_forbidden_path(tmp_path, endpoint):
    source = f'ENDPOINT = "{endpoint}"\n'
    path = tmp_path / "dirty.py"
    with pytest.raises(EncodeOnlyCheckError, match="generation-shaped"):
        assert_source_has_no_forbidden_endpoint_strings(path, source=source)


def test_pinned_modules_carry_no_forbidden_endpoint_strings():
    for module_name in PINNED_ENCODE_ONLY_MODULE_NAMES:
        import importlib

        module = importlib.import_module(module_name)
        assert_source_has_no_forbidden_endpoint_strings(Path(module.__file__))


# ---------------------------------------------------------------------------
# Guard 3 -- CLIENT SURFACE.
# ---------------------------------------------------------------------------


def test_client_surface_check_passes_on_the_real_embedding_client():
    assert_client_surface_is_encode_only(
        EmbeddingClient(base_url="http://127.0.0.1:8091", expected_media_marker="<m>", post=lambda *a: b"", get=lambda *a: b"")
    )


def test_client_surface_check_passes_on_mock_embedding_client():
    assert_client_surface_is_encode_only(MockEmbeddingClient())


def test_client_surface_check_passes_on_mock_local_encoder_client():
    assert_client_surface_is_encode_only(MockLocalEncoderClient())


def test_client_surface_check_refuses_an_object_exposing_complete():
    class _Forbidden:
        def embed_text(self, *, contact_id, text):
            return None

        def complete(self, messages):
            return "generated text"

    with pytest.raises(EncodeOnlyCheckError, match="complete"):
        assert_client_surface_is_encode_only(_Forbidden())


def test_client_surface_check_refuses_an_object_exposing_chat():
    class _Forbidden:
        def embed_audio(self, *, contact_id, audio_bytes):
            return None

        def chat(self, messages):
            return "reply"

    with pytest.raises(EncodeOnlyCheckError, match="chat"):
        assert_client_surface_is_encode_only(_Forbidden())


def test_client_surface_check_refuses_an_object_with_no_encode_shaped_method():
    class _Unrecognizable:
        def ping(self):
            return True

    with pytest.raises(EncodeOnlyCheckError, match="not a recognizable encode-only client surface"):
        assert_client_surface_is_encode_only(_Unrecognizable())


# ---------------------------------------------------------------------------
# Guard 4 -- PAYLOAD KEY.
# ---------------------------------------------------------------------------


def test_payload_key_check_passes_on_the_real_embed_text_request_shape():
    assert_payload_has_no_forbidden_keys({"content": ["hello"]})


def test_payload_key_check_passes_on_the_real_embed_audio_request_shape():
    assert_payload_has_no_forbidden_keys(
        {"content": [{"prompt_string": "<marker>", "multimodal_data": ["base64=="]}]}
    )


@pytest.mark.parametrize("key", sorted(FORBIDDEN_PAYLOAD_KEYS))
def test_payload_key_check_refuses_every_forbidden_key_at_top_level(key):
    with pytest.raises(EncodeOnlyCheckError, match="forbidden"):
        assert_payload_has_no_forbidden_keys({key: 0.7})


def test_payload_key_check_refuses_a_forbidden_key_nested_inside_a_list():
    with pytest.raises(EncodeOnlyCheckError, match="temperature"):
        assert_payload_has_no_forbidden_keys({"content": [{"temperature": 0.7}]})


def test_payload_key_check_is_case_insensitive():
    with pytest.raises(EncodeOnlyCheckError, match="forbidden"):
        assert_payload_has_no_forbidden_keys({"Temperature": 0.7})


# ---------------------------------------------------------------------------
# Sweep entry point.
# ---------------------------------------------------------------------------


def test_run_encode_only_machine_check_passes_on_the_real_pinned_modules():
    report = run_encode_only_machine_check()
    assert set(report.checked_modules) == set(PINNED_ENCODE_ONLY_MODULE_NAMES)


def test_run_encode_only_machine_check_refuses_a_module_that_imports_the_generation_client(monkeypatch, tmp_path):
    dirty = tmp_path / "dirty_module.py"
    dirty.write_text("from speech_aware_evidence_acquisition.rails.core_client import CoreClient\n", encoding="utf-8")

    import importlib
    import sys

    spec = importlib.util.spec_from_file_location("dirty_encode_only_module", dirty)
    module = importlib.util.module_from_spec(spec)
    sys.modules["dirty_encode_only_module"] = module
    try:
        spec.loader.exec_module(module)  # noqa: S102 -- trusted, in-repo test fixture
    except ImportError:
        pytest.skip("rails.core_client is not importable in this environment")
    try:
        with pytest.raises(EncodeOnlyCheckError):
            run_encode_only_machine_check(module_names=("dirty_encode_only_module",))
    finally:
        del sys.modules["dirty_encode_only_module"]


def test_pemb3m_flight_module_is_one_of_the_pinned_modules():
    assert "speech_aware_evidence_acquisition.rails.probes.pemb3m_flight" in PINNED_ENCODE_ONLY_MODULE_NAMES


def test_encode_only_check_module_itself_names_pemb3m_flight_kind_import_free():
    # Sanity: pemb3m_flight legitimately duck-types a core_client parameter
    # for its own CASCADE-T0 supplement (rails.probes.pemb3m_flight.
    # run_cascade_t0_supplement_flight) without ever importing the
    # generation-capable client -- prove the sweep still passes with that
    # function present.
    assert hasattr(pemb3m_flight, "run_cascade_t0_supplement_flight")
    report = run_encode_only_machine_check(module_names=("speech_aware_evidence_acquisition.rails.probes.pemb3m_flight",))
    assert report.checked_modules == ("speech_aware_evidence_acquisition.rails.probes.pemb3m_flight",)


def test_pemb4r_flight_module_is_one_of_the_pinned_modules():
    # P-EMB-4R (SAEA-PROBE-pemb4r-4100): coverage EXTENDED to this module
    # (this check's own logic carried unchanged, mission instruction).
    assert "speech_aware_evidence_acquisition.rails.probes.pemb4r_flight" in PINNED_ENCODE_ONLY_MODULE_NAMES


def test_encode_only_check_module_itself_names_pemb4r_flight_kind_import_free():
    # Sanity: pemb4r_flight legitimately duck-types a core_client parameter
    # for its own C-DECODE arm (rails.probes.pemb4r_flight.
    # run_c_decode_flight) without ever importing the generation-capable
    # client -- prove the sweep still passes with that function present.
    assert hasattr(pemb4r_flight, "run_c_decode_flight")
    report = run_encode_only_machine_check(module_names=("speech_aware_evidence_acquisition.rails.probes.pemb4r_flight",))
    assert report.checked_modules == ("speech_aware_evidence_acquisition.rails.probes.pemb4r_flight",)


def test_run_encode_only_machine_check_refuses_a_module_with_no_file(monkeypatch):
    class _FakeModule:
        __file__ = None

    import importlib

    import speech_aware_evidence_acquisition.rails.encode_only_check as encode_only_check

    original_import_module = importlib.import_module
    monkeypatch.setattr(
        importlib, "import_module", lambda name: _FakeModule() if name == "fake.module" else original_import_module(name)
    )
    with pytest.raises(EncodeOnlyCheckError, match="__file__"):
        encode_only_check._module_file_path("fake.module")
