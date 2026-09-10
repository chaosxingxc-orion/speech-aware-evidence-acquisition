# E21 DR GPU budget accounting correction

Root corrects a live accounting error before any cap-triggered intervention or
current quality-result read. The registered parent budget remains1.2 GPU hours.

The repository does not use elapsed wall time for the sampled gpu_seconds field.
core.resources.ResourceSampler._record accumulates elapsed multiplied by bounded
GPU utilization divided by100. The frozen inference checkout and the reviewed
analysis checkout carry byte-identical resources.py. The inherited DR plan
describes its1.2-hour allowance relative to KC-E1f's measured sampler value.

The prior wall-time projection and proposed2-hour amendment conflated that
utilization integral with elapsed runtime. The conservative15:05:20UTC wall
deadline is therefore superseded. It is not a valid trigger for stopping this
flight. Preserve the original plan, exposure cap, source roster, attempts, service
identity and decoding settings. No added generation is admitted by this correction.

The live external monitor can apply the same integration formula over its
registered10-second samples. At the correction snapshot, the unit parent had752
durably charged generation calls,3921.616 wall seconds, and1935.800 utilization-
weighted GPU seconds (0.53772 GPU hours). The full1593-window projection was
1.13908 GPU hours, below1.2. This supports continuing the original authorized run;
it is not a guarantee about its eventual cost.

The immutable external correction receipt is
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/e21-dr-packets-unit-budget-accounting-correction-v1.json.
It binds the exact monitor prefix length/hash, resource implementation hash,
integration window and actual charged-contact snapshot. Its window starts at
worker launch and conservatively includes CPU preparation.

Report wall time, service residence, utilization-integrated time, model loading,
preparation waiting and generation separately. The external monitor is a sampled
measurement with a different interval from the historical inline sampler; do not
call it exact kernel execution time or invent an inline sampler reading. Bind the
complete monitor interval after seal. Reassess the actual integral as the run
progresses; if it approaches the original1.2 cap before completion, stop admitting
new contacts and obtain a decision based on the measured quantity.

The owner was informed that the earlier amendment question is superseded and no
additional budget approval is currently required. Future cost or permission
decisions must cite both quantities and the measurement source.
