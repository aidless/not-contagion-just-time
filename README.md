# Not Contagion, Just Time — Experiment Scripts
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  [![Data](https://img.shields.io/badge/data-CC--BY--4.0-lightgrey.svg)](LICENSE)

Companion code for: *Not Contagion, Just Time: Temporal Calibration Fatigue in LLM Agents*

## Setup

Set your API keys as environment variables:

```bash
export DMXAPI_KEY="sk-..."        # GPT-4o via DMXAPI
export DEEPSEEK_API_KEY="sk-..."  # DeepSeek V4
```

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `pilot_cc_v3.py` | Pilot experiment (v3) | `python pilot_cc_v3.py --model gpt-4o --reps 10` |
| `cc_full_experiment.py` | Main C1-C4 experiment | `python cc_full_experiment.py --phase 1 --reps 30` |
| `cc_ablations.py` | Ablation A1+A2 | `python cc_ablations.py --reps 20` |
| `cc_revision_experiments.py` | DeepSeek cross-model | `python cc_revision_experiments.py --model deepseek-v4-pro --reps 30` |
| `cc_t1_nosync.py` | T1 isolation baselines C1b+C3b | `python cc_t1_nosync.py --model gpt-4o --reps 30` |
| `cc_analysis_figures.py` | Figure generation | `python cc_analysis_figures.py cc_full_phase1_30reps.json` |

## Data

Checkpoint JSON files and result JSON files available upon request.
Total: 100,500 API calls across GPT-4o, DeepSeek V4 Pro, DeepSeek V4 Flash.

## Reproducibility notes

- **Environment**: CI runs on Python 3.12 (`.github/workflows/ci.yml`); install
  dependencies with `pip install -r requirements.txt`
  (numpy / scipy / matplotlib / pytest).
- **No PRNG seeding**: the experiment state is driven by live LLM API responses
  (scripts send a per-call `temperature`), so re-runs are not bit-identical.
  "Seeded miscalibration" in the code refers to planting an overconfident agent
  persona in the group, not a random seed.
- **Checkpoints**: `cc_full_experiment.py` writes `cc_full_ckpt_{cid}.json`
  after every repetition and resumes from it on restart; the final aggregate
  (e.g. `cc_full_phase1_30reps.json`) is the input to `cc_analysis_figures.py`.

### 复现结构（可从代码复算的真实数字）

| 数字 | 复算来源 | 值 |
|---|---|---|
| 实验脚本数 | `git ls-files "*.py"` | 7 |
| GSM8K 题库 | `cc_full_experiment.py:28-64` | 30 题 |
| 每 agent 每轮题数 | `cc_full_experiment.py:27` | N_Q = 5 |
| 条件数 | `cc_full_experiment.py:87-91` | C1-C4（4） |
| C1 配置 | `:88` | 3 agent / 10 round / 无 sync / 无 seed |
| C2-C4 配置 | `:89-91` | 3/20、5/10、5/20，均 SYNC+seed |

这是**设计结构**（可复算），不是性能/准确度数字——那些（ECE、100,500 API calls）不在本仓。

### Fail-closed 声明（真实机制）

- **Rate-limit 即中止**：403 且 `calls > 500` 时**保存并中止**（`RuntimeError("RATE_LIMIT")`，`cc_full_experiment.py:243-245`），打印"clean reps saved"后退出——**不静默填假数据**。
- **Checkpoint 断点续跑**：每 rep 写 `cc_full_ckpt_{cid}.json`，`start_rep = len(all_ece)` 从断点续跑（`cc_full_experiment.py:183-199`），`--resume` 幂等。
- **Fig 3 不冒充实测**：`cc_analysis_figures.py:164-167` 明示 reliability 曲线是 **schematic**（示意图），非真实数据。

## Data availability

This repository contains **scripts only**. No result JSONs, checkpoint files,
or figures are committed — the experiment outputs live in the author's working
environment (environment-bound) and are available from the author on request.
All figures can be regenerated from those JSONs via
`python cc_analysis_figures.py <result>.json` after re-running the scripts
with the API keys above.

## What this does and does not prove

**Proves:** the experiment harness is runnable — each script takes `--reps` /
`--phase`, writes a checkpoint after every repetition (`cc_full_ckpt_{cid}.json`),
and resumes from it on restart (`--resume`). The figure generator
(`cc_analysis_figures.py`) consumes the final aggregate JSON and produces the
reported plots.

**Does not prove:** the headline numbers themselves. The "100,500 API calls"
total and every ECE / calibration figure in the companion paper are **not
recomputable from this repository** — the result JSONs, checkpoints, and figures
are environment-bound and not committed. Re-running the scripts here yields
*new* data (the LLM answers differ on every call because the state is driven by
live API responses, not a PRNG seed). This repo is the **reproduction harness**,
not the evidence archive.

**Why the number can't be derived from code:** the per-call counts depend on
runtime question sets, retry/rate-limit handling, and model answers, none of
which are committed. The honest statement is: the harness is here, the data is
not.

## License

Code is MIT-licensed ([LICENSE](LICENSE)). Not Contagion, Just Time releases the experiment scripts, results, and figures under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

GitHub's license detector reports this repository as `NOASSERTION` because it reads
a single SPDX id per repository and this one carries two. The split is deliberate:
the code stays permissively licensed so it can be reused, and the research material
stays attributable so a citation is required.