"""Tests for stackup parsing (.kicad_pcb s-expression) and XLSX report."""

import pytest

pd = pytest.importorskip("pandas")

BOARD_WITH_STACKUP = """\
(kicad_pcb
  (version 20221018)
  (setup
    (stackup
      (layer (name "F.Cu") (type "copper") (thickness 0.035))
      (layer (name "dielectric 1") (type "core") (material "FR4")
             (thickness 1.51) (color "#4D4D4D"))
      (layer (name "B.Cu") (type "copper") (thickness 0.035))
    )
    (pad_to_mask_clearance 0)
  )
)
"""


def test_get_stackup_info_parses_layers(make_process_manager, tmp_path):
    board_file = tmp_path / "project.kicad_pcb"
    board_file.write_text(BOARD_WITH_STACKUP)

    pm = make_process_manager()
    layers = pm.get_stackup_info(str(board_file))

    assert len(layers) == 3
    assert layers[0] == {
        "Layer": 1,
        "Name": "copper",
        "Material": None,
        "Thickness": 0.035,
        "Color": None,
    }
    assert layers[1]["Material"] == "FR4"
    assert layers[1]["Color"] == "#4D4D4D"
    assert layers[1]["Thickness"] == 1.51
    assert layers[2]["Layer"] == 3


def test_stackup_xlsx_report(make_process_manager, tmp_path):
    board_file = tmp_path / "project.kicad_pcb"
    board_file.write_text(BOARD_WITH_STACKUP)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    pm = make_process_manager()
    pm.genarate_stackup_info(str(out_dir), str(board_file), "proj")

    xlsx = out_dir / "proj.xlsx"
    assert xlsx.exists()
    df = pd.read_excel(xlsx, sheet_name="Stackup")
    assert list(df.columns) == ["Layer", "Name", "Material", "Thickness", "Color"]
    assert len(df) == 3


def test_missing_stackup_raises(make_process_manager, tmp_path):
    board_file = tmp_path / "project.kicad_pcb"
    board_file.write_text("(kicad_pcb (version 20221018))\n")

    pm = make_process_manager()
    with pytest.raises(RuntimeError, match="stack"):
        pm.genarate_stackup_info(str(tmp_path), str(board_file), "proj")
