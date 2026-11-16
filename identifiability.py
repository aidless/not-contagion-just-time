#!/usr/bin/env python3
"""Synthetic identifiability check for the C1–C4 factorial reading.

This is a method check. It does not estimate, confirm, or reproduce any
number from the manuscript "Not Contagion, Just Time". No API is called.

What is planted
---------------
Three generative models write per-trial (confidence, accuracy) records for
the condition dicts in ``cc_full_experiment.CONDITIONS``. Accuracy is an
independent coin flip at ``P_ACC`` in every model, so the only signal is
confidence.

* ``temporal`` — confidence rises by ``DRIFT_PER_ROUND`` each round for every
  agent. ``sync`` and ``seeded_miscal`` are ignored.
* ``contagion`` — the seeded agent (last index, only when the condition sets
  ``seeded_miscal``) reports confidence near ``SEED_CONFIDENCE``. On later
  rounds, and only when ``sync`` is set, every other agent's confidence is
  pulled toward that seed's previous-round mean by ``CONTAGION_PULL``.
* ``null`` — confidence stays near ``P_ACC``. Condition flags are ignored.

What is read back
-----------------
Round-level ECE is ``cc_full_experiment.calc_ece`` on that agent's trials,
then averaged across agents, matching ``run_condition``. The decision uses
``cc_full_experiment.wilcoxon`` (the same two-sided test ``main`` prints)
on final-round ECE versus C1, and the sign of the mean difference.

The label is a reading of those printed contrasts, not a new estimator:

1. ``contagion`` if C3's final ECE is significantly higher than C1.
   C3 is the matched-horizon (T=10) sync cell. This contrast also changes
   N and the seeded agent; see FAILURE_MODES.md.
2. else ``temporal`` if both C2 and C4 are significantly higher than C1
   and C3 is not.
3. else ``null`` if none of C2, C3, C4 is significantly higher than C1.
4. else ``other``.

"Significantly higher" means two-sided p < ``ALPHA`` and a positive mean
difference. p-values are not multiplicity-corrected, because the experiment
script prints them uncorrected.

Recovery is the fraction of seeds whose label equals the planted name.
False-attribution under the null is the fraction of null seeds labeled
``temporal`` or ``contagion`` (a named mechanism). ``other`` is counted
separately and is not included in that rate.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

import cc_full_experiment as exp

MASTER_SEED = 20261116
N_SEEDS = 40
N_REPS = 20
N_TRIALS = 40
P_ACC = 0.55
NOISE_SD = 0.03
DRIFT_PER_ROUND = 0.03
SEED_CONFIDENCE = 0.90
CONTAGION_PULL = 0.75
ALPHA = 0.05

MECHANISMS = ("temporal", "contagion", "null")
LABELS = ("temporal", "contagion", "null", "other")

# Human headline must contain these phrases plus the fraction. `make check`
# rejects a README whose sentence and machine block disagree.
PROSE_TEMPORAL = "temporal"
PROSE_CONTAGION = "contagion"
PROSE_FALSE = "null false-attribution"


def _rng(mechanism: str, seed: int) -> np.random.Generator:
    code = {"temporal": 1, "contagion": 2, "null": 3}[mechanism]
    return np.random.default_rng(np.random.SeedSequence([MASTER_SEED, int(seed), code]))


def _clip(x: np.ndarray) -> np.ndarray:
    return np.clip(x, 0.0, 1.0)


def simulate_mechanism(mechanism: str, seed: int) -> dict:
    """One planted mechanism, one seed, all four conditions.

    The returned dict is shaped like one ``cc_full_experiment`` result file:
    per condition, ``ece_per_rep`` is a list of per-round mean ECE.
    """
    if mechanism not in MECHANISMS:
        raise ValueError(mechanism)
    rng = _rng(mechanism, seed)
    out = {}
    for cid, cfg in exp.CONDITIONS.items():
        n_agents = cfg["n_agents"]
        n_rounds = cfg["n_rounds"]
        sync = bool(cfg["sync"])
        seeded = bool(cfg["seeded_miscal"])
        ece_per_rep = []
        for _rep in range(N_REPS):
            prev_seed_mean = None
            rounds = []
            for rnd in range(n_rounds):
                agent_ece = []
                seed_values = None
                for ai in range(n_agents):
                    noise = rng.normal(0.0, NOISE_SD, size=N_TRIALS)
                    acc = (rng.random(N_TRIALS) < P_ACC).astype(float)
                    is_seed = seeded and ai == n_agents - 1
                    if mechanism == "temporal":
                        conf = _clip(P_ACC + DRIFT_PER_ROUND * rnd + noise)
                    elif mechanism == "contagion":
                        if is_seed:
                            conf = _clip(np.full(N_TRIALS, SEED_CONFIDENCE) + noise)
                        elif sync and rnd > 0 and prev_seed_mean is not None:
                            own = _clip(P_ACC + noise)
                            conf = _clip((1.0 - CONTAGION_PULL) * own + CONTAGION_PULL * prev_seed_mean)
                        else:
                            conf = _clip(P_ACC + noise)
                    else:
                        conf = _clip(P_ACC + noise)
                    agent_ece.append(exp.calc_ece(conf, acc))
                    if is_seed:
                        seed_values = conf
                if seed_values is not None:
                    prev_seed_mean = float(np.mean(seed_values))
                rounds.append(float(np.mean(agent_ece)))
            ece_per_rep.append(rounds)
        arr = np.asarray(ece_per_rep, dtype=float)
        out[cid] = {
            "condition": cid,
            "desc": cfg["desc"],
            "n_agents": n_agents,
            "n_rounds": n_rounds,
            "sync": sync,
            "seeded_miscal": seeded,
            "n_reps": N_REPS,
            "ece_per_rep": ece_per_rep,
            "ece_traj_mean": arr.mean(axis=0).tolist(),
            "ece_traj_std": arr.std(axis=0).tolist(),
        }
    return out


def _significantly_higher(candidate: np.ndarray, baseline: np.ndarray, alpha: float) -> bool:
    candidate = np.asarray(candidate, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    if candidate.shape != baseline.shape or candidate.size == 0:
        raise ValueError("Wilcoxon contrast requires equal non-empty samples")
    if float(np.mean(candidate) - np.mean(baseline)) <= 0.0:
        return False
    p = exp.wilcoxon(candidate, baseline)
    if p != p:  # NaN: the repo helper returns this when every difference is 0
        return False
    return float(p) < alpha


def attribute(finals: dict, alpha: float = ALPHA) -> str:
    """Label a finished factorial from final-round ECE vectors keyed by condition."""
    missing = [cid for cid in ("C1", "C2", "C3", "C4") if cid not in finals]
    if missing:
        raise KeyError(",".join(missing))
    base = finals["C1"]
    higher = {cid: _significantly_higher(finals[cid], base, alpha) for cid in ("C2", "C3", "C4")}
    if higher["C3"]:
        return "contagion"
    if higher["C2"] and higher["C4"]:
        return "temporal"
    if not higher["C2"] and not higher["C3"] and not higher["C4"]:
        return "null"
    return "other"


def _finals(data: dict) -> dict:
    return {
        cid: np.asarray([rep[-1] for rep in data[cid]["ece_per_rep"]], dtype=float)
        for cid in exp.CONDITIONS
    }


def run_study(n_seeds: int = N_SEEDS) -> dict:
    counts = {mechanism: {label: 0 for label in LABELS} for mechanism in MECHANISMS}
    for index in range(n_seeds):
        seed = MASTER_SEED + index
        for mechanism in MECHANISMS:
            label = attribute(_finals(simulate_mechanism(mechanism, seed)))
            counts[mechanism][label] += 1
    return counts


def summary_from_counts(counts: dict, n_seeds: int) -> dict:
    def frac(mechanism: str, label: str) -> str:
        return f"{counts[mechanism][label]}/{n_seeds}"

    false_named = counts["null"]["temporal"] + counts["null"]["contagion"]
    return {
        "seeds": str(n_seeds),
        "reps": str(N_REPS),
        "trials_per_agent_round": str(N_TRIALS),
        "alpha": f"{ALPHA:.2f}",
        "drift_per_round": f"{DRIFT_PER_ROUND:.2f}",
        "contagion_pull": f"{CONTAGION_PULL:.2f}",
        "seed_confidence": f"{SEED_CONFIDENCE:.2f}",
        "noise_sd": f"{NOISE_SD:.2f}",
        "p_acc": f"{P_ACC:.2f}",
        "master_seed": str(MASTER_SEED),
        "recovery_temporal": frac("temporal", "temporal"),
        "recovery_contagion": frac("contagion", "contagion"),
        "false_attribution_null": f"{false_named}/{n_seeds}",
        "null_labeled_null": frac("null", "null"),
        "null_labeled_other": frac("null", "other"),
        "temporal_labeled_other": frac("temporal", "other"),
        "contagion_labeled_other": frac("contagion", "other"),
        "temporal_labeled_contagion": frac("temporal", "contagion"),
        "contagion_labeled_temporal": frac("contagion", "temporal"),
    }


def render_block(summary: dict) -> str:
    lines = ["<!-- IDENTIFIABILITY"]
    for key, value in summary.items():
        lines.append(f"{key}={value}")
    lines.append("-->")
    return "\n".join(lines)


def extract_block(text: str) -> str:
    start = text.find("<!-- IDENTIFIABILITY")
    if start < 0:
        raise ValueError("README is missing the IDENTIFIABILITY block")
    end = text.find("-->", start)
    if end < 0:
        raise ValueError("IDENTIFIABILITY block is not closed")
    return text[start : end + 3].strip()


def block_matches(text: str, summary: dict) -> bool:
    try:
        found = extract_block(text)
    except ValueError:
        return False
    return found == render_block(summary).strip()


def prose_matches(text: str, summary: dict) -> bool:
    """The visible headline has to carry the same fractions as the block."""
    needed = (
        f"temporal {summary['recovery_temporal']}",
        f"contagion {summary['recovery_contagion']}",
        f"null false-attribution {summary['false_attribution_null']}",
        f"temporal labeled contagion {summary['temporal_labeled_contagion']}",
        f"null labeled other {summary['null_labeled_other']}",
    )
    return all(token in text for token in needed)


def write_figures(directory: str | Path, seed: int = MASTER_SEED) -> None:
    """Run the repo's figure script on one planted temporal factorial.

    Outputs are synthetic. Fig 3 in that script does not read the JSON; it
    draws a schematic. The files are written only under ``directory``.
    """
    import cc_analysis_figures as figs

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    data = simulate_mechanism("temporal", seed)
    note = directory / "SYNTHETIC.txt"
    note.write_text(
        "Synthetic identifiability draw (planted temporal drift, one seed).\n"
        "Not manuscript data. Fig 3 from cc_analysis_figures.py is a schematic\n"
        "and does not plot these trajectories.\n",
        encoding="utf-8",
    )
    previous = Path.cwd()
    try:
        os.chdir(directory)
        figs.fig1_trajectories(data, "fig1_ece_trajectories.pdf")
        figs.fig2_final_comparison(data, "fig2_final_ece.pdf")
        figs.fig3_reliability(data, "fig3_reliability.pdf")
        figs.table1_latex(data)
    finally:
        os.chdir(previous)
    expected = (
        "fig1_ece_trajectories.pdf",
        "fig2_final_ece.pdf",
        "fig3_reliability.pdf",
        "cc_table1.tex",
        "SYNTHETIC.txt",
    )
    missing = [name for name in expected if not (directory / name).is_file()]
    if missing:
        raise RuntimeError(f"analysis outputs missing: {missing}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic identifiability study (not manuscript results).")
    parser.add_argument("--check", default="", help="README path; exit 1 if the block or headline drifts")
    parser.add_argument("--figures-dir", default="", help="write one synthetic factorial through cc_analysis_figures")
    parser.add_argument("--seeds", type=int, default=N_SEEDS)
    args = parser.parse_args(argv)

    counts = run_study(args.seeds)
    summary = summary_from_counts(counts, args.seeds)
    print(render_block(summary))
    print(
        f"Synthetic recovery: temporal {summary['recovery_temporal']}, "
        f"contagion {summary['recovery_contagion']}, "
        f"null false-attribution {summary['false_attribution_null']}."
    )
    if args.figures_dir:
        write_figures(args.figures_dir)
        print(f"synthetic figures: {args.figures_dir}")
    if args.check:
        text = Path(args.check).read_text(encoding="utf-8")
        ok_block = block_matches(text, summary)
        ok_prose = prose_matches(text, summary)
        if not ok_block or not ok_prose:
            print("README drift: identifiability summary does not match a fresh run", file=sys.stderr)
            if not ok_block:
                print("--- README block ---", file=sys.stderr)
                try:
                    print(extract_block(text), file=sys.stderr)
                except ValueError as exc:
                    print(str(exc), file=sys.stderr)
                print("--- fresh block ---", file=sys.stderr)
                print(render_block(summary), file=sys.stderr)
            if not ok_prose:
                print(
                    "headline is missing the fresh fractions "
                    f"(temporal {summary['recovery_temporal']}, "
                    f"contagion {summary['recovery_contagion']}, "
                    f"null false-attribution {summary['false_attribution_null']})",
                    file=sys.stderr,
                )
            return 1
        print(f"README matches {args.check}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
