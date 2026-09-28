#!/usr/bin/env python3
"""Fill the review-slide template. This is the only way to produce a review PPT.

The script edits text inside the template's existing runs and picture frames.
It does not create text boxes, so the template font, size, and color stay.
"""

import argparse
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "review-slide-template.pptx"
FINDING_SLIDE = "ppt/slides/slide19.xml"
FINDING_RELS = "ppt/slides/_rels/slide19.xml.rels"
# Left body box is about 6.9 by 4.5 inches at the template's 14 pt body style.
BODY_CHAR_BUDGET = 1000
# The existing subtitle line is 7.28 in wide at 18 pt. 60 characters stays on that one line.
SUBTITLE_CHAR_LIMIT = 60
DEFAULT_TITLE = "Design review report"


def escape_xml(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def set_shape_text(xml, name, text):
    marker = f'name="{name}"'
    index = xml.find(marker)
    if index < 0:
        raise SystemExit(f"template shape {name} is missing")
    start = xml.rfind("<p:sp", 0, index)
    end = xml.find("</p:sp>", index) + len("</p:sp>")
    block = xml[start:end]
    matches = list(re.finditer(r"(<a:t(?:\s[^>]*)?>)(.*?)(</a:t>)", block, flags=re.S))
    if not matches:
        raise SystemExit(f"template shape {name} has no text run")
    pieces = []
    cursor = 0
    escaped = escape_xml(text)
    for number, match in enumerate(matches):
        pieces.append(block[cursor:match.start(2)])
        pieces.append(escaped if number == 0 else "")
        cursor = match.end(2)
    pieces.append(block[cursor:])
    return xml[:start] + "".join(pieces) + xml[end:]


SUBTITLE_COLORS = {
    "critical": "C62828",
    "warning": "E65100",
    "info": "1565C0",
    "accept": "2E7D32",
}


def set_subtitle_color(xml, severity):
    color = SUBTITLE_COLORS.get(str(severity).strip().lower())
    if color is None:
        names = ", ".join(SUBTITLE_COLORS)
        raise SystemExit(f"severity must be one of {names}")
    marker = 'name="Subtitle"'
    index = xml.find(marker)
    if index < 0:
        raise SystemExit("template shape Subtitle is missing")
    start = xml.rfind("<p:sp", 0, index)
    end = xml.find("</p:sp>", index) + len("</p:sp>")
    block = xml[start:end]
    updated, count = re.subn(r'(<a:srgbClr val=")[0-9A-Fa-f]{6}(")', rf"\g<1>{color}\2", block, count=1)
    if count != 1:
        raise SystemExit("subtitle has no font color to replace")
    # The layout's paragraph mark is gray and italic. PowerPoint uses that mark
    # for the visible subtitle unless this slide carries the same color on the
    # paragraph style and on the paragraph end mark.
    style = (
        '<a:lstStyle><a:lvl1pPr algn="l"><a:buNone/>'
        f'<a:defRPr sz="1800" b="1" i="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        '<a:latin typeface="Arial"/><a:ea typeface="Arial"/><a:cs typeface="Arial"/>'
        '</a:defRPr></a:lvl1pPr></a:lstStyle>'
    )
    updated = updated.replace("<a:lstStyle/>", style, 1)
    end_mark = (
        f'<a:endParaRPr lang="en-US" sz="1800" b="1" i="0" dirty="0">'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        '<a:latin typeface="Arial"/><a:ea typeface="Arial"/><a:cs typeface="Arial"/>'
        '</a:endParaRPr>'
    )
    updated = updated.replace("</a:r></a:p>", f"</a:r>{end_mark}</a:p>", 1)
    return xml[:start] + updated + xml[end:]


def remove_pic(xml, name):
    marker = f'name="{name}"'
    index = xml.find(marker)
    if index < 0:
        return xml
    start = xml.rfind("<p:pic", 0, index)
    end = xml.find("</p:pic>", index) + len("</p:pic>")
    return xml[:start] + xml[end:]


def pic_embed(xml, name):
    marker = f'name="{name}"'
    index = xml.find(marker)
    start = xml.rfind("<p:pic", 0, index)
    end = xml.find("</p:pic>", index)
    match = re.search(r'r:embed="([^"]+)"', xml[start:end])
    if not match:
        raise SystemExit(f"template picture {name} has no image relationship")
    return match.group(1)


def retarget(rels, relationship_id, target):
    pattern = rf'(<Relationship\s+Id="{relationship_id}"[^>]*\sTarget=")[^"]+(")'
    updated, count = re.subn(pattern, rf"\1{target}\2", rels, count=1)
    if count != 1:
        raise SystemExit(f"cannot retarget {relationship_id}")
    return updated


def split_body(text):
    remaining = " ".join(str(text).split())
    if len(remaining) <= BODY_CHAR_BUDGET:
        return [remaining]
    parts = []
    while remaining:
        if len(remaining) <= BODY_CHAR_BUDGET:
            parts.append(remaining)
            break
        window = remaining[:BODY_CHAR_BUDGET]
        dot = window.rfind(". ")
        if dot >= 80:
            parts.append(remaining[: dot + 1].strip())
            remaining = remaining[dot + 2 :].strip()
            continue
        space = window.rfind(" ")
        if space < 40:
            space = BODY_CHAR_BUDGET
        parts.append(remaining[:space].strip())
        remaining = remaining[space:].strip()
    return [part for part in parts if part]


def load_template():
    if not TEMPLATE.is_file():
        raise SystemExit(f"missing template {TEMPLATE}")
    with zipfile.ZipFile(TEMPLATE) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def add_slide_relationship(files, slide_name):
    rels_name = "ppt/_rels/presentation.xml.rels"
    rels = files[rels_name].decode("utf-8")
    numbers = [int(value) for value in re.findall(r'Id="rId(\d+)"', rels)]
    relationship_id = f"rId{(max(numbers) if numbers else 0) + 1}"
    target = slide_name.split("/", 1)[1]
    insertion = (
        f'<Relationship Id="{relationship_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        f'Target="{target}"/>'
    )
    rels = rels.replace("</Relationships>", insertion + "</Relationships>")
    files[rels_name] = rels.encode("utf-8")
    presentation = files["ppt/presentation.xml"].decode("utf-8")
    slide_ids = [int(value) for value in re.findall(r'<p:sldId id="(\d+)"', presentation)]
    slide_id = (max(slide_ids) if slide_ids else 256) + 1
    presentation = presentation.replace(
        "</p:sldIdLst>",
        f'<p:sldId id="{slide_id}" r:id="{relationship_id}"/></p:sldIdLst>',
    )
    files["ppt/presentation.xml"] = presentation.encode("utf-8")
    content_types = files["[Content_Types].xml"].decode("utf-8")
    override = (
        f'<Override PartName="/{slide_name}" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
    )
    if override not in content_types:
        content_types = content_types.replace("</Types>", override + "</Types>")
        files["[Content_Types].xml"] = content_types.encode("utf-8")


def require_subtitle_line(text):
    line = " ".join(str(text).split())
    if not line:
        raise SystemExit("each slide needs a one-line subtitle")
    if len(line) > SUBTITLE_CHAR_LIMIT:
        raise SystemExit(
            f"the subtitle is {len(line)} characters; keep it to {SUBTITLE_CHAR_LIMIT} so it stays on one line"
        )
    return line


def image_pixel_size(blob):
    if blob.startswith(b"\x89PNG\r\n\x1a\n") and blob[12:16] == b"IHDR":
        width, height = struct.unpack(">II", blob[16:24])
        return width, height
    if blob.startswith(b"\xff\xd8"):
        index = 2
        while index + 8 < len(blob):
            if blob[index] != 0xFF:
                index += 1
                continue
            marker = blob[index + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack(">HH", blob[index + 5:index + 9])
                return width, height
            segment = struct.unpack(">H", blob[index + 2:index + 4])[0]
            index += 2 + segment
    raise SystemExit("could not read image width and height; use png or jpeg")


def fit_pic(xml, name, width_px, height_px):
    """Keep the bitmap's aspect ratio inside the template frame.

    The frame uses stretch-to-fill, so a different aspect is otherwise drawn
    distorted. Shrink one side and center the picture. It stays inside the frame.
    """
    marker = f'name="{name}"'
    index = xml.find(marker)
    start = xml.rfind("<p:pic", 0, index)
    end = xml.find("</p:pic>", index) + len("</p:pic>")
    block = xml[start:end]
    off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', block)
    ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', block)
    if not off or not ext:
        raise SystemExit(f"template picture {name} has no frame")
    x, y = int(off.group(1)), int(off.group(2))
    cx, cy = int(ext.group(1)), int(ext.group(2))
    image_ar = width_px / height_px
    frame_ar = cx / cy
    if image_ar >= frame_ar:
        new_cx = cx
        new_cy = max(1, int(round(cx / image_ar)))
    else:
        new_cy = cy
        new_cx = max(1, int(round(cy * image_ar)))
    new_x = x + (cx - new_cx) // 2
    new_y = y + (cy - new_cy) // 2
    block = block.replace(off.group(0), f'<a:off x="{new_x}" y="{new_y}"/>', 1)
    block = re.sub(
        r'<a:ext cx="\d+" cy="\d+"/>',
        f'<a:ext cx="{new_cx}" cy="{new_cy}"/>',
        block,
        count=1,
    )
    return xml[:start] + block + xml[end:]


def image_extension(path):
    suffix = path.suffix.lower()
    if suffix in (".png", ".jpeg"):
        return suffix
    if suffix == ".jpg":
        return ".jpeg"
    raise SystemExit(f"image must be png or jpeg: {path}")


def fill_finding(files, slide_xml_name, rels_name, finding, index):
    xml = files[slide_xml_name].decode("utf-8")
    xml = set_shape_text(xml, "Eyebrow", finding["eyebrow"])
    xml = set_shape_text(xml, "Subtitle", finding["subtitle"])
    xml = set_subtitle_color(xml, finding["severity"])
    xml = set_shape_text(xml, "Body", finding["body"])
    images = list(finding.get("images") or [])
    if finding.get("image"):
        images.append(finding["image"])
    rels = files[rels_name].decode("utf-8")
    slots = (("Evidence1", 1), ("Evidence2", 2))
    for name, slot in slots:
        if slot > len(images):
            xml = remove_pic(xml, name)
            continue
        path = Path(images[slot - 1])
        if not path.is_file():
            raise SystemExit(f"missing image {path}")
        embed = pic_embed(xml, name)
        blob = path.read_bytes()
        width_px, height_px = image_pixel_size(blob)
        xml = fit_pic(xml, name, width_px, height_px)
        media_name = f"ppt/media/finding-{index + 1}-{slot}{image_extension(path)}"
        files[media_name] = blob
        rels = retarget(rels, embed, "../" + media_name.split("/", 1)[1])
    table = validate_table(finding.get("table"))
    if table:
        xml = add_table(xml, table[0], table[1])
    files[slide_xml_name] = xml.encode("utf-8")
    files[rels_name] = rels.encode("utf-8")


def validate_table(table):
    if not table:
        return None
    columns = [str(column).strip() for column in table.get("columns") or []]
    rows = table.get("rows") or []
    if len(columns) < 2 or not rows:
        raise SystemExit("a table needs at least two columns and one row")
    for row in rows:
        if len(row) != len(columns):
            raise SystemExit("every table row must have one cell per column")
    return columns, [[str(cell).strip() for cell in row] for row in rows]


def _cell(text, header):
    size = "1200" if header else "1100"
    weight = ' b="1"' if header else ""
    ink = "FFFFFF" if header else "1A1A1A"
    fill = "1A1A1A" if header else "F7F7F7"
    safe = escape_xml(text)
    return (
        "<a:tc><a:txBody><a:bodyPr anchor=\"ctr\" lIns=\"60000\" rIns=\"60000\" tIns=\"30000\" bIns=\"30000\"/>"
        "<a:lstStyle/><a:p><a:r>"
        f'<a:rPr lang="en-US" sz="{size}"{weight} dirty="0">'
        f'<a:solidFill><a:srgbClr val="{ink}"/></a:solidFill>'
        '<a:latin typeface="Arial"/><a:ea typeface="Arial"/><a:cs typeface="Arial"/>'
        f"</a:rPr><a:t>{safe}</a:t></a:r></a:p></a:txBody>"
        f'<a:tcPr><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>'
    )


def add_table(xml, columns, rows):
    marker = 'name="Body"'
    index = xml.find(marker)
    if index < 0:
        raise SystemExit("template shape Body is missing")
    start = xml.rfind("<p:sp", 0, index)
    end = xml.find("</p:sp>", index) + len("</p:sp>")
    block = xml[start:end]
    off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', block)
    ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', block)
    if not off or not ext:
        raise SystemExit("template shape Body has no frame")
    x, y = int(off.group(1)), int(off.group(2))
    cx, cy = int(ext.group(1)), int(ext.group(2))
    verdict_cy = min(820000, cy // 4)
    gap = 80000
    table_y = y + verdict_cy + gap
    table_cy = max(1, cy - verdict_cy - gap)
    block = re.sub(
        r'<a:ext cx="\d+" cy="\d+"/>',
        f'<a:ext cx="{cx}" cy="{verdict_cy}"/>',
        block,
        count=1,
    )
    xml = xml[:start] + block + xml[end:]
    row_count = len(rows) + 1
    row_h = max(1, table_cy // row_count)
    col_w = max(1, cx // len(columns))
    grid = "".join(f'<a:gridCol w="{col_w}"/>' for _ in columns)
    header = "".join(_cell(column, True) for column in columns)
    body_rows = []
    for row in rows:
        cells = "".join(_cell(cell, False) for cell in row)
        body_rows.append(f'<a:tr h="{row_h}">{cells}</a:tr>')
    table = (
        '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="40" name="Table"/>'
        '<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/>'
        "</p:nvGraphicFramePr>"
        f'<p:xfrm><a:off x="{x}" y="{table_y}"/><a:ext cx="{cx}" cy="{table_cy}"/></p:xfrm>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl>'
        f"<a:tblPr/><a:tblGrid>{grid}</a:tblGrid>"
        f'<a:tr h="{row_h}">{header}</a:tr>'
        f'{"".join(body_rows)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
    )
    tree = "</p:spTree>"
    at = xml.rfind(tree)
    return xml[:at] + table + xml[at:]


def build_deck(data, output):
    for field in ("project_code", "designer", "reviewer", "review_date"):
        if not str(data.get(field, "")).strip():
            raise SystemExit(f"{field} is required; ask for it instead of inventing a value")
    if not re.fullmatch(r"\d{8}", str(data["review_date"])):
        raise SystemExit("review_date must be YYYYMMDD")
    title = data.get("document_title") or DEFAULT_TITLE
    raw_slides = data.get("slides") or []
    if not raw_slides:
        raise SystemExit("slides must contain at least one finding with a location and a verdict")

    expanded = []
    for slide in raw_slides:
        for key in ("eyebrow", "subtitle", "body", "severity"):
            if not str(slide.get(key, "")).strip():
                raise SystemExit(f"each slide needs {key}")
        subtitle = require_subtitle_line(slide["subtitle"])
        images = list(slide.get("images") or [])
        if slide.get("image"):
            images.append(slide["image"])
        if slide.get("single_page"):
            chunks = [slide["body"]]
        else:
            chunks = split_body(slide["body"])
        groups = [images[start:start + 2] for start in range(0, len(images), 2)] or [[]]
        pages = max(len(chunks), len(groups))
        for page in range(pages):
            expanded.append({
                "eyebrow": slide["eyebrow"],
                "subtitle": subtitle,
                "severity": slide["severity"],
                "body": chunks[page] if page < len(chunks) else chunks[-1],
                "images": groups[page] if page < len(groups) else [],
                "table": slide.get("table") if page == 0 else None,
            })

    files = load_template()
    prototype_xml = files[FINDING_SLIDE]
    prototype_rels = files[FINDING_RELS]
    cover = files["ppt/slides/slide1.xml"].decode("utf-8")
    replacements = {
        "{{PROJECT_CODE}}": data["project_code"],
        "{{DESIGNER}}": data["designer"],
        "{{REVIEWER}}": data["reviewer"],
        "{{DATE}}": data["review_date"],
        "{{DOC_TITLE}}": title,
    }
    for token, value in replacements.items():
        if token not in cover:
            raise SystemExit(f"template is missing {token}")
        cover = cover.replace(token, escape_xml(value), 1)
    files["ppt/slides/slide1.xml"] = cover.encode("utf-8")

    for index, finding in enumerate(expanded):
        if index == 0:
            slide_name = FINDING_SLIDE
            rels_name = FINDING_RELS
        else:
            slide_name = f"ppt/slides/slide{30 + index}.xml"
            rels_name = f"ppt/slides/_rels/slide{30 + index}.xml.rels"
            add_slide_relationship(files, slide_name)
        files[slide_name] = prototype_xml
        files[rels_name] = prototype_rels
        fill_finding(files, slide_name, rels_name, finding, index)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return output


def main(argv):
    parser = argparse.ArgumentParser(description="Fill the review PPT template from JSON")
    parser.add_argument("deck_json")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    data = json.loads(Path(args.deck_json).read_text(encoding="utf-8"))
    build_deck(data, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
