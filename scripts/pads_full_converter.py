#!/usr/bin/env python3
"""
PADS ASCII Full Converter for KiCad

Extends the route injector with:
  1. Board outline injection (Edge.Cuts)
  2. Silk screen text injection (F.SilkS)
  3. Documentation lines injection (F.Fab / Cmts.User)
  4. Copper zone creation (B.Cu) from board outline
  5. Per-pad solder paste/mask margin injection

Shares the route-injection coordinate transformation model used by pads_route_injector.py.

Usage:
    python3 pads_full_converter.py <pads_ascii.asc> <input.kicad_pcb> <output.kicad_pcb> [--max-transform-error <mm>]
"""

import argparse
import re
import sys
import math
from typing import List, Dict, Tuple, Optional

from pads_common import (
    DEFAULT_MAX_TRANSFORM_ERROR_MM,
    PadsPart,
    PadsRoutePoint,
    PadsViaDef,
    parse_pads_header,
    parse_pads_parts,
    parse_pads_routes,
    parse_pads_vias,
    read_pads_ascii,
    transform_error_allowed,
)


# ─── PADS ASCII PARSER ──────────────────────────────────────────────────────────

class PadsTextItem:
    def __init__(self, x, y, ori, level, height, width, mirrored, hjust, vjust, text):
        self.x = x
        self.y = y
        self.ori = ori
        self.level = level
        self.height = height
        self.width = width
        self.mirrored = mirrored
        self.hjust = hjust
        self.vjust = vjust
        self.text = text


class PadsLinePiece:
    def __init__(self, piece_type, corners, width, level, points):
        self.piece_type = piece_type  # OPEN, CLOSED, CIRCLE, BRDCLS, COPOPN
        self.corners = corners
        self.width = width
        self.level = level
        self.points = points  # list of (x, y)


class PadsLinesItem:
    def __init__(self, name, item_type, x, y, pieces_count, extra):
        self.name = name
        self.item_type = item_type  # LINES, BOARD
        self.x = x  # origin
        self.y = y
        self.pieces_count = pieces_count
        self.pieces = []


class PadsPadStack:
    def __init__(self, pad_num, stacks):
        self.pad_num = pad_num
        self.stacks = stacks  # list of (level, size, shape, extra)


class PadsDecal:
    def __init__(self, name, units, origin_x, origin_y):
        self.name = name
        self.units = units  # I or M
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.pad_stacks = {}  # pad_num -> PadsPadStack
        self.terminals = []  # terminal positions


class PadsAsciiParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.parts = {}
        self.routes = []
        self.route_nets = []
        self.via_defs = {}
        self.max_layer = 2
        self.units = 1
        self.text_items = []
        self.lines_items = []
        self.decals = {}
        self.part_types = {}  # ptype_name -> list of decal names
        self.thermal_points = []  # (x, y, layer, net)
        self.arptom = 114300  # global pad-to-mask annular ring

    def parse(self):
        lines, self.encoding = read_pads_ascii(self.filepath)
        header = parse_pads_header(lines, {"arptom": self.arptom})
        self.units = int(header["units"])
        self.max_layer = int(header["max_layer"])
        self.arptom = header["arptom"]
        self._parse_header(lines)
        self._parse_text(lines)
        self._parse_lines(lines)
        self.via_defs = parse_pads_vias(lines, PadsViaDef)
        self._parse_partdecals(lines)
        self._parse_parttypes(lines)
        self.parts = parse_pads_parts(lines, PadsPart)
        self.routes, self.route_nets = parse_pads_routes(lines, PadsRoutePoint, self.thermal_points)

    def _parse_header(self, lines):
        header = parse_pads_header(lines, {"arptom": self.arptom})
        self.units = int(header["units"])
        self.max_layer = int(header["max_layer"])
        self.arptom = header["arptom"]

    def _parse_text(self, lines):
        in_text = False
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith('*TEXT*'):
                in_text = True
                i += 1
                continue
            if in_text:
                if s.startswith('*') and not s.startswith('*REMARK*'):
                    break
                if not s or s.startswith('*REMARK*'):
                    i += 1
                    continue
                # Parse: XLOC YLOC ORI LEVEL HEIGHT WIDTH MIRRORED HJUST VJUST .REUSE. INSTANCENM
                p = s.split()
                if len(p) >= 10:
                    try:
                        x = float(p[0])
                        y = float(p[1])
                        ori = float(p[2])
                        level = int(p[3])
                        height = float(p[4])
                        width = float(p[5])
                        mirrored = p[6]
                        hjust = p[7]
                        vjust = p[8]
                        # Next line: FONTSTYLE FONTFACE
                        # Line after: actual text
                        i += 1  # skip font line
                        if i < len(lines):
                            text_line = lines[i].strip()
                            # Skip "Regular <Romansim Stroke Font>" font lines
                            if text_line.startswith('Regular') or text_line.startswith('Stroke'):
                                i += 1
                                if i < len(lines):
                                    text_line = lines[i].strip()
                            self.text_items.append(PadsTextItem(
                                x, y, ori, level, height, width,
                                mirrored, hjust, vjust, text_line
                            ))
                    except (ValueError, IndexError):
                        pass
            i += 1

    def _parse_lines(self, lines):
        in_lines = False
        current_item = None
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith('*LINES*'):
                in_lines = True
                i += 1
                continue
            if in_lines:
                if s.startswith('*') and not s.startswith('*REMARK*'):
                    if current_item:
                        self.lines_items.append(current_item)
                        current_item = None
                    break
                if not s or s.startswith('*REMARK*'):
                    i += 1
                    continue

                # Check if this is a new item header
                # Format: NAME TYPE XLOC YLOC PIECES ...
                p = s.split()
                if len(p) >= 5 and (p[1] in ('LINES', 'BOARD', 'COPPER', 'DRAFTING')):
                    # New item
                    if current_item:
                        self.lines_items.append(current_item)
                    try:
                        name = p[0]
                        item_type = p[1]
                        x = float(p[2])
                        y = float(p[3])
                        pieces = int(p[4])
                        current_item = PadsLinesItem(name, item_type, x, y, pieces, p[5:])
                    except (ValueError, IndexError):
                        current_item = None
                elif current_item is not None:
                    # Parse piece: PIECETYPE CORNERS WIDTH LEVEL [RESTRICTIONS]
                    piece_type = p[0]
                    if piece_type in ('OPEN', 'CLOSED', 'CIRCLE', 'BRDCLS', 'COPOPN'):
                        try:
                            corners = int(p[1])
                            width = float(p[2])
                            level = int(p[3]) if len(p) > 3 else 0
                            # Read corner coordinates
                            points = []
                            for j in range(corners):
                                if i + 1 + j < len(lines):
                                    coord_line = lines[i + 1 + j].strip()
                                    cp = coord_line.split()
                                    if len(cp) >= 2:
                                        px = float(cp[0])
                                        py = float(cp[1])
                                        points.append((px, py))
                            # Skip consumed coordinate lines
                            i += corners
                            current_item.pieces.append(
                                PadsLinePiece(piece_type, corners, width, level, points)
                            )
                        except (ValueError, IndexError):
                            pass
            i += 1

        if current_item:
            self.lines_items.append(current_item)

    def _parse_vias(self, lines):
        self.via_defs = parse_pads_vias(lines, PadsViaDef)

    def _parse_partdecals(self, lines):
        in_decal = False
        current_decal = None
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith('*PARTDECAL*'):
                in_decal = True
                i += 1
                continue
            if in_decal:
                if s.startswith('*') and not s.startswith('*REMARK*'):
                    break
                if not s or s.startswith('*REMARK*'):
                    i += 1
                    continue

                p = s.split()
                # Decal header: NAME UNITS ORIX ORIY PIECES TERMINALS STACKS TEXT LABELS
                if len(p) >= 2 and p[1] in ('I', 'M') and not p[0].startswith('-'):
                    if current_decal:
                        self.decals[current_decal.name] = current_decal
                    try:
                        name = p[0]
                        units = p[1]
                        orix = float(p[2]) if len(p) > 2 else 0
                        oriy = float(p[3]) if len(p) > 3 else 0
                        current_decal = PadsDecal(name, units, orix, oriy)
                    except (ValueError, IndexError):
                        current_decal = None
                elif current_decal is not None:
                    # Check for PAD line: PAD pad_num num_stacks
                    if p[0] == 'PAD' and len(p) >= 3:
                        try:
                            pad_num = int(p[1])
                            num_stacks = int(p[2])
                            stacks = []
                            for j in range(num_stacks):
                                if i + 1 + j < len(lines):
                                    sl = lines[i + 1 + j].strip()
                                    sp = sl.split()
                                    if len(sp) >= 3:
                                        level = int(sp[0])
                                        size = float(sp[1])
                                        shape = sp[2]
                                        extra = sp[3:] if len(sp) > 3 else []
                                        stacks.append((level, size, shape, extra))
                            i += num_stacks
                            current_decal.pad_stacks[pad_num] = PadsPadStack(pad_num, stacks)
                        except (ValueError, IndexError):
                            pass
                    # Also parse terminal positions: T<tx> <ty> <nmx> <nmy> <pinnum>
                    elif p[0].startswith('T') and len(p) >= 5:
                        try:
                            tx = float(p[1])
                            ty = float(p[2])
                            current_decal.terminals.append((tx, ty, p[4] if len(p) > 4 else ''))
                        except (ValueError, IndexError):
                            pass
            i += 1

        if current_decal:
            self.decals[current_decal.name] = current_decal

    def _parse_parttypes(self, lines):
        in_ptype = False
        for line in lines:
            s = line.strip()
            if s.startswith('*PARTTYPE*'):
                in_ptype = True
                continue
            if in_ptype:
                if s.startswith('*') and not s.startswith('*REMARK*'):
                    break
                if not s or s.startswith('*REMARK*'):
                    continue
                p = s.split()
                if len(p) >= 3:
                    name = p[0]
                    decal_field = p[1]
                    # Decal field is colon-separated list
                    decals = decal_field.split(':')
                    self.part_types[name] = decals

    def _parse_parts(self, lines):
        self.parts = parse_pads_parts(lines, PadsPart)

    def _parse_routes(self, lines):
        self.routes, self.route_nets = parse_pads_routes(
            lines, PadsRoutePoint, self.thermal_points
        )

    def get_decal_for_part(self, refdes):
        """Get the decal name for a part using its ALT field and PARTTYPE decal list."""
        part = self.parts.get(refdes)
        if not part:
            return None
        decals = self.part_types.get(part.ptype, [])
        if not decals:
            return None
        alt_idx = part.alt
        if alt_idx < len(decals):
            return decals[alt_idx]
        return decals[0] if decals else None


# ─── KICAD PCB PARSER ───────────────────────────────────────────────────────────

def parse_kicad_footprints(filepath):
    """Parse .kicad_pcb: refdes -> {x, y, ori, name, pads}."""
    with open(filepath, 'r') as f:
        content = f.read()

    footprints = {}
    for fp_match in re.finditer(r'\(footprint\s+"([^"]*)"', content):
        fp_name = fp_match.group(1)
        start = fp_match.start()
        depth = 0
        end = start
        for i in range(start, len(content)):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        block = content[start:end]

        at_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?', block)
        if not at_match:
            continue
        fp_x = float(at_match.group(1))
        fp_y = float(at_match.group(2))
        fp_ori = float(at_match.group(3)) if at_match.group(3) else 0.0

        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not ref_match:
            continue
        refdes = ref_match.group(1)

        # Parse pads within this footprint
        pads = []
        for pad_match in re.finditer(r'\(pad\s+"?(\w+)"?\s+(\w+)\s+(roundrect|rect|circle|oval|custom|trapezoid)', block):
            pad_num = pad_match.group(1)
            pad_type = pad_match.group(2)
            pad_shape = pad_match.group(3)
            pad_start = pad_match.start()
            # Find the end of this pad block
            pd = 0
            pad_end = pad_start
            for i in range(pad_start, len(block)):
                if block[i] == '(':
                    pd += 1
                elif block[i] == ')':
                    pd -= 1
                    if pd == 0:
                        pad_end = i + 1
                        break
            pad_block = block[pad_start:pad_end]

            # Parse pad size and position
            size_match = re.search(r'\(size\s+([\d.]+)\s+([\d.]+)', pad_block)
            at_pad = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?', pad_block)
            drill_match = re.search(r'\(drill(?:\s+oval)?\s+([\d.]+)(?:\s+([\d.]+))?', pad_block)

            pad_info = {
                'num': pad_num,
                'type': pad_type,
                'shape': pad_shape,
                'size_x': float(size_match.group(1)) if size_match else 0,
                'size_y': float(size_match.group(2)) if size_match else 0,
                'x': float(at_pad.group(1)) if at_pad else 0,
                'y': float(at_pad.group(2)) if at_pad else 0,
                'ori': float(at_pad.group(3)) if at_pad and at_pad.group(3) else 0,
                'drill': float(drill_match.group(1)) if drill_match else 0,
                'block_start': pad_start,
                'block_end': pad_end,
                'raw_block': pad_block,
            }
            pads.append(pad_info)

        footprints[refdes] = {
            'x': fp_x, 'y': fp_y, 'ori': fp_ori, 'name': fp_name,
            'block_start': start, 'block_end': end, 'pads': pads
        }

    return footprints


# ─── COORDINATE TRANSFORMATION ──────────────────────────────────────────────────

def compute_transform(pads_parts, kicad_fps):
    """Compute transformation: KiCad = scale * PADS + offset (scale = 2/3 * 1e-6)."""
    pairs = []
    for refdes, pp in pads_parts.items():
        if refdes in kicad_fps:
            kp = kicad_fps[refdes]
            pairs.append((pp.x, kp['x'], pp.y, kp['y']))

    if len(pairs) < 2:
        print(f"  Warning: Only {len(pairs)} matched parts (need >= 2)")
        return None

    n = len(pairs)
    sxx = sum(p[0]**2 for p in pairs)
    sx = sum(p[0] for p in pairs)
    skx = sum(p[1] for p in pairs)
    sxkx = sum(p[0]*p[1] for p in pairs)

    det = sxx * n - sx * sx
    if abs(det) < 1e-20:
        return None
    a = (n * sxkx - sx * skx) / det
    c = (sxx * skx - sx * sxkx) / det

    syy = sum(p[2]**2 for p in pairs)
    sy = sum(p[2] for p in pairs)
    sky = sum(p[3] for p in pairs)
    syky = sum(p[2]*p[3] for p in pairs)

    det_y = syy * n - sy * sy
    if abs(det_y) < 1e-20:
        return None
    b = (n * syky - sy * sky) / det_y
    f = (syy * sky - sy * syky) / det_y

    print(f"  Matched {n} parts")
    print(f"  KiCad_X = {a:.10f} * PADS_X + {c:.6f}")
    print(f"  KiCad_Y = {b:.10f} * PADS_Y + {f:.6f}")

    max_err = 0
    for px, kx, py, ky in pairs:
        pred_x = a * px + c
        pred_y = b * py + f
        err = math.sqrt((pred_x - kx)**2 + (pred_y - ky)**2)
        max_err = max(max_err, err)
    print(f"  Max error: {max_err:.8f} mm")
    if max_err > 0.01:
        print("  WARNING: Transformation error > 10µm — results may be inaccurate!")

    compute_transform.last_error = max_err
    return (a, c, b, f)


def pads_to_kicad_xy(x, y, transform):
    a, c, b, f = transform
    return a * x + c, b * y + f


def pads_size_to_mm(size, transform):
    """Convert PADS size (basic units) to mm using scale factor."""
    return abs(transform[0]) * size


# ─── LAYER MAPPING ──────────────────────────────────────────────────────────────

def pads_layer_to_kicad(pads_layer, max_layer):
    if pads_layer >= 64:
        pads_layer = pads_layer - 64
    if pads_layer == 0:
        return "F.Cu"
    elif pads_layer == max_layer - 1:
        return "B.Cu"
    elif pads_layer < max_layer - 1:
        return f"In{pads_layer}.Cu"
    return "F.Cu"


def pads_doc_layer_to_kicad(level):
    """Map PADS documentation/graphics layer to KiCad layer."""
    # Level 0 = board outline
    if level == 0:
        return "Edge.Cuts"
    # Level 1 = bottom copper (for lines items, could be bottom silk)
    if level == 1:
        return "B.SilkS"
    # Level 26 = top silk
    if level == 26:
        return "F.SilkS"
    # Level 27 = bottom silk
    if level == 27:
        return "B.SilkS"
    # Level 126 = all layers / documentation → F.SilkS for text, F.Fab for lines
    if level == 126:
        return "F.SilkS"
    # Level 127 = documentation
    if level == 127:
        return "F.Fab"
    # Default
    return "Cmts.User"


# ─── BOARD OUTLINE GENERATION ───────────────────────────────────────────────────

def generate_board_outline(lines_items, transform):
    """Generate KiCad gr_line entries on Edge.Cuts from PADS BOARD items."""
    gr_lines = []
    board_polygon = []  # for zone creation

    for item in lines_items:
        if item.item_type != 'BOARD':
            continue

        # Convert origin
        ox, oy = pads_to_kicad_xy(item.x, item.y, transform)

        for piece in item.pieces:
            if piece.piece_type == 'BRDCLS' or piece.piece_type == 'CLOSED':
                # Closed polygon - board outline
                abs_points = []
                for px, py in piece.points:
                    # Points are relative to item origin in PADS basic units
                    kx, ky = pads_to_kicad_xy(item.x + px, item.y + py, transform)
                    abs_points.append((kx, ky))

                # Generate gr_line segments (closed polygon)
                # Skip last point if it duplicates the first (common in PADS closed shapes)
                pts = abs_points[:]
                if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 0.001 and abs(pts[0][1] - pts[-1][1]) < 0.001:
                    pts = pts[:-1]  # Remove duplicate closing point

                for i in range(len(pts)):
                    p1 = pts[i]
                    p2 = pts[(i + 1) % len(pts)]
                    seg_len = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                    if seg_len < 0.001:
                        continue  # Skip zero-length segments
                    w = pads_size_to_mm(piece.width, transform)
                    gr_lines.append(
                        f'\t(gr_line (start {p1[0]:.6f} {p1[1]:.6f}) '
                        f'(end {p2[0]:.6f} {p2[1]:.6f}) '
                        f'(stroke (width {w:.6f})) (layer "Edge.Cuts"))'
                    )

                board_polygon = pts

            elif piece.piece_type == 'CIRCLE':
                # Circle on board outline (likely mounting hole)
                if len(piece.points) >= 2:
                    cx1, cy1 = pads_to_kicad_xy(item.x + piece.points[0][0], item.y + piece.points[0][1], transform)
                    cx2, cy2 = pads_to_kicad_xy(item.x + piece.points[1][0], item.y + piece.points[1][1], transform)
                    # Circle defined by two points on diameter
                    cx = (cx1 + cx2) / 2
                    cy = (cy1 + cy2) / 2
                    r = math.sqrt((cx2 - cx1)**2 + (cy2 - cy1)**2) / 2
                    w = pads_size_to_mm(piece.width, transform)
                    gr_lines.append(
                        f'\t(gr_circle (center {cx:.6f} {cy:.6f}) '
                        f'(end {cx + r:.6f} {cy:.6f}) '
                        f'(stroke (width {w:.6f})) (layer "Edge.Cuts"))'
                    )

            elif piece.piece_type == 'OPEN':
                # Open polyline on board outline
                abs_points = []
                for px, py in piece.points:
                    kx, ky = pads_to_kicad_xy(item.x + px, item.y + py, transform)
                    abs_points.append((kx, ky))
                for i in range(len(abs_points) - 1):
                    p1 = abs_points[i]
                    p2 = abs_points[i + 1]
                    w = pads_size_to_mm(piece.width, transform)
                    gr_lines.append(
                        f'\t(gr_line (start {p1[0]:.6f} {p1[1]:.6f}) '
                        f'(end {p2[0]:.6f} {p2[1]:.6f}) '
                        f'(stroke (width {w:.6f})) (layer "Edge.Cuts"))'
                    )

    if gr_lines:
        text = "\n\t# Board outline (injected by pads_full_converter.py)\n"
        text += "\n".join(gr_lines)
        text += "\n"
        return text, board_polygon, len(gr_lines)
    return "", [], 0


# ─── SILK TEXT GENERATION ───────────────────────────────────────────────────────

def generate_silk_text(text_items, transform):
    """Generate KiCad gr_text entries from PADS free text items."""
    gr_texts = []

    for item in text_items:
        kx, ky = pads_to_kicad_xy(item.x, item.y, transform)
        height_mm = pads_size_to_mm(item.height, transform)
        width_mm = pads_size_to_mm(item.width, transform)
        layer = pads_doc_layer_to_kicad(item.level)

        # KiCad gr_text format
        # Escape quotes in text
        escaped_text = item.text.replace('"', '\\"')
        gr_texts.append(
            f'\t(gr_text "{escaped_text}" '
            f'(at {kx:.6f} {ky:.6f} {item.ori:.3f}) '
            f'(layer "{layer}") '
            f'(effects (font (size {height_mm:.4f} {height_mm:.4f}) (thickness {width_mm:.4f}))))'
        )

    if gr_texts:
        text = "\n\t# Silk screen text (injected by pads_full_converter.py)\n"
        text += "\n".join(gr_texts)
        text += "\n"
        return text, len(gr_texts)
    return "", 0


# ─── SILK / DOCUMENTATION LINES GENERATION ──────────────────────────────────────

def generate_silk_lines(lines_items, transform):
    """Generate KiCad gr_line entries from PADS LINES items (documentation)."""
    gr_lines = []

    for item in lines_items:
        if item.item_type == 'BOARD':
            continue  # Skip board items (handled separately)

        for piece in item.pieces:
            layer = pads_doc_layer_to_kicad(piece.level)
            w = pads_size_to_mm(piece.width, transform)

            if piece.piece_type == 'OPEN' or piece.piece_type == 'CLOSED':
                abs_points = []
                for px, py in piece.points:
                    kx, ky = pads_to_kicad_xy(item.x + px, item.y + py, transform)
                    abs_points.append((kx, ky))

                num_segs = len(abs_points) - 1
                if piece.piece_type == 'CLOSED':
                    num_segs = len(abs_points)

                for i in range(num_segs):
                    p1 = abs_points[i]
                    p2 = abs_points[(i + 1) % len(abs_points)]
                    gr_lines.append(
                        f'\t(gr_line (start {p1[0]:.6f} {p1[1]:.6f}) '
                        f'(end {p2[0]:.6f} {p2[1]:.6f}) '
                        f'(stroke (width {w:.6f})) (layer "{layer}"))'
                    )

            elif piece.piece_type == 'CIRCLE':
                if len(piece.points) >= 2:
                    cx1, cy1 = pads_to_kicad_xy(item.x + piece.points[0][0], item.y + piece.points[0][1], transform)
                    cx2, cy2 = pads_to_kicad_xy(item.x + piece.points[1][0], item.y + piece.points[1][1], transform)
                    cx = (cx1 + cx2) / 2
                    cy = (cy1 + cy2) / 2
                    r = math.sqrt((cx2 - cx1)**2 + (cy2 - cy1)**2) / 2
                    gr_lines.append(
                        f'\t(gr_circle (center {cx:.6f} {cy:.6f}) '
                        f'(end {cx + r:.6f} {cy:.6f}) '
                        f'(stroke (width {w:.6f})) (layer "{layer}"))'
                    )

            elif piece.piece_type == 'COPOPN':
                # Copper pour outline - skip for now
                pass

    if gr_lines:
        text = "\n\t# Documentation lines (injected by pads_full_converter.py)\n"
        text += "\n".join(gr_lines)
        text += "\n"
        return text, len(gr_lines)
    return "", 0


# ─── COPPER ZONE GENERATION ─────────────────────────────────────────────────────

def generate_copper_zone(board_polygon, thermal_points, transform, parser):
    """Generate a KiCad (zone) on B.Cu from board outline polygon."""
    if not board_polygon or len(board_polygon) < 3:
        return "", 0

    # Determine the dominant net from thermal connections on layer 65 (B.Cu plane)
    net_counts = {}
    for tx, ty, layer, net in thermal_points:
        if layer >= 64:
            net_counts[net] = net_counts.get(net, 0) + 1

    if net_counts:
        dominant_net = max(net_counts, key=net_counts.get)
    else:
        dominant_net = "GND"

    print(f"  Copper zone net: {dominant_net} (from {len(net_counts)} nets with thermal connections)")
    if net_counts:
        for net, count in sorted(net_counts.items(), key=lambda x: -x[1]):
            print(f"    {net}: {count} thermal connections")

    # Build zone polygon points
    pts_str = ""
    for px, py in board_polygon:
        pts_str += f"\t\t\t(xy {px:.6f} {py:.6f})\n"

    # Zone fill
    fill_margin = pads_size_to_mm(parser.arptom, transform)  # use ARPTOM as clearance

    zone_text = f"""
\t# Copper zone on B.Cu (injected by pads_full_converter.py)
\t(zone (net "{dominant_net}") (net_name "{dominant_net}") (layer "B.Cu") (tstamp 0)
\t\t(hatch edge 0.508)
\t\t(connect_pads (clearance {fill_margin:.4f}))
\t\t(min_thickness 0.254)
\t\t(fill (thermal_gap {fill_margin:.4f}) (thermal_bridge_width 0.508))
\t\t(polygon
\t\t\t{pts_str.rstrip()}
\t\t)
)"""

    return zone_text, 1


# ─── SEGMENT & VIA GENERATION ───────────────────────────────────────────────────

def generate_kicad_segments(routes, route_nets, transform, max_layer, via_defs):
    """Generate KiCad (segment) and (via) entries from PADS route data."""
    a, c, b, f = transform
    scale = abs(a)

    segments = []
    vias = []
    via_positions = set()

    default_via = via_defs.get('JMPVIA_AAAAA')
    if default_via is None:
        default_via = via_defs.get('VIN_0603')
    if default_via is None and via_defs:
        default_via = next(iter(via_defs.values()))
    via_drill_mm = pads_size_to_mm(default_via.drill, transform) if default_via else 0.3

    if default_via and default_via.pads:
        routing_pads = [p for p in default_via.pads if p[0] in (-2, 0)]
        if routing_pads:
            via_size_raw = routing_pads[0][1]
        else:
            via_size_raw = default_via.pads[0][1]
    else:
        via_size_raw = 600000
    via_size_mm = pads_size_to_mm(via_size_raw, transform)

    print(f"  Via drill: {via_drill_mm:.4f} mm, size: {via_size_mm:.4f} mm")

    for route, net_name in zip(routes, route_nets):
        if len(route) < 2:
            continue

        for i in range(len(route) - 1):
            p1 = route[i]
            p2 = route[i + 1]

            kx1, ky1 = pads_to_kicad_xy(p1.x, p1.y, transform)
            kx2, ky2 = pads_to_kicad_xy(p2.x, p2.y, transform)
            width_mm = scale * p1.width

            l1 = p1.layer
            l2 = p2.layer

            if l1 == l2:
                layer_name = pads_layer_to_kicad(l1, max_layer)
                seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                if seg_len < 0.001:
                    continue
                segments.append(
                    f'\t(segment\n'
                    f'\t\t(start {kx1:.6f} {ky1:.6f})\n'
                    f'\t\t(end {kx2:.6f} {ky2:.6f})\n'
                    f'\t\t(width {width_mm:.6f})\n'
                    f'\t\t(layer "{layer_name}")\n'
                    f'\t\t(net "{net_name}")\n'
                    f'\t)'
                )

            elif l1 < 64 and l2 >= 64:
                routing_layer = l1
                plane_layer = l2 - 64
                ki_routing = pads_layer_to_kicad(routing_layer, max_layer)

                if routing_layer != plane_layer:
                    via_key = (round(kx2, 4), round(ky2, 4))
                    if via_key not in via_positions:
                        via_positions.add(via_key)
                        vias.append(
                            f'\t(via\n'
                            f'\t\t(at {kx2:.6f} {ky2:.6f})\n'
                            f'\t\t(size {via_size_mm:.4f})\n'
                            f'\t\t(drill {via_drill_mm:.4f})\n'
                            f'\t\t(layers "F.Cu" "B.Cu")\n'
                            f'\t\t(net "{net_name}")\n'
                            f'\t)'
                        )
                    seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                    if seg_len >= 0.001:
                        segments.append(
                            f'\t(segment\n'
                            f'\t\t(start {kx1:.6f} {ky1:.6f})\n'
                            f'\t\t(end {kx2:.6f} {ky2:.6f})\n'
                            f'\t\t(width {width_mm:.6f})\n'
                            f'\t\t(layer "{ki_routing}")\n'
                            f'\t\t(net "{net_name}")\n'
                            f'\t)'
                        )
                else:
                    seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                    if seg_len >= 0.001:
                        segments.append(
                            f'\t(segment\n'
                            f'\t\t(start {kx1:.6f} {ky1:.6f})\n'
                            f'\t\t(end {kx2:.6f} {ky2:.6f})\n'
                            f'\t\t(width {width_mm:.6f})\n'
                            f'\t\t(layer "{ki_routing}")\n'
                            f'\t\t(net "{net_name}")\n'
                            f'\t)'
                        )

            elif l1 >= 64 and l2 < 64:
                routing_layer = l2
                plane_layer = l1 - 64
                ki_routing = pads_layer_to_kicad(routing_layer, max_layer)

                if routing_layer != plane_layer:
                    via_key = (round(kx1, 4), round(ky1, 4))
                    if via_key not in via_positions:
                        via_positions.add(via_key)
                        vias.append(
                            f'\t(via\n'
                            f'\t\t(at {kx1:.6f} {ky1:.6f})\n'
                            f'\t\t(size {via_size_mm:.4f})\n'
                            f'\t\t(drill {via_drill_mm:.4f})\n'
                            f'\t\t(layers "F.Cu" "B.Cu")\n'
                            f'\t\t(net "{net_name}")\n'
                            f'\t)'
                        )
                    seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                    if seg_len >= 0.001:
                        segments.append(
                            f'\t(segment\n'
                            f'\t\t(start {kx1:.6f} {ky1:.6f})\n'
                            f'\t\t(end {kx2:.6f} {ky2:.6f})\n'
                            f'\t\t(width {width_mm:.6f})\n'
                            f'\t\t(layer "{ki_routing}")\n'
                            f'\t\t(net "{net_name}")\n'
                            f'\t)'
                        )
                else:
                    seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                    if seg_len >= 0.001:
                        segments.append(
                            f'\t(segment\n'
                            f'\t\t(start {kx1:.6f} {ky1:.6f})\n'
                            f'\t\t(end {kx2:.6f} {ky2:.6f})\n'
                            f'\t\t(width {width_mm:.6f})\n'
                            f'\t\t(layer "{ki_routing}")\n'
                            f'\t\t(net "{net_name}")\n'
                            f'\t)'
                        )

            elif l1 < 64 and l2 < 64 and l1 != l2:
                ki_l1 = pads_layer_to_kicad(l1, max_layer)
                via_key = (round(kx2, 4), round(ky2, 4))
                if via_key not in via_positions:
                    via_positions.add(via_key)
                    vias.append(
                        f'\t(via\n'
                        f'\t\t(at {kx2:.6f} {ky2:.6f})\n'
                        f'\t\t(size {via_size_mm:.4f})\n'
                        f'\t\t(drill {via_drill_mm:.4f})\n'
                        f'\t\t(layers "F.Cu" "B.Cu")\n'
                        f'\t\t(net "{net_name}")\n'
                        f'\t)'
                    )
                seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                if seg_len >= 0.001:
                    segments.append(
                        f'\t(segment\n'
                        f'\t\t(start {kx1:.6f} {ky1:.6f})\n'
                        f'\t\t(end {kx2:.6f} {ky2:.6f})\n'
                        f'\t\t(width {width_mm:.6f})\n'
                        f'\t\t(layer "{ki_l1}")\n'
                        f'\t\t(net "{net_name}")\n'
                        f'\t)'
                    )

    # Deduplicate segments
    seen_keys = set()
    unique_segments = []
    dup_count = 0
    for seg_text in segments:
        coord_match = re.search(
            r'\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\n\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)\s*\n'
            r'\s*\(width\s+([-\d.]+)\)\s*\n\s*\(layer\s+"([^"]+)"\)\s*\n\s*\(net\s+"([^"]+)"\)',
            seg_text
        )
        if coord_match:
            sx, sy = float(coord_match.group(1)), float(coord_match.group(2))
            ex, ey = float(coord_match.group(3)), float(coord_match.group(4))
            layer = coord_match.group(6)
            net = coord_match.group(7)
            pt1 = (round(sx, 4), round(sy, 4))
            pt2 = (round(ex, 4), round(ey, 4))
            key = (frozenset([pt1, pt2]), layer, net)
            if key in seen_keys:
                dup_count += 1
                continue
            seen_keys.add(key)
        unique_segments.append(seg_text)

    if dup_count > 0:
        print(f"  Deduplicated {dup_count} duplicate segments")

    segments = unique_segments

    segments_text = "\n"
    if segments:
        segments_text += "\t# PADS routing traces (injected by pads_full_converter.py)\n"
        segments_text += "\n".join(segments)
        segments_text += "\n"
    if vias:
        segments_text += "\n\t# PADS vias (injected by pads_full_converter.py)\n"
        segments_text += "\n".join(vias)
        segments_text += "\n"

    return segments_text, len(segments), len(vias)


# ─── PAD PASTE/MASK MARGIN INJECTION ─────────────────────────────────────────────

def inject_pad_margins(kicad_content, parser, kicad_fps, transform):
    """
    Inject solder_paste_margin and solder_mask_margin on pads based on PADS pad stack data.

    For each part, determine its decal, look up pad stacks, compute margins.
    """
    injected_count = 0
    scale = abs(transform[0])
    arptom_mm = scale * parser.arptom  # global annular ring in mm

    # For each part in PADS, get decal and pad stacks
    for refdes, part in parser.parts.items():
        decal_name = parser.get_decal_for_part(refdes)
        if not decal_name or decal_name not in parser.decals:
            continue

        decal = parser.decals[decal_name]
        fp = kicad_fps.get(refdes)
        if not fp:
            continue

        # For each pad in the decal, compute margins
        for pad_num_str, pad_stack in decal.pad_stacks.items():
            # Find matching pad in KiCad footprint
            # PADS pad numbers are 0-indexed, KiCad pads are usually 1-indexed
            ki_pad_num = str(int(pad_num_str) + 1)

            matching_pad = None
            for p in fp['pads']:
                if p['num'] == ki_pad_num or p['num'] == pad_num_str:
                    matching_pad = p
                    break

            if not matching_pad:
                continue

            # Get stack levels
            paste_size = 0
            mask_size = 0
            copper_size = 0

            for level, size, shape, extra in pad_stack.stacks:
                if level == -2:  # PASTE_MASK
                    paste_size = size
                elif level == -1:  # SOLDER_MASK
                    mask_size = size
                elif level == 0:  # COPPER
                    copper_size = size

            # Convert to mm
            paste_mm = scale * paste_size if paste_size > 0 else 0
            mask_mm = scale * mask_size if mask_size > 0 else 0
            copper_mm = scale * copper_size if copper_size > 0 else 0

            # If copper_size is 0 in PADS, use the KiCad pad size
            if copper_mm == 0:
                # Use the larger of size_x/size_y for round pads, or size_x for rect
                copper_mm = max(matching_pad['size_x'], matching_pad['size_y'])

            # Compute margins
            # Margin = (mask_or_paste_size - copper_size) / 2
            # Positive margin = larger opening (mask), negative = smaller (paste reduction)
            paste_margin = None
            mask_margin = None

            if paste_mm > 0 and copper_mm > 0:
                paste_margin = (paste_mm - copper_mm) / 2
            elif paste_mm == 0:
                # If paste size not explicitly set, paste = copper (no reduction)
                paste_margin = 0.0

            if mask_mm > 0 and copper_mm > 0:
                # Explicit mask size: margin = (mask - copper) / 2 (can be 0)
                mask_margin = (mask_mm - copper_mm) / 2
            elif mask_mm == 0:
                # If mask size not set, use global ARPTOM
                mask_margin = arptom_mm

            # Skip only if nothing to set
            if paste_margin is None and mask_margin is None:
                continue

            # Inject into the pad block in the KiCad file
            # We need to add (solder_paste_margin X) and (solder_mask_margin Y)
            # after the pad's layers line
            pad_block = matching_pad['raw_block']

            # Check if margins already exist
            if 'solder_paste_margin' in pad_block and 'solder_mask_margin' in pad_block:
                continue

            additions = []
            if paste_margin is not None:
                additions.append(f'(solder_paste_margin {paste_margin:.6f})')
            if mask_margin is not None:
                # Always inject mask margin (KiCad default ~0.051mm differs from PADS ARPTOM)
                additions.append(f'(solder_mask_margin {mask_margin:.6f})')

            if not additions:
                continue

            # Find the layers line in the pad block and add after it
            layers_match = re.search(r'\(layers[^)]*\)', pad_block)
            if layers_match:
                insert_pos = layers_match.end()
                new_pad_block = (
                    pad_block[:insert_pos] +
                    ' ' + ' '.join(additions) +
                    pad_block[insert_pos:]
                )

                # Replace in the full content
                old_block = matching_pad['raw_block']
                if old_block in kicad_content:
                    kicad_content = kicad_content.replace(old_block, new_pad_block, 1)
                    injected_count += 1

    print(f"  Injected paste/mask margins on {injected_count} pads")
    return kicad_content, injected_count


# ─── MAIN ───────────────────────────────────────────────────────────────────────

def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Convert PADS ASCII layout data into a KiCad PCB."
    )
    cli.add_argument("pads_file", help="PADS ASCII .asc file")
    cli.add_argument("kicad_input", help="KiCad PCB produced by the importer")
    cli.add_argument("kicad_output", help="Output PCB path")
    cli.add_argument(
        "--max-transform-error",
        type=float,
        default=DEFAULT_MAX_TRANSFORM_ERROR_MM,
        help=f"Maximum allowed footprint-fit error in mm (default: {DEFAULT_MAX_TRANSFORM_ERROR_MM})",
    )
    args = cli.parse_args(argv)

    pads_file = args.pads_file
    kicad_input = args.kicad_input
    kicad_output = args.kicad_output

    print("=== PADS Full Converter ===")
    print(f"  PADS ASCII:  {pads_file}")
    print(f"  KiCad input: {kicad_input}")
    print(f"  KiCad output: {kicad_output}")

    # Step 1: Parse PADS ASCII
    print("\n--- Step 1: Parsing PADS ASCII ---")
    parser = PadsAsciiParser(pads_file)
    parser.parse()
    print(f"  Source encoding: {parser.encoding}")
    print(f"  Parts: {len(parser.parts)}")
    print(f"  Via defs: {len(parser.via_defs)}")
    print(f"  Max layers: {parser.max_layer}")
    print(f"  Text items: {len(parser.text_items)}")
    print(f"  Lines items: {len(parser.lines_items)}")
    for li in parser.lines_items:
        print(f"    {li.name}: type={li.item_type}, pieces={li.pieces_count}, "
              f"actual={len(li.pieces)}, origin=({li.x}, {li.y})")
    print(f"  Decals: {len(parser.decals)}")
    for dn, d in parser.decals.items():
        pad_info = {pn: [(s[0], s[1]) for s in ps.stacks] for pn, ps in d.pad_stacks.items()}
        print(f"    {dn}: pads={pad_info}")
    print(f"  Part types: {len(parser.part_types)}")
    for pt, decals in parser.part_types.items():
        print(f"    {pt}: decals={decals}")

    total_points = sum(len(r) for r in parser.routes)
    total_conns = len(parser.routes)
    print(f"  Total connections: {total_conns}")
    print(f"  Total route points: {total_points}")
    print(f"  Thermal points (B.Cu plane): {len(parser.thermal_points)}")
    print(f"  ARPTOM: {parser.arptom} basic units = {abs(0):.4f} mm (computed later)")

    # Step 2: Parse KiCad PCB
    print("\n--- Step 2: Parsing KiCad PCB ---")
    kicad_fps = parse_kicad_footprints(kicad_input)
    print(f"  Footprints: {len(kicad_fps)}")

    # Step 3: Compute transformation
    print("\n--- Step 3: Computing coordinate transformation ---")
    transform = compute_transform(parser.parts, kicad_fps)
    if transform is None:
        print("  ERROR: Could not compute transformation!")
        sys.exit(1)
    transform_error = getattr(compute_transform, "last_error", None)
    if not transform_error_allowed(transform_error, args.max_transform_error):
        print(
            f"  ERROR: Transformation max error {transform_error:.8f} mm exceeds "
            f"the allowed {args.max_transform_error:.8f} mm."
        )
        print("         Correct the source/import alignment or raise --max-transform-error explicitly.")
        sys.exit(2)

    arptom_mm = abs(transform[0]) * parser.arptom
    print(f"  ARPTOM = {parser.arptom} basic units = {arptom_mm:.6f} mm")

    # Step 4: Generate board outline
    print("\n--- Step 4: Generating board outline ---")
    outline_text, board_polygon, num_outline = generate_board_outline(parser.lines_items, transform)
    print(f"  Board outline segments: {num_outline}")
    if board_polygon:
        print(f"  Board polygon vertices: {len(board_polygon)}")

    # Step 5: Generate silk text
    print("\n--- Step 5: Generating silk screen text ---")
    silk_text, num_text = generate_silk_text(parser.text_items, transform)
    print(f"  Silk text items: {num_text}")

    # Step 6: Generate silk/doc lines
    print("\n--- Step 6: Generating documentation lines ---")
    doc_lines_text, num_doc_lines = generate_silk_lines(parser.lines_items, transform)
    print(f"  Documentation line segments: {num_doc_lines}")

    # Step 7: Generate copper zone
    print("\n--- Step 7: Generating copper zone ---")
    zone_text, num_zones = generate_copper_zone(board_polygon, parser.thermal_points, transform, parser)
    print(f"  Copper zones: {num_zones}")

    # Step 8: Generate routing segments + vias
    print("\n--- Step 8: Generating routing segments + vias ---")
    segments_text, num_segs, num_vias = generate_kicad_segments(
        parser.routes, parser.route_nets, transform, parser.max_layer, parser.via_defs
    )
    print(f"  Segments: {num_segs}")
    print(f"  Vias: {num_vias}")

    # Step 9: Read KiCad file and inject everything
    print("\n--- Step 9: Injecting into KiCad PCB ---")
    with open(kicad_input, 'r') as f:
        kicad_content = f.read()

    # Step 9a: Inject pad margins (modifies pad blocks in-place)
    print("  Injecting pad paste/mask margins...")
    kicad_content, num_margins = inject_pad_margins(kicad_content, parser, kicad_fps, transform)

    # Step 9b: Inject all other items before the last closing paren
    all_injections = ""
    if outline_text:
        all_injections += outline_text
    if silk_text:
        all_injections += silk_text
    if doc_lines_text:
        all_injections += doc_lines_text
    if zone_text:
        all_injections += zone_text
    if segments_text.strip():
        all_injections += segments_text

    last_paren = kicad_content.rstrip().rfind(')')
    if last_paren > 0:
        new_content = kicad_content[:last_paren] + all_injections + kicad_content[last_paren:]
    else:
        new_content = kicad_content + all_injections

    with open(kicad_output, 'w') as f:
        f.write(new_content)

    file_size = len(new_content)
    print(f"\n  Output written to: {kicad_output}")
    print(f"  File size: {file_size:,} bytes")

    # Step 10: Summary
    print("\n=== SUMMARY ===")
    print(f"  Board outline segments: {num_outline}")
    print(f"  Silk text items: {num_text}")
    print(f"  Documentation line segments: {num_doc_lines}")
    print(f"  Copper zones: {num_zones}")
    print(f"  Routing segments: {num_segs}")
    print(f"  Vias: {num_vias}")
    print(f"  Pad margins injected: {num_margins}")
    if transform_error is not None:
        print(f"  Transformation max error: {transform_error:.8f} mm")
    print(f"  Output: {kicad_output}")


if __name__ == '__main__':
    main()
