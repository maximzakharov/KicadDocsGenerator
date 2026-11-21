"""Tests for generate_positions() BOM collection + generate_bom() output.

These tests exercise real CSV and XLSX output and therefore need pandas,
openpyxl and xlsxwriter (see requirements-dev.txt).
"""

import csv

import pytest

pd = pytest.importorskip("pandas")


def read_csv_rows(tmp_path, project_name):
    path = tmp_path / f"Bill of Materials-{project_name}.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_same_mpn_merges_into_single_line(make_process_manager, tmp_path):
    part = {"Mfr_Part_Number": "RC0603", "Unit price": "0.5"}
    pm = make_process_manager(
        footprints=[
            dict(reference="R1", fields=part),
            dict(reference="R2", fields=part),
            dict(reference="R3", fields=part),
        ]
    )
    pm.generate_positions(str(tmp_path))
    assert len(pm.bom) == 1

    pm.generate_bom(str(tmp_path), "proj")
    rows = read_csv_rows(tmp_path, "proj")
    assert len(rows) == 1
    row = rows[0]
    assert row["Designator"] == "R1, R2, R3"
    assert int(row["Quantity"]) == 3
    assert float(row["Total price"]) == pytest.approx(1.5)


def test_different_mpn_stay_separate(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(reference="R1", fields={"Mfr_Part_Number": "PN_A"}),
            dict(reference="C1", fields={"Mfr_Part_Number": "PN_B"}),
        ]
    )
    pm.generate_positions(str(tmp_path))
    pm.generate_bom(str(tmp_path), "proj")
    rows = read_csv_rows(tmp_path, "proj")
    # footprints are processed sorted by reference: C1 first
    assert [r["Mfr_Part_Number"] for r in rows] == ["PN_B", "PN_A"]


def test_bom_columns_and_fields(make_process_manager, tmp_path):
    fields = {
        "Mfr_Name": "Yageo",
        "Mfr_Part_Number": "RC0603FR-0710KL",
        "LCSC": "C25804",  # via fallback key (no LCSC_Part present)
        "Link": "https://example.com/p/RC0603FR-0710KL",
        "Unit price": "0.12",
    }
    pm = make_process_manager(
        footprints=[
            dict(
                reference="R1",
                value="10k",
                footprint_name="Resistor_SMD:R_0603_1608Metric",
                fields=fields,
            )
        ]
    )
    pm.generate_positions(str(tmp_path))
    pm.generate_bom(str(tmp_path), "proj")

    row = read_csv_rows(tmp_path, "proj")[0]
    assert row["Value"] == "10k"
    assert row["Footprint"] == "0603"  # normalized footprint name
    assert row["Mfr_Name"] == "Yageo"
    assert row["Mfr_Part_Number"] == "RC0603FR-0710KL"
    assert row["LCSC_Part"] == "C25804"
    assert row["Link"] == "https://example.com/p/RC0603FR-0710KL"
    assert float(row["Unit price"]) == 0.12
    assert float(row["Total price"]) == 0.12


def test_xlsx_written_and_matches_csv(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(reference="R1", fields={"Mfr_Part_Number": "PN_A"}),
            dict(reference="R2", fields={"Mfr_Part_Number": "PN_A"}),
            dict(reference="C1", fields={"Mfr_Part_Number": "PN_B"}),
        ]
    )
    pm.generate_positions(str(tmp_path))
    pm.generate_bom(str(tmp_path), "proj")

    xlsx = tmp_path / "Bill of Materials-proj.xlsx"
    assert xlsx.exists()
    df = pd.read_excel(xlsx, sheet_name="BOM")
    assert len(df) == 2
    # footprints are processed sorted by reference: C1 first
    assert list(df["Designator"]) == ["C1", "R1, R2"]
    assert list(df["Quantity"]) == [1, 2]


def test_asterisk_designators_filtered(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(reference="R1"),
            dict(
                reference="**",  # e.g. mechanical / fiducial markers
                footprint_name="MountingHole_3.2mm_M3",
            ),
        ]
    )
    pm.generate_positions(str(tmp_path))
    pm.generate_bom(str(tmp_path), "proj")
    rows = read_csv_rows(tmp_path, "proj")
    assert [r["Designator"] for r in rows] == ["R1"]


def test_same_mpn_different_footprints_merges(make_process_manager, tmp_path):
    """Same MPN = one purchasing line even if footprint names differ.

    Real-world case: Hirose DF40HC(3.0)-100DS-0.4V(51) on CM4_Connector_1
    and CM4_Connector_2 footprints must end up as a single BOM line.
    """
    pm = make_process_manager(
        footprints=[
            dict(
                reference="J4",
                value="DF40HC(3.0)-100DS-0.4V",
                footprint_name="CM4_Connector_1",
                fields={"Mfr_Part_Number": "DF40HC(3.0)-100DS-0.4V(51)"},
            ),
            dict(
                reference="J8",
                value="DF40HC(3.0)-100DS-0.4V",
                footprint_name="CM4_Connector_2",
                fields={"Mfr_Part_Number": "DF40HC(3.0)-100DS-0.4V(51)"},
            ),
        ]
    )
    pm.generate_positions(str(tmp_path))
    pm.generate_bom(str(tmp_path), "proj")
    rows = read_csv_rows(tmp_path, "proj")
    assert len(rows) == 1
    assert rows[0]["Designator"] == "J4, J8"
    assert int(rows[0]["Quantity"]) == 2


def test_parts_without_mpn_merge_by_footprint_and_value(make_process_manager, tmp_path):
    """Without MPN the merge key falls back to footprint + value."""
    pm = make_process_manager(
        footprints=[
            dict(reference="C1", value="100nF"),
            dict(reference="C2", value="100nF"),
            dict(reference="C3", value="1uF"),
            dict(
                reference="L1",
                value="10uH",
                footprint_name="Inductor_SMD:L_0402_1005Metric",
            ),
        ]
    )
    pm.generate_positions(str(tmp_path))
    pm.generate_bom(str(tmp_path), "proj")
    rows = read_csv_rows(tmp_path, "proj")
    assert [r["Designator"] for r in rows] == ["C1, C2", "C3", "L1"]


def test_excluded_from_bom_not_in_bom(make_process_manager, tmp_path):
    pm = make_process_manager(
        footprints=[
            dict(reference="R1"),
            dict(reference="LOGO1", attributes=2),  # FP_EXCLUDE_FROM_BOM
        ]
    )
    pm.generate_positions(str(tmp_path))
    assert [b["Designator"] for b in pm.bom] == ["R1"]


def test_positions_file_only_contains_bom_designators(make_process_manager, tmp_path):
    """Components missing from the BOM are dropped from positions.csv too."""
    pm = make_process_manager(
        footprints=[
            dict(reference="R1"),
            dict(reference="LOGO1", attributes=2),  # in positions, not in BOM
        ]
    )
    pm.generate_positions(str(tmp_path))

    with open(tmp_path / "positions.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["Designator"] for r in rows] == ["R1"]
