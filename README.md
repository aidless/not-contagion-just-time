# Not Contagion, Just Time — Experiment Scripts

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
