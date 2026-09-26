# Schematic Review Checklist

## 1. Power Supply Design (电源设计)

### 1.1 Power Tree & Distribution
- Verify complete power tree diagram exists (Vmain → regulators → loads).
- Check all voltage rails have defined source, target, and current budget.
- Confirm power sequencing requirements are met (especially for FPGA/CPU/SoC).
- Verify power-on/power-off sequencing order and timing.
- Check power rail naming consistency across all sheets.

### 1.2 Decoupling
- Verify decoupling capacitors on every IC power pin (typically 0.1uF + 10uF).
- Check bulk capacitance on regulator outputs.
- Verify decoupling capacitor placement is close to power pins (in PCB layout).
- Check for missing decoupling on critical signals (e.g., reference voltage pins).
- Confirm capacitor voltage ratings have adequate margin (>= 1.5x rail voltage).

### 1.3 Regulation & Protection
- Verify regulator output voltage and current ratings match load requirements.
- Check thermal design current vs. maximum load current.
- Verify over-current protection (OCP) and over-voltage protection (OVP) circuits.
- Confirm reverse-polarity protection on external power inputs.
- Check soft-start circuitry for high-capacitance loads.
- Verify power-good (PG) signals are connected where required.

### 1.4 Battery & Backup
- Check battery charging circuit parameters (if applicable).
- Verify battery protection (overcharge, over-discharge, over-current).
- Confirm RTC backup battery circuit.
- Check fuel gauge / battery monitoring connections.

### 1.5 Power Margin Analysis
| Component | Parameter | Minimum Margin | Recommended Margin |
|-----------|-----------|----------------|-------------------|
| Voltage Regulator | Output current | 20% | 30%+ |
| Capacitor | Voltage rating | 50% | 100% |
| Inductor | Saturation current | 20% | 30%+ |
| MOSFET | Drain current | 30% | 50%+ |

---

## 2. Signal Integrity (信号完整性)

### 2.1 High-Speed Signals
- Verify series termination resistors on clock and high-speed signals.
- Check parallel termination on clock distribution networks.
- Confirm stub length on high-speed buses is within limits (typically < 1/6 rise-time length).
- Verify differential pair routing rules are documented (impedance, skew).
- Check AC coupling capacitors on serial links (PCIe, USB 3.x, etc.).

### 2.2 Clock Design
- Verify crystal/oscillator load capacitor values match datasheet.
- Check clock distribution buffer fan-out vs. input load.
- Confirm jitter attenuation for sensitive clock domains.
- Verify clock signal routing constraints are specified.

### 2.3 Bus & Interface
- Verify pull-up/pull-down resistors on I2C, SPI, UART, GPIO lines.
- Check I2C bus capacitance budget (typically < 400pF for standard mode).
- Confirm SPI clock polarity and phase (CPOL/CPHA) settings documented.
- Verify CAN bus termination (120 ohm at both ends).
- Check RS-485 termination and fail-safe biasing.

### 2.4 Level Shifting
- Verify voltage level translators for mixed-voltage interfaces.
- Check bidirectional level shifter direction control.
- Confirm open-drain vs. push-pull compatibility.

---

## 3. Protection Circuits (保护电路)

### 3.1 ESD Protection
- Verify TVS diodes on all external-facing interfaces (USB, HDMI, Ethernet, GPIO headers).
- Check TVS clamping voltage vs. IC maximum rating.
- Confirm ESD protection on antenna/RF paths.
- Verify spark gaps or discharge resistors where applicable.

### 3.2 Over-Voltage / Over-Current
- Check fuse or polyfuse on power inputs.
- Verify crowbar circuit on critical rails (if applicable).
- Confirm current limiting on USB VBUS output.
- Check zener clamping on sensitive analog inputs.

### 3.3 Isolation
- Verify galvanic isolation on isolated interfaces (optocoupler, digital isolator).
- Check isolation creepage/clearance distance markings.
- Confirm isolated power supply for isolated sections.

---

## 4. Circuit Logic & Correctness (电路逻辑)

### 4.1 Functional Verification
- Verify logic gates and combinational logic truth tables.
- Check flip-flop clock domains and synchronization.
- Confirm reset circuit (RC reset, supervisor IC, watchdog).
- Verify boot configuration pins (strapping pins) have correct pull values.
- Check unused input pins are tied to defined levels (not floating).

### 4.2 Feedback & Control Loops
- Verify feedback resistor divider values for adjustable regulators.
- Check compensation network values for switching regulators.
- Confirm loop stability criteria are documented.

### 4.3 Timing
- Verify setup/hold time margins for synchronous interfaces.
- Check propagation delay budget for asynchronous paths.
- Confirm power-on reset (POR) timing.

### 4.4 Component Value Verification
- Cross-check critical component values against design calculations.
- Verify resistor power ratings for high-dissipation paths.
- Check capacitor ESR requirements (especially for switching regulators).
- Confirm inductor saturation current vs. peak current.

---

## 5. Design Rule Checks (设计规则)

### 5.1 Netlist Consistency
- Verify all nets are properly labeled (no orphaned nets).
- Check for net name conflicts or ambiguous naming.
- Confirm power/ground net assignments.
- Verify multi-page net connections via global labels/ports.

### 5.2 Pin & Connector
- Check connector pinout matches mechanical drawing.
- Verify pin 1 markings are present.
- Confirm keyed connectors for polarized interfaces.
- Check for unused connector pins (documented as NC).

### 5.3 Documentation
- Verify revision history / version control markers.
- Check design notes and critical parameter annotations.
- Confirm test points are documented and accessible.
- Verify BOM cross-reference numbers on schematic.

---

## 6. Common Schematic Issues (常见问题)

| Issue | Severity | Description |
|-------|----------|-------------|
| Floating input pins | Critical | Unused CMOS inputs must be tied high or low |
| Missing decoupling | Critical | Every IC power pin needs decoupling |
| Missing pull on open-drain | Critical | I2C/SPI/INT lines need pull-up resistors |
| Wrong TVS direction | Warning | TVS orientation matters for unidirectional types |
| Exceeding absolute max | Critical | Any pin exceeding datasheet absolute maximum ratings |
| Missing test points | Info | Test points improve debuggability and DFT |
| Inconsistent naming | Info | Mixed naming conventions reduce readability |
| No power sequencing | Critical | Multi-rail SoCs require defined power-up sequence |
