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

## 6. Low-Power Design (低功耗设计)

### 6.1 Sleep / Standby Current Budget
- Sum every block's sleep and standby current; compare the always-on leakage total against cell capacity and the standby-life target.
- Require a measured sleep/standby current, not a nominal datasheet sum; mark unverified claims.

### 6.2 Floating & Unused Pins
- Unused CMOS inputs must be tied high/low or firmware-disabled; floating inputs leak and emit EMI.
- Avoid resistor-divider bias that leaves a pin near Vdd/2 (region of maximum leakage).

### 6.3 Pull Resistor Leakage vs. Speed
- Choose weak pull-ups for low leakage where edge speed allows; do not blindly use 4.7k on always-on lines.
- Confirm pulldowns on unused inputs and on power-gated enable lines.

### 6.4 Power-Gated Domains
- Loads switched by load switch/FET must be truly isolated when off: no sneak path through protection diodes, rail pull-ups, or unpowered bidirectional IO.
- Verify EN/gate default state (active-low enable needs a pulldown to stay off until firmware acts).

### 6.5 Regulator Quiescent Current & Light-Load Efficiency
- Always-on rail must use a nano-Iq LDO/PMIC; switching regulators must keep efficiency at the typical light load, not only at full load.
- Disabled/unused regulators must be actually off (a regulator left enabled defeats the power gate).

### 6.6 Always-On Domain & RTC/Backup
- Keep the always-on domain minimal (e.g. BLE/PMIC only); high-power domains (camera, boost, backlight) enabled only on demand, never fed from an always-on rail.
- Backup/RTC supply must not quietly drain the main cell; confirm ship/storage mode prevents deep discharge during shipping/shelf.

---

## 7. EMC / EMI Design (电磁兼容 - 原理图级)

### 7.1 I/O Filtering at Connector Entry
- Every external cable/connector (USB, antenna, I/O, power) needs EMC filtering at the entry point: TVS + ferrite bead / RC / common-mode choke, placed connector-side first.
- Distinguish ESD clamp (fast, low clamp) from EMI filter (common-mode, broadband); one TVS is not both.

### 7.2 Decoupling for EMC
- Proper decoupling values and dielectric (X7R) on every IC and each rail; high-frequency ceramic close to pins. Decoupling is the first line of radiated-emission control.

### 7.3 Clock EMI
- Enable spread-spectrum on clock/PLL where available; add series damping resistors on clock lines; avoid unterminated clocks routed near edges or I/O.
- Keep clock traces short and away from cables/connectors; prefer internal layers.

### 7.4 Switching Regulator EMI
- Note snubber / bootstrap / switching-frequency choices that affect EMI; synchronous vs asynchronous trade-off; keep switching loops small (a PCB-layout rule, flagged to the layout stage).

### 7.5 Grounding Strategy (defined at schematic)
- Define AGND/DGND/RF ground relationship and the single-point tie; no net that silently bridges splits. Return-path continuity is the top EMI root cause.

### 7.6 Unused & Floating
- Tie unused CMOS inputs (floating inputs emit EMI); avoid intermediate-resistor bias near Vdd/2.

---

## 8. Safety / Electrical Safety (电气安全)

### 8.1 Creepage & Clearance
- Verify spacing per applied working voltage and pollution degree (IPC-2221 / IEC 62368-1); flag any user-accessible node above SELV.
- Isolation barriers: optocoupler/digital-isolator rated voltage; reinforced vs basic; margin to working/surge voltage.

### 8.2 Over-Protection Coordination
- Fuse/PTC/e-fuse rating and coordination with downstream OVP/OCP; verify against the accessible-voltage class.

### 8.3 Battery Safety
- Over-charge/over-discharge/over-current/short/reverse protection; thermal-runaway margin; ship/storage mode present. Cell + protector + charger coordination.

---

## 9. DFM / DFT (可制造可测试)

### 9.1 Test Points & ICT
- Test points on every critical net (power, reset, key signals, programming); probe clearance and bed-of-nails access.

### 9.2 Programming & Debug Access
- SWD/JTAG/UART header present, accessible, keyed; provision for production programming and trim/calibration.

### 9.3 Panelization & Process
- Fiducials, orientation markings, solder-paste/aperture, assembly orientation; minimum annular ring / mask-sliver margins.

---

## 10. Firmware-Hardware Co-Verification (固件-硬件协同)

### 10.1 FW-Dependent Blocks
- Any block enabled/configured by firmware (charger, PMIC, load switch, boost/buck EN, sensor config) must have its bring-up sequence specified and cross-checked to the datasheet.

### 10.2 Safe Default State
- Pre-firmware state must be safe: enables pulled to off/default, no rail back-driven, no latch-up.

### 10.3 Production / Startup Flow
- BIST/unlock/calibration (fuel-gauge, charger trim) must be in the production/startup flow; document the HW-FW dependency so "brick without FW" is explicit.

---

## 11. Common Schematic Issues (常见问题)

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
