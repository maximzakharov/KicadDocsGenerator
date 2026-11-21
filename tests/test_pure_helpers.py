"""Tests for helpers that need no KiCad objects at all."""

import math

import pytest

from plugins.plot import hex_to_rgb, is_number as plot_is_number
from plugins.thread import bool_convert


@pytest.fixture
def pm(make_process_manager):
    return make_process_manager()


# ---------------------------------------------------------------------------
# s-expression parser
# ---------------------------------------------------------------------------


def test_parse_sexp_types(pm):
    src = '(kicad_pcb (version 20221018) (generator "edea") (num 3.5) (neg -7))'
    out = pm.parse_sexp(src)
    assert out[0] == "kicad_pcb"
    assert out[1] == ["version", 20221018]  # integer stays int
    assert out[2] == ["generator", "edea"]  # quoted string unquoted
    assert out[3] == ["num", 3.5]
    assert out[4] == ["neg", -7]


def test_parse_sexp_deep_nesting(pm):
    out = pm.parse_sexp("(a (b (c (d 1))))")
    assert out == ["a", ["b", ["c", ["d", 1]]]]


def test_parse_sexp_unbalanced_raises(pm):
    with pytest.raises(AssertionError):
        pm.parse_sexp("(a (b)")
    with pytest.raises(AssertionError):
        pm.parse_sexp("(a b))")


# ---------------------------------------------------------------------------
# revision lookup
# ---------------------------------------------------------------------------


def test_get_revision_found(pm, tmp_path):
    board = tmp_path / "project.kicad_pcb"
    board.write_text(
        '(kicad_pcb\n (property "VERSION" "rev_42")\n'
        ' (property "Sheetname" "root")\n)\n'
    )
    assert pm.get_revision(str(board)) == "rev_42"


def test_get_revision_missing(pm, tmp_path):
    board = tmp_path / "project.kicad_pcb"
    board.write_text('(kicad_pcb (property "Sheetname" "root"))\n')
    assert pm.get_revision(str(board)) is None


# ---------------------------------------------------------------------------
# footprint name normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Resistor_SMD:R_0603_1608Metric", "0603"),
        ("R_0402_1005Metric", "0402"),
        ("LED_0603_1608Metric", "0603"),
        ("Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm", "0805"),
        # non-metric footprints pass through unchanged
        ("Package_SO:SOP-8_3.9x4.9mm_P1.27mm", "Package_SO:SOP-8_3.9x4.9mm_P1.27mm"),
        ("Package_TO_SOT_SMD:SOT-23", "Package_TO_SOT_SMD:SOT-23"),
    ],
)
def test_normalize_footprint_name(pm, name, expected):
    assert pm._normalize_footprint_name(name) == expected


# ---------------------------------------------------------------------------
# small numeric helpers
# ---------------------------------------------------------------------------


def test_is_number(pm):
    assert pm.is_number("1.5")
    assert pm.is_number("-2")
    assert not pm.is_number("abc")
    assert not pm.is_number("")


def test_to_float(pm):
    assert pm.to_float("2.5") == 2.5
    assert pm.to_float("") == 0
    assert pm.to_float("x") == 0


def test_plot_is_number():
    assert plot_is_number("2")
    assert not plot_is_number("1,5")


def test_hex_to_rgb():
    r, g, b = hex_to_rgb("#00CD66")
    assert r == 0.0
    assert math.isclose(g, 205 / 255, abs_tol=1e-9)
    assert math.isclose(b, 102 / 255, abs_tol=1e-9)


def test_bool_convert():
    assert bool_convert("True") is True
    assert bool_convert("False") is False
    assert bool_convert("true") is False  # strict match, documented behavior
