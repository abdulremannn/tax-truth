def to_markdown(extraction: dict, doc_title: str = "Document") -> str:
    """Convert extraction result into clean Markdown."""
    lines = [f"# {doc_title}\n"]

    for page in extraction["pages"]:
        lines.append(f"## Page {page['page']} ({page['source']})\n")
        lines.append(page["text"].strip())
        lines.append("")

    if extraction["tables"]:
        lines.append("## Extracted Tables\n")
        for t in extraction["tables"]:
            lines.append(f"### Page {t['page']} Tables\n")
            for table in t["tables"]:
                lines.append(_table_to_markdown(table))
                lines.append("")

    return "\n".join(lines)


def _table_to_markdown(table: list[list]) -> str:
    if not table:
        return ""
    header = table[0]
    rows = table[1:]
    md = ["| " + " | ".join(str(c or "") for c in header) + " |"]
    md.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows:
        md.append("| " + " | ".join(str(c or "") for c in row) + " |")
    return "\n".join(md)
