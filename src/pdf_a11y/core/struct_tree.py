"""Structure tree wrapper for PDF tag trees.

This module provides the in-memory model that bridges pikepdf PDF dictionaries
and the UI panels.  It contains the :class:`StructNode` dataclass and the
:class:`StructTree` high-level wrapper that exposes every edit operation as an
undoable :class:`~pdf_a11y.core.document.Command`.

Public API
----------
StructNode   -- Dataclass representing a single node in the structure tree.
StructTree   -- Wrapper around the PDF ``/StructTreeRoot`` with read/write
                operations over the tag hierarchy.
"""
from __future__ import annotations

import contextlib
import itertools
from collections.abc import Iterator
from dataclasses import dataclass, field

import pikepdf

from pdf_a11y.core.document import Command

# ---------------------------------------------------------------------------
# Unique ID generator
# ---------------------------------------------------------------------------
_id_counter = itertools.count(1)


def _next_id() -> str:
    return f"sn-{next(_id_counter)}"


# ---------------------------------------------------------------------------
# StructNode dataclass
# ---------------------------------------------------------------------------

@dataclass
class StructNode:
    """One node in the structure tree, corresponding to a PDF StructElem."""

    tag: str
    """``/S`` value: ``"P"``, ``"H1"``, ``"Table"``, etc."""

    page: int | None = None
    """Page index if this element has page content."""

    alt_text: str = ""
    """``/Alt`` text alternative."""

    actual_text: str = ""
    """``/ActualText`` replacement text."""

    expansion_text: str = ""
    """``/E`` expansion of an abbreviation."""

    language: str = ""
    """``/Lang`` BCP 47 language code."""

    attributes: dict[str, str] = field(default_factory=dict)
    """``/A`` attribute dictionary (Scope, Headers, etc.)."""

    mcids: list[int] = field(default_factory=list)
    """Marked-content IDs linking to the content stream."""

    children: list[StructNode] = field(default_factory=list)
    """``/K`` child elements (ordered -- this **is** reading order)."""

    parent: StructNode | None = field(default=None, repr=False)
    """``/P`` parent reference."""

    pdf_obj: pikepdf.Object | None = field(default=None, repr=False)
    """Reference to the underlying pikepdf indirect object."""

    node_id: str = field(default_factory=_next_id)
    """Unique ID for UI tracking."""


# ---------------------------------------------------------------------------
# pikepdf helpers
# ---------------------------------------------------------------------------

def _str_or_empty(obj: pikepdf.Object | None) -> str:
    """Extract a Python ``str`` from a pikepdf String/Name, or ``""``."""
    if obj is None:
        return ""
    if isinstance(obj, (pikepdf.String, pikepdf.Name)):
        return str(obj)
    return str(obj)


def _parse_attributes(a_obj: pikepdf.Object | None) -> dict[str, str]:
    """Parse ``/A`` which can be a dict, an array of dicts, or absent."""
    if a_obj is None:
        return {}
    result: dict[str, str] = {}
    if isinstance(a_obj, pikepdf.Array):
        for item in list(a_obj):  # type: ignore[arg-type]
            if isinstance(item, pikepdf.Dictionary):
                for key in item:
                    result[str(key)] = str(item[key])
    elif isinstance(a_obj, pikepdf.Dictionary):
        for key in a_obj:
            result[str(key)] = str(a_obj[key])
    return result


def _resolve_page_index(
    pdf: pikepdf.Pdf,
    elem: pikepdf.Dictionary,
    page_lookup: dict[int, int],
) -> int | None:
    """Determine the zero-based page index for a StructElem, or ``None``."""
    pg = elem.get("/Pg")
    if pg is None:
        return None
    try:
        obj_id = pg.objgen[0] if hasattr(pg, "objgen") else id(pg)
        return page_lookup.get(obj_id)
    except Exception:
        return None


def _build_page_lookup(pdf: pikepdf.Pdf) -> dict[int, int]:
    """Map page object-generation ids to zero-based page indices."""
    lookup: dict[int, int] = {}
    for idx, page in enumerate(pdf.pages):
        try:
            obj_id = page.obj.objgen[0]
        except Exception:
            obj_id = id(page.obj)
        lookup[obj_id] = idx
    return lookup


# ---------------------------------------------------------------------------
# Tree parsing
# ---------------------------------------------------------------------------

def _parse_k_entry(
    pdf: pikepdf.Pdf,
    k_obj: pikepdf.Object,
    parent: StructNode,
    page_lookup: dict[int, int],
) -> None:
    """Recursively parse a ``/K`` entry which can be int, dict, or array."""
    if isinstance(k_obj, pikepdf.Array):
        for item in list(k_obj):  # type: ignore[arg-type]
            _parse_k_entry(pdf, item, parent, page_lookup)
        return

    # Integer MCID -- leaf content reference
    if not isinstance(
        k_obj, (pikepdf.Dictionary, pikepdf.Array, pikepdf.Name, pikepdf.String)
    ):
        try:
            mcid = int(k_obj)
            parent.mcids.append(mcid)
        except (TypeError, ValueError):
            pass
        return

    if not isinstance(k_obj, pikepdf.Dictionary):
        return

    # MCR (marked-content reference) dict -- has /Type /MCR and /MCID
    type_val = k_obj.get("/Type")
    if type_val is not None and str(type_val) == "/MCR":
        mcid_val = k_obj.get("/MCID")
        if mcid_val is not None:
            with contextlib.suppress(TypeError, ValueError):
                parent.mcids.append(int(mcid_val))
        return

    # OBJR (object reference) -- skip for now
    if type_val is not None and str(type_val) == "/OBJR":
        return

    # Otherwise treat as a StructElem child dict
    s_val = k_obj.get("/S")
    if s_val is None:
        return

    child = StructNode(
        tag=str(s_val).lstrip("/"),
        page=_resolve_page_index(pdf, k_obj, page_lookup),
        alt_text=_str_or_empty(k_obj.get("/Alt")),
        actual_text=_str_or_empty(k_obj.get("/ActualText")),
        expansion_text=_str_or_empty(k_obj.get("/E")),
        language=_str_or_empty(k_obj.get("/Lang")),
        attributes=_parse_attributes(k_obj.get("/A")),
        parent=parent,
        pdf_obj=k_obj,
    )
    parent.children.append(child)

    child_k = k_obj.get("/K")
    if child_k is not None:
        _parse_k_entry(pdf, child_k, child, page_lookup)


# ---------------------------------------------------------------------------
# Command classes
# ---------------------------------------------------------------------------

class ChangeTagCommand(Command):
    """Change the ``/S`` tag on a StructElem."""

    def __init__(self, node: StructNode, new_tag: str) -> None:
        self._node = node
        self._new_tag = new_tag
        self._old_tag = node.tag

    @property
    def description(self) -> str:
        return f"Change tag {self._old_tag} -> {self._new_tag}"

    def execute(self) -> None:
        self._node.tag = self._new_tag
        if self._node.pdf_obj is not None:
            self._node.pdf_obj["/S"] = pikepdf.Name(f"/{self._new_tag}")

    def undo(self) -> None:
        self._node.tag = self._old_tag
        if self._node.pdf_obj is not None:
            self._node.pdf_obj["/S"] = pikepdf.Name(f"/{self._old_tag}")


class SetStringPropertyCommand(Command):
    """Set a string property (``/Alt``, ``/ActualText``, ``/E``, ``/Lang``)."""

    def __init__(
        self,
        node: StructNode,
        pdf_key: str,
        attr_name: str,
        new_value: str,
        description: str,
    ) -> None:
        self._node = node
        self._pdf_key = pdf_key
        self._attr_name = attr_name
        self._new_value = new_value
        self._old_value: str = getattr(node, attr_name)
        self._desc = description

    @property
    def description(self) -> str:
        return self._desc

    def execute(self) -> None:
        setattr(self._node, self._attr_name, self._new_value)
        if self._node.pdf_obj is not None:
            if self._new_value:
                self._node.pdf_obj[self._pdf_key] = pikepdf.String(self._new_value)
            elif self._pdf_key in self._node.pdf_obj:
                del self._node.pdf_obj[self._pdf_key]

    def undo(self) -> None:
        setattr(self._node, self._attr_name, self._old_value)
        if self._node.pdf_obj is not None:
            if self._old_value:
                self._node.pdf_obj[self._pdf_key] = pikepdf.String(self._old_value)
            elif self._pdf_key in self._node.pdf_obj:
                del self._node.pdf_obj[self._pdf_key]


class SetAttributeCommand(Command):
    """Set an arbitrary key in the ``/A`` attribute dictionary."""

    def __init__(self, node: StructNode, key: str, value: str) -> None:
        self._node = node
        self._key = key
        self._new_value = value
        self._old_value: str | None = node.attributes.get(key)

    @property
    def description(self) -> str:
        return f"Set attribute {self._key}"

    def execute(self) -> None:
        self._node.attributes[self._key] = self._new_value
        self._write_to_pdf(self._new_value)

    def undo(self) -> None:
        if self._old_value is None:
            self._node.attributes.pop(self._key, None)
        else:
            self._node.attributes[self._key] = self._old_value
        self._write_to_pdf(self._old_value)

    def _write_to_pdf(self, value: str | None) -> None:
        if self._node.pdf_obj is None:
            return
        a_obj = self._node.pdf_obj.get("/A")
        if a_obj is None or not isinstance(a_obj, pikepdf.Dictionary):
            if value is not None:
                a_obj = pikepdf.Dictionary()
                self._node.pdf_obj["/A"] = a_obj
            else:
                return
        if value is not None:
            a_obj[self._key] = pikepdf.String(value)
        elif self._key in a_obj:
            del a_obj[self._key]


class ReorderChildrenCommand(Command):
    """Rearrange children of *parent* to match *new_order* (list of StructNode)."""

    def __init__(self, parent: StructNode, new_order: list[StructNode]) -> None:
        self._parent = parent
        self._new_order = list(new_order)
        self._old_order = list(parent.children)

    @property
    def description(self) -> str:
        return "Reorder children"

    def execute(self) -> None:
        self._apply(self._new_order)

    def undo(self) -> None:
        self._apply(self._old_order)

    def _apply(self, order: list[StructNode]) -> None:
        self._parent.children = list(order)
        if self._parent.pdf_obj is not None:
            k_array = self._rebuild_k(order)
            self._parent.pdf_obj["/K"] = k_array

    def _rebuild_k(self, order: list[StructNode]) -> pikepdf.Array:
        """Rebuild the ``/K`` array preserving MCIDs at their original positions."""
        items: list[pikepdf.Object] = []
        # First, put back any bare MCIDs from the parent
        # (MCIDs belong to the parent, not reordered with children)
        old_k = self._parent.pdf_obj.get("/K") if self._parent.pdf_obj else None
        if isinstance(old_k, pikepdf.Array):
            for item in list(old_k):  # type: ignore[arg-type]
                if not isinstance(item, pikepdf.Dictionary):
                    items.append(item)  # type: ignore[arg-type]
        # Then append child pdf objects in new order
        for child in order:
            if child.pdf_obj is not None:
                items.append(child.pdf_obj)
        return pikepdf.Array(items)


def _sync_k_to_pdf(parent: StructNode) -> None:
    """Rebuild the ``/K`` array on *parent*'s PDF object from its children."""
    if parent.pdf_obj is None:
        return
    old_k = parent.pdf_obj.get("/K")
    non_dict_items: list[pikepdf.Object] = []
    if isinstance(old_k, pikepdf.Array):
        for item in list(old_k):  # type: ignore[arg-type]
            if not isinstance(item, pikepdf.Dictionary):
                non_dict_items.append(item)  # type: ignore[arg-type]
    items: list[pikepdf.Object] = list(non_dict_items)
    for child in parent.children:
        if child.pdf_obj is not None:
            items.append(child.pdf_obj)
    parent.pdf_obj["/K"] = pikepdf.Array(items)


class MoveUpCommand(Command):
    """Swap a node with its previous sibling."""

    def __init__(self, node: StructNode) -> None:
        self._node = node

    @property
    def description(self) -> str:
        return f"Move {self._node.tag} up"

    def execute(self) -> None:
        self._swap(-1)

    def undo(self) -> None:
        self._swap(1)

    def _swap(self, direction: int) -> None:
        parent = self._node.parent
        if parent is None:
            return
        idx = parent.children.index(self._node)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(parent.children):
            return
        parent.children[idx], parent.children[new_idx] = (
            parent.children[new_idx],
            parent.children[idx],
        )
        _sync_k_to_pdf(parent)


class MoveDownCommand(Command):
    """Swap a node with its next sibling."""

    def __init__(self, node: StructNode) -> None:
        self._node = node

    @property
    def description(self) -> str:
        return f"Move {self._node.tag} down"

    def execute(self) -> None:
        self._swap(1)

    def undo(self) -> None:
        self._swap(-1)

    def _swap(self, direction: int) -> None:
        parent = self._node.parent
        if parent is None:
            return
        idx = parent.children.index(self._node)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(parent.children):
            return
        parent.children[idx], parent.children[new_idx] = (
            parent.children[new_idx],
            parent.children[idx],
        )
        _sync_k_to_pdf(parent)


class ReparentCommand(Command):
    """Move *node* from its current parent to *new_parent* at *index*."""

    def __init__(self, node: StructNode, new_parent: StructNode, index: int) -> None:
        self._node = node
        self._new_parent = new_parent
        self._index = index
        self._old_parent: StructNode | None = node.parent
        self._old_index: int = (
            node.parent.children.index(node) if node.parent else 0
        )

    @property
    def description(self) -> str:
        return f"Reparent {self._node.tag}"

    def execute(self) -> None:
        self._move(
            self._old_parent, self._new_parent, self._index,
        )

    def undo(self) -> None:
        self._move(
            self._new_parent, self._old_parent, self._old_index,
        )

    def _move(
        self,
        from_parent: StructNode | None,
        to_parent: StructNode | None,
        to_index: int,
    ) -> None:
        if from_parent is not None and self._node in from_parent.children:
            from_parent.children.remove(self._node)
            _sync_k_to_pdf(from_parent)
        if to_parent is not None:
            clamped = min(to_index, len(to_parent.children))
            to_parent.children.insert(clamped, self._node)
            self._node.parent = to_parent
            _sync_k_to_pdf(to_parent)
            if self._node.pdf_obj is not None and to_parent.pdf_obj is not None:
                self._node.pdf_obj["/P"] = to_parent.pdf_obj


class AddChildCommand(Command):
    """Create a new StructElem as a child of *parent* at *index*."""

    def __init__(
        self, pdf: pikepdf.Pdf, parent: StructNode, tag: str, index: int
    ) -> None:
        self._pdf = pdf
        self._parent = parent
        self._tag = tag
        self._index = index
        self._child: StructNode | None = None

    @property
    def description(self) -> str:
        return f"Add {self._tag}"

    @property
    def created_node(self) -> StructNode | None:
        return self._child

    def execute(self) -> None:
        new_dict = pikepdf.Dictionary(
            S=pikepdf.Name(f"/{self._tag}"),
        )
        if self._parent.pdf_obj is not None:
            new_dict["/P"] = self._parent.pdf_obj
        obj = self._pdf.make_indirect(new_dict)

        if self._child is None:
            self._child = StructNode(
                tag=self._tag,
                parent=self._parent,
                pdf_obj=obj,
            )
        else:
            self._child.pdf_obj = obj
            self._child.parent = self._parent

        clamped = min(self._index, len(self._parent.children))
        self._parent.children.insert(clamped, self._child)
        _sync_k_to_pdf(self._parent)

    def undo(self) -> None:
        if self._child is not None and self._child in self._parent.children:
            self._parent.children.remove(self._child)
            _sync_k_to_pdf(self._parent)


class DeleteCommand(Command):
    """Remove *node* from its parent's ``/K``."""

    def __init__(self, node: StructNode) -> None:
        self._node = node
        self._parent: StructNode | None = node.parent
        self._index: int = (
            node.parent.children.index(node) if node.parent else 0
        )

    @property
    def description(self) -> str:
        return f"Delete {self._node.tag}"

    def execute(self) -> None:
        if self._parent is not None and self._node in self._parent.children:
            self._parent.children.remove(self._node)
            _sync_k_to_pdf(self._parent)

    def undo(self) -> None:
        if self._parent is not None:
            clamped = min(self._index, len(self._parent.children))
            self._parent.children.insert(clamped, self._node)
            self._node.parent = self._parent
            _sync_k_to_pdf(self._parent)


# ---------------------------------------------------------------------------
# StructTree: high-level wrapper
# ---------------------------------------------------------------------------

class StructTree:
    """Wrapper around the PDF ``/StructTreeRoot``.

    Parses the structure tree into :class:`StructNode` objects and exposes
    every edit operation as an undoable :class:`Command`.
    """

    def __init__(self, pdf: pikepdf.Pdf) -> None:
        self._pdf = pdf
        self._root: StructNode | None = None
        self._parse()

    def _parse(self) -> None:
        """Parse ``/StructTreeRoot`` into a :class:`StructNode` tree."""
        root_dict = self._pdf.Root.get("/StructTreeRoot")
        if root_dict is None:
            self._root = None
            return

        page_lookup = _build_page_lookup(self._pdf)

        # Determine the root tag -- often "Document" but can vary
        s_val = root_dict.get("/S")
        root_tag = str(s_val).lstrip("/") if s_val is not None else "Document"

        self._root = StructNode(
            tag=root_tag,
            alt_text=_str_or_empty(root_dict.get("/Alt")),
            actual_text=_str_or_empty(root_dict.get("/ActualText")),
            expansion_text=_str_or_empty(root_dict.get("/E")),
            language=_str_or_empty(root_dict.get("/Lang")),
            attributes=_parse_attributes(root_dict.get("/A")),
            pdf_obj=root_dict,
        )

        k_obj = root_dict.get("/K")
        if k_obj is not None:
            _parse_k_entry(self._pdf, k_obj, self._root, page_lookup)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> StructNode | None:
        """The root :class:`StructNode`, or ``None`` if no structure tree."""
        return self._root

    @property
    def has_structure(self) -> bool:
        """``True`` if the PDF contains a ``/StructTreeRoot``."""
        return self._root is not None

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def walk(self) -> Iterator[StructNode]:
        """Yield every node depth-first, starting from the root."""
        if self._root is None:
            return
        stack: list[StructNode] = [self._root]
        while stack:
            node = stack.pop()
            yield node
            # Push children in reverse so first child is visited first
            stack.extend(reversed(node.children))

    def find_by_tag(self, tag_name: str) -> list[StructNode]:
        """Return all nodes whose tag matches *tag_name*."""
        return [n for n in self.walk() if n.tag == tag_name]

    def find_by_page(self, page_index: int) -> list[StructNode]:
        """Return all nodes associated with *page_index*."""
        return [n for n in self.walk() if n.page == page_index]

    def get_reading_order(self) -> list[StructNode]:
        """Return a flat list of leaf-level nodes in reading order.

        Reading order is defined by the depth-first traversal of the
        ``/K`` arrays.  Only nodes that have MCIDs (i.e. actual page
        content) are included.
        """
        return [n for n in self.walk() if n.mcids]

    # ------------------------------------------------------------------
    # Edit operations -- each returns a Command
    # ------------------------------------------------------------------

    def change_tag(self, node: StructNode, new_tag: str) -> Command:
        """Return a command that changes *node*'s tag to *new_tag*."""
        return ChangeTagCommand(node, new_tag)

    def set_alt_text(self, node: StructNode, text: str) -> Command:
        """Return a command that sets ``/Alt`` on *node*."""
        return SetStringPropertyCommand(
            node, "/Alt", "alt_text", text, "Set alt text",
        )

    def set_actual_text(self, node: StructNode, text: str) -> Command:
        """Return a command that sets ``/ActualText`` on *node*."""
        return SetStringPropertyCommand(
            node, "/ActualText", "actual_text", text, "Set actual text",
        )

    def set_expansion_text(self, node: StructNode, text: str) -> Command:
        """Return a command that sets ``/E`` on *node*."""
        return SetStringPropertyCommand(
            node, "/E", "expansion_text", text, "Set expansion text",
        )

    def set_language(self, node: StructNode, lang: str) -> Command:
        """Return a command that sets ``/Lang`` on *node*."""
        return SetStringPropertyCommand(
            node, "/Lang", "language", lang, "Set language",
        )

    def set_attribute(self, node: StructNode, key: str, value: str) -> Command:
        """Return a command that sets *key* in the ``/A`` dict."""
        return SetAttributeCommand(node, key, value)

    def reorder_children(
        self, parent: StructNode, new_order: list[StructNode],
    ) -> Command:
        """Return a command that rearranges *parent*'s children."""
        return ReorderChildrenCommand(parent, new_order)

    def move_up(self, node: StructNode) -> Command:
        """Return a command that swaps *node* with its previous sibling."""
        return MoveUpCommand(node)

    def move_down(self, node: StructNode) -> Command:
        """Return a command that swaps *node* with its next sibling."""
        return MoveDownCommand(node)

    def reparent(
        self, node: StructNode, new_parent: StructNode, index: int,
    ) -> Command:
        """Return a command that moves *node* to *new_parent* at *index*."""
        return ReparentCommand(node, new_parent, index)

    def add_child(
        self, parent: StructNode, tag: str, index: int,
    ) -> AddChildCommand:
        """Return a command that creates a new child element."""
        return AddChildCommand(self._pdf, parent, tag, index)

    def delete(self, node: StructNode) -> Command:
        """Return a command that removes *node* from the tree."""
        return DeleteCommand(node)

    # ------------------------------------------------------------------
    # ParentTree rebuild
    # ------------------------------------------------------------------

    def rebuild_parent_tree(self) -> None:
        """Recalculate ``/ParentTree`` from a depth-first walk.

        The ``/ParentTree`` is a number tree mapping ``(page, MCID)`` pairs
        to structure elements.  Rather than incrementally updating it after
        edits, we rebuild it entirely -- safer at the cost of being slightly
        slower on very large documents.
        """
        if self._root is None:
            return

        root_dict = self._pdf.Root.get("/StructTreeRoot")
        if root_dict is None:
            return

        # Collect every (page_index, mcid) -> pdf_obj mapping
        page_lookup = _build_page_lookup(self._pdf)
        num_pages = len(self._pdf.pages)

        # per-page lists: page_entries[page_idx] is a dict {mcid: struct_elem_obj}
        page_entries: list[dict[int, pikepdf.Object]] = [
            {} for _ in range(num_pages)
        ]

        for node in self.walk():
            if not node.mcids or node.pdf_obj is None:
                continue
            page_idx = node.page
            if page_idx is None:
                # Try to derive from the pdf_obj /Pg
                pg = node.pdf_obj.get("/Pg")
                if pg is not None:
                    try:
                        obj_id = pg.objgen[0] if hasattr(pg, "objgen") else id(pg)
                        page_idx = page_lookup.get(obj_id)
                    except Exception:
                        pass
            if page_idx is None or page_idx < 0 or page_idx >= num_pages:
                continue
            for mcid in node.mcids:
                page_entries[page_idx][mcid] = node.pdf_obj

        # Build the /Nums array: [page_idx, array_of_elem_refs, ...]
        nums: list[pikepdf.Object] = []
        for page_idx, mcid_map in enumerate(page_entries):
            if not mcid_map:
                continue
            max_mcid = max(mcid_map.keys())
            # Fill with null objects for unused MCIDs
            arr = pikepdf.Array(
                [pikepdf.Object.parse(b"null")] * (max_mcid + 1),
            )
            for mcid, obj in mcid_map.items():
                arr[mcid] = obj
            nums.append(pikepdf.Object.parse(str(page_idx).encode()))
            nums.append(self._pdf.make_indirect(arr))

        parent_tree = pikepdf.Dictionary(Nums=pikepdf.Array(nums))
        root_dict["/ParentTree"] = self._pdf.make_indirect(parent_tree)

        # Update /ParentTreeNextKey
        total_entries = sum(len(m) for m in page_entries)
        root_dict["/ParentTreeNextKey"] = pikepdf.Object.parse(
            str(total_entries).encode(),
        )
