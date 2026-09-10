"""Configure exact-window encoding through the shared gate, client and lease."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .configured_transport import build_configured_transport
from .config import model_materialization_root
from .model.paths import _normalized_relative_path, _resolve_confined
from .model.slices import SliceRegistry
from .preparation import PreparationError, digest, hash_stable_file, load_artifact
from .preparation_encoding import (
    encode_window_feature_cache,
    window_encoding_sources,
    validate_window_encoding_parameters,
)
from .preparation_runtime import verify_feature_encoder_runtime
from .preparation_windows import WINDOW_FEATURE_INVENTORY_KIND
from .session import load_runtime_receipt
from .session.serving import SESSION_RECEIPT_NAME, serving_session_dir
from .session.worker import LeaseCheckedTransport, attach_worker_session

_SPEC_KEYS = {
    "inventory_relpath",
    "inventory_sha256",
    "source_run_id",
    "expected_n_embd",
    "instruction",
}


def _spec(values):
    spec = values.get("window_feature_preparation")
    if not isinstance(spec, Mapping) or set(spec) != _SPEC_KEYS:
        raise PreparationError(
            "window_feature_preparation requires exact registered fields"
        )
    width = spec["expected_n_embd"]
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise PreparationError(
            "window_feature_preparation embedding width must be positive"
        )
    for key in ("source_run_id", "instruction"):
        if not isinstance(spec[key], str) or not spec[key]:
            raise PreparationError(f"window_feature_preparation {key} must be nonempty")
    if "/" in spec["source_run_id"] or "\\" in spec["source_run_id"]:
        raise PreparationError("window feature source run must be a plain identifier")
    return spec


def _inventory(spec, data_root):
    relative = _normalized_relative_path(spec["inventory_relpath"], "window inventory")
    path = _resolve_confined(
        data_root, relative, data_root, "window inventory", strict=True
    )
    try:
        wrapper = json.loads(path.read_bytes())
        inputs = wrapper["inputs"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise PreparationError("window inventory artifact is invalid") from error
    return load_artifact(
        path,
        expected_sha256=spec["inventory_sha256"],
        kind=WINDOW_FEATURE_INVENTORY_KIND,
        inputs=inputs,
    )


def prepare_window_feature_encoding(
    runtime,
    output: Path,
    *,
    policy,
    attach=None,
    client_factory=None,
    transport_factory=None,
):
    """Attach for a cold encoder operation; verify a warm artifact without contact.

    The root owns service start, normal stop and lease release. This operation
    never starts or stops a process and cannot mint its own execution capability.
    """
    context = runtime.preparation_context()
    values = context["values"]
    spec = _spec(values)
    validate_window_encoding_parameters(
        values.get("decoding_params"), spec["instruction"]
    )
    receipt = context["runtime_receipt"]
    if receipt.get("role") != "preprocess":
        raise PreparationError("window encoding requires a preprocess runtime receipt")
    if values.get("arm") != "bare-core":
        raise PreparationError(
            "window encoding uses the registered bare-core preprocessing arm"
        )
    env = values.get("server_env")
    if not isinstance(env, Mapping) or not isinstance(
        env.get("LLAMA_MTMD_FEAT_CACHE_DIR"), str
    ):
        raise PreparationError(
            "window encoding requires an explicitly configured feature cache"
        )
    if any(
        key in env
        for key in (
            "LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT",
            "LLAMA_MTMD_FEAT_CACHE_VALIDATE",
        )
    ):
        raise PreparationError(
            "preprocessing refuses require-hit or validation re-encoding modes"
        )
    cache = Path(env["LLAMA_MTMD_FEAT_CACHE_DIR"])
    if not cache.is_absolute() or not cache.is_dir():
        raise PreparationError(
            "window encoding cache must be an existing absolute directory"
        )
    root = Path(context["data_root"])
    model_root = model_materialization_root(values)
    verified = verify_feature_encoder_runtime(
        repo_root=Path(context["repo_root"]),
        data_root=Path(model_root) if model_root else root,
        runtime_root=Path(context["runtime_root"]),
        values={**values, "feature_encoder_runtime_receipt": values["runtime_receipt"]},
        generation_receipt=receipt,
        receipt_loader=load_runtime_receipt,
    )
    if verified is None:
        raise PreparationError("preprocess runtime identity is absent")
    inventory = _inventory(spec, root)
    if inventory.get("encoder_identity") != verified.encoder_identity.as_json():
        raise PreparationError(
            "window inventory encoder identity differs from actual runtime"
        )
    sources = window_encoding_sources(inventory)
    if {source["sample_id"] for source in sources.values()} != set(
        context["sample_ids"]
    ):
        raise PreparationError(
            "window inventory does not cover the declared sample roster"
        )
    parents = {}
    for source in sources.values():
        media = _normalized_relative_path(source["media_relpath"], "prepared window")
        if Path(media).parts[:3] != ("derived", "obs-slices", spec["source_run_id"]):
            raise PreparationError(
                "window source is outside its registered source-run prefix"
            )
        parent_rel = _normalized_relative_path(
            source["parent_media_relpath"], "window parent"
        )
        parent = _resolve_confined(root, parent_rel, root, "window parent", strict=True)
        expected = source["parent_sha256"]
        if parent not in parents:
            parents[parent] = hash_stable_file(parent, "window parent")[1]
        if parents[parent] != expected:
            raise PreparationError(
                "window parent bytes differ from the prepared inventory"
            )
    plan = context["execution_plan"]
    if plan.planned_model_calls != len(sources):
        raise PreparationError(
            "fresh window encoding plan must match the unique-input contact count"
        )
    session_path = (
        serving_session_dir(root, policy.expected_session_id) / SESSION_RECEIPT_NAME
    )
    session_hash = hash_stable_file(session_path, "preprocess session receipt")[1]
    arguments = dict(
        inventory=inventory,
        data_root=root,
        encoder_identity=verified.encoder_identity.as_json(),
        legacy_cache_dir=cache,
        expected_n_embd=spec["expected_n_embd"],
        output_path=Path(output),
        run_id=context["run_id"],
        attempt_id=context["attempt_id"],
        session_id=policy.expected_session_id,
        runtime_receipt_file_sha256=verified.receipt_sha256,
        runtime_receipt_document_sha256=digest(receipt),
        session_receipt_file_sha256=session_hash,
        decoding_params=values["decoding_params"],
        instruction=spec["instruction"],
    )

    def guard():
        policy.assert_lease(
            root, run_id=context["run_id"], attempt_id=context["attempt_id"]
        )

    if Path(output).exists():
        return encode_window_feature_cache(
            client=None, custody_guard=guard, **arguments
        )
    checked_plan, gate = runtime.authorize_preparation_client(contact_cap=len(sources))
    if checked_plan != plan:
        raise PreparationError(
            "authorized encoding plan differs from preparation context"
        )
    guard()
    session_dir, document, session = (attach or attach_worker_session)(
        policy=policy,
        data_root=root,
        run_id=context["run_id"],
        attempt_id=context["attempt_id"],
        required_identity=context["required_identity"],
        runtime_receipt=receipt,
        runtime_root=context["runtime_root"],
    )
    if (
        Path(session_dir) / SESSION_RECEIPT_NAME != session_path
        or document["session_id"] != policy.expected_session_id
        or session.role != "preprocess"
    ):
        raise PreparationError(
            "attached preprocessing session differs from registered identity"
        )
    if hash_stable_file(session_path, "preprocess session receipt")[1] != session_hash:
        raise PreparationError("preprocess session receipt changed during attachment")
    transport = build_configured_transport(
        values,
        root,
        session=session,
        repo_root=Path(context["repo_root"]),
        runtime_receipt=receipt,
        runtime_root=context["runtime_root"],
        transport_factory=transport_factory,
    )
    kwargs = runtime.frozen_core_client_kwargs(
        plan=checked_plan, gate=gate, transport=LeaseCheckedTransport(transport, guard)
    )
    binding = kwargs["binding"]
    registry = SliceRegistry(
        data_root=root,
        run_id=spec["source_run_id"],
        parent_facts={
            sample_id: (
                binding.media_relpaths[sample_id],
                binding.sample_facts[sample_id][0],
            )
            for sample_id in binding.allowed_sample_ids
        },
    )
    from ..rails.core_client import FrozenCoreClient

    client = (client_factory or FrozenCoreClient)(**kwargs, slice_registry=registry)
    return encode_window_feature_cache(client=client, custody_guard=guard, **arguments)
