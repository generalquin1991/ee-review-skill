import io
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


if __name__ == "__main__":
    unittest.main()
