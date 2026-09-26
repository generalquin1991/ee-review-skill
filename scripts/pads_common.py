"""Shared PADS ASCII parsing helpers used by both converters.

PADS exports are usually ASCII with a legacy Windows code page, but projects
can contain UTF-8 metadata.  Keep decoding and the common sections in one
place so route-only and full conversion cannot silently drift apart.
"""

import re
from typing import Dict, Iterable, List, Optional, Tuple


PADS_ENCODINGS = ("utf-8-sig", "cp936", "cp1252", "latin-1")
DEFAULT_MAX_TRANSFORM_ERROR_MM = 0.01


class PadsPart:
    def __init__(self, refdes, x, y, ori, ptype, alt=0):
        self.refdes = refdes
        self.x = x
        self.y = y
        self.ori = ori
        self.ptype = ptype
        self.alt = alt


class PadsRoutePoint:
    def __init__(self, x, y, layer, width, flags, net, extra):
        self.x = x
        self.y = y
        self.layer = layer
        self.width = width
        self.flags = flags
        self.net = net
        self.extra = extra


class PadsViaDef:
    def __init__(self, name, drill, pads):
        self.name = name
        self.drill = drill
        self.pads = pads


def _format_score(text: str) -> int:
    """Score likely PADS markers so a permissive fallback cannot win by luck."""
    markers = ("!PADS-POWERPCB", "*PADS-PCB*", "*PART*", "*ROUTE*", "*VIA*")
    return sum(text.count(marker) for marker in markers)


def read_pads_ascii(path) -> Tuple[List[str], str]:
    """Read a PADS ASCII file with strict, deterministic encoding fallback."""
    with open(path, "rb") as handle:
        payload = handle.read()

    candidates = []
    for encoding in PADS_ENCODINGS:
        try:
            text = payload.decode(encoding)
        except UnicodeDecodeError:
            continue
        candidates.append((_format_score(text), encoding, text))

    if not candidates:
        raise UnicodeError("PADS file cannot be decoded as UTF-8, CP936, CP1252, or Latin-1")

    _, encoding, text = max(candidates, key=lambda item: (item[0], -PADS_ENCODINGS.index(item[1])))
    return text.splitlines(keepends=True), encoding


def parse_pads_header(lines: Iterable[str], defaults=None) -> Dict[str, float]:
    """Return common header values without making callers know field order."""
    result = {"units": 1, "max_layer": 2, "arptom": 114300}
    if defaults:
        result.update(defaults)
    for line in lines:
        s = line.strip()
        if s.startswith("UNITS") and "MAXIMUMLAYER" not in s:
            parts = s.split()
            if len(parts) >= 2:
                try:
                    result["units"] = int(parts[1])
                except ValueError:
                    pass
        elif s.startswith("MAXIMUMLAYER"):
            parts = s.split()
            if len(parts) >= 2:
                try:
                    result["max_layer"] = int(parts[1])
                except ValueError:
                    pass
            continue
        elif s.startswith("ARPTOM"):
            parts = s.split()
            if len(parts) >= 2:
                try:
                    result["arptom"] = float(parts[1])
                except ValueError:
                    pass
    return result


def parse_pads_vias(lines: Iterable[str], via_cls=PadsViaDef):
    vias = {}
    in_via = False
    current_via = None
    for line in lines:
        s = line.strip()
        if s.startswith("*VIA*"):
            in_via = True
            continue
        if not in_via:
            continue
        if s.startswith("*") and not s.startswith("*REMARK*"):
            break
        if not s or s.startswith("*REMARK*"):
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        if not parts[0].startswith("-") and not parts[0].isdigit():
            try:
                current_via = via_cls(parts[0], float(parts[1]), [])
                vias[parts[0]] = current_via
            except (ValueError, IndexError):
                current_via = None
        elif current_via is not None:
            try:
                level = int(parts[0])
                size = float(parts[1])
                shape = parts[2] if len(parts) > 2 else "R"
                current_via.pads.append((level, size, shape))
            except (ValueError, IndexError):
                pass
    return vias


def parse_pads_parts(lines: Iterable[str], part_cls=PadsPart):
    parts = {}
    in_part = False
    for line in lines:
        s = line.strip()
        if s.startswith("*PART*"):
            in_part = True
            continue
        if not in_part:
            continue
        if s.startswith("*") and not s.startswith("*REMARK*"):
            break
        if not s or s.startswith("*REMARK*") or s.startswith(("VALUE", "Regular", "Ref.Des.", "Value", "Comment", "NONE")):
            continue
        fields = s.split()
        if len(fields) < 5 or not re.match(r"^[A-Z]+\d+", fields[0]):
            continue
        try:
            alt = int(fields[7]) if len(fields) >= 8 else 0
            parts[fields[0]] = part_cls(fields[0], float(fields[2]), float(fields[3]), float(fields[4]), fields[1], alt)
        except (ValueError, IndexError, TypeError):
            pass
    return parts


def parse_pads_routes(lines: Iterable[str], point_cls=PadsRoutePoint, thermal_points: Optional[list] = None):
    routes = []
    route_nets = []
    in_route = False
    current_net = ""
    current_connection = None

    def flush():
        nonlocal current_connection
        if current_connection is not None:
            routes.append(current_connection)
            route_nets.append(current_net)
            current_connection = None

    for line in lines:
        s = line.strip()
        if s == "*ROUTE*":
            in_route = True
            continue
        if not in_route:
            continue
        if s.startswith("*") and not s.startswith("*SIGNAL*") and not s.startswith("*REMARK*"):
            flush()
            break
        if not s or s.startswith("*REMARK*"):
            continue
        if s.startswith("*SIGNAL*"):
            flush()
            fields = s.split()
            current_net = fields[1] if len(fields) > 1 else "?"
            continue

        fields = s.split()
        try:
            x, y = float(fields[0]), float(fields[1])
            layer, width, flags = int(fields[2]), float(fields[3]), int(fields[4])
            extra = fields[5:]
        except (ValueError, IndexError):
            flush()
            continue

        if thermal_points is not None and layer >= 64 and "THERMAL" in " ".join(extra):
            thermal_points.append((x, y, layer, current_net))
        if current_connection is None:
            current_connection = []
        current_connection.append(point_cls(x, y, layer, width, flags, current_net, extra))

    flush()
    return routes, route_nets


def transform_error_allowed(error_mm: Optional[float], threshold_mm: float = DEFAULT_MAX_TRANSFORM_ERROR_MM) -> bool:
    """Return whether a fitted coordinate transform is safe to apply."""
    return error_mm is not None and threshold_mm >= 0 and error_mm <= threshold_mm
