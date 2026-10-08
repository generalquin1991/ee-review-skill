import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import convert_layout
import generate_report
import pads_common
import pads_full_converter
import pads_route_injector
import validate_skill
from parse_netlist import TelNetlist


class FormatAndExportTests(unittest.TestCase):
    def test_detects_schematic_and_project_files_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            schdoc = tmp_path / "design.SchDoc"
            schdoc.write_bytes(b"not parsed by extension")
            project = tmp_path / "design.PrjPcb"
            project.write_bytes(b"not parsed by extension")
            self.assertEqual(convert_layout.detect_format(str(schdoc)), "altium_sch")
            self.assertEqual(convert_layout.detect_format(str(project)), "altium_project")

    def test_detects_eagle_schematic_from_xml_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            schematic = Path(tmp) / "design.sch"
            schematic.write_text('<?xml version="1.0"?><eagle><drawing/></eagle>', encoding="utf-8")
            self.assertEqual(convert_layout.detect_format(str(schematic)), "eagle_sch")

    def test_export_results_preserve_failed_artifact(self):
        with mock.patch.object(convert_layout, "export_gerber", return_value=False):
            results = convert_layout.export_requested_files(
                "board.kicad_pcb",
                "/tmp/output",
                "kicad-cli",
                export_gerber_flag=True,
            )
        self.assertEqual(results, {"gerber": False})

    def test_conversion_manifest_records_exports_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "board.asc"
            converted = Path(tmp) / "board.kicad_pcb"
            source.write_text("source", encoding="utf-8")
            converted.write_text("(kicad_pcb)", encoding="utf-8")
            manifest_path = convert_layout.write_conversion_manifest(
                tmp,
                str(source),
                "pads",
                str(converted),
                export_results={"gerber": True, "drill": False},
                audit_findings=[{"severity": "warning", "category": "routing"}],
            )
            manifest = __import__("json").loads(Path(manifest_path).read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_format"], "pads")
            self.assertTrue(manifest["artifacts"]["gerber"]["success"])
            self.assertFalse(manifest["artifacts"]["drill"]["success"])
            self.assertEqual(len(manifest["audit_findings"]), 1)


class PadsCommonTests(unittest.TestCase):
    def test_parser_uses_shared_sections_and_encoding_fallback(self):
        pads = """!PADS-POWERPCB-V9.0\n*REMARK* 中文\nUNITS 1\nMAXIMUMLAYER 2\n*VIA*\nVIA1 100 1\n0 200 R\n*PART*\nR1 RES 100 200 0 0 0 0\n*ROUTE*\n*SIGNAL* N1\n100 200 0 50 0\n120 220 0 50 0\n*END*\n"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "board.asc"
            path.write_bytes(pads.encode("cp936"))
            lines, encoding = pads_common.read_pads_ascii(path)
            self.assertEqual(encoding, "cp936")
            self.assertEqual(pads_common.parse_pads_header(lines)["max_layer"], 2)
            parts = pads_common.parse_pads_parts(lines)
            self.assertEqual(parts["R1"].x, 100)
            routes, nets = pads_common.parse_pads_routes(lines)
            self.assertEqual(nets, ["N1"])
            self.assertEqual(len(routes[0]), 2)

            route_parser = pads_route_injector.PadsAsciiParser(str(path))
            route_parser.parse()
            full_parser = pads_full_converter.PadsAsciiParser(str(path))
            full_parser.parse()
            self.assertEqual(route_parser.encoding, "cp936")
            self.assertEqual(full_parser.encoding, "cp936")
            self.assertEqual(len(full_parser.routes), len(route_parser.routes))

    def test_transform_error_threshold_is_explicit(self):
        self.assertTrue(pads_common.transform_error_allowed(0.01, 0.01))
        self.assertFalse(pads_common.transform_error_allowed(0.010001, 0.01))
        self.assertFalse(pads_common.transform_error_allowed(None, 0.01))


class NetlistTests(unittest.TestCase):
    def test_continuation_line_stays_on_previous_net(self):
        text = """
$NETS
'GND' ; U1.1
U1.2
VCC ; U1.3
"""
        netlist = TelNetlist.from_text(text)
        self.assertEqual(netlist.pin_net("U1", "1"), "GND")
        self.assertEqual(netlist.pin_net("U1", "2"), "GND")
        self.assertEqual(netlist.pin_net("U1", "3"), "VCC")


class ReportTests(unittest.TestCase):
    def test_report_escapes_input_and_uses_data_driven_topology_note(self):
        data = {
            "project_name": "<Project>",
            "review_date": "2026-09-26",
            "overall_grade": "A",
            "overall_summary": "<script>alert(1)</script>",
            "dimensions": [
                {
                    "name": "Power & <Signals>",
                    "category": "schematic",
                    "grade": "A",
                    "score": 90,
                    "max_score": 100,
                    "findings": [
                        {
                            "severity": "warning",
                            "title": "<b>bad</b>",
                            "description": "a <script> tag",
                            "location": "U1 & C1",
                            "recommendation": "Use <value>",
                        }
                    ],
                }
            ],
            "summary": {
                "total_findings": 1,
                "critical_count": 0,
                "warning_count": 1,
                "info_count": 0,
                "top_risks": ["<risk>"],
                "recommendations": ["<fix>"],
            },
            "i2c_topology": {
                "title": "Custom topology",
                "note": "<b>custom</b>",
                "controllers": [
                    {
                        "id": "I2C0",
                        "pins": "SDA/SCL",
                        "label": "custom",
                        "nodes": [{"ref": "U1", "type": "MUX", "addr": "0x70", "role": "<role>"}],
                    }
                ],
            },
        }
        report = generate_report.generate_html_report(data)
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("Custom topology", report)
        self.assertIn("&lt;b&gt;custom&lt;/b&gt;", report)
        self.assertNotIn("ESP32-S3", report)
        self.assertIn("System block diagram", report)
        self.assertIn("not verifiable", report)

    def test_report_renders_mandatory_coverage_table(self):
        report = generate_report.generate_html_report(
            {
                "project_name": "Coverage",
                "coverage": [
                    {
                        "check": "USB-C CC",
                        "trigger": "USB-C detected",
                        "status": "not verifiable",
                        "evidence": "CC1/CC2 not present in supplied netlist",
                    }
                ],
            }
        )
        self.assertIn("Review Coverage", report)
        self.assertIn("USB-C CC", report)
        self.assertIn("coverage-unverified", report)
        self.assertIn("CC1/CC2 not present", report)


class CliTests(unittest.TestCase):
    def test_netlist_help_is_available(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "parse_netlist.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout.lower())


class ValidationPreflightTests(unittest.TestCase):
    def test_missing_pyyaml_has_install_guidance(self):
        with mock.patch.object(validate_skill, "has_pyyaml", return_value=False):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                result = validate_skill.main(["validate_skill.py"])
        self.assertEqual(result, 2)
        self.assertIn("pip install PyYAML", stderr.getvalue())


class SkillCoverageTests(unittest.TestCase):
    def test_ppt_cover_identity_requires_current_user_confirmation(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        ppt_style = (ROOT / "references" / "ppt-style.md").read_text(encoding="utf-8")
        for text in (skill, ppt_style):
            self.assertIn("explicitly ask the user to confirm", text)
            self.assertIn("even when", text)
            self.assertIn("already supplied in the current request", text)
            self.assertIn("never silently reuse", text)

    def test_conditional_matrix_is_linked_and_covers_requested_features(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        matrix = (ROOT / "references" / "conditional-review.md").read_text(encoding="utf-8")
        self.assertIn("references/conditional-review.md", skill)
        for phrase in ("ESD", "Battery", "Antenna", "USB Type-C", "4G", "Motor", "CERE"):
            self.assertIn(phrase, matrix)
        self.assertIn("System block diagram", matrix)
        diagrams = (ROOT / "references" / "architecture-diagrams.md").read_text(encoding="utf-8")
        self.assertIn("ask the user before skipping", diagrams)
        self.assertIn("A multi-board design requires the system block diagram", diagrams)
        self.assertIn("A battery product requires the power tree", diagrams)
        schematic = (ROOT / "references" / "schematic-review.md").read_text(encoding="utf-8")
        self.assertIn("Regulator under source sag", schematic)
        self.assertIn("The same row applies with no battery", schematic)
        self.assertIn("IO level", schematic)
        self.assertIn("I2C addresses", schematic)
        self.assertIn("Charge by default", schematic)
        self.assertIn("Power path and full charge", schematic)
        self.assertIn("Pack protection and PTC", schematic)
        self.assertIn("Clock rework footprint", schematic)
        self.assertIn("High-speed termination", schematic)
        self.assertIn("Footprint pin name and number", (ROOT / "references" / "pcb-review.md").read_text(encoding="utf-8"))
        self.assertIn("One slide lists every part whose pin table was opened", (ROOT / "references" / "pcb-review.md").read_text(encoding="utf-8"))
        self.assertIn("Footprint pin name and number", matrix)
        self.assertIn("not a finding until the user confirms", (ROOT / "references" / "bom-review.md").read_text(encoding="utf-8"))
        self.assertIn("one crop per board", (ROOT / "references" / "ppt-style.md").read_text(encoding="utf-8"))
        self.assertIn("crop of that region", (ROOT / "references" / "ppt-style.md").read_text(encoding="utf-8"))
        self.assertIn("Power tree", matrix)
        self.assertIn("references/review-contract.md", skill)
        self.assertIn("PDF-only", skill)
        contract = (ROOT / "references" / "review-contract.md").read_text(encoding="utf-8")
        self.assertIn("no schematic or netlist in this review", contract)
        self.assertIn("not verifiable", contract)
        self.assertIn("This skill does not include a distributor client", contract)
        self.assertIn("ee-review/datasheets", contract)
        self.assertIn("<project>/ee-review/", (ROOT / "references" / "architecture-diagrams.md").read_text(encoding="utf-8"))
        self.assertIn("EMC and safety applicability (private)", matrix)
        schematic = (ROOT / "references" / "schematic-review.md").read_text(encoding="utf-8")
        self.assertIn("Resistor is E96", schematic)
        self.assertIn("Schematic value versus ordered part", schematic)
        self.assertIn("footprint-library assignment error", schematic)
        self.assertIn("2.2` is not `2.21", schematic)
        self.assertIn("Class II DC bias", schematic)
        self.assertIn("MCU and SoC minimum system", schematic)
        self.assertIn("E96 resistors", matrix)
        self.assertIn("MCU/SoC minimum system", matrix)
        self.assertIn("That choice is not a slide", (ROOT / "references" / "ppt-style.md").read_text(encoding="utf-8"))


class GradePolicyTests(unittest.TestCase):
    def test_critical_finding_caps_dimension_and_overall_at_c(self):
        data = {
            "project_name": "Cap",
            "overall_grade": "A",
            "overall_summary": "kept",
            "dimensions": [
                {
                    "name": "Power",
                    "grade": "A",
                    "score": 85,
                    "findings": [
                        {
                            "severity": "critical",
                            "title": "short",
                            "description": "rail shorted",
                            "location": "U1",
                            "recommendation": "cut the net",
                        }
                    ],
                }
            ],
        }
        report = generate_report.generate_html_report(data)
        self.assertEqual(data["dimensions"][0]["grade"], "C")
        self.assertEqual(data["overall_grade"], "C")
        self.assertIn("Critical present", report)
        self.assertIn("overall: A → C", report)

    def test_dimension_d_caps_overall_without_raising_it(self):
        data = {
            "overall_grade": "S",
            "dimensions": [{"name": "Power", "grade": "D", "findings": []}],
        }
        generate_report.generate_html_report(data)
        self.assertEqual(data["overall_grade"], "C")
        self.assertEqual(data["dimensions"][0]["grade"], "D")

    def test_existing_d_stays_d_when_a_critical_is_present(self):
        data = {
            "overall_grade": "D",
            "dimensions": [
                {
                    "name": "Power",
                    "grade": "D",
                    "findings": [{"severity": "Critical", "title": "t", "description": "d", "location": "L", "recommendation": "r"}],
                }
            ],
        }
        generate_report.generate_html_report(data)
        self.assertEqual(data["overall_grade"], "D")
        self.assertEqual(data["dimensions"][0]["grade"], "D")
        self.assertNotIn("grade_policy_notes", data)


class DeckCommandTests(unittest.TestCase):
    def test_template_uses_placeholders_not_a_filled_cover(self):
        import zipfile

        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        with zipfile.ZipFile(ROOT / "assets" / "review-slide-template.pptx") as archive:
            cover = archive.read("ppt/slides/slide1.xml").decode("utf-8")
            layout = archive.read("ppt/slideLayouts/slideLayout5.xml").decode("utf-8")
            slide = archive.read("ppt/slides/slide19.xml").decode("utf-8")
        self.assertIn("{{PROJECT_CODE}}", cover)
        self.assertIn("{{REVIEWER}}", cover)
        self.assertNotIn("{{PROBLEM}}", cover)
        self.assertNotIn("Problem Placeholder", layout)
        self.assertIn('name="Subtitle"', slide)
        self.assertIn('wrap="none"', slide)
        self.assertIn('sz="1800"', slide)
        self.assertIn("scripts/generate_pptx.py", skill)
        self.assertIn("scripts/crop_schematic.py", skill)
        self.assertIn("one-off script", skill)
        self.assertIn("not verifiable", (ROOT / "references" / "ppt-style.md").read_text(encoding="utf-8"))

    def test_deck_keeps_template_font(self):
        import zipfile

        import generate_pptx

        def run_properties(blob, shape_name):
            text = blob.decode("utf-8")
            index = text.find(f'name="{shape_name}"')
            start = text.rfind("<p:sp", 0, index)
            end = text.find("</p:sp>", index)
            block = text[start:end]
            match = re.search(r"<a:rPr\b[^>]*(?:/>|>.*?</a:rPr>)", block, flags=re.S)
            return match.group(0)

        with zipfile.ZipFile(ROOT / "assets" / "review-slide-template.pptx") as archive:
            before = run_properties(archive.read("ppt/slides/slide1.xml"), "Google Shape;93;p14")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "DEMO_design_review_20260927.pptx"
            deck = {
                "project_code": "DEMO",
                "designer": "A. Engineer",
                "reviewer": "R. Name",
                "review_date": "20260927",
                "slides": [
                    {
                        "eyebrow": "Schematic · power",
                        "subtitle": "The set current needs a cell-limit check.",
                        "severity": "critical",
                        "body": "Rset is 3.4 kΩ. Therefore the fast-charge current is 39.7 mA. It is recommended to verify the cell's 1C rate.",
                    }
                ],
            }
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            generate_pptx.main([str(json_path), "-o", str(output)])
            with zipfile.ZipFile(output) as archive:
                slide = archive.read("ppt/slides/slide1.xml")
                finding = archive.read("ppt/slides/slide19.xml").decode("utf-8")
            self.assertEqual(run_properties(slide, "Google Shape;93;p14"), before)
            self.assertIn("DEMO", slide.decode("utf-8"))
            self.assertIn("Schematic · power", finding)
            self.assertIn("The set current needs a cell-limit check.", finding)
            self.assertNotIn("{{PROBLEM}}", finding)
            self.assertNotIn("Evidence1", finding)
            self.assertNotIn("{{PROJECT_CODE}}", slide.decode("utf-8"))
            start = finding.find('name="Subtitle"')
            subtitle = finding[finding.rfind("<p:sp", 0, start):finding.find("</p:sp>", start)]
            self.assertIn("C62828", subtitle)
            self.assertNotIn("Critical", subtitle)

    def test_evidence_picture_keeps_aspect_inside_the_frame(self):
        import struct
        import zipfile
        import zlib

        import generate_pptx

        def png(width, height):
            row = b"\x00" + (b"\xff\x00\x00" * width)
            raw = row * height

            def chunk(tag, data):
                return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

            ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

        with zipfile.ZipFile(ROOT / "assets" / "review-slide-template.pptx") as archive:
            template = archive.read("ppt/slides/slide19.xml").decode("utf-8")
        start = template.find('name="Evidence1"')
        block = template[template.rfind("<p:pic", 0, start):template.find("</p:pic>", start)]
        frame = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', block)
        frame_cx, frame_cy = int(frame.group(1)), int(frame.group(2))
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "square.png"
            image.write_bytes(png(80, 80))
            output = Path(tmp) / "out.pptx"
            deck = {
                "project_code": "DEMO",
                "designer": "A. Engineer",
                "reviewer": "R. Name",
                "review_date": "20260927",
                "slides": [
                    {
                        "eyebrow": "Schematic · port",
                        "subtitle": "J1 leaves the pair without a choke.",
                        "severity": "warning",
                        "body": "J1 has a TVS and no common-mode choke. We recommend a choke at the connector.",
                        "image": str(image),
                    }
                ],
            }
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            generate_pptx.main([str(json_path), "-o", str(output)])
            with zipfile.ZipFile(output) as archive:
                slide = archive.read("ppt/slides/slide19.xml").decode("utf-8")
        start = slide.find('name="Evidence1"')
        block = slide[slide.rfind("<p:pic", 0, start):slide.find("</p:pic>", start)]
        ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', block)
        off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', block)
        cx, cy = int(ext.group(1)), int(ext.group(2))
        self.assertAlmostEqual(cx / cy, 1.0, places=2)
        self.assertLessEqual(cx, frame_cx)
        self.assertLessEqual(cy, frame_cy)
        self.assertGreaterEqual(int(off.group(1)), 7100575)
        self.assertLess(int(off.group(1)) + cx, 7100575 + frame_cx + 2)

    def test_third_crop_continues_on_the_next_slide(self):
        import struct
        import zipfile
        import zlib

        import generate_pptx

        def png(width, height):
            row = b"\x00" + (b"\xff\x00\x00" * width)
            raw = row * height

            def chunk(tag, data):
                return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

            ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name in ("a.png", "b.png", "c.png"):
                path = Path(tmp) / name
                path.write_bytes(png(40, 20))
                paths.append(str(path))
            output = Path(tmp) / "out.pptx"
            deck = {
                "project_code": "DEMO",
                "designer": "A. Engineer",
                "reviewer": "R. Name",
                "review_date": "20260927",
                "slides": [
                    {
                        "eyebrow": "Schematic · I2C",
                        "subtitle": "The pull-up for this bus sits on board B.",
                        "severity": "warning",
                        "body": "SDA leaves board A. The pull-up is on board B. We recommend keeping that pull-up.",
                        "images": paths,
                    }
                ],
            }
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            generate_pptx.main([str(json_path), "-o", str(output)])
            with zipfile.ZipFile(output) as archive:
                first = archive.read("ppt/slides/slide19.xml").decode("utf-8")
                second = archive.read("ppt/slides/slide31.xml").decode("utf-8")
        self.assertIn("Evidence1", first)
        self.assertIn("Evidence2", first)
        self.assertIn("Evidence1", second)
        self.assertNotIn("Evidence2", second)

    def test_subtitle_must_fit_one_line(self):
        import generate_pptx

        deck = {
            "project_code": "DEMO",
            "designer": "A. Engineer",
            "reviewer": "R. Name",
            "review_date": "20260927",
            "slides": [
                {
                    "eyebrow": "Schematic · power",
                    "subtitle": "x" * (generate_pptx.SUBTITLE_CHAR_LIMIT + 1),
                    "severity": "info",
                    "body": "The resistor sets the current. We recommend checking the cell limit.",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.pptx"
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            with self.assertRaises(SystemExit):
                generate_pptx.main([str(json_path), "-o", str(output)])

    def test_long_body_continues_on_the_next_slide(self):
        import generate_pptx

        sentence = "The resistor stays on the rail and sets the charge current. "
        body = sentence * 40
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.pptx"
            deck = {
                "project_code": "DEMO",
                "designer": "A. Engineer",
                "reviewer": "R. Name",
                "review_date": "20260927",
                "slides": [
                    {
                        "eyebrow": "Schematic · power",
                        "subtitle": "The set current needs a cell-limit check.",
                        "severity": "warning",
                        "body": body,
                    }
                ],
            }
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            generate_pptx.main([str(json_path), "-o", str(output)])
            import zipfile

            with zipfile.ZipFile(output) as archive:
                names = [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
            self.assertGreaterEqual(len(names), 3)

    def test_single_page_finding_does_not_continue(self):
        import generate_pptx

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.pptx"
            deck = {
                "project_code": "DEMO",
                "designer": "A. Engineer",
                "reviewer": "R. Name",
                "review_date": "20260927",
                "slides": [
                    {
                        "eyebrow": "BOM · resistors",
                        "subtitle": "Several resistors are outside the E96 series.",
                        "severity": "warning",
                        "body": "Replace each value with the recommended E96 resistance.",
                        "table": {
                            "columns": ["Value", "References", "Recommended"],
                            "rows": [["2.2 kΩ", "R41, R39", "2.21 kΩ"], ["4.7 kΩ", "R12", "4.75 kΩ"]],
                        },
                        "single_page": True,
                    }
                ],
            }
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            generate_pptx.main([str(json_path), "-o", str(output)])
            import zipfile

            with zipfile.ZipFile(output) as archive:
                names = [name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
                finding = archive.read("ppt/slides/slide19.xml").decode("utf-8")
            self.assertEqual(len(names), 2)
            self.assertIn("<a:tbl>", finding)
            self.assertIn("Recommended", finding)
            self.assertIn("2.21 kΩ", finding)

    def test_single_page_keeps_extra_datasheet_crops(self):
        import struct
        import zipfile
        import zlib

        import generate_pptx

        def png(width, height):
            row = b"\x00" + (b"\xff\x00\x00" * width)
            raw = row * height

            def chunk(tag, data):
                return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

            ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name in ("schematic.png", "equation.png", "table.png"):
                path = Path(tmp) / name
                path.write_bytes(png(40, 20))
                paths.append(str(path))
            output = Path(tmp) / "out.pptx"
            deck = {
                "project_code": "DEMO",
                "designer": "A. Engineer",
                "reviewer": "R. Name",
                "review_date": "20260927",
                "slides": [
                    {
                        "eyebrow": "BOM · resistors",
                        "subtitle": "Several resistors are outside the E96 series.",
                        "severity": "warning",
                        "body": "Replace each off-grid value, except the divider set by the cited equation.",
                        "table": {
                            "columns": ["Value", "References", "Recommended"],
                            "rows": [["2.2 kΩ", "R41", "2.21 kΩ"]],
                        },
                        "images": paths,
                        "single_page": True,
                    }
                ],
            }
            json_path = Path(tmp) / "deck.json"
            json_path.write_text(json.dumps(deck), encoding="utf-8")
            generate_pptx.main([str(json_path), "-o", str(output)])
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                slides = [name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
                first = archive.read("ppt/slides/slide19.xml").decode("utf-8")
                second = archive.read("ppt/slides/slide31.xml").decode("utf-8")
            self.assertEqual(len(slides), 3)
            self.assertIn("<a:tbl>", first)
            self.assertNotIn("<a:tbl>", second)
            self.assertIn("ppt/media/finding-2-1.png", names)

    def test_symbol_crop_box_uses_sheet_coordinates(self):
        import crop_schematic

        schematic = """
        (kicad_sch (version 20231120) (generator eeschema)
          (paper "A4")
          (lib_symbols
            (symbol "Device:R" (pin passive line (at 0 0 0) (length 0))
              (property "Reference" "R" (at 0 0 0))
            )
          )
          (symbol (lib_id "Device:R") (at 100 40 0) (unit 1)
            (property "Reference" "R35" (at 100 38 0))
          )
        )
        """
        positions = crop_schematic.symbol_positions(schematic)
        self.assertEqual(positions["R35"], [(100.0, 40.0)])
        self.assertNotIn("R", positions)
        box = crop_schematic.crop_box_mm(positions["R35"], 25, (297.0, 210.0))
        self.assertEqual(box, (75.0, 15.0, 125.0, 65.0))


if __name__ == "__main__":
    unittest.main()
