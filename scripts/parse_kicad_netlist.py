#!/usr/bin/env python3
"""
parse_kicad_netlist.py — Native KiCad netlist parser for the ee-review skill.

WHY THIS EXISTS (and why it is NOT a hand-rolled parser)
-------------------------------------------------------
KiCad ships an OFFICIAL netlist reader, ``kicad_netlist_reader.py``, inside every
KiCad install. It parses the KiCad *generic XML* netlist
(``kicad-cli sch export netlist --format kicadxml``) using KiCad's own SAX parser.
That is the authoritative, format-stable source of truth.

Re-implementing an S-expression or XML parser for KiCad netlists is both
redundant and a direct violation of this skill's own Rule 0 ("don't hand-roll
parsing — it produces false 'not connected' findings"). We therefore import
KiCad's own reader and wrap it, instead of writing a second parser.

THE FORMAT TRAP (this is the bug that broke the old workflow)
------------------------------------------------------------
``kicad-cli sch export netlist`` defaults to ``kicadsexpr`` (S-expression), which
``kicad_netlist_reader`` CANNOT parse (it is an XML reader). The legacy
``parse_netlist.py`` (``TelNetlist``) only understands TARGET ``$NETS``/``$PACKAGES``
text. So the OLD instruction "KiCad ``.net`` -> ``parse_netlist.py``" silently
yielded 0 nets / 0 components. The fix is twofold:

  1. Export KiCad netlists as XML:  ``--format kicadxml``
  2. Parse them with KiCad's native reader (this module).

This module's ``KicadNetlist`` class exposes the SAME public interface as
``parse_netlist.TelNetlist`` — ``pin_net``, ``is_connected``, ``net_pins``,
``component_pins``, ``all_pins_of``, ``missing_pins``, ``verify_by_pinmap``,
``sanity``, ``ref_to_fp``, ``ref_to_val``, ``fp_to_refs``, ``duplicate_nets``,
``pin_conflicts`` — so ``references/netlist-verification.md`` and any script that
calls those methods keep working unchanged. Legacy TARGET ``.tel`` files should
continue to use ``parse_netlist.TelNetlist``.

Locating kicad_netlist_reader.py
--------------------------------
Set env ``KICAD_NETLIST_READER`` to its absolute path, OR it is auto-discovered
from the common install locations for macOS / Linux / Windows. (The skill already
requires KiCad to be installed for ``kicad-cli``, so the reader is always present
somewhere — we just need its path.)

USAGE (library):
    from parse_kicad_netlist import KicadNetlist
    nl = KicadNetlist.from_file("board.xml")          # KiCad kicadxml netlist
    nl.pin_net("U26", "24")          -> "3V3-EXP"   (or None)
    nl.component_pins("U26")         -> {"24": "3V3-EXP", ...}
    nl.net_pins("CH_SDA_L15")        -> {"R316.1", "TP139.1", ...}
    nl.is_connected("U26", "22")     -> True
    nl.missing_pins("U26", all_pins) -> set of pins absent from the whole netlist
    nl.verify_by_pinmap("U26", {"24": "3V3", "12": "GND", "23": "SDA", "22": "SCL"})
    nl.ref_to_fp["U81"]              -> "TSSOP-24_L7-8-W4-4-..."
    nl.fp_to_refs["MSOP-10..."]      -> {"U11", "U12", ...}
    nl.lib_pins("U26")               -> ["1", "2", ..., "48"]   (device full pin list)

USAGE (CLI):
    python3 parse_kicad_netlist.py board.xml
    python3 parse_kicad_netlist.py board.xml --comp U26
    python3 parse_kicad_netlist.py board.xml --pins U26.24,U26.23,U26.22
    python3 parse_kicad_netlist.py board.xml --net CH_SDA_L15
    python3 parse_kicad_netlist.py board.xml --verify U26:24=3V3,12=GND,23=SDA,22=SCL
"""

import argparse
import importlib.util
import os
import re
import sys
from collections import defaultdict


# ----------------------------------------------------------------- discovery
def _load_kicad_reader():
    """Import KiCad's official kicad_netlist_reader module from the install."""
    candidates = []
    env = os.environ.get("KICAD_NETLIST_READER")
    if env:
        candidates.append(env)
    candidates += [
        # macOS (homebrew cask & official dmg)
        "/Applications/KiCad/KiCad.app/Contents/SharedSupport/plugins/kicad_netlist_reader.py",
        "/opt/homebrew/Caskroom/kicad/*/KiCad.app/Contents/SharedSupport/plugins/kicad_netlist_reader.py",
        # Linux
        "/usr/share/kicad/plugins/kicad_netlist_reader.py",
        "/usr/lib/kicad/plugins/kicad_netlist_reader.py",
        "/snap/kicad/current/usr/share/kicad/plugins/kicad_netlist_reader.py",
        # Windows
        "C:/Program Files/KiCad/share/kicad/plugins/kicad_netlist_reader.py",
        "C:/Program Files/KiCad/plugins/kicad_netlist_reader.py",
    ]
    for path in candidates:
        # expand a single '*' glob (kept simple on purpose)
        if "*" in path:
            import glob
            matches = sorted(glob.glob(path))
            if matches:
                path = matches[-1]
            else:
                continue
        if path and os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("kicad_netlist_reader", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError(
        "Could not locate KiCad's kicad_netlist_reader.py. Set the environment "
        "variable KICAD_NETLIST_READER to its absolute path, or install KiCad "
        "(this skill already requires kicad-cli). Typical locations:\n"
        "  macOS : /Applications/KiCad/KiCad.app/Contents/SharedSupport/plugins/\n"
        "  Linux : /usr/share/kicad/plugins/\n"
        "  Win   : C:/Program Files/KiCad/share/kicad/plugins/"
    )


# --------------------------------------------------------------- token matcher
# Net-name matching for verify_by_pinmap. We tokenize on separators and require
# the expected string to be a WHOLE token, which fixes the old substring bug
# where "GND" falsely matched "AGND"/"DGND" and "VCC" matched "VCC_1V8".
# (Different grounds are genuinely different nets; "VCC_1V8" sharing the "VCC"
# token IS the same power domain and is correctly accepted.)
_SEP = re.compile(r"[_\-/. ]")


def _net_matches(net, expected):
    if net is None:
        return False
    if expected is None:
        return True
    n = net.strip()
    e = expected.strip()
    if not e:
        return True
    if n.lower() == e.lower():
        return True
    ntokens = {t.lower() for t in _SEP.split(n) if t}
    return e.lower() in ntokens


def _full_pins(comp):
    """Extract the device's full pin list (pin numbers) from a kicad_netlist_reader
    ``comp`` object, reading the ``<units><unit><pins><pin num=.../></pins>`` tree."""
    out = []
    units = comp.element.getChild("units")
    if not units:
        return out
    for unit in units.getChildren("unit"):
        pins_el = unit.getChild("pins")
        if not pins_el:
            continue
        for p in pins_el.getChildren("pin"):
            num = p.get("pin", "num")
            if num:
                out.append(num)
    return out


class KicadNetlist:
    """Drop-in, native-KiCad-compatible replacement for ``TelNetlist``.

    Built from KiCad's own ``kicad_netlist_reader.netlist`` object so every
    pin->net fact is proven by KiCad's parser, never by ad-hoc string scanning.
    """

    def __init__(self):
        self.net_to_pins = defaultdict(set)   # net name -> {REF.PIN, ...}
        self.pin_to_net = {}                  # "REF.PIN" -> net name
        self.refs = set()                     # all component references
        self.ref_to_fp = {}                   # REF -> footprint string
        self.ref_to_val = {}                  # REF -> value string
        self.ref_to_dnp = {}                  # REF -> bool (do-not-populate)
        self.fp_to_refs = defaultdict(set)    # footprint -> {REF, ...}
        self.ref_to_full_pins = {}            # REF -> [pin numbers] (device full list)
        # export-defect tracking
        self.duplicate_nets = []              # net names declared more than once
        self.pin_conflicts = defaultdict(list)  # "REF.PIN" -> [net names]

    # ----------------------------------------------------------- construction
    @classmethod
    def from_file(cls, path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
        stripped = head.lstrip()
        if stripped.startswith("<?xml") or "<export" in head[:200]:
            return cls._from_kicad_xml(path)
        if stripped.startswith("(export"):
            raise ValueError(
                "Input looks like a KiCad S-expression netlist (kicadsexpr), which "
                "KiCad's native reader cannot parse. Re-export it as XML with:\n"
                "    kicad-cli sch export netlist --format kicadxml -o board.xml board.kicad_sch\n"
                "then pass board.xml to KicadNetlist.from_file()."
            )
        raise ValueError(
            "Unrecognized netlist format. Expected KiCad kicadxml (XML) produced by "
            "`kicad-cli sch export netlist --format kicadxml`."
        )

    @classmethod
    def from_text(cls, text):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as fh:
            fh.write(text)
            tmp = fh.name
        try:
            return cls._from_kicad_xml(tmp)
        finally:
            os.unlink(tmp)

    @classmethod
    def _from_kicad_xml(cls, path):
        mod = _load_kicad_reader()
        knr_net = mod.netlist(path)
        return cls._from_knr(knr_net)

    @classmethod
    def _from_knr(cls, knr_net):
        nl = cls()
        # --- component metadata + full pin lists -----------------------------
        for c in knr_net.components:
            ref = c.getRef()
            if not ref:
                continue
            nl.refs.add(ref)
            nl.ref_to_fp.setdefault(ref, c.getFootprint() or "")
            nl.ref_to_val.setdefault(ref, c.getValue() or "")
            nl.ref_to_dnp[ref] = c.getDNP()
            fp = nl.ref_to_fp.get(ref, "")
            if fp:
                nl.fp_to_refs[fp].add(ref)
            nl.ref_to_full_pins[ref] = _full_pins(c)
        # --- net -> pin index (authoritative, from KiCad's parser) ------------
        for net_node in knr_net.nets:
            net_name = net_node.get("net", "name")
            if net_name in nl.net_to_pins:
                nl.duplicate_nets.append(net_name)
            nl.net_to_pins.setdefault(net_name, set())
            for node in net_node.children:
                if getattr(node, "name", None) != "node":
                    continue
                ref = node.get("node", "ref")
                pin = node.get("node", "pin")
                if not ref or not pin:
                    continue
                key = f"{ref}.{pin}"
                nl.pin_to_net[key] = net_name
                nl.net_to_pins[net_name].add(key)
                nl.refs.add(ref)
                prev = nl.pin_to_net.get(key)
                if prev is not None and prev != net_name:
                    nl.pin_conflicts[key].append(net_name)
        return nl

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
            "refs_without_footprint": sorted(
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
        """Return {pin: net} for every pin of `ref` that appears in the netlist
        (i.e. pins that are actually connected to something)."""
        out = {}
        for key, net in self.pin_to_net.items():
            if key.startswith(ref + "."):
                out[key.split(".", 1)[1]] = net
        return out

    def all_pins_of(self, ref):
        return set(p for p in self.pin_to_net if p.startswith(ref + "."))

    def lib_pins(self, ref):
        """Return the device's FULL pin list (from the symbol), regardless of
        whether each pin is connected. Useful to detect unconnected pins."""
        return list(self.ref_to_full_pins.get(ref, []))

    def missing_pins(self, ref, expected_pins):
        """Pins from expected_pins that are absent anywhere in the netlist
        (i.e. genuinely not connected to anything).

        `expected_pins` is typically the device's full pin list (use
        ``lib_pins(ref)``) when you want to find every unconnected pin.
        """
        present = self.all_pins_of(ref)
        return set(str(p) for p in expected_pins) - present

    def verify_by_pinmap(self, ref, pinmap):
        """pinmap: {pin: expected_net_substring_or_None}. Returns list of dicts:
        {pin, connected(bool), net, expected, ok(bool)}.

        `ok` is True when connected AND the net name contains `expected` as a
        WHOLE token (case-insensitive). Different grounds (AGND vs GND) no longer
        false-match; same-domain supplies (VCC_1V8 vs VCC) correctly match.
        `expected` may be None to only check presence.
        """
        results = []
        for pin, expected in pinmap.items():
            net = self.pin_net(ref, pin)
            connected = net is not None
            if expected is None:
                ok = connected
            else:
                ok = connected and _net_matches(net, expected)
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
        description="Parse a KiCad kicadxml netlist (native KiCad reader) and provide "
                    "reverse-lookup helpers.",
        epilog="Examples: --comp U26; --pins U26.24,U26.23; --net GND; "
               "--verify U26:24=3V3,12=GND",
    )
    parser.add_argument("path", help="Path to the KiCad kicadxml netlist (.xml)")
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
        nl = KicadNetlist.from_file(args.path)
    except (OSError, ValueError, ImportError) as exc:
        parser.error(f"{args.path!r}: {exc}")

    if not any((args.comp, args.pins, args.net, args.verify)):
        s = nl.sanity()
        print(f"Parsed {args.path}: {s['nets']} nets, {s['refs']} components, {s['pins']} pins.")
        if s["duplicate_nets"]:
            print(f"  !! duplicate net names: {s['duplicate_nets']}")
        if s["pin_conflicts"]:
            print(f"  !! pins in >1 net: {s['pin_conflicts']}")
        print(f"  refs without footprint: {len(s['refs_without_footprint'])}")
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
