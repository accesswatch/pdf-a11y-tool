"""Accessibility findings list panel.

This panel shows the results of the most recent accessibility check run,
listing each Finding with its severity, rule ID, WCAG criterion,
description, and page reference. Double-clicking an issue navigates to the
offending element in the Tag Tree and Page View.

Public API
----------
IssuesPanel      -- wx.Panel subclass wrapping a wx.ListCtrl populated
                    from a list[Finding]. Supports sorting by column,
                    filtering by severity, and text search.
"""
from __future__ import annotations

import webbrowser

import wx
import wx.lib.newevent

from pdf_a11y.core.validator import Finding

# Custom event fired when user activates a finding row.
FindingSelectedEvent, EVT_FINDING_SELECTED = wx.lib.newevent.NewEvent()

# WCAG quick reference base URL.
_WCAG_BASE = "https://www.w3.org/WAI/WCAG22/quickref/#"

# Map WCAG SC number to quick-reference anchor fragment.
_WCAG_ANCHORS: dict[str, str] = {
    "1.1.1": "non-text-content",
    "1.3.1": "info-and-relationships",
    "1.3.2": "meaningful-sequence",
    "1.4.3": "contrast-minimum",
    "2.4.1": "bypass-blocks",
    "2.4.2": "page-titled",
    "2.4.4": "link-purpose-in-context",
    "2.4.6": "headings-and-labels",
    "3.1.1": "language-of-page",
    "4.1.2": "name-role-value",
}

# Severity display order for sorting.
_SEVERITY_ORDER: dict[str, int] = {"error": 0, "warning": 1, "tip": 2}


class _FindingsListCtrl(wx.ListCtrl):
    """Virtual list control that reads data from a findings list."""

    def __init__(self, parent: wx.Window, **kwargs: object) -> None:
        super().__init__(parent, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL, **kwargs)
        self.findings: list[Finding] = []

    def OnGetItemText(self, index: int, col: int) -> str:
        if index < 0 or index >= len(self.findings):
            return ""
        f = self.findings[index]
        if col == 0:
            return f.severity.capitalize()
        elif col == 1:
            return f.rule_id
        elif col == 2:
            return f.wcag
        elif col == 3:
            return f.description
        elif col == 4:
            return str(f.page) if f.page is not None else ""
        elif col == 5:
            return f.element or ""
        return ""


class IssuesPanel(wx.Panel):
    """Panel that displays accessibility findings in a sortable list.

    Binds :data:`EVT_FINDING_SELECTED` when a user activates a row.
    The event carries ``finding`` (a :class:`Finding` instance).
    """

    def __init__(self, parent: wx.Window, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self.SetName("Issues panel")

        self._findings: list[Finding] = []
        self._filtered: list[Finding] = []
        self._sort_col: int = 0
        self._sort_ascending: bool = True

        self._build_ui()
        self._bind_events()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Filter bar
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)

        sev_label = wx.StaticText(self, label="Severity:")
        sev_label.SetName("Severity filter label")
        self._severity_choice = wx.Choice(
            self, choices=["All", "Errors", "Warnings", "Tips"]
        )
        self._severity_choice.SetSelection(0)
        self._severity_choice.SetName("Severity filter")
        self._severity_choice.SetToolTip("Filter findings by severity level")

        search_label = wx.StaticText(self, label="Search:")
        search_label.SetName("Search filter label")
        self._search_ctrl = wx.TextCtrl(
            self, style=wx.TE_PROCESS_ENTER, size=(200, -1)
        )
        self._search_ctrl.SetName("Search findings")
        self._search_ctrl.SetToolTip("Type to filter findings by text")

        filter_sizer.Add(sev_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        filter_sizer.Add(self._severity_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        filter_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        filter_sizer.Add(self._search_ctrl, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(filter_sizer, 0, wx.EXPAND | wx.ALL, 4)

        # List
        self._list = _FindingsListCtrl(self)
        self._list.SetName("Accessibility issues list")
        self._list.InsertColumn(0, "Severity", width=80)
        self._list.InsertColumn(1, "Rule ID", width=120)
        self._list.InsertColumn(2, "WCAG", width=70)
        self._list.InsertColumn(3, "Description", width=350)
        self._list.InsertColumn(4, "Page", width=50)
        self._list.InsertColumn(5, "Element", width=120)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 4)

        # Status line
        self._status = wx.StaticText(self, label="No findings.")
        self._status.SetName("Issues status")
        sizer.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 4)

        self.SetSizer(sizer)

    def _bind_events(self) -> None:
        self._severity_choice.Bind(wx.EVT_CHOICE, self._on_filter_changed)
        self._search_ctrl.Bind(wx.EVT_TEXT, self._on_filter_changed)
        self._search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_filter_changed)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._list.Bind(wx.EVT_LIST_COL_CLICK, self._on_col_click)
        self._list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._on_context_menu)

        # Virtual list callbacks
        self._list.Bind(wx.EVT_LIST_CACHE_HINT, lambda e: None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_findings(self, findings: list[Finding]) -> None:
        """Replace the displayed findings and refresh the list."""
        self._findings = list(findings)
        self._apply_filter()

    def clear(self) -> None:
        """Remove all findings."""
        self._findings = []
        self._filtered = []
        self._list.findings = []
        self._list.SetItemCount(0)
        self._list.Refresh()
        self._update_status()

    def get_findings(self) -> list[Finding]:
        """Return the currently displayed (filtered) findings."""
        return list(self._filtered)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filter(self) -> None:
        severity_sel = self._severity_choice.GetSelection()
        severity_map = {0: None, 1: "error", 2: "warning", 3: "tip"}
        severity_filter = severity_map.get(severity_sel)

        search_text = self._search_ctrl.GetValue().strip().lower()

        filtered = self._findings
        if severity_filter:
            filtered = [f for f in filtered if f.severity == severity_filter]
        if search_text:
            filtered = [
                f
                for f in filtered
                if search_text in f.description.lower()
                or search_text in f.rule_id.lower()
                or search_text in f.wcag.lower()
                or search_text in (f.element or "").lower()
            ]

        self._filtered = filtered
        self._sort_findings()
        self._list.findings = self._filtered
        self._list.SetItemCount(len(self._filtered))
        self._list.Refresh()
        self._update_status()

    def _on_filter_changed(self, _event: wx.CommandEvent) -> None:
        self._apply_filter()

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def _sort_findings(self) -> None:
        reverse = not self._sort_ascending

        def key_fn(f: Finding) -> object:
            if self._sort_col == 0:
                return _SEVERITY_ORDER.get(f.severity, 9)
            elif self._sort_col == 1:
                return f.rule_id
            elif self._sort_col == 2:
                return f.wcag
            elif self._sort_col == 3:
                return f.description.lower()
            elif self._sort_col == 4:
                return f.page if f.page is not None else 0
            elif self._sort_col == 5:
                return (f.element or "").lower()
            return ""

        self._filtered.sort(key=key_fn, reverse=reverse)

    def _on_col_click(self, event: wx.ListEvent) -> None:
        col = event.GetColumn()
        if col == self._sort_col:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_col = col
            self._sort_ascending = True
        self._sort_findings()
        self._list.Refresh()

    # ------------------------------------------------------------------
    # Row activation
    # ------------------------------------------------------------------

    def _on_activate(self, event: wx.ListEvent) -> None:
        idx = event.GetIndex()
        if 0 <= idx < len(self._filtered):
            finding = self._filtered[idx]
            evt = FindingSelectedEvent(finding=finding)
            wx.PostEvent(self, evt)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _on_context_menu(self, event: wx.ListEvent) -> None:
        idx = event.GetIndex()
        if idx < 0 or idx >= len(self._filtered):
            return
        self._context_finding = self._filtered[idx]

        menu = wx.Menu()
        go_item = menu.Append(wx.ID_ANY, "Go to Element")
        learn_item = menu.Append(wx.ID_ANY, "Learn More (WCAG)")

        self.Bind(wx.EVT_MENU, self._on_go_to_element, go_item)
        self.Bind(wx.EVT_MENU, self._on_learn_more, learn_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def _on_go_to_element(self, _event: wx.CommandEvent) -> None:
        if hasattr(self, "_context_finding"):
            evt = FindingSelectedEvent(finding=self._context_finding)
            wx.PostEvent(self, evt)

    def _on_learn_more(self, _event: wx.CommandEvent) -> None:
        if hasattr(self, "_context_finding"):
            wcag = self._context_finding.wcag
            anchor = _WCAG_ANCHORS.get(wcag, "")
            if anchor:
                webbrowser.open(_WCAG_BASE + anchor)

    # ------------------------------------------------------------------
    # Status line
    # ------------------------------------------------------------------

    def _update_status(self) -> None:
        if not self._filtered:
            self._status.SetLabel("No findings.")
            return
        errors = sum(1 for f in self._filtered if f.severity == "error")
        warnings = sum(1 for f in self._filtered if f.severity == "warning")
        tips = sum(1 for f in self._filtered if f.severity == "tip")
        total = len(self._filtered)
        self._status.SetLabel(
            f"{errors} errors, {warnings} warnings, {tips} tips ({total} total)"
        )
