# PREREG — Not Contagion, Just Time 预注册与评测规格

> 本文件是 not-contagion-just-time 的**预注册规格**（registered-report 风格）：声明本仓库**实际存在、可从落盘证据复算**的实验结构假设、评测方案、成功标准与明确边界。
> **诚实约束**：本仓是**复现 harness，不是证据档案**。所有数字要么来自代码结构（可复算），要么明确标注为「不在本仓、不可复算」——**绝不虚构 ECE 数字或 100,500 API calls**。

---

## 0. 一句话假设（先读这行）

> 本仓是「Not Contagion, Just Time: Temporal Calibration Fatigue in LLM Agents」的**复现脚本**：7 个可运行脚本实现 C1-C4 条件（30 GSM8K 题 × 5 q/agent/round，C1 隔离基线、C2-C4 加 BOUNDARY_SYNC + 一个过度自信种子代理），每 rep 写 checkpoint 可断点续跑；**本仓不包含结果数据**——ECE/校准图/100,500 API calls 全部环境绑定、不可复算。

---

## 1. 主假设 H1（实验设计结构）

- **假设**：C1-C4 四条件结构为 C1（3 agent/10 round/无 sync/无 seed）、C2（3/20/sync+seed）、C3（5/10/sync+seed）、C4（5/20/sync+seed）；GSM8K 题库 30 题；每 agent 每轮 5 题（N_Q=5）。
- **可证伪方向**：若 `CONDITIONS` 配置或 GSM8K 题数偏离，则 H1 不成立。
- **评测方案**：读 `cc_full_experiment.py:87-91`（CONDITIONS）+ `:28-64`（GSM8K）+ `:27`（N_Q）。
- **成功标准**：4 条件、30 题、N_Q=5（代码可复算）。

## 2. 假设 H2（checkpoint 断点续跑）

- **假设**：每 rep 结束写 `cc_full_ckpt_{cid}.json`，重启从上次 rep 续跑（`--resume`）。
- **可证伪方向**：若 checkpoint 不写或 `start_rep` 不从 `len(all_ece)` 恢复，则 H2 不成立。
- **评测方案**：`cc_full_experiment.py:183-199`（读 ckpt + resume）。
- **成功标准**：`start_rep = len(all_ece)`；断点续跑可复现。

## 3. 假设 H3（rate-limit 失败即中止，非假数据）

- **假设**：403 且 calls>500 时**保存并中止**（`RuntimeError("RATE_LIMIT")`），不产出伪造的补齐数据。
- **可证伪方向**：若 rate-limit 时静默填假数据继续，则 H3 不成立。
- **评测方案**：`cc_full_experiment.py:243-245, 277-278`（rate-limit → save + abort + "clean reps saved"）。
- **成功标准**：rate-limit 时保存干净 rep 并中止，不伪造。

## 4. 假设 H4（Fig 3 是示意图，非实证）

- **假设**：`cc_analysis_figures.py` 的 Fig 3 reliability 曲线是**示意图**（`# Simulated reliability curves (schematic)`），不是真实数据绘制。
- **可证伪方向**：若 Fig 3 标注为真实数据，则 H4 不成立。
- **评测方案**：`cc_analysis_figures.py:164-167`（schematic 注释）。
- **成功标准**：Fig 3 明示 schematic，不冒充实测。

---

## 5. 明确边界（不证明什么）

| 维度 | 不证明 | 原因 |
|---|---|---|
| 100,500 API calls | 总数不可复算 | 结果/checkpoint/图均未提交，环境绑定 |
| ECE / 校准图数字 | 论文标题数字不可复算 | 输入 JSON 不在本仓 |
| Fig 3 reliability | 非真实可靠性曲线 | 代码明示 schematic |
| 复现数据 | 重跑得**新**数据 | LLM 状态由实时响应驱动，非 PRNG 种子 |
| 因果结论 | 校准疲劳的因果机制 | 无结果数据支撑 |

---

## 6. 结论纪律

- 本仓**不包含**结果 JSON / checkpoint / 图——`git ls-files` 26 个文件全为代码与文档。
- 重跑本仓脚本产生**新**数据（非位相同），因此本仓是 harness 而非证据档案。
- 任何从本仓引用的「100,500 API calls」或 ECE 数字都是**未在本仓的声明**，需作者提供结果 JSON 方可复核。
- 本 PREREG 是规格声明，不新增实验，不改变已冻结脚本。
