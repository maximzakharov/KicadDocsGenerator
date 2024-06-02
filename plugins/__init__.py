import wx

try:
    from .plugin import Plugin

    plugin = Plugin()
    plugin.register()
except Exception as e:
    wx.MessageBox("Error: " + str(e))
