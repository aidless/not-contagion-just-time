# Not Contagion, Just Time — Experiment Scripts

[![CI](https://github.com/aidless/not-contagion-just-time/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/not-contagion-just-time/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Companion scripts for the manuscript *Not Contagion, Just Time: Temporal Calibration Fatigue in LLM Agents*. This repository does not record a venue acceptance. Some filenames say `revision` or `rebuttal`; that is the script's name, not a decision.

The manuscript asks whether group calibration error grows because peers copy an overconfident agent, or because more rounds pass.
This repository is the C1–C4 harness for that question: an isolated baseline against sync with one seeded overconfident agent.
Scripts only. No result JSONs, checkpoints or figures are committed — manuscript ECE, p-values, effect sizes, and the stated 100,500 API calls are not in this tree and are not re-checkable here.

**Headline (method check, not the manuscript).** A synthetic identifiability study plants temporal drift, peer contagion, or a null, then labels each seed with this repo's own two-sided Wilcoxon test on final-round ECE (`cc_full_experiment.wilcoxon`, uncorrected, versus C1). Synthetic recovery: temporal 39/40, contagion 40/40, null false-attribution 0/40 (temporal labeled contagion 1/40; null labeled other 1/40). Limits: effects in the simulator are large, accuracy is independent of confidence, and each agent-round has 40 trials rather than the live `N_Q = 5`, so the setup favors the analysis. The C3-versus-C1 contrast also changes group size and the seeded agent. Nothing above is a manuscript ΔECE, p-value, or effect size. Live re-runs need `DMXAPI_KEY` and, for the DeepSeek scripts, `DEEPSEEK_API_KEY`, and they are not bit-identical.

**STATUS: WORK-IN-PROGRESS — not A yet.** The in-tree README, MIT badge, and CI entry point agree that no result file is committed. The remaining gap is the GitHub About string, which is not stored in git. It still reads: `Companion scripts for "Not Contagion, Just Time: Temporal Calibration Fatigue in LLM Agents"; result data available upon request`. Replacement to paste into About:

`Manuscript scripts for "Not Contagion, Just Time". No result files are in this repo, and no acceptance is recorded here.`

<!-- IDENTIFIABILITY
seeds=40
reps=20
trials_per_agent_round=40
alpha=0.05
drift_per_round=0.03
contagion_pull=0.75
seed_confidence=0.90
noise_sd=0.03
p_acc=0.55
master_seed=20261116
recovery_temporal=39/40
recovery_contagion=40/40
false_attribution_null=0/40
null_labeled_null=39/40
null_labeled_other=1/40
temporal_labeled_other=0/40
contagion_labeled_other=0/40
temporal_labeled_contagion=1/40
contagion_labeled_temporal=0/40
-->

`make check` recomputes that block with the fixed seeds and exits non-zero if this file drifts. Definitions, and the ways the simulator favors a positive reading, are in [FAILURE_MODES.md](FAILURE_MODES.md).

## Offline check

No API keys.

```bash
python3 -m pip install -r requirements.txt
make check
```

`make check` runs the unit tests, `eval/run_cases.py` (20/20, and a self-test that must score 19/20), a `--dry-run` that uses a deterministic mock LLM, and `identifiability.py`. The mock does not open a socket. `--dry-run` without the flag still calls the live API.

```bash
python3 cc_full_experiment.py --phase 1 --reps 1 --conditions C1 --dry-run
python3 identifiability.py
```

## What is not in this repository

- No result JSON, checkpoint, or figure from the manuscript runs. The figure script `cc_analysis_figures.py` still reads an external result file. Its Fig 3 is a schematic and does not plot that file.
- The 100,500-call total is a stated figure from those runs. It cannot be re-derived from committed files.
- Re-running the live scripts produces new responses. The harness sends a per-call temperature and does not seed model outputs.
- `identifiability.py` writes synthetic trajectories only. `make check` puts the example figures in a temp directory and does not commit them.

## Design constants (from the scripts, not from outcomes)

| Item | Value | Where |
|------|-------|--------|
| Questions per agent-round | `N_Q = 5` | `cc_full_experiment.py` |
| GSM8K items | 30 | `GSM8K` in the experiment scripts |
| C1 | 3 agents, 10 rounds, no sync, no seed | `CONDITIONS` |
| C2 | 3 agents, 20 rounds, sync + seed | `CONDITIONS` |
| C3 | 5 agents, 10 rounds, sync + seed | `CONDITIONS` |
| C4 | 5 agents, 20 rounds, sync + seed | `CONDITIONS` |
| Default reps | 30 | `cc_full_experiment.py --reps` |

A 403 after more than 500 calls saves the finished reps and raises `RATE_LIMIT`. It does not fill the missing reps. Checkpoints are `cc_full_ckpt_{cid}.json`.

## Acceptance cases

`eval/cases.jsonl` has 20 executable checks of the metric, parser, condition dicts, and the "scripts only" sentence. They do not check manuscript outcomes.

```bash
python3 eval/run_cases.py
python3 eval/run_cases.py --selftest   # must fail exactly one case
```

## License

Code is MIT ([LICENSE](LICENSE)). No dataset, result JSON, checkpoint, or figure is committed, so there is no in-tree data release to put under CC BY 4.0. [LICENSE-DATA](LICENSE-DATA) records that absence. GitHub's license detector reports `NOASSERTION` when a repository contains more than one license file; the code license is the MIT file.

## GitHub About

About is a repository setting, not a file in this checkout. Current text (read from the GitHub API, not from git):

`Companion scripts for "Not Contagion, Just Time: Temporal Calibration Fatigue in LLM Agents"; result data available upon request`

That sentence points at data this checkout does not contain. Paste this instead:

`Manuscript scripts for "Not Contagion, Just Time". No result files are in this repo, and no acceptance is recorded here.`
