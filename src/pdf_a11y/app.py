"""wx.App subclass and application startup logic."""
from __future__ import annotations

import wx

from pdf_a11y.ui.main_frame import MainFrame


class PdfA11yApp(wx.App):
    def OnInit(self) -> bool:
        self.frame = MainFrame(None)
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True


def main() -> None:
    app = PdfA11yApp()
    app.MainLoop()
