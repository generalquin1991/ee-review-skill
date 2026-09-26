# PCB Design Review Checklist

## 1. Layer Stackup (层叠设计)

### 1.1 Stackup Definition
- Verify layer count is adequate for design complexity (signal density, power/ground planes).
- Check signal layer / plane layer ratio (recommend >= 1 ground plane per 2 signal layers).
- Confirm impedance-controlled layers are documented with target impedance.
- Verify stackup symmetry for warpage control (balanced copper distribution).
- Check prepreg/core thicknesses and copper weights are specified.
- Confirm reference plane assignment for each signal layer.

### 1.2 Material & Thickness
- Verify board thickness (standard: 1.6mm, check if different).
- Check copper weight for power planes (1oz min for moderate current, 2oz+ for high current).
- Confirm high-Tg material for lead-free / high-temperature applications (Tg >= 170C).
- Verify dielectric constant (Dk) is specified for impedance control.

### 1.3 Reference Layer
| Signal Type | Recommended Reference | Via Transition | Notes |
|-------------|----------------------|----------------|-------|
| High-speed single-ended | Adjacent ground plane | Stitching via | Minimize return path discontinuity |
| Differential pair | Adjacent ground plane | Pair stitching vias | Maintain impedance through via |
| Power | Adjacent ground plane | Decoupling nearby | Minimize loop inductance |
| Analog | Dedicated analog ground | Bridge to digital GND | Star-point or bridge connection |

---

## 2. Signal Integrity (信号完整性)

### 2.1 Impedance Control
- Verify impedance-controlled nets are documented (50 ohm single-ended, 90/100 ohm differential).
- Check trace width vs. stackup for target impedance.
- Confirm impedance is maintained through connector transitions.
- Verify layer change vias have reference plane stitching vias nearby.

### 2.2 Length Matching
- Verify differential pair intra-pair skew (typically < 5 mil).
- Check bus length matching requirements (DDR: byte-lane matching).
- Confirm clock-to-data length matching for synchronous buses.
- Verify serpentine/pattern matching compensation is applied correctly.

### 2.3 Crosstalk
- Check parallel trace spacing (3W rule minimum for critical signals).
- Verify high-speed signals are separated from sensitive analog.
- Confirm guard traces / ground copper pour between critical nets.
- Check layer-to-layer crosstalk (orthogonal routing on adjacent layers).

### 2.4 Return Path
- Verify continuous return path under all high-speed traces.
- Check for return path discontinuities (plane splits, voids, cutouts).
- Confirm stitching vias near signal layer transition vias.
- Verify no traces cross plane splits (especially high-speed and clock).

---

## 3. Power Integrity (电源完整性)

### 3.1 Power Distribution
- Verify power plane integrity (no excessive segmentation).
- Check power plane width / copper area for current carrying capacity.
- Confirm DC voltage drop analysis for high-current rails.
- Verify power and ground plane pair is adjacent (minimizes loop inductance).

### 3.2 Decoupling Placement
- Verify decoupling capacitors are placed as close to IC power pins as possible.
- Check via-in-pad or short trace connections for decoupling.
- Confirm bulk capacitors placed near regulator output.
- Verify decoupling via connection directly to plane (minimize trace loop).

### 3.3 Power Plane Current Capacity
| Copper Weight | 1oz (35um) | 2oz (70um) | Temperature Rise |
|---------------|------------|------------|-----------------|
| 0.25mm trace | 0.5A | 0.8A | 10C |
| 0.50mm trace | 1.0A | 1.5A | 10C |
| 1.00mm trace | 1.8A | 2.8A | 10C |
| 2.00mm trace | 3.5A | 5.5A | 10C |

---

## 4. Thermal Management (热设计)

### 4.1 Component Placement
- Verify high-power components are spaced adequately.
- Check thermal-sensitive components (crystal, electrolytic cap) away from heat sources.
- Confirm thermal vias under QFN/BGA thermal pads.
- Verify thermal pad solder paste pattern (window-pane / dots to prevent voiding).

### 4.2 Copper Pour & Heat Spreading
- Check solid copper pour connected to heat-dissipating pads.
- Verify thermal relief connections for solderability (on plane connections).
- Confirm adequate copper area for heat spreading (estimate via theta-JA).

### 4.3 Airflow & Ventilation
- Verify component orientation aligns with airflow direction (if forced air).
- Check tall components do not block airflow to downstream heat sinks.

---

## 5. EMC / EMI Design (电磁兼容设计)

### 5.1 Layout Partitioning
- Verify clear separation between analog, digital, and RF sections.
- Check mixed-signal IC placement at section boundary.
- Confirm ground plane splits are intentional and documented.
- Verify no traces cross ground plane splits.

### 5.2 Filtering & Shielding
- Verify common-mode chokes on external cables (USB, Ethernet, HDMI).
- Check pi-filter / ferrite bead on power entry.
- Confirm shield can / EMI gasket footprint where required.
- Verify stitching capacitors across plane splits at signal crossing points.

### 5.3 Clock & High-Frequency
- Check clock oscillator placement (away from edges and I/O connectors).
- Verify clock traces are routed on internal layers where possible.
- Confirm clock traces have guard ground traces or are embedded between planes.
- Check return current path for all high-frequency signals.

### 5.4 Grounding
- Verify single-point or multi-point grounding strategy is defined.
- Check chassis ground connection points (ESD discharge path).
- Confirm ground via stitching density (approx every lambda/20 for highest freq).

---

## 6. Footprint & Land Pattern Verification (封装与焊盘验证)

### 6.1 Footprint Accuracy
- Verify every footprint matches the actual component package (cross-check with BOM).
- Check pad count, pad pitch, and pad position against component datasheet.
- Confirm thermal pad dimensions for QFN/DFN/MLF packages match exposed pad size.
- Verify BGA land pattern: ball count, ball pitch (0.8mm/1.0mm/0.5mm/0.4mm), ball map.
- Check connector footprint matches mating connector pinout and mechanical drawing.
- Verify through-hole component drill sizes match lead diameters with adequate clearance.

### 6.2 Pad Design (IPC-7351 Compliance)
- Verify land pattern follows IPC-7351 recommendations (pad width, pad length, toe/heel fillet).
- Check SMD (Solder Mask Defined) vs NSMD (Non-Solder Mask Defined) pad selection:
  - NSMD preferred for most SMT (better solder joint reliability).
  - SMD preferred for BGA near board edge (prevents pad lifting).
- Verify solder mask opening is larger than pad (typical 0.05-0.1mm per side expansion).
- Check paste mask aperture size and shape (typical 70-90% of pad area for fine-pitch).
- Confirm thermal pad paste pattern uses window-pane / dot pattern to prevent voiding.

### 6.2a Solder Mask Layer Verification (阻焊层验证)
- Verify board-level `solder_mask_margin` is set in KiCad setup (typical: 0.051mm / 2mil). If NOT SET, flag as warning — KiCad default may not match fabricator requirements.
- Check that all SMD pads include `"F.Mask"` (or `"B.Mask"`) in their `(layers ...)` list. Pads without mask layer entries will have NO solder mask opening (completely covered by solder mask).
- Verify via tenting strategy is explicitly defined:
  - Tented vias: via layers = `"F.Cu" "B.Cu"` (no F.Mask/B.Mask) — solder mask covers the via hole.
  - Non-tented (open) vias: via layers = `"F.Cu" "F.Mask" "B.Cu" "B.Mask"` — solder mask has opening over via.
  - Check if tenting is appropriate: tenting prevents solder wicking through vias during reflow; non-tenting allows via to serve as test point.
  - If vias are used as test points, they MUST be non-tented (include F.Mask or B.Mask in layers).
- Verify special pad mask treatments:
  - Gold finger pads: solder mask opening should expose the entire gold finger contact area.
  - Test point pads: should be non-tented (include mask layer) for probe access.
  - Connector mating pads: verify mask opening matches connector mechanical requirements.
- Check for solder mask sliver violations (minimum mask web between adjacent pads: typically 0.1mm / 4mil).
- Verify NSMD vs SMD pad definition method:
  - NSMD (Non-Solder Mask Defined): mask opening is larger than copper pad — preferred for most SMT.
  - SMD (Solder Mask Defined): mask opening is smaller than or equal to copper pad — used for BGA edge pads.
  - In KiCad, NSMD is the default (mask opening = pad size + solder_mask_margin).
  - Check if any pads need SMD definition (requires custom pad shape or negative margin).

### 6.2b Solder Paste Layer Verification (助焊层/钢网层验证)
- Verify board-level `solder_paste_margin` and `solder_paste_margin_ratio` are set in KiCad setup. If NOT SET, paste = copper pad size (no reduction) — flag as warning for fine-pitch designs.
- Check paste aperture reduction for fine-pitch components:
  | Component Pitch | Recommended Paste Reduction | Reason |
  |----------------|---------------------------|--------|
  | >= 1.0mm | 0% (full size) | Adequate spacing, full paste needed |
  | 0.8mm (QFP/connector) | 5-10% reduction | Prevent solder bridging |
  | 0.5mm (QFP/BGA) | 10-15% reduction | Prevent bridging, control solder volume |
  | 0.4mm (BGA) | 15-20% reduction | Critical for joint reliability |
  | <= 0.3mm | 20-30% reduction or stepped stencil | Prevent shorts, ensure volume |
- Verify per-pad paste margin overrides are applied where needed:
  - Fine-pitch pads: `(solder_paste_margin -0.05)` or `(solder_paste_margin_ratio -0.1)`
  - Thermal pads (QFN/DFN): use window-pane or dot pattern paste stencil, NOT full paste coverage
  - Large copper pads (> 5mm): use divided paste pattern to prevent voiding and outgassing
- Check that paste layer is NOT included for non-SMT pads:
  - Through-hole pads should NOT have F.Paste in layers (paste is applied by wave solder, not stencil)
  - Mechanical mounting holes should NOT have paste
  - Test points may or may not have paste depending on assembly process
- Verify paste aperture shape matches pad shape (rectangular pad → rectangular aperture, circular pad → circular aperture).
- For via-in-pad designs: verify paste is NOT applied over filled vias (should be covered, not paste-applied).

### 6.2c PADS-to-KiCad Conversion Data Loss Warning
When reviewing a PADS ASCII file converted via kicad-cli, be aware of these known conversion limitations:
- **Per-layer pad sizes LOST**: PADS allows different sizes for copper, solder mask, and paste layers per pad stack. KiCad uses a single `(size ...)` for all layers. Paste reduction defined in PADS is LOST.
- **Solder mask margin NOT SET**: KiCad's `solder_mask_margin` is not populated from PADS default expansion. Verify and set manually.
- **Solder paste margin NOT SET**: KiCad's `solder_paste_margin` and `solder_paste_margin_ratio` are not populated from PADS paste sizes. Verify and set manually.
- **Board-level silk text LOST**: PADS TEXT section items (board name, date, logos) are not converted to KiCad gr_text. Only footprint-level silkscreen (fp_line) is preserved.
- **Board-level graphics PARTIAL**: PADS LINES section board-level drawings are partially converted. Verify board outline (Edge.Cuts) is complete.
- **Copper zones NOT converted**: PADS plane/thermal definitions are not converted to KiCad zones. Must be re-created manually.
- **Via definitions SIMPLIFIED**: PADS via definitions (drill, pad stack) are not converted to KiCad vias. kicad-cli does not import PADS routing traces or vias (use pads_route_injector.py or pads_full_converter.py to inject routes).

### 6.3 Courtyard & Spacing
- Verify component courtyard (IPC-7351 body + clearance zone) does not overlap neighbors.
- Check minimum component-to-component spacing (typical: 0.15mm for 0402, 0.2mm for 0603+).
- Confirm body-to-body clearance for rework accessibility (recommend >= 0.5mm).
- Verify tall component shadowing on low components (reflow solder temperature uniformity).

### 6.4 Orientation & Marking
- Verify pin 1 indicator on footprint (silk dot, chamfer, or notch).
- Check orientation markers match BOM assembly notes (polarity for diodes, tantalum caps, LEDs).
- Confirm body outline silkscreen matches actual package outline.
- Verify reference designator silkscreen is within component courtyard and readable.

### 6.5 Footprint-to-BOM Cross-Check
- Verify each BOM line item has a corresponding footprint assigned in PCB.
- Check for orphaned footprints (placed in PCB but not in BOM - "Do Not Install" items).
- Confirm footprint name in PCB library matches package type in BOM (e.g., "SOIC-8_3.9x4.9mm_P1.27mm").
- Verify same-value components use consistent footprint (no mixing 0603 and 0805 for same resistor value).

| Common Footprint Issue | Severity | Impact |
|----------------------|----------|--------|
| Wrong package assigned (e.g., QFN32 vs QFN48) | Critical | Component won't fit, assembly failure |
| Pad size mismatch vs. component | Critical | Solder joint reliability, tombstoning |
| Missing thermal pad footprint on QFN | Critical | Overheating, electrical instability |
| NSMD/SMD selection wrong for BGA | Warning | Pad lifting risk, joint reliability |
| Courtyard overlap | Warning | Assembly difficulty, rework challenge |
| Pin 1 marker missing | Warning | Wrong orientation risk during assembly |
| Inconsistent footprints for same value | Info | Library management issue, confusion |
| Silkscreen over pad | Info | Solderability concern, cosmetic |

---

## 7. DFM / DFT (可制造性 & 可测试性)

### 7.1 DFM - Manufacturing
- Verify minimum trace width / spacing meets fabricator capability.
- Check minimum drill size and annular ring requirements.
- Confirm solder mask defined (SMD) vs. non-solder mask defined (NSMD) pads for BGA.
- Verify panelization considerations (breakaway tabs, fiducials).
- Check silkscreen clarity (no overlap with pads, readable font size >= 0.8mm).
- Confirm tombstone prevention for small passive components (0402 and below).

### 7.2 DFT - Testability
- Verify test points on critical nets (power rails, clocks, reset, debug).
- Check test point spacing for bed-of-nails fixture compatibility (>= 2.54mm).
- Confirm ICT (In-Circuit Test) accessibility for key nodes.
- Verify boundary scan chain is complete and documented.
- Check JTAG/SWD debug connector is accessible.

### 7.3 Assembly
- Verify component spacing meets pick-and-place requirements.
- Check for component orientation markers (pin 1 indicators).
- Confirm no components under shields that cannot be accessed.
- Verify BGA fan-out pattern and escape routing.

---

## 8. Routing Quality (布线质量)

### 8.1 General Routing
- Verify no acute angle traces (90-degree or less).
- Check trace necking is gradual and minimal.
- Confirm copper pour is applied on all layers (ground fill).
- Verify teardrops on pad/via connections (especially for flex boards).

### 8.2 Via Design
- Check via aspect ratio (depth/diameter) is within fabricator capability (typically < 10:1).
- Verify microvia / blind / buried via usage is documented.
- Confirm via tenting (solder mask) strategy for unused vias.
- Check current capacity of vias for power paths (parallel vias for high current).

### 8.3 Net-Specific Routing
| Net Type | Routing Rule | Priority |
|----------|-------------|----------|
| Clock | Shortest path, guard ground | Highest |
| Differential pair | Equal length, controlled impedance | High |
| High-speed bus | Length matched, ground reference | High |
| Power | Wide trace/plane, short as possible | Medium |
| Analog | Away from digital, guard ground | High |
| Reset | Short,远离 noise sources, pull resistor close | High |

---

## 8. Common PCB Issues (常见PCB问题)

| Issue | Severity | Description |
|-------|----------|-------------|
| Trace over plane split | Critical | Return path discontinuity causes EMI and SI issues |
| Insufficient decoupling vias | Critical | High loop inductance reduces decoupling effectiveness |
| No thermal vias on QFN | Warning | Overheating risk for thermal pad components |
| Clock near board edge | Warning | EMI radiation from edge, coupling to cables |
| 90-degree trace corners | Info | Can cause etching issues and impedance discontinuity at high freq |
| Missing test points | Info | Reduces debuggability and test coverage |
| Tight component spacing | Warning | Assembly difficulty, rework challenges |
| Via in BGA pad without fill | Warning | Solder joint reliability concern |
| No copper balance | Warning | Warpage risk during reflow |
| Acid trap routing | Info | Acute angle traps etchant causing over-etching |
| Wrong footprint assigned | Critical | Component body does not match PCB pad layout |
| Missing thermal pad on QFN footprint | Critical | No heat dissipation path, component overheating |
| NSMD pads at board edge | Warning | Pad lifting risk during depanelization |
| Silkscreen over solder pad | Warning | Solderability issue, cosmetic defect |
| Courtyard overlap between components | Warning | Assembly difficulty, potential solder bridging |
| Inconsistent footprints for same value | Info | Library management issue, maintenance confusion |
