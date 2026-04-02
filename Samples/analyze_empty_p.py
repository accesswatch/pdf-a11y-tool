"""Analyze P tags in the sample PDF to identify empty/spacing paragraphs."""

import pikepdf

pdf = pikepdf.open("Samples/Medication Self-Administration Authorization.pdf")
root = pdf.Root["/StructTreeRoot"]


def res(o):
    try:
        while o.is_indirect:
            o = o.get_object()
    except Exception:
        pass
    return o


top_k = res(root["/K"])
if isinstance(top_k, pikepdf.Array):
    doc = res(top_k[0])
else:
    doc = top_k

print("Doc tag:", str(doc.get("/S", "")))
kids = res(doc["/K"])
print(
    "Children type:",
    type(kids).__name__,
    "count:",
    len(kids) if isinstance(kids, pikepdf.Array) else 1,
)

# Examine each P tag
p_tags = []
for i, child in enumerate(kids):
    child = res(child)
    if not isinstance(child, pikepdf.Dictionary):
        continue
    s = str(child.get("/S", ""))
    if s not in ("/P", "P"):
        continue

    k = child.get("/K")
    mcids = []
    has_struct_children = False

    if k is not None:
        kr = res(k)
        if isinstance(kr, pikepdf.Array):
            for item in kr:
                item_r = res(item)
                if isinstance(item_r, pikepdf.Dictionary):
                    if "/S" in item_r:
                        has_struct_children = True
                    elif "/MCID" in item_r:
                        mcids.append(int(item_r["/MCID"]))
                else:
                    try:
                        mcids.append(int(item_r))
                    except (TypeError, ValueError):
                        pass
        elif isinstance(kr, pikepdf.Dictionary):
            if "/S" in kr:
                has_struct_children = True
            elif "/MCID" in kr:
                mcids.append(int(kr["/MCID"]))
        else:
            try:
                mcids.append(int(kr))
            except (TypeError, ValueError):
                pass

    pg = child.get("/Pg")
    page_num = "?"
    if pg is not None:
        pg_obj = res(pg)
        for pi, p in enumerate(pdf.pages):
            if p.obj.objgen == pg_obj.objgen:
                page_num = str(pi + 1)
                break

    p_tags.append(
        {
            "idx": i,
            "page": page_num,
            "mcids": mcids,
            "has_children": has_struct_children,
            "empty": len(mcids) == 0 and not has_struct_children,
        }
    )

print(f"Total /P tags as direct children of Document: {len(p_tags)}")
empty_count = sum(1 for p in p_tags if p["empty"])
print(f"Empty /P tags (no MCIDs, no children): {empty_count}")
print(f"/P tags with content: {len(p_tags) - empty_count}")
print()

# Show consecutive empty P tags
runs = []
current_run = []
for p in p_tags:
    if p["empty"]:
        current_run.append(p)
    else:
        if len(current_run) >= 1:
            runs.append(current_run)
        current_run = []
if current_run:
    runs.append(current_run)

print(f"Runs of empty P tags: {len(runs)}")
for r in runs:
    idxs = [p["idx"] for p in r]
    print(f"  {len(r)} empty P(s) at child indices {idxs} (page {r[0]['page']})")
