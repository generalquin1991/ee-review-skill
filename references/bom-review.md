# BOM review checks

Apply `references/review-contract.md`. Stock, price, lead time, and lifecycle are `not verifiable` unless this review fetched a distributor page or the user supplied a dated export. This skill has no distributor client. Do not fill those cells from memory.

When evidence exists, read it in this order: LCSC (szlcsc) first, then Digi-Key, Mouser, Arrow, Avnet. Quote the stock and lifecycle strings, the URL or filename, and the date. A miss at LCSC is not itself a finding; name the next source that is actually in the evidence and the price delta printed there.

## 1. Component availability and lifecycle

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Lifecycle of a major IC | MCU, radio, PMIC, memory, charger, or a sole connector | Fetched page or dated user export for the full MPN | Status shown is Active, or NRND with a second source named in the BOM | Status shown is EOL or Obsolete for that full MPN | critical when the page says Obsolete or EOL and no alternate is on the BOM; warning for NRND | The fetched page, not a recollection of the part |
| Stock and lead time | The same parts, and any part the user flagged as long-lead | The same page or export | The page shows stock that covers the stated build quantity, or a lead time the user accepted in writing | The page shows zero stock and lead time above 16 weeks for the build date | warning | Page stock and lead-time fields |
| MPN is orderable | Every BOM line for an assembled part | BOM manufacturer part number field | The MPN includes the ordering suffix (package, temperature, packing) and matches the manufacturer page you opened | The MPN is truncated, or the page's package suffix differs from the footprint | critical when the page shows a different package (for example LQFP48 vs LQFP64); warning when the suffix is simply missing | Manufacturer ordering guide |
| Second source | MCU, PMIC, memory, or a custom connector | BOM AVL column or a note | A second MPN is listed and its package drawing matches the footprint, or the user marked the part sole-source on purpose | No second source and no sole-source note | warning. Sole-source is not Critical by itself | Second-source package drawing |

### Lifecycle words, only after the page shows them

| Status on the page | Result |
|---|---|
| Active | Pass |
| NRND | Warning, and name an alternate or a sole-source acceptance |
| EOL with a last-time-buy date | Warning if the buy covers the build; Critical if the date is already past and no alternate is on the BOM |
| Obsolete | Critical when no alternate is on the BOM |

---

## 2. Second Source & Alternatives (第二货源)

Section 1 is the verdict for second source, lifecycle, and MPN suffix. Do not raise those as Critical from the bullets below. A bullet with no evidence file is `not verifiable`.

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

Severity for lifecycle, stock, and package suffix comes from section 1. Do not mark a part EOL, out of stock, or sole-source Critical without the fetched page or the dated export. A capacitor voltage rating is Critical only when the BOM voltage is below the rail voltage on the schematic. A reference-designator mismatch between BOM and schematic is Critical when both files are in the review and the same ref maps to two MPNs. Package height versus the enclosure is `not verifiable` unless a mechanical drawing states the limit.
