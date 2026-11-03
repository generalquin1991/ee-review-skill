#!/usr/bin/env python3
"""Parse PADS/EasyEDA ASCII nets and component attributes from structured sections."""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


_PIN_TOKEN = re.compile(r"^([^\s.]+)\.([^\s.]+)$")


class PadsAsciiNetlist:
    """Section-aware pin/net index for PADS ASCII netlist exports."""

    def __init__(self):
        self.parts = {}
        self.attributes = defaultdict(dict)
        self.net_to_pins = defaultdict(set)
        self.pin_to_net = {}
        self.duplicate_nets = []
        self.pin_conflicts = defaultdict(list)
        self.unknown_refs = set()

    @classmethod
    def from_file(cls, path):
        data = Path(path).read_bytes()
        for encoding in ("utf-8-sig", "cp936", "cp1252", "latin-1"):
            try:
                return cls.from_text(data.decode(encoding))
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot decode PADS ASCII file: {path}")

    @classmethod
    def from_text(cls, text):
        nl = cls()
        section = None
        current_net = None
        current_attr_ref = None
        reading_attributes = False

        for line_no, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line:
                continue

            marker = re.match(r"^\*([A-Z][A-Z0-9_-]*)\*", line, re.IGNORECASE)
            if marker:
                tag = marker.group(1).upper()
                if tag == "SIGNAL":
                    name = line[marker.end():].strip().strip("'\"")
                    if not name:
                        raise ValueError(f"Line {line_no}: empty *SIGNAL* name")
                    if name in nl.net_to_pins:
                        nl.duplicate_nets.append(name)
                    nl.net_to_pins[name]
                    current_net = name
                    section = "NET"
                else:
                    current_net = None
                    section = {"PART": "PART", "NET": "NET", "MISC": "MISC", "END": "END"}.get(tag, "OTHER")
                continue

            if section == "PART":
                fields = line.split()
                if len(fields) < 2 or fields[0].upper() in {"ITEMS", "ATTRIBUTE", "VALUES"}:
                    continue
                ref, footprint = fields[0], fields[1]
                if ref in nl.parts:
                    raise ValueError(f"Line {line_no}: duplicate component reference {ref}")
                nl.parts[ref] = footprint
            elif section == "NET":
                if current_net is None:
                    continue
                for token in line.split():
                    match = _PIN_TOKEN.fullmatch(token.strip(","))
                    if not match:
                        raise ValueError(f"Line {line_no}: malformed pin token {token!r}")
                    ref, pin = match.groups()
                    qualified = f"{ref}.{pin}"
                    nl.net_to_pins[current_net].add(qualified)
                    previous = nl.pin_to_net.get(qualified)
                    if previous is not None and previous != current_net:
                        nl.pin_conflicts[qualified].append(current_net)
                    nl.pin_to_net[qualified] = current_net
                    if ref not in nl.parts:
                        nl.unknown_refs.add(ref)
            elif section == "MISC":
                if line == "ATTRIBUTE VALUES":
                    reading_attributes = True
                    current_attr_ref = None
                    continue
                if not reading_attributes:
                    continue
                part_match = re.fullmatch(r"PART\s+(\S+)", line)
                if part_match:
                    current_attr_ref = part_match.group(1)
                    nl.attributes[current_attr_ref]
                    continue
                if line == "}":
                    current_attr_ref = None
                    continue
                if current_attr_ref and line.startswith('"'):
                    key, value = _parse_attribute(line, line_no)
                    nl.attributes[current_attr_ref][key] = value

        if not nl.parts:
            raise ValueError("No *PART* component records found")
        if not nl.net_to_pins:
            raise ValueError("No *SIGNAL* net records found")
        return nl

    def pin_net(self, ref, pin):
        return self.pin_to_net.get(f"{ref}.{pin}")

    def component_pins(self, ref):
        prefix = f"{ref}."
        return {key[len(prefix):]: net for key, net in self.pin_to_net.items() if key.startswith(prefix)}

    def net_pins(self, net):
        return set(self.net_to_pins.get(net, ()))

    def is_connected(self, ref, pin):
        return self.pin_net(ref, pin) is not None

    def missing_pins(self, ref, expected_pins):
        return set(map(str, expected_pins)) - set(self.component_pins(ref))

    def sanity(self):
        return {
            "parts": len(self.parts),
            "nets": len(self.net_to_pins),
            "pins": len(self.pin_to_net),
            "duplicate_nets": sorted(set(self.duplicate_nets)),
            "pin_conflicts": {k: sorted(set(v)) for k, v in self.pin_conflicts.items()},
            "unknown_refs": sorted(self.unknown_refs),
            "attributes_without_part": sorted(set(self.attributes) - set(self.parts)),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--comp", help="show a component's connected pins")
    parser.add_argument("--net", help="show all pins on a net")
    parser.add_argument("--pins", help="comma-separated REF.PIN lookups")
    parser.add_argument("--attrs", help="show all exported attributes for a reference")
    args = parser.parse_args()

    try:
        nl = PadsAsciiNetlist.from_file(args.file)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    sanity = nl.sanity()
    print("sanity:", sanity)
    if any(sanity[key] for key in ("duplicate_nets", "pin_conflicts", "unknown_refs", "attributes_without_part")):
        print("ERROR: parser sanity gate failed; do not use connectivity lookups", file=sys.stderr)
        return 3
    if args.comp:
        print(f"{args.comp} footprint: {nl.parts.get(args.comp)}")
        print(f"{args.comp} pins: {nl.component_pins(args.comp)}")
    if args.attrs:
        print(f"{args.attrs} attributes: {nl.attributes.get(args.attrs, {})}")
    if args.net:
        print(f"{args.net}: {sorted(nl.net_pins(args.net))}")
    if args.pins:
        for item in args.pins.split(","):
            ref, sep, pin = item.partition(".")
            print(f"{item}: {nl.pin_net(ref, pin) if sep else 'INVALID; expected REF.PIN'}")
    return 0


def _parse_attribute(line, line_no):
    escaped = False
    closing = None
    for index in range(1, len(line)):
        char = line[index]
        if char == '"' and not escaped:
            closing = index
            break
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    if closing is None:
        raise ValueError(f"Line {line_no}: unterminated attribute name")
    key = line[1:closing]
    value = line[closing + 1:].strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return key, value


if __name__ == "__main__":
    raise SystemExit(main())
