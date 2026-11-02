#!/usr/bin/env python3
"""Parse PADS/EasyEDA ASCII netlist exports with *PART*/*SIGNAL* sections."""

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
                    section = {"PART": "PART", "NET": "NET", "MISC": "END", "END": "END"}.get(tag, "OTHER")
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
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--comp", help="show a component's connected pins")
    parser.add_argument("--net", help="show all pins on a net")
    parser.add_argument("--pins", help="comma-separated REF.PIN lookups")
    args = parser.parse_args()

    try:
        nl = PadsAsciiNetlist.from_file(args.file)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("sanity:", nl.sanity())
    sanity = nl.sanity()
    if sanity["duplicate_nets"] or sanity["pin_conflicts"] or sanity["unknown_refs"]:
        print("ERROR: parser sanity gate failed; do not use connectivity lookups", file=sys.stderr)
        return 3
    if args.comp:
        print(f"{args.comp} footprint: {nl.parts.get(args.comp)}")
        print(f"{args.comp} pins: {nl.component_pins(args.comp)}")
    if args.net:
        print(f"{args.net}: {sorted(nl.net_pins(args.net))}")
    if args.pins:
        for item in args.pins.split(","):
            ref, sep, pin = item.partition(".")
            print(f"{item}: {nl.pin_net(ref, pin) if sep else 'INVALID; expected REF.PIN'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
