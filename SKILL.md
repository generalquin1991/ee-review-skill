---
name: ee-review
description: "Comprehensive Electronics Engineering design review skill. This skill should be used when reviewing hardware designs including schematics (PDF or netlist format), PCB layout files, and BOM documents. Performs deep, professional, multi-dimensional analysis covering power supply design, signal integrity, protection circuits, EMC/EMI, thermal management, DFM/DFT, component lifecycle, and supply chain risk. Generates a structured HTML report with S/A/B/C/D grading, risk-level marking (Critical/Warning/Info), and actionable recommendations. Triggers: review schematic, check PCB design, audit BOM, hardware design review, EE review, 审核原理图, PCB审核, BOM检查, 硬件设计评审."
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
| Netlist / Schematic source | .net, .sch, .kicad_sch, .schdoc, .DSN | Schematic + PCB review |
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

### Step 2: Load Reference Checklists

Based on detected review scope, load the appropriate reference documents:

- **Schematic review**: Read `references/schematic-review.md` and `references/netlist-verification.md` (the latter is mandatory whenever the input includes a netlist — it governs how connection claims must be proven)
- **PCB review**: Read `references/pcb-review.md`
- **BOM review**: Read `references/bom-review.md`
- **Standards reference**: Read `references/standards-reference.md` (always load for cross-referencing)

These reference files contain detailed checklists organized by review dimension. Use them systematically - go through each checklist item and evaluate the design against it.

### Step 3: Execute Review

For each applicable review dimension, systematically evaluate the design:

1. **Parse the input files** - Extract component lists, net connections, design rules, and structural information.
   - **If the input is a netlist (`.tel`, `.net`, `.dsn`, KiCad `.net`) you MUST parse it with `scripts/parse_netlist.py` (the `TelNetlist` class).** This parser is continuation-aware and builds `pin->net` / `net->pins` indexes via reverse lookup. **Do NOT** hand-roll regex that scans lines by prefix — long nets span multiple physical lines and a prefix scan will silently drop continuation pins, producing false "pin missing / device unpowered" findings. See `references/netlist-verification.md` for the mandatory verification discipline and real failure-mode examples.
   - Any claim that a pin is connected, miswired, or **not connected** must be proven by a `TelNetlist` lookup (`pin_net`, `net_pins`, `component_pins`, `missing_pins`). A "device not connected" claim requires `component_pins(ref)` to confirm the pin is absent across the *entire* netlist.
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
- Critical dimensions (Power, Signal Integrity, Protection, Safety): weight 1.5x
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

## Resources

### scripts/
- validate_skill.py - Preflight wrapper for the Codex structural validator. Checks for PyYAML and the local quick_validate.py before running validation, with actionable install guidance when a dependency is missing.
- `parse_netlist.py` - **MANDATORY parser for netlist inputs** (`.tel`/`.net`/`.dsn`/KiCad `.net`). Continuation-aware state machine that correctly handles multi-line nets (a net definition can span many physical lines; only the first begins with `'`/`$`), builds `pin->net` and `net->pins` indexes, and exposes reverse-lookup + verification helpers: `pin_net(ref,pin)`, `net_pins(net)`, `component_pins(ref)`, `is_connected`, `missing_pins(ref,expected)`, `verify_by_pinmap(ref,pinmap)`. CLI: `--comp`, `--pins`, `--net`, `--verify`. Use this INSTEAD of any ad-hoc line-prefix regex — see `references/netlist-verification.md`.
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
3. Load `references/pcb-review.md`, `references/bom-review.md`, `references/standards-reference.md`
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
3. Load `references/schematic-review.md`, `references/bom-review.md`, `references/standards-reference.md`
4. Parse schematic PDF - extract component list, power rails, signal connections, protection circuits
5. Parse BOM CSV - extract part numbers, quantities, descriptions
6. Apply schematic checklist (5 dimensions)
7. Apply BOM checklist (6 dimensions)
8. Cross-reference findings with standards
9. Score each dimension (S/A/B/C/D)
10. Calculate overall grade
11. Assemble JSON, run `generate_report.py`
12. Present HTML report to user
