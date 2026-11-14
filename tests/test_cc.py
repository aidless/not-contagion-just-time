"""tests/test_cc.py — 真实单元测试（无 API key，纯函数）。

覆盖 not-contagion-just-time 的纯函数：calc_ece / calc_mce / calc_brier / parse /
norm / correct。全部为确定值断言（RED→GREEN 可复现），不触网、不需要 API key。

测试值来自函数定义本身的数学性质（ECE/MCE/Brier 对完美校准=0、对全错=1），
非编造。用 pytest 运行：`pytest tests/ -q`。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from cc_full_experiment import calc_ece, calc_mce, calc_brier, parse, norm, correct


# ---- ECE / MCE / Brier: 完美校准 = 0 ----
def test_calc_ece_perfect_calibration_is_zero():
    # 完美校准：每个 bin 内 conf==acc → ECE=0
    conf = [0.1, 0.3, 0.5, 0.7, 0.9]
    acc = [0.1, 0.3, 0.5, 0.7, 0.9]
    assert calc_ece(conf, acc) == 0.0


def test_calc_mce_perfect_calibration_is_zero():
    conf = [0.2, 0.8]
    acc = [0.2, 0.8]
    assert calc_mce(conf, acc) == 0.0


def test_calc_brier_perfect_calibration_is_zero():
    conf = [0.5, 0.5]
    acc = [0.5, 0.5]
    assert calc_brier(conf, acc) == 0.0


# ---- ECE 非负、Brier 非负 ----
def test_calc_ece_non_negative():
    conf = [0.9, 0.9, 0.9]
    acc = [0.0, 0.0, 0.0]
    assert calc_ece(conf, acc) >= 0.0


def test_calc_brier_non_negative():
    conf = [0.9, 0.9]
    acc = [0.1, 0.1]
    assert calc_brier(conf, acc) > 0.0


# ---- Brier 最差情形（conf=1, acc=0）→ 1.0 ----
def test_calc_brier_worst_case_is_one():
    conf = [1.0, 1.0]
    acc = [0.0, 0.0]
    assert abs(calc_brier(conf, acc) - 1.0) < 1e-9


# ---- parse: JSON 与字符串两种格式 ----
def test_parse_json_response():
    resp = '{"answer":"42","confidence":0.8}'
    ans, conf = parse(resp)
    assert ans == "42"
    assert conf == 0.8


def test_parse_string_fallback():
    # 非 JSON → 字符串截断 + 默认 0.5
    ans, conf = parse("some text without json")
    assert conf == 0.5
    assert isinstance(ans, str)


def test_parse_clamps_confidence():
    # 越界 confidence 被 clamp 到 [0,1]
    _, conf = parse('{"answer":"42","confidence":1.7}')
    assert conf == 1.0


# ---- norm: 数值归一 ----
def test_norm_strips_currency_and_commas():
    assert norm("$1,000") == "1000"


def test_norm_handles_fraction():
    assert norm("1/2") == "0.5"


# ---- correct: 答案判等 ----
def test_correct_exact():
    assert correct("42", "42") is True


def test_correct_numeric_tolerance():
    assert correct("42.0", "42") is True


def test_correct_wrong_answer():
    assert correct("43", "42") is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
