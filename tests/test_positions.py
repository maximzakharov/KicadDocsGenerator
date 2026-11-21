"""Tests for generate_positions() output (positions.csv contents)."""

import csv

import pytest

import pcbnew  # the mock installed by conftest.py

from plugins.config import placementFileName


def read_rows(tmp_path):
    path = tmp_path / placementFileName
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_basic_row(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(
                reference="R1",
                value="10k",
                position=(1000000, -2000000),  # nm
                orientation=90.0,
            )
        ]
    )
    pm.generate_positions(str(tmp_path))

    rows = read_rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["Designator"] == "R1"
    assert float(row["Mid X"]) == 1.0
    assert float(row["Mid Y"]) == 2.0  # Y axis is inverted
    assert float(row["Rotation"]) == 90.0
    assert row["Layer"] == "top"


def test_footprints_sorted_by_reference(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[dict(reference="C2"), dict(reference="R10"), dict(reference="C1")]
    )
    pm.generate_positions(str(tmp_path))
    assert [r["Designator"] for r in read_rows(tmp_path)] == ["C1", "C2", "R10"]


def test_aux_origin_subtracted(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[dict(reference="R1", position=(3000000, 4000000))],
        aux_origin=(1000000, 2000000),
    )
    pm.generate_positions(str(tmp_path))
    row = read_rows(tmp_path)[0]
    assert float(row["Mid X"]) == 2.0
    assert float(row["Mid Y"]) == -2.0


def test_bottom_layer(make_process_manager, tmp_path):
    pm = make_process_manager(footprints=[dict(reference="R1", layer=pcbnew.B_Cu)])
    pm.generate_positions(str(tmp_path))
    assert read_rows(tmp_path)[0]["Layer"] == "bottom"


def test_rotation_offset_wraps(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(
                reference="R1",
                orientation=10.0,
                fields={"JLCPCB Rotation Offset": "350"},
            )
        ]
    )
    pm.generate_positions(str(tmp_path))
    assert float(read_rows(tmp_path)[0]["Rotation"]) == 0.0  # (10 + 350) % 360


def test_legacy_orientation_api(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[dict(reference="R1", orientation_raw=900)]  # tenths of degree
    )
    pm.generate_positions(str(tmp_path))
    assert float(read_rows(tmp_path)[0]["Rotation"]) == 90.0


def test_position_offset_is_rotated(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(
                reference="R1",
                orientation=90.0,
                fields={"JLCPCB Position Offset": "1,0"},
            )
        ]
    )
    pm.generate_positions(str(tmp_path))
    row = read_rows(tmp_path)[0]
    # offset (1, 0) rotated by 90 deg -> (0, 1)
    assert float(row["Mid X"]) == pytest.approx(0.0, abs=1e-9)
    assert float(row["Mid Y"]) == pytest.approx(1.0, abs=1e-9)


def test_duplicate_references_get_unique_suffix(make_process_manager, tmp_path):
    pm = make_process_manager(footprints=[dict(reference="R1"), dict(reference="R1")])
    pm.generate_positions(str(tmp_path))
    assert [r["Designator"] for r in read_rows(tmp_path)] == ["R1_2", "R1"]


def test_excluded_from_pos_files(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(reference="R1"),
            dict(reference="TP1", attributes=pcbnew.FP_EXCLUDE_FROM_POS_FILES),
        ]
    )
    pm.generate_positions(str(tmp_path))
    assert [r["Designator"] for r in read_rows(tmp_path)] == ["R1"]


def test_legacy_board_api_get_modules(make_process_manager, tmp_path):
    pm = make_process_manager(footprints=[dict(reference="R1")], legacy=True)
    pm.generate_positions(str(tmp_path))
    assert [r["Designator"] for r in read_rows(tmp_path)] == ["R1"]


def test_kicad9_strict_field_api_end_to_end(make_process_manager, tmp_path):
    """KiCad >= 9 raises for missing fields; generation must still complete."""
    pm = make_process_manager(
        footprints=[
            dict(
                reference="R1",
                fields={"Mfr_Part_Number": "PN_A"},
                strict_fields=True,
            ),
            dict(reference="C1", strict_fields=True),  # no fields at all
        ]
    )
    pm.generate_positions(str(tmp_path))
    assert [r["Designator"] for r in read_rows(tmp_path)] == ["C1", "R1"]
