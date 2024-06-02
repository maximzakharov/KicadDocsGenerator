import pcbnew
import wx
import os

from .thread import ProcessThread
from .events import StatusEvent


class ProgressDialog(wx.Frame):
    def __init__(self):
        wx.Dialog.__init__(
            self,
            None,
            id=wx.ID_ANY,
            title="Processing...",
            pos=wx.DefaultPosition,
            size=wx.DefaultSize,
            style=wx.DEFAULT_DIALOG_STYLE,
        )

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        bSizer1 = wx.BoxSizer(wx.VERTICAL)
        self.m_gaugeStatus = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size(300, 20), wx.GA_HORIZONTAL)
        self.m_gaugeStatus.SetValue(0)
        bSizer1.Add(self.m_gaugeStatus, 0, wx.ALL, 5)
        self.SetSizer(bSizer1)
        self.Layout()
        bSizer1.Fit(self)
        self.Centre(wx.BOTH)
        StatusEvent.invoke(self, self.updateDisplay)
        ProcessThread(self)

    def updateDisplay(self, status):
        if status.data == -1:
            pcbnew.Refresh()
            self.Destroy()
        else:
            self.m_gaugeStatus.SetValue(int(status.data))


class Plugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "KicadDocsGenerator"
        self.category = "Manufacturing"
        self.description = (
            "This plugin automates the creation of all essential documentation required for PCB manufacturing."
        )
        self.pcbnew_icon_support = hasattr(self, "show_toolbar_button")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")
        self.dark_icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")

    def Run(self):
        try:
            ProgressDialog().Show()
        except Exception as e:
            wx.MessageBox("Error: " + str(e))
