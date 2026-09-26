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


if __name__ == "__main__":
    unittest.main()
