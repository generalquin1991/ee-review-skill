#!/usr/bin/env python3
"""
convert_layout.py - Auto-detect and convert PCB layout or schematic files to KiCad format.

Detects input file format by extension and content, then uses kicad-cli to convert
board files to .kicad_pcb or supported schematic files to .kicad_sch. PCB inputs
can optionally export Gerber, drill, pick-place, and IPC-D-356 netlist files.
Successful conversions write conversion-manifest.json beside the output with
the source format, artifact status, and post-conversion audit findings.

Requirements:
  - kicad-cli must be installed and available in PATH (KiCad 8+ / 10.0+)
  - Python 3.8+

Usage:
  python3 convert_layout.py <input_file> [options]

Options:
  --output-dir <dir>     Output directory (default: ./converted_output)
  --export-gerber        Also export Gerber files after conversion
  --export-drill         Also export drill files after conversion
  --export-pos           Also export pick-place file after conversion
  --export-netlist       Also export netlist file after conversion
  --export-all           Export all above formats after conversion
  --dry-run              Show detected format and planned commands without executing

Examples:
  # Altium -> KiCad
  python3 convert_layout.py board.PcbDoc --output-dir ./output --export-all

  # PADS ASCII -> KiCad
  python3 convert_layout.py board.asc --output-dir ./output --export-all

  # KiCad (no conversion needed, just export)
  python3 convert_layout.py board.kicad_pcb --export-gerber --export-drill

  # Dry run to see what would happen
  python3 convert_layout.py board.PcbDoc --dry-run
"""

import sys
import os
import shutil
import subprocess
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


# ─── Format Detection ───────────────────────────────────────────────────────

# Extension → kicad-cli format name mapping
EXT_FORMAT_MAP = {
    # Altium Designer
    ".pcbdoc":      "altium",
    ".prjpcb":      "altium_project",  # Altium project (pass the referenced .PcbDoc explicitly)
    ".schdoc":      "altium_sch",      # Altium schematic
    # PADS
    ".asc":         "pads",       # PADS ASCII export
    # KiCad (native, no conversion needed)
    ".kicad_pcb":   "kicad",
    ".kicad_pro":   "kicad_project",
    # Eagle
    ".brd":         "eagle",      # Eagle board (could also be Altium, check content)
    # PADS Logic schematic (binary, not convertible by kicad-cli)
    ".sch":         "pads_sch",   # PADS Logic binary schematic
    # Could be PADS binary .pcb or Cadstar — check content
    ".pcb":         "unknown",    # Ambiguous, must check content
    # PCAD
    ".pcad":        "pcad",
}

# Formats that kicad-cli pcb import supports
SUPPORTED_IMPORT_FORMATS = {
    "altium", "pads", "eagle", "cadstar", "pcad", "fabmaster", "solidworks"
}

SCHEMATIC_FORMATS = {"altium_sch", "eagle_sch"}
PROJECT_FORMATS = {"altium_project", "kicad_project"}

# Binary formats that need content-based detection
AMBIGUOUS_EXTENSIONS = {".brd", ".pcb", ".sch"}


def detect_format_by_content(file_path: str) -> str:
    """Detect file format by reading file header/content."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(512)
    except Exception:
        return "unknown"

    header_str = header.decode("latin-1", errors="replace")

    # Altium .PcbDoc starts with specific binary markers
    # Contains "Board" or "PCB" binary structures
    if b"PCB" in header[:64] and b"Binary" in header:
        return "altium"

    # PADS ASCII starts with !PADS-POWERPCB-Vx.x or *PADS-PCB*
    # Real-world headers: !PADS-POWERPCB-V9.0-BASIC-..., *PADS-PCB*
    if header_str.strip().startswith("!PADS-POWERPCB") or \
       header_str.strip().startswith("*PADS-PCB*") or \
       header_str.strip().startswith("!PADS-PCB"):
        return "pads"

    # PADS Layout binary .pcb — magic bytes: 00 FF 27 20
    if len(header) >= 4 and header[0] == 0x00 and header[1] == 0xFF \
       and header[2] == 0x27 and header[3] == 0x20:
        return "pads_binary"

    # PADS Logic binary .sch — magic bytes: 00 FE 0D 00
    if len(header) >= 4 and header[0] == 0x00 and header[1] == 0xFE \
       and header[2] == 0x0D:
        return "pads_sch"

    # KiCad starts with (kicad_pcb
    if header_str.strip().startswith("(kicad_pcb"):
        return "kicad"

    # Eagle .brd is XML, starts with <?xml or < eagle
    if header_str.strip().startswith("<?xml") or "<eagle" in header_str[:200]:
        return "eagle"

    # Cadstar
    if "CADSTAR" in header_str[:200] or "<CADSTAR" in header_str[:200]:
        return "cadstar"

    return "unknown"


def detect_format(file_path: str) -> str:
    """
    Detect the PCB file format.

    Returns one of: altium, pads, pads_binary, pads_sch, eagle, cadstar, pcad, kicad, unknown
    """
    ext = Path(file_path).suffix.lower()

    # Direct mapping for unambiguous extensions
    if ext == ".pcbdoc":
        return "altium"
    if ext == ".schdoc":
        return "altium_sch"
    if ext == ".prjpcb":
        return "altium_project"
    if ext == ".asc":
        return "pads"
    if ext == ".kicad_pcb":
        return "kicad"
    if ext == ".kicad_pro":
        return "kicad_project"

    # Ambiguous extensions - check content first
    if ext in AMBIGUOUS_EXTENSIONS:
        fmt = detect_format_by_content(file_path)
        if ext == ".sch" and fmt == "eagle":
            return "eagle_sch"
        if fmt != "unknown":
            return fmt
        # Fall back to extension-based guess
        return EXT_FORMAT_MAP.get(ext, "unknown")

    return EXT_FORMAT_MAP.get(ext, "unknown")


# ─── Conversion ────────────────────────────────────────────────────────────

def convert_schematic_to_kicad(input_file: str, output_dir: str, fmt: str, kicad_cli: str) -> str:
    """Convert a supported schematic source to a KiCad .kicad_sch file."""
    import_format = {"altium_sch": "altium", "eagle_sch": "eagle"}.get(fmt)
    if import_format is None:
        print(f"  [ERROR] Unsupported schematic format: {fmt}")
        return ""

    output_path = os.path.join(output_dir, f"{Path(input_file).stem}.kicad_sch")
    cmd = [kicad_cli, "sch", "import", "--format", import_format, input_file, "-o", output_path]
    print(f"  [CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        print("  [ERROR] kicad-cli schematic import timed out after 300 seconds")
        return ""
    except FileNotFoundError:
        print("  [ERROR] kicad-cli not found. Please install KiCad 8+ or 10.0+")
        return ""
    except Exception as exc:
        print(f"  [ERROR] Schematic import error: {exc}")
        return ""

    if result.returncode != 0:
        print(f"  [ERROR] kicad-cli returned error code {result.returncode}")
        if result.stderr:
            print(f"         stderr: {result.stderr[:500]}")
        return ""
    if not os.path.isfile(output_path):
        print(f"  [ERROR] kicad-cli reported success but did not create {output_path}")
        return ""
    print(f"  [OK] Converted to: {output_path}")
    return output_path

def check_kicad_cli() -> str:
    """Check if kicad-cli is available. Returns the command path or empty string."""
    kicad_cli = shutil.which("kicad-cli")
    if kicad_cli:
        return kicad_cli

    # Try common install locations
    common_paths = [
        # macOS - KiCad app bundle
        "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        "/Applications/KiCad/kicad-cli",
        # Linux
        "/usr/bin/kicad-cli",
        "/usr/local/bin/kicad-cli",
        "/opt/kicad/bin/kicad-cli",
        # Windows (Git Bash / WSL paths)
        "/c/Program Files/KiCad/bin/kicad-cli.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    return ""


def convert_to_kicad(input_file: str, output_dir: str, fmt: str, kicad_cli: str) -> str:
    """
    Convert input file to .kicad_pcb using kicad-cli.

    Returns the path to the converted .kicad_pcb file, or empty string on failure.
    """
    input_name = Path(input_file).stem
    output_kicad_pcb = os.path.join(output_dir, f"{input_name}.kicad_pcb")

    if fmt == "kicad":
        # Already KiCad format - just copy if needed or return original
        print(f"  [SKIP] File is already in KiCad format: {input_file}")
        return input_file

    if fmt not in SUPPORTED_IMPORT_FORMATS:
        print(f"  [ERROR] Unsupported import format: {fmt}")
        print(f"          Supported formats: {', '.join(sorted(SUPPORTED_IMPORT_FORMATS))}")
        return ""

    cmd = [
        kicad_cli, "pcb", "import",
        "--format", fmt,
        input_file,
        "-o", output_kicad_pcb
    ]

    print(f"  [CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"  [ERROR] kicad-cli returned error code {result.returncode}")
            if result.stderr:
                print(f"         stderr: {result.stderr[:500]}")
            if result.stdout:
                print(f"         stdout: {result.stdout[:500]}")
            return ""
        print(f"  [OK] Converted to: {output_kicad_pcb}")
        return output_kicad_pcb
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] kicad-cli timed out after 300 seconds")
        return ""
    except FileNotFoundError:
        print(f"  [ERROR] kicad-cli not found. Please install KiCad 8+ or 10.0+")
        return ""
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        return ""


def export_gerber(kicad_pcb: str, output_dir: str, kicad_cli: str) -> bool:
    """Export Gerber files from a .kicad_pcb file."""
    gerber_dir = os.path.join(output_dir, "gerber")
    os.makedirs(gerber_dir, exist_ok=True)

    cmd = [kicad_cli, "pcb", "export", "gerbers", "-o", gerber_dir + "/", kicad_pcb]
    print(f"  [CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  [ERROR] Gerber export failed: {result.stderr[:300]}")
            return False
        print(f"  [OK] Gerber files exported to: {gerber_dir}")
        return True
    except Exception as e:
        print(f"  [ERROR] Gerber export error: {e}")
        return False


def export_drill(kicad_pcb: str, output_dir: str, kicad_cli: str) -> bool:
    """Export drill files from a .kicad_pcb file."""
    drill_dir = os.path.join(output_dir, "drill")
    os.makedirs(drill_dir, exist_ok=True)

    cmd = [kicad_cli, "pcb", "export", "drill", "-o", drill_dir + "/", kicad_pcb]
    print(f"  [CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  [ERROR] Drill export failed: {result.stderr[:300]}")
            return False
        print(f"  [OK] Drill files exported to: {drill_dir}")
        return True
    except Exception as e:
        print(f"  [ERROR] Drill export error: {e}")
        return False


def export_positions(kicad_pcb: str, output_dir: str, kicad_cli: str) -> bool:
    """Export pick-place file from a .kicad_pcb file."""
    pos_file = os.path.join(output_dir, "positions.csv")
    cmd = [kicad_cli, "pcb", "export", "pos", "-o", pos_file, kicad_pcb]
    print(f"  [CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  [ERROR] Position export failed: {result.stderr[:300]}")
            return False
        print(f"  [OK] Pick-place file exported to: {pos_file}")
        return True
    except Exception as e:
        print(f"  [ERROR] Position export error: {e}")
        return False


def export_netlist(kicad_pcb: str, output_dir: str, kicad_cli: str) -> bool:
    """Export IPC-D-356 netlist file from a .kicad_pcb file."""
    netlist_file = os.path.join(output_dir, "netlist.ipc356")
    cmd = [kicad_cli, "pcb", "export", "ipcd356", "-o", netlist_file, kicad_pcb]
    print(f"  [CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  [ERROR] Netlist export failed: {result.stderr[:300]}")
            return False
        print(f"  [OK] Netlist (IPC-D-356) exported to: {netlist_file}")
        return True
    except Exception as e:
        print(f"  [ERROR] Netlist export error: {e}")
        return False


def export_requested_files(kicad_pcb: str, output_dir: str, kicad_cli: str,
                           export_all: bool = False, export_gerber_flag: bool = False,
                           export_drill_flag: bool = False, export_pos_flag: bool = False,
                           export_netlist_flag: bool = False) -> dict:
    """Run requested exporters and return ``artifact -> success`` results."""
    results = {}
    if export_all or export_gerber_flag:
        results["gerber"] = export_gerber(kicad_pcb, output_dir, kicad_cli)
    if export_all or export_drill_flag:
        results["drill"] = export_drill(kicad_pcb, output_dir, kicad_cli)
    if export_all or export_pos_flag:
        results["positions"] = export_positions(kicad_pcb, output_dir, kicad_cli)
    if export_all or export_netlist_flag:
        results["netlist"] = export_netlist(kicad_pcb, output_dir, kicad_cli)
    return results


def audit_conversion(kicad_pcb: str, source_fmt: str) -> list:
    """
    Audit the converted KiCad PCB for common data loss issues.

    Returns a list of audit findings (dicts with 'severity', 'category', 'message').
    """
    import re

    findings = []

    try:
        with open(kicad_pcb, 'r', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return [{'severity': 'critical', 'category': 'file', 'message': f'Cannot read file: {e}'}]

    # 1. Check for routing traces
    segments = len(re.findall(r'\(segment\b', content))
    vias = len(re.findall(r'\(via\b', content))
    if segments == 0:
        findings.append({
            'severity': 'critical',
            'category': 'routing',
            'message': 'No routing traces (segments) found. kicad-cli PADS importer does not convert *ROUTE* data. Use pads_route_injector.py or pads_full_converter.py to inject routes from PADS ASCII.'
        })
    if vias == 0 and source_fmt == 'pads':
        findings.append({
            'severity': 'warning',
            'category': 'routing',
            'message': 'No vias found. PADS via definitions are not converted by kicad-cli.'
        })

    # 2. Check solder mask settings
    smm = re.search(r'\(solder_mask_margin\s+([\d.]+)\)', content)
    if not smm:
        findings.append({
            'severity': 'warning',
            'category': 'solder_mask',
            'message': 'Board-level solder_mask_margin NOT SET. KiCad uses default (~0.051mm). Verify this matches fabricator requirements. PADS per-pad mask expansion data is lost during conversion.'
        })

    # 3. Check solder paste settings
    spm = re.search(r'\(solder_paste_margin\s+([\d.]+)\)', content)
    spr = re.search(r'\(solder_paste_margin_ratio\s+([\d.]+)\)', content)
    if not spm and not spr:
        # Check if any fine-pitch components exist
        pads = re.findall(r'\(pad\s+"[^"]+"\s+\w+\s+\w+\s+\(at\s+[\d.-]+\s+[\d.-]+\s*\)?\s*\n?\s*\(size\s+([\d.]+)\s+([\d.]+)\)', content)
        fine_pitch_found = False
        for w, h in pads:
            if float(w) < 0.5 or float(h) < 0.5:
                fine_pitch_found = True
                break
        if fine_pitch_found:
            findings.append({
                'severity': 'warning',
                'category': 'solder_paste',
                'message': 'Board-level solder_paste_margin NOT SET and fine-pitch pads detected. Paste = copper size (no reduction). PADS per-pad paste sizes are lost during conversion. Consider setting paste reduction for fine-pitch components.'
            })
        else:
            findings.append({
                'severity': 'info',
                'category': 'solder_paste',
                'message': 'Board-level solder_paste_margin NOT SET. Paste = copper size (no reduction). Acceptable if no fine-pitch components.'
            })

    # 4. Check via tenting
    via_layers = re.findall(r'\(via\b.*?\(layers\s+([^)]+)\)', content, re.DOTALL)
    tented_count = 0
    open_count = 0
    for vl in via_layers:
        if 'F.Mask' not in vl and 'B.Mask' not in vl:
            tented_count += 1
        else:
            open_count += 1
    if tented_count > 0 and open_count == 0:
        findings.append({
            'severity': 'info',
            'category': 'via_tenting',
            'message': f'All {tented_count} vias are fully tented (no mask opening). Verify this matches design intent — tented vias cannot be used as test points.'
        })
    elif tented_count > 0 and open_count > 0:
        findings.append({
            'severity': 'info',
            'category': 'via_tenting',
            'message': f'Mixed via tenting: {tented_count} tented, {open_count} non-tented. Verify tenting strategy is intentional.'
        })

    # 5. Check silk screen
    silk_fp_lines = len(re.findall(r'fp_line.*?"F\.SilkS"', content, re.DOTALL))
    silk_gr_text = len(re.findall(r'gr_text.*?"F\.SilkS"', content, re.DOTALL))
    if silk_fp_lines == 0 and silk_gr_text == 0:
        findings.append({
            'severity': 'warning',
            'category': 'silk_screen',
            'message': 'No silk screen data found on F.SilkS. Footprint silhouettes and reference designators may be missing.'
        })
    elif silk_gr_text == 0 and source_fmt == 'pads':
        findings.append({
            'severity': 'info',
            'category': 'silk_screen',
            'message': f'{silk_fp_lines} footprint silk lines found, but no board-level silk text. PADS TEXT section (board name, date, etc.) was not converted.'
        })

    # 6. Check board outline
    edge_cuts = len(re.findall(r'gr_line.*?"Edge\.Cuts"', content, re.DOTALL))
    if edge_cuts < 4:
        findings.append({
            'severity': 'warning',
            'category': 'board_outline',
            'message': f'Only {edge_cuts} Edge.Cuts lines found. Board outline may be incomplete. PADS LINES section board outline was not fully converted.'
        })

    # 7. Check copper zones
    zones = len(re.findall(r'\(zone\b', content))
    if zones == 0:
        findings.append({
            'severity': 'info',
            'category': 'copper_zones',
            'message': 'No copper zones found. PADS plane/thermal definitions are not converted by kicad-cli. Ground/power pours must be re-created manually.'
        })

    # 8. Check pad layer consistency
    pads_with_all_layers = len(re.findall(r'\(layers\s+"F\.Cu"\s+"F\.Mask"\s+"F\.Paste"\)', content))
    pads_without_paste = len(re.findall(r'\(layers\s+"F\.Cu"\s+"F\.Mask"\)', content))
    pads_copper_only = len(re.findall(r'\(layers\s+"F\.Cu"\)', content))
    tht_pads = len(re.findall(r'\(pad\s+"[^"]+"\s+thru_hole', content))

    if tht_pads > 0:
        # Check if through-hole pads have paste (they shouldn't for wave solder)
        tht_with_paste = 0
        for m in re.finditer(r'\(pad\s+"[^"]+"\s+thru_hole.*?\(layers\s+([^)]+)\)', content, re.DOTALL):
            if 'F.Paste' in m.group(1):
                tht_with_paste += 1
        if tht_with_paste > 0:
            findings.append({
                'severity': 'warning',
                'category': 'pad_paste',
                'message': f'{tht_with_paste} through-hole pads have F.Paste in layers. Through-hole pads typically should NOT have paste (paste is applied by wave solder, not stencil).'
            })

    return findings


def print_audit_report(findings: list):
    """Print the post-conversion audit report."""
    print()

    print("-" * 60)
    print("Post-Conversion Audit Report")
    print("-" * 60)

    if not findings:
        print("  [OK] No issues found in converted file.")
        return

    # Group by severity
    critical = [f for f in findings if f['severity'] == 'critical']
    warnings = [f for f in findings if f['severity'] == 'warning']
    infos = [f for f in findings if f['severity'] == 'info']

    if critical:
        print(f"\n  [CRITICAL] ({len(critical)} issues)")
        for f in critical:
            print(f"    [{f['category']}] {f['message']}")

    if warnings:
        print(f"\n  [WARNING] ({len(warnings)} issues)")
        for f in warnings:
            print(f"    [{f['category']}] {f['message']}")

    if infos:
        print(f"\n  [INFO] ({len(infos)} issues)")
        for f in infos:
            print(f"    [{f['category']}] {f['message']}")

    print()


def write_conversion_manifest(output_dir: str, input_file: str, source_format: str,
                              converted_file: str, export_results=None,
                              audit_findings=None) -> str:
    """Write a machine-readable record of conversion and verification results."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name, ok in (export_results or {}).items():
        artifacts[name] = {
            "requested": True,
            "success": bool(ok),
        }
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(Path(input_file).resolve()),
        "source_format": source_format,
        "converted_file": str(Path(converted_file).resolve()) if converted_file else None,
        "artifacts": artifacts,
        "audit_findings": audit_findings or [],
    }
    manifest_path = output_path / "conversion-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(manifest_path)


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Auto-detect and convert PCB layout or supported schematic files to KiCad format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("input_file", help="Path to the input PCB/schematic file")
    parser.add_argument("--output-dir", default="./converted_output",
                        help="Output directory (default: ./converted_output)")
    parser.add_argument("--export-gerber", action="store_true",
                        help="Export Gerber files after conversion")
    parser.add_argument("--export-drill", action="store_true",
                        help="Export drill files after conversion")
    parser.add_argument("--export-pos", action="store_true",
                        help="Export pick-place file after conversion")
    parser.add_argument("--export-netlist", action="store_true",
                        help="Export netlist file after conversion")
    parser.add_argument("--export-all", action="store_true",
                        help="Export all formats after conversion")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show detected format and planned commands without executing")

    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.input_file):
        print(f"[ERROR] Input file not found: {args.input_file}")
        sys.exit(1)

    # Normalize paths
    input_file = os.path.abspath(args.input_file)
    output_dir = os.path.abspath(args.output_dir)

    print("=" * 60)
    print("EE Review - Layout File Converter")
    print("=" * 60)
    print(f"  Input file:  {input_file}")
    print(f"  Output dir:  {output_dir}")
    print()

    # Step 1: Detect format
    fmt = detect_format(input_file)
    print(f"[1] Format Detection")
    print(f"  Detected format: {fmt}")

    if fmt == "unknown":
        print(f"  [ERROR] Could not detect file format from: {input_file}")
        print(f"          Supported extensions: {', '.join(sorted(EXT_FORMAT_MAP.keys()))}")
        print()
        print(f"  If this is a PADS binary .pcb file, please export as ASCII (.asc) first:")
        print(f"    In PADS: File -> Export -> ASCII (select all: Parts, Nets, Routes, Vias, Layer Stackup)")
        sys.exit(1)

    if fmt == "pads_binary":
        print(f"  [ERROR] This is a PADS Layout binary .pcb file.")
        print(f"          kicad-cli cannot import PADS binary format directly.")
        print(f"          Please export as ASCII (.asc) first:")
        print(f"            Option A (manual): In PADS Layout -> File -> Export -> ASCII")
        print(f"            Option B (automated): Use pads_export_all.bas script in PADS")
        print(f"          Then run this script on the .asc file.")
        sys.exit(1)

    if fmt == "pads_sch":
        print(f"  [ERROR] This is a PADS Logic binary .sch schematic file.")
        print(f"          kicad-cli cannot import PADS Logic schematics.")
        print(f"          Options:")
        print(f"            1. Export PDF from PADS Logic: File -> Print -> PDF")
        print(f"               (then use the PDF for schematic review)")
        print(f"            2. Export netlist from PADS Logic: File -> Export -> Netlist")
        print(f"               (then use the netlist for connectivity review)")
        sys.exit(1)

    if fmt in PROJECT_FORMATS:
        print(f"  [ERROR] {fmt} is a project file, not a PCB input.")
        if fmt == "altium_project":
            print("          Pass the referenced Altium .PcbDoc file explicitly.")
        else:
            print("          Pass the KiCad .kicad_pcb file explicitly.")
        sys.exit(1)

    if fmt in SCHEMATIC_FORMATS:
        export_requested = args.export_all or args.export_gerber or args.export_drill or args.export_pos or args.export_netlist
        if export_requested:
            print("  [ERROR] Manufacturing exports apply to PCB files, not schematic files.")
            sys.exit(1)
        if args.dry_run:
            import_format = {"altium_sch": "altium", "eagle_sch": "eagle"}[fmt]
            print("[DRY RUN] No files were modified.")
            print(f"  Convert: kicad-cli sch import --format {import_format} {input_file} -o {output_dir}/{Path(input_file).stem}.kicad_sch")
            sys.exit(0)
        kicad_cli = check_kicad_cli()
        if not kicad_cli:
            print("  [ERROR] kicad-cli not found in PATH or common install locations.")
            sys.exit(1)
        os.makedirs(output_dir, exist_ok=True)
        schematic_path = convert_schematic_to_kicad(input_file, output_dir, fmt, kicad_cli)
        if not schematic_path:
            sys.exit(1)
        manifest_path = write_conversion_manifest(output_dir, input_file, fmt, schematic_path)
        print("[DONE] Schematic conversion complete!")
        print(f"  KiCad schematic: {schematic_path}")
        print(f"  Manifest: {manifest_path}")
        return

    if fmt == "pads":
        # Double-check it's ASCII, not binary
        content_fmt = detect_format_by_content(input_file)
        if content_fmt == "unknown":
            print(f"  [WARNING] File has .asc extension but content doesn't match PADS ASCII format.")
            print(f"           Verify the file was exported correctly from PADS.")
        elif content_fmt == "pads":
            print(f"  [OK] PADS ASCII format verified.")

    print()

    # Step 2: Check kicad-cli availability
    kicad_cli = check_kicad_cli()
    print(f"[2] Tool Availability")
    if fmt == "kicad":
        print(f"  No conversion needed - file is already KiCad format")
        kicad_pcb_path = input_file
    else:
        if not kicad_cli:
            print(f"  [ERROR] kicad-cli not found in PATH or common install locations.")
            print(f"          Please install KiCad 8+ or 10.0+:")
            print(f"            macOS:  brew install --cask kicad")
            print(f"            Ubuntu: sudo apt install kicad")
            print(f"            Windows: Download from https://www.kicad.org/download/")
            print()
            if args.dry_run:
                print(f"  [DRY RUN] Would use kicad-cli to convert {fmt} -> .kicad_pcb")
            else:
                sys.exit(1)
        else:
            print(f"  kicad-cli found: {kicad_cli}")
        print()

    # Dry run mode - show planned commands and exit
    if args.dry_run:
        print("[3] Planned Actions (DRY RUN)")
        if fmt != "kicad":
            print(f"  Convert: kicad-cli pcb import --format {fmt} {input_file} -o {output_dir}/{Path(input_file).stem}.kicad_pcb")
        if args.export_all or args.export_gerber:
            print(f"  Export:  kicad-cli pcb export gerbers -o {output_dir}/gerber/ <kicad_pcb>")
        if args.export_all or args.export_drill:
            print(f"  Export:  kicad-cli pcb export drill -o {output_dir}/drill/ <kicad_pcb>")
        if args.export_all or args.export_pos:
            print(f"  Export:  kicad-cli pcb export pos -o {output_dir}/positions.csv <kicad_pcb>")
        if args.export_all or args.export_netlist:
            print(f"  Export:  kicad-cli pcb export ipcd356 -o {output_dir}/netlist.ipc356 <kicad_pcb>")
        print()
        print("[OK] Dry run complete. No files were modified.")
        sys.exit(0)

    # Step 3: Convert
    if fmt != "kicad":
        os.makedirs(output_dir, exist_ok=True)
        print(f"[3] Conversion: {fmt} -> KiCad")
        kicad_pcb_path = convert_to_kicad(input_file, output_dir, fmt, kicad_cli)
        if not kicad_pcb_path:
            print(f"\n[FAILED] Conversion failed. See errors above.")
            sys.exit(1)
    else:
        kicad_pcb_path = input_file
        print(f"[3] Conversion: skipped (already KiCad)")
    print()

    # Step 4: Export (if requested)
    export_any = args.export_all or args.export_gerber or args.export_drill or args.export_pos or args.export_netlist
    export_results = {}
    if export_any:
        os.makedirs(output_dir, exist_ok=True)
        print(f"[4] Exporting manufacturing files")
        if fmt == "kicad":
            kicad_cli = kicad_cli or check_kicad_cli()
            if not kicad_cli:
                print(f"  [ERROR] kicad-cli needed for export but not found")
                sys.exit(1)

        export_results = export_requested_files(
            kicad_pcb_path,
            output_dir,
            kicad_cli,
            export_all=args.export_all,
            export_gerber_flag=args.export_gerber,
            export_drill_flag=args.export_drill,
            export_pos_flag=args.export_pos,
            export_netlist_flag=args.export_netlist,
        )
        failed_exports = [name for name, ok in export_results.items() if not ok]
        if failed_exports:
            manifest_path = write_conversion_manifest(
                output_dir,
                input_file,
                fmt,
                kicad_pcb_path,
                export_results=export_results,
                audit_findings=[],
            )
            print(f"[FAILED] Export failed for: {', '.join(failed_exports)}")
            print(f"  Manifest: {manifest_path}")
            sys.exit(1)
    else:
        print(f"[4] Export: skipped (no --export flags)")

    # Step 5: Post-conversion audit
    findings = []
    if fmt != "kicad":
        print(f"[5] Post-Conversion Audit")
        findings = audit_conversion(kicad_pcb_path, fmt)
        print_audit_report(findings)
    else:
        print(f"[5] Audit: skipped (native KiCad file)")

    manifest_path = write_conversion_manifest(
        output_dir,
        input_file,
        fmt,
        kicad_pcb_path,
        export_results=export_results,
        audit_findings=findings,
    )

    print()
    print("=" * 60)
    print(f"[DONE] Conversion complete!")
    print(f"  KiCad PCB:  {kicad_pcb_path}")
    print(f"  Manifest:   {manifest_path}")
    if export_any:
        print(f"  Output dir: {output_dir}")
        print(f"  Contains:   ", end="")
        items = []
        if args.export_all or args.export_gerber:
            items.append("gerber/")
        if args.export_all or args.export_drill:
            items.append("drill/")
        if args.export_all or args.export_pos:
            items.append("positions.csv")
        if args.export_all or args.export_netlist:
            items.append("netlist.ipc356")
        print(", ".join(items))
    print("=" * 60)


if __name__ == "__main__":
    main()
