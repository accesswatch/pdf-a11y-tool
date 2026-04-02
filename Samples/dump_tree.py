"""Dump the structure tree reading order for analysis.

Shows reading order number, depth, tag, MCIDs, field name, and page.
Leaf elements (content with MCIDs, form fields) are numbered sequentially
in the same order a screen reader would encounter them -- this is exactly
what Adobe Acrobat Pro shows in the Reading Order pane.
"""

import pikepdf

pdf = pikepdf.open("Samples/Medication Self-Administration Authorization.pdf")
root = pdf.Root["/StructTreeRoot"]

# Build page lookup using objgen tuples for reliable identity
page_map: dict[tuple[int, int], int] = {}
for i, p in enumerate(pdf.pages):
    page_map[p.obj.objgen] = i + 1


def res(o: pikepdf.Object) -> pikepdf.Object:
    try:
        while o.is_indirect:
            o = o.get_object()
    except Exception:
        pass
    return o


def is_se(o: pikepdf.Object) -> bool:
    try:
        _ = o["/S"]
        return True
    except Exception:
        return False


def get_page_num(elem: pikepdf.Dictionary) -> int | None:
    """Get page number from /Pg reference."""
    pg = elem.get("/Pg")
    if pg is not None:
        pg_obj = res(pg)
        try:
            return page_map.get(pg_obj.objgen)
        except Exception:
            pass
    return None


leaf_idx = [0]  # reading order counter for leaf elements


def walk(e: pikepdf.Object, depth: int) -> None:
    e = res(e)
    if not is_se(e):
        return
    tag = str(e["/S"])

    # Collect MCIDs and field info from /K
    mcids: list[int] = []
    field_name = ""
    has_child_se = False
    k = e.get("/K")

    if k is not None:
        kr = res(k)
        items = list(kr) if isinstance(kr, pikepdf.Array) else [kr]
        for it in items:
            itr = res(it)
            # Integer MCID
            if isinstance(itr, (int, pikepdf.objects.Object)):
                try:
                    val = int(itr)
                    mcids.append(val)
                    continue
                except (TypeError, ValueError):
                    pass
            # Dict items
            try:
                if is_se(itr):
                    has_child_se = True
                    continue
                obj_type = str(itr.get("/Type", ""))
                if obj_type == "/MCR":
                    mcid_val = itr.get("/MCID")
                    if mcid_val is not None:
                        mcids.append(int(mcid_val))
                elif obj_type == "/OBJR":
                    obj = res(itr["/Obj"])
                    t = str(obj.get("/T", ""))
                    if t:
                        field_name = t
            except Exception:
                pass

    page = get_page_num(e)
    page_str = f"p{page}" if page else ""

    # Alt text
    alt = ""
    try:
        a = e.get("/Alt")
        if a is not None:
            alt = str(a)[:50]
    except Exception:
        pass

    indent = "  " * depth
    is_leaf = (mcids or field_name) and not has_child_se

    if is_leaf:
        n = leaf_idx[0]
        leaf_idx[0] += 1
        mcid_str = f"mcid={','.join(str(m) for m in mcids)}" if mcids else ""
        field_str = f"[{field_name}]" if field_name else ""
        alt_str = f'alt="{alt}"' if alt else ""
        parts = [p for p in [page_str, mcid_str, field_str, alt_str] if p]
        print(f"{n:3d} {indent}<{tag}>  {' '.join(parts)}")
    else:
        # Container - no number, just show structure
        print(f"    {indent}<{tag}>  {page_str}")

    # Recurse into child structure elements
    if k is not None and has_child_se:
        kr = res(k)
        items = list(kr) if isinstance(kr, pikepdf.Array) else [kr]
        for c in items:
            cr = res(c)
            if is_se(cr):
                walk(cr, depth + 1)


# Print header
print("Reading Order Derived from Structure Tree (/K arrays)")
print("=" * 70)
print("Numbered entries = leaf elements (what a screen reader reads)")
print("Unnumbered entries = containers (organize the tree)")
print()

# Start walk
top_k = res(root["/K"])
if isinstance(top_k, pikepdf.Array):
    for item in top_k:
        item = res(item)
        if is_se(item):
            walk(item, 0)
else:
    walk(top_k, 0)

print()
print(f"Total leaf elements in reading order: {leaf_idx[0]}")
print()
print("NOTE: All /Form tags appear at positions 78+ (after ALL page content).")
print("A correct reading order would interleave fields with their labels.")
