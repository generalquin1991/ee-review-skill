#!/usr/bin/env python3
"""
parse_netlist.py — Robust parser for TARGET-style `.tel` netlists (and similar
Net/Pin text netlists) used by the ee-review skill.

WHY THIS EXISTS
---------------
During an actual review, three independent critical findings were wrongly raised
because ad-hoc parsing scripts relied on line-prefix regex (`line.startswith("'")`)
and therefore MISSED continuation lines of long nets. A `.tel` net definition can
span many physical lines; only the FIRST line carries the net name, while the
continuation lines contain only `REF.PIN` tokens (often comma-separated). Any
"pin is missing / device is not connected" claim that is based on scanning line
prefixes is therefore UNRELIABLE and MUST use this parser instead.

SECOND, SUBTLER TRAP  (fixed 2026-09-20 — this bug produced a HARD FALSE POSITIVE)
---------------------------------------------------------------------------------
Exporter quoting of record names is INCONSISTENT. In the same file you can see:
      '+5V'     ; C53.2 C54.2 ...
      'GND'     ; ...          <- quoted
      GND       ; C1.1 C2.1 ...      <- NOT quoted
      CC1       ; R415.1 ...
So the rule "a new net record starts with a quote" is WRONG. If you use it, every
unquoted record is mis-read as a *continuation line* of the previous net, and the
two nets get silently MERGED. Real damage seen in practice: the plain `GND` net
(1155 pins) was appended to the preceding 7-pin `VCC_I2C_MATRIX` net, which made
it look as though a switch IC's VCC pin was shorted to ground. Nothing was wrong
with the board — only with the parser.

THE RELIABLE DELIMITERS (use these, never the leading quote):
  * $NETS      record starts on ANY line containing ";" (quoted name or not)
  * $PACKAGES  record starts on a line containing " ! " (FP ! ALT_FP ! VALUE ; REFS)
Continuation lines never contain those delimiters.

This module:
  * parses nets and packages correctly across continuation lines (state-machine,
    section-aware, quote-agnostic),
  * builds `pin -> net` and `net -> pins` indexes,
  * exposes reverse-lookup helpers so you can PROVE a connection instead of
    assuming it,
  * provides `verify_by_pinmap()` to check that every required pin of a part
    (VCC/GND/SDA/SCL/straps) is actually connected,
  * records `pin_conflicts` (a pin claimed by >1 net) and `duplicate_nets`
    (same net name declared twice) so export defects are not silently hidden.

USAGE (library):
    from parse_netlist import TelNetlist
    nl = TelNetlist.from_file("board.tel")
    nl.pin_net("U26", "24")          -> "3V3-EXP"   (or None)
    nl.component_pins("U26")         -> {"24": "3V3-EXP", "23": "GPIO47-I2C-SDA", ...}
    nl.net_pins("CH_SDA_L15")        -> {"R316.1", "TP139.1", "U68.E4"}
    nl.is_connected("U26", "22")     -> True
    nl.missing_pins("U26", all_pins) -> set of pins absent from the whole netlist
    nl.verify_by_pinmap("U26", {"24": "3V3", "12": "GND", "23": "SDA", "22": "SCL"})
    nl.ref_to_fp["U81"]              -> "TSSOP-24_L7-8-W4-4-..."   (footprint)
    nl.fp_to_refs["MSOP-10..."]      -> {"U11", "U12", ...}

USAGE (CLI):
    python3 parse_netlist.py board.tel
    python3 parse_netlist.py board.tel --comp U26
    python3 parse_netlist.py board.tel --pins U26.24,U26.23,U26.22
    python3 parse_netlist.py board.tel --net CH_SDA_L15
    python3 parse_netlist.py board.tel --verify U26:24=3V3,12=GND,23=SDA,22=SCL
"""

import argparse
import re
import sys
from collections import defaultdict


class TelNetlist:
    def __init__(self):
        self.net_to_pins = defaultdict(set)   # net name -> {REF.PIN, ...}
        self.pin_to_net = {}                  # "REF.PIN" -> net name
        self.refs = set()                     # all component references
        self.section = None                   # $PACKAGES / $NETS / ...
        # package metadata
        self.ref_to_fp = {}                   # REF -> footprint string
        self.ref_to_val = {}                  # REF -> value string (e.g. "DNP")
        self.fp_to_refs = defaultdict(set)    # footprint -> {REF, ...}
        self.ref_to_alt_fp = {}
        # export-defect tracking
        self.duplicate_nets = []              # net names declared more than once
        self.pin_conflicts = defaultdict(list)  # "REF.PIN" -> [net names]

    # ---------------------------------------------------------------- parsing
    @classmethod
    def from_file(cls, path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return cls.from_lines(f.read().replace("\r\n", "\n").split("\n"))

    @classmethod
    def from_text(cls, text):
        return cls.from_lines(text.replace("\r\n", "\n").split("\n"))

    @classmethod
    def from_lines(cls, lines):
        """Section-aware state machine.

        A record is accumulated across physical lines. The ONLY reliable
        "new record" signals are:
            $PACKAGES -> the line contains " ! "
            $NETS     -> the line contains ";"
        (the leading quote is NOT reliable: exporter quoting is inconsistent)
        """
        nl = cls()
        section = None
        buf = None

        def flush():
            if buf is None:
                return
            if section == "$PACKAGES":
                nl._add_package(buf)
            elif section == "$NETS":
                nl._add_net_record(buf)

        for raw in lines:
            s = raw.strip()
            if not s:
                continue
            marker = re.fullmatch(r"\$([A-Za-z_]+)", s)
            if marker:
                flush()
                buf = None
                section = "$" + marker.group(1)
                nl.section = section
                continue

            if section == "$PACKAGES":
                if " ! " in s:
                    flush()
                    buf = s
                elif buf is None:
                    buf = s
                else:
                    buf += " " + s
            elif section == "$NETS":
                if ";" in s:
                    flush()
                    buf = s
                elif buf is None:
                    buf = s
                else:
                    buf += " " + s
            else:
                buf = s if buf is None else buf + " " + s

        flush()
        return nl

    # ---- record level -----------------------------------------------------
    def _add_package(self, rec):
        pre, sep, rest = rec.partition(";")
        fields = [f.strip() for f in pre.split("!")]
        fp = fields[0].strip() if fields else ""
        alt = fields[1].strip() if len(fields) > 1 else ""
        raw_val = fields[2] if len(fields) > 2 else ""
        # value field is quoted and may carry a trailing comma (fields can span
        # lines): '2.2uF' , / DNP / '{Value}' ,
        val = re.sub(r"^[\s',]+|[\s',]+$", "", raw_val)
        for tok in rest.replace(",", " ").split():
            ref = tok.strip(",").strip()
            if not ref or "." in ref:
                continue
            self.refs.add(ref)
            # first (non-sentinel) assignment wins; avoid index artifacts
            self.ref_to_fp.setdefault(ref, fp)
            self.ref_to_alt_fp.setdefault(ref, alt)
            self.ref_to_val.setdefault(ref, val)
            if fp:
                self.fp_to_refs[fp].add(ref)

    def _add_net_record(self, rec):
        name, sep, rest = rec.partition(";")
        name = name.strip().strip("'").strip().strip(",").strip()
        members = [m for m in (t.strip(",").strip() for t in rest.split()) if m]
        if not name:
            for tok in members:
                if "." not in tok:
                    self.refs.add(tok)
            return
        if name in self.net_to_pins:
            self.duplicate_nets.append(name)
        self.net_to_pins[name]  # register the net even if it has 0/1 members
        self._add(name, members)

    def _add(self, net, members):
        for tok in members:
            if "." not in tok:
                # a bare ref inside a net line (e.g. power-flag markers) -> skip pin index
                if tok:
                    self.refs.add(tok)
                continue
            self.net_to_pins[net].add(tok)
            prev = self.pin_to_net.get(tok)
            if prev is not None and prev != net:
                self.pin_conflicts[tok].append(net)
            self.pin_to_net[tok] = net
            self.refs.add(tok.split(".", 1)[0])

    # ----------------------------------------------------------- integrity
    def sanity(self):
        """Return a dict of export-consistency signals worth eyeballing before
        you trust any 'not connected' finding."""
        return {
            "nets": len(self.net_to_pins),
            "pins": len(self.pin_to_net),
            "refs": len(self.refs),
            "duplicate_nets": sorted(set(self.duplicate_nets)),
            "pin_conflicts": {k: sorted(set(v)) for k, v in self.pin_conflicts.items()},
            "nets_without_footprint": sorted(
                r for r in self.refs if not self.ref_to_fp.get(r, "")
            ),
        }

    # ----------------------------------------------------------- lookups
    def pin_net(self, ref, pin):
        """Return the net name a specific pin is connected to, or None."""
        return self.pin_to_net.get(f"{ref}.{pin}")

    def is_connected(self, ref, pin):
        return f"{ref}.{pin}" in self.pin_to_net

    def net_pins(self, net):
        return set(self.net_to_pins.get(net, set()))

    def component_pins(self, ref):
        """Return {pin: net} for every pin of `ref` that appears in the netlist."""
        out = {}
        for key, net in self.pin_to_net.items():
            if key.startswith(ref + "."):
                out[key.split(".", 1)[1]] = net
        return out

    def all_pins_of(self, ref):
        return set(p for p in self.pin_to_net if p.startswith(ref + "."))

    def missing_pins(self, ref, expected_pins):
        """Pins from expected_pins that are absent anywhere in the netlist
        (i.e. genuinely not connected to anything)."""
        present = self.all_pins_of(ref)
        return set(expected_pins) - present

    def verify_by_pinmap(self, ref, pinmap):
        """pinmap: {pin: expected_net_substring}. Returns list of dicts:
        {pin, connected(bool), net, expected, ok(bool)}.
        `ok` is True when connected AND the net name contains expected substring
        (case-insensitive); expected may be None to only check presence."""
        results = []
        for pin, expected in pinmap.items():
            net = self.pin_net(ref, pin)
            connected = net is not None
            if expected is None:
                ok = connected
            else:
                ok = connected and expected.lower() in net.lower()
            results.append({
                "pin": pin,
                "connected": connected,
                "net": net,
                "expected": expected,
                "ok": ok,
            })
        return results


# -------------------------------------------------------------------- CLI
def _print_comp(nl, ref):
    pins = nl.component_pins(ref)
    if not pins:
        print(f"  {ref}: no pins found in netlist")
        return
    print(f"  {ref} pins ({len(pins)}) fp={nl.ref_to_fp.get(ref)!r} val={nl.ref_to_val.get(ref)!r}:")
    for pin in sorted(pins, key=lambda p: (len(p), p)):
        print(f"    {pin:>5s} -> {pins[pin]}")


def main(argv):
    parser = argparse.ArgumentParser(
        description="Parse a TARGET-style netlist and provide reverse-lookup helpers.",
        epilog="Examples: --comp U26; --pins U26.24,U26.23; --net GND; "
               "--verify U26:24=3V3,12=GND",
    )
    parser.add_argument("path", help="Path to the .tel/.net/.dsn netlist")
    parser.add_argument("--comp", action="append", metavar="REF",
                        help="Print all pins for a component (repeatable)")
    parser.add_argument("--pins", action="append", metavar="ITEMS",
                        help="Look up REF.PIN values or net names, comma-separated")
    parser.add_argument("--net", action="append", metavar="NAME",
                        help="Print all pins on a net (repeatable)")
    parser.add_argument("--verify", action="append", metavar="SPEC",
                        help="Verify REF:pin=expected,pin=expected (repeatable)")

    if len(argv) < 2:
        parser.print_help()
        return 1

    args = parser.parse_args(argv[1:])
    try:
        nl = TelNetlist.from_file(args.path)
    except OSError as exc:
        parser.error(f"cannot read netlist {args.path!r}: {exc}")

    if not any((args.comp, args.pins, args.net, args.verify)):
        s = nl.sanity()
        print(f"Parsed {args.path}: {s['nets']} nets, {s['refs']} components, {s['pins']} pins.")
        if s["duplicate_nets"]:
            print(f"  !! duplicate net names: {s['duplicate_nets']}")
        if s["pin_conflicts"]:
            print(f"  !! pins in >1 net: {s['pin_conflicts']}")
        print(f"  refs without footprint: {len(s['nets_without_footprint'])}")
        return 0

    for ref in args.comp or []:
        _print_comp(nl, ref)

    for pins_arg in args.pins or []:
        for p in pins_arg.split(","):
            if "." in p:
                ref, pin = p.split(".", 1)
                print(f"  {p} -> {nl.pin_net(ref, pin)}")
            else:
                print(f"  net '{p}': {sorted(nl.net_pins(p))}")

    for net in args.net or []:
        print(f"  net '{net}': {sorted(nl.net_pins(net))}")

    for spec in args.verify or []:
        # format: REF:pin=exp,pin=exp  (exp empty = only check presence)
        if ":" not in spec:
            parser.error(f"invalid --verify value {spec!r}; expected REF:pin=expected,...")
        ref, pairs = spec.split(":", 1)
        pinmap = {}
        try:
            for kv in pairs.split(","):
                pin, exp = kv.split("=", 1)
                pinmap[pin] = exp
        except ValueError:
            parser.error(f"invalid --verify value {spec!r}; expected REF:pin=expected,...")
        print(f"  verify {ref}:")
        for result in nl.verify_by_pinmap(ref, pinmap):
            status = "OK " if result["ok"] else ("MISSING" if not result["connected"] else "WRONG-NET")
            print(f"    pin {result['pin']:>4s}: {status}  net={result['net']}  expected~{result['expected']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
