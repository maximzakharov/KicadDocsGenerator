"""Tests for the footprint field getters and their fallback keys."""


class FakeFP:
    def __init__(self, fields):
        self.fields = fields

    def GetFieldText(self, key):
        return self.fields.get(key, "")

    def GetReference(self):
        return "R1"


def test_primary_key_wins(make_process_manager):
    pm = make_process_manager()
    fp = FakeFP({"LCSC_Part": "C111", "LCSC": "C222"})
    assert pm._get_lcsc_pn_from_footprint(fp) == "C111"


def test_lcsc_fallback_keys(make_process_manager):
    pm = make_process_manager()
    assert pm._get_lcsc_pn_from_footprint(FakeFP({"MPN": "C333"})) == "C333"
    assert pm._get_lcsc_pn_from_footprint(FakeFP({"mpn": "C334"})) == "C334"
    assert pm._get_lcsc_pn_from_footprint(FakeFP({})) == ""


def test_simple_field_getters(make_process_manager):
    pm = make_process_manager()
    fp = FakeFP(
        {
            "Mfr_Name": "Yageo",
            "Mfr_Part_Number": "RC0603FR-0710KL",
            "Link": "https://example.com",
            "Unit price": "0.12",
        }
    )
    assert pm._get_mfr_name_from_footprint(fp) == "Yageo"
    assert pm._get_mfr_pn_from_footprint(fp) == "RC0603FR-0710KL"
    assert pm._get_link_from_footprint(fp) == "https://example.com"
    assert pm._get_unit_price_from_footprint(fp) == "0.12"


def test_empty_field_falls_through_to_fallback(make_process_manager):
    pm = make_process_manager()
    fp = FakeFP({"JLCPCB Rotation Offset": "", "JLCRotOffset": "270"})
    assert pm._get_rotation_offset_from_footprint(fp) == 270.0


def test_rotation_offset(make_process_manager):
    pm = make_process_manager()
    assert pm._get_rotation_offset_from_footprint(FakeFP({})) == 0
    assert (
        pm._get_rotation_offset_from_footprint(FakeFP({"JlcRotOffset": "90"})) == 90.0
    )
    assert (
        pm._get_rotation_offset_from_footprint(
            FakeFP({"JLCPCB Rotation Offset": "-45"})
        )
        == -45.0
    )


def test_rotation_offset_invalid_raises(make_process_manager):
    pm = make_process_manager()
    try:
        pm._get_rotation_offset_from_footprint(
            FakeFP({"JLCPCB Rotation Offset": "abc"})
        )
    except RuntimeError as e:
        assert "R1" in str(e)  # message names the offending reference
    else:
        raise AssertionError("expected RuntimeError")


def test_position_offset(make_process_manager):
    pm = make_process_manager()
    assert pm._get_position_offset_from_footprint(FakeFP({})) == (0, 0)
    assert pm._get_position_offset_from_footprint(
        FakeFP({"JlcPosOffset": "1.5,-2"})
    ) == (1.5, -2.0)


def test_position_offset_invalid_raises(make_process_manager):
    pm = make_process_manager()
    for bad in ("1,x", "abc"):
        try:
            pm._get_position_offset_from_footprint(
                FakeFP({"JLCPCB Position Offset": bad})
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"expected RuntimeError for {bad!r}")


class StrictFakeFP:
    """Mimics KiCad >= 9: GetFieldText raises for a missing field."""

    def __init__(self, fields):
        self.fields = fields

    def GetFieldText(self, key):
        if key not in self.fields:
            raise LookupError(f"Field not found: {key}")
        return self.fields[key]

    def GetReference(self):
        return "R1"


def test_kicad9_missing_field_raises_instead_of_empty(make_process_manager):
    """Regression: KiCad >= 9 raises 'Field not found: ...' for absent fields.

    The getters must swallow that and fall through to the next key instead
    of aborting the whole generation.
    """
    pm = make_process_manager()
    fp = StrictFakeFP({})  # no fields at all
    assert pm._get_rotation_offset_from_footprint(fp) == 0
    assert pm._get_position_offset_from_footprint(fp) == (0, 0)
    assert pm._get_lcsc_pn_from_footprint(fp) == ""
    assert pm._get_mfr_pn_from_footprint(fp) == ""


def test_kicad9_fallback_key_reached_through_exception(make_process_manager):
    pm = make_process_manager()
    fp = StrictFakeFP({"JLCRotOffset": "270"})  # primary key missing
    assert pm._get_rotation_offset_from_footprint(fp) == 270.0
    fp = StrictFakeFP({"MPN": "C123"})
    assert pm._get_lcsc_pn_from_footprint(fp) == "C123"
