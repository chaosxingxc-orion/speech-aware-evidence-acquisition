# CLAUDE.md — speech-aware-evidence-acquisition

独立研究仓：冻结 speech-capable omni 核上的语音感知证据获取。研究对象是在 API-only 冻结核之外
构建 reward-guided 控制面，分开控制语音观察（OBS）、知识组织（ORG）、证据供给（SUPPLY）与证据
使用（USE），在不改参数与内部结构的前提下稳定提升 speech-domain 任务能力。

## 研究边界（不可变）

- 只研究人类言语及其语言内容：ASR、实体、contextual biasing、spoken QA、会议语音理解。
- WAV/MP3 是 speech signal 的载体；general/environmental audio 任务不在范围内。FSD50K、
  AudioSet、ESC-50 不得由本仓 loader、测试或配置消费。
- 冻结 Qwen3-Omni 核经 API 形态服务边界访问；零参数训练；无 task-trained model；无第二答题 LLM。
- gold/参考转写/test annotation/future turn 不得进入 runtime；discovery 与 confirmatory 隔离。
- OBS/ORG/SUPPLY/USE 分开 trace；外部响应、工具动作、模型请求和派生物均版本化可哈希。
- 冻结工具级 retriever/judge 仅在 pin 且入日志时允许；最终答案权在冻结核。

## 授权与序列

本仓是 **Stage‑2 study 载体**（伞仓 Decision-Log 续91/续92）：终点是一个或多个合格 paper
candidate，不是完成论文。当前唯一自包含有效合同：伞仓
`wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-consolidated-execution-contract.md`；
入场序列：伞仓
`docs/superpowers/specs/2026-08-02-speech-aware-evidence-acquisition-stage2a-entry.md`。
执行 profile 只接受 `model-free-check` / `baseline-reproduction` / `bounded-discovery-probe`
（`contracts.assert_execution_scope`，fail-closed）。
首次模型触达前必须关闭 E0 D1–D4，并落 llama.cpp build commit + GGUF 逐文件 SHA-256 runtime
receipt。每次模型/工具触达在读结果前记 `docs/exposure-ledger.md`。

## 路由

- 当前状态：伞仓 `wiki/Research-Objective.md`；实验台账：
  `wiki/experiments/speech-aware-evidence-acquisition/README.md`。
- 数据身份唯一 live source：伞仓 `docs/datasets.lock.json`。核心键为
  `earnings21-original`、`earnings22-original`、`conec`、
  `qwen3-omni-30b-a3b-instruct-gguf`；不复制 revision/hash。
- 大字节在 `SPEECHRL_DATA_DIR`，永不入 Git。D0 收据：
  `docs/checks/speech-aware-evidence-acquisition/2026-08-02-acquisition/`。
- W1–W4 代码进入本仓必须走 `docs/migration-manifest.md` copy-and-verify 登记。

## 环境与检查

- WSL2 `Ubuntu-24.04`；Python 3.12 `~/.venvs/speechrl`。
- 安装：`uv pip install -e ".[dev]"`；测试：`pytest`。
- 推理：llama.cpp llama-server；复现入口：`bash scripts/reproduce.sh`（R0 后生效）。
- 本仓当前不依赖 `speechrl_common`；首次消费必须按 migration manifest 精确 pin。

## 禁止

- **paper-scale 工作**：`paper-scale-confirmatory` profile、production-scale 方法实现、大规模
  confirmatory campaign、最终优越性/泛化结论、manuscript/submission/publication——这些属
  Stage‑3，须经 `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` 晋级到 `papers/<slug>` 独立仓，本仓
  永不接受（机器强制：`contracts.assert_execution_scope`）；
- 越过首切片预算（≤3000 冻结核调用 / ≤40 GPU-hours / ≤20 小时 speech audio / 付费 API=0）；
- 提交数据、权重、speech files 或 raw trace；绕过 migration manifest 搬运代码；
- 把 R2 等候选编号写进包名、MLflow namespace 或正式 experiment ID；
- 未经 owner 授权发布 Wiki 镜像或 public release。
