"""Standard PDF 2.0 / PDF/UA structure element type definitions.

Constants for all standard PDF structure element types as defined in
ISO 32000-2 (PDF 2.0), organised by category with parent/child
relationship metadata for validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TagType:
    """A single PDF structure element type."""

    name: str
    category: str
    description: str
    allowed_children: list[str] = field(default_factory=list)
    allowed_parents: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Category names
# ---------------------------------------------------------------------------
CAT_GROUPING = "grouping"
CAT_BLOCK = "block"
CAT_TABLE = "table"
CAT_INLINE = "inline"
CAT_ILLUSTRATION = "illustration"
CAT_RUBY_WARICHU = "ruby_warichu"

# ---------------------------------------------------------------------------
# Name lists used to build allowed_children / allowed_parents
# ---------------------------------------------------------------------------
_GROUPING_NAMES = [
    "Document", "Part", "Sect", "Div", "Art",
    "BlockQuote", "Caption", "TOC", "TOCI", "Index",
    "NonStruct", "Private",
]

_BLOCK_NAMES = [
    "H", "H1", "H2", "H3", "H4", "H5", "H6",
    "P", "L", "LI", "Lbl", "LBody",
]

_TABLE_NAMES = ["Table", "THead", "TBody", "TFoot", "TR", "TH", "TD"]

_INLINE_NAMES = [
    "Span", "Quote", "Note", "Reference", "BibEntry",
    "Code", "Link", "Annot",
]

_ILLUSTRATION_NAMES = ["Figure", "Formula", "Form"]

_RUBY_WARICHU_NAMES = ["Ruby", "RB", "RT", "RP", "Warichu", "WT", "WP"]

_ALL_NAMES = (
    _GROUPING_NAMES + _BLOCK_NAMES + _TABLE_NAMES
    + _INLINE_NAMES + _ILLUSTRATION_NAMES + _RUBY_WARICHU_NAMES
)

# Broad child/parent sets referenced below
_FLOW_CHILDREN = _GROUPING_NAMES + _BLOCK_NAMES + _TABLE_NAMES + _INLINE_NAMES + _ILLUSTRATION_NAMES + _RUBY_WARICHU_NAMES
_BLOCK_AND_INLINE = _BLOCK_NAMES + _INLINE_NAMES + _ILLUSTRATION_NAMES + _RUBY_WARICHU_NAMES
_INLINE_CHILDREN = _INLINE_NAMES + _ILLUSTRATION_NAMES + _RUBY_WARICHU_NAMES
_GROUPING_AND_BLOCK_PARENTS = _GROUPING_NAMES + ["LI", "LBody", "TD", "TH", "BlockQuote", "Caption"]

# ---------------------------------------------------------------------------
# Grouping elements
# ---------------------------------------------------------------------------
Document = TagType(
    name="Document",
    category=CAT_GROUPING,
    description="Document root",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=[],
)

Part = TagType(
    name="Part",
    category=CAT_GROUPING,
    description="Part",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=["Document", "Part"],
)

Sect = TagType(
    name="Sect",
    category=CAT_GROUPING,
    description="Section",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=["Document", "Part", "Sect", "Art", "Div", "BlockQuote"],
)

Div = TagType(
    name="Div",
    category=CAT_GROUPING,
    description="Division",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=_GROUPING_NAMES + ["LI", "LBody", "TD", "TH"],
)

Art = TagType(
    name="Art",
    category=CAT_GROUPING,
    description="Article",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=["Document", "Part", "Sect", "Div"],
)

BlockQuote = TagType(
    name="BlockQuote",
    category=CAT_GROUPING,
    description="Block quotation",
    allowed_children=_BLOCK_AND_INLINE,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

Caption = TagType(
    name="Caption",
    category=CAT_GROUPING,
    description="Caption",
    allowed_children=_BLOCK_AND_INLINE,
    allowed_parents=["Table", "Figure", "Formula", "Form"] + _GROUPING_NAMES,
)

TOC = TagType(
    name="TOC",
    category=CAT_GROUPING,
    description="Table of contents",
    allowed_children=["TOCI", "TOC", "Caption"],
    allowed_parents=["Document", "Part", "Sect", "Div", "Art"],
)

TOCI = TagType(
    name="TOCI",
    category=CAT_GROUPING,
    description="Table of contents item",
    allowed_children=["P", "Lbl", "Reference", "Link", "TOC", "NonStruct"] + _INLINE_NAMES,
    allowed_parents=["TOC"],
)

Index = TagType(
    name="Index",
    category=CAT_GROUPING,
    description="Index",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=["Document", "Part", "Sect", "Div"],
)

NonStruct = TagType(
    name="NonStruct",
    category=CAT_GROUPING,
    description="Non-structural element",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=_ALL_NAMES,
)

Private = TagType(
    name="Private",
    category=CAT_GROUPING,
    description="Private element",
    allowed_children=_FLOW_CHILDREN,
    allowed_parents=_ALL_NAMES,
)

# ---------------------------------------------------------------------------
# Block-level elements
# ---------------------------------------------------------------------------
H = TagType(
    name="H",
    category=CAT_BLOCK,
    description="Heading (generic)",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

H1 = TagType(
    name="H1",
    category=CAT_BLOCK,
    description="Heading level 1",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

H2 = TagType(
    name="H2",
    category=CAT_BLOCK,
    description="Heading level 2",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

H3 = TagType(
    name="H3",
    category=CAT_BLOCK,
    description="Heading level 3",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

H4 = TagType(
    name="H4",
    category=CAT_BLOCK,
    description="Heading level 4",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

H5 = TagType(
    name="H5",
    category=CAT_BLOCK,
    description="Heading level 5",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

H6 = TagType(
    name="H6",
    category=CAT_BLOCK,
    description="Heading level 6",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

P = TagType(
    name="P",
    category=CAT_BLOCK,
    description="Paragraph",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

L = TagType(
    name="L",
    category=CAT_BLOCK,
    description="List",
    allowed_children=["LI", "Caption"],
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

LI = TagType(
    name="LI",
    category=CAT_BLOCK,
    description="List item",
    allowed_children=["Lbl", "LBody", "L"] + _INLINE_CHILDREN,
    allowed_parents=["L"],
)

Lbl = TagType(
    name="Lbl",
    category=CAT_BLOCK,
    description="Label",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=["LI", "TOCI"] + _GROUPING_NAMES,
)

LBody = TagType(
    name="LBody",
    category=CAT_BLOCK,
    description="List body",
    allowed_children=_BLOCK_AND_INLINE + ["Table"],
    allowed_parents=["LI"],
)

# ---------------------------------------------------------------------------
# Table elements
# ---------------------------------------------------------------------------
Table = TagType(
    name="Table",
    category=CAT_TABLE,
    description="Table",
    allowed_children=["THead", "TBody", "TFoot", "TR", "Caption"],
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS,
)

THead = TagType(
    name="THead",
    category=CAT_TABLE,
    description="Table header row group",
    allowed_children=["TR"],
    allowed_parents=["Table"],
)

TBody = TagType(
    name="TBody",
    category=CAT_TABLE,
    description="Table body row group",
    allowed_children=["TR"],
    allowed_parents=["Table"],
)

TFoot = TagType(
    name="TFoot",
    category=CAT_TABLE,
    description="Table footer row group",
    allowed_children=["TR"],
    allowed_parents=["Table"],
)

TR = TagType(
    name="TR",
    category=CAT_TABLE,
    description="Table row",
    allowed_children=["TH", "TD"],
    allowed_parents=["Table", "THead", "TBody", "TFoot"],
)

TH = TagType(
    name="TH",
    category=CAT_TABLE,
    description="Table header cell",
    allowed_children=_BLOCK_AND_INLINE + ["Table"],
    allowed_parents=["TR"],
)

TD = TagType(
    name="TD",
    category=CAT_TABLE,
    description="Table data cell",
    allowed_children=_BLOCK_AND_INLINE + ["Table"],
    allowed_parents=["TR"],
)

# ---------------------------------------------------------------------------
# Inline elements
# ---------------------------------------------------------------------------
Span = TagType(
    name="Span",
    category=CAT_INLINE,
    description="Span",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

Quote = TagType(
    name="Quote",
    category=CAT_INLINE,
    description="Inline quotation",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

Note = TagType(
    name="Note",
    category=CAT_INLINE,
    description="Note",
    allowed_children=_BLOCK_AND_INLINE,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

Reference = TagType(
    name="Reference",
    category=CAT_INLINE,
    description="Reference",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

BibEntry = TagType(
    name="BibEntry",
    category=CAT_INLINE,
    description="Bibliography entry",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

Code = TagType(
    name="Code",
    category=CAT_INLINE,
    description="Code fragment",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

Link = TagType(
    name="Link",
    category=CAT_INLINE,
    description="Hyperlink",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH", "TOCI"],
)

Annot = TagType(
    name="Annot",
    category=CAT_INLINE,
    description="Annotation",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

# ---------------------------------------------------------------------------
# Illustration elements
# ---------------------------------------------------------------------------
Figure = TagType(
    name="Figure",
    category=CAT_ILLUSTRATION,
    description="Figure",
    allowed_children=["Caption"] + _INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS + _INLINE_NAMES,
)

Formula = TagType(
    name="Formula",
    category=CAT_ILLUSTRATION,
    description="Formula",
    allowed_children=["Caption"] + _INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS + _INLINE_NAMES,
)

Form = TagType(
    name="Form",
    category=CAT_ILLUSTRATION,
    description="Form",
    allowed_children=["Caption"] + _INLINE_CHILDREN,
    allowed_parents=_GROUPING_AND_BLOCK_PARENTS + _INLINE_NAMES,
)

# ---------------------------------------------------------------------------
# Ruby / Warichu elements
# ---------------------------------------------------------------------------
Ruby = TagType(
    name="Ruby",
    category=CAT_RUBY_WARICHU,
    description="Ruby annotation",
    allowed_children=["RB", "RT", "RP"],
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

RB = TagType(
    name="RB",
    category=CAT_RUBY_WARICHU,
    description="Ruby base text",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=["Ruby"],
)

RT = TagType(
    name="RT",
    category=CAT_RUBY_WARICHU,
    description="Ruby annotation text",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=["Ruby"],
)

RP = TagType(
    name="RP",
    category=CAT_RUBY_WARICHU,
    description="Ruby punctuation",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=["Ruby"],
)

Warichu = TagType(
    name="Warichu",
    category=CAT_RUBY_WARICHU,
    description="Warichu annotation",
    allowed_children=["WT", "WP"],
    allowed_parents=_BLOCK_NAMES + _INLINE_NAMES + _GROUPING_NAMES + ["TD", "TH"],
)

WT = TagType(
    name="WT",
    category=CAT_RUBY_WARICHU,
    description="Warichu text",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=["Warichu"],
)

WP = TagType(
    name="WP",
    category=CAT_RUBY_WARICHU,
    description="Warichu punctuation",
    allowed_children=_INLINE_CHILDREN,
    allowed_parents=["Warichu"],
)

# ---------------------------------------------------------------------------
# Lookup dictionaries
# ---------------------------------------------------------------------------
STANDARD_TAGS: dict[str, TagType] = {
    t.name: t
    for t in [
        Document, Part, Sect, Div, Art, BlockQuote, Caption, TOC, TOCI,
        Index, NonStruct, Private,
        H, H1, H2, H3, H4, H5, H6, P, L, LI, Lbl, LBody,
        Table, THead, TBody, TFoot, TR, TH, TD,
        Span, Quote, Note, Reference, BibEntry, Code, Link, Annot,
        Figure, Formula, Form,
        Ruby, RB, RT, RP, Warichu, WT, WP,
    ]
}

CATEGORIES: dict[str, list[TagType]] = {}
for _tag in STANDARD_TAGS.values():
    CATEGORIES.setdefault(_tag.category, []).append(_tag)

_HEADING_LEVELS: dict[str, int] = {
    "H1": 1, "H2": 2, "H3": 3, "H4": 4, "H5": 5, "H6": 6,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def get_tag_type(name: str) -> TagType | None:
    """Return the ``TagType`` for *name*, or ``None`` if unknown."""
    return STANDARD_TAGS.get(name)


def get_category(name: str) -> list[TagType]:
    """Return all ``TagType`` instances in the given category."""
    return list(CATEGORIES.get(name, []))


def is_valid_tag(name: str) -> bool:
    """Return ``True`` if *name* is a recognised standard PDF tag."""
    return name in STANDARD_TAGS


def get_heading_level(name: str) -> int | None:
    """Return 1-6 for H1-H6, or ``None`` for any other tag."""
    return _HEADING_LEVELS.get(name)
