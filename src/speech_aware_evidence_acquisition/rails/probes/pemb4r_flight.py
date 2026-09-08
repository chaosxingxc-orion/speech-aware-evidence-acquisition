"""P-EMB-4R flight orchestration -- REGISTERED probe SAEA-PROBE-pemb4r-4100
(``bounded-discovery-probe``): ``docs/readiness/
2026-08-20-pemb4r-preregistration-REGISTERED.md``. MACHINERY ONLY: this
module contains ZERO live model/server contact and is never itself pointed
at a real server -- every test drives ``rails.embedding_client.
MockEmbeddingClient`` / ``rails.local_encoder_client.MockLocalEncoderClient``
or a duck-typed double.

Question (the owner's register-alignment diagnosis, registration section 1):
every prior audio arm matched an UTTERANCE-register query against
WORD-register label keys. This probe re-tests audio (and text) embeddings on
the natural pairing -- utterance query <-> utterance keys -- with labels
demoted to un-embedded VALUE metadata: **query = speech/text embedding, key =
gold TRAIN-split text samples, value = gold TRAIN scenario label -- the
value is used for kNN label voting, never embedded, never rendered into an
embedding request.**

Shared harness (registration section 2):

- **Key bank** (:func:`build_bank_table`): 18 canonical SLURP scenarios x 50
  TRAIN-split ``train.jsonl`` utterance texts each = 900 rows, seed
  :data:`DEFAULT_BANK_SEED` = 20260807, one ``random.Random(seed)`` stream
  walked in SORTED scenario-label order (the SAME "single seeded stream,
  sorted-key order" discipline ``rails.probes.pfew_flight.build_demo_binding``
  already establishes for its own per-sample draws, generalized here to
  per-scenario draws). Reuses ``rails.probes.pfew_flight.
  load_train_demo_pool`` VERBATIM for the underlying TRAIN-split
  (utterance-text -> scenario-label) pool -- never a second miner, never
  ``train_synthetic``. Verified LIVE, read-only, against the real governed
  ``train.jsonl`` during this module's own build mission: every one of the
  18 canonical labels carries >= 50 distinct TRAIN candidates (minimum 211,
  for ``cooking``); the bank is bit-reproducible (two independent draws
  from the same seed produce an IDENTICAL sha256, :data:`BANK_MANIFEST_
  SHA256`, pinned and drift-checked fail-closed by
  :func:`assert_bank_manifest_sha256`). Each bank row's OWN ``gold_scenario``
  field is construction metadata legal under the split philosophy (TRAIN
  gold) -- it is NEVER embedded and NEVER appears in an embedding request
  payload; only ``text`` is ever passed to ``embed_text``.
- **Queries**: audio arms use the frozen 60 SLURP devel samples (split
  identity :data:`EXPECTED_SPLIT_IDENTITY_HASH`) -- ONLY ``sample_id``/
  ``media_relpath`` are ever read off a loaded ``SlurpSample`` anywhere in
  this module (never ``.scenario``/``.action``/``.entities``/``.intent``,
  the DEVEL gold fields loader-legally present on that dataclass -- see
  :func:`assert_never_accesses_frozen_60_gold`, an AST guard scoped
  narrowly to those four attribute names, run at import time and again at
  the top of every gold-adjacent entry point, mirroring ``rails.probes.
  pcorrf_flight.assert_never_references_forbidden_gold_symbols``'s own
  discipline). Text arms use the CONSUMED ``SAEA-PROBE-pkey2-338`` T0
  self-transcript registry (ledger row verified ``consumed = yes`` BEFORE
  it is opened) -- this module reuses ``rails.probes.pemb3m_flight.
  run_cascade_source_check``/``assert_ledger_row_consumed`` VERBATIM
  (never a second implementation of that check).

Seven embedding arms (registration section 3), grouped by the FOUR distinct
embedding models each arm's own bank is embedded against exactly ONCE
(:data:`MODELS`; "arms sharing a model share the bank" -- the SAME 900 bank
vectors serve both an audio arm and a text arm of the SAME model, since
every bank row is TEXT and every model's OWN ``embed_text`` capability
embeds it, never re-embedded per arm):

======  ============  ========  ===============  ===================================
arm     model         query     dim              client / kind
======  ============  ========  ===============  ===================================
A-LCO3  lco3           audio     2048 (proven)    llama.cpp server, ``EmbeddingClient``
T-LCO3  lco3           text      2048 (proven)    SAME server session as A-LCO3
A-LCO7  lco7           audio     measured at gate llama.cpp server, ``EmbeddingClient``,
                                                   server-sanity gated (DROPPED-LCO7 on
                                                   failure, non-blocking)
T-LCO7  lco7           text      measured at gate SAME server session as A-LCO7
A-GLAP  glap           audio     1024             in-process, ``LocalTransformersEncoderClient``,
                                                   import+audio-path sanity gated
T-GLAP  glap           text      1024             SAME in-process client as A-GLAP
T-QW    qw             text      1024             llama.cpp server, text-only
                                                   (``require_marker_verification=False``)
======  ============  ========  ===============  ===================================

LCO-7B's own pooled dim is NOT hardcoded in this module's arm table (unlike
LCO-3B's proven 2048, ``rails.embedding_client.EMBEDDING_DIM``) -- it is
MEASURED at gate time (:func:`run_lco7_server_sanity_gate`) and carried
forward as that arm's own runtime dim for the rest of the flight, a
documented design delta from ``rails.probes.pemb3m_flight``'s own fully
statically-declared ``Pemb3mArm.embedding_dim`` (recorded here for audit:
LCO-7B has no prior proven-dim probe the way LCO-3B does via P-EMB-3M's own
M1 arm).

Environment-gated, documented NOT flown (registration section 3):
``omni-embed-nemotron-3b`` and ``clsp`` -- both carry a real umbrella lock
entry (``resolve_model_binding`` can resolve either), but neither is wired
into :data:`ARMS`; their feasibility is a READ-side, gold-free judgment for
the feasibility matrix (never flown here, never gated here).

C-DECODE (registration section 3 item 8): the frozen core's own closed-set
decode over a RETRIEVAL-SHRUNK label space. Two pieces, both machinery-only
here:

1. :func:`build_arm_retrieval`/:func:`select_retrieval_winner`/
   :func:`build_retrieval_plan_document` -- retrieval (query vector -> top-K
   bank neighbors -> their OWN VALUE-metadata scenario labels, deduplicated)
   is a PURE function of already-flown vectors plus bank metadata and
   involves NO scoring-side (devel) gold whatsoever -- so, per this
   mission's own explicit instruction, it runs FLIGHT-SIDE, in the SAME
   attempt, immediately after the seven embedding arms complete and BEFORE
   C-DECODE fires: the result is a single ``retrieval_plan.json`` (per-
   sample candidate label sets for EVERY arm, plus a resolved ``winner_arm_
   id``), hashed and written under the data root. ``analysis.pemb4r_read``
   later independently RE-DERIVES the SAME retrieval from the SAME flown
   vectors and compares it byte-for-byte against this artifact -- never
   trusts it blindly (the SAME "tri-derivation" discipline ``rails.probes.
   pcorrf_flight``'s own corrective binding hash uses, generalized from a
   single hash equality to a full per-sample structural comparison, since
   the read additionally needs the PER-SAMPLE candidate sets themselves,
   not merely a fingerprint of them).

   **Judgment call, recorded for audit** (the registration's own "winner's
   top-K dedup labels" is not operationally defined, and a GOLD-based
   "best arm" selection is illegal at flight time): :func:`select_
   retrieval_winner` resolves "winner" via a GOLD-FREE, deterministic proxy
   -- the arm with the HIGHEST mean top-1 retrieval cosine across the 60
   queries (a legitimate unsupervised retrieval-confidence signal, ties
   broken by sorted ``arm_id``). This is disclosed plainly in the written
   ``retrieval_plan.json`` (``winner_selection_rule``) and in every receipt
   this module produces; the read reports the winner's identity, never
   hides the mechanical rule that picked it.
2. :func:`run_c_decode_flight` -- builds one closed-set decode prompt per
   sample from that sample's own winner-arm top-5 DEDUPLICATED candidate
   labels, reusing ``rails.probes.pslu_s2_flight.
   closed_set_phase1_supply_packet``/``map_predicted_scenario_to_canonical``
   VERBATIM (:func:`build_c_decode_supply_packet` -- "the FS-NONE
   construction reused verbatim from the pfew machinery", since ``rails.
   probes.pfew_flight``'s own FS-NONE arm is exactly this SAME reused
   phase-1 packet with zero demos; here the closed candidate set is the
   per-sample RETRIEVED set rather than the fixed 18) -- exactly
   :data:`QUERY_N` = 60 generation calls on the pinned q4km core, presenting
   the SAME modality (audio or T0 transcript text) the winner arm's own
   query side used (:func:`assemble_c_decode_messages`). Accuracy/recall
   computation over C-DECODE's own responses stays entirely READ-side
   (``analysis.pemb4r_read``); this module never opens the frozen 60's own
   gold to score anything.

Four gates (registration section 3/5), each fail-closed and disclosed,
run BEFORE any scored contact:

(a) :func:`run_lco7_server_sanity_gate` -- one sanity ``embed_text`` call
    against a freshly spun LCO-7B session; on failure both A-LCO7 and
    T-LCO7 are :data:`STATUS_DROPPED_LCO7` (disclosed, NON-BLOCKING to
    every other arm).
(b) :func:`run_glap_import_and_audio_sanity_gate` -- the pemb3m gate-(b)
    pattern (``rails.local_encoder_client.run_import_feasibility_gate``)
    AMENDED with a second, audio-path sanity embed (P-EMB-3M's own gate (b)
    only sanity-checked ``embed_text``; this probe's GLAP arms need
    ``embed_audio`` too, so the sanity check is extended to cover both
    before either A-GLAP or T-GLAP is trusted) -- never pip-installs
    anything, a missing dependency reports :data:`STATUS_DROPPED_DEPS
    <rails.local_encoder_client.STATUS_DROPPED_DEPS>` and never blocks any
    other arm.
(c) POOLING-DIFFER, carried for the LCO arms (registration section 3):
    ``rails.probes.pemb3m_flight.run_pooling_differ_gate`` reused VERBATIM,
    once per LCO model (LCO-3B, LCO-7B) -- :func:`pooling_override_scope_
    for_model` records the SAME ``pooling_override_present`` flag against
    BOTH that model's own audio arm AND its own text arm (a property of the
    server construction, not of query modality; "the scope tag flows into
    receipts").
(d) :func:`run_encode_only_preflight_gate` -- the charter-mandated
    structural encode-only machine check, reused verbatim
    (``rails.encode_only_check.run_encode_only_machine_check``); this
    module's own name is added to ``rails.encode_only_check.
    PINNED_ENCODE_ONLY_MODULE_NAMES`` (coverage EXTENDED, the check's own
    logic carried unchanged, per this mission's own instruction).
(e) Cascade/T0 source check: ``rails.probes.pemb3m_flight.
    run_cascade_source_check`` reused VERBATIM against the SAME consumed
    ``SAEA-PROBE-pkey2-338`` artifact.

Ceilings (registration section 5, fail-closed): :func:`assert_within_
registered_ceilings` refuses any plan claiming more than :data:`CEILING_
CALLS` = 4500 calls, :data:`CEILING_AUDIO_SECONDS` = 700 metered
audio-seconds, or :data:`CEILING_GPU_HOURS` = 0.5 GPU-hours.
:func:`assert_gpu_hours_within_ceiling` implements the pcorrf section-8
GPU-accounting ruling this mission carries forward: the ceiling's own
ACCOUNTING BASIS is per-call measured-equivalent AND GPU-active occupancy
-- server-alive WALL time is recorded on :class:`GpuHoursAccounting` but
NEVER gates. **Forward rule for the eventual real launcher** (the pcorrf
section-8 ruling's own corrective, carried here verbatim): build the
transport and every payload binding BEFORE spawning any server, so
model-identity hashing never runs while a server session holds VRAM idle.
:func:`build_execution_plan` constructs and ``.validate()``s a
``contracts.ExecutionPlan`` (``execution_profile = "bounded-discovery-
probe"``), mirroring ``rails.probes.pemb3m_flight.build_execution_plan``'s
own pattern.

Manifest persistence (:func:`write_bank_vectors`/:func:`load_bank_vectors`
for the FOUR per-model bank vector sets, :func:`write_query_vectors`/
:func:`load_query_vectors` for the SEVEN per-arm query vector sets): a NEW,
dim-generic, TWO-NAMESPACE scheme (bank-vectors keyed by model, query-
vectors keyed by arm) -- a documented design delta from ``rails.probes.
pemb3m_flight.write_pemb3m_arm_manifest``'s own single per-arm-only
manifest, made necessary by THIS probe's own shared-bank-per-model
construction (pemb3m had no shared-bank concept: every arm owned its own
18-label set). Both namespaces share ONE low-level primitive
(:func:`_write_vector_manifest`/:func:`_load_vector_manifest`) so the
sha256-per-vector, dim-consistency, and count-consistency checks are
written and tested exactly once.

Arm-level (bank-level and query-level) idempotence (the pemb3l/pemb3m abort
lesson): :func:`run_pemb4r_bank_sweep`/:func:`run_pemb4r_query_sweep` each
check ``is_*_complete`` (an already-written, sha256-verified manifest under
the data root) BEFORE invoking a runner callable -- an already-complete
bank/arm's own vectors are loaded from disk and its runner is NEVER called
a second time.

Binding config + sha256 (:func:`build_binding_config_document`/
:func:`binding_config_sha256`/:func:`assert_binding_config_sha256`): covers
the frozen split identity, the bank's own construction parameters (seed,
per-scenario count, PINNED manifest sha256), the T0-transcript-registry
pin, the retrieval K values, and -- for every one of the four models --
its identity RESOLVED FROM THE UMBRELLA LOCK AT CALL TIME (``rails.probes.
pemb3m_flight.resolve_model_binding``, reused verbatim, never a hardcoded
hash in this module's own source).

Zero live model contact, engineering only: every test in this module's own
suite drives ``MockEmbeddingClient``/``MockLocalEncoderClient``/
``MockCoreClient``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ...contracts import ExecutionPlan, assert_execution_scope
from ..adapters.slurp import _INSTRUCTION as _SLU_INSTRUCTION
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..embedding_client import (
    EMBEDDING_DIM as LCO_EMBEDDING_DIM,
)
from ..embedding_client import (
    EmbeddingClientError,
    EmbeddingClientProtocol,
    EmbeddingVector,
)
from ..local_encoder_client import (
    GLAP_EMBEDDING_DIM,
    STATUS_DROPPED_DEPS,
    STATUS_OK,
    ImportFeasibilityResult,
    LocalEncoderClientProtocol,
    run_import_feasibility_gate,
)
from ..supply import SupplyPacket
from .pemb_flight import (
    PembFlightError,
    _npy_bytes,
    _npy_to_array,
    _read_audio_bytes,
    _safe_filename,
)
from .pemb3m_flight import (
    PKEY2_338_ATTEMPT_ID,
    PKEY2_338_RUN_EXPERIMENT_ID,
    PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH,
    PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
    CascadeSourceCheckResult,
    PoolingDifferGateResult,
    assert_ledger_row_consumed,
    resolve_model_binding,
    run_cascade_source_check,
    run_pooling_differ_gate,
)
from .pfew_flight import DemoCandidate
from .pkey_flight import TranscriptRecord, render_txt_transcript_block
from .pslu_flight import (
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
)
from .pslu_s2_flight import (
    ClosedSetMapping,
    canonical_scenario_labels,
    closed_set_phase1_supply_packet,
    map_predicted_scenario_to_canonical,
)

PROBE_ID = "SAEA-PROBE-pemb4r-4100"

# docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md's own
# opening line: "the frozen 60 (split fc9de436...5ee5)" -- configs/probes/
# g0-binding/pslu-sample-devel-n60.json's own split_identity_hash, pinned
# VERBATIM (IDENTICAL to every consumed sibling probe's own value; this
# module redefines the literal itself rather than importing it, the SAME
# decoupling choice ``rails.probes.pcorrf_flight``/``pfew_flight`` each
# record for their own copy).
EXPECTED_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"

QUERY_N = 60  # the frozen 60 SLURP devel samples, every arm's own query side


class Pemb4rFlightError(PembFlightError):
    """A P-EMB-4R input is malformed, a hard count/identity/legality
    invariant is violated, the ontology-miner or frozen-60-gold-access AST
    guard tripped, a registered ceiling was exceeded, or a binding/bank/
    retrieval sha256 drifted from its pinned value. A subclass of
    :class:`~.pemb_flight.PembFlightError` -- every sibling module's
    ``except PembFlightError`` clause catches this without modification."""


# ---------------------------------------------------------------------------
# Guards: ontology-miner ban + the frozen-60-gold-access AST guard (module
# docstring).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise Pemb4rFlightError(
            "rails.probes.pemb4r_flight source references load_slurp_ontology; the canonical "
            "scenario labels come ONLY from configs/probes/g0-binding/pslu-rosters-train-only.json "
            "(rails.probes.pslu_flight.load_pslu_rosters), and the key bank comes ONLY from "
            "rails.probes.pfew_flight.load_train_demo_pool's own direct train.jsonl read"
        )


# Deliberately narrow (module docstring): the four DEVEL-gold attribute
# names ``rails.adapters.slurp.SlurpSample`` carries loader-legally but this
# probe's own research boundary forbids reading anywhere in a flight path.
# ``gold_scenario`` (the BANK's own, TRAIN-split, legal VALUE-metadata
# field) is a DIFFERENT attribute name and never trips this guard.
_FORBIDDEN_FROZEN60_GOLD_ATTRS = frozenset({"scenario", "action", "entities", "intent"})


def _source_accesses_forbidden_frozen60_gold(source: str) -> str | None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_FROZEN60_GOLD_ATTRS:
            return node.attr
    return None


def assert_never_accesses_frozen_60_gold(source: str | None = None) -> None:
    """Legality guard (module docstring): this module's OWN source must
    never dot-access ``.scenario``/``.action``/``.entities``/``.intent`` --
    the frozen 60's own devel-gold fields, loader-legally present on
    ``SlurpSample`` but forbidden anywhere in a flight path. Run at import
    time and again at the top of every gold-adjacent entry point (mirrors
    ``rails.probes.pcorrf_flight.assert_never_references_forbidden_gold_
    symbols``'s own AST-based, never-substring-search discipline)."""

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    offender = _source_accesses_forbidden_frozen60_gold(text)
    if offender is not None:
        raise Pemb4rFlightError(
            f"rails.probes.pemb4r_flight source dot-accesses {offender!r} -- a devel-gold field of "
            "SlurpSample; the frozen 60's gold must never appear anywhere in a flight path "
            "(research boundary, docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md)"
        )


def assert_split_identity_hash(split_identity_hash: str) -> None:
    if split_identity_hash != EXPECTED_SPLIT_IDENTITY_HASH:
        raise Pemb4rFlightError(
            f"split_identity_hash {split_identity_hash!r} does not match the REGISTERED P-EMB-4R "
            f"sample manifest's own hash {EXPECTED_SPLIT_IDENTITY_HASH!r} -- fail-closed"
        )


def _validate_query_samples(samples: Sequence[SlurpSample], *, expected_n: int = QUERY_N) -> None:
    if len(samples) != expected_n:
        raise Pemb4rFlightError(f"requires exactly {expected_n} query sample(s), got {len(samples)}")
    sample_ids = [sample.sample_id for sample in samples]
    if len(set(sample_ids)) != len(sample_ids):
        raise Pemb4rFlightError("duplicate sample_id in samples")


# ---------------------------------------------------------------------------
# Model / arm tables.
# ---------------------------------------------------------------------------

MODEL_LCO3 = "lco3"
MODEL_LCO7 = "lco7"
MODEL_GLAP = "glap"
MODEL_QW = "qw"
MODELS: tuple[str, ...] = (MODEL_LCO3, MODEL_LCO7, MODEL_GLAP, MODEL_QW)

MODEL_LOCK_KEY: Mapping[str, str] = MappingProxyType(
    {
        MODEL_LCO3: "lco-embedding-omni-3b-gguf",
        MODEL_LCO7: "lco-embedding-omni-7b-gguf",
        MODEL_GLAP: "glap",
        MODEL_QW: "qwen3-embedding-0.6b-gguf",
    }
)

# Proven dims (module docstring): LCO-3B (P-EMB-3M's own M1), GLAP, QW are
# ALL already statically known. LCO-7B is deliberately absent here -- its
# dim is MEASURED at gate time (run_lco7_server_sanity_gate), never assumed.
QWEN3_EMB_EMBEDDING_DIM = 1024
KNOWN_MODEL_DIM: Mapping[str, int] = MappingProxyType(
    {MODEL_LCO3: LCO_EMBEDDING_DIM, MODEL_GLAP: GLAP_EMBEDDING_DIM, MODEL_QW: QWEN3_EMB_EMBEDDING_DIM}
)

ARM_A_LCO3 = "a-lco3"
ARM_A_LCO7 = "a-lco7"
ARM_A_GLAP = "a-glap"
ARM_T_LCO3 = "t-lco3"
ARM_T_LCO7 = "t-lco7"
ARM_T_GLAP = "t-glap"
ARM_T_QW = "t-qw"

KIND_LLAMACPP_SERVER = "llamacpp-server"
KIND_LLAMACPP_SERVER_TEXT_ONLY = "llamacpp-server-text-only"
KIND_IN_PROCESS_TRANSFORMERS = "in-process-transformers"


@dataclass(frozen=True)
class Pemb4rArm:
    arm_id: str
    model: str
    query_kind: str  # "audio" | "text"
    kind: str


ARMS: tuple[Pemb4rArm, ...] = (
    Pemb4rArm(ARM_A_LCO3, MODEL_LCO3, "audio", KIND_LLAMACPP_SERVER),
    Pemb4rArm(ARM_A_LCO7, MODEL_LCO7, "audio", KIND_LLAMACPP_SERVER),
    Pemb4rArm(ARM_A_GLAP, MODEL_GLAP, "audio", KIND_IN_PROCESS_TRANSFORMERS),
    Pemb4rArm(ARM_T_LCO3, MODEL_LCO3, "text", KIND_LLAMACPP_SERVER),
    Pemb4rArm(ARM_T_LCO7, MODEL_LCO7, "text", KIND_LLAMACPP_SERVER),
    Pemb4rArm(ARM_T_GLAP, MODEL_GLAP, "text", KIND_IN_PROCESS_TRANSFORMERS),
    Pemb4rArm(ARM_T_QW, MODEL_QW, "text", KIND_LLAMACPP_SERVER_TEXT_ONLY),
)
ARM_IDS: tuple[str, ...] = tuple(arm.arm_id for arm in ARMS)
ARMS_BY_ID: Mapping[str, Pemb4rArm] = MappingProxyType({arm.arm_id: arm for arm in ARMS})
AUDIO_ARM_IDS: tuple[str, ...] = tuple(arm.arm_id for arm in ARMS if arm.query_kind == "audio")
TEXT_ARM_IDS: tuple[str, ...] = tuple(arm.arm_id for arm in ARMS if arm.query_kind == "text")
ARM_IDS_BY_MODEL: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {model: tuple(arm.arm_id for arm in ARMS if arm.model == model) for model in MODELS}
)


def arm_run_id(arm_id: str) -> str:
    if arm_id not in ARMS_BY_ID:
        raise Pemb4rFlightError(f"arm_run_id: unknown arm_id {arm_id!r}, expected one of {ARM_IDS}")
    return f"{PROBE_ID}/{arm_id}"


# ---------------------------------------------------------------------------
# Bank builder (module docstring).
# ---------------------------------------------------------------------------

BANK_N_SCENARIOS = 18
BANK_PER_SCENARIO_N = 50
BANK_TOTAL_N = BANK_N_SCENARIOS * BANK_PER_SCENARIO_N  # 900
DEFAULT_BANK_SEED = 20260807

BANK_MANIFEST_SCHEMA = "saea-pemb4r-bank-v1"


@dataclass(frozen=True)
class BankEntry:
    bank_id: str
    gold_scenario: str  # TRAIN-split VALUE metadata -- never embedded
    text: str
    text_sha256: str
    train_sample_id: str

    def as_json(self) -> dict[str, object]:
        return {
            "bank_id": self.bank_id,
            "gold_scenario": self.gold_scenario,
            "text": self.text,
            "text_sha256": self.text_sha256,
            "train_sample_id": self.train_sample_id,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "BankEntry":
        return cls(
            bank_id=str(document["bank_id"]),
            gold_scenario=str(document["gold_scenario"]),
            text=str(document["text"]),
            text_sha256=str(document["text_sha256"]),
            train_sample_id=str(document["train_sample_id"]),
        )


@dataclass(frozen=True)
class BankTable:
    entries: tuple[BankEntry, ...]
    seed: int
    per_scenario_n: int


def build_bank_table(
    pool: Mapping[str, tuple[DemoCandidate, ...]],
    canonical_labels: Sequence[str],
    *,
    seed: int = DEFAULT_BANK_SEED,
    per_scenario_n: int = BANK_PER_SCENARIO_N,
) -> BankTable:
    """Deterministic per-scenario sampling (module docstring): a SINGLE
    ``random.Random(seed)`` stream walked once per label, in SORTED label
    order -- the SAME "one seeded stream, sorted-key order" discipline
    ``rails.probes.pfew_flight.build_demo_binding`` already establishes.
    Pure, offline, no I/O of its own -- ``pool`` is an ALREADY-LOADED TRAIN
    demo pool (``rails.probes.pfew_flight.load_train_demo_pool(lock, root)``,
    reused verbatim; this function never opens ``train.jsonl`` itself, the
    SAME "loading is the caller's job, construction is pure" split ``rails.
    probes.pfew_flight.build_demo_binding`` already establishes for its own
    ``demo_pool`` parameter -- makes this function trivially testable
    against a small synthetic pool without a real governed carrier)."""

    labels = tuple(sorted(canonical_labels))
    if len(labels) != len(set(labels)):
        raise Pemb4rFlightError("build_bank_table: duplicate canonical label")
    rng = random.Random(seed)
    entries: list[BankEntry] = []
    for label in labels:
        candidates: tuple[DemoCandidate, ...] = pool.get(label, ())
        if len(candidates) < per_scenario_n:
            raise Pemb4rFlightError(
                f"train demo pool covers only {len(candidates)} TRAIN candidate(s) for scenario "
                f"{label!r}; the bank needs >= {per_scenario_n}"
            )
        chosen_indices = sorted(rng.sample(range(len(candidates)), per_scenario_n))
        for index, candidate_index in enumerate(chosen_indices):
            candidate = candidates[candidate_index]
            entries.append(
                BankEntry(
                    bank_id=f"bank-{label}-{index:03d}",
                    gold_scenario=label,
                    text=candidate.utterance_text,
                    text_sha256=hashlib.sha256(candidate.utterance_text.encode("utf-8")).hexdigest(),
                    train_sample_id=candidate.train_sample_id,
                )
            )
    return BankTable(entries=tuple(entries), seed=seed, per_scenario_n=per_scenario_n)


def validate_bank_table(
    bank: BankTable,
    *,
    expected_n_scenarios: int = BANK_N_SCENARIOS,
    expected_per_scenario_n: int = BANK_PER_SCENARIO_N,
) -> None:
    expected_total = expected_n_scenarios * expected_per_scenario_n
    if len(bank.entries) != expected_total:
        raise Pemb4rFlightError(
            f"bank carries {len(bank.entries)} entries, expected exactly {expected_total} "
            f"({expected_n_scenarios} scenarios x {expected_per_scenario_n})"
        )
    ids = [entry.bank_id for entry in bank.entries]
    if len(set(ids)) != len(ids):
        raise Pemb4rFlightError("bank carries a duplicate bank_id")
    train_ids = [entry.train_sample_id for entry in bank.entries]
    if len(set(train_ids)) != len(train_ids):
        raise Pemb4rFlightError("bank carries a duplicate train_sample_id (double-counted TRAIN sentence)")
    counts: dict[str, int] = {}
    for entry in bank.entries:
        counts[entry.gold_scenario] = counts.get(entry.gold_scenario, 0) + 1
    if len(counts) != expected_n_scenarios:
        raise Pemb4rFlightError(f"bank spans {len(counts)} distinct scenario(s), expected {expected_n_scenarios}")
    uneven = {label: count for label, count in counts.items() if count != expected_per_scenario_n}
    if uneven:
        raise Pemb4rFlightError(f"bank scenario counts are not all {expected_per_scenario_n}: {uneven}")


def bank_table_to_json(bank: BankTable) -> dict[str, object]:
    return {
        "schema": BANK_MANIFEST_SCHEMA,
        "seed": bank.seed,
        "per_scenario_n": bank.per_scenario_n,
        "entries": [entry.as_json() for entry in bank.entries],
    }


def bank_manifest_sha256(bank: BankTable) -> str:
    canonical = json.dumps([entry.as_json() for entry in bank.entries], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Pinned against the REAL governed SLURP train.jsonl at the time this module
# was built (module docstring): verified LIVE, read-only -- two independent
# seeded draws produced a BIT-IDENTICAL sha256 (the determinism proof this
# mission's own report cites). A future train.jsonl edit drifts this digest
# and refuses fail-closed via assert_bank_manifest_sha256.
BANK_MANIFEST_SHA256 = "5f48895107d715a7eae2954fe56f833455d33df3d6527e3643a0b0c924f5b112"


def assert_bank_manifest_sha256(bank: BankTable, *, expected: str = BANK_MANIFEST_SHA256) -> None:
    actual = bank_manifest_sha256(bank)
    if actual != expected:
        raise Pemb4rFlightError(
            f"bank manifest sha256 {actual!r} does not match the pinned {expected!r} -- train.jsonl "
            "or the bank construction has drifted; refusing (fail-closed)"
        )


def _bank_manifest_path(root: Path) -> Path:
    return Path(root) / "derived" / "embeddings" / PROBE_ID / "bank" / "manifest.json"


def write_bank_manifest(root: Path, bank: BankTable) -> Path:
    from ...e0.artifacts import write_json_artifact

    path = _bank_manifest_path(root)
    write_json_artifact(path, bank_table_to_json(bank))
    return path


def load_bank_manifest(root: Path, *, expected_sha256: str | None = BANK_MANIFEST_SHA256) -> BankTable:
    """``expected_sha256`` defaults to the module's own pinned :data:`BANK_
    MANIFEST_SHA256` (real-flight fail-closed drift check, unchanged for
    every real caller); pass ``None`` to skip the pin check entirely -- the
    SAME seam ``rails.probes.pemb3m_flight.run_cascade_source_check``'s own
    ``expected_registry_sha256`` parameter establishes, used here by this
    module's own test suite to round-trip a small synthetic bank that
    structurally satisfies :func:`validate_bank_table` without matching the
    real governed carrier's own pinned content."""

    path = _bank_manifest_path(root)
    if not path.is_file():
        raise Pemb4rFlightError(f"bank manifest missing: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Pemb4rFlightError(f"cannot read bank manifest {path}: {error}") from error
    if not isinstance(document, Mapping) or document.get("schema") != BANK_MANIFEST_SCHEMA:
        raise Pemb4rFlightError(f"{path}: schema must be {BANK_MANIFEST_SCHEMA!r}")
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise Pemb4rFlightError(f"{path}: no entries")
    entries: list[BankEntry] = []
    for raw in raw_entries:
        entry = BankEntry.from_json(raw)
        if entry.text_sha256 != hashlib.sha256(entry.text.encode("utf-8")).hexdigest():
            raise Pemb4rFlightError(f"{path}: text_sha256 mismatch for bank_id {entry.bank_id!r}")
        entries.append(entry)
    bank = BankTable(entries=tuple(entries), seed=int(document["seed"]), per_scenario_n=int(document["per_scenario_n"]))
    ids = [entry.bank_id for entry in bank.entries]
    if len(set(ids)) != len(ids):
        raise Pemb4rFlightError(f"{path}: duplicate bank_id in manifest")
    if expected_sha256 is not None:
        assert_bank_manifest_sha256(bank, expected=expected_sha256)
    return bank


# ---------------------------------------------------------------------------
# Query-side loading: T0 transcript registry (text arms) -- reused verbatim.
# PKEY2_338_RUN_EXPERIMENT_ID / PKEY2_338_ATTEMPT_ID / PKEY2_338_TRANSCRIPT_
# REGISTRY_RELPATH / PKEY2_338_TRANSCRIPT_REGISTRY_SHA256 are imported above
# from rails.probes.pemb3m_flight and re-exported via __all__ below, never
# re-derived here (module docstring: "reused VERBATIM").
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Ceilings (registration section 5, fail-closed) + GPU accounting (the
# pcorrf section-8 ruling, module docstring).
# ---------------------------------------------------------------------------

CEILING_CALLS = 4500
CEILING_AUDIO_SECONDS = 700
CEILING_GPU_HOURS = 0.5

PLANNED_BANK_CONTACTS = len(MODELS) * BANK_TOTAL_N  # 4 * 900 = 3600
PLANNED_AUDIO_QUERY_CONTACTS = len(AUDIO_ARM_IDS) * QUERY_N  # 3 * 60 = 180
PLANNED_TEXT_QUERY_CONTACTS = len(TEXT_ARM_IDS) * QUERY_N  # 4 * 60 = 240
PLANNED_C_DECODE_CONTACTS = QUERY_N  # 60
GATE_CONTACTS_MAX = 20

DEFAULT_PLANNED_MODEL_CALLS = (
    PLANNED_BANK_CONTACTS + PLANNED_AUDIO_QUERY_CONTACTS + PLANNED_TEXT_QUERY_CONTACTS + PLANNED_C_DECODE_CONTACTS + GATE_CONTACTS_MAX
)  # 4100
DEFAULT_PLANNED_GPU_HOURS = CEILING_GPU_HOURS
# Registration section 5: "3x182.26 planned" = 546.78 s -> ceil 547 (mirrors
# rails.probes.pcorrf_flight.DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS's own
# "ceil(4*182.26)=729.04 -> 730" convention).
DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS = 547


def assert_within_registered_ceilings(*, calls: int, audio_seconds: float, gpu_hours: float) -> None:
    if calls > CEILING_CALLS:
        raise Pemb4rFlightError(f"{calls} calls exceeds the registered ceiling of {CEILING_CALLS}")
    if audio_seconds > CEILING_AUDIO_SECONDS:
        raise Pemb4rFlightError(
            f"{audio_seconds} metered audio-second(s) exceeds the registered ceiling of {CEILING_AUDIO_SECONDS}"
        )
    if gpu_hours > CEILING_GPU_HOURS:
        raise Pemb4rFlightError(f"{gpu_hours} GPU-hour(s) exceeds the registered ceiling of {CEILING_GPU_HOURS}")


@dataclass(frozen=True)
class GpuHoursAccounting:
    """The pcorrf section-8 ruling's own three figures (module docstring):
    ``wall_hours`` is recorded but NEVER gates; ``gpu_active_hours`` and
    ``measured_equivalent_hours`` are the two bases :func:`assert_gpu_
    hours_within_ceiling` actually checks."""

    wall_hours: float
    gpu_active_hours: float
    measured_equivalent_hours: float


def assert_gpu_hours_within_ceiling(accounting: GpuHoursAccounting, *, ceiling: float = CEILING_GPU_HOURS) -> None:
    if accounting.gpu_active_hours > ceiling:
        raise Pemb4rFlightError(
            f"GPU-active occupancy {accounting.gpu_active_hours} h exceeds the registered ceiling of "
            f"{ceiling} h (wall={accounting.wall_hours} h, recorded but never gates -- pcorrf section-8 ruling)"
        )
    if accounting.measured_equivalent_hours > ceiling:
        raise Pemb4rFlightError(
            f"measured-equivalent GPU accounting {accounting.measured_equivalent_hours} h exceeds the "
            f"registered ceiling of {ceiling} h (wall={accounting.wall_hours} h, recorded but never gates)"
        )


# ---------------------------------------------------------------------------
# contracts.ExecutionPlan integration.
# ---------------------------------------------------------------------------


def build_execution_plan(
    *,
    lock: Mapping[str, object],
    attempt_id: str | None = None,
    planned_model_calls: int = DEFAULT_PLANNED_MODEL_CALLS,
    planned_gpu_hours: float = DEFAULT_PLANNED_GPU_HOURS,
    planned_speech_audio_seconds: int = DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
    carrier_lock_key: str = "slurp",
) -> ExecutionPlan:
    execution_profile = assert_execution_scope("bounded-discovery-probe")
    assert_within_registered_ceilings(
        calls=planned_model_calls, audio_seconds=planned_speech_audio_seconds, gpu_hours=planned_gpu_hours
    )
    plan = ExecutionPlan(
        run_id=PROBE_ID,
        execution_profile=execution_profile,
        carrier_lock_key=carrier_lock_key,
        split_role="discovery",
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        planned_model_calls=planned_model_calls,
        planned_gpu_hours=planned_gpu_hours,
        planned_speech_audio_seconds=planned_speech_audio_seconds,
        protocol_hash=binding_config_sha256(lock),
        attempt_id=attempt_id,
    )
    return plan.validate()


# ---------------------------------------------------------------------------
# Binding config + sha256 (module docstring).
# ---------------------------------------------------------------------------

BINDING_CONFIG_SCHEMA = "saea-pemb4r-binding-config-v1"

RETRIEVAL_K_PRIMARY = 5
RETRIEVAL_K_REPORTED: tuple[int, ...] = (1, 3)


def build_binding_config_document(lock: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": BINDING_CONFIG_SCHEMA,
        "split_identity_hash": EXPECTED_SPLIT_IDENTITY_HASH,
        "query_n": QUERY_N,
        "bank": {
            "n_scenarios": BANK_N_SCENARIOS,
            "per_scenario_n": BANK_PER_SCENARIO_N,
            "seed": DEFAULT_BANK_SEED,
            "manifest_sha256": BANK_MANIFEST_SHA256,
        },
        "t0_transcript_registry_sha256": PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
        "retrieval": {"k_primary": RETRIEVAL_K_PRIMARY, "k_reported": list(RETRIEVAL_K_REPORTED)},
        "arms": [
            {
                "arm_id": arm.arm_id,
                "model": arm.model,
                "query_kind": arm.query_kind,
                "kind": arm.kind,
                "model_binding": resolve_model_binding(lock, MODEL_LOCK_KEY[arm.model]),
            }
            for arm in sorted(ARMS, key=lambda arm: arm.arm_id)
        ],
    }


def binding_config_sha256(lock: Mapping[str, object]) -> str:
    canonical = json.dumps(build_binding_config_document(lock), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# HISTORICAL. Pinned against the umbrella lock's own content for the four
# model keys as it stood when this module was written and when the
# 2026-08-20 P-EMB-4R flight sealed (docs/checks/speech-aware-evidence-
# acquisition/2026-08-20-pemb4r-flight/{flight-receipt,flight-state,
# config-values}.json all carry this exact value under
# "binding_config_sha256"). Kept ONLY so those sealed receipts stay
# readable against a named constant -- no live code checks against this
# value any more; see BINDING_CONFIG_SHA256 below for the constant
# assert_binding_config_sha256 actually enforces.
BINDING_CONFIG_SHA256_AT_FLIGHT = "a193f63422ae4c990911752f3d14f37400c57d73cc4908af84d698dd3ccce17a"

# Re-pinned 2026-09-08 against umbrella commit faebc8f (owner Decision 11-D:
# "commit the pending umbrella changes AND re-pin the study's P-EMB
# hashes", chosen over reverting the lock; mirrors rails.probes.
# pemb3m_flight.BINDING_CONFIG_SHA256's own re-pin note). The umbrella
# lock's own entry for one of these four keys -- lco-embedding-omni-3b-
# gguf -- changed in that commit: from an unresolved local candidate
# (source.kind "observed-local", id UNRESOLVED_LOCAL_SOURCE, revision
# UNRESOLVED_LOCAL_REVISION, lifecycle LOCAL_CANDIDATE, aggregate-only
# verification) to a resolved HF source (marksverdhei/LCO-Embedding-Omni-
# 3B-GGUF, revision af8a36fbb6e7629c9dbcb218478c6b1477b36e09, lifecycle
# AUXILIARY, profile speech-aware-tools, 3 verified files with real
# per-file sha256). lco-embedding-omni-7b-gguf, glap and
# qwen3-embedding-0.6b-gguf are byte-identical across the two lock
# commits -- this is NOT incidental lock growth riding along; it is the
# bound model's own identity becoming resolved, so the digest change is
# deliberate reviewed content, never silently absorbed drift.
#
# The lock's PRE-faebc8f entry for lco-embedding-omni-3b-gguf carried no
# per-file sha256 at all (only an aggregate size_bytes/files count), so
# the lock's own metadata cannot prove the model bytes are identical
# across the two commits -- only that the aggregate size moved by 1,462
# bytes (6238572624 -> 6238571162) as the file count dropped 5 -> 3. (For
# context, not a substitute for that proof: the sealed 2026-08-20
# P-EMB-3M/P-EMB-4R flight receipts independently hashed the local
# LCO-Embedding-Omni-3B-Q8_0.gguf and its mmproj file at flight time --
# before the lock carried any per-file hash for this model -- and both
# measured hashes equal the two GGUF hashes the resolved lock entry now
# pins; the entry's third file, README.md, was never independently hashed
# by either flight.) Any future reuse of this embedder must re-verify
# against the resolved lock entry rather than lean on this note.
BINDING_CONFIG_SHA256 = "c45a10ae3b2459662e13a71399837987c8e963ee97bb8ebeba8da3b8a52cb25e"


def assert_binding_config_sha256(lock: Mapping[str, object]) -> None:
    actual = binding_config_sha256(lock)
    if actual != BINDING_CONFIG_SHA256:
        raise Pemb4rFlightError(
            f"P-EMB-4R binding config sha256 {actual!r} does not match the pinned "
            f"{BINDING_CONFIG_SHA256!r} -- the arm table, bank pin, T0 registry pin, retrieval K "
            "values, or the umbrella lock's own content for one of the four model keys has drifted; "
            "refusing (fail-closed)"
        )


# ---------------------------------------------------------------------------
# Gate (a): LCO-7B server sanity (DROPPED-LCO7 on failure, non-blocking).
# ---------------------------------------------------------------------------

STATUS_DROPPED_LCO7 = "DROPPED-LCO7"


@dataclass(frozen=True)
class Lco7SanityResult:
    status: str  # STATUS_OK | STATUS_DROPPED_LCO7
    detail: str
    measured_dim: int | None
    sanity_vector: EmbeddingVector | None = None


def run_lco7_server_sanity_gate(
    *, client: EmbeddingClientProtocol, sanity_text: str = "sanity check"
) -> Lco7SanityResult:
    """One sanity ``embed_text`` call against a freshly spun LCO-7B session
    -- MEASURES this session's own pooled dim (module docstring: never
    hardcoded). Any :class:`~rails.embedding_client.EmbeddingClientError`
    (marker mismatch, malformed response, transport failure) is caught and
    reported as :data:`STATUS_DROPPED_LCO7`, disclosed, NON-BLOCKING to
    every other arm -- this function never raises for that case."""

    try:
        client.verify_media_marker()
        vector = client.embed_text(contact_id="a-lco7-sanity", text=sanity_text)
    except EmbeddingClientError as error:
        return Lco7SanityResult(status=STATUS_DROPPED_LCO7, detail=str(error), measured_dim=None)
    return Lco7SanityResult(
        status=STATUS_OK,
        detail=f"LCO-7B server sanity embed succeeded (measured dim {vector.dims})",
        measured_dim=vector.dims,
        sanity_vector=vector,
    )


# ---------------------------------------------------------------------------
# Gate (b): GLAP import + audio-path sanity (the pemb3m gate-(b) amendment).
# ---------------------------------------------------------------------------


def run_glap_import_and_audio_sanity_gate(
    *,
    model_id: str,
    loader: Callable[[], LocalEncoderClientProtocol],
    sanity_text: str = "sanity check",
    sanity_audio_bytes: bytes,
) -> ImportFeasibilityResult:
    """AMENDS ``rails.local_encoder_client.run_import_feasibility_gate``'s
    own text-only sanity (module docstring): first the SAME text sanity
    check that pattern already performs, then -- only if that succeeded --
    one ADDITIONAL ``embed_audio`` sanity call, since this probe's GLAP arms
    (A-GLAP/T-GLAP) both depend on the audio path working, unlike P-EMB-3M's
    own GLAP control which this codebase's gate (b) never actually
    exercised on audio. ``sanity_audio_bytes`` is caller-supplied (this
    module never synthesizes audio, mirrors ``rails.probes.pemb3m_flight.
    run_pooling_differ_gate``'s own injected ``audio_bytes`` parameter)."""

    text_result = run_import_feasibility_gate(arm_id=MODEL_GLAP, model_id=model_id, loader=loader, sanity_text=sanity_text)
    if text_result.status != STATUS_OK:
        return text_result
    try:
        client = loader()
        audio_vector = client.embed_audio(contact_id=f"{MODEL_GLAP}-audio-sanity", audio_bytes=sanity_audio_bytes)
    except ImportError as error:
        return ImportFeasibilityResult(
            arm_id=MODEL_GLAP,
            model_id=model_id,
            status=STATUS_DROPPED_DEPS,
            detail=f"text sanity OK but audio-path sanity failed: {error}",
        )
    return ImportFeasibilityResult(
        arm_id=MODEL_GLAP,
        model_id=model_id,
        status=STATUS_OK,
        detail=f"text+audio sanity succeeded (text dim {text_result.sanity_vector.dims}, audio dim {audio_vector.dims})",
        sanity_vector=audio_vector,
    )


# ---------------------------------------------------------------------------
# Gate (c): POOLING-DIFFER, carried for the LCO arms (module docstring).
# ---------------------------------------------------------------------------

POOLING_OVERRIDE_SCOPE_TAG = "POOLING-OVERRIDE-PRESENT"


def pooling_override_scope_for_model(model: str, pooling_override_present: bool) -> dict[str, object]:
    """Records the SAME ``pooling_override_present`` flag (from ``rails.
    probes.pemb3m_flight.run_pooling_differ_gate``, reused verbatim, called
    ONCE per LCO model on its own audio-arm session) against BOTH that
    model's own audio arm AND its own text arm -- a property of the server
    construction, not of query modality ("the scope tag flows into
    receipts")."""

    if model not in ARM_IDS_BY_MODEL:
        raise Pemb4rFlightError(f"pooling_override_scope_for_model: unknown model {model!r}")
    return {
        "model": model,
        "pooling_override_present": pooling_override_present,
        "scope_tag": POOLING_OVERRIDE_SCOPE_TAG if pooling_override_present else None,
        "scoped_arm_ids": ARM_IDS_BY_MODEL[model],
    }


# ---------------------------------------------------------------------------
# Gate (d): encode-only structural machine check.
# ---------------------------------------------------------------------------


def run_encode_only_preflight_gate():
    from ..encode_only_check import run_encode_only_machine_check

    return run_encode_only_machine_check()


# ---------------------------------------------------------------------------
# Gate (e): cascade/T0 source check -- reused verbatim.
# ---------------------------------------------------------------------------


def run_pemb4r_cascade_source_check(
    *, data_root: Path, ledger_text: str, expected_sample_ids: frozenset[str]
) -> CascadeSourceCheckResult:
    """Thin, named wrapper over ``rails.probes.pemb3m_flight.
    run_cascade_source_check`` (module docstring: reused VERBATIM, never a
    second implementation) -- this probe's own text arms depend on the SAME
    consumed ``SAEA-PROBE-pkey2-338`` T0 self-transcript registry P-EMB-3M's
    own M4 (CASCADE) arm already located and pinned."""

    return run_cascade_source_check(data_root=data_root, ledger_text=ledger_text, expected_sample_ids=expected_sample_ids)


# ---------------------------------------------------------------------------
# Generic dim-generic vector-manifest primitive (module docstring: shared by
# both the bank-vectors and query-vectors namespaces).
# ---------------------------------------------------------------------------

VECTOR_MANIFEST_SCHEMA = "saea-pemb4r-vectors-manifest-v1"


@dataclass(frozen=True)
class LoadedVectorSet:
    owner: str
    dims: int
    vectors: Mapping[str, object]  # contact_id -> numpy array


def _write_vector_manifest(out_dir: Path, *, owner: str, vectors: Sequence[EmbeddingVector]) -> Path:
    if not vectors:
        raise Pemb4rFlightError(f"_write_vector_manifest({owner!r}): vectors must be non-empty")
    dims = vectors[0].dims
    entries: list[dict[str, object]] = []
    seen_safe: dict[str, str] = {}
    for vector in vectors:
        if vector.dims != dims:
            raise Pemb4rFlightError(
                f"_write_vector_manifest({owner!r}): vector for {vector.contact_id!r} has dim "
                f"{vector.dims} != this set's own dim {dims}"
            )
        safe_id = _safe_filename(vector.contact_id)
        if safe_id in seen_safe and seen_safe[safe_id] != vector.contact_id:
            raise Pemb4rFlightError(
                f"_write_vector_manifest({owner!r}): contact ids {seen_safe[safe_id]!r} and "
                f"{vector.contact_id!r} both sanitize to filename {safe_id!r}"
            )
        seen_safe[safe_id] = vector.contact_id
        path = out_dir / f"{safe_id}.npy"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _npy_bytes(vector.values)
        path.write_bytes(data)
        entries.append(
            {
                "contact_id": vector.contact_id,
                "relpath": f"{safe_id}.npy",
                "dims": len(vector.values),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    entries.sort(key=lambda entry: entry["contact_id"])
    document = {
        "schema": VECTOR_MANIFEST_SCHEMA,
        "owner": owner,
        "dims": dims,
        "count": len(entries),
        "entries": entries,
    }
    from ...e0.artifacts import write_json_artifact

    manifest_path = out_dir / "manifest.json"
    write_json_artifact(manifest_path, document)
    return manifest_path


def _load_vector_manifest(out_dir: Path, *, expected_owner: str, expected_count: int | None = None) -> LoadedVectorSet:
    import numpy as np

    manifest_path = out_dir / "manifest.json"
    if not manifest_path.is_file():
        raise Pemb4rFlightError(f"vector manifest missing for {expected_owner!r}: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Pemb4rFlightError(f"cannot read vector manifest {manifest_path}: {error}") from error
    if not isinstance(document, Mapping) or document.get("schema") != VECTOR_MANIFEST_SCHEMA:
        raise Pemb4rFlightError(f"{manifest_path}: schema must be {VECTOR_MANIFEST_SCHEMA!r}")
    if document.get("owner") != expected_owner:
        raise Pemb4rFlightError(f"{manifest_path}: owner {document.get('owner')!r} != expected {expected_owner!r}")
    dims = document.get("dims")
    if not isinstance(dims, int) or isinstance(dims, bool) or dims <= 0:
        raise Pemb4rFlightError(f"{manifest_path}: dims must be a positive integer, got {dims!r}")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise Pemb4rFlightError(f"{manifest_path}: no entries")

    vectors: dict[str, object] = {}
    for entry in entries:
        contact_id = entry.get("contact_id")
        relpath = entry.get("relpath")
        expected_sha256 = entry.get("sha256")
        if not isinstance(contact_id, str) or not contact_id:
            raise Pemb4rFlightError(f"{manifest_path}: entry missing non-empty contact_id: {entry!r}")
        if contact_id in vectors:
            raise Pemb4rFlightError(f"{manifest_path}: duplicate contact_id {contact_id!r}")
        vector_path = out_dir / str(relpath)
        if not vector_path.is_file():
            raise Pemb4rFlightError(f"{manifest_path}: vector file missing for {contact_id!r}: {vector_path}")
        data = vector_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Pemb4rFlightError(f"{manifest_path}: sha256 mismatch for {contact_id!r}")
        array = _npy_to_array(data)
        if array.shape != (dims,):
            raise Pemb4rFlightError(f"{manifest_path}: vector for {contact_id!r} has shape {array.shape}, expected ({dims},)")
        if not np.isfinite(array).all():
            raise Pemb4rFlightError(f"{manifest_path}: vector for {contact_id!r} contains a non-finite value")
        vectors[contact_id] = array

    if expected_count is not None and len(vectors) != expected_count:
        raise Pemb4rFlightError(f"{manifest_path}: {len(vectors)} vector(s), expected exactly {expected_count}")
    if document.get("count") != len(vectors):
        raise Pemb4rFlightError(f"{manifest_path}: count {document.get('count')!r} != {len(vectors)} loaded entries")

    return LoadedVectorSet(owner=expected_owner, dims=dims, vectors=MappingProxyType(vectors))


def _bank_vectors_dir(root: Path, model: str) -> Path:
    return Path(root) / "derived" / "embeddings" / PROBE_ID / "bank-vectors" / model


def _query_vectors_dir(root: Path, arm_id: str) -> Path:
    return Path(root) / "derived" / "embeddings" / arm_run_id(arm_id) / "query"


def is_bank_vectors_complete(root: Path, model: str) -> bool:
    return (_bank_vectors_dir(root, model) / "manifest.json").is_file()


def is_query_vectors_complete(root: Path, arm_id: str) -> bool:
    return (_query_vectors_dir(root, arm_id) / "manifest.json").is_file()


def write_bank_vectors(root: Path, model: str, vectors: Sequence[EmbeddingVector]) -> Path:
    if model not in MODELS:
        raise Pemb4rFlightError(f"write_bank_vectors: unknown model {model!r}")
    return _write_vector_manifest(_bank_vectors_dir(root, model), owner=f"bank:{model}", vectors=vectors)


def load_bank_vectors(root: Path, model: str, *, expected_count: int = BANK_TOTAL_N) -> LoadedVectorSet:
    if model not in MODELS:
        raise Pemb4rFlightError(f"load_bank_vectors: unknown model {model!r}")
    return _load_vector_manifest(_bank_vectors_dir(root, model), expected_owner=f"bank:{model}", expected_count=expected_count)


def write_query_vectors(root: Path, arm_id: str, vectors: Sequence[EmbeddingVector]) -> Path:
    if arm_id not in ARMS_BY_ID:
        raise Pemb4rFlightError(f"write_query_vectors: unknown arm_id {arm_id!r}")
    return _write_vector_manifest(_query_vectors_dir(root, arm_id), owner=f"query:{arm_id}", vectors=vectors)


def load_query_vectors(root: Path, arm_id: str, *, expected_count: int = QUERY_N) -> LoadedVectorSet:
    if arm_id not in ARMS_BY_ID:
        raise Pemb4rFlightError(f"load_query_vectors: unknown arm_id {arm_id!r}")
    return _load_vector_manifest(_query_vectors_dir(root, arm_id), expected_owner=f"query:{arm_id}", expected_count=expected_count)


# ---------------------------------------------------------------------------
# Bank / query embedding runners.
# ---------------------------------------------------------------------------


def run_server_bank_embedding(*, client: EmbeddingClientProtocol, bank: BankTable) -> tuple[EmbeddingVector, ...]:
    client.verify_media_marker()
    return tuple(client.embed_text(contact_id=entry.bank_id, text=entry.text) for entry in bank.entries)


def run_local_bank_embedding(*, client: LocalEncoderClientProtocol, bank: BankTable) -> tuple[EmbeddingVector, ...]:
    return tuple(client.embed_text(contact_id=entry.bank_id, text=entry.text) for entry in bank.entries)


def run_server_audio_query(
    *, client: EmbeddingClientProtocol, samples: Sequence[SlurpSample], data_root: Path
) -> tuple[EmbeddingVector, ...]:
    assert_never_accesses_frozen_60_gold()
    _validate_query_samples(samples)
    client.verify_media_marker()
    return tuple(
        client.embed_audio(contact_id=sample.sample_id, audio_bytes=_read_audio_bytes(data_root, sample.media_relpath))
        for sample in samples
    )


def run_local_audio_query(
    *, client: LocalEncoderClientProtocol, samples: Sequence[SlurpSample], data_root: Path
) -> tuple[EmbeddingVector, ...]:
    assert_never_accesses_frozen_60_gold()
    _validate_query_samples(samples)
    return tuple(
        client.embed_audio(contact_id=sample.sample_id, audio_bytes=_read_audio_bytes(data_root, sample.media_relpath))
        for sample in samples
    )


def run_server_text_query(
    *, client: EmbeddingClientProtocol, transcript_registry: Mapping[str, TranscriptRecord], sample_ids: Sequence[str]
) -> tuple[EmbeddingVector, ...]:
    _assert_transcript_registry_covers(transcript_registry, sample_ids)
    client.verify_media_marker()
    return tuple(client.embed_text(contact_id=sid, text=transcript_registry[sid].text) for sid in sorted(sample_ids))


def run_local_text_query(
    *, client: LocalEncoderClientProtocol, transcript_registry: Mapping[str, TranscriptRecord], sample_ids: Sequence[str]
) -> tuple[EmbeddingVector, ...]:
    _assert_transcript_registry_covers(transcript_registry, sample_ids)
    return tuple(client.embed_text(contact_id=sid, text=transcript_registry[sid].text) for sid in sorted(sample_ids))


def _assert_transcript_registry_covers(transcript_registry: Mapping[str, TranscriptRecord], sample_ids: Sequence[str]) -> None:
    ids = list(sample_ids)
    if len(ids) != QUERY_N:
        raise Pemb4rFlightError(f"requires exactly {QUERY_N} sample id(s), got {len(ids)}")
    if len(set(ids)) != len(ids):
        raise Pemb4rFlightError("duplicate sample_id")
    missing = [sid for sid in ids if sid not in transcript_registry]
    if missing:
        raise Pemb4rFlightError(f"transcript_registry missing {len(missing)} sample id(s): {missing[:5]}")


# ---------------------------------------------------------------------------
# Bank / query sweep orchestration -- idempotence (module docstring).
# ---------------------------------------------------------------------------


def run_pemb4r_bank_sweep(
    *, root: Path, bank: BankTable, model_runners: Mapping[str, Callable[[], Sequence[EmbeddingVector]]]
) -> dict[str, LoadedVectorSet]:
    unknown = set(model_runners) - set(MODELS)
    if unknown:
        raise Pemb4rFlightError(f"run_pemb4r_bank_sweep: unknown model(s) {sorted(unknown)}")
    bank_ids = frozenset(entry.bank_id for entry in bank.entries)
    results: dict[str, LoadedVectorSet] = {}
    for model, runner in model_runners.items():
        if not is_bank_vectors_complete(root, model):
            vectors = tuple(runner())
            if len(vectors) != len(bank.entries):
                raise Pemb4rFlightError(f"model {model!r}: runner returned {len(vectors)} vector(s), expected {len(bank.entries)}")
            got_ids = frozenset(vector.contact_id for vector in vectors)
            if got_ids != bank_ids:
                raise Pemb4rFlightError(f"model {model!r}: runner's own contact_id set does not match the bank's own bank_id set")
            write_bank_vectors(root, model, vectors)
        results[model] = load_bank_vectors(root, model, expected_count=len(bank.entries))
    return results


def run_pemb4r_query_sweep(
    *, root: Path, arm_runners: Mapping[str, Callable[[], Sequence[EmbeddingVector]]]
) -> dict[str, LoadedVectorSet]:
    unknown = set(arm_runners) - set(ARM_IDS)
    if unknown:
        raise Pemb4rFlightError(f"run_pemb4r_query_sweep: unknown arm id(s) {sorted(unknown)}")
    results: dict[str, LoadedVectorSet] = {}
    for arm_id, runner in arm_runners.items():
        if not is_query_vectors_complete(root, arm_id):
            vectors = tuple(runner())
            if len(vectors) != QUERY_N:
                raise Pemb4rFlightError(f"arm {arm_id!r}: runner returned {len(vectors)} vector(s), expected {QUERY_N}")
            write_query_vectors(root, arm_id, vectors)
        results[arm_id] = load_query_vectors(root, arm_id)
    return results


# ---------------------------------------------------------------------------
# Retrieval plan (flight-side, gold-free -- module docstring).
# ---------------------------------------------------------------------------


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    import numpy as np

    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a == 0.0 or norm_b == 0.0:
        raise Pemb4rFlightError("_cosine: zero-norm vector cannot be compared")
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _rank(query: Sequence[float], candidates: Mapping[str, object]) -> tuple[tuple[str, float], ...]:
    if not candidates:
        raise Pemb4rFlightError("_rank: candidates must be non-empty")
    scored = [(candidate_id, _cosine(query, vector)) for candidate_id, vector in candidates.items()]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return tuple(scored)


def _dedup_labels(ranked_labels: Sequence[str], k: int) -> tuple[str, ...]:
    seen: list[str] = []
    for label in ranked_labels[:k]:
        if label not in seen:
            seen.append(label)
    return tuple(seen)


@dataclass(frozen=True)
class PerSampleRetrieval:
    sample_id: str
    top_k_bank_ids: tuple[str, ...]
    top_k_cosines: tuple[float, ...]
    top_k_labels: tuple[str, ...]
    dedup_labels_k1: tuple[str, ...]
    dedup_labels_k3: tuple[str, ...]
    dedup_labels_k5: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "top_k_bank_ids": list(self.top_k_bank_ids),
            "top_k_cosines": list(self.top_k_cosines),
            "top_k_labels": list(self.top_k_labels),
            "dedup_labels_k1": list(self.dedup_labels_k1),
            "dedup_labels_k3": list(self.dedup_labels_k3),
            "dedup_labels_k5": list(self.dedup_labels_k5),
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "PerSampleRetrieval":
        return cls(
            sample_id=str(document["sample_id"]),
            top_k_bank_ids=tuple(document["top_k_bank_ids"]),
            top_k_cosines=tuple(float(c) for c in document["top_k_cosines"]),
            top_k_labels=tuple(document["top_k_labels"]),
            dedup_labels_k1=tuple(document["dedup_labels_k1"]),
            dedup_labels_k3=tuple(document["dedup_labels_k3"]),
            dedup_labels_k5=tuple(document["dedup_labels_k5"]),
        )


@dataclass(frozen=True)
class ArmRetrieval:
    arm_id: str
    per_sample: Mapping[str, PerSampleRetrieval]
    mean_top1_cosine: float


def build_arm_retrieval(
    arm_id: str,
    query_vectors: Mapping[str, object],
    bank_vectors: Mapping[str, object],
    bank_labels: Mapping[str, str],
    *,
    k: int = RETRIEVAL_K_PRIMARY,
) -> ArmRetrieval:
    """Pure, gold-free (module docstring): ranks every query vector against
    ``bank_vectors`` (the SAME model's own bank), looks up each retrieved
    bank id's own ``gold_scenario`` VALUE (never re-embeds it), and
    deduplicates the top-K label sequence at K=1/3/5."""

    per_sample: dict[str, PerSampleRetrieval] = {}
    top1_cosines: list[float] = []
    for sample_id in sorted(query_vectors):
        ranking = _rank(query_vectors[sample_id], bank_vectors)[:k]
        bank_ids = tuple(bank_id for bank_id, _cosine_value in ranking)
        cosines = tuple(cosine_value for _bank_id, cosine_value in ranking)
        labels = tuple(bank_labels[bank_id] for bank_id in bank_ids)
        per_sample[sample_id] = PerSampleRetrieval(
            sample_id=sample_id,
            top_k_bank_ids=bank_ids,
            top_k_cosines=cosines,
            top_k_labels=labels,
            dedup_labels_k1=_dedup_labels(labels, 1),
            dedup_labels_k3=_dedup_labels(labels, 3),
            dedup_labels_k5=_dedup_labels(labels, 5),
        )
        top1_cosines.append(cosines[0])
    mean_top1 = sum(top1_cosines) / len(top1_cosines) if top1_cosines else 0.0
    return ArmRetrieval(arm_id=arm_id, per_sample=MappingProxyType(per_sample), mean_top1_cosine=mean_top1)


def select_retrieval_winner(arm_retrievals: Mapping[str, ArmRetrieval]) -> str:
    """Judgment call (module docstring): the GOLD-FREE proxy is the highest
    mean top-1 retrieval cosine across the 60 queries, ties broken by
    sorted ``arm_id`` (``max`` over a sorted-key iteration order returns
    the FIRST maximal element, making this deterministic)."""

    if not arm_retrievals:
        raise Pemb4rFlightError("select_retrieval_winner: arm_retrievals must be non-empty")
    ordered_ids = sorted(arm_retrievals)
    return max(ordered_ids, key=lambda arm_id: arm_retrievals[arm_id].mean_top1_cosine)


RETRIEVAL_PLAN_SCHEMA = "saea-pemb4r-retrieval-plan-v1"
WINNER_SELECTION_RULE = (
    "max mean_top1_cosine across all flown kNN arms (gold-free proxy; documented judgment call, "
    "ties broken by sorted arm_id)"
)


def build_retrieval_plan_document(arm_retrievals: Mapping[str, ArmRetrieval], winner_arm_id: str) -> dict[str, object]:
    if winner_arm_id not in arm_retrievals:
        raise Pemb4rFlightError(f"build_retrieval_plan_document: winner_arm_id {winner_arm_id!r} not in arm_retrievals")
    return {
        "schema": RETRIEVAL_PLAN_SCHEMA,
        "k_primary": RETRIEVAL_K_PRIMARY,
        "winner_arm_id": winner_arm_id,
        "winner_selection_rule": WINNER_SELECTION_RULE,
        "arms": {
            arm_id: {
                "mean_top1_cosine": arm_retrieval.mean_top1_cosine,
                "per_sample": {sid: ps.as_json() for sid, ps in sorted(arm_retrieval.per_sample.items())},
            }
            for arm_id, arm_retrieval in sorted(arm_retrievals.items())
        },
    }


def retrieval_plan_document_sha256(document: Mapping[str, object]) -> str:
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _retrieval_plan_path(root: Path) -> Path:
    return Path(root) / "derived" / "embeddings" / PROBE_ID / "retrieval-plan" / "retrieval_plan.json"


def write_retrieval_plan(root: Path, document: Mapping[str, object]) -> tuple[Path, str]:
    from ...e0.artifacts import write_json_artifact

    path = _retrieval_plan_path(root)
    write_json_artifact(path, document)
    return path, retrieval_plan_document_sha256(document)


def load_retrieval_plan(root: Path) -> dict[str, object]:
    path = _retrieval_plan_path(root)
    if not path.is_file():
        raise Pemb4rFlightError(f"retrieval plan missing: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Pemb4rFlightError(f"cannot read retrieval plan {path}: {error}") from error
    if not isinstance(document, Mapping) or document.get("schema") != RETRIEVAL_PLAN_SCHEMA:
        raise Pemb4rFlightError(f"{path}: schema must be {RETRIEVAL_PLAN_SCHEMA!r}")
    return document


# ---------------------------------------------------------------------------
# C-DECODE: closed-set decode over the winner's retrieval-shrunk label space
# (module docstring).
# ---------------------------------------------------------------------------


def build_c_decode_supply_packet(candidate_labels: Sequence[str]) -> SupplyPacket:
    """The FS-NONE construction, reused VERBATIM (module docstring)."""

    return closed_set_phase1_supply_packet(candidate_labels)


def assemble_c_decode_messages(
    sample: SlurpSample,
    supply: SupplyPacket,
    *,
    query_kind: str,
    transcript_registry: Mapping[str, TranscriptRecord] | None = None,
    adapter: SlurpAdapter | None = None,
) -> tuple[Mapping[str, object], ...]:
    """Presents the SAME modality the winner arm's own query side used
    (module docstring): ``"audio"`` reuses ``SlurpAdapter.assemble_prompt``
    verbatim (the SAME construction ``rails.probes.pslu_s2_flight``'s own
    phase-1 arm uses); ``"text"`` mirrors ``rails.probes.pkey_flight.
    assemble_txt_messages``'s own audio-free shape (T0's OWN transcript,
    never gold)."""

    if query_kind == "audio":
        if adapter is None:
            raise Pemb4rFlightError("assemble_c_decode_messages: query_kind='audio' requires an adapter")
        return adapter.assemble_prompt(sample, supply)
    if query_kind == "text":
        if transcript_registry is None:
            raise Pemb4rFlightError("assemble_c_decode_messages: query_kind='text' requires a transcript_registry")
        record = transcript_registry.get(sample.sample_id)
        if record is None:
            raise Pemb4rFlightError(f"assemble_c_decode_messages: no T0 transcript for sample {sample.sample_id!r}")
        content: tuple[Mapping[str, object], ...] = (
            {"type": "text", "text": supply.prompt_block},
            {"type": "text", "text": render_txt_transcript_block(record.text)},
        )
        return ({"role": "system", "content": _SLU_INSTRUCTION}, {"role": "user", "content": content})
    raise Pemb4rFlightError(f"assemble_c_decode_messages: unknown query_kind {query_kind!r}")


@dataclass(frozen=True)
class CDecodeResult:
    sample_id: str
    candidate_labels: tuple[str, ...]
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    closed_set_mapping: ClosedSetMapping


def run_c_decode_flight(
    *,
    core_client,
    samples: Sequence[SlurpSample],
    retrieval_plan_document: Mapping[str, object],
    winner_arm_id: str,
    winner_query_kind: str,
    transcript_registry: Mapping[str, TranscriptRecord] | None = None,
    adapter: SlurpAdapter | None = None,
    decoding_params: Mapping[str, object] | None = None,
) -> tuple[CDecodeResult, ...]:
    """Exactly :data:`QUERY_N` = 60 generation calls (module docstring) --
    one per sample, built from that sample's own winner-arm top-5
    deduplicated candidate labels. ``core_client`` is duck-typed against
    ``rails.core_client.CoreClient`` (the SAME "no forced import"
    discipline every sibling flight in this package uses)."""

    assert_never_accesses_frozen_60_gold()
    _validate_query_samples(samples)
    arms_block = retrieval_plan_document.get("arms")
    if not isinstance(arms_block, Mapping) or winner_arm_id not in arms_block:
        raise Pemb4rFlightError(f"retrieval_plan_document carries no arm block for winner_arm_id {winner_arm_id!r}")
    per_sample_block = arms_block[winner_arm_id].get("per_sample")
    if not isinstance(per_sample_block, Mapping):
        raise Pemb4rFlightError(f"retrieval_plan_document arm {winner_arm_id!r} carries no per_sample block")

    results: list[CDecodeResult] = []
    for sample in samples:
        row = per_sample_block.get(sample.sample_id)
        if row is None:
            raise Pemb4rFlightError(f"retrieval plan carries no row for sample {sample.sample_id!r} on winner arm {winner_arm_id!r}")
        candidate_labels = tuple(row["dedup_labels_k5"])
        if not candidate_labels:
            raise Pemb4rFlightError(f"sample {sample.sample_id!r}: winner arm retrieval produced an empty candidate label set")
        supply = build_c_decode_supply_packet(candidate_labels)
        messages = assemble_c_decode_messages(
            sample, supply, query_kind=winner_query_kind, transcript_registry=transcript_registry, adapter=adapter
        )
        response_text = core_client.complete(
            messages,
            decoding_params=decoding_params,
            text_only_sample_id=(sample.sample_id if winner_query_kind == "text" else None),
        )
        predicted_scenario, _action, _entities, parsed = _parse_slu_response_lazy(response_text)
        mapping = map_predicted_scenario_to_canonical(predicted_scenario if parsed else None, candidate_labels)
        results.append(
            CDecodeResult(
                sample_id=sample.sample_id,
                candidate_labels=candidate_labels,
                messages=tuple(messages),
                response_text=response_text,
                closed_set_mapping=mapping,
            )
        )
    validate_c_decode_results(results, expected_sample_ids=tuple(sample.sample_id for sample in samples))
    return tuple(results)


def _parse_slu_response_lazy(text: str):
    from ...reproduction.slurp_scoring import parse_slu_response

    return parse_slu_response(text)


def validate_c_decode_results(results: Sequence[CDecodeResult], *, expected_sample_ids: Sequence[str]) -> None:
    expected = tuple(expected_sample_ids)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise Pemb4rFlightError("validate_c_decode_results: expected_sample_ids carries a duplicate")
    ids = [result.sample_id for result in results]
    if len(set(ids)) != len(ids):
        raise Pemb4rFlightError("validate_c_decode_results: duplicate sample_id row(s)")
    got = set(ids)
    if got != expected_set:
        missing = sorted(expected_set - got)
        extra = sorted(got - expected_set)
        raise Pemb4rFlightError(f"validate_c_decode_results: sample id set mismatch (missing={missing[:5]}, extra={extra[:5]})")


__all__ = [
    "ARMS",
    "ARM_A_GLAP",
    "ARM_A_LCO3",
    "ARM_A_LCO7",
    "ARM_IDS",
    "ARM_IDS_BY_MODEL",
    "ARM_T_GLAP",
    "ARM_T_LCO3",
    "ARM_T_LCO7",
    "ARM_T_QW",
    "ARMS_BY_ID",
    "AUDIO_ARM_IDS",
    "BANK_MANIFEST_SCHEMA",
    "BANK_MANIFEST_SHA256",
    "BANK_N_SCENARIOS",
    "BANK_PER_SCENARIO_N",
    "BANK_TOTAL_N",
    "BINDING_CONFIG_SCHEMA",
    "BINDING_CONFIG_SHA256",
    "BINDING_CONFIG_SHA256_AT_FLIGHT",
    "CEILING_AUDIO_SECONDS",
    "CEILING_CALLS",
    "CEILING_GPU_HOURS",
    "DEFAULT_BANK_SEED",
    "DEFAULT_PLANNED_GPU_HOURS",
    "DEFAULT_PLANNED_MODEL_CALLS",
    "DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS",
    "EXPECTED_SPLIT_IDENTITY_HASH",
    "GATE_CONTACTS_MAX",
    "KIND_IN_PROCESS_TRANSFORMERS",
    "KIND_LLAMACPP_SERVER",
    "KIND_LLAMACPP_SERVER_TEXT_ONLY",
    "KNOWN_MODEL_DIM",
    "MODELS",
    "MODEL_GLAP",
    "MODEL_LCO3",
    "MODEL_LCO7",
    "MODEL_LOCK_KEY",
    "MODEL_QW",
    "PKEY2_338_ATTEMPT_ID",
    "PKEY2_338_RUN_EXPERIMENT_ID",
    "PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH",
    "PKEY2_338_TRANSCRIPT_REGISTRY_SHA256",
    "PLANNED_AUDIO_QUERY_CONTACTS",
    "PLANNED_BANK_CONTACTS",
    "PLANNED_C_DECODE_CONTACTS",
    "PLANNED_TEXT_QUERY_CONTACTS",
    "POOLING_OVERRIDE_SCOPE_TAG",
    "PROBE_ID",
    "QUERY_N",
    "QWEN3_EMB_EMBEDDING_DIM",
    "RETRIEVAL_K_PRIMARY",
    "RETRIEVAL_K_REPORTED",
    "RETRIEVAL_PLAN_SCHEMA",
    "STATUS_DROPPED_LCO7",
    "TEXT_ARM_IDS",
    "VECTOR_MANIFEST_SCHEMA",
    "WINNER_SELECTION_RULE",
    "ArmRetrieval",
    "BankEntry",
    "BankTable",
    "CDecodeResult",
    "GpuHoursAccounting",
    "Lco7SanityResult",
    "LoadedVectorSet",
    "Pemb4rArm",
    "Pemb4rFlightError",
    "PerSampleRetrieval",
    "assemble_c_decode_messages",
    "assert_bank_manifest_sha256",
    "assert_binding_config_sha256",
    "assert_gpu_hours_within_ceiling",
    "assert_never_accesses_frozen_60_gold",
    "assert_split_identity_hash",
    "assert_within_registered_ceilings",
    "arm_run_id",
    "bank_manifest_sha256",
    "bank_table_to_json",
    "binding_config_sha256",
    "build_arm_retrieval",
    "build_bank_table",
    "build_binding_config_document",
    "build_c_decode_supply_packet",
    "build_execution_plan",
    "build_retrieval_plan_document",
    "is_bank_vectors_complete",
    "is_query_vectors_complete",
    "load_bank_manifest",
    "load_bank_vectors",
    "load_query_vectors",
    "load_retrieval_plan",
    "pooling_override_scope_for_model",
    "retrieval_plan_document_sha256",
    "run_c_decode_flight",
    "run_encode_only_preflight_gate",
    "run_glap_import_and_audio_sanity_gate",
    "run_lco7_server_sanity_gate",
    "run_local_audio_query",
    "run_local_bank_embedding",
    "run_local_text_query",
    "run_pemb4r_bank_sweep",
    "run_pemb4r_cascade_source_check",
    "run_pemb4r_query_sweep",
    "run_server_audio_query",
    "run_server_bank_embedding",
    "run_server_text_query",
    "select_retrieval_winner",
    "validate_bank_table",
    "validate_c_decode_results",
    "write_bank_manifest",
    "write_bank_vectors",
    "write_query_vectors",
    "write_retrieval_plan",
    # Re-exported (module docstring: "reused VERBATIM").
    "CascadeSourceCheckResult",
    "PoolingDifferGateResult",
    "assert_ledger_row_consumed",
    "resolve_model_binding",
    "run_pooling_differ_gate",
    "canonical_scenario_labels",
    "closed_set_phase1_supply_packet",
    "map_predicted_scenario_to_canonical",
]


# Executed at import time (mirrors rails.probes.pemb3m_flight's own
# module-bottom self-check): fails LOUD the moment this module is next
# imported if a future edit adds a forbidden reference.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
assert_never_accesses_frozen_60_gold()
