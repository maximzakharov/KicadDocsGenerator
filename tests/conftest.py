"""
Pytest configuration.

The plugin runs inside KiCad's Python and imports `pcbnew` / `wx`, which do not
exist in the test environment. Mock modules are installed into sys.modules
before any `plugins.*` import so the modules under test can be imported and
their pure/testable logic exercised outside KiCad.

Tests that need real spreadsheet output (pandas + openpyxl + xlsxwriter) are
run with the dependencies from requirements-dev.txt.
"""

import sys
import types

import pytest


class _Placeholder:
    """Permissive stand-in for any wx/pcbnew class."""

    def __init__(self, *args, **kwargs):
        pass


class _WxMock(types.ModuleType):
    def __getattr__(self, name):
        cls = type(name, (_Placeholder,), {})
        setattr(self, name, cls)
        return cls


class _Angle:
    """Stand-in for pcbnew.EDA_ANGLE."""

    def __init__(self, degrees):
        self._degrees = degrees

    def AsDegrees(self):
        return self._degrees


class _PcbnewMock(types.ModuleType):
    # Realistic KiCad constants (values matter for layer dicts and bit flags).
    F_Cu = 0
    In1_Cu = 1
    In2_Cu = 2
    In3_Cu = 3
    In4_Cu = 4
    B_Cu = 31
    F_Paste = 33
    B_Paste = 34
    F_SilkS = 35
    B_SilkS = 36
    F_Mask = 37
    B_Mask = 38
    Edge_Cuts = 44
    Eco1_User = 45
    Eco2_User = 46
    FP_EXCLUDE_FROM_POS_FILES = 1
    FP_EXCLUDE_FROM_BOM = 2
    PCBNEW_LAYER_ID_START = 0
    PCB_LAYER_ID_COUNT = 32

    @staticmethod
    def FromMM(mm):
        return int(mm * 1000000)

    @staticmethod
    def IsCopperLayer(layer_id):
        return 0 <= layer_id < 32

    @staticmethod
    def Version():
        return "9.0"

    @staticmethod
    def GetBoard():
        raise AssertionError(
            "pcbnew.GetBoard() called in test: inject a FakeBoard instead"
        )

    def __getattr__(self, name):
        cls = type(name, (_Placeholder,), {})
        setattr(self, name, cls)
        return cls


sys.modules.setdefault("wx", _WxMock("wx"))
sys.modules.setdefault("pcbnew", _PcbnewMock("pcbnew"))

from plugins.process import ProcessManager  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes for board objects
# ---------------------------------------------------------------------------


class FakeDesignSettings:
    def __init__(self, aux_origin=(0, 0)):
        self._aux_origin = tuple(aux_origin)

    def GetAuxOrigin(self):
        return self._aux_origin


class FakeBoard:
    """Minimal pcbnew.BOARD fake for positions/BOM/stackup tests."""

    def __init__(self, footprints=(), aux_origin=(0, 0), file_name=None, legacy=False):
        self._footprints = list(footprints)
        self._design_settings = FakeDesignSettings(aux_origin)
        self._file_name = file_name or "/fake/project.kicad_pcb"
        if legacy:
            self.GetModules = self._get_modules  # KiCad <= 5 API
        else:
            self.GetFootprints = self._get_footprints

    def _get_footprints(self):
        return list(self._footprints)

    def _get_modules(self):
        return list(self._footprints)

    def GetDesignSettings(self):
        return self._design_settings

    def GetFileName(self):
        return self._file_name


class _FpId:
    def __init__(self, name):
        self._name = name

    def GetFootprintName(self):
        return self._name

    def GetLibItemName(self):
        return self._name


class FakeFootprint:
    """Minimal pcbnew.FOOTPRINT fake.

    `orientation` accepts degrees (float) for the modern EDA_ANGLE API.
    Pass `orientation_raw` (int, tenths of a degree) to exercise the legacy
    API without AsDegrees().

    `strict_fields=True` mimics KiCad >= 9: GetFieldText() raises for a
    missing field instead of returning an empty string.
    """

    def __init__(
        self,
        reference,
        value="",
        footprint_name="R_0603_1608Metric",
        layer=0,
        attributes=0,
        position=(0, 0),
        orientation=0.0,
        orientation_raw=None,
        fields=None,
        strict_fields=False,
    ):
        self._reference = reference
        self._value = value
        self._fp_id = _FpId(footprint_name)
        self._layer = layer
        self._attributes = attributes
        self._position = tuple(position)
        self._fields = dict(fields or {})
        if orientation_raw is not None:
            self._orientation = orientation_raw
        else:
            self._orientation = _Angle(orientation)

    def GetReference(self):
        return self._reference

    def GetValue(self):
        return self._value

    def GetFPID(self):
        return self._fp_id

    def GetLayer(self):
        return self._layer

    def GetAttributes(self):
        return self._attributes

    def GetPosition(self):
        return self._position

    def GetOrientation(self):
        return self._orientation

    def GetFieldText(self, key):
        if key not in self._fields:
            if self._strict_fields:
                raise LookupError(f"Field not found: {key}")
            return ""
        return self._fields[key]


@pytest.fixture
def make_process_manager(tmp_path):
    """Build a ProcessManager wired to a FakeBoard (skips pcbnew.GetBoard)."""

    def _make(footprints=(), aux_origin=(0, 0), legacy=False):
        # dict specs are accepted for brevity: dict(reference=..., fields=...)
        footprints = [
            FakeFootprint(**fp) if isinstance(fp, dict) else fp for fp in footprints
        ]
        board = FakeBoard(
            footprints=footprints,
            aux_origin=aux_origin,
            file_name=str(tmp_path / "project.kicad_pcb"),
            legacy=legacy,
        )
        manager = ProcessManager.__new__(ProcessManager)
        manager.board = board
        manager.bom = []
        manager.components = []
        return manager

    return _make
