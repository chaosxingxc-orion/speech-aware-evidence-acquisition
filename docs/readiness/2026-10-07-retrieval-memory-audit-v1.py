"""Synthetic cache identity/lifetime proof; no dataset or model access."""
import gc
import json
from speech_aware_evidence_acquisition.rails import kb_policy as kb

N, WIDTH = 256, 64

def vectors():
    return tuple(tuple(float((i + j) % 17 + 1) for j in range(WIDTH)) for i in range(N))

cache = kb._KeyMatrixCache(capacity=4)
first = vectors()
first_entry = cache.get_or_build(first)
reused = cache.get_or_build(first)
assert reused is first_entry and len(cache) == 1
proof = []
for load in range(1, 6):
    same_bytes = vectors()
    assert same_bytes == first and all(a is not b for a,b in zip(same_bytes, first))
    entry = cache.get_or_build(same_bytes)
    assert entry is not first_entry
    assert entry.norm_values == first_entry.norm_values
    assert entry.matrix.tobytes() == first_entry.matrix.tobytes()
    proof.append({"fresh_parse": load, "cache_entries": len(cache),
                  "matrix_bytes_resident": sum(x.matrix.nbytes for x in cache._entries),
                  "first_entry_still_cached": any(x is first_entry for x in cache._entries)})
assert proof[2]["cache_entries"] == 4 and proof[3]["first_entry_still_cached"] is False
first = None
first_entry = None
reused = None
same_bytes = None
entry = None
gc.collect()
retained = sum(len(x.vectors) for x in cache._entries)
assert retained == 4 * N
result = {"schema":"saea-synthetic-key-matrix-retention-audit-v1",
          "rows":N,"width":WIDTH,"same_object_reuses_one_entry":True,
          "equal_content_fresh_tuples_allocate_new_entry":True,
          "matrix_and_exact_norm_bytes_unchanged":True,
          "cached_vector_rows_after_external_reference_drop":retained,
          "observations":proof,
          "active_11514x2048_matrix_bytes_formula":11514*2048*8,
          "active_tuple_payload_bytes_formula_64bit_cpython":11514*2048*(24+8),
          "formula_excludes_row_tuple_headers_dicts_and_input_json":True}
print(json.dumps(result,indent=2,sort_keys=True))
