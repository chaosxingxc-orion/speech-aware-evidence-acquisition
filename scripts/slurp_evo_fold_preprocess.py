#!/usr/bin/env python3
"""Receipt-bound speech-feature packet preprocessing and promotion.

Exposure rows ``SAEA-SLURP-EVO-FOLD-PACKETS-V2`` (contracts
``configs/experiment/slurp-evo-fold-{a,b}-preprocess.json``, preregistration
section 13 item 3) and ``SAEA-SN-DEV2000-ADDED-PREPROCESS`` (contract
``configs/experiment/slurp-dev2000-added-preprocess.json``, item E33,
``docs/readiness/2026-09-21-slurp-dev2000-added-preprocess-v1/``). SLURP
sibling of ``scripts/a2t_g1_preprocess.py``, following
``SAEA-SN-DEV1000-PREPROCESS`` (2026-08-24), which is the precedent the EVO
fold row names and which this DEV-2000-ADDED registration copies again.

Two phases in one invocation, per roster:

1. ENCODE -- a CPU-only llama-server sidecar on port 8081 (``-ngl 0
   --no-mmproj-offload``, ``receipts/runtime-q4km-preprocess.json``: decoder AND
   bf16 mmproj) is spawned under its own session receipt, driven with one contact
   per roster row at ``max_tokens: 1``, and stopped with its own stop receipt. The
   prompt is a fixed minimal instruction: the legacy feature-cache key is the
   FNV-1a hash of the media bytes ALONE, so the prompt cannot affect the cached
   features. No response is read semantically and no gold is ever opened.
2. PROMOTE -- ``core.model.speech_features.
   materialize_legacy_cached_speech_feature_packets`` promotes the warm entries
   into audited packets under the resident ``04ccc72a`` packet root and writes the
   roster's own promotion receipt. Zero contacts, and only after a verified normal
   stop. Promotion is additive and refuse-on-conflict by construction: a packet
   id that already exists under the resident root is re-verified byte-for-byte
   (``materialize_speech_feature_packet``, ``core/model/speech_features.py``) and
   any mismatch raises before anything is written, and this driver separately
   refuses to run a roster whose own promotion receipt file already exists (see
   the "promotion receipt already exists" guard below), so a roster can never be
   silently re-promoted or made to overwrite a sibling roster's packets.

   Item E40 (2026-09-22): "refuse on conflict" never meant "refuse on
   provenance". A packet id that already exists and differs from this pass in
   EXACTLY ``encoder_receipt_sha256`` -- the hash of the runtime RECEIPT
   DOCUMENT, not of anything the encoder produced -- while its chunk count and
   every chunk hash are identical is SHARED: accepted unchanged, not one byte
   of the feature root written, and listed in the receipt's ``shared_packets``
   ledger with both receipt hashes. Every other difference still refuses.

3. PROMOTE-ONLY (``--promote-only``) -- phase 2 alone, for a roster whose
   legacy cache is ALREADY fully warm (e.g. an ENCODE pass whose PROMOTE was
   refused). No sidecar, no session, no encoder, ZERO contacts. It refuses
   unless every roster row is warm, runs the same D1 / frozen-core preflight as
   ``--run``, and records a NEW attempt id under the same run id. Because it
   touches no model it constructs no ``contracts.ExecutionPlan`` and reserves
   no attempt budget: both refuse a zero declaration by design
   (``contracts/plan.py`` requires finite POSITIVE calls/GPU-hours/speech
   seconds, ``core/attempts/store.py`` positive reserved calls), and a
   zero-contact pass must not weaken either.

Label-free by construction: samples are built from a roster's frozen
``saea-speech-native-runtime-view-v1`` dataset fragment, which carries media
identity and nothing else, and every media file is re-hashed against the view's
own record before it can become a sample. `-ngl 0` means this pass leaves the GPU
free.

Rosters (``PREPROCESS_ROSTERS``):

- ``fold-a`` / ``fold-b`` -- the two disjoint SLURP EVO-S1 TRAIN folds
  (``slurp:train:...`` rows, ``split_role="discovery"``). ``--fold a`` and
  ``--fold b`` are deprecated aliases for ``--roster fold-a`` / ``--roster
  fold-b``, kept so the two already-sealed fold runs stay reproducible byte for
  byte.
- ``dev2000-added`` -- item E33, the DEV-2000-ADDED preparation
  (``slurp:devel:...`` rows, ``split_role="dev"``, 1,000 rows / 2,984 speech
  seconds). Promotes additively into the SAME resident packet root the two
  folds use, under its own ``DEV-2000-ADDED-promotion.json`` receipt.
- ``stage3-construction-r01`` -- Stage-3 item S3-1, the SLURP-STAGE3-
  CONSTRUCTION-R01 preparation (``slurp:train:...`` rows,
  ``split_role="discovery"``, 800 rows / 3,491.426125 speech seconds).
  Promotes additively into the same resident packet root under its own
  ``STAGE3-CONSTRUCTION-R01-promotion.json`` receipt. 8 of its 800 rows are
  already promoted by the August TRAIN90 / GATE18 / GATE-C36 / OPT-A36 /
  EFFECT-C108 / EVIDENCE-E108 / FACTOR-D108 receipts, which the additive
  refuse-on-conflict promotion re-verifies byte for byte instead of
  rewriting; the remaining 792 are new.
- ``devel-remainder`` -- owner decision 107 of 2026-09-23, the expansion of the
  development side to the SLURP devel split, carved by the coordinator ruling of
  2026-09-23 (provisional decision 109) so that it neither spends the FINAL60
  reservation nor carries an already-contacted row: ``SLURP-DEVEL-REMAINDER-V2``
  (``slurp:devel:...`` rows, ``split_role="dev"``, 6,570 rows / 18,611.584875
  speech seconds; the superseded V1 was 6,690 / 18,978.9523125). Promotes
  additively into the same resident packet root under its own
  ``DEVEL-REMAINDER-promotion.json`` receipt. It is the first roster to run on
  the ``-np 8`` sidecar fragment (see "More slots, honestly" below).
- ``devel-remainder-np8-equivalence-4`` -- the 4-row GEOMETRY-EQUIVALENCE
  preflight of that np8 pass. It is not a preparation: it promotes nothing,
  writes no promotion receipt, and exists only to prove that ``-np 8`` produces
  the same encoder features as the ``-np 4`` geometry every sealed packet was
  produced with. See "Geometry equivalence" below.

More slots, honestly
--------------------
``--workers`` is encode CONCURRENCY and the sidecar's ``-np`` is how many
sequences it actually serves in parallel; asking for more workers than slots
only queues requests inside the server, which looks like throughput and is not.
The number therefore comes from the composed model fragment, not from prose:
each roster names its own ``sidecar_fragment`` (``RosterSpec``), the driver
reads that fragment's ``-np`` out of ``server_args``, and ``--workers`` above it
is REFUSED rather than silently clamped. ``q4km-preprocess-featcache-cpu-
sidecar`` serves ``-np 4``; ``q4km-preprocess-featcache-cpu-sidecar-np8`` is its
one-value sibling at ``-np 8``.

Geometry equivalence
--------------------
Changing ``-np`` changes how the server batches, so before a 6,570-row pass
runs on a geometry no sealed packet was produced with, the equivalence is
MEASURED. ``devel-remainder-np8-equivalence-4`` re-encodes 4 already-promoted
DEV-2000-ADDED rows through the np8 sidecar into a SCRATCH feature cache, then
compares, per row: the legacy cache entry (ordinals, token counts, file bytes)
against the resident cache's entry, and the SHA-256 of each chunk's feature
payload against the ``feature_sha256`` the resident PACKET manifest already
serves. Nothing is written under the resident cache or the resident packet
root, no packet is materialised and no promotion receipt is created; the driver
refuses a promotion for any roster carrying an ``EquivalenceSpec``, refuses a
scratch geometry whose cache or feature root is the resident one, and refuses
``--promote-only`` for it. The verdict plus the measured per-row wall clock go
into the ``--output`` report.
- ``test-full`` -- the COMPLETE official SLURP test split
  (``slurp:test:...`` rows, ``split_role="final-report"``, 13,078 rows /
  36,911.9388125 speech seconds), the packet preparation of the ONE end-of-
  Stage-3 read (owner decisions 99 of 2026-09-22 and 107 of 2026-09-23).
  REFUSED TODAY, in every mode including ``--preflight-only``: the roster's
  split role is ``final-report`` and
  ``contracts.plan.require_owner_split_allowance`` accepts only an
  ``authorised`` owner-allowance receipt, while the committed
  ``docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json`` says
  ``pending-owner``. The refusal is raised BEFORE the data root is opened, so
  not one test media file is read while the allowance is pending.
- ``test-sample-3010`` -- the SLURP test SAMPLE ``SLURP-TEST-SAMPLE-3010-V1``
  (``slurp:test:...`` rows, ``split_role="final-report"``, 3,010 rows /
  8,206.436875 speech seconds), preparation 1 of 3 of the sample. Its pinned
  allowance ``docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json``
  says ``authorised`` (owner decision 151), and owner decision 156 lets the
  three label-free preparations run ahead of the milestone gate. The allowance
  check above still runs in every mode; the exposure row's root
  countersignature is checked by ``scripts/flights/testsample/prep_test_sample.sh``
  before this driver is launched.

Modes::

    python scripts/slurp_evo_fold_preprocess.py --roster fold-a --preflight-only
    python scripts/slurp_evo_fold_preprocess.py --fold a --run  # deprecated alias
    python scripts/slurp_evo_fold_preprocess.py --roster dev2000-added --preflight-only
    python scripts/slurp_evo_fold_preprocess.py --roster dev2000-added --run
    python scripts/slurp_evo_fold_preprocess.py --roster stage3-construction-r01 --preflight-only
    python scripts/slurp_evo_fold_preprocess.py --roster stage3-construction-r01 --run
    python scripts/slurp_evo_fold_preprocess.py --roster stage3-construction-r01-recovery \
        --promote-only --attempt-id attempt-promote-only-stage3-construction-r01-v1
    python scripts/slurp_evo_fold_preprocess.py --roster devel-remainder-np8-equivalence-4 --run
    python scripts/slurp_evo_fold_preprocess.py --roster devel-remainder --run --workers 8
    python scripts/slurp_evo_fold_preprocess.py --roster test-full --preflight-only  # refuses
    python scripts/slurp_evo_fold_preprocess.py --roster test-sample-3010 --run  # via prep_test_sample.sh
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, NamedTuple, Sequence

# Derived from this file's own location (not a hardcoded literal), exactly as
# the sibling script scripts/slurp_dev1000_ts2_preprocess.py already does, so
# the module's own package-identity self-check below (and any test that
# imports this file via importlib, e.g. tests/unit/test_slurp_dev1000_ts2_
# preprocess.py's pattern) is portable to a git worktree checkout of this
# study and not pinned to one literal absolute path.
REPO = Path(__file__).resolve().parent.parent
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    FINAL_REPORT_SPLIT_ROLE, ExecutionPlan, FrozenCoreGate,
    require_owner_split_allowance)
from speech_aware_evidence_acquisition.core.base import TRANSPORTS  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose, d1_media_supplement_relpath, d1_media_supplement_sha256)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    PROMOTION_MODE_ENCODE_AND_PROMOTE, PROMOTION_MODE_PROMOTE_ONLY,
    SharedSpeechFeaturePacketRecord, legacy_audio_feature_cache_key,
    load_speech_feature_packet, materialize_legacy_cached_speech_feature_packets)
# The legacy feature-cache file header, imported rather than re-declared so the
# geometry-equivalence comparison below can never drift from the parse the
# promotion path itself performs (core/model/speech_features.py).
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    _LEGACY_FEAT_HEADER as LEGACY_FEAT_HEADER)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt, start_session, stop_session)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir, data_root, load_lock, umbrella_lock_path)
from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY  # noqa: E402
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient, build_payload_binding)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpSample  # noqa: E402
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-preprocess-featcache-cpu-sidecar"
#: The one-value sibling of MODEL_FRAGMENT: identical except ``-np 8``.
MODEL_FRAGMENT_NP8 = "q4km-preprocess-featcache-cpu-sidecar-np8"
#: The np8 sidecar pointed at a SCRATCH feature cache, for the geometry
#: equivalence preflight alone. Never used by a preparation that promotes.
MODEL_FRAGMENT_NP8_SCRATCH = "q4km-preprocess-featcache-cpu-sidecar-np8-scratch"
BASELINE_FRAGMENT = "speech-native-preprocess"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
SIDECAR_PORT = 8081
INFERENCE_PORT = 8080
EXPECTED_N_EMBD = 2048
PREPROCESS_INSTRUCTION = (
    "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."
)
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}

# The resident packet root and legacy feature-cache directory every roster in
# PREPROCESS_ROSTERS promotes into/reads from BY DEFAULT. The two EVO fold
# experiment fragments already carry their own "feature_root" /
# "legacy_cache_dir" keys equal to these same literal paths (checked below via
# values.get(..., DEFAULT_*)), so this is not a behavior change for --fold;
# it is what lets a roster whose composed config does not declare these keys
# (dev2000-added, by design: the same resident root, additive) still resolve
# them.
DEFAULT_FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
DEFAULT_LEGACY_CACHE_DIR = Path("/home/chao/feat-cache/slurp-q4km")

# Item E40. --promote-only makes zero model contacts, so it opens no budget at
# all: no contracts.ExecutionPlan is constructed and no attempt is reserved in
# the attempt store. Neither would accept a zero declaration -- contracts/
# plan.py requires finite POSITIVE planned_model_calls / planned_gpu_hours /
# planned_speech_audio_seconds and core/attempts/store.py positive
# reserved_calls -- and item E40 weakens neither: a pass that touches no model
# must not reserve one contact of head-room. These numbers are what the run
# directory's own attempt report declares.
PROMOTE_ONLY_PROFILE = "model-free-check"
PROMOTE_ONLY_PLAN: dict[str, object] = {
    "calls": 0,
    "speech_audio_seconds": 0,
    "gpu_hours": 0.0,
    "basis": (
        "promote-only: zero model contacts, therefore no ExecutionPlan is "
        "validated and no attempt budget is reserved; the plan validator and "
        "the attempt store both refuse a zero declaration by design and "
        "neither is weakened"
    ),
}
PROMOTE_ONLY_REPORT_NAME = "promote-only.report.json"


class EquivalenceSpec(NamedTuple):
    """A roster that MEASURES a serving geometry instead of preparing packets.

    ``reference_feature_root`` is the RESIDENT packet root, opened read-only:
    its already-promoted packet manifests are the reference the freshly encoded
    scratch-cache features are compared against. ``reference_promotion_receipt``
    is the receipt (under that root) that promoted them, recorded in the report
    so a reader can re-derive the comparison from committed documents.
    """

    reference_feature_root: Path
    reference_promotion_receipt: str
    reference_geometry_slots: int


class RosterSpec(NamedTuple):
    """One preprocessing roster: which rows, which receipt, which plan.

    ``promotion_receipt_name`` is used only when the composed config does not
    itself carry a ``promotion_receipt`` key (the EVO fold experiment
    fragments do; the DEV-2000-ADDED one does not, by design -- see
    DEFAULT_FEATURE_ROOT above). When used, the final path is
    ``DEFAULT_FEATURE_ROOT / promotion_receipt_name``.
    """

    run_id: str
    dataset_fragment: str
    experiment_fragment: str
    sample_id_prefix: str
    split_role: str
    promotion_receipt_name: str | None
    default_attempt_id: str
    # A plan's budget is metered run-CUMULATIVELY across every attempt of a
    # run id (``core.model.adapter`` re-reads the attempt store's prior
    # actuals on every request), so a SUCCESSOR session must declare prior
    # durable spend PLUS its own worst case -- not its own roster's
    # arithmetic alone. These are the FIRST session of each roster;
    # ``--plan-calls`` / ``--plan-speech-seconds`` are how a successor states
    # the cumulative figure.
    plan_calls: int
    plan_speech_seconds: int
    plan_gpu_hours: float
    # WHICH SIDECAR GEOMETRY this roster encodes on. The default is the
    # historical ``-np 4`` fragment, so every sealed roster above keeps its
    # exact composed config hash; a roster that wants more slots names the
    # ``-np 8`` sibling here rather than passing a flag, because the fragment
    # enters the composed config hash and therefore the protocol hash its
    # exposure row pins.
    sidecar_fragment: str = MODEL_FRAGMENT
    # Set only on a geometry-equivalence roster: it promotes NOTHING.
    equivalence: EquivalenceSpec | None = None


PREPROCESS_ROSTERS: dict[str, RosterSpec] = {
    "fold-a": RosterSpec(
        run_id="SAEA-SLURP-EVO-FOLD-PACKETS-V2",
        dataset_fragment="slurp-speech-native-evo-fold-a-1080",
        experiment_fragment="slurp-evo-fold-a-preprocess",
        sample_id_prefix="slurp:train:",
        split_role="discovery",
        promotion_receipt_name=None,
        default_attempt_id="attempt-packets-fold-a",
        plan_calls=1090, plan_speech_seconds=3085, plan_gpu_hours=1.0,
    ),
    "fold-b": RosterSpec(
        run_id="SAEA-SLURP-EVO-FOLD-PACKETS-V2",
        dataset_fragment="slurp-speech-native-evo-fold-b-1080",
        experiment_fragment="slurp-evo-fold-b-preprocess",
        sample_id_prefix="slurp:train:",
        split_role="discovery",
        promotion_receipt_name=None,
        default_attempt_id="attempt-packets-fold-b",
        plan_calls=1090, plan_speech_seconds=3155, plan_gpu_hours=1.0,
    ),
    "dev2000-added": RosterSpec(
        run_id="SAEA-SN-DEV2000-ADDED-PREPROCESS",
        dataset_fragment="slurp-speech-native-dev2000-added",
        experiment_fragment="slurp-dev2000-added-preprocess",
        sample_id_prefix="slurp:devel:",
        split_role="dev",
        promotion_receipt_name="DEV-2000-ADDED-promotion.json",
        default_attempt_id="attempt-packets-dev2000-added-v1",
        plan_calls=1000, plan_speech_seconds=2984, plan_gpu_hours=1.0,
    ),
    "stage3-construction-r01": RosterSpec(
        run_id="SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS",
        dataset_fragment="slurp-speech-native-stage3-construction-r01",
        experiment_fragment="slurp-stage3-construction-r01-preprocess",
        sample_id_prefix="slurp:train:",
        split_role="discovery",
        promotion_receipt_name="STAGE3-CONSTRUCTION-R01-promotion.json",
        default_attempt_id="attempt-packets-stage3-construction-r01-v1",
        plan_calls=800, plan_speech_seconds=3492, plan_gpu_hours=1.0,
    ),
    # The one recovery of the R01 preprocess (2026-09-22): attempt v1 lost its CPU sidecar to the serving task entry's
    # unscoped orphan reaper during the E21 -> SLURP geometry switch (72 ok / 728 failed, partial cache refused). Own run id
    # because the plan budget is cumulative per run id; same roster, same dataset fragment, same promotion receipt target.
    "stage3-construction-r01-recovery": RosterSpec(
        run_id="SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS-RECOVERY-V1",
        dataset_fragment="slurp-speech-native-stage3-construction-r01",
        experiment_fragment="slurp-stage3-construction-r01-preprocess-recovery-v1",
        sample_id_prefix="slurp:train:",
        split_role="discovery",
        promotion_receipt_name="STAGE3-CONSTRUCTION-R01-promotion.json",
        default_attempt_id="attempt-packets-stage3-construction-r01-recovery-v1",
        plan_calls=800, plan_speech_seconds=3492, plan_gpu_hours=1.0,
    ),
    # Owner decision 107 (2026-09-23): the development side expands to the SLURP
    # devel split; the coordinator ruling of 2026-09-23 (provisional decision
    # 109) then carved the 60 reserved-final-unread FINAL60 recordings and the
    # 60 already-contacted historic probe-60 recordings out of it, so the roster
    # is SLURP-DEVEL-REMAINDER-V2: 6,570 rows / 18,611.584875 speech seconds
    # (declared 18,612). 0 rows are warm in the legacy cache -- the 60 warm rows
    # of V1 were exactly the carved-out probe-60 -- and 0 are promoted, so all
    # 6,570 are contacted once and every contact is a first contact. The
    # superseded V1 fragments stay committed and are bound by nothing.
    "devel-remainder": RosterSpec(
        run_id="SAEA-SN-DEVEL-REMAINDER-PREPROCESS",
        dataset_fragment="slurp-speech-native-devel-remainder-v2",
        experiment_fragment="slurp-devel-remainder-preprocess-v2",
        sample_id_prefix="slurp:devel:",
        split_role="dev",
        promotion_receipt_name="DEVEL-REMAINDER-promotion.json",
        default_attempt_id="attempt-packets-devel-remainder-v1",
        plan_calls=6570, plan_speech_seconds=18612, plan_gpu_hours=1.0,
        sidecar_fragment=MODEL_FRAGMENT_NP8,
    ),
    # The 4-row geometry-equivalence preflight of the roster above: it re-encodes
    # four ALREADY-PROMOTED DEV-2000-ADDED rows on the np8 sidecar into a scratch
    # cache and compares the result against what the resident root already
    # serves. It promotes nothing and writes no promotion receipt.
    "devel-remainder-np8-equivalence-4": RosterSpec(
        run_id="SAEA-SN-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1",
        dataset_fragment="slurp-speech-native-devel-remainder-np8-equivalence-4",
        experiment_fragment="slurp-devel-remainder-np8-equivalence-4-preprocess",
        sample_id_prefix="slurp:devel:",
        split_role="dev",
        promotion_receipt_name=None,
        default_attempt_id="attempt-np8-equivalence-4-v1",
        plan_calls=4, plan_speech_seconds=12, plan_gpu_hours=1.0,
        sidecar_fragment=MODEL_FRAGMENT_NP8_SCRATCH,
        equivalence=EquivalenceSpec(
            reference_feature_root=DEFAULT_FEATURE_ROOT,
            reference_promotion_receipt="DEV-2000-ADDED-promotion.json",
            reference_geometry_slots=4,
        ),
    ),
    # Owner decisions 99 (2026-09-22) and 107 (2026-09-23): the packet
    # preparation of the ONE complete official SLURP test-split read, registered
    # now and built ahead of time so the read waits on nothing. 13,078 rows /
    # 36,911.9388125 measured audio seconds (declared 36,912 = the ceiling, the
    # form every roster above uses) / 1.0 declared GPU hours against 0.0 actually
    # consumed, because the sidecar runs -ngl 0 --no-mmproj-offload and leaves
    # the GPU to the resident serving session. The split role is the
    # owner-allowance-gated FINAL_REPORT_SPLIT_ROLE, so main() refuses this
    # roster in EVERY mode until the committed allowance says "authorised".
    "test-full": RosterSpec(
        run_id="SAEA-SN-TEST-FULL-PREPROCESS",
        dataset_fragment="slurp-speech-native-test-full",
        experiment_fragment="slurp-test-full-preprocess",
        sample_id_prefix="slurp:test:",
        split_role=FINAL_REPORT_SPLIT_ROLE,
        promotion_receipt_name="TEST-FULL-promotion.json",
        default_attempt_id="attempt-packets-test-full-v1",
        plan_calls=13078, plan_speech_seconds=36912, plan_gpu_hours=1.0,
    ),
    # Owner decisions 151 and 156 (2026-09-27): preparation 1 of 3 of the test
    # SAMPLE SLURP-TEST-SAMPLE-3010-V1, the label-free restriction of the FULL
    # roster above to the sample's 3,010 ids. 3,010 rows / 8,206.436875 audio
    # seconds (declared 8,207 = the ceiling) / 1.0 declared GPU hours against
    # 0.0 consumed (-ngl 0 --no-mmproj-offload). Its allowance is authorised;
    # the countersignature of its exposure row is what gates the launch.
    "test-sample-3010": RosterSpec(
        run_id="SAEA-SN-TEST-SAMPLE-3010-PREPROCESS",
        dataset_fragment="slurp-speech-native-test-sample-3010",
        experiment_fragment="slurp-test-sample-3010-preprocess",
        sample_id_prefix="slurp:test:",
        split_role=FINAL_REPORT_SPLIT_ROLE,
        promotion_receipt_name="TEST-SAMPLE-3010-promotion.json",
        default_attempt_id="attempt-packets-test-sample-3010-v1",
        plan_calls=3010, plan_speech_seconds=8207, plan_gpu_hours=1.0,
    ),
}

# The two EVO-S1 TRAIN folds, in the fixed order the union receipt merges them.
# ``stage3-construction-r01`` is a separate preparation with its own receipt and
# is never folded into this union, exactly as ``dev2000-added`` is not.
FOLD_ROSTER_KEYS: tuple[str, ...] = ("fold-a", "fold-b")


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def roster_samples(
    values: Mapping[str, object], root: Path, workers: int,
    sample_id_prefix: str, roster_key: str,
) -> tuple[SlurpSample, ...]:
    """Label-free samples from the frozen runtime view, each file re-hashed."""

    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a speech-native runtime view")
    if int(values.get("count", len(items))) != len(items):
        raise SystemExit("runtime view count disagrees with its own items")

    def build(item: Mapping[str, object]) -> SlurpSample:
        sample_id = str(item["sample_id"])
        if not sample_id.startswith(sample_id_prefix):
            raise SystemExit(
                "roster %r rows must start with %r; %r does not" % (roster_key, sample_id_prefix, sample_id)
            )
        measured = sha256_file(root / str(item["media_relpath"]))
        if measured != str(item["audio_sha256"]):
            raise SystemExit("media %s hashes to %s" % (item["media_relpath"], measured))
        return SlurpSample(
            sample_id=sample_id,
            audio_ref=AudioRef(path=str(item["media_relpath"]), sha256=measured).validate(),
            audio_seconds=float(item["audio_seconds"]), utterance_id=sample_id.split(":")[2],
            media_relpath=str(item["media_relpath"]), scenario="", action="", intent="", entities=())

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        samples = list(pool.map(build, items))
    return tuple(sorted(samples, key=lambda sample: sample.sample_id))


def _resolve_promotion_receipt(
    values: Mapping[str, object], spec: RosterSpec, packet_root: Path, roster_key: str,
) -> Path:
    if "promotion_receipt" in values:
        return Path(str(values["promotion_receipt"]))
    if spec.promotion_receipt_name is None:
        raise SystemExit(
            "roster %r has neither a config promotion_receipt key nor a default receipt name" % roster_key
        )
    return packet_root / spec.promotion_receipt_name


def _require_fully_warm(warm: int, total: int, roster_key: str) -> None:
    """--promote-only never encodes, so a cold row could only fail closed."""

    if warm != total:
        raise SystemExit(
            "--promote-only requires every roster row to be warm in the legacy "
            "cache; roster %r has %d/%d warm (%d cold). Run --run instead, or "
            "complete the ENCODE pass first." % (roster_key, warm, total, total - warm)
        )


def _server_slots(values: Mapping[str, object], fragment: str) -> int:
    """The ``-np`` the composed sidecar fragment actually serves.

    Read from the fragment rather than from a docstring, so "the sidecar serves
    -np 4" can never drift away from what the sidecar is launched with.
    """

    argv = [str(token) for token in values.get("server_args", ())]
    for index, token in enumerate(argv):
        if token == "-np":
            if index + 1 >= len(argv) or not argv[index + 1].isdecimal():
                raise SystemExit("model fragment %r has a malformed -np value" % fragment)
            slots = int(argv[index + 1])
            if slots <= 0:
                raise SystemExit("model fragment %r declares -np %d" % (fragment, slots))
            return slots
    raise SystemExit("model fragment %r declares no -np; refusing to guess" % fragment)


def _assert_worker_fit(workers: int, slots: int, roster_key: str, fragment: str) -> None:
    """--workers above the sidecar's -np only queues requests inside the server.

    Refused, never clamped: a silently clamped concurrency would be reported as
    throughput that the geometry cannot deliver.
    """

    if workers > slots:
        raise SystemExit(
            "--workers %d exceeds the %d slots model fragment %r serves for roster %r; "
            "raise -np in a sibling fragment instead of over-subscribing the sidecar"
            % (workers, slots, fragment, roster_key)
        )


def _assert_equivalence_isolation(
    values: Mapping[str, object], spec: RosterSpec, roster_key: str,
    packet_root: Path, legacy_cache: Path,
) -> None:
    """A geometry-equivalence roster may not touch anything the session serves."""

    assert spec.equivalence is not None
    if spec.promotion_receipt_name is not None or "promotion_receipt" in values:
        raise SystemExit(
            "roster %r is a geometry-equivalence roster and must name no promotion "
            "receipt: it promotes nothing" % roster_key
        )
    if legacy_cache == DEFAULT_LEGACY_CACHE_DIR:
        raise SystemExit(
            "roster %r must encode into a SCRATCH legacy cache, not the resident %s"
            % (roster_key, DEFAULT_LEGACY_CACHE_DIR)
        )
    if packet_root == DEFAULT_FEATURE_ROOT:
        raise SystemExit(
            "roster %r must not declare the resident packet root %s as its feature root"
            % (roster_key, DEFAULT_FEATURE_ROOT)
        )
    if spec.equivalence.reference_feature_root != DEFAULT_FEATURE_ROOT:
        raise SystemExit(
            "roster %r compares against %s, which is not the resident packet root"
            % (roster_key, spec.equivalence.reference_feature_root)
        )
    served = dict(values.get("server_env", {})).get("LLAMA_MTMD_FEAT_CACHE_DIR")
    if served is None or Path(str(served)) != legacy_cache:
        raise SystemExit(
            "roster %r declares legacy_cache_dir %s but its sidecar writes to %r; the "
            "comparison would read an empty directory" % (roster_key, legacy_cache, served)
        )


def _compare_row_against_resident_packet(
    *, sample, root: Path, legacy_cache: Path, reference_root: Path,
) -> dict[str, object]:
    """One row's scratch-cache features against the resident packet it already has.

    Model-free, read-only, and byte-level: the freshly encoded scratch cache is
    parsed with the SAME header the promotion path parses, each chunk's feature
    payload is hashed exactly as ``materialize_speech_feature_packet`` hashes it
    (``sha256(feature_bytes)``), and the result is compared with the
    ``feature_sha256`` the resident packet manifest already serves. The resident
    legacy cache entry, when it is still warm, is compared as a whole file too.
    Nothing is written anywhere.
    """

    packet_id = sample.sample_id.replace(":", "/")
    audio_path = root / sample.media_relpath
    audio_bytes = audio_path.read_bytes()
    key = legacy_audio_feature_cache_key(audio_bytes)

    def payloads(cache_dir: Path) -> list[dict[str, object]] | None:
        entries = sorted(cache_dir.glob("%s_o*.feat" % key))
        if not entries:
            return None
        rows: list[dict[str, object]] = []
        for path in entries:
            raw = path.read_bytes()
            n_tokens, n_embd = LEGACY_FEAT_HEADER.unpack_from(raw)
            rows.append(
                {
                    "filename": path.name,
                    "file_bytes": len(raw),
                    "file_sha256": hashlib.sha256(raw).hexdigest(),
                    "n_tokens": int(n_tokens),
                    "n_embd": int(n_embd),
                    "feature_payload_sha256": hashlib.sha256(
                        raw[LEGACY_FEAT_HEADER.size :]
                    ).hexdigest(),
                }
            )
        rows.sort(key=lambda entry: str(entry["filename"]))
        return rows

    fresh = payloads(legacy_cache)
    if fresh is None:
        raise SystemExit(
            "geometry equivalence: the scratch cache has no entry for %s after ENCODE"
            % sample.sample_id
        )
    resident_cache = payloads(DEFAULT_LEGACY_CACHE_DIR)
    packet = load_speech_feature_packet(reference_root, packet_id)
    packet_chunks = [
        {
            "ordinal": chunk.ordinal,
            "n_tokens": chunk.n_tokens,
            "n_embd": chunk.n_embd,
            "feature_sha256": chunk.feature_sha256,
        }
        for chunk in packet.chunks
    ]
    payload_match = len(fresh) == len(packet_chunks) and all(
        str(row["feature_payload_sha256"]) == str(chunk["feature_sha256"])
        and int(row["n_tokens"]) == int(chunk["n_tokens"])
        and int(row["n_embd"]) == int(chunk["n_embd"])
        for row, chunk in zip(fresh, packet_chunks)
    )
    cache_match: bool | None = None
    if resident_cache is not None:
        cache_match = [
            (row["file_sha256"], row["file_bytes"]) for row in fresh
        ] == [(row["file_sha256"], row["file_bytes"]) for row in resident_cache]
    return {
        "sample_id": sample.sample_id,
        "packet_id": packet_id,
        "audio_sha256": sample.audio_ref.sha256,
        "audio_seconds": round(float(sample.audio_seconds), 6),
        "legacy_cache_key": key,
        "scratch_chunks": fresh,
        "resident_packet": {
            "packet_sha256": packet.packet_sha256,
            "audio_sha256": packet.audio_sha256,
            "encoder_receipt_sha256": packet.encoder_receipt_sha256,
            "chunks": packet_chunks,
        },
        "resident_legacy_cache_still_warm": resident_cache is not None,
        "feature_payload_identical_to_resident_packet": payload_match,
        "legacy_cache_file_identical_to_resident_cache": cache_match,
    }


def _decoder_and_mmproj(runtime_receipt: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object]]:
    gguf = runtime_receipt["gguf_files"]
    decoder = [e for e in gguf if "mmproj" not in Path(str(e["path"])).name.lower()]
    mmproj = [e for e in gguf if "mmproj" in Path(str(e["path"])).name.lower()]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise SystemExit("preprocess receipt must bind exactly one decoder and one mmproj")
    return decoder[0], mmproj[0]


def _promote_roster(
    *, samples, root: Path, packet_root: Path, legacy_cache: Path,
    runtime_receipt: Mapping[str, object], decoder: Mapping[str, object],
    mmproj: Mapping[str, object], workers: int,
) -> tuple[tuple, tuple[SharedSpeechFeaturePacketRecord, ...]]:
    """PROMOTE the warm legacy cache into audited packets. Zero contacts.

    Item E40: an already-promoted packet whose identity differs from this pass
    in exactly the encoder receipt hash, with identical chunks, comes back as a
    shared record instead of a refusal; nothing under the feature root is
    rewritten either way.
    """

    shared: list[SharedSpeechFeaturePacketRecord] = []
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=packet_root,
        bindings=tuple({"packet_id": sample.sample_id.replace(":", "/"),
                        "audio_path": str(root / sample.media_relpath)} for sample in samples),
        legacy_cache_dir=legacy_cache, encoder_receipt_sha256=canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder["sha256"]), mmproj_sha256=str(mmproj["sha256"]),
        expected_n_embd=EXPECTED_N_EMBD, causal_attention=True, workers=workers,
        on_shared=shared.append)
    if len(packets) != len(samples):
        raise SystemExit("promotion produced %d packets for %d samples" % (len(packets), len(samples)))
    audio_by_packet = {sample.sample_id.replace(":", "/"): sample.audio_ref.sha256 for sample in samples}
    for packet in packets:
        if packet.audio_sha256 != audio_by_packet[packet.packet_id]:
            raise SystemExit("promoted packet %s carries a different audio sha256" % packet.packet_id)
    return packets, tuple(shared)


def _promotion_receipt_document(
    *, packets, shared: Sequence[SharedSpeechFeaturePacketRecord],
    values: Mapping[str, object], packet_root: Path, legacy_cache: Path,
    decoder: Mapping[str, object], mmproj: Mapping[str, object],
    runtime_receipt: Mapping[str, object], mode: str, encode_contacts: int,
    session_id: str, session_receipt_sha256: str | None,
    stop_receipt_sha256: str | None,
) -> dict[str, object]:
    """The roster's promotion receipt, identical in both modes but for its mode.

    The per-packet entries stay exactly as they have always been -- the
    EXISTING packet's own ``packet_sha256`` -- so re-verifying this receipt
    against the packet root still holds for a shared packet. The item E40
    ``shared_packets`` ledger is provenance beside them, never instead of them.
    """

    return {
        "schema": "saea-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "count": len(packets),
        "mode": mode,
        "encode_contacts": encode_contacts,
        "dataset_runtime_view_sha256": str(values["runtime_view_sha256"]),
        "feature_root": str(packet_root),
        "legacy_cache_dir": str(legacy_cache),
        "preprocess_session_id": session_id,
        "preprocess_session_receipt_sha256": session_receipt_sha256,
        "preprocess_stop_receipt_sha256": stop_receipt_sha256,
        "runtime_receipt_sha256": canonical_sha256(runtime_receipt),
        "shared_packet_count": len(shared),
        "shared_packets": [
            record.as_json()
            for record in sorted(shared, key=lambda entry: entry.packet_id)
        ],
        "packets": [
            {"packet_id": packet.packet_id, "packet_sha256": packet.packet_sha256,
             "audio_sha256": packet.audio_sha256,
             "decoder_gguf_sha256": str(decoder["sha256"]), "mmproj_sha256": str(mmproj["sha256"])}
            for packet in sorted(packets, key=lambda entry: entry.packet_id)
        ],
    }


def _write_promotion_receipt(path: Path, receipt: Mapping[str, object]) -> str:
    """Create-only: a promotion receipt is never rewritten in place."""

    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except FileExistsError as error:
        raise SystemExit("promotion receipt already exists: %s" % path) from error
    return sha256_file(path)


def _emit(args, report: Mapping[str, object]) -> None:
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")
        log("wrote %s" % args.output)
    else:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))


def _write_union_receipt(args) -> int:
    """One promotion receipt over both TRAIN folds, from the two the sessions wrote.

    Zero contacts, no server, no encoder: a deterministic merge of two committed
    documents whose parents are recorded by sha256, so a reader can rebuild it or
    refuse it. It exists because a candidate portfolio has ONE artifact and TWO
    fold fragment variants copied from ONE base, and a base can name one receipt.
    Covers only ``FOLD_ROSTER_KEYS``; the DEV-2000-ADDED roster is a separate
    preparation with its own receipt and is never folded into this union.
    """

    root = data_root()
    parents, packets, seen = [], [], set()
    for roster_key in FOLD_ROSTER_KEYS:
        spec = PREPROCESS_ROSTERS[roster_key]
        values = compose(REPO, MODEL_FRAGMENT, spec.dataset_fragment,
                         BASELINE_FRAGMENT, spec.experiment_fragment).values
        path = Path(str(values["promotion_receipt"]))
        document = json.loads(path.read_text(encoding="utf-8"))
        parents.append({"fold": str(values["fold"]), "path": str(path),
                        "sha256": sha256_file(path), "count": int(document["count"])})
        for entry in document["packets"]:
            packet_id = str(entry["packet_id"])
            if packet_id in seen:
                raise SystemExit("the two folds share packet %s; they are disjoint by draw" % packet_id)
            seen.add(packet_id)
            packets.append(dict(entry))
        for key in ("feature_root", "legacy_cache_dir", "runtime_receipt_sha256"):
            if document[key] != json.loads(Path(str(parents[0]["path"])).read_text(encoding="utf-8"))[key]:
                raise SystemExit("the two promotion receipts disagree on %s" % key)
    first = json.loads(Path(str(parents[0]["path"])).read_text(encoding="utf-8"))
    receipt = {
        "schema": "saea-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "count": len(packets),
        "feature_root": first["feature_root"],
        "legacy_cache_dir": first["legacy_cache_dir"],
        "runtime_receipt_sha256": first["runtime_receipt_sha256"],
        "preprocess_session_id": "union of %s" % ", ".join(p["fold"] for p in parents),
        "preprocess_session_receipt_sha256": first["preprocess_session_receipt_sha256"],
        "preprocess_stop_receipt_sha256": first["preprocess_stop_receipt_sha256"],
        "dataset_runtime_view_sha256": first["dataset_runtime_view_sha256"],
        "union_of": parents,
        "union_note": (
            "MODEL-FREE MERGE, zero contacts. The two per-fold receipts are unchanged and are "
            "the authority; this document exists only because a candidate portfolio has one "
            "artifact and two fold fragment variants copied from ONE base fragment, and a base "
            "fragment names one promotion receipt. Every packet entry is copied verbatim from "
            "the fold receipt that promoted it, and the two folds are proved disjoint by draw."
        ),
        "packets": sorted(packets, key=lambda entry: str(entry["packet_id"])),
    }
    out = Path(first["feature_root"]) / "EVO-FOLDS-V2-promotion.json"
    if out.exists():
        raise SystemExit("union promotion receipt already exists: %s" % out)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    summary = {"path": str(out), "sha256": sha256_file(out), "count": len(packets),
               "parents": parents, "data_root": str(root)}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _promote_only(
    args, *, roster_key: str, spec: RosterSpec, values: Mapping[str, object],
    samples, root: Path, packet_root: Path, legacy_cache: Path,
    promotion_receipt: Path, composed, audio_seconds: float, warm: int,
) -> int:
    """PROMOTE alone, zero contacts, for a roster whose cache is already warm.

    The caller has already run the shared preflight: the frozen runtime view,
    every media file re-hashed, the promotion-receipt-absent guard, and the D1
    media-identity check through the same FrozenCoreGate --run builds. What
    this mode adds is the refusal that makes "no encoder" safe: EVERY roster
    row must already be warm, because a cold row could otherwise only be
    completed by an online encode, which this mode cannot and must not do.

    No server is started, no session or stop receipt exists, and no model is
    touched -- so no contracts.ExecutionPlan is validated and no attempt budget
    is reserved (see PROMOTE_ONLY_PLAN). The attempt is recorded by its own NEW
    run directory plus the report written into it.
    """

    attempt_id = args.attempt_id
    _require_fully_warm(warm, len(samples), roster_key)
    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    if runtime_receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    decoder, mmproj = _decoder_and_mmproj(runtime_receipt)
    run_dir = root / "runs" / spec.run_id / attempt_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise SystemExit(
            "--promote-only records a NEW attempt; %s already exists" % run_dir
        ) from error
    log("PROMOTE-ONLY: %d/%d rows warm, zero contacts, no sidecar, attempt %s"
        % (warm, len(samples), attempt_id))

    promote_started = time.time()
    packets, shared = _promote_roster(
        samples=samples, root=root, packet_root=packet_root, legacy_cache=legacy_cache,
        runtime_receipt=runtime_receipt, decoder=decoder, mmproj=mmproj,
        workers=args.promote_workers)
    promote_seconds = time.time() - promote_started
    tokens = {packet.packet_id: sum(chunk.n_tokens for chunk in packet.chunks) for packet in packets}

    receipt = _promotion_receipt_document(
        packets=packets, shared=shared, values=values, packet_root=packet_root,
        legacy_cache=legacy_cache, decoder=decoder, mmproj=mmproj,
        runtime_receipt=runtime_receipt, mode=PROMOTION_MODE_PROMOTE_ONLY,
        encode_contacts=0,
        session_id="promote-only:%s:%s" % (spec.run_id, attempt_id),
        session_receipt_sha256=None, stop_receipt_sha256=None)
    promotion_receipt_sha256 = _write_promotion_receipt(promotion_receipt, receipt)
    log("promotion receipt %s (sha256 %s, %d shared of %d)"
        % (promotion_receipt, promotion_receipt_sha256[:16], len(shared), len(packets)))

    report = {
        "schema": "saea-slurp-evo-fold-preprocess-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": spec.run_id, "attempt_id": attempt_id, "roster": roster_key,
        "mode": PROMOTION_MODE_PROMOTE_ONLY,
        "execution_profile": PROMOTE_ONLY_PROFILE,
        "fold": str(values["fold"]) if "fold" in values else None,
        "config_fragments": {"model": MODEL_FRAGMENT, "dataset": spec.dataset_fragment,
                             "baseline": BASELINE_FRAGMENT, "experiment": spec.experiment_fragment},
        "config_hash": composed.config_hash,
        "split_identity_hash": str(values["split_identity_hash"]),
        "rows": len(samples), "audio_seconds": round(audio_seconds, 6),
        "declared_plan": dict(PROMOTE_ONLY_PLAN),
        "legacy_cache_warm_before": warm,
        "contacts": 0, "failures": [],
        "promote_seconds": round(promote_seconds, 3),
        "promote_packets_per_second": round(len(packets) / max(promote_seconds, 1e-9), 4),
        "promote_workers": args.promote_workers,
        "promotion_receipt": str(promotion_receipt),
        "promotion_receipt_sha256": promotion_receipt_sha256,
        "shared_packet_count": len(shared),
        "shared_packets": [
            record.as_json() for record in sorted(shared, key=lambda entry: entry.packet_id)
        ],
        "packet_tokens": {"min": min(tokens.values()), "max": max(tokens.values()),
                          "total": sum(tokens.values())},
        "session": None,
        "run_dir": str(run_dir),
        "gpu_offload": "no server is started: this mode leaves the GPU and both ports untouched",
    }
    with (run_dir / PROMOTE_ONLY_REPORT_NAME).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")
    _emit(args, report)
    return 0


def _geometry_equivalence(
    args, *, roster_key: str, spec: RosterSpec, values: Mapping[str, object],
    samples, root: Path, legacy_cache: Path, composed, audio_seconds: float,
    binding, gate, slots: int,
) -> int:
    """ENCODE on a new serving geometry, compare, and promote NOTHING.

    The one mode that is allowed to encode a row whose packet already exists:
    it writes into a SCRATCH feature cache, never the resident one, and its
    whole output is a comparison report. ``_promote_roster`` and
    ``_write_promotion_receipt`` are unreachable from here by construction --
    the caller has already refused a promotion receipt for this roster
    (``_assert_equivalence_isolation``) and nothing below materialises a packet.
    """

    equivalence = spec.equivalence
    assert equivalence is not None
    attempt_id = args.attempt_id or spec.default_attempt_id
    if legacy_cache.exists() and any(legacy_cache.glob("*_o*.feat")):
        raise SystemExit(
            "geometry equivalence: the scratch cache %s is not empty; a stale entry would "
            "make a cache HIT look like a fresh encode. Move it aside first." % legacy_cache
        )
    legacy_cache.mkdir(parents=True, exist_ok=True)
    for sample in samples:
        packet_id = sample.sample_id.replace(":", "/")
        if not (equivalence.reference_feature_root / packet_id / "packet.json").is_file():
            raise SystemExit(
                "geometry equivalence: row %s has no resident packet to compare against"
                % sample.sample_id
            )

    for port, label in ((SIDECAR_PORT, "sidecar"), ):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                raise SystemExit("something already listens on the %s port %d" % (label, port))
        except OSError:
            pass

    plan = ExecutionPlan(
        run_id=spec.run_id, execution_profile=str(values["execution_profile"]),
        carrier_lock_key=SLURP_LOCK_KEY, split_role=spec.split_role,
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=args.plan_calls if args.plan_calls is not None else spec.plan_calls,
        planned_gpu_hours=spec.plan_gpu_hours,
        planned_speech_audio_seconds=(
            args.plan_speech_seconds if args.plan_speech_seconds is not None
            else spec.plan_speech_seconds),
        protocol_hash=composed.config_hash, attempt_id=attempt_id).validate()
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    if runtime_receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    run_dir = root / "runs" / spec.run_id / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log("spawning the CPU-only sidecar on %d at -np %d (SCRATCH cache %s)"
        % (SIDECAR_PORT, slots, legacy_cache))
    session = start_session(
        runtime_root=RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt,
        host="127.0.0.1", port=SIDECAR_PORT, session_id="%s-%s-cpu-sidecar" % (spec.run_id, attempt_id),
        extra_argv=list(values["server_args"]), extra_env=dict(values["server_env"]),
        receipt_path=run_dir / "session-preprocess.receipt.json",
        server_log_path=run_dir / "session-preprocess.server.log",
        role="preprocess", ready_timeout_seconds=1800.0)
    log("sidecar up: pid=%s port=%s" % (session.pid, session.port))

    contacts, failures, timings = 0, [], {}
    started = time.time()
    try:
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT)
        client = FrozenCoreClient(plan=plan, gate=gate, transport=transport, run_dir=run_dir,
                                  binding=binding, request_id_prefix="slurpnp8equiv")

        def encode(sample) -> tuple[str, float, str | None]:
            messages = (
                {"role": "system", "content": PREPROCESS_INSTRUCTION},
                {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
            )
            row_started = time.time()
            try:
                client.complete(messages, decoding_params=DECODING_PARAMS)
                return sample.sample_id, time.time() - row_started, None
            except Exception as error:  # noqa: BLE001 -- reported, never masked
                return sample.sample_id, time.time() - row_started, "%s: %r" % (sample.sample_id, error)

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for sample_id, seconds, problem in pool.map(encode, samples):
                timings[sample_id] = round(seconds, 3)
                if problem is None:
                    contacts += 1
                else:
                    failures.append(problem)
                    log("contact FAILED %s" % problem)
        core_receipt = client.close()
    finally:
        stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT,
                            receipt_path=run_dir / "session-preprocess.stop-receipt.json",
                            force_after_timeout=True)
        log("sidecar stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
    encode_seconds = time.time() - started
    if failures:
        raise SystemExit("%d encode contacts failed; the comparison is void: %r"
                         % (len(failures), failures[:5]))

    comparisons = [
        _compare_row_against_resident_packet(
            sample=sample, root=root, legacy_cache=legacy_cache,
            reference_root=equivalence.reference_feature_root)
        for sample in samples
    ]
    payload_equal = all(row["feature_payload_identical_to_resident_packet"] for row in comparisons)
    cache_rows = [row for row in comparisons if row["legacy_cache_file_identical_to_resident_cache"] is not None]
    cache_equal = all(row["legacy_cache_file_identical_to_resident_cache"] for row in cache_rows)
    verdict = "EQUIVALENT" if payload_equal else "NOT EQUIVALENT"
    log("geometry equivalence %s: %d/%d rows byte-identical to the resident packets"
        % (verdict, sum(1 for row in comparisons if row["feature_payload_identical_to_resident_packet"]),
           len(comparisons)))

    report = {
        "schema": "saea-sidecar-geometry-equivalence-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": spec.run_id, "attempt_id": attempt_id, "roster": roster_key,
        "mode": "geometry-equivalence",
        "verdict": verdict,
        "feature_payload_identical_on_every_row": payload_equal,
        "legacy_cache_file_identical_on_every_comparable_row": cache_equal,
        "rows_compared": len(comparisons),
        "config_fragments": {"model": spec.sidecar_fragment, "dataset": spec.dataset_fragment,
                             "baseline": BASELINE_FRAGMENT, "experiment": spec.experiment_fragment},
        "config_hash": composed.config_hash,
        "split_identity_hash": str(values["split_identity_hash"]),
        "geometry": {
            "measured_slots": slots,
            "reference_slots": equivalence.reference_geometry_slots,
            "server_args": [str(token) for token in values["server_args"]],
            "encode_workers": args.workers,
            "scratch_legacy_cache_dir": str(legacy_cache),
            "resident_legacy_cache_dir": str(DEFAULT_LEGACY_CACHE_DIR),
            "reference_feature_root": str(equivalence.reference_feature_root),
            "reference_promotion_receipt": equivalence.reference_promotion_receipt,
        },
        "rows": len(samples), "audio_seconds": round(audio_seconds, 6),
        "contacts": contacts, "failures": failures,
        "encode_seconds": round(encode_seconds, 3),
        "per_row_seconds": timings,
        "per_row_seconds_mean": round(sum(timings.values()) / max(len(timings), 1), 3),
        "per_row_audio_second_per_wall_second": round(
            audio_seconds / max(encode_seconds, 1e-9), 4),
        "comparisons": comparisons,
        "promotion": (
            "NONE. This roster promotes nothing: no packet is materialised, no promotion "
            "receipt is written, and neither the resident legacy cache nor the resident "
            "packet root is opened for writing."
        ),
        "core_client": {"trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
                        "cost": core_receipt.get("cost")},
        "session": {"session_id": session.session_id, "pid": session.pid, "stop": stop},
        "gpu_offload": "-ngl 0 --no-mmproj-offload: this pass leaves the GPU free",
    }
    _emit(args, report)
    return 0 if payload_equal else 4


def build_parser() -> argparse.ArgumentParser:
    """The driver's whole CLI surface, built where a test can read it."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fold", default=None, choices=("a", "b"),
        help="deprecated alias for --roster fold-a / --roster fold-b (kept for the sealed folds)",
    )
    parser.add_argument("--roster", default=None, choices=sorted(PREPROCESS_ROSTERS))
    parser.add_argument(
        "--workers", type=int, default=4,
        help=(
            "encode concurrency; refused above the -np the roster's own sidecar fragment "
            "serves (4 for q4km-preprocess-featcache-cpu-sidecar, 8 for its -np8 sibling)"
        ),
    )
    parser.add_argument("--promote-workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--plan-calls", type=int, default=None,
                        help="cumulative call ceiling this attempt declares (prior spend + its own)")
    parser.add_argument("--plan-speech-seconds", type=int, default=None,
                        help="cumulative speech-second ceiling this attempt declares")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument(
        "--union-receipt", action="store_true",
        help=(
            "MODEL-FREE: merge the two per-fold promotion receipts into one covering all "
            "2,160 rows. rails.evolution.write_candidate_fragments copies ONE base fragment "
            "into a fold-a and a fold-b variant, so the base can name only one promotion "
            "receipt and it has to cover both folds; the per-fold receipts stay exactly as "
            "the two sessions wrote them and this one records their sha256s as its parents. "
            "The DEV-2000-ADDED roster is never part of this union."
        ),
    )
    mode.add_argument(
        "--promote-only", action="store_true",
        help=(
            "PROMOTE phase alone, ZERO contacts: no sidecar, no session, no encoder. "
            "Requires an already fully warm legacy cache for the roster and an explicit "
            "--attempt-id, runs the same D1 / frozen-core preflight as --run, and writes "
            "the roster's promotion receipt with mode=promote-only and encode_contacts=0."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Before any config, data root, or media read: --promote-only records a NEW
    # attempt under the roster's run id and must never inherit the roster's
    # default attempt id, which an earlier ENCODE pass already used.
    if args.promote_only and args.attempt_id is None:
        raise SystemExit("--promote-only requires an explicit --attempt-id (a NEW attempt)")

    if args.union_receipt:
        return _write_union_receipt(args)

    if args.fold is not None and args.roster is not None:
        raise SystemExit("--fold and --roster are mutually exclusive; --fold is only a deprecated alias")
    roster_key = args.roster if args.roster is not None else (
        "fold-%s" % args.fold if args.fold is not None else None
    )
    if roster_key is None:
        raise SystemExit(
            "--roster (or the deprecated --fold a|b) is required for "
            "--preflight-only, --run and --promote-only"
        )
    spec = PREPROCESS_ROSTERS[roster_key]

    if args.promote_only and spec.equivalence is not None:
        raise SystemExit(
            "roster %r is a geometry-equivalence roster: it promotes nothing, so "
            "--promote-only is meaningless for it" % roster_key
        )

    lock, root = load_lock(umbrella_lock_path()), data_root()
    composed = compose(REPO, spec.sidecar_fragment, spec.dataset_fragment, BASELINE_FRAGMENT, spec.experiment_fragment)
    values = composed.values
    if str(values["experiment_id"]) != spec.run_id:
        raise SystemExit("experiment fragment names a different run id")
    if values.get("split_role") != spec.split_role:
        raise SystemExit(
            "roster %r expects dataset split_role %r, fragment carries %r"
            % (roster_key, spec.split_role, values.get("split_role"))
        )
    if spec.split_role == FINAL_REPORT_SPLIT_ROLE:
        # Owner decisions 99 and 107. A final-reporting roster is refused HERE,
        # before roster_samples() opens the first media file, in EVERY mode --
        # --preflight-only and --promote-only included. Neither of those builds
        # a contracts.ExecutionPlan, so without this call the plan validator
        # (which only --run reaches) would let a whole 700 MB media pass and a
        # cache-warmth measurement run over the test split while the owner
        # allowance is still pending. The composed config carries the pin, so
        # flipping the receipt's status breaks it and forces a deliberate
        # re-pin plus a fresh countersignature.
        require_owner_split_allowance(
            run_id=spec.run_id,
            execution_profile=str(values["execution_profile"]),
            carrier_lock_key=SLURP_LOCK_KEY,
            split_identity_hash=str(values["split_identity_hash"]),
            owner_allowance=values.get("owner_allowance"),
            source_root=REPO,
        )
    slots = _server_slots(values, spec.sidecar_fragment)
    _assert_worker_fit(args.workers, slots, roster_key, spec.sidecar_fragment)
    packet_root = Path(str(values.get("feature_root", DEFAULT_FEATURE_ROOT)))
    legacy_cache = Path(str(values.get("legacy_cache_dir", DEFAULT_LEGACY_CACHE_DIR)))
    if spec.equivalence is None:
        promotion_receipt = _resolve_promotion_receipt(values, spec, packet_root, roster_key)
    else:
        _assert_equivalence_isolation(values, spec, roster_key, packet_root, legacy_cache)
        promotion_receipt = None
    samples = roster_samples(values, root, args.promote_workers, spec.sample_id_prefix, roster_key)
    audio_seconds = sum(float(sample.audio_seconds) for sample in samples)
    log("roster %s: %d samples, %.6f audio-s, config %s"
        % (roster_key, len(samples), audio_seconds, composed.config_hash[:16]))

    warm = sum(
        1 for sample in samples
        if any(legacy_cache.glob("%s_o*.feat"
                                 % legacy_audio_feature_cache_key((root / sample.media_relpath).read_bytes())))
    )
    log("artifact preflight: %d/%d legacy cache entries warm; promotion receipt exists=%s"
        % (warm, len(samples), promotion_receipt.exists() if promotion_receipt else "n/a"))
    if promotion_receipt is not None and promotion_receipt.exists():
        raise SystemExit("promotion receipt already exists: %s" % promotion_receipt)

    binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY, samples=samples, data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root))
    media_facts = {
        sample_id: (binding.media_relpaths[sample_id], binding.sample_facts[sample_id][0])
        for sample_id in sorted(binding.allowed_sample_ids)
    }
    gate = FrozenCoreGate.for_study_repo(
        REPO, root, RUNTIME_ROOT, runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values))
    gate.verify_media_identity(SLURP_LOCK_KEY, media_facts)
    log("D1 media identity PASS for %d samples" % len(media_facts))

    if args.preflight_only:
        log("PREFLIGHT-ONLY PASS: inputs verified, zero contacts, no session, no gate open")
        return 0

    if args.promote_only:
        assert promotion_receipt is not None  # refused above for an equivalence roster
        return _promote_only(
            args, roster_key=roster_key, spec=spec, values=values, samples=samples,
            root=root, packet_root=packet_root, legacy_cache=legacy_cache,
            promotion_receipt=promotion_receipt, composed=composed,
            audio_seconds=audio_seconds, warm=warm)

    if spec.equivalence is not None:
        return _geometry_equivalence(
            args, roster_key=roster_key, spec=spec, values=values, samples=samples,
            root=root, legacy_cache=legacy_cache, composed=composed,
            audio_seconds=audio_seconds, binding=binding, gate=gate, slots=slots)

    for port, label in ((SIDECAR_PORT, "sidecar"), ):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                raise SystemExit("something already listens on the %s port %d" % (label, port))
        except OSError:
            pass
    log("preflight: %d free (the GPU inference port %d is not touched)" % (SIDECAR_PORT, INFERENCE_PORT))

    calls, speech, gpu_hours = spec.plan_calls, spec.plan_speech_seconds, spec.plan_gpu_hours
    calls = args.plan_calls if args.plan_calls is not None else calls
    speech = args.plan_speech_seconds if args.plan_speech_seconds is not None else speech
    attempt_id = args.attempt_id or spec.default_attempt_id
    plan = ExecutionPlan(
        run_id=spec.run_id, execution_profile=str(values["execution_profile"]),
        carrier_lock_key=SLURP_LOCK_KEY, split_role=spec.split_role,
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=calls, planned_gpu_hours=gpu_hours,
        planned_speech_audio_seconds=speech, protocol_hash=composed.config_hash,
        attempt_id=attempt_id,
        # None for every Stage-2 roster above (and a Stage-2 plan that declared
        # one would be refused); the final-report roster carries its committed
        # owner-allowance pin, which validate() and the gate both re-verify.
        owner_allowance=values.get("owner_allowance")).validate(source_root=REPO)
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    if runtime_receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    run_dir = root / "runs" / spec.run_id / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log("spawning the CPU-only preprocessing sidecar on %d" % SIDECAR_PORT)
    session = start_session(
        runtime_root=RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt,
        host="127.0.0.1", port=SIDECAR_PORT, session_id="%s-%s-cpu-sidecar" % (spec.run_id, attempt_id),
        extra_argv=list(values["server_args"]), extra_env=dict(values["server_env"]),
        receipt_path=run_dir / "session-preprocess.receipt.json",
        server_log_path=run_dir / "session-preprocess.server.log",
        role="preprocess", ready_timeout_seconds=1800.0)
    log("sidecar up: pid=%s port=%s" % (session.pid, session.port))

    contacts, failures, started = 0, [], time.time()
    try:
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT)
        client = FrozenCoreClient(plan=plan, gate=gate, transport=transport, run_dir=run_dir,
                                  binding=binding, request_id_prefix="slurpevoprep")

        def encode(sample: SlurpSample) -> str | None:
            messages = (
                {"role": "system", "content": PREPROCESS_INSTRUCTION},
                {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
            )
            try:
                client.complete(messages, decoding_params=DECODING_PARAMS)
                return None
            except Exception as error:  # noqa: BLE001 -- reported, never masked
                return "%s: %r" % (sample.sample_id, error)

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for index, problem in enumerate(pool.map(encode, samples), start=1):
                if problem is None:
                    contacts += 1
                else:
                    failures.append(problem)
                    log("contact FAILED %s" % problem)
                if index % 100 == 0 or index == len(samples):
                    log("encode %d/%d (%d ok, %d failed, %.1fs)"
                        % (index, len(samples), contacts, len(failures), time.time() - started))
        core_receipt = client.close()
    finally:
        stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT,
                            receipt_path=run_dir / "session-preprocess.stop-receipt.json",
                            force_after_timeout=True)
        log("sidecar stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
    encode_seconds = time.time() - started
    if failures:
        raise SystemExit("%d encode contacts failed; refusing to promote a partial cache: %r"
                         % (len(failures), failures[:5]))

    decoder, mmproj = _decoder_and_mmproj(runtime_receipt)
    promote_started = time.time()
    packets, shared = _promote_roster(
        samples=samples, root=root, packet_root=packet_root, legacy_cache=legacy_cache,
        runtime_receipt=runtime_receipt, decoder=decoder, mmproj=mmproj,
        workers=args.promote_workers)
    promote_seconds = time.time() - promote_started
    tokens = {packet.packet_id: sum(chunk.n_tokens for chunk in packet.chunks) for packet in packets}

    receipt = _promotion_receipt_document(
        packets=packets, shared=shared, values=values, packet_root=packet_root,
        legacy_cache=legacy_cache, decoder=decoder, mmproj=mmproj,
        runtime_receipt=runtime_receipt, mode=PROMOTION_MODE_ENCODE_AND_PROMOTE,
        encode_contacts=contacts, session_id=session.session_id,
        session_receipt_sha256=canonical_sha256(session.as_json()),
        stop_receipt_sha256=canonical_sha256(stop))
    promotion_receipt_sha256 = _write_promotion_receipt(promotion_receipt, receipt)
    log("promotion receipt %s (sha256 %s, %d shared)"
        % (promotion_receipt, promotion_receipt_sha256[:16], len(shared)))

    report = {
        "schema": "saea-slurp-evo-fold-preprocess-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": spec.run_id, "attempt_id": attempt_id, "roster": roster_key,
        "mode": PROMOTION_MODE_ENCODE_AND_PROMOTE,
        "fold": str(values["fold"]) if "fold" in values else None,
        "config_fragments": {"model": MODEL_FRAGMENT, "dataset": spec.dataset_fragment,
                             "baseline": BASELINE_FRAGMENT, "experiment": spec.experiment_fragment},
        "config_hash": composed.config_hash,
        "split_identity_hash": str(values["split_identity_hash"]),
        "rows": len(samples), "audio_seconds": round(audio_seconds, 6),
        "declared_plan": {"calls": calls, "speech_audio_seconds": speech,
                          "gpu_hours": gpu_hours,
                          "basis": "run-cumulative: prior durable spend on this run id plus this attempt's own worst case"},
        "legacy_cache_warm_before": warm,
        "contacts": contacts, "failures": failures,
        "encode_seconds": round(encode_seconds, 3),
        "encode_rows_per_second": round(len(samples) / max(encode_seconds, 1e-9), 4),
        "encode_workers": args.workers,
        "promote_seconds": round(promote_seconds, 3),
        "promote_packets_per_second": round(len(packets) / max(promote_seconds, 1e-9), 4),
        "promote_workers": args.promote_workers,
        "promotion_receipt": str(promotion_receipt),
        "promotion_receipt_sha256": promotion_receipt_sha256,
        "shared_packet_count": len(shared),
        "packet_tokens": {"min": min(tokens.values()), "max": max(tokens.values()),
                          "total": sum(tokens.values())},
        "core_client": {"trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
                        "cost": core_receipt.get("cost")},
        "session": {"session_id": session.session_id, "pid": session.pid, "stop": stop},
        "gpu_offload": "-ngl 0 --no-mmproj-offload: this pass leaves the GPU free",
    }
    _emit(args, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
