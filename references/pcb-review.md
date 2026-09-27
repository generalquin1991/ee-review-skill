# PCB design review checks

Apply `references/review-contract.md` to every row. Geometry that is not in the layout file, stackup note, or fabrication drawing is `not verifiable`. A PDF stackup picture counts as evidence for the numbers it actually shows. Do not mark a row `confirmed` because the board "looks fine".

Reference for return path when a high-speed net changes layers: the new layer still needs an adjacent ground plane, and a stitching via beside the signal via. Analog ground ties to digital ground at one documented bridge, not by an unlabelled copper gap.

## 1. Stackup, impedance, return path

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Stackup called out | Impedance-controlled net, or a board with more than two copper layers | Fabrication stackup (layer count, copper weight, dielectric thickness, Dk) | Every signal layer names its reference plane, and the impedance note names the target (50 Ω single-ended, or the diff target the interface DS states) | No stackup file, or a controlled-impedance net has no target | not verifiable if the stackup was not supplied; warning if a controlled net has no target on a supplied stackup | IPC-2221 conductor and spacing sections; interface DS impedance |
| Trace versus stackup | A net with a stated impedance | Calculated width from the stackup Dk and height, and the width measured in the layout | Width is within 10% of the calculation, or a field-solver note is attached | Width differs by more than 10% and no solver note exists | warning | Stackup note; IPC-2141 or the solver output the user supplied |
| Pair skew | Differential pair whose standard names a skew limit | Layout length of P and N | Skew is inside the cited limit (USB 2.0, PCIe, DDR byte lane, or the PHY DS). Do not use 5 mil as a universal limit | Skew exceeds the cited limit | warning; critical only when the PHY DS states the link will not train beyond that skew | PHY or memory DS timing/routing section |
| Trace over a split | Clock, differential pair, or other net the design calls high-speed | Layout crossing of that trace against plane voids and splits | The trace stays over a continuous reference, including across a layer change (stitching via present) | The trace crosses a split or a void in its reference with no stitch | critical when the crossing is visible in the layout | IPC-2221 return-path guidance; interface layout note |
| Copper current | A power trace whose load current is known | Trace width, copper weight, and the load current | Current is at or below the 10 °C-rise row in the table below for that width and weight | Known current exceeds that row | warning; critical if the excess is >2× the table value | IPC-2221 Figure 6-1. The table below is an external approximation, not a substitute for the figure when the stackup is unusual |

| Copper weight | 0.25 mm | 0.50 mm | 1.00 mm | 2.00 mm | Rise |
|---|---|---|---|---|---|
| 1 oz (35 µm) | 0.5 A | 1.0 A | 1.8 A | 3.5 A | 10 °C |
| 2 oz (70 µm) | 0.8 A | 1.5 A | 2.8 A | 5.5 A | 10 °C |

## 2. Power and thermal geometry

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Decoupling loop | IC power pin whose schematic check requires a local capacitor | Layout distance from that capacitor pad to the IC pin, and the via to the plane | Capacitor is on the same side or opposite side directly under the pin, with a via to the plane at the cap pad | The only capacitor on that net is on the far side of the board with a long trace before the via | warning | IC layout section |
| QFN thermal pad | QFN, DFN, or exposed-pad package | Footprint pad, via count under the pad, paste window | Paste is a window or dot pattern, and thermal vias are inside the exposed pad | Exposed pad has no copper pad, or paste is a single full-size opening on a pad larger than 5 mm | critical if the exposed pad is missing from the footprint; warning for paste voiding | Package DS land pattern; IPC-7351 |
| Heat versus rating | Part with a cited dissipation and θJA | θJA, copper area or thermal vias, worst ambient the user named | Estimated Tj = Ta + P·θJA is below the DS maximum | Estimated Tj exceeds the maximum at the named ambient | critical when P, θJA, and Ta are all cited; otherwise not verifiable | Package DS thermal characteristics |

## 3. EMC geometry

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Clock placement | A clock or crystal | Layout location versus board edge and connectors | The clock net is not on the outer millimetres beside an external connector, and it has a continuous adjacent ground | The clock runs along the board edge into a connector with no ground between them | warning | CISPR 32 is a test, not a layout proof; cite the PHY/clock layout note you used |
| Plane split with no document | A ground pour that is split | Split polygon and any schematic note that names AGND versus DGND | The split matches a named AGND/DGND bridge, and no high-speed trace crosses it | A split exists with no note, or a clock crosses it | warning for an undocumented split; critical if a clock or differential pair crosses it | Design note; IPC-2221 |
| Entry filter | External cable that the schematic places a choke or ferrite on | Placement of that part versus the connector | The filter part is the first component after the connector, not after a long trace | The series filter is several centimetres inside the board | warning | Filter DS recommended layout |

## 4. Footprint checks that close only against a datasheet

Pad count, pitch, and exposed-pad size are Critical only when compared with the package drawing you opened. A library name that resembles the package is not that comparison.

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Land versus package | Every IC, connector, and non-0201 passive | Footprint pad count, pitch, and courtyard versus the package drawing | Pad count and pitch match the drawing; QFN exposed pad matches the EP size | Pad count or pitch differs, or the EP is absent | critical | Package outline drawing, dimensions page |
| Same BOM value, two lands | One value used in more than one footprint | BOM line and the footprints of its reference designators | One land pattern per value, or the BOM splits the lines by package | The same value and the same MPN are on both 0603 and 0805 | warning | BOM MPN; package drawing |
| Pin-1 mark | Polarized part | Silk or fab mark on the footprint, visible outside the pad | A pin-1 mark exists and is not on a pad | No pin-1 mark, or silk crosses a pad | warning | IPC-7351 marking; assembly drawing |

---

## 5. KiCad mask, paste, and conversion checks

The checks below are evidence rules for solder mask, paste, and PADS conversion loss. Record each one with the six fields in `references/review-contract.md`. A footprint or routing mismatch is Critical only when the package drawing or the layout measurement in sections 1–4 says so. Do not raise a finding from the category name alone.

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

Footprint severity is decided in section 4. Do not copy a Critical from this section without the package drawing.

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

## 9. Severity source

Return path, copper current, clock placement, and footprint mismatches take their severity from sections 1–4. A missing test point is `info` only when the net is named in the DFT list and the layout shows no probe pad. An acute trace corner is `info` and only on a net whose edge rate is cited.
