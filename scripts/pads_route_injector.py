#!/usr/bin/env python3
"""
PADS ASCII Route Extractor & KiCad Segment Injector (v2)

Parses the *ROUTE* section of a PADS PowerPCB ASCII file, extracts all routing
traces (segments) and via locations, converts them to KiCad coordinate space by
matching PART positions between PADS and KiCad, and injects them into a .kicad_pcb file.

Key discoveries:
  - PADS "Metric" basic unit is 2/3 nm (not 1 nm). The kicad-cli importer applies
    a 2/3 scale factor and Y-flip when converting PADS to KiCad coordinates.
  - Transformation: KiCad_X = (2/3) * PADS_X/1e6 - offset_x
                   KiCad_Y = -(2/3) * PADS_Y/1e6 + offset_y
  - The offset is computed dynamically by matching PADS PART positions with KiCad
    footprint positions (matched by refdes).
  - Layer changes between routing layer 0 (F.Cu) and plane layer 65 (B.Cu plane)
    require a via; layer changes between routing layer 1 (B.Cu) and plane layer 65
    do not (same physical layer, just a thermal connection to the copper pour).
  - Via definitions from *VIA* section provide drill and pad sizes.

Usage:
    python3 pads_route_injector.py <pads_ascii.asc> <input.kicad_pcb> <output.kicad_pcb>
"""

import re
import sys
import math
from typing import List, Dict, Tuple, Optional


# ─── PADS ASCII PARSER ──────────────────────────────────────────────────────────

class PadsPart:
    def __init__(self, refdes: str, x: float, y: float, ori: float, ptype: str):
        self.refdes = refdes
        self.x = x          # PADS basic units (2/3 nm each)
        self.y = y
        self.ori = ori      # degrees
        self.ptype = ptype  # part type name


class PadsRoutePoint:
    def __init__(self, x: float, y: float, layer: int, width: float, flags: int, net: str, extra: list):
        self.x = x
        self.y = y
        self.layer = layer
        self.width = width
        self.flags = flags
        self.net = net
        self.extra = extra  # additional fields after FLAGS


class PadsViaDef:
    def __init__(self, name: str, drill: float, pads: list):
        self.name = name
        self.drill = drill  # PADS basic units
        self.pads = pads    # list of (level, size, shape)


class PadsAsciiParser:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.parts: Dict[str, PadsPart] = {}
        self.routes: List[List[PadsRoutePoint]] = []  # list of connections (each is a list of points)
        self.route_nets: List[str] = []               # net name for each connection
        self.via_defs: Dict[str, PadsViaDef] = {}
        self.max_layer = 2
        self.units = 1  # 0=Mils, 1=Metric, 2=Inches

    def parse(self):
        with open(self.filepath, 'r', encoding='cp936', errors='replace') as f:
            lines = f.readlines()
        self._parse_header(lines)
        self._parse_vias(lines)
        self._parse_parts(lines)
        self._parse_routes(lines)

    def _parse_header(self, lines):
        for line in lines:
            s = line.strip()
            if s.startswith('UNITS') and 'MAXIMUMLAYER' not in s:
                p = s.split()
                if len(p) >= 2:
                    try: self.units = int(p[1])
                    except ValueError: pass
            elif s.startswith('MAXIMUMLAYER'):
                p = s.split()
                if len(p) >= 2:
                    try: self.max_layer = int(p[1])
                    except ValueError: pass
                break

    def _parse_vias(self, lines):
        in_via = False
        current_via = None
        for line in lines:
            s = line.strip()
            if s.startswith('*VIA*'):
                in_via = True
                continue
            if in_via:
                if s.startswith('*') and not s.startswith('*REMARK*'):
                    break
                if not s or s.startswith('*REMARK*'):
                    continue
                p = s.split()
                if len(p) >= 2:
                    # Via definition line: NAME DRILL NUMSTACKS
                    if not p[0].startswith('-') and not p[0].isdigit():
                        try:
                            name = p[0]
                            drill = float(p[1])
                            current_via = PadsViaDef(name, drill, [])
                            self.via_defs[name] = current_via
                        except (ValueError, IndexError):
                            pass
                    elif current_via is not None:
                        # Stack line: LEVEL SIZE SHAPE
                        try:
                            level = int(p[0])
                            size = float(p[1])
                            shape = p[2] if len(p) > 2 else 'R'
                            current_via.pads.append((level, size, shape))
                        except (ValueError, IndexError):
                            pass

    def _parse_parts(self, lines):
        in_part = False
        for line in lines:
            s = line.strip()
            if s.startswith('*PART*'):
                in_part = True
                continue
            if in_part:
                if s.startswith('*') and not s.startswith('*REMARK*'):
                    break
                if not s or s.startswith('*REMARK*'):
                    continue
                if s.startswith(('VALUE', 'Regular', 'Ref.Des.', 'Value', 'Comment', 'NONE')):
                    continue
                p = s.split()
                if len(p) >= 5 and re.match(r'^[A-Z]+\d+', p[0]):
                    try:
                        self.parts[p[0]] = PadsPart(p[0], float(p[2]), float(p[3]), float(p[4]), p[1])
                    except (ValueError, IndexError):
                        pass

    def _parse_routes(self, lines):
        in_route = False
        current_net = ""
        current_connection = None

        for line in lines:
            s = line.strip()
            if s == '*ROUTE*':
                in_route = True
                continue
            if in_route:
                if s.startswith('*') and not s.startswith('*SIGNAL*') and not s.startswith('*REMARK*'):
                    if current_connection is not None:
                        self.routes.append(current_connection)
                        self.route_nets.append(current_net)
                        current_connection = None
                    break
                if not s or s.startswith('*REMARK*'):
                    continue
                if s.startswith('*SIGNAL*'):
                    if current_connection is not None:
                        self.routes.append(current_connection)
                        self.route_nets.append(current_net)
                        current_connection = None
                    sig_parts = s.split()
                    current_net = sig_parts[1] if len(sig_parts) > 1 else "?"
                    continue

                p = s.split()
                # Try to parse as coordinate line: X Y LAYER WIDTH FLAGS [extra...]
                try:
                    x = float(p[0])
                    y = float(p[1])
                    layer = int(p[2])
                    width = float(p[3])
                    flags = int(p[4])
                    extra = p[5:] if len(p) > 5 else []
                    point = PadsRoutePoint(x, y, layer, width, flags, current_net, extra)
                    if current_connection is None:
                        current_connection = []
                    current_connection.append(point)
                except (ValueError, IndexError):
                    # Pin-pair line — start new connection
                    if current_connection is not None:
                        self.routes.append(current_connection)
                        self.route_nets.append(current_net)
                        current_connection = None

        if current_connection is not None:
            self.routes.append(current_connection)
            self.route_nets.append(current_net)


# ─── KICAD PCB PARSER ───────────────────────────────────────────────────────────

def parse_kicad_footprints(filepath: str) -> Dict[str, dict]:
    """Parse .kicad_pcb: refdes -> {x(mm), y(mm), ori(deg)}."""
    with open(filepath, 'r') as f:
        content = f.read()

    footprints = {}
    for fp_match in re.finditer(r'\(footprint\s+"([^"]*)"', content):
        fp_name = fp_match.group(1)
        start = fp_match.start()
        depth = 0
        end = start
        for i in range(start, len(content)):
            if content[i] == '(': depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        block = content[start:end]

        at_match = re.search(r'\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?', block)
        if not at_match: continue
        fp_x = float(at_match.group(1))
        fp_y = float(at_match.group(2))
        fp_ori = float(at_match.group(3)) if at_match.group(3) else 0.0

        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not ref_match: continue
        refdes = ref_match.group(1)

        footprints[refdes] = {'x': fp_x, 'y': fp_y, 'ori': fp_ori, 'name': fp_name}

    return footprints


# ─── COORDINATE TRANSFORMATION ──────────────────────────────────────────────────

def compute_transform(pads_parts: Dict[str, PadsPart], kicad_fps: Dict[str, dict]) -> Optional[Tuple]:
    """
    Compute transformation: KiCad = scale * PADS + offset
    where scale_x = 2/3, scale_y = -2/3 (Y-flip).

    PADS coordinates are in basic units (2/3 nm each).
    KiCad coordinates are in mm.

    KiCad_X = a * PADS_X + c
    KiCad_Y = b * PADS_Y + f

    Returns (a, c, b, f)
    """
    # Collect matched pairs
    pairs = []
    for refdes, pp in pads_parts.items():
        if refdes in kicad_fps:
            kp = kicad_fps[refdes]
            pairs.append((pp.x, kp['x'], pp.y, kp['y']))

    if len(pairs) < 2:
        print(f"  Warning: Only {len(pairs)} matched parts (need >= 2)")
        return None

    # Least squares: KiCad_X = a * PADS_X + c
    # [sum(xx) sum(x)] [a]   [sum(x*kx)]
    # [sum(x)  n    ] [c] = [sum(kx)  ]
    n = len(pairs)
    sxx = sum(p[0]**2 for p in pairs)
    sx = sum(p[0] for p in pairs)
    skx = sum(p[1] for p in pairs)
    sxkx = sum(p[0]*p[1] for p in pairs)

    # 2x2 system for X
    det = sxx * n - sx * sx
    if abs(det) < 1e-20:
        return None
    a = (n * sxkx - sx * skx) / det
    c = (sxx * skx - sx * sxkx) / det

    # Same for Y
    syy = sum(p[2]**2 for p in pairs)
    sy = sum(p[2] for p in pairs)
    sky = sum(p[3] for p in pairs)
    syky = sum(p[2]*p[3] for p in pairs)

    det_y = syy * n - sy * sy
    if abs(det_y) < 1e-20:
        return None
    b = (n * syky - sy * sky) / det_y
    f = (syy * sky - sy * syky) / det_y

    # Report
    print(f"  Matched {n} parts")
    print(f"  Transformation:")
    print(f"    KiCad_X = {a:.10f} * PADS_X + {c:.6f}")
    print(f"    KiCad_Y = {b:.10f} * PADS_Y + {f:.6f}")

    # Verify
    max_err = 0
    for px, kx, py, ky in pairs:
        pred_x = a * px + c
        pred_y = b * py + f
        err = math.sqrt((pred_x - kx)**2 + (pred_y - ky)**2)
        max_err = max(max_err, err)
    print(f"    Max error: {max_err:.8f} mm")

    if max_err > 0.01:
        print(f"  WARNING: Transformation error > 10µm — results may be inaccurate!")

    compute_transform.last_error = max_err
    return (a, c, b, f)


# ─── LAYER MAPPING ──────────────────────────────────────────────────────────────

def pads_layer_to_kicad(pads_layer: int, max_layer: int) -> str:
    """Map PADS layer number to KiCad layer name."""
    if pads_layer >= 64:
        pads_layer = pads_layer - 64
    if pads_layer == 0:
        return "F.Cu"
    elif pads_layer == max_layer - 1:
        return "B.Cu"
    elif pads_layer < max_layer - 1:
        return f"In{pads_layer}.Cu"
    return "F.Cu"


# ─── UNIT CONVERSION ────────────────────────────────────────────────────────────

def pads_to_kicad_xy(x: float, y: float, transform: Tuple) -> Tuple[float, float]:
    """Convert PADS coordinate (basic units) to KiCad (mm)."""
    a, c, b, f = transform
    kx = a * x + c
    ky = b * y + f
    return kx, ky


def pads_width_to_mm(width: float, transform: Tuple) -> float:
    """Convert PADS width (basic units) to mm."""
    a = transform[0]  # scale factor (should be 2/3 * 1e-6)
    return abs(a) * width


def pads_drill_to_mm(drill: float, transform: Tuple) -> float:
    """Convert PADS drill (basic units) to mm."""
    a = transform[0]
    return abs(a) * drill


# ─── SEGMENT & VIA GENERATION ───────────────────────────────────────────────────

def generate_kicad_segments(routes: List[List[PadsRoutePoint]],
                           route_nets: List[str],
                           transform: Tuple,
                           max_layer: int,
                           via_defs: Dict[str, PadsViaDef]) -> Tuple[str, int, int]:
    """
    Generate KiCad (segment) and (via) entries from PADS route data.

    Rules:
    - Same layer, consecutive points: generate (segment)
    - Layer 0 → 65 (F.Cu → B.Cu plane): via at the plane point + segment on F.Cu
    - Layer 1 → 65 (B.Cu → B.Cu plane): segment on B.Cu (thermal, no via)
    - Layer 65 → 0: via at the plane point + segment on F.Cu
    - Layer 65 → 1: segment on B.Cu (thermal, no via)
    """
    a, c, b, f = transform
    scale = abs(a)  # should be ~6.667e-7 (2/3 * 1e-6)

    segments = []
    vias = []
    via_positions = set()  # avoid duplicate vias at same position

    # Get default via parameters — prefer JMPVIA_AAAAA (standard via), fall back to others
    # BUGFIX: Previous version had `if via_defs: default_via = next(iter(...))` which
    # always overwrote the carefully selected via with an arbitrary dict iteration order.
    default_via = via_defs.get('JMPVIA_AAAAA')
    if default_via is None:
        default_via = via_defs.get('VIN_0603')
    if default_via is None and via_defs:
        default_via = next(iter(via_defs.values()))
    via_drill_mm = pads_drill_to_mm(default_via.drill, transform) if default_via else 0.3
    # Via pad size: use the routing layer pad (level -2 = top, or level 0 = bottom).
    # Do NOT use the plane/thermal pad (level -1) as it's typically larger and handled
    # by KiCad zones, not the via size.
    if default_via and default_via.pads:
        # Prefer level -2 (top routing layer), then level 0 (bottom), then first
        routing_pads = [p for p in default_via.pads if p[0] in (-2, 0)]
        if routing_pads:
            via_size_raw = routing_pads[0][1]
        else:
            via_size_raw = default_via.pads[0][1]
    else:
        via_size_raw = 600000
    via_size_mm = pads_drill_to_mm(via_size_raw, transform)

    print(f"  Via drill: {via_drill_mm:.4f} mm, size: {via_size_mm:.4f} mm")

    for route, net_name in zip(routes, route_nets):
        if len(route) < 2:
            continue

        for i in range(len(route) - 1):
            p1 = route[i]
            p2 = route[i + 1]

            # Convert coordinates
            kx1, ky1 = pads_to_kicad_xy(p1.x, p1.y, transform)
            kx2, ky2 = pads_to_kicad_xy(p2.x, p2.y, transform)
            width_mm = scale * p1.width

            l1 = p1.layer
            l2 = p2.layer

            # Determine segment type based on layer transition
            if l1 == l2:
                # Same layer — regular segment
                layer_name = pads_layer_to_kicad(l1, max_layer)
                seg_len = math.sqrt((kx2 - kx1)**2 + (ky2 - ky1)**2)
                if seg_len < 0.001:  # skip < 1µm
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
                # Routing layer → plane layer
                routing_layer = l1
                plane_layer = l2 - 64
                ki_routing = pads_layer_to_kicad(routing_layer, max_layer)

                if routing_layer != plane_layer:
                    # Different physical layers — need a via
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
                    # Segment on routing layer to the via
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
                    # Same physical layer — thermal connection, no via
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
                # Plane layer → routing layer
                routing_layer = l2
                plane_layer = l1 - 64
                ki_routing = pads_layer_to_kicad(routing_layer, max_layer)

                if routing_layer != plane_layer:
                    # Different physical layers — need a via at p1
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
                    # Segment on routing layer from the via
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
                    # Same physical layer — thermal connection
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
                # Routing layer → different routing layer — via
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
                # Segment on first layer to the via
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
            # else: both plane layers — skip

    # Deduplicate segments — same start, end, layer, and net = duplicate
    # (overlapping connections in PADS route data can produce identical segments)
    seen_keys = set()
    unique_segments = []
    dup_count = 0
    for seg_text in segments:
        # Extract coordinates from the segment text for dedup key
        coord_match = re.search(r'\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\n\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)\s*\n\s*\(width\s+([-\d.]+)\)\s*\n\s*\(layer\s+"([^"]+)"\)\s*\n\s*\(net\s+"([^"]+)"\)', seg_text)
        if coord_match:
            sx, sy = float(coord_match.group(1)), float(coord_match.group(2))
            ex, ey = float(coord_match.group(3)), float(coord_match.group(4))
            layer = coord_match.group(6)
            net = coord_match.group(7)
            # Use sorted endpoints as key (A→B same as B→A)
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

    # Build output text
    segments_text = "\n"
    if segments:
        segments_text += "\t# PADS routing traces (injected by pads_route_injector.py v2)\n"
        segments_text += "\n".join(segments)
        segments_text += "\n"
    if vias:
        segments_text += "\n\t# PADS vias (injected by pads_route_injector.py v2)\n"
        segments_text += "\n".join(vias)
        segments_text += "\n"

    return segments_text, len(segments), len(vias)


# ─── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 4:
        print("Usage: pads_route_injector.py <pads_ascii.asc> <input.kicad_pcb> <output.kicad_pcb>")
        sys.exit(1)

    pads_file = sys.argv[1]
    kicad_input = sys.argv[2]
    kicad_output = sys.argv[3]

    print("=== PADS Route Injector v2 ===")
    print(f"  PADS ASCII:  {pads_file}")
    print(f"  KiCad input: {kicad_input}")
    print(f"  KiCad output: {kicad_output}")

    # Step 1: Parse PADS ASCII
    print("\n--- Step 1: Parsing PADS ASCII ---")
    parser = PadsAsciiParser(pads_file)
    parser.parse()
    print(f"  Parts: {len(parser.parts)}")
    print(f"  Via defs: {len(parser.via_defs)}")
    for name, vd in parser.via_defs.items():
        print(f"    {name}: drill={vd.drill}, pads={vd.pads}")
    print(f"  Max layers: {parser.max_layer}")

    total_points = sum(len(r) for r in parser.routes)
    total_conns = len(parser.routes)
    print(f"  Total connections: {total_conns}")
    print(f"  Total route points: {total_points}")

    # Count layers used
    layer_counts = {}
    for route in parser.routes:
        for pt in route:
            layer_counts[pt.layer] = layer_counts.get(pt.layer, 0) + 1
    print(f"  Layer usage: {dict(sorted(layer_counts.items()))}")

    # Count widths
    width_counts = {}
    for route in parser.routes:
        for pt in route:
            w = pt.width
            width_counts[w] = width_counts.get(w, 0) + 1
    print(f"  Width usage: {dict(sorted(width_counts.items()))}")

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

    # Step 4: Generate segments
    print("\n--- Step 4: Generating KiCad segments ---")
    segments_text, num_segs, num_vias = generate_kicad_segments(
        parser.routes, parser.route_nets, transform, parser.max_layer, parser.via_defs
    )
    print(f"  Segments: {num_segs}")
    print(f"  Vias: {num_vias}")

    # Step 5: Inject into kicad_pcb
    print("\n--- Step 5: Injecting into KiCad PCB ---")
    with open(kicad_input, 'r') as f:
        kicad_content = f.read()

    # Find the last closing parenthesis
    last_paren = kicad_content.rstrip().rfind(')')
    if last_paren > 0:
        new_content = kicad_content[:last_paren] + segments_text + kicad_content[last_paren:]
    else:
        new_content = kicad_content + segments_text

    with open(kicad_output, 'w') as f:
        f.write(new_content)

    file_size = len(new_content)
    print(f"  Output written to: {kicad_output}")
    print(f"  File size: {file_size:,} bytes")
    print(f"  Added {num_segs} segments and {num_vias} vias")

    # Step 6: Verify
    print("\n--- Step 6: Verification ---")
    # Count nets
    nets = set()
    for route_net in parser.route_nets:
        nets.add(route_net)
    print(f"  Nets with routing: {len(nets)}")
    print(f"  Segments per layer:")
    layer_seg_counts = {}
    via_count = new_content.count('(via')
    seg_count = new_content.count('(segment')
    # Count by layer
    for layer in ['F.Cu', 'B.Cu', 'In1.Cu']:
        count = new_content.count(f'(layer "{layer}")')
        if count > 0:
            layer_seg_counts[layer] = count
    print(f"    {layer_seg_counts}")
    print(f"  Total (segment) entries: {seg_count}")
    print(f"  Total (via) entries: {via_count}")

    print("\n=== SUMMARY ===")
    print(f"  PADS connections: {total_conns}")
    print(f"  PADS route points: {total_points}")
    print(f"  KiCad segments: {num_segs}")
    print(f"  KiCad vias: {num_vias}")
    if transform_error is not None:
        print(f"  Transformation max error: {transform_error:.8f} mm")
    print(f"  Output: {kicad_output}")


if __name__ == '__main__':
    main()
