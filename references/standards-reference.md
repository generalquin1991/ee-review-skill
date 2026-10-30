# Standards Reference Guide

This is an orientation index, not a source of normative requirements or numeric pass/fail limits. Standards are revised, adopted differently across markets, and may be licensed documents. Before making a compliance finding, identify the target market and product category, verify the applicable edition and amendments using the standards body's official catalog, and cite the exact clause/table from a lawfully available copy or project-controlled compliance record. Do not infer a compliance limit from this summary. Catalog status linked below was checked on 2026-10-30; recheck it for each project review.

## IPC Standards (PCB Design & Assembly)

### IPC-2221 - Generic Standard on Printed Board Design
- **Scope**: Base document for all IPC-222x series, covering rigid, flex, and MCM-L boards.
- **Key Areas**: Material selection, conductor sizing, hole sizing, electrical clearance.
- **Review Use**: Verify trace width for current carrying capacity, annular ring requirements, and minimum spacing.
- **Review use**: Identify applicable clearance, conductor sizing, and hole/ring checks, then verify the design against the licensed edition, its conditions, and the fabrication supplier's capabilities. Do not use a generic spacing or annular-ring number from this guide as an acceptance limit.

### IPC-2222 - Sectional Standard for Rigid Organic Printed Boards
- **Scope**: Rigid PCB specific design requirements.
- **Key Areas**: Layer count, stackup, via design, density classification.

### IPC-7351 - Generic Requirements for Surface Mount Design and Land Pattern Standard
- **Scope**: Land pattern (footprint) design for SMT components.
- **Key Areas**: Pad size, solder mask, stencil aperture, component tolerance.
- **Review Use**: Verify footprints match IPC-7351 recommended land patterns.
- **Note**: Use IPC-7351B calculator or library (e.g., KiCad, Altium) for accurate patterns.

### IPC-A-610 - Acceptability of Electronic Assemblies
- **Scope**: Visual acceptance criteria for assembled PCBs.
- **Key Areas**: Solder joint quality, component placement, cleanliness.
- **Classes**:
  - Class 1: General Electronic Products (consumer)
  - Class 2: Dedicated Service Electronic Products (industrial)
  - Class 3: High Performance Electronic Products (military/medical/automotive)

### IPC-6012 - Qualification and Performance Specification for Rigid Printed Boards
- **Scope**: Bare board performance and qualification.
- **Key Areas**: Thermal stress, conductor adhesion, hole quality.

### IPC-9252 - Guidelines and Requirements for Electrical Testing
- **Scope**: Electrical test methods for unpopulated PCBs.
- **Key Areas**: Continuity and isolation testing, test point requirements.

## IEEE Standards (Electrical & Signal)

### IEEE 802.3 - Ethernet
- **Scope**: Wired Ethernet physical layer specifications.
- **Review Use**: Verify Ethernet PHY connections, magnetics, termination.

### IEEE 1149.1 - JTAG / Boundary Scan
- **Scope**: Test access port and boundary-scan architecture.
- **Review Use**: Verify JTAG chain integrity, TAP controller connections.
- **Key Requirements**: TCK, TMS, TDI, TDO signals; daisy-chain topology.

### IEEE 1596.3 - LVDS
- **Scope**: Low-voltage differential signaling standard.
- **Review Use**: Verify LVDS termination (100 ohm differential), routing rules.

## IEC Standards (Safety & EMC)

### IEC 61000 Series - Electromagnetic Compatibility (EMC)
| Standard | Scope | Key Review Points |
|----------|-------|-------------------|
| IEC 61000-4-2 | ESD immunity | TVS placement, ESD path to chassis ground |
| IEC 61000-4-3 | Radiated immunity | Shielding, filtering on external interfaces |
| IEC 61000-4-4 | EFT immunity | Decoupling, ferrite beads on I/O |
| IEC 61000-4-5 | Surge immunity | MOV, GDT, TVS on power inputs |
| IEC 61000-4-6 | Conducted immunity | Common-mode chokes, filtering |
| IEC 61000-4-8 | Magnetic immunity | Layout, shielding for magnetic fields |

### IEC 62368-1 - Audio/video, information and communication technology equipment
- **Scope**: Product safety framework for equipment in its stated scope; applicability depends on product and market.
- **Review Use**: Identify the current adopted edition and applicable safeguards, then cite the controlled clause and evidence. IEC lists [IEC 62368-1:2023, Edition 4.0](https://webstore.iec.ch/en/publication/69308) as valid at the time this guide was updated.

### IEC 60950-1 - Legacy reference
- IEC lists [IEC 60950-1:2005 as withdrawn on 2024-03-29](https://webstore.iec.ch/en/publication/4020). Do not use it as the default current basis for a new review; retain it only when a specific legacy approval or transition regime makes it relevant, and verify that basis with the project compliance owner.

### IEC 60601-1 - Medical Electrical Equipment Safety
- **Scope**: Safety and essential performance for medical electrical equipment.
- **Key Areas**: Patient leakage current, MOPP/MOOP insulation.

## CE / FCC Certification (EMC Compliance)

### FCC Part 15 (US)
- **Scope**: Radio frequency devices, unintentional radiators.
- **Classes**:
  - Class A: Commercial/industrial environments (higher emission limits).
  - Class B: Residential environments (stricter limits).
- **Review Use**: Verify EMI mitigation for digital clocks, high-speed interfaces.
- **Key Checklist**:
  - Clock frequency and harmonic analysis.
  - Cable shielding and filtering.
  - Chassis shielding and apertures.
  - PCB layout for emission control.

### CE EMC Directive (EU - 2014/30/EU)
- **Scope**: Electromagnetic compatibility requirements for EU market.
- **Official text**: [EUR-Lex consolidated text](https://eur-lex.europa.eu/eli/dir/2014/30/oj/eng).
- **Key Standards**:
  - EN 55032: Emission limits for multimedia equipment.
  - EN 55035: Immunity requirements for multimedia equipment.
  - EN 61000-3-2: Harmonic current emissions.
  - EN 61000-3-3: Voltage fluctuations and flicker.

### CE RED Directive (EU - 2014/53/EU)
- **Scope**: Radio equipment directive for wireless devices.
- **Official text**: [EUR-Lex text](https://eur-lex.europa.eu/eli/dir/2014/53/oj/eng).
- **Key Areas**: RF power, frequency band compliance, spectrum access.

## USB-IF Standards
- **Scope**: USB interface compliance (USB 2.0, 3.x, USB-C).
- **Review Use**: Verify USB signal routing, power delivery, connector pinout.
- **Review use**: Verify interface-specific electrical, routing, connector, and role requirements against the applicable USB-IF specification and device datasheets. Do not treat generic impedance or length-matching values as pass/fail limits; the applicable value depends on the interface, topology, stackup, and specification revision. Use the [USB-IF document library](https://www.usb.org/documents) to identify current specifications.

## JEDEC Standards (Memory)
| Standard | Scope | Review Focus |
|----------|-------|-------------|
| JESD79-3 | DDR3 SDRAM | Address/command routing, termination, ODT |
| JESD79-4 | DDR4 SDRAM | Fly-by topology, CA training, ZQ calibration |
| JESD79-5 | DDR5 SDRAM | DFE, on-die termination, power management |
| JESD209 | LPDDR | Low-power DDR for mobile applications |

## AEC-Q100 (Automotive Grade)
- **Scope**: Stress test qualification for integrated circuits in automotive applications.
- **Review Use**: Verify the required qualification grade and temperature range from the applicable AEC-Q100 revision and the exact component qualification record. Do not infer a component's suitability from a grade label alone.

## Quick Reference: When to Apply Which Standard

| Design Feature | Primary Standard | Secondary Standard |
|----------------|-----------------|-------------------|
| PCB stackup & trace width | IPC-2221/2222 | IPC-6012 |
| Component footprint | IPC-7351 | - |
| Assembly quality | IPC-A-610 | - |
| Ethernet interface | IEEE 802.3 | - |
| USB interface | USB-IF spec | - |
| DDR memory | JEDEC JESD79 | - |
| ESD protection | IEC 61000-4-2 | - |
| EMI emission | EN 55032 / FCC Part 15 | - |
| Product safety | Applicable product safety standard for the target market (for example, IEC 62368-1 where in scope) | Applicable insulation coordination / component requirements |
| Automotive components | AEC-Q100 | - |
| Boundary scan test | IEEE 1149.1 | - |
