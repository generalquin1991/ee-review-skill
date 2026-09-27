# Conditional and Mandatory Hardware Review Matrix

Use this matrix for every hardware review. Record each item as `confirmed`,
`finding`, `not applicable (evidence)`, or `not verifiable (missing evidence)`.
Never infer `not applicable` only because a symbol or reference designator was
not recognized.

## Evidence Gate for Every Case

Before scoring any electrical dimension, request or locate:

1. **System block diagram** - power sources, processors, radios, motors,
   connectors, protection boundaries, and major loads.
2. **Power tree** - every input source and rail, regulator, enable/sequence,
   expected voltage/current, operating mode, and fault path.
3. **Operating envelope** - input range, battery range, temperature range,
   peak/steady loads, startup/shutdown behavior, and product environment.
4. **Target compliance/test baseline** - product ESD level, emissions/immunity
   target, safety class, and any project-specific requirement such as CERE.

If the block diagram or power tree is missing, add a warning finding under
`Power Supply Design` and state which claims cannot be verified. A schematic
that contains rails but does not provide an explicit power tree is not evidence
that the power architecture has been reviewed.

## Checks for Every Case: ESD and External Boundaries

Always review electrostatic discharge protection, even when no dedicated ESD
part is visible:

- Identify every user-accessible, cable-connected, test, charging, RF, and
  battery interface and trace its discharge path to chassis/ground.
- Verify the protection device's working voltage, clamping voltage, pulse
  rating, leakage, and capacitance against the protected signal.
- Check placement: connector-side first, short low-inductance return, no long
  protected trace before the clamp, and no noisy return shared with sensitive
  analog/RF grounds.
- Check whether the product target distinguishes contact and air discharge and
  whether the PCB, enclosure, cable shield, and connector shell are included in
  the path.
- For USB, RF, battery, sensor, and motor wiring, review common-mode/current
  return paths separately; one TVS symbol is not proof that all pins are
  protected.

Missing ESD evidence is a warning at minimum. An exposed interface with no
credible clamp/return path is critical when the interface can damage a safety-
or mission-critical rail.

## Feature Triggers

### Battery or Rechargeable Cell

Trigger on a battery symbol, cell/pack/BMS/fuel-gauge/charger part, BAT/VBAT/
PACK nets, or battery-related BOM text. Review all of the following:

- **Temperature protection:** cell and charger NTC/sensor placement, cold/hot
  charge inhibit thresholds, discharge over-temperature cutoff, sensor open/
  short behavior, thermal propagation assumptions, and whether limits match the
  cell maker's datasheet.
- **Electrical protection:** over-charge, over-discharge, over-current, short
  circuit, reverse polarity, fuse/e-fuse, pack isolation, and balancing for
  multi-cell packs. Verify thresholds, delay, recovery, and FET body-diode
  paths by netlist and datasheet.
- **Energy utilization:** compare usable energy between charge termination and
  discharge cutoff with the cell's specified voltage/capacity curve. Check
  converter dropout, UVLO hysteresis, reserve energy, fuel-gauge calibration,
  low-battery shutdown, ship/storage mode, and whether load power is stranded
  above the cutoff. A design does not "use all capacity" merely because the
  nominal mAh value appears in the BOM.
- **Power-path behavior:** charge and system-load sharing, load transients while
  charging, brownout during cable insertion/removal, reverse current, and
  behavior when the battery is absent or deeply discharged.
- **Thermal/mechanical evidence:** cell temperature rise at peak load/charge,
  sensor coupling to the cell, enclosure hot spots, and safe spacing from heat
  sources.

Required evidence includes the cell/pack datasheet, charger/BMS configuration,
temperature limits, and an energy budget or measured cutoff-to-termination
capacity. If unavailable, report the energy-utilization and thermal claims as
not verifiable.

### Antenna or RF Port

Trigger on an antenna connector, antenna matching network, RF switch/front-end,
cellular/Wi-Fi/Bluetooth/GNSS transceiver, ANT/RF nets, or an antenna in the
mechanical drawing/BOM. Review:

- 50-ohm controlled-impedance path, stackup evidence, width calculation, via
  transitions, reference-plane continuity, and connector launch.
- Matching circuit topology (normally a documented pi/T option), component
  values and package parasitics, DNP population strategy, and whether the
  network is placed at the antenna/transceiver boundary intended by the RF
  design.
- RF keepout, ground stitching, shield/enclosure interaction, antenna
  clearance, cable/connector strain, and isolation from clocks, DC/DC nodes,
  USB, and motor currents.
- ESD/surge path at an external antenna connector without degrading RF return
  loss or receiver noise figure.
- Tuning evidence: target band, VNA/S-parameter or OTA results, populated
  revision, and worst-case enclosure/cable/battery conditions. Do not approve a
  "matching circuit" based only on three unverified capacitor/inductor values.

### USB Type-C

Trigger on a USB-C receptacle, CC1/CC2, USB PD controller, VBUS, D+/D-, SSTX/
SSRX, or USB-C BOM description. Confirm:

- CC1 and CC2 are independently connected to the correct Rp, Rd, or Ra role
  circuitry for the product's source/sink/DRP role; no accidental short,
  floating pin, or single-CC assumption.
- VBUS current path, attach/detach behavior, VBUS discharge, over-voltage/
  over-current/reverse-current protection, dead-battery attach, and power-role
  transitions.
- USB 2.0/3.x shield, ground, ESD, common-mode, impedance, pair routing,
  orientation muxing, and connector shell/chassis return.
- If USB PD is claimed, verify the PD controller configuration, advertised
  PDOs/current, sink/source limits, cable assumptions, and fault recovery.

Every CC connection claim must be proven by netlist lookup and the selected
USB-C/PD controller datasheet. "CC is present" is insufficient; both pins and
their role resistors must be accounted for.

### 4G / Cellular Modem

Trigger on a cellular modem/module, SIM/eSIM, LTE/4G/5G label, or cellular RF
front end. Review supply stability under the modem's transmit burst and attach
events:

- peak and average current budget, rail impedance, bulk/high-frequency
  decoupling, regulator current limit, battery/cable resistance, and brownout
  margin;
- measured or calculated load-transient response, startup sequencing, reset/
  power-good behavior, and thermal rise at worst-case transmit duty cycle;
- antenna matching/keepout, SIM ESD/hot-plug protection, and coexistence with
  GNSS/Wi-Fi/Bluetooth;
- layout return paths and separation from sensitive ADC/audio/clock rails.

If only a nominal modem current is supplied, treat power stability as
unverified; nominal current is not a transmit-burst validation.

### Motor, Solenoid, Relay, or Other Inductive Load

Trigger on a motor driver, H-bridge, coil, solenoid, relay, fan, pump, or
inductive-load BOM description. Review:

- startup/inrush, stall/locked-rotor current, PWM frequency, current limit, and
  thermal derating;
- flyback/freewheel path, MOSFET avalanche margin, snubber/TVS, reverse battery
  protection, and fault containment;
- supply droop, ground bounce, reset immunity, bulk capacitance, regulator
  current limit, and separation from RF/ADC/audio rails;
- conducted/radiated EMI, cable discharge/ESD, connector arcing, and mechanical
  end-stop or jam behavior.

Use the worst-case stalled or jammed condition for the power-stability review;
the no-load motor current is not sufficient evidence.

### Low-Power Design (power-constrained designs)

Trigger on any battery, cell/pack, Li-Po, wearable, portable, always-on,
energy-harvesting design, or an explicit "low-power"/"sleep"/"standby" requirement,
or a DC/DC/regulator whose quiescent current is called out. Review all of the
following:

- **Sleep / standby budget:** sum every block's sleep and standby current and the
  always-on leakage; compare the standby total against cell capacity and the
  product's standby-life target. A design is not "low-power" merely because the
  active current is small.
- **Floating / unused pins:** unused CMOS inputs must be tied high/low or
  firmware-disabled — floating inputs leak and emit EMI. Verify no resistor-
  divider bias leaves a pin near Vdd/2 (the region of maximum leakage).
- **Pull-resistor leakage vs. noise:** weak pull-ups cut leakage but slow edges;
  confirm pull values are chosen for the lowest-leakage acceptable speed, not a
  blanket 4.7k.
- **Power-gated domains:** loads switched by load switch/FET must be truly
  isolated when off — no sneak path through protection diodes, rail pull-ups, or
  unpowered bidirectional IO back-driving the rail. Verify the gate/EN default
  state (an active-low enable needs a pulldown so it stays off until firmware
  acts). A regulator left enabled "just in case" defeats the gate.
- **Regulator quiescent current & light-load efficiency:** the always-on rail
  must use a nano-Iq LDO/PMIC; switching regulators must keep acceptable
  efficiency at the typical light-load current, not only at full load.
- **Always-on domain minimization:** keep the always-on domain (e.g. BLE/PMIC)
  as small as possible; high-power domains (camera, boost, backlight) must be
  enabled only on demand and never fed from an always-on rail.
- **RTC / backup domain:** backup/RTC supply must not quietly drain the main
  cell; confirm a ship/storage mode exists so the cell is not deeply discharged
  during shipping/shelf storage.
- **Measurement discipline:** require a measured sleep/standby current, not a
  nominal datasheet sum. Mark unverified sleep claims as `not verifiable`.

If a power budget or measured standby current is unavailable for a triggered
design, report low-power as `not verifiable` and name the missing evidence.

### EMC / EMI (radiated & conducted emissions, immunity)

Trigger on any clock above ~1 MHz, switching regulator/DC-DC, radio (BLE/Wi-Fi/
cellular/GNSS), cable/connector (USB, antenna, I/O, power), motor, or an explicit
emissions/immunity/CISPR/CE/FCC/ISO 11452 target. Review all of the following:

- **Radiated emissions:** clock harmonics, DC/DC switching spectrum, RF spurious,
  and cable/loop antenna effect. Confirm spread-spectrum is enabled on clock/PLL
  where available, series damping on clock lines, and routing away from edges/I-O.
- **Conducted emissions:** noise on power and cable lines; verify pi-filter /
  ferrite bead / common-mode choke at power entry and on external cables, placed
  connector-side first.
- **Immunity:** ESD is handled by the always-on check; confirm surge/burst/
  radiated-immunity margins for the product environment and that no long
  unprotected trace precedes a clamp.
- **Filtering & shielding:** CM chokes on external cables, shield-can / EMI-
  gasket footprint where required, stitching capacitors across plane splits.
- **Grounding strategy:** single- vs multi-point ground defined; chassis/ESD
  return path; no traces crossing ground splits (return-path discontinuity is a
  leading EMI cause); ground via stitching density.
- **Layout partitioning:** analog / digital / RF sections separated; mixed-
  signal IC straddles the boundary intentionally.

If the product names an emissions/immunity class but the design provides no
filtering/shielding evidence, report EMC/EMI as `not verifiable`.

### Safety / Electrical Safety

Trigger on any mains/AC input, isolation barrier, user-accessible voltage above
SELV, battery/Li-Po, or high-energy storage. Review:

- **Creepage / clearance:** spacing per applied working voltage and pollution
  degree (IPC-2221 / IEC 62368-1 / IEC 61010); flag any user-accessible node
  above SELV.
- **Isolation barriers:** optocoupler/digital-isolator rated voltage; reinforced
  vs basic; margin to working and surge voltage.
- **Over-protection coordination:** fuse/PTC/e-fuse rating and coordination with
  downstream OVP/OCP, verified against the accessible-voltage class.
- **Battery safety:** thermal-runaway margin, over-charge/over-discharge/
  over-current/short/reverse protection, and ship/storage mode; cell + protector
  + charger coordination.
- **User-accessible parts:** no exposed live conductor above SELV; enclosure/
  connector-shell earthing/return path.

If no safety class/baseline is provided, report Safety as `not verifiable`.

### Thermal Management

Trigger on high-power devices, power-dense or enclosed designs, or an explicit
temperature/derating target. Review:

- **Junction temperature:** estimate via theta-JA and measured/estimated power;
  margin to the maximum rating at worst ambient.
- **Board/enclosure hot spots:** copper pour, thermal vias, conductive/air-flow
  path to case; avoid placing temperature-sensitive parts near power stages.
- **Power-stage losses:** DC/DC, linear regulator, FET losses and temperature
  rise at worst duty cycle.
- **Battery temperature rise:** at peak charge/discharge; coupling to the cell.

If no thermal budget or environment is provided, report Thermal as
`not verifiable`.

### DFM / DFT (manufacturability & testability)

Trigger on any design going to production (always for new products). Review:

- **Test points & ICT:** test points on every critical net (power, reset, key
  signals, programming); probe clearance and bed-of-nails access.
- **Programming / debug access:** SWD/JTAG/UART header present, accessible,
  keyed; provision for production programming and trim/calibration.
- **Panelization & process:** fiducials, orientation markings, solder-paste/
  aperture, assembly orientation; minimum annular ring / mask-sliver margins.
- **DFT:** boundary-scan/loopback where feasible; calibration/trim access.

If a design omits test access, report DFM/DFT as a finding (production blind
spots).

### Firmware-Hardware Co-Verification

Trigger on any hardware block whose enable, configuration, or safe operation
depends on firmware (chargers, PMIC, load switches, boost/buck enable, sensor
config, security/lock bits). Review:

- **Bring-up sequence specified:** the firmware sequence (register writes, order,
  timing) that brings the block up must be documented and cross-checked against
  the datasheet; "it works after FW runs" is a finding, not an assumption.
- **Safe default state:** the pre-firmware hardware state must be safe — enables
  pulled to the off/default state, no rail back-driven, no latch-up.
- **Production / startup flow:** BIST/unlock/calibration (fuel-gauge, charger
  trim) must be part of the production/startup flow.
- **Document the dependency** so a "brick without FW" risk is explicit.

If the firmware sequence is not provided, report Firmware-HW co-verification as
`not verifiable`.

## CERE and Project-Specific Power Baseline

If the project references **CERE** or another internal power/reliability
baseline, locate the controlled document and record its revision. Do not expand
or reinterpret the acronym from memory. At minimum, map the baseline to:

- input and rail voltage/current limits;
- efficiency and thermal limits;
- ripple/noise and load-transient limits;
- startup, shutdown, UVLO/OVLO, sequencing, and recovery;
- short-circuit, over-current, over-temperature, reverse-current, and surge
  behavior;
- required measurements, fixtures, tolerances, and pass/fail evidence.

If the CERE document, revision, or acceptance data is missing, add a
`not verifiable` finding rather than claiming compliance.

## Required Report Coverage

The final report must include a short coverage table, even when a feature is
absent:

| Check | Trigger/evidence | Status | Finding or evidence location |
|---|---|---|---|
| System block diagram | file/page or missing | confirmed/finding/not verifiable | location |
| Power tree | file/page or missing | confirmed/finding/not verifiable | location |
| ESD and external boundaries | ports reviewed | confirmed/finding/not verifiable | location |
| Battery thermal/energy | battery trigger or N/A evidence | confirmed/finding/not applicable/not verifiable | location |
| Antenna matching | RF trigger or N/A evidence | confirmed/finding/not applicable/not verifiable | location |
| USB-C CC | USB-C trigger or N/A evidence | confirmed/finding/not applicable/not verifiable | location |
| 4G burst power | modem trigger or N/A evidence | confirmed/finding/not applicable/not verifiable | location |
| Motor transient power | motor trigger or N/A evidence | confirmed/finding/not applicable/not verifiable | location |
| Low-power design | battery/portable/always-on or low-power claim | confirmed/finding/not applicable/not verifiable | location |
| EMC/EMI | any clock/switcher/radio/cable or emission/immunity target | confirmed/finding/not applicable/not verifiable | location |
| Safety (electrical) | mains/isolation/battery/user-voltage or safety class | confirmed/finding/not applicable/not verifiable | location |
| Thermal management | high-power/power-dense/enclosure or temp target | confirmed/finding/not applicable/not verifiable | location |
| DFM/DFT readiness | production design | confirmed/finding/not applicable/not verifiable | location |
| Firmware-HW co-verification | any HW gated by firmware | confirmed/finding/not applicable/not verifiable | location |
| CERE/project power baseline | controlled doc or missing | confirmed/finding/not verifiable | location |

The coverage table is not a substitute for dimension findings. It is the audit
trail proving that conditional checks were considered.
