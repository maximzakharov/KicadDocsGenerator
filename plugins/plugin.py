import logging
import os

import pcbnew
import wx

from .events import StatusEvent
from .logs import setup_logging
from .thread import ProcessThread


class ProgressDialog(wx.Frame):
    def __init__(self):
        logging.info("Initializing progress dialog...")

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
        self.m_gaugeStatus = wx.Gauge(
            self, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size(300, 20), wx.GA_HORIZONTAL
        )
        self.m_gaugeStatus.SetValue(0)
        bSizer1.Add(self.m_gaugeStatus, 0, wx.ALL, 5)
        self.SetSizer(bSizer1)
        self.Layout()
        bSizer1.Fit(self)
        self.Centre(wx.BOTH)
        logging.info("Starting process thread...")
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
        setup_logging()
        self.name = "KicadDocsGenerator"
        self.category = "Manufacturing"
        self.description = "This plugin automates the creation of all essential documentation required for PCB manufacturing."
        self.pcbnew_icon_support = hasattr(self, "show_toolbar_button")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")
        self.dark_icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")

    def Run(self):
        logging.info("KicadDocsGenerator plugin started")
        try:
            ProgressDialog().Show()
            logging.info("Progress dialog displayed successfully")
        except Exception as e:
            logging.error(f"Error running plugin: {str(e)}")
            wx.MessageBox("Error: " + str(e))
