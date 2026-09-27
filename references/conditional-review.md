# Conditional and Mandatory Hardware Review Matrix

Use this matrix for every hardware review. Record each item with the six fields in `references/review-contract.md`: trigger, evidence, pass, fail, severity, citation. Status is only `confirmed`, `finding`, `not applicable`, or `not verifiable`. Never infer `not applicable` only because a symbol or reference designator was not recognized. A row whose text is only "checked" or "已检查" is invalid.

## Evidence gate

Before scoring an electrical dimension, record where each of these came from. If the file is missing, the coverage row is `not verifiable` and names the missing file. Do not add a finding that only says the item was checked.

1. **System block diagram and power tree** — a multi-board design requires the system block diagram (`references/architecture-diagrams.md`); do not ask to skip it. A battery product requires the power tree. The source-sag row in `references/schematic-review.md` applies to every shared upstream node, with or without a battery. Otherwise decide each diagram, draw it when the topology would change a finding, and ask the user before skipping one you think is unnecessary. BOM-only, Gerber-only, or a PCB with neither schematic nor netlist: do not invent a drawing; ask, and use `no schematic or netlist in this review` only after they confirm a skip or there is still nothing to draw from.
2. **Operating envelope** — input range, battery range, temperature, peak and steady loads, startup and shutdown. If the user did not provide it, claims about margin stay `not verifiable`.
3. **Compliance target** — ESD level, emissions class, safety class, or a named project baseline such as CERE. If unnamed, do not invent one.

A schematic that shows rails but has no power-tree file has not closed the power architecture. When a schematic or netlist is present and the `.dot` file is missing, add a warning under Power Supply Design and mark the coverage row `not verifiable`.

Connectivity findings follow the PDF rule in `references/review-contract.md`: no Critical connectivity claim without a `TelNetlist` or `KicadNetlist` lookup.

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

Missing ESD evidence is `not verifiable` when the connector pin net cannot be traced. An exposed interface with no clamp is Critical only when a netlist lookup shows the connector pin has no protection part and a cited absolute maximum is below the hot-plug voltage on that net. On a PDF with no parser lookup the ceiling is warning.

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
- **Charge by default:** apply the charge-by-default row in
  `references/schematic-review.md`. Plugging in the adapter must start a charge
  that the cell datasheet allows, without the host running.
- **Power path and full charge:** apply that row in `references/schematic-review.md`.
  Decide from the nets whether the running load shares the cell or is fed from
  the adapter on a separate power-path pin. A shared cell node charges to full
  only when the on-state load is below the termination current. Name the
  missing running-load current as `not verifiable` instead of assuming the cell
  finishes.
- **Pack protection and PTC:** when the cell connector goes to the charger
  without a protection IC or back-to-back FETs on this board, ask whether the
  pack includes a protection board and a series PTC. Apply that row in
  `references/schematic-review.md`. The charger's TEMP/NTC pin is not the PTC.
- **Power-tree topology:** draw the power tree, then apply the regulator-under-source-sag row in `references/schematic-review.md` to every regulator on the cell. Any high-peak load on that cell sets the sag, including audio, a motor, a radio burst, or another cited peak. The cell is one upstream node; the same row also covers VBUS, an adapter, and an intermediate rail.
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

### EMC and safety applicability (private)

Before the EMC or safety checks, decide which phenomena apply. Use the schematic and, when the user supplied one, the PRD. Keep this list in the working notes. Do not put it in the HTML report or the PPT: no slide and no paragraph that says which of RE, CE, RS, CS, EFT, surge, or a safety standard "applies".

| What the schematic or PRD shows | Review the design against |
|---|---|
| Mains inlet | CE, EFT, surge, and the barrier / fuse / Y-capacitor parts |
| DC jack, USB VBUS, or other cable used as power | CE and EFT on that cable; ESD on the connector |
| USB, HDMI, Ethernet, or another data cable that leaves the enclosure | RE and RS via the cable, plus CE, CS, and EFT if the cable also carries power or is long |
| Battery only, no cable and no mains | Switcher and radio RE only; do not invent cable CE, CS, or EFT findings |
| Radio antenna | RE and RS of the RF path; do not treat a 50 Ω antenna net as a place for a common-mode choke unless the radio reference design puts one there |
| Motor or other inductive lead | EFT and CE on that lead |

A TVS is the ESD clamp. It is not by itself a filter for RE, CE, RS, CS, or EFT.

### EMC / EMI (radiated & conducted emissions, immunity)

Trigger on any clock above ~1 MHz, switching regulator, radio, cable, motor, or a PRD emissions line. Review only the rows selected above. Write findings as missing or present parts, not as the applicability judgment.

- **RE:** a clock or switch node that can leave on a cable needs a series damping resistor or a common-mode choke / ferrite at the connector. The shield pin of that connector returns to the chassis or connector ground at the connector, not through a long trace.
- **CE:** a power cable has a pi-filter, common-mode choke, or ferrite before the rest of the board. The part, or a DNP footprint for it, sits on the connector side of the first bulk capacitor.
- **RS and CS:** the same cable filter is the immunity part. An analog or I/O net that runs from a connector to an IC with no series impedance and no DNP footprint is a finding.
- **EFT:** a cable longer than an on-board jumper has a ferrite or common-mode choke and a clamp at the entry. A logic net that crosses the connector with neither is a finding.
- **Reserved filter:** a DNP footprint for the choke, ferrite, or extra capacitor counts as provision. Say whether it is populated or DNP. No footprint at all, on a cable the private table says needs a filter, is a finding that asks for the footprint even if the part stays DNP on the prototype.
- **Antenna exception:** do not call a missing choke on the RF antenna net a CE/RE fix.

If the private table selects a cable phenomenon and the connector net has neither a filter nor a DNP footprint, the EMC coverage status is `finding`. If the product has no cable, no switcher, and no radio, EMC is `not applicable` and the report does not explain the phenomena that were skipped.

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

Use the same private table as EMC. A battery product with no mains and no isolation barrier does not get a creepage finding, and the report does not say which safety standard was considered. When mains or a barrier is actually on the schematic, the finding names the fuse, Y capacitor, or barrier part that is missing or underrated. If the PRD names a safety class and the schematic has mains, but the barrier rating cannot be read, Safety is `not verifiable` and the report names the missing datasheet, not the class-selection step.

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

### Component Availability (Sourcing)

Trigger on any BOM, component list, or design that names purchasable parts
(always for production designs). Review the procureability of every major
component (ICs, key passives, connectors, mechanicals):

- **Source evidence:** this skill has no distributor client. Stock, lead time, and lifecycle are `not verifiable` until a page fetched in this session or a dated user export quotes them. When that evidence exists, read **LCSC (szlcsc.com) first**, then **Digi-Key**, **Mouser**, **Arrow**, **Avnet**. A miss at LCSC is not a finding; name the next source that appears in the evidence and the price delta printed there.
- **Lifecycle status:** Active, NRND, EOL, or Obsolete only as written on that page. Do not assign NRND or EOL from memory. Obsolete or past last-time-buy with no alternate on the BOM is Critical. NRND is a warning.
- **Stock & lead time:** compare the page's stock and lead time with the build quantity the user stated. Flag lead time above 16 weeks only when the page shows it.
- **Second source:** a pin-compatible alternate on the BOM, or an explicit sole-source note. A missing second source is a warning, not a Critical, and only when the BOM is in the review.
- **MOQ / packaging:** MOQ reasonable for production volume; tape-and-reel /
  MSL documented for SMT.

Record the page URL or export filename and the quoted status for each flagged
part. If no BOM or component list is provided, report Component Availability as
`not applicable`. If a BOM is present and no page or dated export was fetched,
report it as `not verifiable`. Do not write "in stock" or "Active" from memory.

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

### Passives and minimum systems

When the schematic or BOM contains resistors, check every printed value against IEC 60063 E96 as specified in `references/schematic-review.md`. `0 Ω` is a jumper. Report every non-E96 value together in one finding, unless a cited IC equation requires that exact value.

When capacitors are present, check the voltage rating of every capacitor against the DC voltage across it, and the DC-bias loss of every Class II ceramic. C0G/NP0 does not get a bias-loss finding. Electrolytic and tantalum parts use the derating in that same section. A missing voltage rating is `not verifiable` for that capacitor.

When the design contains a microcontroller or an SoC, check that part's minimum system against its datasheet figure: supply capacitors, reset, clock, boot straps, debug pins, and every other part the figure shows for a feature this design uses. No MCU or SoC in the design means `not applicable`. The figure was not opened means `not verifiable`.

## Required Report Coverage

The final report must include a short coverage table, even when a feature is
absent:

| Check | Trigger/evidence | Status | Finding or evidence location |
|---|---|---|---|
| System block diagram | schematic or netlist present; else not applicable | confirmed/finding/not applicable/not verifiable | `.dot` path, or `no schematic or netlist in this review` |
| Power tree | schematic or netlist present; else not applicable | confirmed/finding/not applicable/not verifiable | `.dot` path, or `no schematic or netlist in this review` |
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
| Component availability (sourcing) | BOM/component list or N/A evidence | confirmed/finding/not applicable/not verifiable | location / primary source |
| CERE/project power baseline | controlled doc or missing | confirmed/finding/not verifiable | location |
| E96 resistors | resistors on the schematic or BOM | confirmed/finding/not applicable/not verifiable | off-grid references |
| Capacitor voltage and DC bias | capacitors on the schematic or BOM | confirmed/finding/not applicable/not verifiable | capacitor references |
| MCU/SoC minimum system | an MCU or SoC, else not applicable | confirmed/finding/not applicable/not verifiable | datasheet figure and the pins |
| IO level | a net joining two logic pins | confirmed/finding/not applicable/not verifiable | driver and receiver |
| Charge by default | a charger, else not applicable | confirmed/finding/not applicable/not verifiable | CE/EN or power-on default |
| Power path and full charge | a charger, else not applicable | confirmed/finding/not applicable/not verifiable | SYS net versus battery net |
| Pack protection and PTC | a cell connector without a protector on this board | confirmed/finding/not applicable/not verifiable | pack drawing or the user's answer |
| I2C addresses | an I2C bus, else not applicable | confirmed/finding/not applicable/not verifiable | bus, device, 7-bit address |
| Clock rework footprint | a clock toward memory, a display, a camera, or another hard-to-rework interface | confirmed/finding/not applicable/not verifiable | clock net |
| High-speed termination | a net whose datasheet shows source or end termination | confirmed/finding/not applicable/not verifiable | net and the cited network |

The coverage table is not a substitute for dimension findings. It is the audit
trail proving that conditional checks were considered.
