---
name: ee-review
description: "Comprehensive Electronics Engineering design review skill. This skill should be used when reviewing hardware designs including schematics (PDF or netlist format), PCB layout files, and BOM documents. Performs deep, professional, multi-dimensional analysis covering power supply design, signal integrity, protection circuits, electrical safety, EMC/EMI, thermal management, DFM/DFT, low-power design, firmware-hardware co-verification, component lifecycle, and supply chain risk. Generates a structured HTML report with S/A/B/C/D grading, risk-level marking (Critical/Warning/Info), and actionable recommendations. Triggers: review schematic, check PCB design, audit BOM, hardware design review, EE review, 审核原理图, PCB审核, BOM检查, 硬件设计评审."
agent_created: true
---

# EE Review - Electronics Engineering Design Review

## Overview

Perform comprehensive, professional, and in-depth review of hardware design artifacts including schematics (PDF or netlist), PCB layout files, and BOM documents. Produce a structured HTML report with hierarchical review dimensions, S/A/B/C/D grading, risk-level marking, and actionable recommendations.

## Skill Validation Preflight

When validating or packaging this skill, run the bundled wrapper before the system validator:

    python3 scripts/validate_skill.py

The wrapper checks that PyYAML is installed before invoking Codex's quick_validate.py. If it is missing, validation stops with an install command and a non-zero exit code; do not report the skill as validated. Install the validation-only dependency with either python3 -m pip install PyYAML or python3 -m pip install -r requirements-validation.txt.

PyYAML is required for skill structure validation only. Normal EE design reviews use the standard-library scripts in this folder and do not require PyYAML.

## When to Use This Skill

Activate this skill when the user requests any of the following:
- Schematic review (原理图审核) - PDF schematics, netlist files, design files
- PCB design review (PCB审核) - Gerber files, layout files, design rule output
- BOM audit (BOM审核) - Bill of materials in CSV/XLSX/PDF format
- Full hardware design review (硬件设计评审) - combination of above
- Keywords: "review", "audit", "check", "审核", "评审", "检查" combined with "schematic", "PCB", "BOM", "原理图", "电路板", "物料清单"

## Review Workflow

### Step 1: Input Classification

Analyze the provided files to determine the review scope:

| Input File Type | Detected Extension | Review Scope |
|----------------|-------------------|-------------|
| Schematic PDF | .pdf (containing circuit diagrams) | Schematic review |
| Schematic source (KiCad / Altium / others) | .kicad_sch, .sch, .schdoc | Schematic review — export a netlist first (KiCad: `kicad-cli sch export netlist --format kicadxml`; Altium: File ▸ Export ▸ Netlist), then parse it. |
| Netlist (KiCad XML / TARGET / PADS) | .xml (kicadxml), .tel, .net, .dsn | Schematic + PCB review — parse with `scripts/parse_kicad_netlist.py` (KiCad `.xml`) or `scripts/parse_netlist.py` (TARGET `.tel`/`.net`/`.dsn`). |
| KiCad PCB | .kicad_pcb | PCB design review (native, no conversion) |
| Altium PCB | .PcbDoc, .pcbdoc | PCB design review (auto-convert via kicad-cli) |
| PADS ASCII | .asc | PCB design review (auto-convert via kicad-cli) |
| Eagle PCB | .brd | PCB design review (auto-convert via kicad-cli) |
| Cadstar PCB | .pcb (CADSTAR content) | PCB design review (auto-convert via kicad-cli) |
| Gerber set | .gbr, .gerber, .gbl, .gtl, etc. | PCB design review (visual/geometric only) |
| BOM | .csv, .xlsx, .xls, .pdf (containing BOM table) | BOM review |
| Multiple files | Combination | Combined review (all applicable dimensions) |

To classify input:
1. Check file extension and content.
2. If PDF, scan for schematic symbols, net labels, component values, or BOM tables.
3. If ambiguous, ask the user to clarify the file type.
4. Determine which review dimensions apply based on detected file types.

### Step 1.5: Layout File Conversion (if needed)

If a PCB layout file is in a non-KiCad format (Altium .PcbDoc, PADS .asc, Eagle .brd, Cadstar .pcb), convert it before review:

**Option A — Automated conversion:**
```bash
python3 scripts/convert_layout.py <input_file> --output-dir ./converted_output --export-all
```
This script auto-detects the format and uses `kicad-cli pcb import` for board files or `kicad-cli sch import` for supported schematic files. PCB inputs can then export Gerber, drill, pick-place, and IPC-D-356 netlist files.

**Prerequisites:**
- KiCad 8+ or 10.0+ must be installed (provides `kicad-cli`)
- macOS: `brew install --cask kicad`
- Ubuntu: `sudo apt install kicad`
- Windows: Download from [kicad.org](https://www.kicad.org/download/)

**Option B — Manual Gerber export:**
If kicad-cli is not available or conversion fails, ask the user to export manufacturing files from their EDA tool. Refer to `references/file-preparation-guide.md` for tool-specific export instructions (Altium Designer, PADS, Eagle, Cadstar, OrCAD/Allegro).

**Special note for PADS users:** PADS binary `.pcb` files cannot be directly converted. The user must export to ASCII `.asc` format first: `File -> Export -> ASCII` (select all sections). This is the only manual step required.

For boards where the KiCad importer drops PADS routing or board graphics, run the full converter after the initial import:

```bash
python3 scripts/pads_full_converter.py board.asc imported.kicad_pcb reviewed.kicad_pcb
```

Both PADS converters fit coordinates against matching reference designators and stop when the maximum fit error exceeds `0.01 mm`. If the source/import alignment has been independently verified, the limit can be changed explicitly with `--max-transform-error <mm>`; record that decision in the review notes.

After conversion, use the `.kicad_pcb` and exported files for the review in subsequent steps.

### Step 1.8: Architecture Diagrams (mandatory, before detailed findings)

Before any checklist findings, produce TWO Graphviz DOT diagrams that fix the design's architecture. These are REQUIRED deliverables for every review (not optional), and the detailed review must cross-check findings against them. See `references/architecture-diagrams.md` for the full style spec and copy-paste DOT templates.

1. **System block diagram** — `<project>_system_block_diagram.dot`. Top-level functional blocks only, arranged in layers, connected by **net-label edges** (the net/signal name on each edge). NO pins, NO internal circuitry, NO component-level detail — it is a block diagram, not a schematic.
2. **Power tree** — `<project>_power_tree.dot`. Power source -> regulator/PMIC -> output rails -> major loads, each edge/block annotated with rail voltage and typical current. NO schematic-level detail (no decoupling caps, no feedback networks).

Render both to PNG and SVG with Graphviz `dot`:
```bash
dot -Tpng -o <project>_system_block_diagram.png <project>_system_block_diagram.dot
dot -Tsvg -o <project>_system_block_diagram.svg <project>_system_block_diagram.dot
# (repeat for <project>_power_tree)
```

**Placement:** put the `.dot`/`.png`/`.svg` deliverables in the PROJECT directory — the same folder that holds the source schematic/board files. Never in the WorkBuddy workspace or a separate deep subfolder. The coverage table (Step 2.5) must list the generated file paths as evidence.

### Step 2: Load Reference Checklists

Based on detected review scope, load the appropriate reference documents:

- **Schematic review**: Read `references/schematic-review.md` and `references/netlist-verification.md` (the latter is mandatory whenever the input includes a netlist — it governs how connection claims must be proven)
- **PCB review**: Read `references/pcb-review.md`
- **BOM review**: Read `references/bom-review.md`
- **Standards reference**: Read `references/standards-reference.md` (always load for cross-referencing)
- **Architecture diagrams**: Read `references/architecture-diagrams.md` (mandatory for every review — defines the required Graphviz DOT format/style for the system block diagram and power tree that Step 1.8 produces).
- **Mandatory and conditional checks**: Read `references/conditional-review.md` for every review. It defines the evidence gate (system block diagram and power tree), all-case ESD review, and feature-triggered checks for batteries, antennas, USB-C, 4G, motors, and CERE/project power baselines.

These reference files contain detailed checklists organized by review dimension. Use them systematically - go through each checklist item and evaluate the design against it.

### Step 2.5: Mandatory Coverage Gate

Before writing findings, determine whether the design contains a battery,
antenna/RF port, USB-C, 4G/cellular modem, motor/inductive load, or a
project-specific CERE requirement. Apply every matching conditional checklist.
Regardless of detected features, confirm the generated system block diagram and
power tree (the Graphviz DOT deliverables from Step 1.8), the ESD/external-boundary
review, the low-power design review (sleep/standby current, leakage, power-gated
domains, power budget), the EMC/EMI review (radiated/conducted emissions,
immunity, filtering, grounding, clock/DC-DC noise), the electrical-safety review
(creepage/clearance, isolation, battery safety), the thermal-management review
(power-dense/enclosure heat), the DFM/DFT readiness review (test points,
programming/debug access, ICT), the firmware-hardware co-verification review
(HW gated by firmware must have the FW sequence specified), and the project power
baseline. Record each item as `confirmed`,
`finding`, `not applicable` with evidence (for the two diagrams, cite the
`.dot`/`.png` file paths), or `not verifiable` due to missing evidence. The final
report must include the coverage table defined in `references/conditional-review.md`.

### Step 3: Execute Review

For each applicable review dimension, systematically evaluate the design:

1. **Parse the input files** - Extract component lists, net connections, design rules, and structural information.
   - **If the input is a netlist you MUST parse it with a real parser — never hand-roll line-prefix regex.** Route by source format:
     - **KiCad** (`.kicad_sch` / `.sch` / `.schdoc`): export the netlist as XML first — `kicad-cli sch export netlist --format kicadxml -o board.xml <file>.kicad_sch` — then parse with `scripts/parse_kicad_netlist.py` (the `KicadNetlist` class). `KicadNetlist` wraps KiCad's own `kicad_netlist_reader`, so every pin→net fact comes from KiCad's native parser. **Do NOT** feed the default `kicadsexpr` (S-expression) export to either parser — it is not XML and will silently yield 0 nets.
     - **TARGET / PADS-style** (`.tel` / `.net` / `.dsn` with `$NETS`/`$PACKAGES`): parse with `scripts/parse_netlist.py` (the `TelNetlist` class). This parser is continuation-aware and builds `pin->net` / `net->pins` indexes via reverse lookup.
     Long nets span multiple physical lines and a prefix scan will silently drop continuation pins, producing false "pin missing / device unpowered" findings. See `references/netlist-verification.md` for the mandatory verification discipline and real failure-mode examples.
   - Any claim that a pin is connected, miswired, or **not connected** must be proven by a parser lookup — `TelNetlist` for TARGET `.tel`/`.net`/`.dsn`, or `KicadNetlist` for KiCad kicadxml (both expose `pin_net`, `net_pins`, `component_pins`, `missing_pins`). A "device not connected" claim requires `component_pins(ref)` to confirm the pin is absent across the *entire* netlist.
2. **Apply checklist items** - Go through each item in the reference checklist for the detected dimension.
3. **Identify findings** - Record each issue found with:
   - Severity level: `critical`, `warning`, or `info`
   - Title (concise summary)
   - Description (detailed explanation of the issue)
   - Location (sheet number, component reference, coordinate, or BOM line)
   - Recommendation (specific action to fix)
4. **Score the dimension** - Based on findings, assign a grade and score.

### Step 4: Grade and Score

#### Grading System (S/A/B/C/D)

| Grade | Label | Criteria | Color |
|-------|-------|---------|-------|
| S | Excellent | Exceeds industry best practices, zero critical issues, minimal warnings | Purple |
| A | Good | Meets all standards, zero critical issues, few minor warnings | Green |
| B | Acceptable | Meets basic requirements, no critical issues, moderate warnings | Blue |
| C | Needs Improvement | Has critical issues that must be addressed before production | Orange |
| D | Fail | Serious design defects, fundamental rework required | Red |

#### Scoring Guidelines

- Start at 100 points per dimension.
- Deduct per finding:
  - Critical finding: -15 points
  - Warning finding: -5 points
  - Info finding: -1 point
- Map score to grade:
  - 90-100: S
  - 80-89: A
  - 65-79: B
  - 50-64: C
  - < 50: D

#### Overall Grade Calculation

Calculate overall grade as the weighted average across dimensions:
- Critical dimensions (Power, Signal Integrity, Protection, Safety, Low-Power for battery/portable/power-constrained designs): weight 1.5x
- Standard dimensions: weight 1.0x
- If ANY dimension is grade D, overall grade cannot exceed C.
- If ANY dimension has 3+ critical findings, overall grade cannot exceed C.

### Step 5: Generate Report

Generate the final HTML report using the report generation script.

#### 5.1 Prepare JSON Data

Assemble review results into the following JSON structure (save as a temporary `.json` file):

```json
{
    "project_name": "<project or file name>",
    "review_date": "<YYYY-MM-DD>",
    "reviewer": "EE Review Skill",
    "input_files": ["<list of input file paths>"],
    "overall_grade": "<S|A|B|C|D>",
    "overall_summary": "<2-3 sentence overall assessment>",
    "coverage": [
        {
            "check": "<system block diagram|power tree|ESD|battery|antenna|USB-C|4G|motor|low-power|emc|safety|thermal|dfm|firmware|CERE>",
            "trigger": "<feature trigger or expected evidence>",
            "status": "<confirmed|finding|not applicable|not verifiable>",
            "evidence": "<file/page, finding location, or reason unavailable>"
        }
    ],
    "dimensions": [
        {
            "name": "<dimension name>",
            "category": "<schematic|pcb|bom|general>",
            "grade": "<S|A|B|C|D>",
            "score": <number>,
            "max_score": 100,
            "findings": [
                {
                    "severity": "<critical|warning|info>",
                    "title": "<finding title>",
                    "description": "<detailed description>",
                    "location": "<sheet, component, or BOM line>",
                    "recommendation": "<actionable fix>"
                }
            ]
        }
    ],
    "summary": {
        "total_findings": <number>,
        "critical_count": <number>,
        "warning_count": <number>,
        "info_count": <number>,
        "top_risks": ["<top risk 1>", "<top risk 2>", "..."],
        "recommendations": ["<recommendation 1>", "<recommendation 2>", "..."]
    }
}

    # -----------------------------------------------------------------------
    # I2C MAP & TOPOLOGY (optional but recommended). generate_report.py's
    # render_i2c_map / render_i2c_topology consume these; if omitted the report
    # simply skips the I2C section. Use one entry per I2C bus segment.
    "i2c_map": {
        "tree": [
            {
                "kind": "controller",        # controller | device
                "label": "ESP32-S3 (master)",
                "ref": "U1",
                "type": "uC",
                "addr": null,                 # null for controllers
                "role": "master",             # master | slave
                "children": [
                    {
                        "kind": "device",
                        "label": "BQ25120A charger",
                        "ref": "U5",
                        "type": "pmic",
                        "addr": "0x6A",
                        "role": "slave",
                        "children": []
                    }
                ]
            }
        ]
    },
    "i2c_topology": {
        "controllers": [
            {
                "id": "I2C0",
                "label": "ESP32-S3 I2C0",
                "pins": "GPIO8/9 (SCL/SDA)",
                "shared": false,              # true if >1 controller drives the same bus
                "nodes": [
                    {"ref": "U5", "addr": "0x6A", "role": "slave"},
                    {"ref": "U6", "addr": "0x48", "role": "slave"}
                ]
            }
        ],
        "pullups": [                          # where are the bus pull-ups?
            {"net": "SCL", "ref": "R22", "to": "3V3"},
            {"net": "SDA", "ref": "R23", "to": "3V3"}
        ]
    }
}
```

#### 5.2 Run Report Generator

Execute the report generation script:

```bash
python3 scripts/generate_report.py <input.json> <output_report.html>
```

The script generates a styled HTML report with:
- Overall grade circle (S/A/B/C/D)
- Summary statistics (total findings, critical/warning/info counts)
- Radar chart showing dimension scores
- Bar chart showing findings distribution
- Top risks and key recommendations sections
- Dimension-by-dimension detail cards with findings list

#### 5.3 Present Report

Return the generated HTML path to the user so it can be opened or previewed by the host environment.

## Review Dimensions

### Schematic Review Dimensions

When schematic files are detected, apply these review dimensions (see `references/schematic-review.md` for detailed checklists):

1. **Power Supply Design** - Power tree, decoupling, regulation, protection, sequencing, margin analysis.
2. **Signal Integrity** - High-speed termination, clock design, bus interfaces, level shifting.
3. **Protection Circuits** - ESD protection, over-voltage/over-current, isolation.
4. **Circuit Logic & Correctness** - Functional verification, feedback loops, timing, component values.
5. **Design Rule Checks** - Netlist consistency, connector pinout, documentation.
6. **Low-Power Design** - Sleep/standby current budget, leakage (floating/unused pins, pull-resistor choice), power-gated domains and off-state isolation, regulator quiescent current / light-load efficiency, always-on domain minimization, RTC/backup domain, ship/storage mode. Mandatory for battery/portable/always-on designs and weighted 1.5x there. See `references/conditional-review.md` (Low-Power Design trigger) and `references/schematic-review.md` §6.
7. **Safety (Electrical)** - Creepage/clearance, isolation barriers, over-voltage/current protection against the accessible-voltage class, and Li-Po battery safety (thermal runaway, over-charge/discharge, short, reverse, ship mode). See `references/schematic-review.md` §8 and `references/conditional-review.md` (Safety trigger).
8. **DFM/DFT** - Test points, programming/debug headers, ICT access, panelization, process margins. See `references/schematic-review.md` §9 and `references/conditional-review.md` (DFM/DFT trigger).
9. **Firmware-HW Co-Verification** - Hardware whose enable/configuration depends on firmware (chargers, load switches, boost, PMIC) must have the firmware sequence specified and cross-checked; "works only after FW runs" is a finding, not an assumption. See `references/schematic-review.md` §10.

For battery designs, Power Supply Design must include temperature protection,
charge/discharge limits, and usable-energy analysis, Low-Power Design must
quantify the sleep/standby budget against the cell capacity, and Electrical
Safety must cover the Li-Po cell's thermal-runaway, over-charge/discharge, short,
reverse-polarity, and ship-mode protection. For 4G and motor designs, Power
Supply Design must include peak/inrush transient stability. For projects naming
CERE or another internal baseline, map the measured design against that
controlled requirement and mark missing evidence explicitly.

### PCB Design Review Dimensions

When PCB layout files are detected, apply these review dimensions (see `references/pcb-review.md` for detailed checklists):

1. **Layer Stackup** - Layer count, material/thickness, reference plane assignment.
2. **Signal Integrity** - Impedance control, length matching, crosstalk, return path.
3. **Power Integrity** - Power distribution, decoupling placement, current capacity.
4. **Thermal Management** - Component placement, copper pour, airflow.
5. **EMC/EMI Design** - Layout partitioning, filtering/shielding, clock routing, grounding.
6. **Footprint & Land Pattern Verification** - Footprint accuracy, IPC-7351 pad design, courtyard spacing, orientation marking, footprint-to-BOM cross-check. Includes solder mask opening verification (NSMD/SMD, via tenting, mask slivers), solder paste aperture verification (paste reduction for fine-pitch, thermal pad patterns, per-pad overrides), and PADS-to-KiCad conversion data loss detection.
7. **DFM/DFT** - Manufacturing rules, testability, assembly considerations.
8. **Routing Quality** - General routing, via design, net-specific routing rules.

For antenna/RF designs, Signal Integrity and EMC/EMI must include the 50-ohm
path, matching network, RF keepout, ground stitching, and tuning evidence. For
USB-C designs, verify both CC pins and role resistors from the netlist and
controller datasheet; do not accept a single generic "USB connector checked"
statement. For battery/portable/always-on designs, Power Integrity and EMC/EMI
must also include low-power implementation: power-gated domain isolation in
layout (no sneak return through a shared ground/pour), minimal always-on copper,
and leakage/light-load behavior of the always-on rail. Cross-reference the
schematic §6 Low-Power Design findings. EMC/EMI is a mandatory coverage check
for every design (radiated/conducted emissions, immunity, filtering, grounding,
clock/DC-DC noise); it must be confirmed even when no explicit EMC target is
named, not treated as optional. Likewise, Thermal Management and DFM/DFT are
mandatory coverage checks (power-dense/enclosure heat and production readiness,
respectively) and must be confirmed for every design.

### BOM Review Dimensions

When BOM files are detected, apply these review dimensions (see `references/bom-review.md` for detailed checklists):

1. **Component Availability & Lifecycle** - Lifecycle status, lead time, stock, distributor availability.
2. **Second Source & Alternatives** - Pin-compatible alternatives, parameter-based substitution, standardization.
3. **Part Number Accuracy** - MPN completeness, description quality, reference designator consistency.
4. **Parameter Verification** - Electrical parameters, environmental ratings, compliance.
5. **Package & Footprint Verification** - Package documentation, footprint-to-package matching, thermal/mechanical, assembly packaging (MSL, tape & reel), package alternatives.
6. **Cost Analysis** - Cost optimization, supply chain risk assessment.

### Standards Cross-Reference

Always reference `references/standards-reference.md` during review to:
- Validate design decisions against applicable industry standards (IPC, IEEE, IEC, CE/FCC, JEDEC, AEC-Q100, USB-IF).
- Identify compliance gaps.
- Provide authoritative citations for findings.

## Findings Severity Definitions

| Severity | Icon | Color | Definition | Action Required |
|----------|------|-------|-----------|----------------|
| Critical | Red circle | #e74c3c | Design will fail or cause reliability/safety issues | Must fix before production |
| Warning | Yellow circle | #f39c12 | Design may work but has elevated risk or non-compliance | Strongly recommend fixing |
| Info | Green circle | #27ae60 | Suggestion for optimization or best practice | Optional improvement |

## Key Review Principles

1. **Be thorough** - Systematically go through every checklist item. Do not skip dimensions even if the design "looks fine."
2. **Be specific** - Each finding must reference exact locations (sheet, component, net, BOM line).
3. **Be actionable** - Every finding must include a concrete recommendation, not just a description of the problem.
4. **Cross-reference standards** - When flagging an issue, cite the relevant standard (e.g., "Per IPC-2221 Table 6-1, minimum conductor spacing for 30V is 0.1mm").
5. **Prioritize by risk** - Always highlight critical findings first in the summary and top risks section.
6. **Maintain objectivity** - Base findings on technical facts and standards, not opinion. If uncertain, mark as "Warning" with a note to verify.
7. **Verify, don't assume** - Every connection-related finding MUST be backed by a `TelNetlist` lookup (`references/netlist-verification.md`). Specifically: (a) parse netlists ONLY with `scripts/parse_netlist.py`, never line-prefix regex; (b) for substitute parts, verify the **substitute's** datasheet pinout/features before asserting a defect carried over from the PRD part's assumptions (e.g. internal vs external current sense); (c) derive I2C addresses by tracing each strap pin to its net, never by assuming strap-pin numbers or addresses from memory. If a finding is not backed by a netlist lookup and, where relevant, a datasheet check, it is a hypothesis — mark it `warning`/"verify" or drop it; never ship it as `critical`.
8. **Close the coverage loop** - Every final report must include the system block diagram and power tree as generated Graphviz DOT deliverables (Step 1.8), ESD, CERE/project baseline, and all triggered feature checks, including explicit not-applicable or not-verifiable statuses. The coverage table must cite the diagram file paths.

## Resources

### scripts/
- validate_skill.py - Preflight wrapper for the Codex structural validator. Checks for PyYAML and the local quick_validate.py before running validation, with actionable install guidance when a dependency is missing.
- `parse_netlist.py` - **MANDATORY parser for netlist inputs** (`.tel`/`.net`/`.dsn` — TARGET/PADS text format). Continuation-aware state machine that correctly handles multi-line nets (a net definition can span many physical lines; only the first begins with `'`/`$`), builds `pin->net` and `net->pins` indexes, and exposes reverse-lookup + verification helpers: `pin_net(ref,pin)`, `net_pins(net)`, `component_pins(ref)`, `is_connected`, `missing_pins(ref,expected)`, `verify_by_pinmap(ref,pinmap)`. CLI: `--comp`, `--pins`, `--net`, `--verify`. Use this INSTEAD of any ad-hoc line-prefix regex — see `references/netlist-verification.md`.
- `parse_kicad_netlist.py` - **MANDATORY parser for KiCad schematic inputs** (`.kicad_sch`/`.sch`/`.schdoc`). Wraps KiCad's own `kicad_netlist_reader` (the official, native netlist parser shipped with every KiCad install) and exposes the SAME interface as `TelNetlist` (`pin_net`, `net_pins`, `component_pins`, `is_connected`, `missing_pins`, `verify_by_pinmap`, plus `lib_pins`). Requires the netlist be exported as XML first: `kicad-cli sch export netlist --format kicadxml -o board.xml <file>.kicad_sch`. The default `kicadsexpr` (S-expression) export is NOT XML and will silently yield 0 nets — do not feed it to either parser. CLI: `--comp`, `--pins`, `--net`, `--verify`. See `references/netlist-verification.md` (Rule 0).
- `generate_report.py` - Python script that converts structured JSON review data into a styled HTML report with radar chart, bar chart, score cards, and findings list. Execute this after assembling review results into JSON format.
- `convert_layout.py` - Auto-detects PCB layout file format (Altium .PcbDoc, PADS .asc, Eagle .brd, Cadstar .pcb, KiCad .kicad_pcb) and converts to KiCad format using kicad-cli. Optionally exports Gerber, drill, pick-place, and netlist files. Includes post-conversion audit that checks for routing trace loss, solder mask/paste settings, via tenting, silk screen completeness, board outline, and copper zones. Requires KiCad 8+ installed.
- `pads_common.py` - Shared PADS ASCII decoding, header/via/part/route parsing, and transform-error policy used by both converters. It tries UTF-8, CP936, CP1252, and Latin-1 in a deterministic order and records the selected encoding.
- `pads_route_injector.py` - Parses PADS ASCII *ROUTE* section and injects KiCad segments and vias into converted .kicad_pcb file. Computes coordinate transformation (scale=2/3, Y-flip) by matching PADS PART positions with KiCad footprint positions, then enforces the fit-error threshold. Usage: `python3 pads_route_injector.py <input.asc> <input.kicad_pcb> <output.kicad_pcb> [--max-transform-error <mm>]`
- `pads_full_converter.py` - Comprehensive PADS→KiCad converter that extends route injection with: (1) board outline injection from PADS BOARD items → Edge.Cuts, (2) silk screen text from *TEXT* → F.SilkS, (3) documentation lines from *LINES* → F.Fab, (4) copper zone creation on B.Cu using board outline + thermal connection analysis, (5) per-pad solder_paste_margin and solder_mask_margin injection from PARTDECAL pad stacks. Parses PARTDECAL pad stack levels (-2=paste, -1=mask, 0=copper) and computes margins using PADS ARPTOM global annular ring. Usage: `python3 pads_full_converter.py <input.asc> <input.kicad_pcb> <output.kicad_pcb> [--max-transform-error <mm>]`
- `conversion-manifest.json` - Written beside converted outputs. Records source format, absolute input/output paths, requested export status, and post-conversion audit findings so a review can distinguish a successful conversion from a partially exported one.
- `pads_export_all.bas` - VBScript for PADS Layout that exports ASCII, IPC-356 netlist, BOM, placement, layer stackup, and design rules in one run. Run inside PADS via `Tools -> Basic Scripts` or from command line with `layout.exe /runscript`.
- `pads_export.bat` - Windows batch file that launches PADS Layout with a PCB file and auto-runs the export script. Designed for VM automation.

### Known PADS-to-KiCad Conversion Limitations

When converting PADS ASCII files via kicad-cli, the following data is NOT converted. Use `pads_full_converter.py` to inject the missing data:

| Data Type | PADS Source | kicad-cli Output | Impact | Mitigation |
|-----------|-------------|------------------|--------|------------|
| Routing traces | *ROUTE* section | 0 segments | Cannot review trace width, spacing, return path | ✅ `pads_full_converter.py` injects segments |
| Vias | *VIA* section + route layer changes | 0 vias | Cannot review via design, tenting | ✅ `pads_full_converter.py` injects vias |
| Per-layer pad sizes | PARTDECAL pad stack (levels -2/-1/0) | Single size for all layers | Paste reduction lost, mask expansion lost | ✅ `pads_full_converter.py` injects margins |
| Solder mask margin | PCB GENERAL + per-pad | NOT SET | Uses KiCad default (~0.051mm) | ✅ `pads_full_converter.py` injects from ARPTOM |
| Solder paste margin | PARTDECAL paste level | NOT SET | Paste = copper (no reduction) | ✅ `pads_full_converter.py` injects from pad stack |
| Board-level silk text | *TEXT* section | 0 gr_text | Board name, date, logos missing | ✅ `pads_full_converter.py` injects gr_text |
| Copper zones/pours | *PLANE* / *COPPER* | 0 zones | No ground/power pour | ✅ `pads_full_converter.py` creates zone from board outline |
| Board outline | *LINES* BOARD items | Partial Edge.Cuts | Board shape may be incomplete | ✅ `pads_full_converter.py` injects full outline |
| Documentation lines | *LINES* items (LEVEL 127) | 0 lines | Assembly drawings incomplete | ✅ `pads_full_converter.py` injects on F.Fab |
| Split planes | Multiple nets on same plane layer | Single zone per layer | Multiple nets need separate zones | ⚠️ Manual: create additional zones in KiCad |
| Via tenting | Per-via mask settings | Default tented | May not match PADS | ⚠️ Manual: adjust via layers in KiCad |

### references/
- `schematic-review.md` - Detailed schematic review checklist covering 5 dimensions with sub-items, margin tables, and common issues reference.
- `netlist-verification.md` - **MANDATORY discipline for netlist/schematic reviews.** Why ad-hoc line-prefix parsing fails (misses continuation lines of long nets), how to use `scripts/parse_netlist.py` for reverse-lookup proof, and the 5 failure modes observed on a real review (false "device unpowered", false "RSENSE missing" from substitute-part assumption, false I2C-address claims from assumed strap pins). Read this before asserting any connection-related finding.
- `pcb-review.md` - Detailed PCB design review checklist covering 8 dimensions including footprint/land pattern verification, with sub-items, current capacity tables, and routing rules.
- `bom-review.md` - Detailed BOM review checklist covering 6 dimensions including package & footprint verification, with lifecycle status reference and cost risk assessment.
- `standards-reference.md` - Quick reference guide to IPC, IEEE, IEC, CE/FCC, JEDEC, AEC-Q100, and USB-IF standards with application guidance.
- `conditional-review.md` - Mandatory evidence gate and feature-triggered review matrix for ESD, electrical safety, battery thermal/energy protection, antenna matching, USB-C CC, 4G burst power, motor transients, low-power design, EMC/EMI, thermal management, DFM/DFT, firmware-hardware co-verification, and CERE/project power baselines.
- `architecture-diagrams.md` - **MANDATORY format spec for the system block diagram and power tree** produced in Step 1.8. Defines the required Graphviz DOT style (layered functional blocks + net-label edges, no internal detail) and gives copy-paste DOT templates for both diagrams plus rendering commands.
- `file-preparation-guide.md` - Step-by-step export instructions for Altium Designer, PADS, KiCad, Eagle, Cadstar, and OrCAD/Allegro. Includes troubleshooting and expected output file structures.

### assets/
No assets required. The HTML report is generated dynamically by the script.

## Example Usage

**Example 1: Review Altium .PcbDoc + BOM**

**User input**: "Review this Altium PCB and BOM file"
**Detected files**: `board.PcbDoc`, `bom.csv`
**Review scope**: PCB + BOM (combined)
**Workflow**:
1. Classify files - .PcbDoc = Altium PCB, CSV = BOM
2. Convert PCB: `python3 scripts/convert_layout.py board.PcbDoc --output-dir ./output --export-all`
   - Output: `output/board.kicad_pcb`, `output/gerber/`, `output/drill/`, `output/netlist.net`
3. Load `references/pcb-review.md`, `references/bom-review.md`, `references/standards-reference.md`, `references/conditional-review.md`, and `references/architecture-diagrams.md`
4. Parse converted .kicad_pcb - extract layer stackup, tracks, vias, component footprints, copper zones
5. Parse BOM CSV - extract part numbers, quantities, descriptions
6. Apply PCB checklist (8 dimensions including footprint verification)
7. Apply BOM checklist (6 dimensions including package verification)
8. Cross-reference findings with standards
9. Score each dimension (S/A/B/C/D)
10. Calculate overall grade
11. Assemble JSON, run `generate_report.py`
12. Present HTML report to user

**Example 2: Review schematic PDF + BOM**

**User input**: "Review this schematic PDF and BOM file"
**Detected files**: `schematic.pdf`, `bom.csv`
**Review scope**: Schematic + BOM (combined)
**Workflow**:
1. Classify files - PDF = schematic, CSV = BOM
2. No conversion needed (PDF and CSV are directly reviewable)
3. Load `references/schematic-review.md`, `references/bom-review.md`, `references/standards-reference.md`, `references/conditional-review.md`, and `references/architecture-diagrams.md`
4. Parse schematic PDF - extract component list, power rails, signal connections, protection circuits
5. Parse BOM CSV - extract part numbers, quantities, descriptions
6. Apply schematic checklist (5 dimensions)
7. Apply BOM checklist (6 dimensions)
8. Cross-reference findings with standards
9. Score each dimension (S/A/B/C/D)
10. Calculate overall grade
11. Assemble JSON, run `generate_report.py`
12. Present HTML report to user
