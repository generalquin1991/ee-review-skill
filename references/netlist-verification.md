# Netlist Verification Discipline (MANDATORY for netlist/schematic reviews)

This document is the anti-bias checklist that MUST be followed whenever a review
asserts anything about component pins, nets, or connections in a netlist
(`.tel`, `.net`, `.dsn`, KiCad `kicadxml`, Altium compiled nets, etc.). It was created after several
critical findings were raised on a real 16-channel battery-jig review and then
had to be **retracted** because the supporting evidence was wrong.

The root cause in every case was the same: an ad-hoc parsing script that scanned
lines by prefix (`line.startswith("'")`) and therefore **missed continuation
lines of long nets**, OR a claim made from memory/assumption instead of from the
netlist itself.

There are **two** independent text-netlist parser traps, and both were hit in practice. Native Altium sources add a third trap: raw OLE records and drawing coordinates do not by themselves encode the project-level flattened net graph.

1. **Missing continuation lines** — a scanner that reads only the first line of a
   long net silently drops the rest (the original bug).
2. **Merging nets because the exporter quotes names inconsistently** (fixed
   2026-09-20). The SAME file contains both `'+5V' ; C53.2 ...` and plain
   `GND ; C1.1 C2.1 ...`. Any rule of the form "a new net record starts with a
   quote" is therefore wrong: every unquoted record gets treated as a
   *continuation line of the previous net* and the two nets are silently merged.
   Real damage: the plain `GND` net (1155 pins) was appended to the preceding
   7-pin `VCC_I2C_MATRIX` net, which produced a published **critical** finding
   "TCA9548A VCC pin shorted to ground". The board had no such defect — only the
   parser did. Same root cause also produced false "decoupling cap shorted",
   "CC resistor shorted" and "228 parts have no footprint" findings.

## Rule 0 — Use the canonical parser, never line-prefix regex

There are **three** source paths; pick the matching parser:

- **KiCad** (`.kicad_sch` / `.sch` / `.schdoc`): export the netlist as XML first —
  `kicad-cli sch export netlist --format kicadxml -o board.xml <file>.kicad_sch` — then parse
  with `scripts/parse_kicad_netlist.py` (import `KicadNetlist`). `KicadNetlist` wraps KiCad's own
  `kicad_netlist_reader`, so every pin→net fact comes from KiCad's **native** parser. **Do NOT**
  feed the default `kicadsexpr` (S-expression) export to either parser — it is not XML and silently
  yields 0 nets / 0 components.
- **TARGET / PADS-style** (`.tel` / `.net` / `.dsn` with `$NETS`/`$PACKAGES`): parse with
  `scripts/parse_netlist.py` (import `TelNetlist`). It is **continuation-aware**: a `.tel` net
  definition can span many physical lines; only the first begins with `'`/`$`, while continuation
  lines are indented and hold only `REF.PIN` tokens. Line-prefix scanning silently drops those
  continuation pins and will report a connected pin as "missing".

- **Altium** (`.PrjPcb` with child `.SchDoc` files): parse with `altium-monkey` using
  `AltiumDesign.from_prjpcb(...)` followed by `design.compile(force=True)`. Use the compiled
  design's `nets`, `terminals`, and `endpoints`, and record diagnostics. Do not use raw OLE
  records, `strings`, SVG/PDF geometry, or component coordinates as a connectivity parser. An
  individual `AltiumSchDoc` without its project is limited to sheet-local inspection and cannot
  prove flattened cross-sheet connectivity. Critical claims additionally require the diagnostic
  and completeness gate in `references/altium-monkey.md`.

The text-netlist classes expose the same interface — `pin_net`, `net_pins`, `component_pins`,
`is_connected`, `missing_pins`, `verify_by_pinmap` — so that discipline is format-agnostic.
`altium-monkey` uses compiled `nets` with `terminals`/`endpoints` instead. (`KicadNetlist`
additionally exposes `lib_pins(ref)` = the device's full pin list, which is the convenient input to
`missing_pins` for finding every unconnected pin.)

KiCad example:
```python
from parse_kicad_netlist import KicadNetlist
nl = KicadNetlist.from_file("board.xml")          # KiCad kicadxml netlist
nl.pin_net("U26", "24")            # -> net name or None
nl.component_pins("U26")           # -> {pin: net, ...}  (ALL connected pins)
nl.net_pins("CH_SDA_L15")          # -> set of REF.PIN on that net
nl.is_connected("U26", "22")       # -> bool
nl.missing_pins("U26", nl.lib_pins("U26"))  # -> pins absent from the WHOLE netlist
nl.verify_by_pinmap("U26", {"24":"3V3","12":"GND","23":"SDA","22":"SCL"})
```

TARGET example:
```python
from parse_netlist import TelNetlist
nl = TelNetlist.from_file("board.tel")
nl.pin_net("U26", "24")            # -> net name or None
nl.component_pins("U26")           # -> {pin: net, ...}  (ALL pins, incl. continuation)
nl.net_pins("CH_SDA_L15")          # -> set of REF.PIN on that net
nl.is_connected("U26", "22")       # -> bool
nl.missing_pins("U26", all_pins)   # -> pins absent from the WHOLE netlist
nl.verify_by_pinmap("U26", {"24":"3V3","12":"GND","23":"SDA","22":"SCL"})
```

CLI:
```bash
# KiCad
python3 scripts/parse_kicad_netlist.py board.xml --comp U26
python3 scripts/parse_kicad_netlist.py board.xml --verify U26:24=3V3,12=GND,23=SDA,22=SCL
# TARGET
python3 scripts/parse_netlist.py board.tel --comp U26
python3 scripts/parse_netlist.py board.tel --pins U3.17,U66.B2,ALTER_L15
python3 scripts/parse_netlist.py board.tel --net CH_SDA_L15
python3 scripts/parse_netlist.py board.tel --verify U26:24=3V3,12=GND,23=SDA,22=SCL
```

### Rule 0a — Reliable record delimiters (never use the leading quote)

| Section | A new record starts on a line containing… |
|---------|-------------------------------------------|
| `$NETS` | `;` (regardless of whether the name is quoted) |
| `$PACKAGES` | ` ! ` (the field separator of `FP ! ALT_FP ! VALUE ; REFS`) |

Continuation lines never contain those delimiters. `TelNetlist` implements exactly
this rule and additionally records `duplicate_nets` and `pin_conflicts`.

### Rule 0b — Run the self-consistency check BEFORE writing any finding

`TelNetlist.sanity()` is a mandatory gate. If it reports anything unexpected, fix
the parse before you analyse the circuit:

```python
nl = TelNetlist.from_file("board.tel")
nl.sanity()
# {'nets': 1810, 'pins': 5505, 'refs': 1791,
#  'duplicate_nets': [...], 'pin_conflicts': {...},
#  'nets_without_footprint': [...]}
```

Sanity signals to interpret:
- **`nets_without_footprint` non-empty** → you are probably mis-splitting the
  `$PACKAGES` section; real boards normally assign a footprint to every ref.
  (A bogus "228 parts have no footprint" finding came from exactly this.)
- **A net whose name looks like a `VCC`/signal rail but whose pin count is wildly
  larger than any plausible rail** → suspect a merged net, not a short circuit.
- **`duplicate_nets` / `pin_conflicts` non-empty** → export defect; report it as
  such rather than silently merging.

Cross-check rule of thumb: a genuine "X is shorted to Y" finding must be
consistent with the pin counts. `VCC_I2C_MATRIX` holding a single IC's VCC pin,
three decoupling caps and three resistors (7 pins) is normal; the same net holding
1155 pins including every GND pin of the board is a parser error, not a short.

## Rule 1 — Prove every connection by reverse lookup

Before writing any finding that says a pin is **connected to / driven by / shorted
to** something, look it up with `pin_net()` / `net_pins()`. Do not infer from the
component's position in a line you eyeballed.

## Rule 2 — "Not connected / pin missing" MUST be proven on the full netlist

A claim like "U26 is missing VCC/GND/SDA/SCL" is the most dangerous kind — it
invalidates an entire device. To make it, you MUST:
1. Call `component_pins(ref)` and confirm the pin truly does not appear **anywhere**
   (use `missing_pins` against the full pin list), AND
2. Confirm via `net_pins()` that no net carries that pin.
A pin that only shows up on a continuation line will look "missing" to a naive
scanner but is actually present. If you only checked line prefixes, your claim is
unverified — do not publish it.

## Rule 3 — Never assume a substitute part's architecture

When the design uses a part that differs from the PRD (e.g. MAX17262 substituted
for MAX17055), do NOT carry over the PRD part's assumptions (pinout, sense
resistor, address, supply). Pull the **substitute part's official datasheet** and
verify pin-by-pin against the netlist. In the real case, MAX17262 has **internal
current sensing (no CSP/CSN, no external RSENSE)**, so a "missing 50mΩ sense
resistor" finding was wrong. Treat the PRD clause as inapplicable, not as a defect.

## Rule 4 — Address / strap-pin claims need per-pin net tracing

I2C address conflicts and "wrong address" findings must be derived by tracing each
strap pin (`A0/A1/A2`) to its net and deciding H/L from the net's contents
(pull-up to 3V3 = H, tie to GND = L), NOT by assuming which physical pins are the
straps. A previous error assumed A0/A1/A2 = pins 1/2/3; the real symbol used
pin21 as A0. Trace every pin; never assume the strap-pin numbers.

## Rule 5 — Re-verify before re-asserting

If a prior round retracted a finding, and you intend to KEEP a similar remaining
finding, re-run the canonical parser on that exact evidence. The two surviving
CH15 criticals in the battery-jig review (CH_SDA_L15 missing its mux drive;
ALTER_L15 net absent) were re-confirmed with `component_pins` / `net_pins` after
the parser bug was fixed — only then were they retained.

## Rule 6 — Unsupported connectivity cannot be Critical

A connectivity claim (connected, unconnected, shorted, swapped, missing from a net, pulled to a rail) is Critical only with a `TelNetlist`, `KicadNetlist`, or successful `altium-monkey` compiled-project lookup quoted in the finding. A schematic PDF, screenshot, raw OLE record dump, SVG geometry, or component-coordinate inference without that lookup is at most `warning`, evidence `PDF-only; connection not proven` or an equivalent unsupported-source note. If the source cannot be compiled or the sheet is unreadable, the row is `not verifiable`. A readable wrong value (setpoint, voltage rating, abs-max) can still be Critical; that is a value claim.

## Failure modes observed (do not repeat)

| # | Symptom | Wrong claim | Correct method |
|---|---------|-------------|----------------|
| 1 | Long net split across lines; scanner only read first line | "U26 missing VCC/GND/SDA/SCL" (unpowered) | continuation-aware parse → all 24 pins present |
| 2 | GND pin on a continuation line of a big ground net | "U10.C3 (GND) not connected" | `pin_net` resolves to ground net |
| 3 | Assumed substitute part has external sense resistor | "50mΩ RSENSE missing" (critical) | datasheet: internal sense, no external R |
| 4 | Assumed strap pins = 1/2/3 from memory | "I2C address collision" | trace each strap pin to its net |
| 5 | Decoded address from memory, not netlist | "U8=0x22, U5=0x70" | per-pin net trace → 0x23, 0x74 |
| 6 | Exporter quotes net names inconsistently; rule "record starts with `'`" | "TCA9548A VCC pin shorted to GND" (critical) | delimiter-based parse → `VCC_I2C_MATRIX` is its own 7-pin net |
| 7 | Same root cause, `$PACKAGES` mis-split | "C1/C2/C110 shorted", "R414/R415 shorted", "228 parts have no footprint" | `sanity()` → `nets_without_footprint == []` |
| 8 | Net has far more pins than physically plausible | "ground net misnamed as a VCC rail" | compare pin count against the rail's expected fan-out first |
| 9 | Strap read as a divider midpoint instead of resolved to a logic level | "address is fine because the divider is 0.3V" | resolve 10k-to-3V3 + 1k-to-GND to a level, then decode AD1/AD0 |

**Bottom line:** A connection finding needs a `TelNetlist` or `KicadNetlist` lookup. A PDF or screenshot without that lookup cannot be Critical. A substitute-part finding also needs that part's datasheet, with the section you opened. Anything else is a hypothesis: `warning` with "verify", or drop it.
