"""
test_utils_formato.py — formatação de números à portuguesa (utils.fmt_int / utils.fmt_pct).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'streamlit-dashboard'))

from utils import fmt_int, fmt_pct


def test_fmt_int_milhares_com_espaco():
    assert fmt_int(58261) == "58\u00a0261"


def test_fmt_int_pequeno():
    assert fmt_int(5) == "5"


def test_fmt_int_nan():
    assert fmt_int(float("nan")) == "—"


def test_fmt_pct_virgula():
    assert fmt_pct(67.25) == "67,2%" or fmt_pct(67.25) == "67,3%"
    assert fmt_pct(15) == "15,0%"
