# BOM Review Checklist

## 1. Component Availability & Lifecycle (器件可采购性 & 生命周期)

### 1.1 Lifecycle Status
- Verify each part is in "Active" production status (not NRND / EOL / Obsolete).
- Check manufacturer end-of-life (EOL) notices for all critical components.
- Confirm last-time-buy (LTB) dates for parts approaching EOL.
- Verify recommended replacement parts are documented for NRND items.
- Check manufacturer health / supply chain risk for sole-source components.

### 1.2 Lead Time & Stock
- Verify lead time is acceptable for production schedule (target: < 16 weeks).
- Check distributor stock levels (DigiKey, Mouser, Arrow, Avnet, LCSC, etc.).
- Confirm minimum order quantity (MOQ) is reasonable for production volume.
- Verify multi-distributor availability (at least 2 authorized distributors).

### 1.3 Lifecycle Status Quick Reference
| Status | Action | Risk Level |
|--------|--------|------------|
| Active | Proceed | Low |
| Not Recommended for New Design (NRND) | Find alternative | Medium |
| End of Life (EOL) - scheduled | Plan LTB + redesign | High |
| Obsolete | Immediate redesign required | Critical |

---

## 2. Second Source & Alternatives (第二货源)

### 2.1 Pin-to-Pin Compatible Alternatives
- Verify second source exists for all critical ICs (processor, regulator, memory).
- Check pin-to-pin compatibility of alternative parts (same package, same pinout).
- Confirm electrical parameter match for alternative components.
- Document approved vendor list (AVL) for each component category.

### 2.2 Parameter-Based Substitution
- Identify components where exact second source is unavailable.
- Verify functional equivalents with compatible electrical parameters.
- Check package and footprint compatibility for substitutes.
- Document any PCB or BOM changes required for substitute parts.

### 2.3 Passive Component Standardization
- Verify resistor/capacitor values follow preferred number series (E12/E24).
- Check for non-standard values that could cause sourcing issues.
- Confirm component tolerance is appropriate (5% vs 1% vs 0.1%).
- Verify package size standardization (minimize unique footprint count).

---

## 3. Part Number Accuracy (型号准确性)

### 3.1 Manufacturer Part Number (MPN)
- Verify MPN format is complete (including package, temperature grade, packing).
- Check for truncated or ambiguous part numbers (e.g., missing suffix).
- Confirm MPN matches manufacturer datasheet specification.
- Verify manufacturer name is correctly spelled and identified.

### 3.2 Description Completeness
- Check each BOM line has adequate description (value, package, tolerance, voltage).
- Verify capacitor entries include: capacitance, voltage rating, tolerance, dielectric, package.
- Verify resistor entries include: resistance, power rating, tolerance, package.
- Verify IC entries include: function, package, temperature grade.
- Confirm inductor entries include: inductance, current rating, DCR, package.

### 3.3 Reference Designator Consistency
- Verify reference designators (R1, C3, U5, etc.) match between BOM and schematic.
- Check no duplicate or missing reference designators.
- Confirm designator numbering follows logical sequence.
- Verify multi-part components (e.g., dual op-amp) have correct part designators.

---

## 4. Parameter Verification (参数匹配性)

### 4.1 Electrical Parameter Cross-Check
- Verify component parameters match design requirements from schematic.
- Check capacitor voltage rating >= 1.5x operating voltage (rule of thumb).
- Verify resistor power rating >= 1.5x calculated dissipation.
- Confirm inductor saturation current >= 1.3x peak operating current.
- Check MOSFET Vds / Id / Rds(on) / gate charge vs. circuit requirements.

### 4.2 Environmental & Rating
- Verify operating temperature range matches application requirements.
- Check component temperature grade:
  - Commercial: 0C to +70C
  - Industrial: -40C to +85C
  - Automotive: -40C to +125C (AEC-Q100)
  - Military: -55C to +125C
- Confirm moisture sensitivity level (MSL) is documented and managed.
- Verify AEC-Q100 qualification for automotive applications.

### 4.3 Compliance & Certification
- Verify RoHS / REACH compliance for all components.
- Check for lead-free / halogen-free requirements.
- Confirm safety-certified components (UL, VDE, CSA) where required.
- Verify components meet applicable standards (USB-IF, HDMI, PCI-SIG, etc.).

---

## 5. Package & Footprint Verification (封装与焊盘验证)

### 5.1 Package Documentation
- Verify package type is explicitly documented for every component (e.g., 0603, SOIC-8, QFN-32, BGA-256).
- Check package designator matches manufacturer datasheet (e.g., SOIC vs SOIC-W vs TSSOP).
- Confirm IC package suffix in MPN matches actual package (e.g., STM32F103C8T6 vs STM32F103CBT6 - LQFP48 vs LQFP64).
- Verify lead pitch / ball pitch is documented for fine-pitch components (BGA, QFP).
- Check package body dimensions are specified (X x Y x Z in mm).

### 5.2 Footprint-to-Package Matching
- Cross-check BOM package type against PCB footprint library name for each component.
- Verify footprint pad layout matches component lead/ball pattern (pitch, count, position).
- Check pad size vs. component body size (pad should not extend beyond component body for SMD).
- Confirm thermal pad footprint matches QFN/DFN exposed pad dimensions.
- Verify BGA pad pattern (NSMD vs SMD) matches BGA ball type recommendation.
- Check for incorrect footprint assignment (e.g., 0805 resistor assigned 0603 footprint).

### 5.3 Package Thermal & Mechanical
- Verify package thermal resistance (theta-JA / theta-JC) is adequate for power dissipation.
- Check package material type (plastic vs. ceramic) for high-reliability applications.
- Confirm package weight is within pick-and-place machine capability.
- Verify package height / profile meets enclosure clearance requirements (Z-axis constraint).
- Check for component body interference with adjacent tall components.

### 5.4 Assembly Packaging
- Verify MSL (Moisture Sensitivity Level) is documented for each SMT component.
| MSL Level | Floor Life | Required Handling |
|-----------|-----------|-------------------|
| MSL 1 | Unlimited | No special handling |
| MSL 2 | 1 year | Dry storage recommended |
| MSL 3 | 168 hours | Dry pack + bake if exposed |
| MSL 4 | 72 hours | Dry pack + track exposure time |
| MSL 5 | 48 hours | Dry pack + strict exposure tracking |
| MSL 5a | 24 hours | Dry pack + immediate use after opening |
| MSL 6 | Time on label | Must bake before use, use immediately |
- Confirm tape & reel / tray / tube / bulk packaging format is specified.
- Verify reel quantity and component orientation (pin 1 direction) for pick-and-place.
- Check leader/trailer length for tape & reel meets assembly equipment requirements.

### 5.5 Package Alternatives & Compatibility
- Identify components available in multiple package options (same die, different package).
- Verify if footprint supports package migration (e.g., SOIC-8 to TSSOP-8, 0805 to 0603).
- Check for drop-in compatible packages from alternative manufacturers.
- Document package change impact on PCB layout (pad pattern, courtyard, routing).

---

## 6. Cost Analysis (成本分析)

### 5.1 Cost Optimization
- Review unit cost at production volume target.
- Identify high-cost components and explore alternatives.
- Check for over-specified components (tighter tolerance / higher grade than needed).
- Verify cost-effective package selection (e.g., QFN vs. BGA for same function).

### 5.2 Cost Risk Assessment
| Cost Factor | Risk Indicator | Action |
|-------------|---------------|--------|
| Sole-source IC | Single supplier dependency | Find second source |
| Custom component | Long lead time, high NRE | Standardize where possible |
| Tight tolerance (<0.1%) | Price premium | Verify if truly needed |
| High-voltage / high-power | Premium pricing | Check alternative topologies |
| Low-volume custom part | NRE + unit cost risk | Evaluate standard alternative |

---

## 7. BOM Structure & Format (BOM格式)

### 7.1 BOM Completeness
- Verify BOM includes: Item #, Qty, Reference Designator, MPN, Manufacturer, Description, Package.
- Check for assembly-level notes (e.g., "Do not install" / "Option" items).
- Confirm quantity calculation is correct (per-board qty x boards per panel x panels).
- Verify level-of-assembly BOM structure (system > board > sub-assembly).

### 7.2 Version Control
- Verify BOM revision matches schematic/PCB revision.
- Check revision history / change log is maintained.
- Confirm approved vs. pending ECN (Engineering Change Notice) status.

---

## 8. Common BOM Issues (常见BOM问题)

| Issue | Severity | Description |
|-------|----------|-------------|
| EOL component in BOM | Critical | Will cause production halt when stock depleted |
| No second source for critical IC | Critical | Supply chain single-point-of-failure |
| Incomplete MPN | Warning | Ambiguous ordering, may receive wrong variant |
| Voltage rating insufficient | Critical | Capacitor failure / reliability risk |
| Tolerance not specified | Warning | May not meet circuit performance requirements |
| Non-standard value | Info | Sourcing difficulty, longer lead time |
| Mismatched ref designators | Critical | Assembly will produce wrong board |
| MSL not documented | Warning | Moisture damage during reflow |
| No temperature grade specified | Warning | Field failure in extreme conditions |
| Missing RoHS status | Info | Compliance documentation gap |
| Package type not documented | Critical | Wrong footprint assignment, assembly failure |
| Package suffix mismatch with MPN | Critical | Wrong package received (e.g., LQFP48 vs LQFP64) |
| Footprint-to-BOM package mismatch | Critical | Component body does not match PCB pad layout |
| No tape & reel spec | Info | Assembly equipment setup delay |
| Package height exceeds enclosure | Warning | Mechanical interference with enclosure |
