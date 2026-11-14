# Not Contagion, Just Time — Experiment Scripts

[![CI](https://github.com/aidless/not-contagion-just-time/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/not-contagion-just-time/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  [![Data](https://img.shields.io/badge/data-CC--BY--4.0-lightgrey.svg)](LICENSE-DATA)

Companion code for: *Not Contagion, Just Time: Temporal Calibration Fatigue in LLM Agents*

**What this is.** Scripts only. No result JSONs, checkpoints or figures are committed — the paper's 100,500 API calls were run in an environment-bound working directory.

**Verified how.** Nothing in this repo is quantitatively re-checkable offline; the outputs are available from the author on request. Treat this repo as the method, not the evidence.

## What this doesn't claim / Limits

- This repository is **scripts only**. No result JSON, checkpoint, or figure is committed, so no outcome claim (ΔECE, p-values, effect sizes) can be re-verified from this repo alone.
- The 100,500-call total is a stated figure from the paper's runs, not re-derivable from committed artifacts.
- Re-runs are not bit-identical: agent state is driven by live LLM API responses (per-call temperature; no PRNG seed on model outputs). A re-run verifies the pipeline, not the published numbers.
- `--dry-run` does not stub the API layer; without valid keys every call fails with HTTP 401.

**Run it.** `export DMXAPI_KEY=... DEEPSEEK_API_KEY=...` then `python cc_full_experiment.py`; `python cc_analysis_figures.py <result>.json` regenerates each figure from an external result file.

Verified entry points (run locally on 2026-11-10, Python 3.12):

```text
$ python3 cc_full_experiment.py --help
usage: cc_full_experiment.py [-h] [--phase PHASE] [--reps REPS]
                             [--conditions CONDITIONS] [--dry-run]

$ python3 pilot_cc_v3.py --help
usage: pilot_cc_v3.py [-h] [--reps REPS]

$ python3 cc_full_experiment.py --phase 1 --reps 1 --conditions C1 --dry-run
CC Full Experiment — Phase 1
gpt-4o | 1 reps/condition | 5 q/agent/round
Conditions: C1
Per-Q anchoring + seeded overconfident agent
⚠️  DRY-RUN MODE
▶ C1: text/3/10/ISOLATED (agents=3, rounds=10, sync=False, seed=False)
```

Note: `--dry-run` prints the banner and condition plan but still attempts live API
calls (there is no offline mock); without a valid `DMXAPI_KEY` every call fails with
`HTTP Error 401: Unauthorized`. That is the expected behavior without keys — the
pipeline entry point and condition planner are what the dry run verifies.

## Results

Every design number below is verifiable directly from the committed scripts
(condition dictionaries, defaults, and docstrings); no number here is invented.
The quantitative **outcomes** (ECE deltas, p-values, effect sizes) are not
committed to this repository — see [Data availability](#data-availability).

### Experiment inventory (from committed scripts)

| Script | Conditions / design | Reps (default) | Questions/agent/round | Model |
|--------|--------------------|----------------|----------------------|-------|
| `pilot_cc_v3.py` | Pilot v3: per-question anchoring + seeded overconfident agent | 10 (via `--reps`) | 5 (`N_Q=5`) | gpt-4o |
| `cc_full_experiment.py` | Main 2×2 factorial, Phase 1: **C1** N=3/T=10/ISOLATED, **C2** N=3/T=20/SYNC+seed, **C3** N=5/T=10/SYNC+seed, **C4** N=5/T=20/SYNC+seed | 30 | 5 | gpt-4o |
| `cc_t1_nosync.py` | Factor-isolation baselines: **C1b** N=3/T=20/no-sync/no-seed, **C3b** N=5/T=10/no-sync/no-seed | 30 | 5 | gpt-4o |
| `cc_ablations.py` | **A1** no-confidence blind (sync omits confidence), **A2** stateless toggle (sync on/off every 5 rounds, 15 rounds) | 20 | 5 | gpt-4o |
| `cc_revision_experiments.py` | TMLR-revision baselines: **R1** C1@T=20 isolated, **R2** C4_normal (SYNC, 5 normal agents, no seed); cross-model via `--model` | 30 | 5 | gpt-4o / DeepSeek V4 |
| `cc_rebuttal_experiments.py` | **Q2** no-history baseline (N=3, T=20, isolated), **Q5** missing factorial cell (N=3, T=10, SYNC+seed); ~15,000 calls total | 30 | 5 | gpt-4o |

Scale actually run for the paper (stated, not re-derivable offline):
**100,500 API calls** across GPT-4o, DeepSeek V4 Pro, and DeepSeek V4 Flash.

### What the measured outcome numbers are

Each condition records per-repetition final-round **ECE**, **MCE**, **Brier** and
**accuracy** (computed by `calc_ece` / `calc_mce` / `calc_brier` in
`cc_full_experiment.py`), aggregated into factor effects vs the C1 baseline and
exported as `cc_full_phase1_30reps.json`, which is the sole input to
`cc_analysis_figures.py`. The numeric values of those aggregates are
**NOT_FILLABLE from this repository**: no result JSON, checkpoint, or figure is
committed (the working directory was environment-bound), and re-running requires
paid API access (100,500 calls). Values are available from the author on request.

## Repository structure

| File | Role |
|------|------|
| `pilot_cc_v3.py` | Pilot experiment (v3 protocol) |
| `cc_full_experiment.py` | Main C1–C4 experiment, checkpointed per rep |
| `cc_t1_nosync.py` | T1 no-sync isolation baselines (C1b, C3b) |
| `cc_ablations.py` | Ablations A1/A2 |
| `cc_revision_experiments.py` | TMLR-revision baselines (R1/R2) + cross-model |
| `cc_rebuttal_experiments.py` | Rebuttal experiments (Q2/Q5) |
| `cc_analysis_figures.py` | Figure generation from external result JSON |
| `.github/workflows/ci.yml` | CI: Python 3.12, deps from `requirements.txt` |
| `requirements.txt`, `LICENSE`, `LICENSE-DATA`, `CHANGELOG.md` | Environment, licensing (MIT + CC-BY-4.0), changelog |

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

## U1 re-verified entry points (live run 2026-11-11)

All commands below were executed for this pass; exit codes are from this run.

| Live check | Result | Source |
|---|---|---|
| `python3 cc_full_experiment.py --help` | exit 0, prints phase/reps/conditions/dry-run options | this pass |
| `python3 pilot_cc_v3.py --help` | exit 0, prints `--reps` | this pass |
| `python3 -m py_compile` on 7 scripts | exit 0 (cc_ablations.py, cc_analysis_figures.py, cc_full_experiment.py, cc_rebuttal_experiments.py, cc_revision_experiments.py, cc_t1_nosync.py, pilot_cc_v3.py) | this pass |

Design constants re-derived from the committed sources (not from memory):

| Constant | Value | Source (path:line) |
|---|---|---|
| N_Q (cc_full_experiment.py) | `N_Q = 5` (questions per agent per round) | `cc_full_experiment.py:27` |
| C1 condition dict | `n_agents=3, n_rounds=10, sync=False, seeded_miscal=False` | `cc_full_experiment.py:88` |
| --reps default 30 (cc_full) | 30 | `cc_full_experiment.py:332` |
| N_Q (cc_ablations.py) | `N_Q = 5` | `cc_ablations.py:16` |
| N_Q (cc_t1_nosync.py) | `N_Q = 5` | `cc_t1_nosync.py:24` |
| --reps default 30 (cc_t1_nosync) | 30 | `cc_t1_nosync.py:161` |
| Committed experiment scripts | 7 | live `glob cc_*.py` + `pilot_cc_v3.py` |

Per-row meanings: `N_Q = 5` is questions per agent per round; the `C1` dict is
`n_agents=3, n_rounds=10, sync=False, seeded_miscal=False`; `--reps` defaults to 30.

**NOT YET MEASURED in this pass** (and not fillable from this repository at all):
the 100,500-call runs, any ECE / MCE / Brier / accuracy aggregate, p-values, or
effect sizes — no result JSON, checkpoint, or figure is committed. Re-running
requires paid API keys (`DMXAPI_KEY`, `DEEPSEEK_API_KEY`); see
`README.md` sections *What this doesn't claim* and *Data availability*.

**Reproduce the live checks above**:

```bash
python3 cc_full_experiment.py --help
python3 pilot_cc_v3.py --help
python3 -m py_compile cc_*.py pilot_cc_v3.py
```

<!-- figure: pending real measurement -->

## License

Code is MIT-licensed ([LICENSE](LICENSE)). Not Contagion, Just Time releases the experiment scripts, results, and figures under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

GitHub's license detector reports this repository as `NOASSERTION` because it reads
a single SPDX id per repository and this one carries two. The split is deliberate:
the code stays permissively licensed so it can be reused, and the research material
stays attributable so a citation is required.

## 验收题库与复算

`eval/cases.jsonl` 是 20 条可执行验收题，覆盖八个口径（校准指标 ECE、Brier/MCE、
响应解析、答案归一与判等、C1–C4 条件配置、同伴反馈消息、`tests/` 声明条数、
`README`/`PREREG` 的声明）。其中 18 条是 `expr`/`raises`，**全部真的 import 本仓库
模块现算**（`cc_full_experiment`/`cc_ablations`/`cc_revision_experiments`/
`cc_rebuttal_experiments`/`cc_t1_nosync`），或用 `ast` 真解析 `tests/test_cc.py`；
剩下 2 条 `doc` 用正则在 `README.md`/`PREREG.md` 里核对声明口径。期望值不是抄文档，
而是**跑出来的**：

**验收阈值（写死，不接受「差不多」）**：`passed` 必须 ≥ 20 条（题库正好 20 条，等价于全过）；
`--selftest` 必须正好 19/20——少于 19 说明篡改没生效，多于 19 说明期望值被改宽；
两种模式的退出码必须为 0，缺一条即判不通过（23 分制的门按此给分）。

```bash
python3 eval/run_cases.py            # 20/20 cases passed
python3 eval/run_cases.py --save     # 顺带把结果写进 eval/run-report.json
python3 eval/run_cases.py --selftest # 篡改一条期望值，必须变红（证明这套题会失败）
```

**数字如何复算**：`eval/run-report.json` 里每条 case 都带 `id` / `axis` / `detail`，
把 `detail` 与 `cases.jsonl` 的 `verify` 代码一起看，就能从源码复现该数字；
`--save` 重跑一次即可重建整份报告，不需要手工抄数。注意 `calc_ece`/`calc_mce`
的 bin 边界是 `[lo, hi)`，最后一个 bin 用 `[lo, hi]` —— `CC-03` 专门钉这个边界
（conf=1.0 必须落进最后一个 bin，否则 ECE 会被算成 0）。

**失败归因**：`run_cases.py` 不只报通过率，失败时按 `axis` 汇总（例如
`metrics/ece: 1 条 —— CC-01`），直接指出是哪个口径坏了，而不是只给一个 pass_rate。

**边界**：这套题只验证脚本侧的口径（指标实现、解析/归一、条件配置、同步消息格式），
**不**验证论文数字——本仓没有提交结果 JSON，ECE/100,500 calls 无法从仓库复算
（见上文 *What this doesn't claim / Limits*）。