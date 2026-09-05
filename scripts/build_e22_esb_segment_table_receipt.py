#!/usr/bin/env python3
"""Pin the ESB Earnings-22 segment table this study cuts its utterances at.

``sanchit-gandhi/earnings22_split`` is the published partition of the
Earnings-22 corpus by source file that the Open ASR Leaderboard's
"Earnings22" column is computed over. This study needs exactly six of its
columns -- ``source_id``, ``segment_id``, ``sentence``, ``start_ts``,
``end_ts``, ``id`` -- to cut the six ESB TEST calls it already owns into the
published utterances.

**This table is a derived-split REFERENCE pinned by hash, not a new umbrella
lock asset.** It adds no entry to ``docs/datasets.lock.json``, materializes
no new audio, and is never resolved through ``data.lock``/``data.carriers``.
The only audio this study sends stays the locked ``earnings22-original``
MP3 bytes D1 already closed over.

Identity, in three independent layers:

1. **The upstream repository.** Pinned at commit
   ``f9fb35f4134e32b9c8100199d949398fd6d08a5f`` -- a content hash, not a
   branch name. Each of the four ``test-*`` parquet files is pinned by the
   repository's own git-LFS ``oid``, which IS the SHA-256 of the file's
   bytes.
2. **A local re-hash.** All four test shards (1.10 GB) were fetched with a
   resumable ranged GET -- a single unranged stream broke twice with
   ``IncompleteRead`` on this link -- and every one of them is re-hashed here
   and compared with the published LFS oid; a disagreement is a hard refusal.
   The receipt records, per file, whether the pin was confirmed locally or
   rests on the published oid alone, so a future rebuild on a machine that
   never fetched the bytes still produces an honest receipt rather than a
   silently weaker one.
3. **The extracted table.** The six metadata columns are read with a pyarrow
   COLUMN PROJECTION so the ``audio`` column is never materialized, written
   to one JSONL under the controlled data root, and hash-pinned here. That
   file -- not the parquet -- is what the roster builder and the ESB scorers
   actually consume, and it is what every downstream receipt binds to.

Row count: this table carries **2,735** test rows. The leaderboard config
``hf-audio/open-asr-leaderboard`` reports **2,741** for the same column. The
six-row gap is unexplained and is recorded here as unresolved rather than
reconciled by guesswork.

Zero model contact, zero tokenizer contact, no audio decode.

Two populations, one pin
------------------------

``--profile test`` (the default) is the sealed 2026-09-04 six-call ESB TEST
subset and every value it produces is unchanged. ``--profile dev10`` pins the
ESB **train** rows of this study's own Earnings-22 ``dev`` subset10 -- the ten
calls ``docs/receipts/splits.json`` already assigns that role -- for the
2026-09-05 prompt A/B experiment. Same repository, same revision, same six
metadata columns, same column-projected read.

The train split carries 113 source calls and 103 of them are in this study's
confirmatory split, so the ``dev10`` extraction filters every record batch by
``source_id`` **before** a row can be retained. No confirmatory sentence,
boundary or per-call count is written, printed or counted anywhere.

Usage::

    python scripts/build_e22_esb_segment_table_receipt.py --write
    python scripts/build_e22_esb_segment_table_receipt.py --profile dev10 --extract --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]

DATASET_REPO_ID = "sanchit-gandhi/earnings22_split"
DATASET_REVISION = "f9fb35f4134e32b9c8100199d949398fd6d08a5f"
COLUMNS = ("source_id", "segment_id", "sentence", "start_ts", "end_ts", "id")
ESB_TEST_CALLS = ("4432298", "4450488", "4470290", "4479741", "4483338", "4485244")
ESB_VALIDATION_CALLS = ("4420696", "4448760", "4461799", "4469836", "4473238", "4482110")
LEADERBOARD_ROW_COUNT = 2741

SEGMENT_TABLE_SUBDIR = "derived/e22-esb-segment-table"
EXTRACTED_RELPATH = f"{SEGMENT_TABLE_SUBDIR}/segments-test.jsonl"
PARQUET_SUBDIR = f"{SEGMENT_TABLE_SUBDIR}/parquet"

# (repo-relative path, git-LFS oid == SHA-256 of the file bytes, size in bytes,
# xet hash) exactly as https://huggingface.co/api/datasets/<repo>/tree/main
# reports them at the pinned revision.
PARQUET_FILES = (
    (
        "data/test-00000-of-00004-d1f708ede2712e90.parquet",
        "59c6dda0a955fd2435ff186ff675954b14dd84ef3716dc4190844ddfa6c6622c",
        383221699,
        "8e5cd221d86ce4ebda9f55585b6d566c6ea4e1c4f0addda07d4b98e9d7aab80b",
    ),
    (
        "data/test-00001-of-00004-f75446185bfca385.parquet",
        "99f92bdeb3965ee02a289100c4085d1024a0bfdb9045bcfb6c19e171c81e73ca",
        304147076,
        "a5108eff5925eb781299f265ca2986652ee5537f902f92848b74b95c0e231353",
    ),
    (
        "data/test-00002-of-00004-0090a7442c459172.parquet",
        "f2f5cf44af8264547646e3e26131e993a705fc1d7adb3770a6ffecd45e13d059",
        218834748,
        "abe269d53baa5ad2891e76822d1569718cd6b3fdcf37bca9ec48462b6f3612c2",
    ),
    (
        "data/test-00003-of-00004-c18462f0ad18104e.parquet",
        "427a0c400efd66f351a1bbba2713c1255e2cb875679a84ea8262dbf39611bf8b",
        194875805,
        "14f400c9d375bdf3423687f8db77626fe1a4f61e1d8717093c158f69e1cb5551",
    ),
)

# The parquet schema the extractor saw, recorded so a future re-extraction
# that silently changes a column type is visible.
PARQUET_SCHEMA = (
    "source_id:string",
    "audio:struct<bytes: binary, path: string>",
    "segment_id:string",
    "sentence:string",
    "start_ts:float",
    "end_ts:float",
    "id:string",
)

# ---------------------------------------------------------------------------
# The ESB TRAIN half, restricted to this study's own Earnings-22 DEV subset10.
#
# The 2026-09-05 prompt A/B experiment runs on the ten calls
# ``docs/receipts/splits.json`` already assigns this study's ``dev`` role, and
# their ESB utterance boundaries and cleaned ``sentence`` references live in the
# TRAIN split of the same pinned repository. Nothing else about the pin changes:
# same repo id, same revision, same six metadata columns, same column-projected
# read that never materializes the ``audio`` column.
#
# CONFINEMENT, and why it is not optional. The train split carries 113 source
# calls, and 103 of them are in this study's earnings22-original CONFIRMATORY
# split. The extractor therefore filters EVERY batch by ``source_id`` before a
# row can reach a list, a file, a log line or a receipt: only rows whose
# ``source_id`` is one of the ten dev calls are ever retained. No confirmatory
# sentence, boundary or per-call count is written down, printed or counted.
DEV10_CALLS = (
    "4453225",
    "4469088",
    "4470684",
    "4474506",
    "4479944",
    "4481952",
    "4482383",
    "4482613",
    "4483937",
    "4485192",
)
# The published train row count for the whole split, recorded as a table-level
# fact about the upstream repository (it is public dataset metadata, not a read
# of any call).
TRAIN_ROW_COUNT_PUBLISHED = 11352

TRAIN_EXTRACTED_RELPATH = f"{SEGMENT_TABLE_SUBDIR}/segments-dev10.jsonl"

# (repo-relative path, git-LFS oid == SHA-256 of the file bytes, size in bytes)
# exactly as https://huggingface.co/api/datasets/<repo>/tree/<revision> reports
# them. The train shards are 22.0 GB in total and are NOT fetched: the column
# projection reads them over ranged GETs through ``HfFileSystem``, so each
# shard's pin rests on the published LFS oid and the receipt says so.
TRAIN_PARQUET_FILES = (
    (
        "data/train-00000-of-00055-96835aacf0889399.parquet",
        "5a54c68d5c79bf741122057a146deadea9f58afbf8613c0ef53836c15543ce86",
        458883213,
    ),
    (
        "data/train-00001-of-00055-6e035819f66245ee.parquet",
        "2eda533722a8137f62262c10291b58dc007a2edf914e24feddd8917650a5ced8",
        622585995,
    ),
    (
        "data/train-00002-of-00055-a7aab4b0f4acd652.parquet",
        "9fe021cc02b60a6d6b730291fa4621a3abf3122ca3204201953679390832f241",
        570949545,
    ),
    (
        "data/train-00003-of-00055-b01e4ab987951502.parquet",
        "402918a99ce8da5fe2d1bbbdb670f891cfd22e2cd5bf15f0afd8c7ef88ca82ef",
        311782991,
    ),
    (
        "data/train-00004-of-00055-fa3e87fa669737ba.parquet",
        "5dc18b99c41ea9cda6aa166885a1ff4935fb9d9d437c97a2cd154c2f2c29547e",
        456038276,
    ),
    (
        "data/train-00005-of-00055-a2acda464e906867.parquet",
        "9fe14019075eaf5469f4a067e89fdbc718ea59388f22e07b7472fc45fc351f42",
        536691801,
    ),
    (
        "data/train-00006-of-00055-17c60b26be427434.parquet",
        "6e30510f09a061537e630a4c8af8ce0d06980241213d58219870e8ede679b91f",
        287271234,
    ),
    (
        "data/train-00007-of-00055-142f0fd2d0f407aa.parquet",
        "9a829b556e131604700492d6f14118d08bc9db32470180300d3933de5209077c",
        318614484,
    ),
    (
        "data/train-00008-of-00055-1e8d89bfd8f3cca2.parquet",
        "9b79d8d4e1ca7d6acf9caac9018687233a953b4c5a032609c4adc00098116fcd",
        366493574,
    ),
    (
        "data/train-00009-of-00055-2d24c33def44dc45.parquet",
        "585b3d56d77ea5dd2a23bec0f2b28370663effcbef32a6ddb5009c2758934d1a",
        168343190,
    ),
    (
        "data/train-00010-of-00055-83e7089edcd27032.parquet",
        "f5c9f98d6184de3b62c8da29d1d9e3fa9bfbea5442213eab4160b67c91d51f01",
        271678293,
    ),
    (
        "data/train-00011-of-00055-6ff9515729b6cfbb.parquet",
        "5f99b802335bdf81939b3cd20961373d114a7b5c15e1244177bbbb538091724c",
        525704219,
    ),
    (
        "data/train-00012-of-00055-d20ce81d6a749134.parquet",
        "b1e799f9d4519ee62b98b7c4df3ea6d725e5692ffdc1aaec1666174bed2a97bb",
        351474482,
    ),
    (
        "data/train-00013-of-00055-db0eb0d3abe526e4.parquet",
        "d6aae9355ed88eeedcac98aac6a12c35c4052cb6065a296b0c70e555f69ff417",
        404613406,
    ),
    (
        "data/train-00014-of-00055-7a530de4322bbf7f.parquet",
        "da0d10ec971d3a7d463f9b03014e2acfbea174971773c3c94fb739f5678dc9d6",
        484101838,
    ),
    (
        "data/train-00015-of-00055-0a2de5e78f85b88b.parquet",
        "502abd0ad0d15a131320dd3ab0bcd980a997e2a29a334c39b88bf5caf2051dc7",
        452073734,
    ),
    (
        "data/train-00016-of-00055-a74bfcdec6c2f16d.parquet",
        "6585d4243f3fb7b714bb31b9da83617a3fcfde5d18b14c29e855e5253ec323ea",
        327368670,
    ),
    (
        "data/train-00017-of-00055-35c3af4e864f8003.parquet",
        "39211c7927bb396ecfbbf27c5eb10c2283bf75ee4668d9ca4f7d322126b56d64",
        694693518,
    ),
    (
        "data/train-00018-of-00055-22a5f2e84070b8a7.parquet",
        "ea9afd991dcd3e62fe0ce25414c63ea1faee828e7b59d4d672470d07e78612a0",
        294787594,
    ),
    (
        "data/train-00019-of-00055-cbda0b602204738d.parquet",
        "56346cb8b5def69fd9c51b3d442feaa41326e69c06696b7cdd1e16426368a621",
        234413131,
    ),
    (
        "data/train-00020-of-00055-79c9c5aea5385ee2.parquet",
        "d94f33a5d1149c9a2e07e266f867f74e1b60cd1ff38ccafec3b3725e1d96ff59",
        182285398,
    ),
    (
        "data/train-00021-of-00055-8b8fdeba065d8c29.parquet",
        "db77f0d954c1e89e488bab1d7edccc6b9de00add5b1d0d2e97d559e43ce098fa",
        275094798,
    ),
    (
        "data/train-00022-of-00055-4ddf453149c076ce.parquet",
        "6579e9e8924d43449372e45a0b85777a6dbe3f33d3822afea7b0d58b6dcec648",
        615388537,
    ),
    (
        "data/train-00023-of-00055-b2e5cb8776a805b5.parquet",
        "609cd98183eec89e771d533dd133c2eb71f7f1934be959c93995d4265eefc224",
        415934396,
    ),
    (
        "data/train-00024-of-00055-ad3f493bf7764ab3.parquet",
        "0e53e23c0406656de3c00a27e592e56118cd211d15fb5a5b578af73070a706d3",
        283353292,
    ),
    (
        "data/train-00025-of-00055-b721a9f59789e977.parquet",
        "3e3b8743aa6f28901017b26712beb536a7887f51ec1e1d0b80e46a3c990d52b9",
        828519911,
    ),
    (
        "data/train-00026-of-00055-190bfc2cc1e829f3.parquet",
        "4d898e2cf6f5f86adeda830beee9de1f8e7c979639657a7fdd5169a30a9178fe",
        685597315,
    ),
    (
        "data/train-00027-of-00055-dc7cd71b785bd2ed.parquet",
        "e4de4c818d919646d86eb0f9fdc21f78c45433a9a5a7f82c20a3320bc56f16b9",
        218896081,
    ),
    (
        "data/train-00028-of-00055-60a917c5fc2d38e0.parquet",
        "b577c6402fa388b7e14b690be18a308caf745ff59d54e6286ffc00d1d2ca7334",
        348470531,
    ),
    (
        "data/train-00029-of-00055-7c4f50319a264c89.parquet",
        "792f141bb65cb764c613d5dc08388bc1e73c2f78b8c82654a62f034efbf89f50",
        263663639,
    ),
    (
        "data/train-00030-of-00055-810e0cd9c61c6fbb.parquet",
        "f62ad8e53ef08d9702429b91910049e1935ecfc5b46450d14c0bce2d68e8b2b1",
        871393519,
    ),
    (
        "data/train-00031-of-00055-5ffe2308764ae5d3.parquet",
        "90ec2843861fc61af16f4969912a72696463509ae19a9a46a4a8c7fccc98f4b3",
        419450317,
    ),
    (
        "data/train-00032-of-00055-dfb2983161325b1c.parquet",
        "55bce43f718c85feea69cca89ec564272523fa58b4c201cf4fe27d2c35a8de1f",
        446458572,
    ),
    (
        "data/train-00033-of-00055-0b37c0541e607f33.parquet",
        "fe03e73bb608deb7598be4469d39067c4dfb3c7baf32ade147bcfb41331dda07",
        373607023,
    ),
    (
        "data/train-00034-of-00055-55ce00e952a71dd8.parquet",
        "314ab0ec2694afd84321758a7d6f5d40538dd58798c00b6f575d40d112a0768b",
        381122538,
    ),
    (
        "data/train-00035-of-00055-7a03c07504c3f194.parquet",
        "f2c7ec42e9414199ae942a719124466409869dc68f96cd9002c3ee134810d856",
        285406499,
    ),
    (
        "data/train-00036-of-00055-30bd9c6eb4d9c510.parquet",
        "3bd671e5e55b1b826d117e20dee449dac5fc10d302d99e014147393c69d3c861",
        293782219,
    ),
    (
        "data/train-00037-of-00055-b8f7c845715832bd.parquet",
        "b991d50cc3cb7ac5170765d56f477bb9b655a834a395aad57bdcdef67c41fc57",
        616652568,
    ),
    (
        "data/train-00038-of-00055-71f5873992b7c236.parquet",
        "80c9f7071891961738d1545f1107fc3a773e103f6a371c55b6fffdb73c899bfb",
        311347447,
    ),
    (
        "data/train-00039-of-00055-fabe2b6d1c3c2d1a.parquet",
        "757b06c18a0a1731749dadde0e9045adbbdbd6abe46d7464fbeb9ee40a5de7f0",
        380449012,
    ),
    (
        "data/train-00040-of-00055-e3e782eb20fc4bd3.parquet",
        "124859bd6200b9da38136fc1b6fdebf1e2af9c2a9b7cc3f49f51717c8fcc9bce",
        324997722,
    ),
    (
        "data/train-00041-of-00055-6e99b495f0d1dc11.parquet",
        "375fbb590698b391fe883ae3028bf26d16ef1bf717a5f2107aeedf596f35dbee",
        406724221,
    ),
    (
        "data/train-00042-of-00055-25037c31ff1acfa8.parquet",
        "db1d307dea0f56420d72a5aae2641ad53fdf0febd2061b6f37bbe579b84c52ba",
        308147128,
    ),
    (
        "data/train-00043-of-00055-145b1136142ecc61.parquet",
        "64e7ade360681984cb53d59c5910be1603a9fb9dcdacb9a4929c30e743ce5a5b",
        290491245,
    ),
    (
        "data/train-00044-of-00055-14d2a1661cf048f3.parquet",
        "779c76de899bc1c3c365455b35bc3c8b620582bb1109954f111ea759bf3cc89b",
        366086598,
    ),
    (
        "data/train-00045-of-00055-7c8765f951e064f5.parquet",
        "3986aaa79123a3e4b90e1c6d6e8eb0f2ffadca1bfe0fc8bcfaef21f16b150594",
        320580196,
    ),
    (
        "data/train-00046-of-00055-6246dd6e4827621e.parquet",
        "3e2c9815161c8b7c9d603260336daead23948cfec223379422e24635a468b878",
        228611781,
    ),
    (
        "data/train-00047-of-00055-389c3c9879f3cb85.parquet",
        "fba13b5fc6c4a095efdd1fea07348202a1cdc8df0b83b13f7574bef9496d6663",
        286658794,
    ),
    (
        "data/train-00048-of-00055-934c727bdaf491fc.parquet",
        "8083c9e6a13aa333a78815352569c20f7db84081f1665b432bde7522628a7b77",
        295929405,
    ),
    (
        "data/train-00049-of-00055-eb3fb0203bd7d52e.parquet",
        "a5461c3f4a718c45c3ec484feb1edba27984e861c8d50dee0fd5701b2495ae25",
        513587840,
    ),
    (
        "data/train-00050-of-00055-0702f42fd97d2047.parquet",
        "771c44fb3cd059e0fe3e516166f20a6896be7be2f590a8636bfa37318526c339",
        436682916,
    ),
    (
        "data/train-00051-of-00055-03e50e9c65eacf3f.parquet",
        "94a610014848b1c00526ec98160a780346ebe0615fd7a91247e83b834f4be0d6",
        453620667,
    ),
    (
        "data/train-00052-of-00055-7e2f40ade640801a.parquet",
        "5bae9efa14c033fc847bcc37490bd811fae6145018f4ad84ed11fa3be5599949",
        334726607,
    ),
    (
        "data/train-00053-of-00055-2076981dc156b6e2.parquet",
        "d910adfe23ef31406e4900e36985808ea3720b1f594dc5f39dac8bda18425177",
        364920502,
    ),
    (
        "data/train-00054-of-00055-64db201174f6184a.parquet",
        "a97d2150a011ed1d4e72d2011c4bc9bdfbc81a6f5b202375813e0a57c0ae0b36",
        472132266,
    ),
)

DEFAULT_OUTPUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e22-esb-shortform-alignment-400-v1"
    / "segment-table"
    / "segment-table-receipt.json"
)

DEV10_DEFAULT_OUTPUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-e22-dev-esb-prompt-ab-v1"
    / "segment-table"
    / "segment-table-receipt.json"
)

#: The two populations this pin serves. ``test`` is the sealed 2026-09-04 one and
#: its every value is UNCHANGED, so a rebuild with the default flags reproduces
#: the committed receipt byte for byte. ``dev10`` is the 2026-09-05 addition.
PROFILES: dict[str, dict[str, Any]] = {
    "test": {
        "split": "test",
        "calls": ESB_TEST_CALLS,
        "parquet": PARQUET_FILES,
        "relpath": EXTRACTED_RELPATH,
        "default_output": DEFAULT_OUTPUT,
        "filtered": False,
        "published_rows": LEADERBOARD_ROW_COUNT,
    },
    "dev10": {
        "split": "train",
        "calls": DEV10_CALLS,
        "parquet": TRAIN_PARQUET_FILES,
        "relpath": TRAIN_EXTRACTED_RELPATH,
        "default_output": DEV10_DEFAULT_OUTPUT,
        "filtered": True,
        "published_rows": TRAIN_ROW_COUNT_PUBLISHED,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract(data_root: Path, profile: Mapping[str, Any] | None = None) -> Path:
    """Re-run the column projection against the pinned revision.

    Heavy imports stay inside this function (repo convention): a plain
    receipt rebuild from an already-extracted table needs neither pyarrow nor
    the hub client, and must not require network.

    ``profile["filtered"]`` turns on per-batch ``source_id`` confinement: rows
    are read a record batch at a time and every row whose call is not in
    ``profile["calls"]`` is dropped BEFORE it can reach the accumulator. That is
    what keeps the 103 confirmatory calls of the train split out of this
    study's files, logs and receipts entirely.
    """

    import pyarrow.parquet as pq  # noqa: PLC0415
    from huggingface_hub import HfFileSystem  # noqa: PLC0415

    if profile is None:
        profile = PROFILES["test"]
    wanted = set(profile["calls"])
    filesystem = HfFileSystem()
    rows: list[dict[str, Any]] = []
    for entry in profile["parquet"]:
        relpath = entry[0]
        remote = f"datasets/{DATASET_REPO_ID}@{DATASET_REVISION}/{relpath}"
        with filesystem.open(remote, "rb") as handle:
            reader = pq.ParquetFile(handle)
            if not profile["filtered"]:
                rows.extend(reader.read(columns=list(COLUMNS)).to_pylist())
                continue
            for batch in reader.iter_batches(columns=list(COLUMNS)):
                for row in batch.to_pylist():
                    if str(row["source_id"]) in wanted:
                        rows.append(row)
    target = Path(data_root) / profile["relpath"]
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return target


def build(data_root: Path, profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if profile is None:
        profile = PROFILES["test"]
    calls = tuple(profile["calls"])
    root = Path(data_root)
    table_path = root / profile["relpath"]
    if not table_path.is_file():
        raise SystemExit(f"extracted segment table is missing: {table_path}")
    rows = [
        json.loads(line)
        for line in table_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit("extracted segment table is empty")
    for row in rows:
        if set(row) != set(COLUMNS):
            raise SystemExit(f"extracted row carries unexpected columns: {sorted(row)}")
    sources = sorted({str(row["source_id"]) for row in rows})
    if tuple(sources) != tuple(sorted(calls)):
        raise SystemExit(
            f"extracted table names {sources}, not the {len(calls)} calls this "
            f"profile pins {sorted(calls)}"
        )
    ids = [str(row["id"]) for row in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("extracted table carries duplicate segment ids")
    counts = Counter(str(row["source_id"]) for row in rows)
    spans = [float(row["end_ts"]) - float(row["start_ts"]) for row in rows]

    parquet: list[dict[str, Any]] = []
    for record in profile["parquet"]:
        relpath, lfs_oid, size = record[0], record[1], record[2]
        xet = record[3] if len(record) > 3 else None
        local = root / PARQUET_SUBDIR / Path(relpath).name
        entry: dict[str, Any] = {
            "path": relpath,
            "bytes": size,
            "sha256": lfs_oid,
            "sha256_source": "git-lfs oid at the pinned revision (the file's own SHA-256)",
            "xet_hash": xet,
            "locally_rehashed": False,
        }
        if local.is_file() and local.stat().st_size == size:
            measured = sha256_file(local)
            entry["locally_rehashed"] = True
            entry["local_sha256"] = measured
            entry["local_matches_lfs_oid"] = measured == lfs_oid
            entry["local_relpath"] = f"{PARQUET_SUBDIR}/{Path(relpath).name}"
            if measured != lfs_oid:
                raise SystemExit(
                    f"{relpath}: local SHA-256 {measured} disagrees with the published "
                    f"LFS oid {lfs_oid}"
                )
        parquet.append(entry)

    payload = table_path.read_bytes()
    document = {
        "schema": "saea-e22-esb-segment-table-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "what_this_is": (
            "A derived-split reference pinned by hash, NOT a new umbrella lock asset. "
            "It adds no entry to docs/datasets.lock.json, materializes no new audio, and "
            "is never resolved through data.lock or data.carriers. The only audio this "
            "study sends stays the locked earnings22-original MP3 bytes D1 already closed "
            "over; this table supplies the published segment BOUNDARIES those bytes are "
            "cut at, and the published reference SENTENCES they are scored against."
        ),
        "upstream": {
            "repo_id": DATASET_REPO_ID,
            "repo_type": "dataset",
            "revision": DATASET_REVISION,
            "split": str(profile["split"]),
            "url": f"https://huggingface.co/datasets/{DATASET_REPO_ID}/tree/{DATASET_REVISION}",
            "license_note": (
                "the split is a repartition of the Rev Earnings-22 corpus this study "
                "already licenses under its earnings22-original lock entry"
            ),
            "esb_test_calls": list(ESB_TEST_CALLS),
            "esb_validation_calls": list(ESB_VALIDATION_CALLS),
            "esb_validation_note": (
                "recorded for completeness only; the validation calls are NOT read by "
                "this study and stay confirmatory"
            ),
        },
        "parquet_files": parquet,
        "parquet_schema": list(PARQUET_SCHEMA),
        "extraction": {
            "method": (
                "pyarrow ParquetFile.read(columns=[...]) over huggingface_hub.HfFileSystem "
                "at the pinned revision -- a COLUMN PROJECTION, so the 'audio' column is "
                "never materialized"
            )
            if not profile["filtered"]
            else (
                "pyarrow ParquetFile.iter_batches(columns=[...]) over "
                "huggingface_hub.HfFileSystem at the pinned revision -- a COLUMN "
                "PROJECTION, so the 'audio' column is never materialized -- with a "
                "per-batch source_id filter applied BEFORE any row is retained, so only "
                "the pinned calls' rows ever reach a list, a file or this receipt"
            ),
            "columns": list(COLUMNS),
            "audio_column_materialized": False,
        },
        "extracted_table": {
            "relpath": profile["relpath"],
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "rows": len(rows),
            "format": "JSONL, one object per segment, sort_keys, LF, UTF-8",
            "location_basis": (
                "under the controlled data root, never in Git and never inside the locked "
                "carrier tree: the 'sentence' column is gold reference text"
            ),
        },
        "population": {
            "calls": len(sources),
            "segments": len(rows),
            "segments_per_call": dict(sorted(counts.items())),
            "segment_seconds_total": round(sum(spans), 6),
            "segment_seconds_longest": round(max(spans), 6),
            "segment_seconds_shortest": round(min(spans), 6),
            "segment_seconds_mean": round(sum(spans) / len(spans), 6),
            "segments_longer_than_20s": sum(1 for span in spans if span > 20.0),
            "segments_longer_than_30s": sum(1 for span in spans if span > 30.0),
        },
        "unresolved": {
            "row_count_discrepancy": (
                f"this table carries {len(rows)} test rows; the leaderboard config "
                f"hf-audio/open-asr-leaderboard reports {LEADERBOARD_ROW_COUNT} for the same "
                "Earnings22 column, and the NVIDIA NeMo AutoModel post that publishes the "
                f"9.79 target states N = {LEADERBOARD_ROW_COUNT}. The "
                f"{LEADERBOARD_ROW_COUNT - len(rows)}-row gap is UNEXPLAINED. It is recorded, "
                "not reconciled: no row is invented, dropped or re-cut to close it, and every "
                "number this study reports is over the 2,735 rows this pinned table actually "
                "contains."
            )
            if not profile["filtered"]
            else (
                f"none of this kind: this table is a SUBSET of the train split by "
                f"construction ({len(rows)} rows over {len(calls)} calls, filtered from a "
                f"split the upstream repository publishes as {profile['published_rows']} "
                "rows over 113 calls), so there is no published per-subset row count to "
                "disagree with. No leaderboard column is computed over these calls."
            ),
            "timestamp_precision": (
                "start_ts/end_ts are float32 in the upstream parquet, so a boundary carries "
                "about 1e-4 s of representation error at these magnitudes; the cut is made at "
                "the float32 value verbatim rather than at a re-rounded one"
            ),
        },
    }
    if profile["filtered"]:
        # Filtered profiles only, so an unfiltered rebuild still reproduces the
        # sealed 2026-09-04 receipt byte for byte.
        document["upstream"]["calls_pinned"] = list(calls)
        document["extraction"]["source_id_filtered_at_extraction"] = True
        document["extraction"]["source_id_filter_basis"] = (
            "the ESB train split carries 113 source calls, 103 of which are in this "
            "study's earnings22-original confirmatory split. Filtering inside the batch "
            "loop is what keeps every one of them out of this study's files, logs and "
            "receipts: no confirmatory sentence, boundary or per-call count is written "
            "down, printed or counted anywhere"
        )
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="test",
        help=(
            "which pinned population to receipt: 'test' is the sealed 2026-09-04 six-call "
            "ESB test subset (default, unchanged), 'dev10' the ESB train rows of this "
            "study's own Earnings-22 dev subset10"
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--extract",
        action="store_true",
        help=(
            "re-run the column-projected read against the pinned revision and rewrite "
            "the extracted JSONL before receipting it (requires network)"
        ),
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    profile = PROFILES[args.profile]
    output = args.output if args.output is not None else profile["default_output"]
    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    if args.extract:
        extract(root, profile)
    document = build(root, profile)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "rows": document["extracted_table"]["rows"],
                "extracted_sha256": document["extracted_table"]["sha256"],
                "segments_per_call": document["population"]["segments_per_call"],
                "segment_seconds_total": document["population"]["segment_seconds_total"],
                "parquet_locally_rehashed": [
                    entry["path"] for entry in document["parquet_files"] if entry["locally_rehashed"]
                ],
                "profile": args.profile,
                "output": str(output),
                "output_sha256": (
                    sha256_file(output)
                    if args.write
                    else hashlib.sha256(text.encode("utf-8")).hexdigest()
                ),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
