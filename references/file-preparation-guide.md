# File Preparation Guide - EDA Tool Export Instructions

This guide provides step-by-step instructions for exporting design files from each major EDA tool so they can be processed by the EE Review skill.

---

## Quick Reference Table

| EDA Tool | Best Export Format | Conversion Needed | One-Line Command |
|----------|-------------------|-------------------|-----------------|
| KiCad | `.kicad_pcb` | None | Direct use |
| Altium Designer | `.PcbDoc` | `kicad-cli pcb import --format altium` | Automatic |
| PADS | `.asc` (ASCII) | `kicad-cli pcb import --format pads` | Manual export step needed |
| Eagle | `.brd` | `kicad-cli pcb import --format eagle` | Automatic |
| Cadstar | `.pcb` | `kicad-cli pcb import --format cadstar` | Automatic |
| OrCAD/Allegro | Gerber + netlist | Manual export | See Allegro section |
| KiCad (target) | `.kicad_pcb` | - | - |

---

## 1. KiCad (Native Format - No Conversion Needed)

KiCad `.kicad_pcb` files are natively supported. No conversion is required.

### What to provide:
- `board.kicad_pcb` - The PCB layout file
- `board.kicad_sch` - The schematic file (if available)
- `board.kicad_pro` - The project file (optional)

### Exporting Gerber from KiCad (for reference):
```bash
# Command line
kicad-cli pcb export gerber -o gerber_out/ board.kicad_pcb
kicad-cli pcb export drill -o drill_out/ board.kicad_pcb
kicad-cli pcb export pos -o positions.csv board.kicad_pcb
kicad-cli pcb export ipcd356 -o netlist.ipc356 board.kicad_pcb
```

Or via GUI: `File -> Fabrication Outputs -> Gerbers / Drill Files / Component Positions`

---

## 2. Altium Designer

Altium `.PcbDoc` files can be directly converted by `kicad-cli`.

### Option A: Direct .PcbDoc (Recommended)

Provide the `.PcbDoc` file directly. The conversion script handles it:

```bash
python3 scripts/convert_layout.py board.PcbDoc --output-dir ./output --export-all
```

Behind the scenes:
```bash
kicad-cli pcb import --format altium board.PcbDoc -o board.kicad_pcb
kicad-cli pcb export gerber -o gerber/ board.kicad_pcb
kicad-cli pcb export drill -o drill/ board.kicad_pcb
kicad-cli pcb export pos -o positions.csv board.kicad_pcb
kicad-cli pcb export ipcd356 -o netlist.ipc356 board.kicad_pcb
```

### Option B: Export Gerber Set (Manual)

If kicad-cli conversion has issues with complex designs, export manually:

1. **Gerber**: `File -> Fabrication Outputs -> Gerber Files`
   - Set format: RS-274X, 4:4 (metric/mm)
   - Select all layers
   - Output: `gerber/` directory

2. **Drill**: `File -> Fabrication Outputs -> NC Drill Files`
   - Units: mm, Format: 4:4
   - Output: `gerber/` directory

3. **Pick & Place**: `File -> Assembly Outputs -> Generates Pick and Place Files`
   - Format: CSV, Metric
   - Output: `pickplace.csv`

4. **Netlist**: `File -> Export -> Netlist`
   - Format: Protel netlist
   - Output: `netlist.net`

5. **Smart PDF** (optional but useful for visual review):
   `File -> Smart PDF -> Current Workspace -> All layers`

### Altium file package:
```
project_name/
├── board.PcbDoc          # Main PCB layout (preferred)
├── schematic.SchDoc      # Schematic (if reviewing schematic)
├── gerber/               # Or manually exported Gerber set
│   ├── *.gbl             # Bottom layer
│   ├── *.gtl             # Top layer
│   ├── *.gbo             # Bottom overlay
│   ├── *.gto             # Top overlay
│   ├── *.gbs             # Bottom solder mask
│   ├── *.gts             # Top solder mask
│   ├── *.gbp             # Bottom paste
│   ├── *.gtp             # Top paste
│   ├── *.gm1             # Mechanical 1 (board outline)
│   ├── *.gko             # Keep-out
│   └── *.drl             # Drill data
├── pickplace.csv         # Pick and place
├── netlist.net           # Netlist
└── layout.pdf            # Smart PDF (optional)
```

---

## 3. PADS (Siemens/Mentor)

PADS uses a closed binary `.pcb` format that cannot be directly parsed. You must export to ASCII `.asc` format first.

### PADS Automation Overview

| Method | How | Requires PADS Running? | Full Automation? |
|--------|-----|----------------------|-----------------|
| **VBScript (in-process)** | Run .bas script inside PADS via `Tools -> Basic Scripts` | Yes (runs inside PADS) | Yes - one-click export |
| **Command-line launch** | `layout.exe /runscript script.bas` | No (launches PADS) | Yes - batch automation |
| **External COM** | `CreateObject(...)` from Python/C# | No | **Not supported** - PADS does not expose an external COM server |

> **Important**: Unlike Altium Designer (which has `CreateObject("Altium.Application")`), PADS does NOT expose an external COM automation server. PADS scripting runs **in-process** — the VBScript executes inside the PADS process and has access to the `Application` and `ActiveDocument` objects. You cannot control PADS from an external Python script via COM.

### Option A: Automated Export (Recommended)

The skill includes a ready-to-use VBScript that exports everything needed:

**Method 1 — Batch file (fully automated):**
```bat
REM Run in the VM where PADS is installed
pads_export.bat "D:\Projects\MyBoard\board.pcb"
```
This launches PADS, opens the PCB file, runs the export script, and generates all files.

**Method 2 — Inside PADS GUI:**
1. Copy `pads_export_all.bas` to the PADS scripts directory (or any accessible folder)
2. Open your PCB file in PADS Layout
3. `Tools -> Basic Scripts -> Basic Scripts...`
4. Browse to `pads_export_all.bas` and click `Run`

**Method 3 — Command line:**
```bat
"C:\MentorGraphics\PADSVX.2.2\SDD_HOME\Programs\layout.exe" "D:\board.pcb" /runscript "C:\scripts\pads_export_all.bas"
```

The script automatically exports:
- ASCII file (`.asc`) — for kicad-cli conversion
- IPC-356 netlist (`.ipc`) — for net connection verification
- BOM + Pick&Place (`.csv`) — for BOM review
- Placement data (`.csv`) — for component coordinate verification
- Layer stackup info (`.txt`) — for stackup review
- Design rules report (`.rpt`) — for DRC review
- Export log (`.txt`) — for audit trail

All files are saved to `<project_dir>/EE_Review_Export/`.

### Option B: Manual Export Step-by-Step

If you prefer to export manually:

### Step 1: Export ASCII from PADS (Manual - required)

In PADS Layout:
1. `File -> Export -> ASCII...`
2. Select output file: `board.asc`
3. In the Export dialog, check ALL sections:
   - [x] Parts
   - [x] Nets
   - [x] Routes
   - [x] Vias
   - [x] Layer Stackup
   - [x] Component Placement
   - [x] Attributes
   - [x] Rules
   - [x] Lines (drawing items)
4. Set Units: Mils or mm (be consistent)
5. Click OK

### Step 2: Convert to KiCad

```bash
python3 scripts/convert_layout.py board.asc --output-dir ./output --export-all
```

### Step 3: Export Gerber from PADS (Alternative)

If you prefer to export manufacturing files directly from PADS:

1. **Gerber**: `File -> Export -> Gerber`
   - Select all layers
   - Format: RS-274X

2. **Drill**: `File -> Export -> DXF/IPC-D-356`
   - Output: `drill.dxf` or `drill.d356`

3. **Placement**: `File -> Export -> Placement`
   - Output: `placement.txt`

4. **Netlist**: `File -> Export -> Netlist`
   - Format: PADS netlist or Spice
   - Output: `netlist.net`

### PADS file package:
```
project_name/
├── board.asc             # PADS ASCII export (REQUIRED for auto-conversion)
├── board.pcb             # Original PADS binary (for reference only)
├── gerber/               # Or manually exported Gerber set
├── drill.d356            # IPC-D-356 drill data
├── placement.txt          # Placement data
└── netlist.net           # Netlist
```

> **Note**: The PADS binary `.pcb` file cannot be processed by open-source tools. The ASCII `.asc` export is mandatory for automated conversion. This is a one-time manual step.

---

## 4. Eagle (Autodesk)

Eagle `.brd` files are XML-based and can be directly imported by kicad-cli.

### Direct conversion:
```bash
python3 scripts/convert_layout.py board.brd --output-dir ./output --export-all
```

### Manual Gerber export from Eagle:
1. `File -> CAM Processor`
2. Load job: `gerb274x-4layer.cam` (or create custom)
3. Process all sections
4. Output to `gerber/` directory

### Eagle file package:
```
project_name/
├── board.brd             # Eagle board (preferred)
├── schematic.sch         # Eagle schematic
└── gerber/               # Or manually exported
```

---

## 5. Cadstar

Cadstar `.pcb` files can be imported by kicad-cli.

### Direct conversion:
```bash
python3 scripts/convert_layout.py board.pcb --output-dir ./output --export-all
```

### Manual export from Cadstar:
1. `Output -> Manufacturing Outputs -> Gerber`
2. `Output -> Manufacturing Outputs -> NC Drill`
3. `Output -> Reports -> Netlist Report`

### Cadstar file package:
```
project_name/
├── board.pcb             # Cadstar PCB (preferred)
├── schematic.sch        # Cadstar schematic
└── gerber/              # Or manually exported
```

---

## 6. OrCAD / Allegro (Cadence)

OrCAD/Allegro uses proprietary binary formats that are not directly supported by kicad-cli. Manual export is required.

### Export steps in Allegro PCB Editor:

1. **Gerber**: `Manufacture -> Artwork`
   - Set film parameters for each layer
   - Output: `artwork/` directory

2. **Drill**: `Manufacture -> NC -> Drill`
   - Parameters: mm, ASCII
   - Output: `drill.txt`

3. **Netlist**: `File -> Export -> Logic`
   - Type: Allegro
   - Output: `netlist.dat`

4. **Placement**: `File -> Export -> Placement`
   - Output: `placement.txt`

### Alternative: Export to ODB++
If your Allegro version supports ODB++:
1. `File -> Export -> ODB++`
2. This creates a structured directory with all design data

### Allegro file package:
```
project_name/
├── artwork/              # Gerber files
│   ├── top.art
│   ├── bottom.art
│   ├── solder_top.art
│   ├── solder_bottom.art
│   └── ...
├── drill.txt             # Drill data
├── netlist.dat           # Netlist
├── placement.txt         # Placement
└── board.brd             # Original Allegro file (for reference)
```

---

## 7. Using the Conversion Script

### Prerequisites

Install KiCad (which includes kicad-cli):

| Platform | Command |
|----------|---------|
| macOS | `brew install --cask kicad` |
| Ubuntu/Debian | `sudo apt install kicad` |
| Windows | Download from [kicad.org](https://www.kicad.org/download/) |

### Basic Usage

```bash
# Convert Altium .PcbDoc to KiCad + export everything
python3 scripts/convert_layout.py board.PcbDoc --export-all

# Convert PADS .asc to KiCad + export Gerber only
python3 scripts/convert_layout.py board.asc --export-gerber

# Convert Eagle .brd
python3 scripts/convert_layout.py board.brd --export-all

# KiCad file - just export Gerber (no conversion needed)
python3 scripts/convert_layout.py board.kicad_pcb --export-gerber --export-drill

# Dry run - see what would happen without executing
python3 scripts/convert_layout.py board.PcbDoc --dry-run --export-all
```

### Output Directory Structure

After running with `--export-all`:

```
converted_output/
├── board.kicad_pcb       # Converted KiCad PCB file
├── gerber/               # Gerber files
│   ├── board-F_Cu.gbr
│   ├── board-B_Cu.gbr
│   ├── board-F_Mask.gbr
│   ├── board-B_Mask.gbr
│   ├── board-F_Paste.gbr
│   ├── board-B_Paste.gbr
│   ├── board-F_Silkscreen.gbr
│   ├── board-B_Silkscreen.gbr
│   ├── board-Edge_Cuts.gbr
│   └── ...
├── drill/                # Drill files
│   ├── board-PTH.drl
│   └── board-NPTH.drl
├── positions.csv         # Pick and place
└── netlist.net           # Netlist
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `kicad-cli not found` | Install KiCad 8+ or add to PATH |
| Altium conversion incomplete | Complex designs may lose some elements. Export Gerber manually from Altium |
| PADS `.pcb` not recognized | PADS binary format is not supported. Export to `.asc` (ASCII) from within PADS first |
| Eagle `.brd` detected as unknown | Verify the file is XML format (Eagle 7+). Old binary Eagle files may need re-saving |
| Conversion timeout | Large designs may take longer. The script allows 5 minutes. For very large designs, export Gerber manually |
| Footprint library errors | KiCad may warn about missing footprint libraries. This doesn't affect Gerber export |

---

## 8. Schematic File Formats

For schematic review, the following formats are accepted:

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF (preferred) | .pdf | Visual review of schematic pages |
| KiCad schematic | .kicad_sch | Full netlist extraction |
| Altium schematic | .SchDoc | Convert via kicad-cli sch import |
| Eagle schematic | .sch | XML-based, parseable |
| Netlist (any) | .net, .csv | Net connection data only |

### Schematic conversion:
```bash
# Altium schematic -> KiCad
kicad-cli sch import --format altium schematic.SchDoc -o schematic.kicad_sch

# Eagle schematic -> KiCad
kicad-cli sch import --format eagle schematic.sch -o schematic.kicad_sch
```

---

## 9. BOM File Formats

BOM files are typically already in a parseable format:

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | .csv | Most common, easily parsed |
| Excel | .xlsx, .xls | Parsed with openpyxl/pandas |
| PDF | .pdf | Scanned/printed BOM - visual review |
| Tab-separated | .tsv, .txt | Common export from EDA tools |

No conversion is needed for BOM files. The EE Review skill handles all common formats directly.
