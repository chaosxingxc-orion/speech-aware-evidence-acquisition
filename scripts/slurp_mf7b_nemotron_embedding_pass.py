#!/usr/bin/env python3
"""MF-7b (b): the Omni-Embed-Nemotron-3B encoder pass for the SLURP key audit.

Exposure row ``SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1``, registered before the
first contact. **Tool-level contacts only; 0 frozen-core contacts.**
Preregistration:
``docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md``.

Same four sets, same ``saea-mf7-vectors-v1`` JSONL schema and same resumable
receipt as the LCO pass, so the two encoders are byte-comparable:
``nemotron-q-speech-query-vectors.jsonl``,
``nemotron-fused-q-speech-query-vectors.jsonl``, ``nemotron-key-vectors.jsonl``
and ``nemotron-label-key-vectors.jsonl``.

THE LOADER, and why it is not ``sentence_transformers``. The model ships a
``sentence_bert_config.json`` naming
``sentence_transformers.base.modules.transformer.Transformer``, but importing
``sentence_transformers`` RAISES in this venv: it pulls ``torchcodec``, which
cannot load ``libavutil`` because **ffmpeg is deliberately absent from this
machine and must never be installed**. So the three shipped modules are
reproduced by hand through plain ``transformers``, exactly as the config
specifies them and with nothing guessed:

* module 0 -- ``NVOmniEmbedModel`` (``trust_remote_code=True``), a
  ``Qwen2_5OmniThinkerForConditionalGeneration`` whose text tower is
  bidirectional; the token embeddings are ``hidden_states[-1]``, which is what
  ``sentence_bert_config.json``'s ``method_output_name`` names;
* module 1 -- ``1_Pooling/config.json``: MEAN pooling over the attention mask,
  ``include_prompt: true``, 2,048 dims;
* module 2 -- L2 normalise.

The wire format is the model's OWN ``additional_chat_templates/
sentence_transformers.jinja``, read from the model directory and rendered by
``processor.apply_chat_template`` rather than hand-written here, and the
contract prompts of ``config_sentence_transformers.json`` are used verbatim:
``"query: "`` for the DEV speech queries and ``"passage: "`` for the TRAIN text
keys.

Audio goes through ``soundfile`` (never ffmpeg) at batch 1, so no padded batch
can contaminate a short clip. The held-out ``test`` split is never named and no
devel sentence text is read.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.slurp_mf7b_vectors import (  # noqa: E402
    RECEIPT_SCHEMA,
    SAMPLE_RATE_HZ,
    dev_rows,
    draft_texts,
    label_key_texts,
    read_audio_array,
    sha256_file,
    train_facets,
    vector_set_block,
    write_vectors_jsonl,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

from speech_aware_evidence_acquisition.core.speech_embedding import (  # noqa: E402
    load_stack, render, encode,
)

ROW_ID = "SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1"
ENCODER_ID = "omni-embed-nemotron-3b"
DIMS = 2048
MODEL_SUBDIR = "models/omni-embed-nemotron-3b"
QUERY_PROMPT = "query: "
PASSAGE_PROMPT = "passage: "
CEILING_CONTACTS = 13600








def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-batch", type=int, default=16)
    parser.add_argument("--sets", default="speech,fused,keys,labels")
    parser.add_argument("--limit", type=int, default=0, help="dry-run row cap (0 = all)")
    parser.add_argument("--no-write", action="store_true", help="dry run: emit no files")
    args = parser.parse_args()
    wanted = {name.strip() for name in args.sets.split(",") if name.strip()}

    root = Path(data_root())
    model_dir = root / MODEL_SUBDIR
    out_dir = root / "vectors/slurp-mf7b"
    out_dir.mkdir(parents=True, exist_ok=True)

    processor, model, template = load_stack(model_dir)
    rows = dev_rows(root)
    facets = train_facets(root)
    drafts = draft_texts(root)
    if args.limit:
        rows = rows[: args.limit]
        facets = facets[: args.limit]

    receipt_sets: dict[str, dict] = {}
    audio_seconds = 0.0
    contacts = 0
    forwards = 0
    jitter: dict[str, object] | None = None
    started_all = time.time()

    def text_pass(items: list[tuple[str, str]], prompt: str, name: str, filename: str,
                  extra: dict) -> None:
        nonlocal contacts, forwards
        ids: list[str] = []
        vectors: list[tuple[float, ...]] = []
        started = time.time()
        for offset in range(0, len(items), args.text_batch):
            chunk = items[offset : offset + args.text_batch]
            rendered = [
                render(processor, template, [{"type": "text", "text": prompt + text}])
                for _identifier, text in chunk
            ]
            vectors.extend(encode(processor, model, rendered, None))
            ids.extend(identifier for identifier, _text in chunk)
            forwards += 1
            contacts += len(chunk)
        wall = time.time() - started
        if args.no_write:
            print(f"{name}: {len(ids)} in {wall:.1f}s (dry run, nothing written)")
            print("  rendered[0] =", repr(rendered[0][:220]))
            return
        path = write_vectors_jsonl(out_dir / filename, ids, vectors)
        receipt_sets[name] = vector_set_block(
            path, ids, vectors, wall,
            extra={"batch_size": args.text_batch, "prompt": prompt, **extra})
        print(f"{name}: {len(ids)} in {wall:.1f}s")

    if "keys" in wanted:
        text_pass([(row["facet_id"], row["text"]) for row in facets], PASSAGE_PROMPT,
                  "nemotron-train-text", "nemotron-key-vectors.jsonl",
                  {"key_space": "TRAIN utterance texts"})
    if "labels" in wanted:
        text_pass(label_key_texts(root), PASSAGE_PROMPT, "nemotron-label-text",
                  "nemotron-label-key-vectors.jsonl",
                  {"key_space": "60 intent label descriptions",
                   "label_text_rule": "saea-mf7b-label-text-v1"})

    for set_name, filename, fused in (
        ("q-speech-nemotron", "nemotron-q-speech-query-vectors.jsonl", False),
        ("q-speech-nemotron-fused", "nemotron-fused-q-speech-query-vectors.jsonl", True),
    ):
        key = "fused" if fused else "speech"
        if key not in wanted:
            continue
        ids = []
        vectors = []
        seconds = 0.0
        started = time.time()
        for index, row in enumerate(rows):
            wave = read_audio_array(root / row["media_relpath"])
            content: list[dict] = [{"type": "text", "text": QUERY_PROMPT}, {"type": "audio"}]
            if fused:
                content.append({"type": "text", "text": "\n" + drafts[row["sample_id"]]})
            rendered = render(processor, template, content)
            vector = encode(processor, model, [rendered], [wave])[0]
            ids.append(row["sample_id"])
            vectors.append(vector)
            seconds += float(row["audio_seconds"])
            contacts += 1
            forwards += 1
            if index == 0 and not fused:
                again = encode(processor, model, [rendered], [wave])[0]
                contacts += 1
                forwards += 1
                jitter = {
                    "sample_id": row["sample_id"],
                    "bit_exact": again == vector,
                    "max_abs_delta": max(
                        abs(a - b) for a, b in zip(again, vector, strict=True)
                    ),
                }
            if (index + 1) % 100 == 0:
                print(f"{set_name} {index + 1}/{len(rows)} at "
                      f"{(index + 1) / (time.time() - started):.2f}/s", flush=True)
        wall = time.time() - started
        audio_seconds += seconds
        if args.no_write:
            print(f"{set_name}: {len(ids)} in {wall:.1f}s (dry run, nothing written)")
            print("  rendered =", repr(rendered[:260]))
            continue
        path = write_vectors_jsonl(out_dir / filename, ids, vectors)
        receipt_sets[set_name] = vector_set_block(
            path, ids, vectors, wall,
            extra={"batch_size": 1, "prompt": QUERY_PROMPT,
                   "audio_seconds_encoded": seconds,
                   "realtime_factor": seconds / wall if wall else None,
                   "request_shape": (
                       "sentence_transformers.jinja user message: 'query: ' + audio"
                       + (" + newline + the sealed KU-S1c draft text" if fused else "")),
                   **({"state_source": "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1 phase-1 "
                                       "draft response text, sealed"} if fused else {})})
        print(f"{set_name}: {len(ids)} in {wall:.1f}s")

    total_wall = time.time() - started_all
    if args.no_write:
        print(json.dumps({"contacts": contacts, "forwards": forwards,
                          "wall_seconds": round(total_wall, 1), "jitter": jitter}, indent=1))
        return 0

    receipt_path = out_dir / "nemotron.receipt.json"
    prior = (
        json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else {}
    )
    prior_sets = dict(prior.get("sets", {}))
    prior_acct = dict(prior.get("accounting", {}))
    prior_passes = list(prior.get("passes", []))
    prior_passes.append({"sets": sorted(wanted), "contacts": contacts,
                         "forwards": forwards, "wall_seconds": total_wall,
                         "speech_audio_seconds": audio_seconds})
    import torch
    import transformers

    write_json_artifact(receipt_path, {
        "schema": RECEIPT_SCHEMA,
        "exposure_ledger_row": ROW_ID,
        "embedder": {
            "encoder_id": ENCODER_ID,
            "role": "pinned TOOL-level omni embedder; never the frozen core",
            "model_dir_relpath": MODEL_SUBDIR,
            "loader": "transformers.AutoModel.from_pretrained(local dir, "
            "trust_remote_code=True, dtype=bfloat16, attn_implementation='sdpa')",
            "sentence_transformers_imported": False,
            "config_sha256": sha256_file(model_dir / "config.json"),
            "modeling_sha256": sha256_file(model_dir / "modeling_nv_omni_embed.py"),
            "tokenizer_sha256": sha256_file(model_dir / "tokenizer.json"),
            "chat_template_sha256": sha256_file(
                model_dir / "additional_chat_templates/sentence_transformers.jinja"),
            "safetensors_sha256": {
                name: sha256_file(model_dir / name)
                for name in ("model-00001-of-00002.safetensors",
                             "model-00002-of-00002.safetensors")
            },
            "dims": DIMS,
            "pooling": "mean over the attention mask, include_prompt=true, then L2 normalise",
            "prompts": {"query": QUERY_PROMPT, "passage": PASSAGE_PROMPT},
            "device": "cuda",
            "dtype": "bfloat16",
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "gpu": True,
        },
        "sets": {**prior_sets, **receipt_sets},
        "jitter_pair": jitter if jitter is not None else prior.get("jitter_pair"),
        "passes": prior_passes,
        "accounting": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": int(prior_acct.get("embedding_tool_contacts", 0))
            + contacts,
            "forward_passes": int(prior_acct.get("forward_passes", 0)) + forwards,
            "registered_ceiling_contacts": CEILING_CONTACTS,
            "speech_audio_seconds": float(prior_acct.get("speech_audio_seconds", 0.0))
            + audio_seconds,
            "wall_seconds": float(prior_acct.get("wall_seconds", 0.0)) + total_wall,
            "gpu_hours": (float(prior_acct.get("wall_seconds", 0.0)) + total_wall) / 3600.0,
        },
        "boundary": {
            "held_out_test_split_named": False,
            "devel_sentence_text_read": False,
            "generation_endpoint_contacted": False,
            "ffmpeg_invoked": False,
        },
    })
    print(json.dumps({"contacts": contacts, "forwards": forwards,
                      "wall_seconds": round(total_wall, 1),
                      "gpu_hours": round(total_wall / 3600.0, 4)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
