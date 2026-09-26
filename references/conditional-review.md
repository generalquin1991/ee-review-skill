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
| CERE/project power baseline | controlled doc or missing | confirmed/finding/not verifiable | location |

The coverage table is not a substitute for dimension findings. It is the audit
trail proving that conditional checks were considered.
