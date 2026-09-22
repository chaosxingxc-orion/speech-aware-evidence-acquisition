#!/bin/bash
# GPU preflight (NOT a model contact): a short fp16 matmul burst that forces the card out of its idle P-state and reports the
# achieved throughput as "<x> TFLOP/s"; the batch driver refuses a launch below 30 TFLOP/s (the WSL P-state / power-cap trap,
# memory gpu-pstate-stuck-wsl). Uses the shared venv's torch; touches no model, server or data.
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import time, torch
assert torch.cuda.is_available(), "no CUDA device"
dev = torch.device("cuda:0")
a = torch.randn(4096, 4096, device=dev, dtype=torch.float16); b = torch.randn(4096, 4096, device=dev, dtype=torch.float16)
for _ in range(5): (a @ b); torch.cuda.synchronize()
best = 0.0
for _ in range(3):
    torch.cuda.synchronize(); t0 = time.perf_counter()
    for _ in range(20): c = a @ b
    torch.cuda.synchronize(); dt = time.perf_counter() - t0
    best = max(best, 20 * 2 * 4096 ** 3 / dt / 1e12)
print(f"gpu ramp: {best:.1f} TFLOP/s ({torch.cuda.get_device_name(0)})")
PY
