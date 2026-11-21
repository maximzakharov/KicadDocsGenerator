import importlib

MODULES = [
    "plugins",
    "plugins.config",
    "plugins.events",
    "plugins.logs",
    "plugins.plot",
    "plugins.process",
    "plugins.thread",
    "plugins.plugin",
]


def test_plugin_modules_import_outside_kicad():
    """With mocked pcbnew/wx (see conftest) every module must import cleanly.

    plugins/__init__.py swallows import errors behind a wx.MessageBox call,
    so each submodule is imported explicitly here to surface failures.
    """
    for name in MODULES:
        importlib.import_module(name)
