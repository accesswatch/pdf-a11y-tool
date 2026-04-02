"""Analyze underscore fill-line content and empty spacing in P tags."""

import pikepdf
import pypdfium2

pdf_path = "Samples/Medication Self-Administration Authorization.pdf"
pf = pypdfium2.PdfDocument(pdf_path)

# Show the visual underscore problem
print("Underscore Fill-Line Analysis")
print("=" * 60)
print()

for pg_idx in range(3):
    page = pf[pg_idx]
    tp = page.get_textpage()
    full_text = tp.get_text_range()
    lines = full_text.split("\n")
    underscore_lines = []
    for i, line in enumerate(lines):
        if "___" in line:
            underscore_lines.append((i, line.strip()))
    if underscore_lines:
        print(f"Page {pg_idx + 1}: {len(underscore_lines)} lines with underscore fills")
        for li, text in underscore_lines:
            # Count underscores
            ucount = text.count("_")
            print(f"  line {li}: ({ucount} underscores) {text[:75]}")
        print()

pf.close()

# Now check the reading order dump to see how many P tags there are
# vs how many unique content items
pk = pikepdf.open(pdf_path)
root = pk.Root["/StructTreeRoot"]


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

doc_kids = res(doc["/K"])

tag_counts = {}
for child in doc_kids:
    child = res(child)
    if isinstance(child, pikepdf.Dictionary) and "/S" in child:
        tag = str(child["/S"]).lstrip("/")
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

print("Direct children of /Document by tag type:")
for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
    print(f"  {tag}: {count}")
print(f"  Total: {sum(tag_counts.values())}")

pk.close()
