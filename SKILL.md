---
name: ee-review
description: "Use for hardware design file reviews whenever the user asks to review, audit, or check an electronic design. Covers schematics, netlists, and BOMs, including PADS ASCII .asc netlist exports, PADS/TARGET .tel/.net/.dsn netlists, KiCad/Altium sources, and schematic PDFs. Does not review PCB layout, Gerbers, or board geometry. Reviews power, signal integrity, protection, safety, EMC, thermal, DFM, low-power, firmware-hardware co-verification, and sourcing. Missing evidence stays not verifiable; connectivity claims require parser-backed evidence."
---

# EE Review

Evidence-based schematic / netlist / BOM review. Output: HTML report; optional PPT when asked.

**PCB layout review is out of scope.** Do not grade `.kicad_pcb`, Gerbers, or board geometry. See `references/pcb-review.md`.

Details live under `references/`. Read those files when a step applies; do not invent a parallel checklist in chat.

## When to use

Activate for schematic, netlist, or BOM review / audit / check (审核 / 评审 / 检查). Do not open a layout-review path for board or Gerber files.

## Validation (maintainers only)

```bash
.venv/bin/python scripts/validate_skill.py
```

PyYAML is required **only** for this structural check. Everyday reviews use stdlib scripts and do **not** need PyYAML. See README.

## Workflow

### 1. Classify inputs

| Input | Scope |
| --- | --- |
| Schematic PDF / KiCad / Altium / other schematic source | Schematic review |
| Netlist: KiCad XML, TARGET `.tel`/`.net`/`.dsn`, PADS/EasyEDA `*PART*`/`*NET*`/`*SIGNAL*` `.asc` | Electrical / connectivity (format-specific parser) |
| BOM CSV/XLSX/PDF | BOM review |
| `.kicad_pcb`, Gerber, layout `.asc` with routes, `.PcbDoc` board, etc. | **Out of scope** — say so; do not convert for findings |

Content beats extension. A `*SIGNAL*` `.asc` is a netlist; a `*ROUTE*` `.asc` is layout and out of scope.

Do **not** run `scripts/convert_layout.py` or the PADS layout injectors as part of this review. They are **legacy / not part of review**.

### 2. Contract + checklists

Always read `references/review-contract.md` (six fields, `not verifiable`, connectivity gate, distributor rule, grade cap).

Then load only what applies:

| Need | File |
| --- | --- |
| Schematic rows | `references/schematic-review.md` |
| Any netlist / pin claim | `references/netlist-verification.md` |
| Altium `.PrjPcb` / `.SchDoc` | `references/altium-monkey.md` |
| BOM / SKU | `references/bom-review.md` |
| Coverage gate / feature triggers | `references/conditional-review.md` |
| Block / power diagrams | `references/architecture-diagrams.md` |
| PPT | `references/ppt-style.md` |
| Standards citations | `references/standards-reference.md` |
| Export help | `references/file-preparation-guide.md` |

Apply matching rows. Unprovable → `not verifiable`. Forbidden filler: "checked" / "已检查".

Coverage, ESD, battery, USB-C, antenna, motor, CERE, E96, MCU minimum system, IO levels, charger/power-path, I2C map, clock rework footprints, termination, footprint pin-name check, and BOM SKU rules are defined in `conditional-review.md` and the schematic/BOM refs — execute them there, not from memory.

### 3. Diagrams

Rules: `references/architecture-diagrams.md` + review-contract architecture section.

- Multi-board → system block diagram required.
- Battery → power tree required; source-sag still applies without a battery.
- Single-board → draw when topology would change a finding; ask before skipping.
- Write under `<project>/ee-review/`. Datasheets cited by findings → `ee-review/datasheets/`.

### 4. Execute review

Parse with the real format parser — never hand-rolled line-prefix regex for connectivity:

| Source | Parser |
| --- | --- |
| KiCad | `kicad-cli sch export netlist --format kicadxml` → `scripts/parse_kicad_netlist.py` |
| TARGET/PADS text | `scripts/parse_netlist.py` (`TelNetlist`) |
| PADS/EasyEDA ASCII netlist | `scripts/parse_pads_ascii_netlist.py` (+ `sanity()`) |
| Altium project | `altium-monkey` compile path in `references/altium-monkey.md` |

Critical connectivity requires a successful canonical lookup quoted in the finding. PDF-only / unsupported source → at most `major`. IC supply/return audit: every VDD/GND-class pin from that part's datasheet, traced to a valid DC source/return — presence on a capacitor-only net is not ground.

Score and grade with the single policy in `references/review-contract.md` (same cap as `scripts/generate_report.py`).

### 5. Report and optional PPT

Assemble JSON → `python3 scripts/generate_report.py <review.json> ee-review/<report.html>`.

Field shapes: follow `examples/acceptance-demo/ee-review/review.json` and the script's expectations. Include the coverage table from the conditional gate.

When the user asks for a deck, read `references/ppt-style.md` and use **only**:

```bash
python3 scripts/crop_schematic.py ...
python3 scripts/generate_pptx.py ee-review/deck.json -o ee-review/<code>_design_review_<YYYYMMDD>.pptx
```

Confirm cover `designer` / `reviewer` (and show `project_code`, `review_date`) before writing the PPT unless the current request already named them.

**Figure ↔ sentence:** every part, net, value, threshold, or absence named in the body must be visible in that finding's crop(s), or the crop must show the claimed absence. If the picture contradicts the sentence, rewrite the sentence or recrop before shipping the slide. Details: `references/ppt-style.md` and `references/review-contract.md`.

## Severity

| Level | Meaning |
| --- | --- |
| critical | Will fail or unsafe / reliability break — must fix |
| major | Elevated risk — strongly fix |
| minor | Optional improvement |
| okay | Evidence supports accept |

PPT subtitle colors: critical red, major yellow, minor black, okay green — do not write those words in the sentence.

## Dimensions (index)

Schematic: Power, SI, Protection, Logic, DRC, Low-Power, Safety, DFM/DFT, Firmware-HW — see `schematic-review.md`.  
BOM: availability, second source, SKU standardization, MPN, parameters, package, cost — see `bom-review.md`.  
PCB layout dimension: never.

## Commands (review path)

| Script | Role |
| --- | --- |
| `parse_kicad_netlist.py` / `parse_netlist.py` / `parse_pads_ascii_netlist.py` | Mandatory connectivity parsers |
| `reconstruct_bom_from_pads_ascii.py` | Review-only BOM from PADS attributes |
| `generate_report.py` | HTML report |
| `crop_schematic.py` / `generate_pptx.py` | PPT figures and deck |
| `validate_skill.py` | Maintainer skill structure check (needs PyYAML + Codex validator) |

**Legacy / not part of review:** `convert_layout.py`, `pads_full_converter.py`, `pads_route_injector.py`, `pads_common.py`, `pads_export_all.bas`, `pads_export.bat`. Do not run them to produce review findings.

## Examples

**Layout-only:** classify out of scope → tell the user → ask for schematic/netlist/BOM → do not convert.

**Schematic PDF + BOM:** PDF connectivity ≤ major; BOM stock/lifecycle `not verifiable` without fetched/dated evidence; score with the contract cap; emit HTML.
