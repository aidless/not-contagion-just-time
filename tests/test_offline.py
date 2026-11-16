"""Offline checks: dry-run must not touch the network, and the identifiability
reading of the repo's own Wilcoxon contrasts must be deterministic.

These tests do not use API keys and do not claim manuscript results.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cc_full_experiment


def _run_dry(tmp_path, monkeypatch, capsys):
    calls = []

    def boom(*args, **kwargs):
        calls.append((args, kwargs))
        raise OSError("network blocked")

    monkeypatch.setattr(cc_full_experiment.urllib.request, "urlopen", boom)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DMXAPI_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cc_full_experiment.py",
            "--phase",
            "1",
            "--reps",
            "1",
            "--conditions",
            "C1",
            "--dry-run",
        ],
    )
    cc_full_experiment.main()
    out = capsys.readouterr().out
    return calls, out


def test_dry_run_does_not_open_the_network(tmp_path, monkeypatch, capsys):
    calls, out = _run_dry(tmp_path, monkeypatch, capsys)
    assert calls == []
    assert "offline deterministic mock" in out
    assert "401" not in out
    assert "Unauthorized" not in out
    assert "API fail" not in out
    result_path = tmp_path / "cc_full_phase1_1reps.json"
    assert result_path.is_file()
    data = json.loads(result_path.read_text(encoding="utf-8"))
    confs = [c for rep in data["C1"]["conf_per_rep"] for c in rep]
    # The error fallback stores 0.5 for every failed call. A real mock must not.
    assert any(abs(c - 0.5) > 1e-9 for c in confs)
    assert data["C1"]["calls"] == 3 * 10 * 5


def test_dry_run_is_deterministic(tmp_path, monkeypatch, capsys):
    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    first_dir.mkdir()
    second_dir.mkdir()
    _, _ = _run_dry(first_dir, monkeypatch, capsys)
    _, _ = _run_dry(second_dir, monkeypatch, capsys)
    a = json.loads((first_dir / "cc_full_phase1_1reps.json").read_text(encoding="utf-8"))
    b = json.loads((second_dir / "cc_full_phase1_1reps.json").read_text(encoding="utf-8"))
    assert a["C1"]["ece_per_rep"] == b["C1"]["ece_per_rep"]
    assert a["C1"]["conf_per_rep"] == b["C1"]["conf_per_rep"]


def test_live_api_still_calls_urlopen(monkeypatch):
    calls = []

    class Resp:
        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"answer\\":\\"18\\",\\"confidence\\":0.4}"}}]}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(*args, **kwargs):
        calls.append(args)
        return Resp()

    monkeypatch.setattr(cc_full_experiment.urllib.request, "urlopen", fake_urlopen)
    cc_full_experiment._DRY_RUN = False
    text = cc_full_experiment.api("system", "user", 0.7)
    assert calls
    assert "18" in text


def test_attribute_reads_wilcoxon_patterns():
    import numpy as np

    from identifiability import attribute

    rng = np.random.default_rng(0)
    low = 0.05 + rng.normal(0, 0.005, size=20)
    high = 0.45 + rng.normal(0, 0.005, size=20)
    assert attribute({"C1": low, "C2": high, "C3": low.copy(), "C4": high.copy()}) == "temporal"
    assert attribute({"C1": low, "C2": high, "C3": high.copy(), "C4": high.copy()}) == "contagion"
    assert attribute({"C1": low, "C2": low.copy(), "C3": low.copy(), "C4": low.copy()}) == "null"
    assert attribute({"C1": low, "C2": high, "C3": low.copy(), "C4": low.copy()}) == "other"


def test_summary_block_detects_readme_drift():
    from identifiability import block_matches, render_block

    summary = {
        "recovery_temporal": "3/4",
        "recovery_contagion": "4/4",
        "false_attribution_null": "1/4",
    }
    text = "before\n" + render_block(summary) + "\nafter\n"
    assert block_matches(text, summary)
    assert not block_matches(text.replace("3/4", "2/4"), summary)


def test_one_seed_shapes_match_condition_dicts():
    from identifiability import simulate_mechanism

    data = simulate_mechanism("temporal", seed=20261116)
    assert set(data) == {"C1", "C2", "C3", "C4"}
    assert len(data["C1"]["ece_per_rep"]) == len(data["C4"]["ece_per_rep"])
    assert len(data["C1"]["ece_per_rep"][0]) == 10
    assert len(data["C2"]["ece_per_rep"][0]) == 20
    assert data["C3"]["n_agents"] == 5
    assert data["C1"]["sync"] is False
    assert data["C4"]["sync"] is True
