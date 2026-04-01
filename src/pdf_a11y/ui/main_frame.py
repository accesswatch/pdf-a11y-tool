"""Main application window with AUI dockable panel layout."""
from __future__ import annotations

import wx
import wx.aui
import wx.lib.newevent

from pdf_a11y.core.document import PdfDocument, EVT_DOC_CHANGED, EVT_DOC_CLOSED
from pdf_a11y.core.renderer import PageRenderer

# ---------------------------------------------------------------------------
# Panel IDs
# ---------------------------------------------------------------------------
ID_PANEL_TAG_TREE = wx.NewIdRef()
ID_PANEL_PAGE_VIEW = wx.NewIdRef()
ID_PANEL_READING_ORDER = wx.NewIdRef()
ID_PANEL_PROPERTIES = wx.NewIdRef()
ID_PANEL_ISSUES = wx.NewIdRef()
ID_PANEL_FIELDS = wx.NewIdRef()
ID_PANEL_ALT_TEXT = wx.NewIdRef()
ID_PANEL_TABLES = wx.NewIdRef()
ID_PANEL_SR_PREVIEW = wx.NewIdRef()

# ---------------------------------------------------------------------------
# Menu IDs
# ---------------------------------------------------------------------------
ID_FILE_NEW = wx.NewIdRef()
ID_FILE_OPEN = wx.NewIdRef()
ID_FILE_SAVE = wx.NewIdRef()
ID_FILE_SAVE_AS = wx.NewIdRef()

ID_EDIT_UNDO = wx.NewIdRef()
ID_EDIT_REDO = wx.NewIdRef()
ID_EDIT_PREFERENCES = wx.NewIdRef()

ID_VIEW_TOGGLE_TAGTREE = wx.NewIdRef()
ID_VIEW_TOGGLE_READINGORDER = wx.NewIdRef()
ID_VIEW_TOGGLE_ISSUES = wx.NewIdRef()
ID_VIEW_TOGGLE_FIELDS = wx.NewIdRef()
ID_VIEW_TOGGLE_ALTTEXT = wx.NewIdRef()
ID_VIEW_TOGGLE_TABLES = wx.NewIdRef()
ID_VIEW_TOGGLE_SRPREVIEW = wx.NewIdRef()
ID_VIEW_READING_ORDER_OVERLAY = wx.NewIdRef()
ID_VIEW_SR_PREVIEW = wx.NewIdRef()
ID_VIEW_ZOOM_IN = wx.NewIdRef()
ID_VIEW_ZOOM_OUT = wx.NewIdRef()
ID_VIEW_FIT_PAGE = wx.NewIdRef()

ID_CHECK_RUN_FULL = wx.NewIdRef()
ID_CHECK_RUN_BUILTIN = wx.NewIdRef()
ID_CHECK_RUN_VERAPDF = wx.NewIdRef()
ID_CHECK_EXPORT_REPORT = wx.NewIdRef()

ID_TAGS_CHANGE_TYPE = wx.NewIdRef()
ID_TAGS_ADD_CHILD = wx.NewIdRef()
ID_TAGS_DELETE = wx.NewIdRef()
ID_TAGS_SET_ALT_TEXT = wx.NewIdRef()
ID_TAGS_SET_LANGUAGE = wx.NewIdRef()
ID_TAGS_AUTO_TAG = wx.NewIdRef()

ID_FORMS_ADD_TEXT = wx.NewIdRef()
ID_FORMS_ADD_CHECKBOX = wx.NewIdRef()
ID_FORMS_ADD_RADIO = wx.NewIdRef()
ID_FORMS_ADD_DROPDOWN = wx.NewIdRef()
ID_FORMS_ADD_BUTTON = wx.NewIdRef()
ID_FORMS_FIELD_PROPS = wx.NewIdRef()

ID_TOOLS_GEN_BOOKMARKS = wx.NewIdRef()
ID_TOOLS_SET_TITLE = wx.NewIdRef()
ID_TOOLS_SET_LANGUAGE = wx.NewIdRef()
ID_TOOLS_VERAPDF_SETUP = wx.NewIdRef()

ID_HELP_SHORTCUTS = wx.NewIdRef()
ID_HELP_USER_GUIDE = wx.NewIdRef()
ID_HELP_ABOUT = wx.NewIdRef()

# Toolbar zoom control
ID_TOOLBAR_ZOOM = wx.NewIdRef()


class MainFrame(wx.Frame):
    """Main application window."""

    _ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    _ZOOM_LABELS = ["50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%"]

    def __init__(self, parent: wx.Window | None) -> None:
        super().__init__(
            parent,
            title="PDF Accessibility Tool",
            size=(1280, 800),
        )
        self.SetName("PDF Accessibility Tool main window")

        self._document = PdfDocument()
        self._document.event_sink = self
        self._renderer = PageRenderer()
        self._current_zoom: float = 1.0
        self._current_page: int = 0
        # Track which panel has focus for F6 cycling
        self._focus_panels: list[wx.Window] = []

        self._build_menu_bar()
        self._build_toolbar()
        self._build_status_bar()
        self._build_aui_panels()

        self.Bind(EVT_DOC_CHANGED, self._on_doc_changed)
        self.Bind(EVT_DOC_CLOSED, self._on_doc_closed)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

        self._update_title()
        self._update_toolbar_state()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menubar = wx.MenuBar()

        # --- File ---
        file_menu = wx.Menu()
        file_menu.Append(ID_FILE_NEW, "&New Blank PDF\tCtrl+N", "Create a new blank tagged PDF")
        file_menu.Append(ID_FILE_OPEN, "&Open...\tCtrl+O", "Open an existing PDF file")
        file_menu.Append(ID_FILE_SAVE, "&Save\tCtrl+S", "Save the current file")
        file_menu.Append(ID_FILE_SAVE_AS, "Save &As...\tCtrl+Shift+S", "Save to a new file")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "E&xit\tAlt+F4", "Exit the application")
        menubar.Append(file_menu, "&File")

        self.Bind(wx.EVT_MENU, self._on_file_new, id=ID_FILE_NEW)
        self.Bind(wx.EVT_MENU, self._on_file_open, id=ID_FILE_OPEN)
        self.Bind(wx.EVT_MENU, self._on_file_save, id=ID_FILE_SAVE)
        self.Bind(wx.EVT_MENU, self._on_file_save_as, id=ID_FILE_SAVE_AS)
        self.Bind(wx.EVT_MENU, self._on_exit, id=wx.ID_EXIT)

        # --- Edit ---
        edit_menu = wx.Menu()
        edit_menu.Append(ID_EDIT_UNDO, "&Undo\tCtrl+Z", "Undo the last action")
        edit_menu.Append(ID_EDIT_REDO, "&Redo\tCtrl+Y", "Redo the last undone action")
        edit_menu.AppendSeparator()
        edit_menu.Append(ID_EDIT_PREFERENCES, "&Preferences...", "Open preferences dialog")
        menubar.Append(edit_menu, "&Edit")

        self.Bind(wx.EVT_MENU, self._on_undo, id=ID_EDIT_UNDO)
        self.Bind(wx.EVT_MENU, self._on_redo, id=ID_EDIT_REDO)
        self.Bind(wx.EVT_MENU, self._on_preferences, id=ID_EDIT_PREFERENCES)

        # --- View ---
        view_menu = wx.Menu()
        panels_submenu = wx.Menu()
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_TAGTREE, "&Tag Tree", "Show/hide the tag tree panel"
        )
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_READINGORDER, "&Reading Order", "Show/hide the reading order panel"
        )
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_ISSUES, "&Issues", "Show/hide the issues panel"
        )
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_FIELDS, "&Fields", "Show/hide the fields panel"
        )
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_ALTTEXT, "&Alt Text", "Show/hide the alt text panel"
        )
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_TABLES, "&Tables", "Show/hide the tables panel"
        )
        panels_submenu.AppendCheckItem(
            ID_VIEW_TOGGLE_SRPREVIEW, "&SR Preview", "Show/hide the screen reader preview panel"
        )
        view_menu.AppendSubMenu(panels_submenu, "&Panels", "Show or hide panels")
        view_menu.AppendSeparator()
        view_menu.AppendCheckItem(
            ID_VIEW_READING_ORDER_OVERLAY,
            "Reading &Order Overlay\tCtrl+Shift+O",
            "Toggle reading order overlay on the page view",
        )
        view_menu.Append(
            ID_VIEW_SR_PREVIEW,
            "&Screen Reader Preview\tCtrl+Shift+R",
            "Switch to the screen reader preview panel",
        )
        view_menu.AppendSeparator()
        view_menu.Append(ID_VIEW_ZOOM_IN, "Zoom &In\tCtrl+=", "Increase zoom level")
        view_menu.Append(ID_VIEW_ZOOM_OUT, "Zoom &Out\tCtrl+-", "Decrease zoom level")
        view_menu.Append(ID_VIEW_FIT_PAGE, "&Fit Page\tCtrl+0", "Fit the page to the window")
        menubar.Append(view_menu, "&View")

        self.Bind(wx.EVT_MENU, self._on_zoom_in, id=ID_VIEW_ZOOM_IN)
        self.Bind(wx.EVT_MENU, self._on_zoom_out, id=ID_VIEW_ZOOM_OUT)
        self.Bind(wx.EVT_MENU, self._on_fit_page, id=ID_VIEW_FIT_PAGE)

        # --- Check ---
        check_menu = wx.Menu()
        check_menu.Append(ID_CHECK_RUN_FULL, "Run &Full Check\tF5", "Run all accessibility checks")
        check_menu.Append(
            ID_CHECK_RUN_BUILTIN, "Run &Built-in Checks Only", "Run built-in checks without veraPDF"
        )
        check_menu.Append(
            ID_CHECK_RUN_VERAPDF, "Run &veraPDF Only", "Run veraPDF checks only"
        )
        check_menu.AppendSeparator()
        check_menu.Append(
            ID_CHECK_EXPORT_REPORT, "&Export Report...", "Export findings as Markdown or CSV"
        )
        menubar.Append(check_menu, "&Check")

        self.Bind(wx.EVT_MENU, self._on_check_full, id=ID_CHECK_RUN_FULL)
        self.Bind(wx.EVT_MENU, self._on_check_builtin, id=ID_CHECK_RUN_BUILTIN)
        self.Bind(wx.EVT_MENU, self._on_check_verapdf, id=ID_CHECK_RUN_VERAPDF)
        self.Bind(wx.EVT_MENU, self._on_export_report, id=ID_CHECK_EXPORT_REPORT)

        # --- Tags ---
        tags_menu = wx.Menu()
        tags_menu.Append(
            ID_TAGS_CHANGE_TYPE, "&Change Type...", "Change the tag type of the selected element"
        )
        tags_menu.Append(
            ID_TAGS_ADD_CHILD, "&Add Child Element...", "Add a new child element"
        )
        tags_menu.Append(ID_TAGS_DELETE, "&Delete Element", "Delete the selected element")
        tags_menu.AppendSeparator()
        tags_menu.Append(
            ID_TAGS_SET_ALT_TEXT,
            "Set &Alt Text...\tCtrl+Alt+A",
            "Set alternative text on the selected element",
        )
        tags_menu.Append(
            ID_TAGS_SET_LANGUAGE,
            "Set &Language...\tCtrl+Alt+L",
            "Set language on the selected element",
        )
        tags_menu.AppendSeparator()
        tags_menu.Append(ID_TAGS_AUTO_TAG, "A&uto-Tag Document...", "Launch the auto-tagger wizard")
        menubar.Append(tags_menu, "&Tags")

        # --- Forms ---
        forms_menu = wx.Menu()
        forms_menu.Append(ID_FORMS_ADD_TEXT, "Add &Text Field...", "Add a new text field")
        forms_menu.Append(ID_FORMS_ADD_CHECKBOX, "Add &Checkbox...", "Add a new checkbox")
        forms_menu.Append(
            ID_FORMS_ADD_RADIO, "Add &Radio Group...", "Add a new radio button group"
        )
        forms_menu.Append(ID_FORMS_ADD_DROPDOWN, "Add &Dropdown...", "Add a new dropdown list")
        forms_menu.Append(ID_FORMS_ADD_BUTTON, "Add &Button...", "Add a new push button")
        forms_menu.AppendSeparator()
        forms_menu.Append(
            ID_FORMS_FIELD_PROPS, "Field &Properties...", "Edit properties of the selected field"
        )
        menubar.Append(forms_menu, "&Forms")

        # --- Tools ---
        tools_menu = wx.Menu()
        tools_menu.Append(
            ID_TOOLS_GEN_BOOKMARKS,
            "&Generate Bookmarks from Headings",
            "Generate bookmarks/outlines from heading structure",
        )
        tools_menu.Append(
            ID_TOOLS_SET_TITLE, "Set Document &Title...", "Set or edit the document title"
        )
        tools_menu.Append(
            ID_TOOLS_SET_LANGUAGE,
            "Set Document &Language...",
            "Set the document language (BCP 47)",
        )
        tools_menu.AppendSeparator()
        tools_menu.Append(
            ID_TOOLS_VERAPDF_SETUP, "veraPDF &Setup...", "Configure veraPDF integration"
        )
        menubar.Append(tools_menu, "&Tools")

        # --- Help ---
        help_menu = wx.Menu()
        help_menu.Append(
            ID_HELP_SHORTCUTS, "&Keyboard Shortcuts\tCtrl+/", "View keyboard shortcuts"
        )
        help_menu.Append(ID_HELP_USER_GUIDE, "&User Guide", "Open the user guide")
        help_menu.AppendSeparator()
        help_menu.Append(ID_HELP_ABOUT, "&About", "About PDF Accessibility Tool")
        menubar.Append(help_menu, "&Help")

        self.Bind(wx.EVT_MENU, self._on_help_shortcuts, id=ID_HELP_SHORTCUTS)
        self.Bind(wx.EVT_MENU, self._on_about, id=ID_HELP_ABOUT)

        self.SetMenuBar(menubar)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = self.CreateToolBar(wx.TB_HORIZONTAL | wx.TB_TEXT | wx.NO_BORDER)
        tb.SetName("Main toolbar")

        icon_size = (24, 24)

        def _tool(id: int, label: str, tooltip: str) -> None:
            bmp = wx.ArtProvider.GetBitmap(wx.ART_MISSING_IMAGE, wx.ART_TOOLBAR, icon_size)
            tb.AddTool(id, label, bmp, tooltip)

        _tool(ID_FILE_OPEN, "Open", "Open PDF file (Ctrl+O)")
        _tool(ID_FILE_SAVE, "Save", "Save file (Ctrl+S)")
        tb.AddSeparator()
        _tool(ID_EDIT_UNDO, "Undo", "Undo last action (Ctrl+Z)")
        _tool(ID_EDIT_REDO, "Redo", "Redo last action (Ctrl+Y)")
        tb.AddSeparator()
        _tool(ID_CHECK_RUN_FULL, "Check", "Run accessibility check (F5)")
        tb.AddSeparator()

        # Zoom control
        zoom_label = wx.StaticText(tb, label="Zoom:")
        zoom_label.SetName("Zoom level label")
        tb.AddControl(zoom_label)

        self._zoom_combo = wx.ComboBox(
            tb,
            id=ID_TOOLBAR_ZOOM,
            value="100%",
            choices=self._ZOOM_LABELS,
            style=wx.CB_DROPDOWN,
            size=(80, -1),
        )
        self._zoom_combo.SetName("Zoom level selector")
        self._zoom_combo.SetToolTip("Select zoom level")
        tb.AddControl(self._zoom_combo)

        tb.Bind(wx.EVT_MENU, self._on_file_open, id=ID_FILE_OPEN)
        tb.Bind(wx.EVT_MENU, self._on_file_save, id=ID_FILE_SAVE)
        tb.Bind(wx.EVT_MENU, self._on_undo, id=ID_EDIT_UNDO)
        tb.Bind(wx.EVT_MENU, self._on_redo, id=ID_EDIT_REDO)
        tb.Bind(wx.EVT_MENU, self._on_check_full, id=ID_CHECK_RUN_FULL)
        self._zoom_combo.Bind(wx.EVT_COMBOBOX, self._on_zoom_combo)
        self._zoom_combo.Bind(wx.EVT_TEXT_ENTER, self._on_zoom_combo)

        tb.Realize()
        self._toolbar = tb

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        sb = self.CreateStatusBar(3)
        sb.SetName("Application status bar")
        sb.SetStatusWidths([-1, 200, 120])
        sb.SetStatusText(
            "Open a PDF file to begin (Ctrl+O) or create a new blank PDF (Ctrl+N)", 0
        )
        sb.SetStatusText("", 1)
        sb.SetStatusText("Zoom: 100%", 2)
        self._statusbar = sb

    # ------------------------------------------------------------------
    # AUI panel layout
    # ------------------------------------------------------------------

    def _build_aui_panels(self) -> None:
        self._aui_mgr = wx.aui.AuiManager(self)
        self._aui_mgr.SetManagedWindow(self)

        # Central page view panel
        self._page_panel = self._make_page_view_panel()
        self._aui_mgr.AddPane(
            self._page_panel,
            wx.aui.AuiPaneInfo()
            .Name("page_view")
            .Caption("Page View")
            .CenterPane()
            .MinSize(400, 300),
        )

        # Left: Tag Tree panel
        self._tag_tree_panel = self._make_tag_tree_panel()
        self._aui_mgr.AddPane(
            self._tag_tree_panel,
            wx.aui.AuiPaneInfo()
            .Name("tag_tree")
            .Caption("Tag Tree")
            .Left()
            .Layer(1)
            .BestSize(300, 400)
            .MinSize(200, 200)
            .CloseButton(True)
            .PinButton(True),
        )

        # Left: Reading Order panel (below tag tree)
        self._reading_order_panel = self._make_reading_order_panel()
        self._aui_mgr.AddPane(
            self._reading_order_panel,
            wx.aui.AuiPaneInfo()
            .Name("reading_order")
            .Caption("Reading Order")
            .Left()
            .Layer(1)
            .BestSize(300, 250)
            .MinSize(200, 150)
            .CloseButton(True)
            .PinButton(True),
        )

        # Right: Properties panel
        self._properties_panel = self._make_properties_panel()
        self._aui_mgr.AddPane(
            self._properties_panel,
            wx.aui.AuiPaneInfo()
            .Name("properties")
            .Caption("Properties")
            .Right()
            .Layer(1)
            .BestSize(280, 400)
            .MinSize(200, 200)
            .CloseButton(True)
            .PinButton(True),
        )

        # Bottom: Tabbed notebook with Issues, Fields, Alt Text, Tables, SR Preview
        self._bottom_notebook = self._make_bottom_notebook()
        self._aui_mgr.AddPane(
            self._bottom_notebook,
            wx.aui.AuiPaneInfo()
            .Name("bottom_tabs")
            .Caption("Details")
            .Bottom()
            .Layer(0)
            .BestSize(800, 200)
            .MinSize(400, 120)
            .CloseButton(False)
            .PinButton(True),
        )

        self._aui_mgr.Update()

        # Register panels for F6 cycling (order matters for cycling)
        self._focus_panels = [
            self._tag_tree_panel,
            self._page_panel,
            self._properties_panel,
            self._bottom_notebook,
        ]

    def _make_page_view_panel(self) -> wx.Panel:
        panel = wx.Panel(self, id=ID_PANEL_PAGE_VIEW)
        panel.SetName("Page view panel")
        panel.SetBackgroundColour(wx.Colour(80, 80, 80))

        sizer = wx.BoxSizer(wx.VERTICAL)
        self._empty_label = wx.StaticText(
            panel,
            label="Open a PDF file to begin (Ctrl+O)\nor create a new blank PDF (Ctrl+N)",
            style=wx.ALIGN_CENTER,
        )
        self._empty_label.SetName("Welcome message")
        self._empty_label.SetForegroundColour(wx.WHITE)
        sizer.AddStretchSpacer()
        sizer.Add(self._empty_label, 0, wx.ALIGN_CENTER)
        sizer.AddStretchSpacer()
        panel.SetSizer(sizer)
        return panel

    def _make_tag_tree_panel(self) -> wx.Panel:
        panel = wx.Panel(self, id=ID_PANEL_TAG_TREE)
        panel.SetName("Tag tree panel")
        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(panel, label="Tag Tree")
        label.SetName("Tag tree heading")

        self._tag_tree = wx.TreeCtrl(
            panel,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_FULL_ROW_HIGHLIGHT,
        )
        self._tag_tree.SetName("Tag tree")
        self._tag_tree.SetToolTip(
            "Document structure tree. Use arrow keys to navigate, F2 to rename."
        )

        sizer.Add(label, 0, wx.ALL, 4)
        sizer.Add(self._tag_tree, 1, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)
        return panel

    def _make_reading_order_panel(self) -> wx.Panel:
        panel = wx.Panel(self, id=ID_PANEL_READING_ORDER)
        panel.SetName("Reading order panel")
        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(panel, label="Reading Order")
        label.SetName("Reading order heading")

        self._reading_order_list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
        )
        self._reading_order_list.SetName("Reading order list")
        self._reading_order_list.SetToolTip(
            "Document reading order. Use Alt+Up/Down to reorder elements."
        )
        self._reading_order_list.InsertColumn(0, "#", width=40)
        self._reading_order_list.InsertColumn(1, "Page", width=50)
        self._reading_order_list.InsertColumn(2, "Type", width=80)
        self._reading_order_list.InsertColumn(3, "Content", width=200)

        sizer.Add(label, 0, wx.ALL, 4)
        sizer.Add(self._reading_order_list, 1, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)
        return panel

    def _make_properties_panel(self) -> wx.Panel:
        panel = wx.Panel(self, id=ID_PANEL_PROPERTIES)
        panel.SetName("Properties panel")
        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(panel, label="Properties")
        label.SetName("Properties heading")

        self._properties_placeholder = wx.StaticText(
            panel,
            label="Select an element to view its properties.",
            style=wx.ALIGN_CENTER,
        )
        self._properties_placeholder.SetName("Properties placeholder text")

        sizer.Add(label, 0, wx.ALL, 4)
        sizer.AddStretchSpacer()
        sizer.Add(self._properties_placeholder, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        sizer.AddStretchSpacer()
        panel.SetSizer(sizer)
        return panel

    def _make_bottom_notebook(self) -> wx.Notebook:
        notebook = wx.Notebook(self, id=ID_PANEL_ISSUES)
        notebook.SetName("Details notebook")

        # Issues tab
        issues_panel = wx.Panel(notebook)
        issues_panel.SetName("Issues panel")
        issues_sizer = wx.BoxSizer(wx.VERTICAL)
        self._issues_list = wx.ListCtrl(
            issues_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
        )
        self._issues_list.SetName("Accessibility issues list")
        self._issues_list.InsertColumn(0, "Severity", width=80)
        self._issues_list.InsertColumn(1, "Rule", width=100)
        self._issues_list.InsertColumn(2, "WCAG", width=70)
        self._issues_list.InsertColumn(3, "Description", width=350)
        self._issues_list.InsertColumn(4, "Page", width=50)
        issues_sizer.Add(self._issues_list, 1, wx.EXPAND | wx.ALL, 4)
        issues_panel.SetSizer(issues_sizer)
        notebook.AddPage(issues_panel, "Issues")

        # Fields tab
        fields_panel = wx.Panel(notebook)
        fields_panel.SetName("Form fields panel")
        fields_sizer = wx.BoxSizer(wx.VERTICAL)
        self._fields_list = wx.ListCtrl(
            fields_panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
        )
        self._fields_list.SetName("Form fields list")
        self._fields_list.InsertColumn(0, "Page", width=50)
        self._fields_list.InsertColumn(1, "Name", width=150)
        self._fields_list.InsertColumn(2, "Type", width=80)
        self._fields_list.InsertColumn(3, "Tooltip", width=200)
        self._fields_list.InsertColumn(4, "Required", width=70)
        fields_sizer.Add(self._fields_list, 1, wx.EXPAND | wx.ALL, 4)
        fields_panel.SetSizer(fields_sizer)
        notebook.AddPage(fields_panel, "Fields")

        # Alt Text tab
        alt_text_panel = wx.Panel(notebook)
        alt_text_panel.SetName("Alt text panel")
        alt_text_sizer = wx.BoxSizer(wx.VERTICAL)
        alt_placeholder = wx.StaticText(
            alt_text_panel,
            label="Open a PDF to browse images and edit alt text.",
            style=wx.ALIGN_CENTER,
        )
        alt_placeholder.SetName("Alt text placeholder")
        alt_text_sizer.AddStretchSpacer()
        alt_text_sizer.Add(alt_placeholder, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        alt_text_sizer.AddStretchSpacer()
        alt_text_panel.SetSizer(alt_text_sizer)
        notebook.AddPage(alt_text_panel, "Alt Text")

        # Tables tab
        tables_panel = wx.Panel(notebook)
        tables_panel.SetName("Tables panel")
        tables_sizer = wx.BoxSizer(wx.VERTICAL)
        tables_placeholder = wx.StaticText(
            tables_panel,
            label="Select a Table element in the tag tree to edit table headers.",
            style=wx.ALIGN_CENTER,
        )
        tables_placeholder.SetName("Tables placeholder")
        tables_sizer.AddStretchSpacer()
        tables_sizer.Add(tables_placeholder, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        tables_sizer.AddStretchSpacer()
        tables_panel.SetSizer(tables_sizer)
        notebook.AddPage(tables_panel, "Tables")

        # SR Preview tab
        sr_panel = wx.Panel(notebook)
        sr_panel.SetName("Screen reader preview panel")
        sr_sizer = wx.BoxSizer(wx.VERTICAL)
        self._sr_preview_list = wx.ListBox(sr_panel, style=wx.LB_SINGLE)
        self._sr_preview_list.SetName("Screen reader preview list")
        self._sr_preview_list.SetToolTip(
            "Linearized screen reader preview. "
            "Use Up/Down to navigate, Enter to select an element."
        )
        sr_placeholder_label = wx.StaticText(
            sr_panel,
            label="Open a PDF to see the screen reader preview.",
        )
        sr_placeholder_label.SetName("SR preview placeholder")
        sr_sizer.Add(sr_placeholder_label, 0, wx.ALL, 4)
        sr_sizer.Add(self._sr_preview_list, 1, wx.EXPAND | wx.ALL, 4)
        sr_panel.SetSizer(sr_sizer)
        notebook.AddPage(sr_panel, "SR Preview")

        notebook.Bind(wx.EVT_KEY_DOWN, self._on_notebook_key)
        return notebook

    # ------------------------------------------------------------------
    # Event handlers -- File
    # ------------------------------------------------------------------

    def _on_file_new(self, event: wx.CommandEvent) -> None:
        if not self._confirm_unsaved():
            return
        wx.MessageBox(
            "New blank PDF creation will be available in a future phase.",
            "Not Yet Implemented",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _on_file_open(self, event: wx.CommandEvent) -> None:
        if not self._confirm_unsaved():
            return
        with wx.FileDialog(
            self,
            "Open PDF file",
            wildcard="PDF files (*.pdf)|*.pdf|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        self._open_file(path)

    def _open_file(self, path: str) -> None:
        try:
            self._document.open(path)
            self._renderer.load(path)
        except Exception as exc:
            wx.MessageBox(
                f"Could not open file:\n{exc}",
                "Error",
                wx.OK | wx.ICON_ERROR,
                self,
            )

    def _on_file_save(self, event: wx.CommandEvent) -> None:
        if not self._document.is_open:
            return
        if self._document.path is None:
            self._on_file_save_as(event)
            return
        try:
            self._document.save()
            self._update_title()
        except Exception as exc:
            wx.MessageBox(
                f"Could not save file:\n{exc}",
                "Error",
                wx.OK | wx.ICON_ERROR,
                self,
            )

    def _on_file_save_as(self, event: wx.CommandEvent) -> None:
        if not self._document.is_open:
            return
        with wx.FileDialog(
            self,
            "Save PDF file",
            wildcard="PDF files (*.pdf)|*.pdf",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        try:
            self._document.save_as(path)
            self._update_title()
        except Exception as exc:
            wx.MessageBox(
                f"Could not save file:\n{exc}",
                "Error",
                wx.OK | wx.ICON_ERROR,
                self,
            )

    def _on_exit(self, event: wx.CommandEvent) -> None:
        self.Close()

    # ------------------------------------------------------------------
    # Event handlers -- Edit
    # ------------------------------------------------------------------

    def _on_undo(self, event: wx.CommandEvent) -> None:
        if self._document.commands.can_undo:
            self._document.undo()
            self._update_toolbar_state()

    def _on_redo(self, event: wx.CommandEvent) -> None:
        if self._document.commands.can_redo:
            self._document.redo()
            self._update_toolbar_state()

    def _on_preferences(self, event: wx.CommandEvent) -> None:
        wx.MessageBox(
            "Preferences will be available in a future phase.",
            "Not Yet Implemented",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    # ------------------------------------------------------------------
    # Event handlers -- View / Zoom
    # ------------------------------------------------------------------

    def _on_zoom_in(self, event: wx.CommandEvent) -> None:
        idx = self._current_zoom_index()
        if idx < len(self._ZOOM_LEVELS) - 1:
            self._set_zoom(self._ZOOM_LEVELS[idx + 1])

    def _on_zoom_out(self, event: wx.CommandEvent) -> None:
        idx = self._current_zoom_index()
        if idx > 0:
            self._set_zoom(self._ZOOM_LEVELS[idx - 1])

    def _on_fit_page(self, event: wx.CommandEvent) -> None:
        self._set_zoom(1.0)

    def _on_zoom_combo(self, event: wx.CommandEvent) -> None:
        text = self._zoom_combo.GetValue().strip().rstrip("%")
        try:
            pct = float(text)
            self._set_zoom(pct / 100.0)
        except ValueError:
            pass

    def _current_zoom_index(self) -> int:
        best = 0
        min_diff = abs(self._ZOOM_LEVELS[0] - self._current_zoom)
        for i, z in enumerate(self._ZOOM_LEVELS):
            diff = abs(z - self._current_zoom)
            if diff < min_diff:
                min_diff = diff
                best = i
        return best

    def _set_zoom(self, zoom: float) -> None:
        zoom = max(0.5, min(4.0, zoom))
        self._current_zoom = zoom
        pct = int(round(zoom * 100))
        self._zoom_combo.SetValue(f"{pct}%")
        self._statusbar.SetStatusText(f"Zoom: {pct}%", 2)

    # ------------------------------------------------------------------
    # Event handlers -- Check
    # ------------------------------------------------------------------

    def _on_check_full(self, event: wx.CommandEvent) -> None:
        if not self._document.is_open:
            wx.MessageBox(
                "Open a PDF file first.", "No Document", wx.OK | wx.ICON_INFORMATION, self
            )
            return
        wx.MessageBox(
            "Accessibility checking will be available in Phase 2.",
            "Not Yet Implemented",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _on_check_builtin(self, event: wx.CommandEvent) -> None:
        self._on_check_full(event)

    def _on_check_verapdf(self, event: wx.CommandEvent) -> None:
        self._on_check_full(event)

    def _on_export_report(self, event: wx.CommandEvent) -> None:
        wx.MessageBox(
            "Report export will be available in Phase 2.",
            "Not Yet Implemented",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    # ------------------------------------------------------------------
    # Event handlers -- Help
    # ------------------------------------------------------------------

    def _on_help_shortcuts(self, event: wx.CommandEvent) -> None:
        msg = (
            "Keyboard Shortcuts\n\n"
            "Ctrl+O  Open file\n"
            "Ctrl+S  Save file\n"
            "Ctrl+Shift+S  Save as\n"
            "Ctrl+Z  Undo\n"
            "Ctrl+Y  Redo\n"
            "F5  Run accessibility check\n"
            "Ctrl+=  Zoom in\n"
            "Ctrl+-  Zoom out\n"
            "Ctrl+0  Fit page\n"
            "F6  Cycle panel focus\n"
            "Ctrl+Tab  Cycle bottom tabs\n"
            "Ctrl+Shift+O  Toggle reading order overlay\n"
            "Ctrl+Shift+R  Screen reader preview\n"
            "Ctrl+/  Show this dialog\n"
        )
        wx.MessageBox(msg, "Keyboard Shortcuts", wx.OK | wx.ICON_INFORMATION, self)

    def _on_about(self, event: wx.CommandEvent) -> None:
        wx.MessageBox(
            "PDF Accessibility Tool v0.1.0\n\n"
            "An accessible PDF remediation, form building, and auto-tagging tool.\n\n"
            "Built with wxPython, pikepdf, pypdfium2, and Pillow.",
            "About PDF Accessibility Tool",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    # ------------------------------------------------------------------
    # Document change events
    # ------------------------------------------------------------------

    def _on_doc_changed(self, event: wx.Event) -> None:
        self._update_title()
        self._update_toolbar_state()
        reason = getattr(event, "reason", "")
        if reason == "open":
            doc = getattr(event, "document", None)
            if doc is not None:
                page_count = doc.page_count
                name = doc.path.name if doc.path else "Untitled"
                self._statusbar.SetStatusText(f"Page 1 of {page_count}", 0)
                self._statusbar.SetStatusText(f"Opened: {name}", 1)

    def _on_doc_closed(self, event: wx.Event) -> None:
        self._update_title()
        self._update_toolbar_state()
        self._statusbar.SetStatusText(
            "Open a PDF file to begin (Ctrl+O) or create a new blank PDF (Ctrl+N)", 0
        )
        self._statusbar.SetStatusText("", 1)

    # ------------------------------------------------------------------
    # Close handling
    # ------------------------------------------------------------------

    def _on_close(self, event: wx.CloseEvent) -> None:
        if event.CanVeto() and not self._confirm_unsaved():
            event.Veto()
            return
        self._aui_mgr.UnInit()
        self._document.close()
        self._renderer.close()
        self.Destroy()

    # ------------------------------------------------------------------
    # Keyboard navigation
    # ------------------------------------------------------------------

    def _on_key_down(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        mods = event.GetModifiers()

        if key == wx.WXK_F6 and not mods:
            self._cycle_panel_focus()
            return

        event.Skip()

    def _on_notebook_key(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        mods = event.GetModifiers()
        if key == wx.WXK_TAB and (mods & wx.MOD_CONTROL):
            nb = self._bottom_notebook
            count = nb.GetPageCount()
            if count > 0:
                current = nb.GetSelection()
                next_page = (current + 1) % count
                nb.SetSelection(next_page)
            return
        event.Skip()

    def _cycle_panel_focus(self) -> None:
        """Cycle focus through the main panels (F6)."""
        focused = wx.Window.FindFocus()
        panels = self._focus_panels
        if not panels:
            return

        # Find which panel currently has (or contains) focus
        current_idx = -1
        for i, panel in enumerate(panels):
            if panel == focused or (
                hasattr(panel, "IsDescendant") and panel.IsDescendant(focused)
            ):
                current_idx = i
                break

        next_idx = (current_idx + 1) % len(panels)
        target = panels[next_idx]
        target.SetFocus()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _confirm_unsaved(self) -> bool:
        """Return True if it is safe to proceed (discard or no changes)."""
        if not self._document.is_dirty:
            return True
        result = wx.MessageBox(
            "The current file has unsaved changes. Do you want to save before continuing?",
            "Unsaved Changes",
            wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
            self,
        )
        if result == wx.YES:
            try:
                self._document.save()
            except Exception:
                self._on_file_save_as(None)
            return True
        if result == wx.NO:
            return True
        return False  # CANCEL

    def _update_title(self) -> None:
        if self._document.is_open and self._document.path:
            name = self._document.path.name
            dirty = " *" if self._document.is_dirty else ""
            self.SetTitle(f"{name}{dirty} — PDF Accessibility Tool")
        else:
            self.SetTitle("PDF Accessibility Tool")

    def _update_toolbar_state(self) -> None:
        tb = self._toolbar
        tb.EnableTool(ID_FILE_SAVE, self._document.is_open and self._document.is_dirty)
        tb.EnableTool(ID_EDIT_UNDO, self._document.commands.can_undo)
        tb.EnableTool(ID_EDIT_REDO, self._document.commands.can_redo)
        tb.Refresh()
