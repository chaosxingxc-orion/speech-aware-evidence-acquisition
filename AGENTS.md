# CLAUDE.md — audio-aware-evidence-acquisition

独立研究仓：冻结 speech/omni 核上的音频感知证据获取。研究对象=为 API-only 冻结核构建外置
reward-guided 控制面，以系统级 in-context 控制构造/选择/更新知识、记忆、技能与证据状态，在不改
参数与内部权重的前提下跨 run 稳定提升任务能力。音频特有机制：误听实体会产生相关但错误的证据，
故需在音频重解析（OBS）与外部搜索（SUPPLY）之间做受控选择。

## 研究边界（不可变，源自执行合同）

- 冻结 Qwen3-Omni 核经 API 形态服务边界访问；零模型参数训练；无任务训练模型；无第二答题 LLM。
- 控制器非模型：外置无梯度有限决策常量，dev 标定、test 冻结。
- gold 答案/参考转写/测试标注/未来轮不得越过运行时边界。
- OBS 重解析与外部证据供给分开可追踪；一切外部响应/工具动作/模型请求版本化可哈希。
- discovery 与 confirmatory 载体不相交；confirmatory 判据读结果前冻结。
- 冻结工具级检索器/judge 仅在 pin 且入日志时允许；最终答案权在冻结核。

## 授权与序列

执行合同与冻结字段：伞仓
`wiki/experiments/audio-aware-evidence-acquisition/2026-08-03-owner-go-and-execution-contract.md`；
入场序列（E0 无模型数据闭环 → R0 工程纵向链 → R1 closest-prior 复现 → X 方向性探索）：伞仓
`docs/superpowers/specs/2026-08-02-audio-aware-evidence-acquisition-stage2a-entry.md`。
**首次模型触达前必须先关 E0（D1–D4）并落 runtime 收据**（llama.cpp build commit + GGUF 逐文件
sha256）。每次模型/工具触达记 `docs/exposure-ledger.md`。

## 路由（伞仓=治理与实验控制面）

- 当前研究状态：伞仓 `wiki/Research-Objective.md`；实验台账：伞仓
  `wiki/experiments/audio-aware-evidence-acquisition/README.md`（每条实验须能解析 study commit、
  config/protocol hash、model/dataset revision、MLflow run、artifact 位置与 hash、结论）。
- 数据身份唯一 live source：伞仓 `docs/datasets.lock.json`（按键引用：`earnings21-original`、
  `earnings22-original`、`conec`、`qwen3-omni-30b-a3b-instruct-gguf`；不复制 hash）。字节在
  `SPEECHRL_DATA_DIR`，永不入 Git。D0 收据：伞仓
  `docs/checks/audio-aware-evidence-acquisition/2026-08-02-acquisition/`。
- 代码采纳：W1–W4 代码进本仓必须走 `docs/migration-manifest.md` copy-and-verify 登记。

## 环境

- 计算在 WSL2 `Ubuntu-24.04`（默认 `Ubuntu` 是 WSL1 无 GPU）；Python 3.12 在
  `~/.venvs/speechrl`。安装：`uv pip install -e ".[dev]"`（本仓目前不依赖 `speechrl_common`；
  若将来消费，走 `docs/migration-manifest.md` 的精确 commit pin 政策，`../../common` 仅限本地开发覆盖）。
- 推理：llama.cpp llama-server 常驻（GGUF `-ngl 28`，30B 于 24 GB）。
- 测试：`pytest`；复现入口：`bash scripts/reproduce.sh`（R0 交付后生效）。

## 禁止

- 越过执行合同预算带（首切片 ≤3000 次冻结核调用 / ≤40 GPU 时 / ≤20 h 音频 / 付费 API=0）；
- 向本仓提交数据/权重/音频/原始 trace；绕过 migration-manifest 搬运代码；
- 把 R2 等候选编号写进包名、MLflow 命名空间或正式实验 ID（provenance 引用除外）；
- push 之外的发布（wiki 镜像、公开 release）需 owner 授权。
