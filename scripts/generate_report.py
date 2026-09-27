#!/usr/bin/env python3
"""
EE Review Report Generator
Generates an interactive HTML report from structured EE review data (JSON input).

Usage:
    python3 generate_report.py <input.json> [output.html]

Input JSON schema:
{
    "project_name": "Project Name",
    "review_date": "2025-01-15",
    "reviewer": "Reviewer Name",
    "input_files": ["schematic.pdf", "bom.xlsx", "pcb.gbr"],
    "overall_grade": "B",
    "overall_summary": "Brief summary text",
    "coverage": [
        {
            "check": "System block diagram",
            "trigger": "file/page or missing",
            "status": "confirmed",
            "evidence": "Sheet 1"
        }
    ],
    "dimensions": [
        {
            "name": "Power Supply Design",
            "category": "schematic",
            "grade": "A",
            "score": 88,
            "max_score": 100,
            "findings": [
                {
                    "severity": "critical",
                    "title": "Missing decoupling on U3",
                    "description": "U3 (DC-DC converter) output lacks bulk capacitor...",
                    "location": "Sheet 3, U3 pin 5",
                    "recommendation": "Add 22uF ceramic capacitor close to pin 5"
                },
                {
                    "severity": "warning",
                    "title": "Capacitor voltage margin low",
                    "description": "C12 is rated 6.3V on a 5V rail, margin only 26%...",
                    "location": "Sheet 2, C12",
                    "recommendation": "Use 10V or 16V rated capacitor"
                },
                {
                    "severity": "info",
                    "title": "Consider adding test point",
                    "description": "No test point on 3.3V rail for easy measurement",
                    "location": "Sheet 1, power section",
                    "recommendation": "Add TP1 test point on 3.3V rail"
                }
            ]
        }
    ],
    "summary": {
        "total_findings": 15,
        "critical_count": 2,
        "warning_count": 5,
        "info_count": 8,
        "top_risks": [
            "Missing decoupling on U3 output",
            "EOL component U7 in BOM",
            "Clock trace crosses ground split"
        ],
        "recommendations": [
            "Address all critical findings before tape-out",
            "Replace EOL component U7 with active alternative",
            "Add decoupling capacitors per findings"
        ]
    }
}
"""

import json
import html as html_lib
import math
import re
import sys
import os
from datetime import datetime

GRADE_COLORS = {
    "S": "#9b59b6",
    "A": "#27ae60",
    "B": "#2196f3",
    "C": "#f39c12",
    "D": "#e74c3c",
}

GRADE_LABELS = {
    "S": "Excellent",
    "A": "Good",
    "B": "Acceptable",
    "C": "Needs Improvement",
    "D": "Fail",
}

SEVERITY_CONFIG = {
    "critical": {"icon": "&#128308;", "color": "#e74c3c", "label": "Critical", "bg": "#fdeaea"},
    "warning": {"icon": "&#128992;", "color": "#f39c12", "label": "Warning", "bg": "#fef5e7"},
    "info": {"icon": "&#128994;", "color": "#27ae60", "label": "Info", "bg": "#eafaf1"},
}

CATEGORY_LABELS = {
    "schematic": "Schematic",
    "pcb": "PCB Design",
    "bom": "BOM",
    "general": "General",
}

MANDATORY_COVERAGE_CHECKS = (
    "System block diagram",
    "Power tree",
    "ESD and external boundaries",
    "Battery thermal/energy",
    "Antenna matching",
    "USB-C CC",
    "4G burst power",
    "Motor transient power",
    "Low-power design",
    "EMC/EMI",
    "Safety (electrical)",
    "Thermal management",
    "DFM/DFT readiness",
    "Firmware-HW co-verification",
    "Component availability (sourcing)",
    "CERE/project power baseline",
)


def _escape(value):
    """Escape text before inserting it into HTML or inline SVG."""
    return html_lib.escape("" if value is None else str(value), quote=True)


def _slug(value):
    """Create a stable, attribute-safe fragment identifier."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value).strip().lower()).strip("-")
    return slug or "unknown"


def generate_radar_chart_svg(dimensions, max_size=400):
    """Generate an SVG radar chart for dimension scores."""
    n = len(dimensions)
    if n < 3:
        return ""

    cx, cy = max_size // 2, max_size // 2
    radius = max_size // 2 - 60
    angle_step = 360 / n

    # Grid circles
    grid_levels = [0.25, 0.5, 0.75, 1.0]
    grid_circles = ""
    for level in grid_levels:
        r = radius * level
        grid_circles += f'<circle cx="{cx}" cy="{cy}" r="{r:.0f}" fill="none" stroke="#ddd" stroke-width="1"/>\n'

    # Axis lines and labels
    axis_lines = ""
    labels = ""
    data_points = ""
    for i, dim in enumerate(dimensions):
        angle = -90 + i * angle_step  # Start from top
        rad = math.radians(angle)
        x_end = cx + radius * math.cos(rad)
        y_end = cy + radius * math.sin(rad)
        axis_lines += f'<line x1="{cx}" y1="{cy}" x2="{x_end:.1f}" y2="{y_end:.1f}" stroke="#ccc" stroke-width="1"/>\n'

        lx = cx + (radius + 25) * math.cos(rad)
        ly = cy + (radius + 25) * math.sin(rad)
        raw_name = str(dim.get("name", ""))
        label_text = raw_name[:12] + ("..." if len(raw_name) > 12 else "")
        label_text = _escape(label_text)
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#666">{label_text}</text>\n'

        score_ratio = dim.get("score", 0) / dim.get("max_score", 100) if dim.get("max_score", 0) > 0 else 0
        px = cx + radius * score_ratio * math.cos(rad)
        py = cy + radius * score_ratio * math.sin(rad)
        data_points += f"{px:.1f},{py:.1f} "

    # Data polygon
    points_str = data_points.strip()
    polygon = f'<polygon points="{points_str}" fill="rgba(33,150,243,0.2)" stroke="#2196f3" stroke-width="2"/>\n'

    # Data points
    point_circles = ""
    for i, dim in enumerate(dimensions):
        angle = -90 + i * angle_step
        rad = math.radians(angle)
        score_ratio = dim.get("score", 0) / dim.get("max_score", 100) if dim.get("max_score", 0) > 0 else 0
        px = cx + radius * score_ratio * math.cos(rad)
        py = cy + radius * score_ratio * math.sin(rad)
        point_circles += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#2196f3"/>\n'

    svg = f'''<svg width="{max_size}" height="{max_size}" viewBox="0 0 {max_size} {max_size}" xmlns="http://www.w3.org/2000/svg">
{grid_circles}
{axis_lines}
{polygon}
{point_circles}
{labels}
</svg>'''
    return svg


def generate_bar_chart_svg(summary, width=350, height=200):
    """Generate a bar chart for finding distribution."""
    critical = summary.get("critical_count", 0)
    warning = summary.get("warning_count", 0)
    info = summary.get("info_count", 0)

    max_val = max(critical, warning, info, 1)
    bar_height = 140
    bar_width = 60
    gap = 30
    x_start = 50

    bars = ""
    labels = ""
    values = ""
    colors = ["#e74c3c", "#f39c12", "#27ae60"]
    data = [("Critical", critical, colors[0]), ("Warning", warning, colors[1]), ("Info", info, colors[2])]

    for i, (label, val, color) in enumerate(data):
        x = x_start + i * (bar_width + gap)
        h = (val / max_val) * bar_height
        y = bar_height + 30 - h
        bars += f'<rect x="{x}" y="{y:.0f}" width="{bar_width}" height="{h:.0f}" fill="{color}" rx="4"/>\n'
        labels += f'<text x="{x + bar_width/2:.0f}" y="{bar_height + 50}" text-anchor="middle" font-size="11" fill="#666">{label}</text>\n'
        values += f'<text x="{x + bar_width/2:.0f}" y="{y - 8:.0f}" text-anchor="middle" font-size="14" font-weight="bold" fill="{color}">{val}</text>\n'

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
<text x="{width/2:.0f}" y="20" text-anchor="middle" font-size="12" font-weight="bold" fill="#333">Findings Distribution</text>
{bars}
{values}
{labels}
</svg>'''
    return svg


def render_finding(finding, idx):
    """Render a single finding as HTML."""
    sev = finding.get("severity", "info")
    cfg = SEVERITY_CONFIG.get(sev, SEVERITY_CONFIG["info"])
    loc = _escape(finding.get("location", ""))
    rec = _escape(finding.get("recommendation", ""))
    title = _escape(finding.get("title", "Untitled"))
    description = _escape(finding.get("description", ""))

    loc_html = f'<div class="finding-loc"><strong>Location:</strong> {loc}</div>' if loc else ""
    rec_html = f'<div class="finding-rec"><strong>Recommendation:</strong> {rec}</div>' if rec else ""

    return f'''
    <div class="finding" style="border-left: 4px solid {cfg['color']}; background: {cfg['bg']};">
        <div class="finding-header">
            <span class="severity-badge" style="background: {cfg['color']};">{cfg['icon']} {cfg['label']}</span>
            <span class="finding-title">{title}</span>
        </div>
        <div class="finding-desc">{description}</div>
        {loc_html}
        {rec_html}
    </div>
    '''


def render_dimension_card(dim):
    """Render a dimension score card."""
    raw_grade = str(dim.get("grade", "N/A"))
    grade = _escape(raw_grade)
    grade_color = GRADE_COLORS.get(raw_grade, "#999")
    grade_label = _escape(GRADE_LABELS.get(raw_grade, ""))
    score = dim.get("score", 0)
    max_score = dim.get("max_score", 100)
    category = dim.get("category", "general")
    cat_label = _escape(CATEGORY_LABELS.get(category, category))
    dimension_name = str(dim.get("name", "Unknown Dimension"))
    dimension_id = _slug(dimension_name)
    findings = dim.get("findings", [])

    critical = sum(1 for f in findings if f.get("severity") == "critical")
    warning = sum(1 for f in findings if f.get("severity") == "warning")
    info = sum(1 for f in findings if f.get("severity") == "info")

    findings_html = "".join(render_finding(f, i) for i, f in enumerate(findings))

    return f'''
    <div class="dimension-card" id="dim-{dimension_id}">
        <div class="dimension-header">
            <div class="dimension-info">
                <span class="category-tag">{cat_label}</span>
                <h2>{_escape(dimension_name)}</h2>
            </div>
            <div class="dimension-grade" style="border-color: {grade_color};">
                <div class="grade-letter" style="color: {grade_color};">{grade}</div>
                <div class="grade-label">{grade_label}</div>
            </div>
        </div>
        <div class="dimension-stats">
            <div class="stat-item">
                <span class="stat-value">{score}/{max_score}</span>
                <span class="stat-label">Score</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" style="color: #e74c3c;">{critical}</span>
                <span class="stat-label">Critical</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" style="color: #f39c12;">{warning}</span>
                <span class="stat-label">Warnings</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" style="color: #27ae60;">{info}</span>
                <span class="stat-label">Info</span>
            </div>
        </div>
        <div class="findings-list">
            {findings_html if findings_html else '<p class="no-findings">No findings recorded for this dimension.</p>'}
        </div>
    </div>
    '''


def render_i2c_map(data):
    """Render an I2C address-map as a single hierarchical table
    (bus ▸ root device/MUX/PCA ▸ sub-segment ▸ mounted device) from data['i2c_map']['tree'].
    Hierarchy is rendered with real table rows + indentation (padding-left by depth),
    NOT ASCII connectors. Each row stays on a single line (white-space: nowrap)."""
    i2c = data.get("i2c_map")
    if not i2c:
        return ""
    note = _escape(i2c.get("note", ""))
    tree = i2c.get("tree", [])

    level_badge = {"bus": "总线", "device": "器件", "segment": "子段"}

    def walk(nodes, depth=0):
        rows = []
        for node in nodes:
            rows.append((node, depth))
            if node.get("children"):
                rows.extend(walk(node["children"], depth + 1))
        return rows

    rows_html = ""
    for node, depth in walk(tree):
        kind = node.get("kind", "device")
        safe_kind = kind if kind in level_badge else "device"
        label = _escape(node.get("label") or node.get("ref") or node.get("type", ""))
        ref = _escape(node.get("ref", ""))
        typ = _escape(node.get("type", ""))
        addr = _escape(node.get("addr", ""))
        role = _escape(node.get("role", ""))
        indent = depth * 22
        badge = f"<span class='lvl-badge lvl-{safe_kind}'>{_escape(level_badge.get(safe_kind, ''))}</span>"
        if safe_kind == "bus":
            rows_html += (
                f"<tr class='i2c-bus-row'>"
                f"<td class='tree'><span style='padding-left:{indent}px'>{badge} {label}</span></td>"
                f"<td colspan='4' class='bus-detail'>{_escape(node.get('detail', ''))}</td>"
                f"</tr>"
            )
        elif safe_kind == "segment":
            rows_html += (
                f"<tr class='i2c-seg-row'>"
                f"<td class='tree'><span style='padding-left:{indent}px'>{badge} {label}</span></td>"
                f"<td></td><td></td><td></td>"
                f"<td class='seg-role'>{role}</td>"
                f"</tr>"
            )
        else:
            rows_html += (
                f"<tr class='i2c-dev-row'>"
                f"<td class='tree'><span style='padding-left:{indent}px'>{badge} {label}</span></td>"
                f"<td class='ref'>{ref}</td>"
                f"<td class='type'>{typ}</td>"
                f"<td class='addr'>{addr}</td>"
                f"<td class='role'>{role}</td>"
                f"</tr>"
            )

    return f"""
    <div class="i2c-section">
        <h3>&#128290; I2C 地址映射表 (netlist 逐脚解析 · 隶属关系)</h3>
        {f'<p class="i2c-note">{note}</p>' if note else ''}
        <div class="i2c-table-wrap">
        <table class="i2c-tree-table">
            <thead><tr>
                <th>拓扑层级（总线 ▸ 根设备 ▸ 子段 ▸ 器件）</th>
                <th>位号</th><th>型号</th><th>地址</th><th>功能 / 挂载</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        </div>
    </div>"""


def render_i2c_topology(data):
    """Render an I2C topology diagram (SVG) from data['i2c_topology']['controllers'].
    Shows every configured controller and device, with mux fan-out annotated.
    Generated programmatically so coordinates stay correct."""
    topo = data.get("i2c_topology")
    if not topo:
        return ""
    controllers = topo.get("controllers", [])
    if not controllers:
        return ""

    col_w = 560
    gap = 40
    margin = 10
    node_h = 52
    node_gap = 16
    top = 56
    header_h = 44

    heights = []
    for c in controllers:
        n = len(c.get("nodes", []))
        heights.append(top + n * (node_h + node_gap) + 20)
    total_h = max(heights)
    svg_w = margin * 2 + len(controllers) * col_w + (len(controllers) - 1) * gap

    cols = []
    for i, c in enumerate(controllers):
        cx = margin + i * (col_w + gap)
        nodes = c.get("nodes", [])
        s = "<g>"
        s += f'<rect x="{cx}" y="0" width="{col_w}" height="{header_h}" rx="10" fill="#1f3a5f"/>'
        s += f'<text x="{cx+16}" y="19" font-size="15" font-weight="700" fill="#fff" font-family="monospace">{_escape(c.get("id", ""))}</text>'
        s += f'<text x="{cx+16}" y="36" font-size="11" fill="#cfe3ff">{_escape(c.get("pins", ""))}</text>'
        tag = "[共享]" if c.get("shared") else "[独立]"
        s += f'<text x="{cx+col_w-12}" y="19" font-size="11" fill="#9ecbff" text-anchor="end">{tag} {_escape(c.get("label", ""))}</text>'
        trunk_x = cx + 18
        s += f'<line x1="{trunk_x}" y1="{top-6}" x2="{trunk_x}" y2="{total_h-10}" stroke="#90a4c4" stroke-width="3"/>'
        box_x = cx + 34
        box_w = col_w - 50
        for j, nd in enumerate(nodes):
            y = top + j * (node_h + node_gap)
            my = y + node_h / 2
            s += f'<line x1="{trunk_x}" y1="{my}" x2="{box_x}" y2="{my}" stroke="#90a4c4" stroke-width="2"/>'
            fill = "#fff7e6" if nd.get("mux") else "#ffffff"
            stroke = "#e0a83c" if nd.get("mux") else "#cdd9e8"
            s += f'<rect x="{box_x}" y="{y}" width="{box_w}" height="{node_h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            ref = _escape(nd.get("ref", ""))
            typ = _escape(nd.get("type", ""))
            addr = _escape(nd.get("addr", ""))
            mux_tag = " ⟂MUX" if nd.get("mux") else ""
            s += f'<text x="{box_x+12}" y="{y+20}" font-size="13" font-weight="700" fill="#1f3a5f">{ref}  {typ}{mux_tag}</text>'
            s += f'<text x="{box_x+box_w-12}" y="{y+20}" font-size="13" font-weight="700" fill="#1565c0" text-anchor="end" font-family="monospace">{addr}</text>'
            s += f'<text x="{box_x+12}" y="{y+40}" font-size="11" fill="#555">{_escape(nd.get("role", ""))}</text>'
        s += "</g>"
        cols.append(s)

    svg = (
        f'<svg viewBox="0 0 {svg_w} {total_h}" width="100%" '
        f'style="max-width:{svg_w}px;margin:0 auto;display:block;" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(cols)}</svg>'
    )

    title = _escape(topo.get("title", "I2C 拓扑架构图"))
    note = _escape(topo.get("note", ""))
    return f"""
    <div class="i2c-topo-section">
        <h3>&#128760; {title}</h3>
        {f'<p class="i2c-note">{note}</p>' if note else ''}
        <div class="i2c-topo-wrap">{svg}</div>
    </div>"""


def render_conclusion(data):
    """Render a consolidated 'final conclusion' section from data['conclusion']."""
    c = data.get("conclusion")
    if not c:
        return ""
    verdict = _escape(c.get("verdict", ""))
    compliance = _escape(c.get("prd_compliance", ""))
    confirmed = c.get("confirmed_real", [])
    retracted = c.get("retracted_false_alarms", [])
    deviations = c.get("prd_deviations", [])
    must_fix = c.get("must_fix_before_tapeout", [])

    def lst(items):
        return "".join(f"<li>{_escape(x)}</li>" for x in items)

    conf_html = lst(confirmed)
    retr_html = lst(retracted)
    dev_html = lst(deviations)
    fix_html = lst(must_fix)

    return f"""
    <div class="conclusion-section">
        <h3>&#128203; 最终审查结论 (Final Conclusion)</h3>
        <div class="conclusion-verdict">
            <div class="verdict-text">{verdict}</div>
            <div class="compliance-badge">PRD 符合性：{compliance}</div>
        </div>
        <div class="conclusion-grid">
            <div class="concl-card real-card">
                <h4>&#9989; 已核实为真 / 结论确认</h4>
                <ul>{conf_html}</ul>
            </div>
            <div class="concl-card retract-card">
                <h4>&#8633; 已撤销的误判 (False Alarms)</h4>
                <ul>{retr_html}</ul>
            </div>
            <div class="concl-card dev-card">
                <h4>&#9888; 须闭环的 PRD 一致性偏离</h4>
                <ul>{dev_html}</ul>
            </div>
            <div class="concl-card fix-card">
                <h4>&#128296; 投板前必须修复 (Must-Fix)</h4>
                <ul>{fix_html}</ul>
            </div>
        </div>
    </div>"""


def render_coverage(data):
    """Render the mandatory/conditional review coverage table."""
    coverage = data.get("coverage")
    if coverage is None:
        coverage = [
            {
                "check": check,
                "trigger": "Coverage data was not supplied",
                "status": "not verifiable",
                "evidence": "Add explicit evidence or not-applicable rationale",
            }
            for check in MANDATORY_COVERAGE_CHECKS
        ]
    elif not coverage:
        return ""
    if isinstance(coverage, dict):
        rows = []
        for check, details in coverage.items():
            details = details if isinstance(details, dict) else {"status": details}
            rows.append({"check": check, **details})
    else:
        rows = coverage

    status_classes = {
        "confirmed": "coverage-confirmed",
        "finding": "coverage-finding",
        "not applicable": "coverage-na",
        "not verifiable": "coverage-unverified",
    }
    rows_html = ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "not verifiable"))
        status_class = status_classes.get(status.lower(), "coverage-unverified")
        rows_html += (
            f"<tr><td>{_escape(row.get('check', ''))}</td>"
            f"<td>{_escape(row.get('trigger', ''))}</td>"
            f"<td><span class='coverage-status {status_class}'>{_escape(status)}</span></td>"
            f"<td>{_escape(row.get('evidence', row.get('location', '')))}</td></tr>"
        )
    if not rows_html:
        return ""
    return f"""
    <div class="coverage-section">
        <h3>&#9989; Review Coverage</h3>
        <p class="coverage-note">Mandatory evidence and feature-triggered checks considered for this review.</p>
        <div class="coverage-table-wrap">
        <table class="coverage-table">
            <thead><tr><th>Check</th><th>Trigger / Evidence Expected</th><th>Status</th><th>Evidence / Finding Location</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        </div>
    </div>"""


def _cap_grade(grade, ceiling):
    """Return grade, lowered so it is not better than ceiling. Unknown letters become ceiling."""
    order = ("D", "C", "B", "A", "S")
    grade = str(grade or "").strip().upper()
    ceiling = ceiling.upper()
    if grade not in order:
        return ceiling
    if order.index(grade) > order.index(ceiling):
        return ceiling
    return grade


def _findings_include_critical(findings):
    for finding in findings or []:
        if isinstance(finding, dict) and str(finding.get("severity", "")).lower() == "critical":
            return True
    return False


def apply_grade_policy(data):
    """One rule for letters and Critical findings.

    Score still maps 90/80/65/50 to S/A/B/C. After that mapping, any Critical
    finding caps that dimension at C, and any Critical anywhere or any dimension
    D caps the overall letter at C. A letter that is already D stays D.
    """
    any_critical = False
    any_d = False
    notes = []
    for dim in data.get("dimensions") or []:
        if not isinstance(dim, dict):
            continue
        name = dim.get("name", "dimension")
        if _findings_include_critical(dim.get("findings")):
            any_critical = True
            capped = _cap_grade(dim.get("grade"), "C")
            previous = str(dim.get("grade", "")).strip().upper()
            if capped != previous:
                notes.append(f"{name}: {previous or 'unset'} → C (Critical present)")
                dim["grade"] = capped
        if str(dim.get("grade", "")).strip().upper() == "D":
            any_d = True
    if any_critical or any_d:
        previous = str(data.get("overall_grade", "")).strip().upper()
        capped = _cap_grade(data.get("overall_grade"), "C")
        if capped != previous:
            reason = "Critical finding" if any_critical else "dimension grade D"
            notes.append(f"overall: {previous or 'unset'} → C ({reason})")
            data["overall_grade"] = capped
    if notes:
        data["grade_policy_notes"] = notes
    return data


def generate_html_report(data):
    """Generate the complete HTML report."""
    apply_grade_policy(data)
    project = _escape(data.get("project_name", "EE Design Review"))
    review_date = _escape(data.get("review_date", datetime.now().strftime("%Y-%m-%d")))
    reviewer = _escape(data.get("reviewer", "EE Review Skill"))
    input_files = data.get("input_files", [])
    raw_overall_grade = str(data.get("overall_grade", "N/A"))
    overall_grade = _escape(raw_overall_grade)
    overall_summary = _escape(data.get("overall_summary", ""))
    dimensions = data.get("dimensions", [])
    summary = data.get("summary", {})

    grade_color = GRADE_COLORS.get(raw_overall_grade, "#999")
    grade_label = _escape(GRADE_LABELS.get(raw_overall_grade, ""))
    policy_notes = data.get("grade_policy_notes") or []
    policy_html = ""
    if policy_notes:
        items = "".join(f"<li>{_escape(note)}</li>" for note in policy_notes)
        policy_html = f"<ul class=\"grade-policy\">{items}</ul>"

    # Charts
    radar_svg = generate_radar_chart_svg(dimensions) if len(dimensions) >= 3 else ""
    bar_svg = generate_bar_chart_svg(summary) if summary else ""

    # Dimension cards
    dim_cards_html = "".join(render_dimension_card(d) for d in dimensions)

    # Dimension nav
    dim_nav_html = "".join(
        f'<a href="#dim-{_slug(d.get("name", "unknown"))}">{_escape(d.get("name", "Unknown"))}</a>'
        for d in dimensions
    )

    # Input files
    files_html = "".join(f'<li>{_escape(f)}</li>' for f in input_files)

    # I2C map section
    i2c_html = render_i2c_map(data)

    # I2C topology diagram
    topo_html = render_i2c_topology(data)

    # Final conclusion section
    conclusion_html = render_conclusion(data)

    # Mandatory and conditional coverage section
    coverage_html = render_coverage(data)

    # Top risks
    top_risks = summary.get("top_risks", [])
    top_risks_html = "".join(f"<li>{_escape(r)}</li>" for r in top_risks)

    # Recommendations
    recommendations = summary.get("recommendations", [])
    rec_html = "".join(f"<li>{_escape(r)}</li>" for r in recommendations)

    # Summary stats
    total = summary.get("total_findings", 0)
    critical = summary.get("critical_count", 0)
    warning = summary.get("warning_count", 0)
    info = summary.get("info_count", 0)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project} - EE Design Review Report</title>
    <style>
        :root {{
            --bg: #f5f7fa;
            --card-bg: #ffffff;
            --text: #2c3e50;
            --text-light: #7f8c8d;
            --border: #e0e6ed;
            --accent: #2196f3;
            --shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}

        /* Header */
        .report-header {{
            background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #3949ab 100%);
            color: white;
            padding: 40px 24px;
            border-radius: 16px;
            margin-bottom: 24px;
        }}
        .report-header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .report-meta {{ display: flex; gap: 24px; flex-wrap: wrap; font-size: 14px; opacity: 0.9; }}
        .report-meta span {{ display: inline-flex; align-items: center; gap: 6px; }}

        /* Overall Score Card */
        .overall-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 32px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 32px;
            flex-wrap: wrap;
        }}
        .overall-grade-circle {{
            width: 120px; height: 120px;
            border-radius: 50%;
            border: 6px solid {grade_color};
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            flex-shrink: 0;
        }}
        .overall-grade-circle .letter {{ font-size: 48px; font-weight: 800; color: {grade_color}; line-height: 1; }}
        .overall-grade-circle .label {{ font-size: 12px; color: var(--text-light); margin-top: 4px; }}
        .overall-summary-text {{ flex: 1; min-width: 300px; }}
        .overall-summary-text h2 {{ font-size: 20px; margin-bottom: 12px; }}
        .overall-summary-text p {{ color: var(--text-light); font-size: 14px; }}

        /* Stats Bar */
        .stats-bar {{
            display: flex; gap: 16px; flex-wrap: wrap;
            margin-bottom: 24px;
        }}
        .stat-box {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px 24px;
            flex: 1; min-width: 140px;
            box-shadow: var(--shadow);
            text-align: center;
        }}
        .stat-box .num {{ font-size: 32px; font-weight: 800; }}
        .stat-box .lbl {{ font-size: 13px; color: var(--text-light); margin-top: 4px; }}

        /* Charts Section */
        .charts-section {{
            display: flex; gap: 24px; flex-wrap: wrap;
            margin-bottom: 24px;
        }}
        .chart-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow);
            flex: 1; min-width: 360px;
        }}
        .chart-card h3 {{ font-size: 16px; margin-bottom: 16px; color: var(--text); }}
        .chart-card svg {{ display: block; margin: 0 auto; }}

        /* Top Risks & Recommendations */
        .insights-grid {{
            display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 768px) {{ .insights-grid {{ grid-template-columns: 1fr; }} }}
        .insight-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            box-shadow: var(--shadow);
        }}
        .insight-card h3 {{ font-size: 16px; margin-bottom: 16px; }}
        .insight-card ul {{ list-style: none; padding: 0; }}
        .insight-card li {{
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
            display: flex; gap: 8px;
        }}
        .insight-card li:last-child {{ border-bottom: none; }}
        .risk-card li::before {{ content: "\\26A0"; color: #f39c12; }}
        .rec-card li::before {{ content: "\\2705"; }}

        /* Dimension Nav */
        .dim-nav {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 24px;
            box-shadow: var(--shadow);
            display: flex; gap: 16px; flex-wrap: wrap;
        }}
        .dim-nav a {{
            text-decoration: none;
            color: var(--accent);
            font-size: 14px;
            font-weight: 500;
        }}
        .dim-nav a:hover {{ text-decoration: underline; }}

        /* Dimension Card */
        .dimension-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 28px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
        }}
        .dimension-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; flex-wrap: wrap; gap: 16px;
        }}
        .dimension-info h2 {{ font-size: 20px; margin-top: 8px; }}
        .category-tag {{
            display: inline-block;
            background: #e8eaf6; color: #3f51b5;
            padding: 3px 10px; border-radius: 4px;
            font-size: 11px; font-weight: 600; text-transform: uppercase;
        }}
        .dimension-grade {{
            border: 3px solid #999;
            border-radius: 12px;
            padding: 12px 20px; text-align: center;
            min-width: 80px;
        }}
        .grade-letter {{ font-size: 36px; font-weight: 800; line-height: 1; }}
        .grade-label {{ font-size: 11px; color: var(--text-light); margin-top: 4px; }}

        .dimension-stats {{
            display: flex; gap: 24px; margin-bottom: 20px; flex-wrap: wrap;
        }}
        .stat-item {{ display: flex; flex-direction: column; }}
        .stat-item .stat-value {{ font-size: 22px; font-weight: 700; }}
        .stat-item .stat-label {{ font-size: 12px; color: var(--text-light); }}

        /* Findings */
        .findings-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .no-findings {{ color: var(--text-light); font-style: italic; padding: 16px 0; }}
        .finding {{
            padding: 16px;
            border-radius: 8px;
        }}
        .finding-header {{
            display: flex; align-items: center; gap: 12px; margin-bottom: 8px;
            flex-wrap: wrap;
        }}
        .severity-badge {{
            color: white; padding: 3px 10px;
            border-radius: 4px; font-size: 11px; font-weight: 600;
        }}
        .finding-title {{ font-weight: 600; font-size: 15px; }}
        .finding-desc {{ font-size: 14px; color: var(--text); margin-bottom: 6px; }}
        .finding-loc, .finding-rec {{ font-size: 13px; color: var(--text-light); margin-top: 4px; }}

        /* Input Files */
        .input-files {{
            background: var(--card-bg);
            border-radius: 12px; padding: 20px 24px;
            margin-bottom: 24px; box-shadow: var(--shadow);
        }}
        .input-files h3 {{ font-size: 15px; margin-bottom: 12px; }}
        .input-files ul {{ list-style: none; }}
        .input-files li {{
            padding: 6px 0; font-size: 14px;
            color: var(--text-light);
        }}
        .input-files li::before {{ content: "\\1F4C4  "; }}

        /* Mandatory / Conditional Coverage */
        .coverage-section {{ background: var(--card-bg); border-radius: 16px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px; }}
        .coverage-section h3 {{ font-size: 16px; margin-bottom: 6px; }}
        .coverage-note {{ color: var(--text-light); font-size: 12.5px; margin-bottom: 14px; }}
        .coverage-table-wrap {{ width: 100%; overflow-x: auto; }}
        .coverage-table {{ border-collapse: collapse; width: 100%; min-width: 760px; font-size: 13px; }}
        .coverage-table th, .coverage-table td {{ border: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; }}
        .coverage-table th {{ background: #f0f4f8; color: #455a75; font-weight: 600; }}
        .coverage-status {{ display: inline-block; border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: 700; white-space: nowrap; }}
        .coverage-confirmed {{ background: #eafaf1; color: #1f8a4c; }}
        .coverage-finding {{ background: #fdeaea; color: #c0392b; }}
        .coverage-na {{ background: #eef1f4; color: #596775; }}
        .coverage-unverified {{ background: #fff4e0; color: #b76e00; }}

        /* I2C Map Section */
        .i2c-section {{ background: var(--card-bg); border-radius: 16px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px; }}
        .i2c-section h3 {{ font-size: 16px; margin-bottom: 12px; }}
        .i2c-note {{ font-size: 12.5px; color: var(--text-light); line-height: 1.6; margin-bottom: 14px; background: #f7f9fc; border-left: 3px solid var(--accent); padding: 10px 14px; border-radius: 6px; }}
        .i2c-table-wrap {{ width: 100%; overflow-x: auto; }}
        .i2c-tree-table {{ border-collapse: collapse; font-size: 13px; min-width: 920px; }}
        .i2c-tree-table th, .i2c-tree-table td {{ border: 1px solid var(--border); padding: 7px 12px; text-align: left; vertical-align: middle; white-space: nowrap; }}
        .i2c-tree-table th {{ background: #f0f4f8; font-weight: 600; color: #455a75; }}
        .i2c-tree-table td.tree {{ color: #2c3e50; }}
        .i2c-tree-table td.ref, .i2c-tree-table td.type {{ color: #455a75; }}
        .i2c-tree-table td.addr {{ font-family: 'SFMono-Regular', Consolas, monospace; font-weight: 700; color: var(--accent); }}
        .i2c-tree-table td.role, .i2c-tree-table td.seg-role {{ color: var(--text); white-space: normal; min-width: 280px; }}
        .lvl-badge {{ display: inline-block; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 1px 6px; margin-right: 6px; vertical-align: middle; }}
        .lvl-bus {{ background: #1f3a5f; color: #fff; }}
        .i2c-topo-section {{ background: var(--card-bg); border-radius: 16px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px; }}
        .i2c-topo-section h3 {{ font-size: 16px; margin-bottom: 12px; }}
        .i2c-topo-wrap {{ width: 100%; overflow-x: auto; }}
        .i2c-topo-wrap svg {{ min-width: 760px; }}
        .lvl-device {{ background: #e3ecf7; color: #2b6cb0; }}
        .lvl-segment {{ background: #fff3e0; color: #c77700; }}
        .i2c-bus-row {{ background: #1f3a5f; }}
        .i2c-bus-row td.tree span {{ color: #fff; font-weight: 700; }}
        .i2c-bus-row td.bus-detail {{ color: #cfe3ff; font-size: 12.5px; font-weight: 500; }}
        .i2c-seg-row {{ background: #eef4fb; }}
        .i2c-seg-row td.tree span {{ color: #2b6cb0; font-weight: 600; }}
        .i2c-dev-row:nth-child(even) {{ background: #fafcfe; }}

        /* Final Conclusion */
        .conclusion-section {{ background: var(--card-bg); border-radius: 16px; padding: 24px; box-shadow: var(--shadow); margin-bottom: 24px; border-left: 5px solid var(--accent); }}
        .conclusion-section h3 {{ font-size: 16px; margin-bottom: 16px; }}
        .conclusion-verdict {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: center; background: #f7f9fc; border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; margin-bottom: 18px; }}
        .verdict-text {{ flex: 1 1 320px; font-size: 14px; line-height: 1.6; color: var(--text); }}
        .compliance-badge {{ flex: 0 0 auto; background: #fff4e0; color: #b76e00; border: 1px solid #ffd591; border-radius: 999px; padding: 8px 16px; font-weight: 700; font-size: 13px; white-space: nowrap; }}
        .conclusion-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .concl-card {{ border-radius: 12px; padding: 16px; border: 1px solid var(--border); }}
        .concl-card h4 {{ font-size: 13.5px; margin-bottom: 10px; }}
        .concl-card ul {{ margin: 0; padding-left: 18px; }}
        .concl-card li {{ font-size: 12.5px; line-height: 1.55; margin-bottom: 6px; }}
        .real-card {{ background: #eafaf0; border-color: #b7ebc8; }}
        .real-card h4 {{ color: #1f8a4c; }}
        .retract-card {{ background: #f3f0ff; border-color: #d3c9ff; }}
        .retract-card h4 {{ color: #6b4cff; }}
        .dev-card {{ background: #fff8e8; border-color: #ffe1a8; }}
        .dev-card h4 {{ color: #b76e00; }}
        .fix-card {{ background: #fdecec; border-color: #f6b8b8; }}
        .fix-card h4 {{ color: #c0392b; }}
        @media (max-width: 768px) {{ .conclusion-grid {{ grid-template-columns: 1fr; }} }}

        /* Footer */
        .report-footer {{
            text-align: center; padding: 32px;
            color: var(--text-light); font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <h1>{project}</h1>
            <div class="report-meta">
                <span>&#128197; {review_date}</span>
                <span>&#128100; {reviewer}</span>
                <span>&#128202; {len(dimensions)} Review Dimensions</span>
            </div>
        </div>

        <!-- Overall Score -->
        <div class="overall-card">
            <div class="overall-grade-circle">
                <div class="letter">{overall_grade}</div>
                <div class="label">{grade_label}</div>
            </div>
            <div class="overall-summary-text">
                <h2>Overall Assessment</h2>
                <p>{overall_summary}</p>
                {policy_html}
            </div>
        </div>

        <!-- Stats Bar -->
        <div class="stats-bar">
            <div class="stat-box">
                <div class="num">{total}</div>
                <div class="lbl">Total Findings</div>
            </div>
            <div class="stat-box">
                <div class="num" style="color: #e74c3c;">{critical}</div>
                <div class="lbl">Critical Issues</div>
            </div>
            <div class="stat-box">
                <div class="num" style="color: #f39c12;">{warning}</div>
                <div class="lbl">Warnings</div>
            </div>
            <div class="stat-box">
                <div class="num" style="color: #27ae60;">{info}</div>
                <div class="lbl">Info / Suggestions</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="charts-section">
            <div class="chart-card">
                <h3>Dimension Score Radar</h3>
                {radar_svg if radar_svg else '<p style="color:#999;text-align:center;padding:40px;">Not enough dimensions for radar chart (minimum 3 required).</p>'}
            </div>
            <div class="chart-card">
                <h3>Findings Distribution</h3>
                {bar_svg if bar_svg else '<p style="color:#999;text-align:center;padding:40px;">No summary data available.</p>'}
            </div>
        </div>

        <!-- Top Risks & Recommendations -->
        <div class="insights-grid">
            <div class="insight-card risk-card">
                <h3>&#9888; Top Risks</h3>
                <ul>{top_risks_html if top_risks_html else '<li>No critical risks identified.</li>'}</ul>
            </div>
            <div class="insight-card rec-card">
                <h3>&#9989; Key Recommendations</h3>
                <ul>{rec_html if rec_html else '<li>No specific recommendations.</li>'}</ul>
            </div>
        </div>

        <!-- Input Files -->
        {f'<div class="input-files"><h3>&#128206; Reviewed Files</h3><ul>{files_html}</ul></div>' if files_html else ''}

        <!-- Mandatory / Conditional Review Coverage -->
        {coverage_html if coverage_html else ''}

        <!-- I2C Address Map -->
        {i2c_html if i2c_html else ''}

        <!-- I2C Topology -->
        {topo_html if topo_html else ''}

        <!-- Final Conclusion -->
        {conclusion_html if conclusion_html else ''}

        <!-- Dimension Nav -->
        {f'<div class="dim-nav">{dim_nav_html}</div>' if dim_nav_html else ''}

        <!-- Dimension Cards -->
        {dim_cards_html}

        <!-- Footer -->
        <div class="report-footer">
            <p>Generated by EE Review Skill | {review_date}</p>
        </div>
    </div>
</body>
</html>'''
    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_report.py <input.json> [output.html]")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = generate_html_report(data)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = os.path.splitext(input_path)[0] + "_report.html"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()
