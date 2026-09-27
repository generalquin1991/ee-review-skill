#!/usr/bin/env python3
"""Crop a KiCad schematic symbol, or mark a box on an existing image.

This is the only schematic-crop and red-box entry point. Do not draw review
figures with a one-off script.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PAPER_MM = {
    "A4": (297.0, 210.0),
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
    "A0": (1189.0, 841.0),
    "A": (279.4, 215.9),
    "B": (431.8, 279.4),
    "C": (558.8, 431.8),
    "D": (863.6, 558.8),
}

KICAD_CLI_CANDIDATES = (
    "kicad-cli",
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
)


def strip_lib_symbols(text):
    start = text.find("(lib_symbols")
    if start < 0:
        return text
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[:start] + text[index + 1 :]
    return text


def _symbol_blocks(text):
    index = 0
    while True:
        found = text.find("(symbol", index)
        if found < 0:
            return
        after = text[found + 7 : found + 8]
        if after and (after.isalnum() or after == "_"):
            index = found + 7
            continue
        depth = 0
        for cursor in range(found, len(text)):
            char = text[cursor]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    yield text[found : cursor + 1]
                    index = cursor + 1
                    break
        else:
            return


def paper_size_mm(text):
    match = re.search(r'\(paper\s+"([^"]+)"([^)]*)\)', text)
    if not match:
        return PAPER_MM["A4"]
    name = match.group(1)
    extras = [float(value) for value in re.findall(r"[-+]?\d+(?:\.\d+)?", match.group(2))]
    if name == "User" and len(extras) >= 2:
        return extras[0], extras[1]
    return PAPER_MM.get(name, PAPER_MM["A4"])


def symbol_positions(text):
    positions = {}
    for block in _symbol_blocks(strip_lib_symbols(text)):
        reference = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', block)
        point = re.search(r'\(at\s+([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)', block)
        if not reference or not point:
            continue
        positions.setdefault(reference.group(1), []).append((float(point.group(1)), float(point.group(2))))
    return positions


def crop_box_mm(points, padding_mm, page_mm):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    width, height = page_mm
    left = max(0.0, min(xs) - padding_mm)
    top = max(0.0, min(ys) - padding_mm)
    right = min(width, max(xs) + padding_mm)
    bottom = min(height, max(ys) + padding_mm)
    if right <= left or bottom <= top:
        raise SystemExit("symbol crop box is empty")
    return left, top, right, bottom


def find_kicad_cli():
    for candidate in KICAD_CLI_CANDIDATES:
        if candidate == "kicad-cli":
            found = shutil.which(candidate)
            if found:
                return found
        elif Path(candidate).is_file():
            return candidate
    raise SystemExit(
        "kicad-cli was not found. Install KiCad, or export a schematic PDF and pass it with --image."
    )


def export_pdf(kicad_cli, schematic, pdf_path):
    completed = subprocess.run(
        [kicad_cli, "sch", "export", "pdf", "--output", str(pdf_path), str(schematic)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not pdf_path.is_file():
        detail = (completed.stderr or completed.stdout or "").strip()
        raise SystemExit(f"kicad-cli sch export pdf failed: {detail}")


def rasterize_pdf(pdf_path, png_path):
    if shutil.which("pdftoppm"):
        prefix = png_path.with_suffix("")
        completed = subprocess.run(
            ["pdftoppm", "-png", "-singlefile", "-r", "200", str(pdf_path), str(prefix)],
            capture_output=True,
            text=True,
            check=False,
        )
        produced = prefix.with_suffix(".png")
        if completed.returncode == 0 and produced.is_file():
            if produced != png_path:
                produced.replace(png_path)
            return
    if shutil.which("sips"):
        completed = subprocess.run(
            ["sips", "-s", "format", "png", str(pdf_path), "--out", str(png_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and png_path.is_file():
            return
    raise SystemExit("could not rasterize the schematic PDF; install poppler (pdftoppm) or use macOS sips")


def require_pillow():
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SystemExit(
            "Pillow is required for schematic crops. Install it with "
            "python3 -m pip install -r requirements-pptx.txt"
        ) from exc
    return Image, ImageDraw


def annotate(image, mark, label):
    if not mark:
        return image
    image = image.convert("RGBA")
    draw = require_pillow()[1].Draw(image)
    margin = max(4, min(image.size) // 40)
    color = (220, 38, 38, 255)
    if mark == "box":
        draw.rectangle((margin, margin, image.width - margin - 1, image.height - margin - 1), outline=color, width=4)
    elif mark == "arrow":
        tip = (image.width // 2, image.height // 3)
        start = (margin * 3, image.height - margin * 3)
        draw.line((start, tip), fill=color, width=4)
        draw.polygon(
            [(tip[0], tip[1] - 8), (tip[0] - 8, tip[1] + 10), (tip[0] + 8, tip[1] + 10)],
            fill=color,
        )
    else:
        raise SystemExit("mark must be box or arrow")
    if label:
        draw.text((margin, image.height - margin * 3), label, fill=color)
    return image


def crop_png(png_path, box_mm, page_mm, output, mark, label):
    Image, _ = require_pillow()
    image = Image.open(png_path)
    width, height = image.size
    left = int(round(box_mm[0] / page_mm[0] * width))
    top = int(round(box_mm[1] / page_mm[1] * height))
    right = int(round(box_mm[2] / page_mm[0] * width))
    bottom = int(round(box_mm[3] / page_mm[1] * height))
    cropped = annotate(image.crop((left, top, right, bottom)), mark, label)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cropped.convert("RGB").save(output)
    return output


def mark_existing(image_path, box, output, mark, label):
    Image, _ = require_pillow()
    image = Image.open(image_path)
    if box:
        left, top, right, bottom = [int(value) for value in box.split(",")]
        image = image.crop((left, top, right, bottom))
    marked = annotate(image, mark, label)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    marked.convert("RGB").save(output)
    return output


def crop_schematic(schematic, reference, output, padding_mm, mark, label):
    text = Path(schematic).read_text(encoding="utf-8", errors="replace")
    positions = symbol_positions(text)
    if reference not in positions:
        known = ", ".join(sorted(positions)) or "(none)"
        raise SystemExit(f"{reference} is not a symbol reference in {schematic}; found {known}")
    page = paper_size_mm(text)
    box = crop_box_mm(positions[reference], padding_mm, page)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "sheet.pdf"
        png_path = Path(tmp) / "sheet.png"
        export_pdf(find_kicad_cli(), schematic, pdf_path)
        rasterize_pdf(pdf_path, png_path)
        return crop_png(png_path, box, page, output, mark, label)


def main(argv):
    parser = argparse.ArgumentParser(description="Crop a schematic symbol or mark an existing image")
    parser.add_argument("schematic", nargs="?", help="KiCad schematic to export and crop")
    parser.add_argument("--ref", help="Reference designator to crop, for example U6")
    parser.add_argument("--image", help="Existing PNG or JPEG to crop or mark")
    parser.add_argument("--box", help="Pixel crop left,top,right,bottom for --image")
    parser.add_argument("--padding-mm", type=float, default=25.0)
    parser.add_argument("--mark", choices=("box", "arrow"))
    parser.add_argument("--label", default="")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    if args.image:
        mark_existing(args.image, args.box, args.output, args.mark, args.label)
    elif args.schematic and args.ref:
        crop_schematic(args.schematic, args.ref, args.output, args.padding_mm, args.mark, args.label)
    else:
        parser.error("pass a schematic and --ref, or --image")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
