"""The Thinking-core Fold B speech-packet preparation (owner decision 266-E): model-free tests.

The live geometry is the GPU encoder pass (run id ...-PACKETS-GPU-V1, re-registration of 2026-10-11); the CPU sidecar geometry (run id
...-PACKETS-V1, stopped after 50 rows) is superseded and exercised only for the record behind ``--allow-cpu``.

Covers the dry-run plan, the pin and root refusals, the exposure-row countersignature gate, the receipt schemas, the proof that the Instruct
driver is untouched, the end-to-end ENCODE and PROMOTE flow against a fake sidecar (smoke without promotion, Fold B with it, then the pin
step), the promotion receipt shape against the Instruct one, and the chain wrapper's guards against a stubbed host. No server, GPU, encoder,
network or governed media is touched: every file is written under tmp_path and every process boundary is replaced by a fake.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "slurp_fold_preprocess_thinking.py"
INSTRUCT_SCRIPT = REPO / "scripts" / "slurp_evo_fold_preprocess.py"
WRAPPER = REPO / "scripts" / "flights" / "direct" / "direct_fb_packets.sh"
ENTRY = REPO / "scripts" / "flights" / "direct" / "direct_fb_packets_task_entry.sh"
GPU_CHAIN = REPO / "scripts" / "flights" / "direct" / "direct_fb_packets_gpu.sh"
GPU_ENTRY = REPO / "scripts" / "flights" / "direct" / "direct_fb_packets_gpu_task_entry.sh"

_SRC = str(REPO / "src")
_existing = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing if _existing else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

_SPEC = importlib.util.spec_from_file_location("slurp_fold_preprocess_thinking_under_test", SCRIPT)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = module
_SPEC.loader.exec_module(module)
evo, fam, pins_mod = module.evo, module.fam, module.pins_mod
REAL_GPU_STATE = module.gpu_state
FREE_GPU_STATE = {"resident_sessions": [], "serving_port_listening": False, "gpu_memory_used_mib": 512, "gpu_free": True, "findings": []}

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_packet_promotion_receipt,
)

MAIN_SHA = "afdaeff6f23c740429aadb3fa180f9d53b78278fe0d331b594b0b71bd9bf4835"
MMPROJ_SHA = "57b7240fb3d8941f5969d760c694a754cbe74f7db428605d63e1dacceda98b38"
SPLIT = "ab" * 32
LEDGER_HEADER = (
    "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash "
    "| consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |"
)
DRAFT_NOTES = "REGISTERED (DRAFT, root countersignature pending) 2026-10-11; a placeholder row, not countersigned with the arms."
SIGNED_NOTES = "REGISTERED BEFORE CONTACT (root countersigned 2026-10-12T00:00:00Z by root flight operations on the coordinator's brief)."


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fake_lock(tmp: Path, *, main_sha: str = MAIN_SHA, status: str = "COMPLETE") -> Path:
    revision = (f"x; {pins_mod.MAIN_NAME} {main_sha} ({pins_mod.MAIN_BYTES} bytes); "
                f"{pins_mod.MMPROJ_NAME} {MMPROJ_SHA} ({pins_mod.MMPROJ_BYTES} bytes)")
    path = tmp / "lock.json"
    path.write_text(json.dumps({"models": [{"name": pins_mod.LOCK_KEY, "status": status, "revision": revision}]}), encoding="utf-8")
    return path


def _local_receipts(tmp: Path, monkeypatch, *, main_sha: str = MAIN_SHA) -> None:
    (tmp / "main.sha256").write_text(main_sha + "  main\n", encoding="utf-8")
    (tmp / "mmproj.sha256").write_text(MMPROJ_SHA + "  mmproj\n", encoding="utf-8")
    monkeypatch.setattr(pins_mod, "LOCAL_MAIN_RECEIPT", tmp / "main.sha256")
    monkeypatch.setattr(pins_mod, "LOCAL_MMPROJ_RECEIPT", tmp / "mmproj.sha256")


def _ledger(tmp: Path, *, notes: str, consumed: str = "no", calls: str = "1084", seconds: str = "3165", split: str = SPLIT,
            profile: str = "bounded-discovery-probe", row_id: str | None = None, gpu: str = "1.0") -> Path:
    cells = ["2026-10-11T18:00:00+00:00", row_id or module.RUN_ID, profile, "scope", "model", "slurp TRAIN Fold B 1,080", "discovery", split,
             consumed, calls, seconds, gpu, "inherited", "artifact", notes]
    path = tmp / "ledger.md"
    path.write_text("\n".join([LEDGER_HEADER, "|" + " --- |" * 15, "| " + " | ".join(cells) + " |"]) + "\n", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path, monkeypatch):
    """No test reads the host's real attempt store or the host's serving/GPU state; World overrides the root with its own."""

    monkeypatch.setattr(evo, "data_root", lambda: tmp_path / "isolated-data")
    monkeypatch.setattr(module, "gpu_state", lambda data_root: dict(FREE_GPU_STATE))
    yield
    module.apply_geometry("gpu")          # a test that switched the geometry must not leak it


# ------------------------------------------------------------------------------------------------ the real registration


def _args(**overrides):
    base = dict(roster="thinking-fold-b", workers=None, promote_workers=8, attempt_id=None, plan_calls=None, plan_speech_seconds=None,
                output=None, promote_only=False, write=False, recovery_of=None, max_fold_seconds=3000.0)
    base.update(overrides)
    return types.SimpleNamespace(**base)


def test_the_registered_composition_is_the_thinking_one_and_never_the_instruct_roots():
    composed, values = module.compose_values()
    module.check_config_identity(values)
    assert values["feature_root"] == "/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6"
    assert values["legacy_cache_dir"] == "/home/chao/feat-cache/slurp-thinking-gpu-q4km"
    assert values["runtime_receipt"] == "receipts/runtime-q4km-thinking-preprocess-gpu.json" and values["server_args"][:4] == ["-c", "16384", "-np", "1"]
    assert values["feature_root"] != str(evo.DEFAULT_FEATURE_ROOT) and values["legacy_cache_dir"] != str(evo.DEFAULT_LEGACY_CACHE_DIR)
    assert values["model_lock_key"] == pins_mod.LOCK_KEY and values["experiment_id"] == fam.PACKETS_ROW_ID
    assert values["execution_profile"] == "bounded-discovery-probe" and values["split_role"] == "discovery"
    assert values["promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT == f"{values['feature_root']}/EVO-FOLD-B-V2-promotion.json"
    assert evo._server_slots(values, module.SIDECAR_FRAGMENT) == 1 and composed.config_hash


def test_the_smoke_is_the_registered_prefix_of_the_fold_b_view():
    _, values = module.compose_values()
    ids = module.smoke_ids()
    assert len(ids) == fam.SMOKE_ROWS == 4
    assert [i["sample_id"] for i in module.select_items(values, module.ROSTERS["thinking-smoke-4"], ids)] == ids
    assert len(module.select_items(values, module.ROSTERS["thinking-fold-b"], ids)) == fam.ROWS
    with pytest.raises(SystemExit, match="not the registered smoke rows"):
        module.select_items(values, module.ROSTERS["thinking-fold-b"], list(reversed(ids)))


@pytest.mark.parametrize("roster,rows", [("thinking-smoke-4", 4), ("thinking-fold-b", 1080)])
def test_dry_run_prints_the_plan_without_any_encoder_call_or_media_read(roster, rows, tmp_path, monkeypatch, capsys):
    _local_receipts(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "root_problems", lambda *a, **k: [])         # the host's real roots are empty today; do not depend on it
    monkeypatch.setattr(module, "legacy_cache_findings", lambda *a, **k: pytest.fail("a dry-run must not open any media file"))
    monkeypatch.setattr(evo, "start_session", lambda **k: pytest.fail("a dry-run must not start a sidecar"))
    out = tmp_path / "plan.json"
    rc = module.dry_run(_args(roster=roster, output=out), lock_path=_fake_lock(tmp_path), ledger_path=REPO / "docs" / "exposure-ledger.md")
    plan = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0 and plan["schema"] == module.PLAN_SCHEMA and plan["rows"] == rows
    assert plan["encoder_calls"] == 0 and plan["contacts"] == 0 and plan["refusals"] == []
    assert plan["roots"]["packet_root"].endswith("slurp-q4km-packets-thinking-gpu-afdaeff6")
    assert plan["device"] == "gpu" and plan["geometry"] == "gpu" and plan["sidecar"]["encode_workers"] == 1
    assert plan["promotes"] is (roster == "thinking-fold-b") and (plan["roots"]["promotion_receipt"] is not None) is plan["promotes"]
    assert plan["pins"]["decoder"]["sha256"] == MAIN_SHA and plan["pins"]["mmproj"]["sha256"] == MMPROJ_SHA
    assert plan["pins"]["llama_cpp_build_commit"] and plan["sidecar"]["slots"] == 1 and plan["sidecar"]["port"] == 8081
    assert plan["row_total"] == {"calls": 1084, "speech_audio_seconds": 3165, "gpu_hours": 1.0}
    assert plan["declared_plan"]["calls_ceiling"] == rows and plan["declared_plan"]["gpu_hours"] == 1.0
    assert plan["ledger"]["present"] is True and plan["ledger"]["problems"] == []               # the registered row matches the numbers, gpu hours included


def test_the_dry_run_refuses_a_populated_packet_root(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch)
    root = tmp_path / "packets"
    (root / "slurp" / "train").mkdir(parents=True)
    original = module.root_problems
    monkeypatch.setattr(module, "root_problems", lambda roster, **kw: original(roster, **{**kw, "packet_root": root}))
    rc = module.dry_run(_args(output=tmp_path / "plan.json"), lock_path=_fake_lock(tmp_path), ledger_path=REPO / "docs" / "exposure-ledger.md")
    plan = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert rc == 3 and any("exists and is not empty" in r for r in plan["refusals"])


def test_the_dry_run_refuses_a_workers_count_above_the_sidecars_slots(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="exceeds the 1 slots"):
        module.dry_run(_args(workers=8), lock_path=_fake_lock(tmp_path), ledger_path=REPO / "docs" / "exposure-ledger.md")


# ------------------------------------------------------------------------------------------------------ pin refusals


def test_pins_that_match_the_lock_and_the_committed_runtime_receipt_pass(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch)
    pins, receipt = module.verify_pins(lock_path=_fake_lock(tmp_path))
    assert pins["main"]["sha256"] == MAIN_SHA and pins["mmproj"]["sha256"] == MMPROJ_SHA
    assert receipt["gguf_files"] == [pins["main"], pins["mmproj"]] and receipt["llama_cpp"]["build_commit"]


def test_a_local_hash_that_disagrees_with_the_lock_refuses(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch, main_sha="1" * 64)
    with pytest.raises(SystemExit, match="does not match the lock entry"):
        module.verify_pins(lock_path=_fake_lock(tmp_path))


def test_a_lock_entry_that_is_not_complete_refuses(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="not COMPLETE"):
        module.verify_pins(lock_path=_fake_lock(tmp_path, status="PENDING"))


def test_a_runtime_receipt_that_binds_other_files_refuses(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch)
    receipt = json.loads((REPO / "docs" / module.RUNTIME_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    receipt["gguf_files"][0]["sha256"] = "2" * 64
    bad = tmp_path / "runtime.json"
    bad.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(SystemExit, match="differ from the lock-verified Thinking pins"):
        module.verify_pins(lock_path=_fake_lock(tmp_path), runtime_receipt_path=bad)
    receipt["gguf_files"][0]["sha256"] = MAIN_SHA
    receipt["model_lock_key"] = "qwen3-omni-30b-a3b-instruct-gguf-q4km"
    bad.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(SystemExit, match="names model"):
        module.verify_pins(lock_path=_fake_lock(tmp_path), runtime_receipt_path=bad)


def test_config_drift_in_a_root_or_the_split_refuses(monkeypatch):
    _, values = module.compose_values()
    for key, bad in (("feature_root", str(evo.DEFAULT_FEATURE_ROOT)), ("legacy_cache_dir", str(evo.DEFAULT_LEGACY_CACHE_DIR)),
                     ("promotion_receipt", "/home/chao/x.json"), ("split_identity_hash", "0" * 64), ("model_lock_key", "other")):
        with pytest.raises(SystemExit):
            module.check_config_identity({**values, key: bad})


# ------------------------------------------------------------------------------------------------------ root refusals


def test_root_problems_refuse_a_non_empty_packet_root_an_existing_receipt_and_a_dirty_smoke_cache(tmp_path):
    root, cache, receipt = tmp_path / "packets", tmp_path / "cache", tmp_path / "packets" / "EVO-FOLD-B-V2-promotion.json"
    fold, smoke = module.ROSTERS["thinking-fold-b"], module.ROSTERS["thinking-smoke-4"]
    kw = dict(packet_root=root, legacy_cache=cache, promotion_receipt=receipt)
    assert module.root_problems(fold, **kw) == [] and module.root_problems(smoke, **kw) == []       # absent roots are fine
    root.mkdir()
    assert module.root_problems(fold, **kw) == []                                                     # an EMPTY root is fine
    (root / "stray").write_text("x", encoding="utf-8")
    assert any("not empty" in p for p in module.root_problems(fold, **kw))
    assert module.root_problems(fold, allow_populated_root=True, **kw) == []                          # promote-only continues a partial root
    receipt.write_text("{}", encoding="utf-8")
    assert any("promotion receipt already exists" in p for p in module.root_problems(fold, allow_populated_root=True, **kw))
    cache.mkdir()
    (cache / "1_o0.feat").write_bytes(b"x")
    assert any("empty legacy cache" in p for p in module.root_problems(smoke, **kw))
    assert not any("empty legacy cache" in p for p in module.root_problems(fold, **kw))


def test_the_real_host_roots_are_not_prepared_yet_or_the_receipt_is_pinned():
    # Guards this test file against being run after the packets exist: then the baselines carry a real sha, not the sentinel.
    baselines = [(REPO / b).read_text(encoding="utf-8") for b in module.BASELINES]
    assert all(('"speech_packet_promotion_receipt_sha256": "%s"' % fam.UNPINNED_SHA) in t or re.search(
        r'"speech_packet_promotion_receipt_sha256": "[0-9a-f]{64}"', t) for t in baselines)


# ---------------------------------------------------------------------------------------------------------- ledger


def test_the_real_ledger_row_is_present_and_a_draft_today():
    _, values = module.compose_values()
    state = module.ledger_state(REPO / "docs" / "exposure-ledger.md", split_identity_hash=str(values["split_identity_hash"]))
    assert state["present"] is True and state["problems"] == []
    assert state["countersigned"] is False or state["draft"] is False       # False while DRAFT; True only after the root countersignature


@pytest.mark.parametrize("kwargs,expect_signed,needle", [
    ({"notes": SIGNED_NOTES}, True, None),
    ({"notes": DRAFT_NOTES}, False, None),
    ({"notes": "REGISTERED BEFORE CONTACT (no signature words)"}, False, None),
    ({"notes": SIGNED_NOTES, "consumed": "yes"}, False, "consumed"),
    ({"notes": SIGNED_NOTES, "calls": "1000"}, False, "budgets"),
    ({"notes": SIGNED_NOTES, "split": "cd" * 32}, False, "split role / identity"),
    ({"notes": SIGNED_NOTES, "profile": "model-free-check"}, False, "execution profile"),
])
def test_ledger_state_requires_a_root_countersignature_and_the_registered_numbers(tmp_path, kwargs, expect_signed, needle):
    state = module.ledger_state(_ledger(tmp_path, **kwargs), split_identity_hash=SPLIT)
    assert state["countersigned"] is expect_signed
    if needle:
        assert any(needle in problem for problem in state["problems"])


def test_an_absent_row_is_reported_and_a_draft_row_refuses_the_run(tmp_path, monkeypatch):
    absent = module.ledger_state(_ledger(tmp_path, notes=SIGNED_NOTES, row_id="OTHER-ROW"), split_identity_hash=SPLIT)
    assert absent["present"] is False and "need exactly one" in absent["problems"][0]
    _local_receipts(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "root_problems", lambda *a, **k: [])
    with pytest.raises(SystemExit, match="not root-countersigned"):
        module.run(_args(), lock_path=_fake_lock(tmp_path), ledger_path=_ledger(tmp_path, notes=DRAFT_NOTES, split=str(module.compose_values()[1]["split_identity_hash"])))


def test_check_ledger_exits_non_zero_for_a_draft_and_zero_for_a_countersigned_row(tmp_path, capsys):
    _, values = module.compose_values()
    assert module.check_ledger(_args(), ledger_path=_ledger(tmp_path, notes=DRAFT_NOTES, split=str(values["split_identity_hash"]))) == 4
    assert json.loads(capsys.readouterr().out)["row"] == module.RUN_ID
    assert module.check_ledger(_args(), ledger_path=_ledger(tmp_path, notes=SIGNED_NOTES, split=str(values["split_identity_hash"]))) == 0
    capsys.readouterr()
    assert module.check_ledger(_args(), ledger_path=_ledger(tmp_path, notes=SIGNED_NOTES, split=str(values["split_identity_hash"]), gpu="0.0")) == 4


# ------------------------------------------------------------------------------------------------- Instruct path unchanged


def test_the_instruct_driver_is_loaded_not_modified_and_keeps_its_own_state():
    raw = INSTRUCT_SCRIPT.read_bytes().replace(b"\r\n", b"\n")
    # Deliberate pin: the Thinking driver is a sibling that reuses this file's helpers. A change to the Instruct driver must be a
    # conscious act that re-proves the sealed Instruct plans and updates this digest in the same change.
    assert hashlib.sha256(raw).hexdigest() == "3acdda4cbeff2c1340f64583a6c5edcd2be392768aa1a654b1e6ed5c33683c3f"
    assert sorted(evo.PREPROCESS_ROSTERS) == ["dev2000-added", "devel-remainder", "devel-remainder-np8-equivalence-4", "fold-a", "fold-b",
                                              "stage3-construction-r01", "stage3-construction-r01-recovery", "test-full", "test-sample-3010"]
    assert evo.RUNTIME_RECEIPT_RELPATH == "receipts/runtime-q4km-preprocess.json" and evo.MODEL_FRAGMENT == "q4km-preprocess-featcache-cpu-sidecar"
    assert str(evo.DEFAULT_FEATURE_ROOT).endswith("slurp-q4km-packets-04ccc72a")
    assert module.RUNTIME_RECEIPT_RELPATH != evo.RUNTIME_RECEIPT_RELPATH and module.SIDECAR_FRAGMENT != evo.MODEL_FRAGMENT


def test_the_instruct_fold_plans_compose_exactly_as_the_sealed_driver_composes_them():
    for key in ("fold-a", "fold-b"):
        spec = evo.PREPROCESS_ROSTERS[key]
        composed = evo.compose(evo.REPO, spec.sidecar_fragment, spec.dataset_fragment, evo.BASELINE_FRAGMENT, spec.experiment_fragment)
        assert composed.values["feature_root"] == str(evo.DEFAULT_FEATURE_ROOT)
        assert composed.values["runtime_receipt"] == "receipts/runtime-q4km-preprocess.json"
        assert composed.values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf-q4km"


# ------------------------------------------------------------------------------------------- the end-to-end flow (fakes)


class World:
    """A six-row synthetic Fold B under tmp_path with every process boundary replaced by a fake."""

    ROWS = 6
    SMOKE = 2

    def __init__(self, tmp: Path, monkeypatch):
        self.tmp = tmp
        self.data = tmp / "data"
        self.packet_root = tmp / "packets"
        self.cache = tmp / "legacy"
        self.receipt = self.packet_root / "EVO-FOLD-B-V2-promotion.json"
        self.contacts: list[str] = []
        self.sessions: list[dict] = []
        self.plans: list[dict] = []
        self._lock = threading.Lock()
        self.drop_features = False        # a server that answers but caches nothing
        self.server_creates_dirs = False  # the patched llama.cpp server does NOT create its cache directory
        items = []
        for index in range(self.ROWS):
            rel = f"datasets/slurp/audio-{index}.flac"
            raw = (b"audio-bytes-%d-" % index) * 40
            (self.data / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.data / rel).write_bytes(raw)
            items.append({"sample_id": f"slurp:train:{index:06d}:audio-{index}", "media_relpath": rel, "audio_sha256": _sha(raw),
                          "audio_seconds": 2.0 + index})
        self.items = items
        self.pins = {"main": {"bytes": 1, "path": "models/x/decoder.gguf", "sha256": MAIN_SHA},
                     "mmproj": {"bytes": 2, "path": "models/x/mmproj-x.gguf", "sha256": MMPROJ_SHA}}
        self.runtime = {"gguf_files": [self.pins["main"], self.pins["mmproj"]], "role": "preprocess", "model_lock_key": pins_mod.LOCK_KEY,
                        "llama_cpp": {"build_commit": "c" * 40, "binary_sha256": "d" * 64, "reported_build": "version: 8 (c)"}}
        self.values = {"schema": "saea-speech-native-runtime-view-v1", "items": items, "count": len(items), "split_identity_hash": SPLIT,
                       "split_role": "discovery", "execution_profile": "bounded-discovery-probe", "experiment_id": module.RUN_ID,
                       "model_lock_key": pins_mod.LOCK_KEY, "server_args": ["-np", "4", "-ngl", "0"],
                       "server_env": {"LLAMA_MTMD_FEAT_CACHE_DIR": str(self.cache)}, "transport": "fake", "runtime_view_sha256": "e" * 64,
                       "fold": "SLURP-EVO-FOLD-B-V2"}
        composed = types.SimpleNamespace(values=self.values, config_hash="f" * 64)
        world = self

        class Client:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def complete(self, messages, decoding_params):
                relpath = messages[1]["content"][0]["media_relpath"]
                world.contacts.append(relpath)
                world.count(self.kwargs["run_dir"].name, (world.data / relpath).stat().st_size)
                if world.drop_features or not (world.cache.is_dir() or world.server_creates_dirs):
                    return
                key = evo.legacy_audio_feature_cache_key((world.data / relpath).read_bytes())
                world.cache.mkdir(parents=True, exist_ok=True)
                payload = struct.pack("<QQ", 3, 2048) + bytes([int(key[-2:]) % 251]) * (3 * 2048 * 4)
                (world.cache / f"{key}_o0.feat").write_bytes(payload)

            def close(self):
                return {"trace_manifest_hash": None, "cost": {}}

        class Plan:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                world.plans.append(kwargs)

            def validate(self, source_root=None):
                return self

        class Gate:
            @staticmethod
            def for_study_repo(*a, **k):
                world.gate_kwargs = k
                return Gate()

            def verify_media_identity(self, *a):
                return None

            def assert_model_touch_allowed(self, plan):
                return "a" * 64

        def start_session(**kwargs):
            world.sessions.append(kwargs)
            world.open_attempt(kwargs["session_id"].split(module.RUN_ID + "-", 1)[1].removesuffix("-gpu-encoder").removesuffix("-cpu-sidecar"))
            return types.SimpleNamespace(pid=4242, port=8081, session_id=kwargs["session_id"],
                                         as_json=lambda: {"session_id": kwargs["session_id"], "pid": 4242})

        binding = types.SimpleNamespace(
            media_relpaths={i["sample_id"]: i["media_relpath"] for i in items},
            sample_facts={i["sample_id"]: (i["audio_sha256"],) for i in items},
            allowed_sample_ids={i["sample_id"] for i in items})
        monkeypatch.setattr(module, "PACKET_ROOT", self.packet_root)
        monkeypatch.setattr(module, "LEGACY_CACHE", self.cache)
        monkeypatch.setattr(module, "PROMOTION_RECEIPT", self.receipt)
        monkeypatch.setattr(module, "compose_values", lambda repo=module.REPO: (composed, self.values))
        monkeypatch.setattr(module, "check_config_identity", lambda *a, **k: None)
        monkeypatch.setattr(module, "verify_pins", lambda **k: (self.pins, self.runtime))
        monkeypatch.setattr(module, "smoke_ids", lambda repo=module.REPO: [i["sample_id"] for i in items[: self.SMOKE]])
        monkeypatch.setitem(module.ROSTERS, "thinking-smoke-4", module.ROSTERS["thinking-smoke-4"]._replace(rows=self.SMOKE, plan_calls=self.SMOKE))
        monkeypatch.setattr(evo, "data_root", lambda: self.data)
        monkeypatch.setattr(evo, "load_lock", lambda path: {})
        monkeypatch.setattr(evo, "asset_dir", lambda *a: self.data)
        monkeypatch.setattr(evo, "build_payload_binding", lambda **k: binding)
        monkeypatch.setattr(evo, "FrozenCoreGate", Gate)
        monkeypatch.setattr(evo, "ExecutionPlan", Plan)
        monkeypatch.setattr(evo, "FrozenCoreClient", Client)
        monkeypatch.setattr(evo, "start_session", start_session)
        monkeypatch.setattr(evo, "stop_session", lambda *a, **k: {"termination_signal": "SIGTERM", "forced": False})
        monkeypatch.setattr(evo, "TRANSPORTS", types.SimpleNamespace(resolve=lambda name: (lambda *a, **k: object())))
        monkeypatch.setattr(evo, "d1_media_supplement_relpath", lambda values: None)
        monkeypatch.setattr(evo, "d1_media_supplement_sha256", lambda values: None)
        self.ledger = _ledger(tmp, notes=SIGNED_NOTES)
        self.lock = tmp / "lock.json"
        monkeypatch.setattr(evo, "data_root", lambda: self.data)

    def _record_path(self, attempt_id: str) -> Path:
        return self.data / "attempts" / module.RUN_ID / f"{attempt_id}.json"

    def open_attempt(self, attempt_id: str) -> None:
        """What the attempt store does when the plan is reserved: an OPENED record with zero actuals."""

        path = self._record_path(attempt_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"attempt_id": attempt_id, "state": "OPENED", "actual": {"calls": 0, "audio_seconds": 0.0}}), encoding="utf-8")

    def count(self, attempt_id: str, size: int) -> None:
      with self._lock:
        record = json.loads(self._record_path(attempt_id).read_text(encoding="utf-8"))
        record["actual"]["calls"] += 1
        record["actual"]["audio_seconds"] += 1.0 + size % 3
        self._record_path(attempt_id).write_text(json.dumps(record), encoding="utf-8")

    def sync_ledger(self, **kwargs) -> Path:
        """Register the row at the totals the attempt store implies (the coordinator's re-registration)."""

        history, _ = module.attempt_history(self.data)
        calls, seconds = module.expected_row_totals(self.values, module.summarize_history(history))
        self.ledger = _ledger(self.tmp, notes=SIGNED_NOTES, calls=str(calls), seconds=str(seconds), **kwargs)
        return self.ledger

    def run(self, roster: str, **overrides):
        self.sync_ledger()
        out = self.tmp / f"report-{roster}.json"
        args = _args(roster=roster, workers=2, promote_workers=2, output=out, **overrides)
        rc = module.run(args, repo=REPO, lock_path=self.lock, ledger_path=self.ledger)
        return rc, json.loads(out.read_text(encoding="utf-8"))

    def encoder_receipt(self, attempt: str) -> dict:
        return json.loads((self.data / "runs" / module.RUN_ID / attempt / module.ENCODER_RECEIPT_NAME).read_text(encoding="utf-8"))


@pytest.fixture()
def world(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def test_the_smoke_encodes_into_the_legacy_cache_only_and_promotes_nothing(world):
    rc, report = world.run("thinking-smoke-4")
    assert rc == 0 and world.contacts == [i["media_relpath"] for i in world.items[:2]]
    assert not world.packet_root.exists() and not world.receipt.exists()                 # the packet root stays empty
    assert len(list(world.cache.glob("*.feat"))) == 2
    assert report["mode"] == "encode-only" and report["promotion_receipt"] is None and report["contacts"] == 2
    assert [f["kind"] for f in report["files"]] == ["legacy-cache-entry"] * 2
    assert all(len(c["file_sha256"]) == 64 for f in report["files"] for c in f["chunks"])
    assert len(world.sessions) == 1 and world.sessions[0]["extra_env"] == world.values["server_env"]
    assert world.sessions[0]["port"] == 8081 and world.sessions[0]["role"] == "preprocess"
    assert world.encoder_receipt("attempt-packets-thinking-gpu-smoke-4-v1")["roster"] == "thinking-smoke-4"


def test_the_fold_b_pass_skips_warm_rows_promotes_all_rows_and_writes_both_receipts(world):
    world.run("thinking-smoke-4")
    world.contacts.clear()
    rc, report = world.run("thinking-fold-b")
    assert rc == 0
    assert world.contacts == [i["media_relpath"] for i in world.items[2:]]               # the smoke's two warm rows are not re-contacted
    assert report["contacts"] == 4 and report["skipped_warm_rows"] == 2 and report["rows"] == 6
    assert report["mode"] == PROMOTE_MODE_ENCODE and report["llama_cpp"]["build_commit"] == "c" * 40
    assert report["decoder_gguf_sha256"] == MAIN_SHA and report["mmproj_sha256"] == MMPROJ_SHA
    assert report["split_identity_hash"] == SPLIT and report["encode_workers"] == 2 and report["file_count"] == 6
    assert all(f["kind"] == "packet" and len(f["packet_sha256"]) == 64 and f["chunks"][0]["feature_sha256"] for f in report["files"])
    document = load_speech_packet_promotion_receipt(
        world.receipt, expected_sha256=_sha(world.receipt.read_bytes()), expected_feature_root=world.packet_root,
        expected_dataset_runtime_view_sha256="e" * 64)
    assert document["count"] == 6 and document["encode_contacts"] == 4 and document["mode"] == PROMOTE_MODE_ENCODE
    assert report["promotion_receipt_sha256"] == _sha(world.receipt.read_bytes())
    assert document["runtime_receipt_sha256"] == evo.canonical_sha256(world.runtime)


def test_a_second_fold_b_pass_refuses_because_the_root_is_no_longer_empty(world):
    world.run("thinking-smoke-4")
    world.run("thinking-fold-b")
    with pytest.raises(SystemExit, match="REFUSED"):
        world.run("thinking-fold-b", attempt_id="attempt-again")


def test_a_foreign_legacy_cache_entry_refuses_before_any_contact(world):
    world.cache.mkdir(parents=True)
    (world.cache / "123456789_o0.feat").write_bytes(b"stale")
    with pytest.raises(SystemExit, match="not roster rows"):
        world.run("thinking-fold-b")
    assert world.contacts == [] and world.sessions == []


def test_a_failed_contact_refuses_to_promote_a_partial_cache(world, monkeypatch):
    original = evo.FrozenCoreClient

    class Flaky(original):
        def complete(self, messages, decoding_params):
            if messages[1]["content"][0]["media_relpath"].endswith("audio-3.flac"):
                raise RuntimeError("sidecar lost")
            return super().complete(messages, decoding_params)

    monkeypatch.setattr(evo, "FrozenCoreClient", Flaky)
    with pytest.raises(SystemExit, match="refusing to promote a partial cache"):
        world.run("thinking-fold-b")
    assert not world.receipt.exists()


def test_promote_only_needs_a_new_attempt_id_and_a_fully_warm_cache(world):
    with pytest.raises(SystemExit, match="explicit --attempt-id"):
        world.run("thinking-fold-b", promote_only=True)
    with pytest.raises(SystemExit, match="requires every roster row to be warm"):
        world.run("thinking-fold-b", promote_only=True, attempt_id="attempt-promote-only-v1")
    assert world.sessions == []
    with pytest.raises(SystemExit, match="promotes nothing"):
        world.run("thinking-smoke-4", promote_only=True, attempt_id="attempt-promote-only-v1")


def test_promote_only_after_a_warm_cache_makes_zero_contacts_and_writes_the_receipt(world):
    world.run("thinking-fold-b", plan_calls=6)
    world.receipt.unlink()
    shutil.rmtree(world.packet_root)
    world.contacts.clear()
    n_sessions = len(world.sessions)
    rc, report = world.run("thinking-fold-b", promote_only=True, attempt_id="attempt-promote-only-v1")
    assert rc == 0 and world.contacts == [] and len(world.sessions) == n_sessions
    document = json.loads(world.receipt.read_text(encoding="utf-8"))
    assert document["mode"] == "promote-only" and document["encode_contacts"] == 0
    assert document["preprocess_session_receipt_sha256"] is None and report["mode"] == "promote-only"


# --------------------------------------------------------------------------------------------- the pin step


PROMOTE_MODE_ENCODE = "encode-and-promote"


def _baseline_copies(world, tmp_repo: Path) -> None:
    for relpath in module.BASELINES:
        target = tmp_repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (REPO / relpath).read_text(encoding="utf-8")
        assert text.count(fam.THINK_PROMOTION_RECEIPT) == 1
        target.write_text(text.replace(fam.THINK_PROMOTION_RECEIPT, str(world.receipt)), encoding="utf-8", newline="")


def test_the_pin_step_verifies_the_receipt_and_substitutes_the_sentinel_exactly_once(world, tmp_path, capsys):
    world.run("thinking-smoke-4")
    world.run("thinking-fold-b")
    capsys.readouterr()
    tmp_repo = tmp_path / "repo"
    _baseline_copies(world, tmp_repo)
    before = {b: (tmp_repo / b).read_text(encoding="utf-8") for b in module.BASELINES}
    sha = _sha(world.receipt.read_bytes())
    # print only: nothing is written without --write
    rc = module.pin_receipt(_args(write=False), repo=tmp_repo, lock_path=world.lock, receipt_path=world.receipt,
                            packet_root=world.packet_root, expected_rows=6)
    summary = json.loads(capsys.readouterr().out)
    assert rc == 0 and summary["promotion_receipt_sha256"] == sha and sorted(summary["baselines_changed"]) == sorted(module.BASELINES)
    assert summary["written"] is False and {b: (tmp_repo / b).read_text(encoding="utf-8") for b in module.BASELINES} == before
    module.pin_receipt(_args(write=True), repo=tmp_repo, lock_path=world.lock, receipt_path=world.receipt,
                       packet_root=world.packet_root, expected_rows=6)
    capsys.readouterr()
    for relpath in module.BASELINES:
        after = (tmp_repo / relpath).read_text(encoding="utf-8")
        assert after.count(sha) == 1 and fam.UNPINNED_SHA not in after
        assert after.replace(sha, fam.UNPINNED_SHA) == before[relpath]                    # nothing else in the baseline changed
    # idempotent, and a different receipt never overwrites a real pin
    module.pin_receipt(_args(write=True), repo=tmp_repo, lock_path=world.lock, receipt_path=world.receipt,
                       packet_root=world.packet_root, expected_rows=6)
    assert json.loads(capsys.readouterr().out)["baselines_changed"] == []
    with pytest.raises(SystemExit, match="already pinned to a different receipt"):
        module.baseline_substitution((tmp_repo / module.BASELINES[0]).read_text(encoding="utf-8"), str(world.receipt), "9" * 64)


def test_the_pin_step_refuses_a_receipt_that_misses_rows_or_a_tampered_packet(world, tmp_path):
    world.run("thinking-fold-b")
    tmp_repo = tmp_path / "repo"
    _baseline_copies(world, tmp_repo)
    with pytest.raises(SystemExit, match="does not cover exactly"):
        module.pin_receipt(_args(), repo=tmp_repo, lock_path=world.lock, receipt_path=world.receipt, packet_root=world.packet_root,
                           expected_rows=1080)
    packet = next(world.packet_root.glob("slurp/train/*/*/packet.json"))
    packet.write_text(packet.read_text(encoding="utf-8").replace('"causal_attention": true', '"causal_attention": false'), encoding="utf-8")
    with pytest.raises(Exception):
        module.pin_receipt(_args(), repo=tmp_repo, lock_path=world.lock, receipt_path=world.receipt, packet_root=world.packet_root,
                           expected_rows=6)


def test_the_real_baselines_carry_the_sentinel_and_the_substitution_rewrites_one_field_only():
    for relpath in module.BASELINES:
        text = (REPO / relpath).read_text(encoding="utf-8")
        new, changed = module.baseline_substitution(text, fam.THINK_PROMOTION_RECEIPT, "5" * 64) if fam.UNPINNED_SHA in text else (text, False)
        if changed:
            assert new.count("5" * 64) == 1 and new.replace("5" * 64, fam.UNPINNED_SHA) == text
            json.loads(new)


# ------------------------------------------------------------------------------------------------------- receipt shapes


def test_the_promotion_receipt_has_the_instruct_shape(world):
    world.run("thinking-fold-b")
    document = json.loads(world.receipt.read_text(encoding="utf-8"))
    instruct = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/EVO-FOLD-B-V2-promotion.json")
    assert document["schema"] == "saea-speech-packet-promotion-receipt-v1" and document["study"] == "speech-aware-evidence-acquisition"
    assert set(document["packets"][0]) == {"packet_id", "packet_sha256", "audio_sha256", "decoder_gguf_sha256", "mmproj_sha256"}
    assert document["feature_root"] == str(world.packet_root) and document["legacy_cache_dir"] == str(world.cache)
    if instruct.is_file():                                                                  # the sealed Instruct receipt, when present
        reference = json.loads(instruct.read_text(encoding="utf-8"))
        assert set(document) == set(reference) | ({"shared_packet_count", "shared_packets", "mode", "encode_contacts"} & set(document))
        assert set(reference["packets"][0]) == set(document["packets"][0])
        assert reference["schema"] == document["schema"]


def test_the_promotion_receipt_is_built_by_the_instruct_drivers_own_builder():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "evo._promotion_receipt_document(" in source and "evo._write_promotion_receipt(" in source and "evo._promote_roster(" in source
    assert "def _promotion_receipt_document" not in source and "def _promote_roster" not in source


def test_the_encoder_receipt_carries_the_registered_identity_fields(world):
    world.run("thinking-fold-b")
    receipt = world.encoder_receipt("attempt-packets-thinking-gpu-fold-b-v1")
    for key in ("schema", "llama_cpp", "decoder_gguf_sha256", "mmproj_sha256", "runtime_receipt_sha256", "split_identity_hash", "files",
                "encode_workers", "promote_workers", "promotion_receipt_sha256", "model_lock_key", "dataset_runtime_view_sha256"):
        assert key in receipt, key
    assert receipt["schema"] == module.ENCODER_RECEIPT_SCHEMA and receipt["llama_cpp"]["build_commit"] == "c" * 40
    assert not any(k in json.dumps(receipt) for k in ("transcript", "gold"))


# ----------------------------------------------------------------------------------------------------- the chain wrapper


def test_the_wrapper_and_entry_parse_and_name_the_collision_guards():
    for script in (WRAPPER, ENTRY):
        assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    text = WRAPPER.read_text(encoding="utf-8")
    for needle in ("saea_sidecar_admission", "saea_flight_alive", "saea_cpu_sidecars", "--check-ledger", "wait_sidecars_gone",
                   "thinking-smoke-4", "thinking-fold-b", "serving-slurp-thinking-direct-fold-b-np4-v1"):
        assert needle in text, needle
    assert text.index("run_attempt thinking-smoke-4") < text.index("run_attempt thinking-fold-b")        # smoke rows first
    assert "serving_swap.sh" not in text.replace("serving swap", "").split("set -u")[1]                    # it never starts a swap
    assert "direct_fb_packets.sh\" --allow-cpu --run --stage all" in ENTRY.read_text(encoding="utf-8")


class Host:
    """A stubbed host for the wrapper: a git checkout holding serving_lib.sh, fake pgrep and driver, a fake serving_session.sh."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.repo = tmp / "repo"
        self.data = tmp / "data"
        self.bin = tmp / "bin"
        self.log = tmp / "driver.log"
        for directory in (self.repo / "scripts" / "flights" / "batch", self.repo / "scripts" / "flights" / "direct", self.data, self.bin):
            directory.mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "flights" / "batch" / "serving_lib.sh", self.repo / "scripts" / "flights" / "batch" / "serving_lib.sh")
        for command in (["init", "-q"], ["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", str(self.repo), *command], check=True, capture_output=True)
        (self.bin / "pgrep").write_text(
            '#!/bin/bash\ncase "$*" in *lama-server*|*slurp_evo*) [ -f "$STUB_PGREP" ] && cat "$STUB_PGREP" ;; esac\nexit 0\n', encoding="utf-8")
        (self.bin / "session.sh").write_text('#!/bin/bash\n[ -f "$STUB_NO_SESSION" ] && exit 3\necho \'{"process_state":"running","stale":false}\'\n', encoding="utf-8")
        (self.bin / "driver").write_text(
            '#!/bin/bash\n'
            'echo "$@" >> "$STUB_LOG"\n'
            'case "$*" in\n'
            '  *--check-ledger*) exit "${STUB_LEDGER_RC:-0}" ;;\n'
            '  *--dry-run*) exit "${STUB_DRY_RC:-0}" ;;\n'
            '  *"thinking-smoke-4 --run"*) exit "${STUB_SMOKE_RC:-0}" ;;\n'
            '  *"thinking-fold-b --run"*) [ -n "$STUB_SIDECAR_AFTER" ] && echo "llama-server -ngl 0" > "$STUB_PGREP"; exit "${STUB_FOLD_RC:-0}" ;;\n'
            'esac\n', encoding="utf-8")
        for stub in ("pgrep", "session.sh", "driver"):
            (self.bin / stub).chmod(0o755)

    def env(self, **extra: str) -> dict[str, str]:
        env = dict(os.environ)
        env.update(PATH=f"{self.bin}:{os.environ['PATH']}", PACKETS_REPO=str(self.repo), SAEA_DATA=str(self.data),
                   SAEA_SERVING_SESSION=str(self.bin / "session.sh"), PACKETS_PY=str(self.bin / "driver"), PACKETS_AVAILABLE_GB="64",
                   PACKETS_FREE_DISK_GB="100", PACKETS_OUT=str(self.tmp / "out"), PACKETS_GONE_WAIT_SECONDS="1",
                   STUB_PGREP=str(self.tmp / "pgrep.txt"), STUB_LOG=str(self.log), STUB_NO_SESSION=str(self.tmp / "no-session"),
                   SAEA_RUNTIME_ROOT=str(self.tmp / "home"), SAEA_SWAP_PENDING=str(self.tmp / "swap.pending"))
        env.update(extra)
        return env

    def run(self, *args: str, **extra: str) -> subprocess.CompletedProcess:
        flags = [] if extra.pop("NO_ALLOW_CPU", None) else ["--allow-cpu"]
        return subprocess.run(["bash", str(WRAPPER), *flags, *args], capture_output=True, text=True, env=self.env(**extra), timeout=60)

    def attempts(self) -> list[str]:
        """The rosters the driver was asked to --run, in order."""
        order = []
        for call in self.driver_calls():
            tokens = call.split()
            if "--run" in tokens and "--roster" in tokens:
                order.append(tokens[tokens.index("--roster") + 1])
        return order

    def driver_calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []


@pytest.fixture()
def host(tmp_path):
    return Host(tmp_path)


def test_check_passes_on_a_clean_stubbed_host_and_starts_nothing(host):
    result = host.run("--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHECK PASS" in result.stdout
    assert host.attempts() == []


@pytest.mark.parametrize("setup,code", [
    (lambda h: (h.data / "locks").mkdir() or (h.data / "locks" / "flight.lock").write_text("x"), 7),
    (lambda h: (h.tmp / "pgrep.txt").write_text("123 llama-server --host 127.0.0.1 --port 8081 -ngl 0\n"), 4),
    (lambda h: (h.tmp / "no-session").write_text("x"), 10),
    (lambda h: (h.data / "serving" / "serving-slurp-thinking-direct-fold-b-np4-v1").mkdir(parents=True) or
     (h.data / "serving" / "serving-slurp-thinking-direct-fold-b-np4-v1" / "session.json").write_text("{}"), 6),
    (lambda h: (h.tmp / "swap.pending").write_text(json.dumps({"pid": os.getpid()})), 10),
])
def test_check_refuses_each_collision_and_names_its_exit_code(host, setup, code):
    setup(host)
    result = host.run("--check")
    assert result.returncode == code, result.stdout + result.stderr
    assert "REFUSED" in result.stdout


def test_check_refuses_low_memory_a_short_disk_an_uncountersigned_row_and_a_refused_dry_run(host):
    assert host.run("--check", PACKETS_AVAILABLE_GB="10").returncode == 8
    assert host.run("--check", PACKETS_FREE_DISK_GB="1").returncode == 8
    assert host.run("--check", STUB_LEDGER_RC="4").returncode == 11
    assert host.run("--check", STUB_DRY_RC="3").returncode == 3
    (host.repo / "dirt.txt").write_text("x")
    subprocess.run(["git", "-C", str(host.repo), "add", "dirt.txt"], check=True, capture_output=True)
    assert host.run("--check").returncode == 2


def test_run_refuses_an_uncountersigned_row_before_the_first_contact(host):
    result = host.run("--run", STUB_LEDGER_RC="4")
    assert result.returncode == 11 and host.attempts() == []


def test_run_flies_the_smoke_before_fold_b_then_waits_for_the_sidecar_to_go(host):
    result = host.run("--run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert host.attempts() == ["thinking-smoke-4", "thinking-fold-b"]
    assert "PACKETS DONE" in result.stdout and "--pin-receipt" in result.stdout


def test_run_stage_smoke_stops_after_the_smoke(host):
    result = host.run("--run", "--stage", "smoke")
    assert result.returncode == 0 and "SMOKE DONE" in result.stdout
    assert host.attempts() == ["thinking-smoke-4"]


def test_a_failed_attempt_stops_the_chain_with_its_own_code(host):
    smoke = host.run("--run", STUB_SMOKE_RC="1")
    assert smoke.returncode == 20 and host.attempts() == ["thinking-smoke-4"]
    host.log.unlink()
    fold = host.run("--run", STUB_FOLD_RC="1")
    assert fold.returncode == 21


def test_a_sidecar_that_does_not_go_away_is_reported(host):
    result = host.run("--run", STUB_SIDECAR_AFTER="1")
    assert result.returncode == 22 and "still up" in result.stdout


# ------------------------------------------------------------------------------------------------------------ the README


def test_the_package_readme_carries_the_runbook_the_writer_would_regenerate():
    import ast

    readme = (REPO / "docs" / "readiness" / "2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1" / "README.md").read_text(encoding="utf-8")
    tree = ast.parse((REPO / "scripts" / "flights" / "direct" / "direct_fb_write_registration.py").read_text(encoding="utf-8"))
    runbook = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "PACKETS_RUNBOOK" for t in node.targets))
    assert runbook in readme
    for needle in ("direct_fb_packets_gpu.sh --check", "--pin-receipt", "Which registered files change hash", "smoke-roster-receipt-v1.json",
                   "Countersign text", "Expected runtime", "NO GPU record"):
        assert needle in runbook, needle


# ----------------------------------------------------------------------- first real run, 2026-10-11: the two defects


def test_the_ledger_check_compares_gpu_hours_like_the_gate(tmp_path):
    ok = module.ledger_state(_ledger(tmp_path, notes=SIGNED_NOTES), split_identity_hash=SPLIT)
    assert ok["countersigned"] is True and ok["problems"] == []
    zero = module.ledger_state(_ledger(tmp_path, notes=SIGNED_NOTES, gpu="0.0"), split_identity_hash=SPLIT)     # run 1: the row said 0.0
    assert zero["countersigned"] is False and any("gpu hours" in problem and "0.0" in problem for problem in zero["problems"])
    two = module.ledger_state(_ledger(tmp_path, notes=SIGNED_NOTES, gpu="2.0"), split_identity_hash=SPLIT)
    assert two["countersigned"] is False
    assert module.ROW_GPU_HOURS == module.ROSTERS["thinking-fold-b"].plan_gpu_hours == module.ROSTERS["thinking-smoke-4"].plan_gpu_hours


def test_the_driver_creates_the_empty_legacy_cache_before_the_first_contact(world):
    assert not world.cache.exists()                                   # nothing else creates it; the server does not
    rc, report = world.run("thinking-smoke-4")
    assert rc == 0 and world.cache.is_dir() and len(list(world.cache.glob("*.feat"))) == 2 and report["contacts"] == 2
    assert not world.packet_root.exists()                             # the packet root itself stays absent until the promotion


def test_answered_contacts_that_cached_nothing_fail_the_attempt_instead_of_crashing_in_the_inspector(world):
    world.drop_features = True
    with pytest.raises(SystemExit, match="holds no entry for 2 of 2 rows"):
        world.run("thinking-smoke-4")
    record = json.loads(world._record_path("attempt-packets-thinking-gpu-smoke-4-v1").read_text(encoding="utf-8"))
    assert record["actual"]["calls"] == 2 and record["state"] == "OPENED"                   # the contacts ARE counted
    assert not (world.data / "runs" / module.RUN_ID / "attempt-packets-thinking-gpu-smoke-4-v1" / module.ENCODER_RECEIPT_NAME).exists()


def _fail_the_first_smoke(world):
    world.drop_features = True
    with pytest.raises(SystemExit):
        world.run("thinking-smoke-4")
    world.drop_features = False


def test_a_failed_attempt_makes_every_default_start_ambiguous_and_refuses_it(world):
    _fail_the_first_smoke(world)
    with pytest.raises(SystemExit, match="already used"):                                    # the same id: never silently reused
        world.run("thinking-smoke-4")
    with pytest.raises(SystemExit, match="wrote NO encoder receipt"):                          # a new id without naming the failure
        world.run("thinking-smoke-4", attempt_id="attempt-packets-thinking-smoke-4-v2")
    with pytest.raises(SystemExit, match="wrote NO encoder receipt"):                          # fold b is ambiguous too
        world.run("thinking-fold-b", attempt_id="attempt-packets-thinking-fold-b-v2")
    with pytest.raises(SystemExit, match="wrote NO encoder receipt"):                          # naming the wrong attempt
        world.run("thinking-smoke-4", attempt_id="attempt-packets-thinking-smoke-4-v2", recovery_of="attempt-other")
    dry = module.dry_run
    with pytest.raises(SystemExit, match="REFUSED"):
        dry(_args(roster="thinking-fold-b"), lock_path=world.lock, ledger_path=world.sync_ledger())
    assert world.sessions and len(world.sessions) == 1                                       # none of the refusals started a sidecar


def test_the_labelled_recovery_declares_the_cumulative_spend_and_a_row_that_carries_it(world):
    _fail_the_first_smoke(world)
    # The ledger row is still the original: the recovery start needs the extra spend registered first.
    original = _ledger(world.tmp, notes=SIGNED_NOTES)
    with pytest.raises(SystemExit, match="budgets"):
        module.run(_args(roster="thinking-smoke-4", workers=2, promote_workers=2, attempt_id="attempt-packets-thinking-smoke-4-v2",
                         recovery_of="attempt-packets-thinking-gpu-smoke-4-v1"), lock_path=world.lock, ledger_path=original)
    rc, report = world.run("thinking-smoke-4", attempt_id="attempt-packets-thinking-smoke-4-v2",
                           recovery_of="attempt-packets-thinking-gpu-smoke-4-v1")
    assert rc == 0 and report["recovery_of"] == ["attempt-packets-thinking-gpu-smoke-4-v1"] and report["prior_calls"] == 2
    assert world.plans[-1]["planned_model_calls"] == 2 + 2                                    # failed 2 + this attempt's 2
    rc, report = world.run("thinking-fold-b", attempt_id="attempt-packets-thinking-fold-b-v2",
                           recovery_of="attempt-packets-thinking-gpu-smoke-4-v1")
    assert rc == 0 and report["contacts"] == 4 and report["skipped_warm_rows"] == 2           # the redone smoke rows are not contacted again
    assert world.plans[-1]["planned_model_calls"] == 2 + 2 + 4


def test_a_second_failure_stops_the_flight_and_a_recovery_flag_without_a_failure_is_refused(world):
    with pytest.raises(SystemExit, match="no failed attempt exists"):
        world.run("thinking-smoke-4", recovery_of="attempt-packets-thinking-gpu-smoke-4-v1")
    _fail_the_first_smoke(world)
    world.drop_features = True
    with pytest.raises(SystemExit, match="holds no entry"):
        world.run("thinking-smoke-4", attempt_id="attempt-packets-thinking-smoke-4-v2", recovery_of="attempt-packets-thinking-gpu-smoke-4-v1")
    world.drop_features = False
    with pytest.raises(SystemExit, match="single recovery re-registration is spent"):
        world.run("thinking-smoke-4", attempt_id="attempt-packets-thinking-smoke-4-v3", recovery_of="attempt-packets-thinking-gpu-smoke-4-v1")


def test_a_run_directory_without_an_attempt_record_is_ambiguous(world):
    (world.data / "runs" / module.RUN_ID / "attempt-orphan").mkdir(parents=True)
    with pytest.raises(SystemExit, match="without an attempt record"):
        world.run("thinking-smoke-4")


def test_check_ledger_expects_the_failed_attempts_spend_in_the_row(world, capsys):
    _fail_the_first_smoke(world)
    capsys.readouterr()
    stale = _ledger(world.tmp, notes=SIGNED_NOTES)
    assert module.check_ledger(_args(), ledger_path=stale) == 4
    state = json.loads(capsys.readouterr().out)
    assert state["expected"]["calls"] == 1084 + 2 and state["expected"]["failed_attempts"] == ["attempt-packets-thinking-gpu-smoke-4-v1"]
    assert module.check_ledger(_args(), ledger_path=world.sync_ledger()) == 0
    capsys.readouterr()
    assert module.check_ledger(_args(), ledger_path=world.sync_ledger(gpu="0.0")) == 4


def test_the_first_attempt_declares_prior_plus_cold_rows_so_the_normal_chain_totals_the_row(world):
    world.run("thinking-smoke-4")
    world.run("thinking-fold-b")
    assert [plan["planned_model_calls"] for plan in world.plans] == [2, 2 + 4]                  # smoke rows are not contacted twice


def test_the_wrapper_forwards_the_recovery_labels_to_every_driver_call(host):
    recovery = host.tmp / "recovery"
    recovery.write_text("SMOKE_ATTEMPT=smoke-v2\nFOLD_ATTEMPT=fold-v2\nRECOVERY_OF=smoke-v1\n", encoding="utf-8")
    result = host.run("--run", PACKETS_RECOVERY_FILE=str(recovery))
    assert result.returncode == 0, result.stdout + result.stderr
    calls = host.driver_calls()
    smoke = [c for c in calls if "thinking-smoke-4" in c]
    fold = [c for c in calls if "thinking-fold-b" in c]
    assert smoke and fold
    assert all("--attempt-id smoke-v2" in c and "--recovery-of smoke-v1" in c for c in smoke)
    assert all("--attempt-id fold-v2" in c and "--recovery-of smoke-v1" in c for c in fold)
    host.log.unlink()
    host.run("--check", PACKETS_RECOVERY_FILE=str(host.tmp / "absent"))
    assert not any("--recovery-of" in c or "--attempt-id" in c for c in host.driver_calls())


# ============================================================================================================
# The GPU geometry (re-registration of 2026-10-11): geometry switch, serving/GPU state refusals, receipt device, rate gate
# ============================================================================================================


def test_the_gpu_geometry_is_the_default_and_the_cpu_geometry_needs_allow_cpu():
    assert module.GEOMETRY.key == "gpu" and module.RUN_ID == fam.PACKETS_ROW_ID and module.SIDECAR_FRAGMENT == pins_mod.PREPROCESS_FRAGMENT
    with pytest.raises(SystemExit, match="SUPERSEDED"):
        module.apply_geometry("cpu")
    assert module.GEOMETRY.key == "gpu"                                                    # a refused switch changes nothing
    with pytest.raises(SystemExit, match="SUPERSEDED"):
        module.main(["--roster", "thinking-smoke-4", "--dry-run", "--geometry", "cpu"])
    cpu = module.apply_geometry("cpu", allow_cpu=True)
    assert cpu.device == "cpu" and module.RUN_ID == fam.CPU_PACKETS_ROW_ID and module.SIDECAR_FRAGMENT == pins_mod.PREPROCESS_FRAGMENT_CPU
    assert module.PACKET_ROOT == Path(fam.CPU_THINK_PACKET_ROOT) and module.LEGACY_CACHE == Path(pins_mod.CPU_THINKING_LEGACY_CACHE)
    assert module.ROSTERS["thinking-smoke-4"].default_attempt_id == "attempt-packets-thinking-smoke-4-v1"       # the record's own attempt ids
    assert module.RUNTIME_RECEIPT_RELPATH == pins_mod.PREPROCESS_RECEIPT_CPU.removeprefix("docs/")
    module.apply_geometry("gpu")
    assert module.RUN_ID == fam.PACKETS_ROW_ID and module.ROSTERS["thinking-smoke-4"].default_attempt_id == "attempt-packets-thinking-gpu-smoke-4-v1"


def test_the_two_geometries_never_share_a_root_a_run_id_a_fragment_or_an_attempt_id():
    gpu, cpu = module.GEOMETRIES["gpu"], module.GEOMETRIES["cpu"]
    for field in ("run_id", "sidecar_fragment", "experiment_fragment", "runtime_receipt_relpath", "packet_root", "legacy_cache", "promotion_receipt",
                  "smoke_attempt", "fold_attempt"):
        assert getattr(gpu, field) != getattr(cpu, field), field
    assert not str(gpu.packet_root).startswith(str(cpu.packet_root)) and not str(cpu.packet_root).startswith(str(gpu.packet_root))
    for geometry in (gpu, cpu):
        assert geometry.packet_root != evo.DEFAULT_FEATURE_ROOT and geometry.legacy_cache != evo.DEFAULT_LEGACY_CACHE_DIR
        assert str(geometry.promotion_receipt).startswith(str(geometry.packet_root))
    assert (gpu.device, gpu.default_workers, gpu.smoke_in_row, gpu.row_calls) == ("gpu", 1, True, 1084)
    assert (cpu.device, cpu.default_workers, cpu.smoke_in_row, cpu.row_calls) == ("cpu", 4, False, 1080)


def test_the_gpu_dry_run_plan_is_a_gpu_encoder_server_at_one_worker_with_the_e21_flags(tmp_path, monkeypatch):
    _local_receipts(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "root_problems", lambda *a, **k: [])
    out = tmp_path / "plan.json"
    assert module.dry_run(_args(roster="thinking-smoke-4", output=out), lock_path=_fake_lock(tmp_path), ledger_path=REPO / "docs" / "exposure-ledger.md") == 0
    plan = json.loads(out.read_text(encoding="utf-8"))
    args = plan["sidecar"]["server_args"]
    assert plan["device"] == "gpu" and plan["sidecar"]["encode_workers"] == 1 and plan["run_id"] == fam.PACKETS_ROW_ID
    assert args[args.index("-ngl") + 1] == "999" and "--no-mmproj-offload" not in args and args[args.index("-np") + 1] == "1"
    assert plan["attempt_id"] == "attempt-packets-thinking-gpu-smoke-4-v1" and plan["pins"]["runtime_receipt"].endswith("runtime-q4km-thinking-preprocess-gpu.json")
    assert plan["serving_state"]["gpu_free"] is True


def _stage_session(data: Path, name: str, *, pid: int | None, stopped: bool = False) -> None:
    folder = data / "serving" / name
    folder.mkdir(parents=True, exist_ok=True)
    record = {"identity": {"port": 8080}}
    if pid is not None:
        record["process"] = {"pid": pid}                                       # the pid sits one level down in some records
    (folder / "session.json").write_text(json.dumps(record), encoding="utf-8")
    if stopped:
        (folder / "session-stop.json").write_text("{}", encoding="utf-8")


def test_gpu_state_names_every_reason_the_card_is_not_free(tmp_path, monkeypatch):
    data = tmp_path / "data"
    _stage_session(data, "serving-live", pid=4242)
    _stage_session(data, "serving-stopped", pid=4243, stopped=True)
    _stage_session(data, "serving-dead", pid=4244)
    monkeypatch.setattr(module, "pid_alive", lambda pid: pid == 4242)
    monkeypatch.setattr(module, "port_listening", lambda port: port == 8080)
    monkeypatch.setattr(module, "gpu_memory_used_mib", lambda: 22976)
    state = REAL_GPU_STATE(data)
    assert state["gpu_free"] is False and state["resident_sessions"] == ["serving-live"]                 # a stop record or a dead pid is not resident
    assert state["serving_port_listening"] is True and state["gpu_memory_used_mib"] == 22976
    assert len(state["findings"]) == 3 and "serving-live" in state["findings"][0] and "8080" in state["findings"][1] and "22976" in state["findings"][2]
    monkeypatch.setattr(module, "pid_alive", lambda pid: False)
    monkeypatch.setattr(module, "port_listening", lambda port: False)
    monkeypatch.setattr(module, "gpu_memory_used_mib", lambda: 300)
    free = REAL_GPU_STATE(data)
    assert free["gpu_free"] is True and free["findings"] == [] and free["resident_sessions"] == []
    monkeypatch.setattr(module, "gpu_memory_used_mib", lambda: None)                                    # nvidia-smi unreadable: unknown, not a refusal
    assert REAL_GPU_STATE(data)["gpu_free"] is True
    _stage_session(data, "serving-no-pid", pid=None)                                                      # no pid recorded: treated as resident
    assert REAL_GPU_STATE(data)["resident_sessions"] == ["serving-no-pid"]


def test_a_gpu_run_refuses_while_any_serving_session_is_resident_before_any_process_starts(world, monkeypatch):
    sid = "serving-slurp-native-candidate-five-train-a-np4-v1"
    busy = {"resident_sessions": [sid], "serving_port_listening": True, "gpu_memory_used_mib": 22976, "gpu_free": False,
            "findings": ["serving session(s) recorded resident: %s (stop them first; the card holds one core)" % sid,
                         "something listens on the serving port 8080", "GPU memory in use is 22976 MiB (> 3072 MiB): the card is not free"]}
    monkeypatch.setattr(module, "gpu_state", lambda root: dict(busy))
    with pytest.raises(SystemExit, match="REFUSED.*recorded resident.*8080.*22976"):
        world.run("thinking-smoke-4")
    assert world.sessions == [] and world.contacts == [] and not world.cache.exists()
    # the dry-run reports the same state as information and does NOT refuse over it (the pre-window --check runs while Instruct is resident)
    out = world.tmp / "dry.json"
    assert module.dry_run(_args(roster="thinking-smoke-4", output=out), lock_path=world.lock, ledger_path=world.sync_ledger()) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["serving_state"]["gpu_free"] is False


def test_the_cpu_geometry_does_not_consult_the_gpu_state(world, monkeypatch):
    monkeypatch.setattr(module, "gpu_state", lambda root: pytest.fail("the CPU sidecar runs beside a resident GPU session"))
    module.apply_geometry("cpu", allow_cpu=True)
    monkeypatch.setattr(module, "PACKET_ROOT", world.packet_root)
    monkeypatch.setattr(module, "LEGACY_CACHE", world.cache)
    monkeypatch.setattr(module, "PROMOTION_RECEIPT", world.receipt)
    rc, report = world.run("thinking-smoke-4")
    assert rc == 0 and report["device"] == "cpu" and report["geometry"] == "cpu"


def test_the_encoder_receipt_records_the_device_the_server_flags_and_the_measured_rate(world):
    world.run("thinking-smoke-4")
    world.run("thinking-fold-b")
    for attempt, roster in (("attempt-packets-thinking-gpu-smoke-4-v1", "thinking-smoke-4"), ("attempt-packets-thinking-gpu-fold-b-v1", "thinking-fold-b")):
        receipt = world.encoder_receipt(attempt)
        assert receipt["schema"] == "saea-thinking-packet-encoder-receipt-v2" and receipt["roster"] == roster
        assert receipt["device"] == "gpu" and receipt["geometry"] == "gpu" and receipt["sidecar_fragment"] == pins_mod.PREPROCESS_FRAGMENT
        assert receipt["server_args"] == world.values["server_args"] and receipt["server_env_keys"] == ["LLAMA_MTMD_FEAT_CACHE_DIR"]
        assert receipt["gpu_memory_before_mib"] == 512 and receipt["seconds_per_row"] is not None and receipt["seconds_per_row"] > 0
        assert receipt["run_id"] == fam.PACKETS_ROW_ID
    assert world.sessions[0]["session_id"].endswith("-gpu-encoder") and world.sessions[1]["session_id"].endswith("-gpu-encoder")


def test_smoke_rate_reads_the_smoke_receipt_and_gates_the_fold_b_projection(tmp_path, capsys):
    root = tmp_path / "d"
    folder = root / "runs" / module.RUN_ID / module.ROSTERS["thinking-smoke-4"].default_attempt_id
    folder.mkdir(parents=True)
    path = folder / module.ENCODER_RECEIPT_NAME
    args = _args(roster=None, max_fold_seconds=3000.0)
    assert module.smoke_rate(args, data_root=root) == 6 and json.loads(capsys.readouterr().out)["usable"] is False        # no receipt yet
    path.write_text(json.dumps({"seconds_per_row": 0.5, "device": "gpu"}), encoding="utf-8")
    assert module.smoke_rate(args, data_root=root) == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["projected_fold_b_encode_seconds"] == round(0.5 * (fam.ROWS - fam.SMOKE_ROWS), 1) and verdict["within_cap"] is True
    path.write_text(json.dumps({"seconds_per_row": 3.0, "device": "gpu"}), encoding="utf-8")                                 # 3.0 x 1,076 = 3,228 s > 3,000 s
    assert module.smoke_rate(args, data_root=root) == 5
    path.write_text(json.dumps({"seconds_per_row": 0.2, "device": "cpu"}), encoding="utf-8")                                 # a CPU receipt never passes the GPU gate
    assert module.smoke_rate(args, data_root=root) == 5
    path.write_text(json.dumps({"device": "gpu"}), encoding="utf-8")
    assert module.smoke_rate(args, data_root=root) == 6


def test_the_gpu_row_total_carries_the_smoke_attempt_and_the_cpu_row_total_does_not(world):
    context = module.AttemptContext(0, 0.0, 0, 0.0, ())
    calls, seconds = module.expected_row_totals(world.values, context)
    smoke_audio = sum(float(i["audio_seconds"]) for i in world.items[:4])
    total = sum(float(i["audio_seconds"]) for i in world.items)
    assert calls == 1084 and seconds == int(-(-(total + smoke_audio) // 1))
    module.apply_geometry("cpu", allow_cpu=True)
    assert module.expected_row_totals(world.values, context) == (1080, int(-(-total // 1)))
    wasted = module.AttemptContext(4, 9.94, 4, 9.94, ("attempt-x",))
    assert module.expected_row_totals(world.values, wasted)[0] == 1084


# ------------------------------------------------------------------------------------------------ the GPU window chain


class GpuHost:
    """A stubbed host for direct_fb_packets_gpu.sh: a git checkout with serving_lib.sh, a fake swap tool, a fake driver, a fake pgrep."""

    SWAP = (
        '#!/bin/bash\n'
        'echo "$*" >> "$STUB_SWAP_LOG"\n'
        'case "$*" in\n'
        '  "--stop-only --dry-run") rc=${STUB_SWAP_DRY_RC:-0} ;;\n'
        '  "--stop-only") rc=${STUB_SWAP_STOP_RC:-0} ;;\n'
        '  "think-np4 --start-only") rc=${STUB_SWAP_THINK_RC:-0} ;;\n'
        '  "slurp-np4 --start-only") rc=${STUB_SWAP_INSTRUCT_RC:-0} ;;\n'
        '  *) rc=64 ;;\n'
        'esac\n'
        'echo "{\\"schema\\": \\"saea-serving-swap-summary-v1\\", \\"exit\\": $rc}"\n'
        'exit $rc\n')
    DRIVER = (
        '#!/bin/bash\n'
        'echo "$@" >> "$STUB_LOG"\n'
        'case "$*" in\n'
        '  *--check-ledger*) exit "${STUB_LEDGER_RC:-0}" ;;\n'
        '  *--dry-run*) exit "${STUB_DRY_RC:-0}" ;;\n'
        '  *--smoke-rate*) echo \'{"seconds_per_row": 0.5}\'; exit "${STUB_RATE_RC:-0}" ;;\n'
        '  *"thinking-smoke-4 --run"*) exit "${STUB_SMOKE_RC:-0}" ;;\n'
        '  *"thinking-fold-b --run"*) exit "${STUB_FOLD_RC:-0}" ;;\n'
        'esac\n')
    PGREP = (
        '#!/bin/bash\n'
        'case "$*" in\n'
        '  *"--port 8081"*) [ -f "$STUB_ENCODER_PGREP" ] && cat "$STUB_ENCODER_PGREP" ;;\n'
        '  *lama-server*) [ -f "$STUB_PGREP" ] && cat "$STUB_PGREP" ;;\n'
        'esac\n'
        'exit 0\n')

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.repo = tmp / "repo"
        self.data = tmp / "data"
        self.bin = tmp / "bin"
        self.log, self.swap_log = tmp / "driver.log", tmp / "swap.log"
        self.hold = tmp / "queue" / "watchdog.hold"
        self.out = tmp / "out"
        for directory in (self.repo / "scripts" / "flights" / "batch", self.repo / "scripts" / "flights" / "direct", self.data, self.bin):
            directory.mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "flights" / "batch" / "serving_lib.sh", self.repo / "scripts" / "flights" / "batch" / "serving_lib.sh")
        for entry in ("serving_task_entry_think.sh", "serving_monitor_start_think.sh"):
            (self.repo / "scripts" / "flights" / "direct" / entry).write_text("#!/bin/bash\n", encoding="utf-8")
        for command in (["init", "-q"], ["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", str(self.repo), *command], check=True, capture_output=True)
        for name, body in (("swap", self.SWAP), ("driver", self.DRIVER), ("pgrep", self.PGREP)):
            (self.bin / name).write_text(body, encoding="utf-8", newline="\n")
            (self.bin / name).chmod(0o755)

    def env(self, **extra: str) -> dict[str, str]:
        env = dict(os.environ)
        env.update(PATH=f"{self.bin}:{os.environ['PATH']}", PACKETS_REPO=str(self.repo), SAEA_DATA=str(self.data), PACKETS_PY=str(self.bin / "driver"),
                   PACKETS_SWAP=str(self.bin / "swap"), PACKETS_OUT=str(self.out), PACKETS_WATCHDOG_HOLD=str(self.hold),
                   PACKETS_AVAILABLE_GB="64", PACKETS_FREE_DISK_GB="100", PACKETS_GONE_WAIT_SECONDS="1",
                   PACKETS_RECOVERY_FILE=str(self.tmp / "absent.recovery"), STUB_LOG=str(self.log), STUB_SWAP_LOG=str(self.swap_log),
                   STUB_PGREP=str(self.tmp / "pgrep.txt"), STUB_ENCODER_PGREP=str(self.tmp / "encoder-pgrep.txt"))
        env.update(extra)
        return env

    def run(self, *args: str, **extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(GPU_CHAIN), *args], capture_output=True, text=True, env=self.env(**extra), timeout=120)

    def swaps(self) -> list[str]:
        return self.swap_log.read_text(encoding="utf-8").splitlines() if self.swap_log.exists() else []

    def driver_calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def attempts(self) -> list[str]:
        order = []
        for call in self.driver_calls():
            tokens = call.split()
            if "--run" in tokens and "--roster" in tokens:
                order.append(tokens[tokens.index("--roster") + 1])
        return order

    def events(self) -> list[str]:
        return [line.split("\t")[1] for line in (self.out / "window-events.tsv").read_text(encoding="utf-8").splitlines()]

    def summary(self) -> dict:
        return json.loads((self.out / "window-summary.json").read_text(encoding="utf-8"))


@pytest.fixture()
def gpu_host(tmp_path):
    return GpuHost(tmp_path)


def _drop_committed(host: "GpuHost", name: str) -> None:
    """Remove a tracked file AND commit the removal, so the tree stays clean and only the missing entry is the finding."""

    (host.repo / "scripts" / "flights" / "direct" / name).unlink()
    for command in (["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "-m", "drop " + name]):
        subprocess.run(["git", "-C", str(host.repo), *command], check=True, capture_output=True)


def test_the_gpu_chain_and_entry_parse_and_never_name_the_cpu_recovery_file():
    for script in (GPU_CHAIN, GPU_ENTRY):
        assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    text = GPU_CHAIN.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))          # the comment names the CPU file to forbid it
    assert "/home/chao/direct-fb-packets-gpu.recovery" in code and "/home/chao/direct-fb-packets.recovery" not in code
    assert "--geometry gpu" in text and "direct_fb_packets_gpu.sh\" --run --stage all" in GPU_ENTRY.read_text(encoding="utf-8")
    body = text[text.index("run)\n    registry_guards"):]
    assert body.index("swap --stop-only") < body.index("run_attempt thinking-smoke-4 20") < body.index("rate_gate") \
        < body.index("run_attempt thinking-fold-b 21") < body.index("swap \"$THINK_TARGET\" --start-only")
    assert "finish_failed()" in text and "swap \"$INSTRUCT_TARGET\" --start-only" in text


def test_the_gpu_chain_check_runs_every_guard_and_only_the_stop_dry_run(gpu_host):
    result = gpu_host.run("--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHECK PASS" in result.stdout and gpu_host.attempts() == [] and gpu_host.swaps() == ["--stop-only --dry-run"]
    assert not gpu_host.hold.exists() and not gpu_host.out.exists()
    assert all("--geometry gpu" in call for call in gpu_host.driver_calls())


def test_the_gpu_window_runs_stop_smoke_rate_foldb_then_the_thinking_start_in_order(gpu_host):
    result = gpu_host.run("--run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert gpu_host.swaps() == ["--stop-only --dry-run", "--stop-only", "think-np4 --start-only"]
    runs = [c for c in gpu_host.driver_calls() if "--run" in c.split() or "--smoke-rate" in c.split()]
    assert [("smoke-rate" if "--smoke-rate" in c else c.split()[c.split().index("--roster") + 1]) for c in runs] == ["thinking-smoke-4", "smoke-rate", "thinking-fold-b"]
    assert all("--geometry gpu" in c and "--workers" not in c for c in runs)                       # one worker is the geometry's default
    events = gpu_host.events()
    assert events == ["window-start", "watchdog-hold", "instruct-stop-start", "instruct-stopped", "attempt-thinking-smoke-4-start", "attempt-thinking-smoke-4-end",
                      "smoke-rate", "attempt-thinking-fold-b-start", "attempt-thinking-fold-b-end", "think-start", "think-ready", "window-end"]
    summary = gpu_host.summary()
    assert summary["schema"] == "saea-packets-gpu-window-summary-v1" and summary["result"] == "ok" and summary["exit"] == 0 and summary["stage"] == "all"
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", e["at"]) for e in summary["events"])
    assert gpu_host.hold.exists() and "WINDOW OK" in result.stdout and "--pin-receipt" in result.stdout             # the hold STAYS for the flight
    assert (gpu_host.out / "swap-summaries.jsonl").read_text(encoding="utf-8").count("saea-serving-swap-summary-v1") == 2


@pytest.mark.parametrize("env,code,failed_event", [
    ({"STUB_SWAP_STOP_RC": "11"}, 14, "--stop-only"),
    ({"STUB_SMOKE_RC": "1"}, 20, "thinking-smoke-4"),
    ({"STUB_RATE_RC": "5"}, 23, "projects Fold B"),
    ({"STUB_FOLD_RC": "1"}, 21, "thinking-fold-b"),
    ({"STUB_SWAP_THINK_RC": "13"}, 24, "think-np4"),
])
def test_any_failure_after_the_stop_restores_the_instruct_geometry_and_names_the_failed_step(gpu_host, env, code, failed_event):
    result = gpu_host.run("--run", **env)
    assert result.returncode == code, result.stdout + result.stderr
    assert gpu_host.swaps()[-1] == "slurp-np4 --start-only" and gpu_host.swaps()[:2] == ["--stop-only --dry-run", "--stop-only"]
    summary = gpu_host.summary()
    assert summary["result"] == "failed-restored" and summary["exit"] == code
    names = [e["event"] for e in summary["events"]]
    assert names[-3:] == ["restore-start", "restore-done", "watchdog-hold-released"] and "failed" in names
    assert failed_event in next(e["detail"] for e in summary["events"] if e["event"] == "failed")
    assert not gpu_host.hold.exists()                                                                         # created by this window, so removed on a restored failure
    if code in (20, 23):
        assert gpu_host.attempts() == ["thinking-smoke-4"]                                                    # Fold B never started after a failed smoke or a rate refusal


def test_a_preexisting_watchdog_hold_survives_a_failed_window(gpu_host):
    gpu_host.hold.parent.mkdir(parents=True)
    gpu_host.hold.write_text("coordinator's own hold", encoding="utf-8")
    result = gpu_host.run("--run", STUB_SMOKE_RC="1")
    assert result.returncode == 20 and gpu_host.hold.read_text(encoding="utf-8") == "coordinator's own hold"


def test_a_failed_restore_is_exit_25_and_leaves_the_hold_in_place(gpu_host):
    result = gpu_host.run("--run", STUB_FOLD_RC="1", STUB_SWAP_INSTRUCT_RC="13")
    assert result.returncode == 25 and "RESTORE FAILED" in result.stdout
    summary = gpu_host.summary()
    assert summary["result"] == "failed-unrestored" and summary["events"][-1]["event"] == "restore-failed"
    assert gpu_host.hold.exists()                                                                               # the coordinator must act with the watchdog held


def test_an_encoder_server_that_does_not_go_away_fails_the_window_and_restores_instruct(gpu_host):
    (gpu_host.tmp / "encoder-pgrep.txt").write_text("9000111\n", encoding="utf-8")
    result = gpu_host.run("--run")
    assert result.returncode == 22, result.stdout + result.stderr
    assert gpu_host.swaps()[-1] == "slurp-np4 --start-only" and gpu_host.attempts() == ["thinking-smoke-4"]


def test_stage_smoke_ends_on_the_instruct_geometry_and_stage_fold_b_ends_on_thinking(gpu_host):
    smoke = gpu_host.run("--run", "--stage", "smoke")
    assert smoke.returncode == 0 and "SMOKE DONE" in smoke.stdout
    assert gpu_host.swaps() == ["--stop-only --dry-run", "--stop-only", "slurp-np4 --start-only"] and gpu_host.attempts() == ["thinking-smoke-4"]
    assert gpu_host.summary()["result"] == "smoke-done" and not gpu_host.hold.exists()
    gpu_host.log.unlink()
    gpu_host.swap_log.unlink()
    fold = gpu_host.run("--run", "--stage", "fold-b")
    assert fold.returncode == 0 and gpu_host.attempts() == ["thinking-fold-b"] and gpu_host.swaps()[-1] == "think-np4 --start-only"
    assert not any("--smoke-rate" in c for c in gpu_host.driver_calls())


@pytest.mark.parametrize("setup,code", [
    (lambda h: (h.data / "locks").mkdir() or (h.data / "locks" / "flight.lock").write_text("x"), 7),
    (lambda h: (h.tmp / "pgrep.txt").write_text("123 llama-server --host 127.0.0.1 --port 8082 -ngl 0\n"), 4),
    (lambda h: _drop_committed(h, "serving_task_entry_think.sh"), 9),
])
def test_the_gpu_chain_refuses_each_collision_before_it_touches_the_card(gpu_host, setup, code):
    setup(gpu_host)
    for mode in ("--check", "--run"):
        result = gpu_host.run(mode)
        assert result.returncode == code and "REFUSED" in result.stdout, result.stdout + result.stderr
    assert gpu_host.attempts() == [] and "--stop-only" not in gpu_host.swaps() and not gpu_host.hold.exists()


def test_the_gpu_chain_refuses_low_memory_a_short_disk_an_uncountersigned_row_a_refused_dry_run_a_refused_swap_dry_run_and_a_dirty_tree(gpu_host):
    assert gpu_host.run("--run", PACKETS_AVAILABLE_GB="2").returncode == 8
    assert gpu_host.run("--run", PACKETS_FREE_DISK_GB="1").returncode == 8
    assert gpu_host.run("--run", STUB_LEDGER_RC="4").returncode == 11
    assert gpu_host.run("--run", STUB_DRY_RC="3").returncode == 3
    assert gpu_host.run("--run", STUB_SWAP_DRY_RC="7").returncode == 8
    (gpu_host.repo / "dirt.txt").write_text("x")
    subprocess.run(["git", "-C", str(gpu_host.repo), "add", "dirt.txt"], check=True, capture_output=True)
    assert gpu_host.run("--run").returncode == 2
    assert "--stop-only" not in gpu_host.swaps() and gpu_host.attempts() == []


def test_the_gpu_chain_forwards_the_gpu_recovery_labels_and_only_those(gpu_host):
    recovery = gpu_host.tmp / "gpu.recovery"
    recovery.write_text("SMOKE_ATTEMPT=gpu-smoke-v2\nFOLD_ATTEMPT=gpu-fold-v2\nRECOVERY_OF=gpu-smoke-v1\n", encoding="utf-8")
    result = gpu_host.run("--run", PACKETS_RECOVERY_FILE=str(recovery))
    assert result.returncode == 0, result.stdout + result.stderr
    smoke = [c for c in gpu_host.driver_calls() if "thinking-smoke-4" in c and "--run" in c.split()]
    fold = [c for c in gpu_host.driver_calls() if "thinking-fold-b" in c and "--run" in c.split()]
    assert all("--attempt-id gpu-smoke-v2" in c and "--recovery-of gpu-smoke-v1" in c for c in smoke)
    assert all("--attempt-id gpu-fold-v2" in c and "--recovery-of gpu-smoke-v1" in c for c in fold)


def test_the_cpu_chain_is_superseded_and_refuses_without_allow_cpu(host):
    result = host.run("--check", NO_ALLOW_CPU="1")
    assert result.returncode == 13 and "SUPERSEDED" in result.stdout and host.attempts() == [] and host.driver_calls() == []
    ok = host.run("--run")
    assert ok.returncode == 0 and host.attempts() == ["thinking-smoke-4", "thinking-fold-b"]
    assert all("--geometry cpu --allow-cpu" in call for call in host.driver_calls())
