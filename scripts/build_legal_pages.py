from pathlib import Path
import re
import html

ROOT = Path(__file__).resolve().parent.parent

SOURCES = {
    "privacy_en": ROOT / "legal/sources/privacy-policy.en.md",
    "terms_en": ROOT / "legal/sources/terms.en.md",
    "privacy_ko": ROOT / "legal/sources/privacy-policy.ko.md",
    "terms_ko": ROOT / "legal/sources/terms.ko.md",
}

PAGES = {
    "privacy_en": {
        "out": ROOT / "privacy-policy/index.html",
        "title": "Moss Labs | Privacy Policy (EN)",
        "doc_title": "Privacy Policy (EN)",
        "lang": "en",
        "switch_label": "한국어 보기",
        "switch_href": "../ko/privacy-policy/index.html",
        "home_href": "../index.html",
        "assets_prefix": "../",
    },
    "terms_en": {
        "out": ROOT / "terms/index.html",
        "title": "Moss Labs | Terms (EN)",
        "doc_title": "Terms (EN)",
        "lang": "en",
        "switch_label": "한국어 보기",
        "switch_href": "../ko/terms/index.html",
        "home_href": "../index.html",
        "assets_prefix": "../",
    },
    "privacy_ko": {
        "out": ROOT / "ko/privacy-policy/index.html",
        "title": "Moss Labs | Privacy Policy (KO)",
        "doc_title": "Privacy Policy (KO)",
        "lang": "ko",
        "switch_label": "View English",
        "switch_href": "../../privacy-policy/index.html",
        "home_href": "../../index.html",
        "assets_prefix": "../../",
    },
    "terms_ko": {
        "out": ROOT / "ko/terms/index.html",
        "title": "Moss Labs | Terms (KO)",
        "doc_title": "Terms (KO)",
        "lang": "ko",
        "switch_label": "View English",
        "switch_href": "../../terms/index.html",
        "home_href": "../../index.html",
        "assets_prefix": "../../",
    },
}

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
URL_RE = re.compile(r"https?://[^\s<]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
TABLE_ALIGN_RE = re.compile(r"^:?-{3,}:?$")


def format_inline(text: str) -> str:
    text = text.replace(r"\.", ".")
    escaped = html.escape(text)
    escaped = BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    escaped = ITALIC_RE.sub(lambda m: f"<em>{m.group(1)}</em>", escaped)

    def repl_url(match: re.Match[str]) -> str:
        url = match.group(0)
        trail = ""
        while url:
            if url[-1] in ",.;":
                trail = url[-1] + trail
                url = url[:-1]
                continue
            if url[-1] == ")" and url.count(")") > url.count("("):
                trail = ")" + trail
                url = url[:-1]
                continue
            break

        return (
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>{trail}'
        )

    escaped = URL_RE.sub(repl_url, escaped)
    return escaped


def markdown_to_html(md_text: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def next_nonempty(start_idx: int) -> str:
        for j in range(start_idx, len(lines)):
            nxt = lines[j].strip()
            if nxt:
                return nxt
        return ""

    def is_bullet(line: str) -> bool:
        return line.startswith("• ") or line.startswith("- ")

    def is_bullet(line: str) -> bool:
        return line.startswith("• ") or line.startswith("- ")

    def split_table_row(line: str) -> list[str]:
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [cell.strip() for cell in s.split("|")]

    def is_table_divider(line: str) -> bool:
        cells = split_table_row(line)
        if not cells:
            return False
        for cell in cells:
            if not TABLE_ALIGN_RE.fullmatch(cell):
                return False
        return True

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            if in_ul:
                nxt = next_nonempty(i + 1)
                if is_bullet(nxt):
                    i += 1
                    continue
                close_ul()
            i += 1
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            close_ul()
            level = len(heading_match.group(1))
            text = format_inline(heading_match.group(2).strip())
            out.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if stripped.startswith("|") and next_line.startswith("|") and is_table_divider(next_line):
            close_ul()
            header_cells = split_table_row(stripped)
            out.append("<table>")
            out.append("<thead>")
            out.append("<tr>")
            for cell in header_cells:
                out.append(f"<th>{format_inline(cell)}</th>")
            out.append("</tr>")
            out.append("</thead>")
            out.append("<tbody>")

            i += 2
            while i < len(lines):
                row = lines[i].strip()
                if not row or not row.startswith("|"):
                    break
                row_cells = split_table_row(row)
                if len(row_cells) < len(header_cells):
                    row_cells.extend([""] * (len(header_cells) - len(row_cells)))
                elif len(row_cells) > len(header_cells):
                    row_cells = row_cells[: len(header_cells)]

                out.append("<tr>")
                for cell in row_cells:
                    out.append(f"<td>{format_inline(cell)}</td>")
                out.append("</tr>")
                i += 1

            out.append("</tbody>")
            out.append("</table>")
            continue

        if is_bullet(stripped):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            item = stripped[2:].strip()
            out.append(f"<li>{format_inline(item)}</li>")
            i += 1
            continue

        close_ul()
        out.append(f"<p>{format_inline(stripped)}</p>")
        i += 1

    close_ul()
    return "\n".join(out)


def build_page(page: dict[str, str], body_html: str) -> str:
    assets_prefix = page["assets_prefix"]
    return f"""<!doctype html>
<html lang=\"{page['lang']}\"> 
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>{html.escape(page['title'])}</title>
    <link rel=\"icon\" type=\"image/png\" href=\"{assets_prefix}assets/images/mossili-logo.png\" />
    <link rel=\"stylesheet\" href=\"{assets_prefix}assets/css/styles.css\" />
  </head>
  <body>
    <main>
      <section class=\"card\" aria-labelledby=\"doc-title\">
        <h1 id=\"doc-title\" class=\"title\">{html.escape(page['doc_title'])}</h1>
        <div class=\"doc-links\">
          <a class=\"doc-link\" href=\"{page['home_href']}\">Back to Home</a>
          <a class=\"doc-link\" href=\"{page['switch_href']}\">{html.escape(page['switch_label'])}</a>
        </div>
      </section>

      <section class=\"card doc-body\">
{body_html}
      </section>
    </main>
  </body>
</html>
"""


def main() -> None:
    for key, src in SOURCES.items():
        md = src.read_text(encoding="utf-8")
        body_html = markdown_to_html(md)
        indented = "\n".join(("        " + ln) if ln else "" for ln in body_html.splitlines())
        page = PAGES[key]
        out_html = build_page(page, indented)
        Path(page["out"]).write_text(out_html, encoding="utf-8")
        print(page["out"])


if __name__ == "__main__":
    main()
