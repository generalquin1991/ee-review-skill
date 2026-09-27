# Schematic review checks

Apply `references/review-contract.md` to every row. The Pass and Fail columns are the verdict. If the Evidence file is not in the review, record `not verifiable` and do not open a finding. Severity in the table is the ceiling after the PDF connectivity rule: a connectivity fail on a PDF with no parser lookup is at most `warning`.

Citation means a document you opened. Copy the table or section id into the finding. A blank citation on a pass that depends on a datasheet makes the row `not verifiable`.

## 1. Power

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Rail has a source | A named load rail (3V3, 1V8, AVDD, PVDD, VBAT, VBUS) | Power-tree `.dot` plus `net_pins` for that rail, or the PDF sheet if no netlist | Every IC power pin on that rail shares a net with a regulator output, a battery pin, or VBUS | A power pin's net has no source pin | critical with netlist; warning on PDF | Regulator or PMIC pin table |
| Current headroom | Regulator, load switch, or USB source feeding a known load | BOM current limit and a load list (datasheet typ/max, or measured) | Source Iout ≥ 1.3× the sum of maximum loads on that rail, including the stated peak | Sum of known maximum loads > source Iout | critical when both numbers are cited; otherwise not verifiable | Source DS output-current spec; load DS supply current |
| Required local capacitor | IC power, PLL, RF, REF, or ADC pin whose datasheet names a capacitor | `net_pins` of that pin, capacitor refs on the same net, values from schematic or BOM | The DS-required value and dielectric are on that net | The named pin's net has no capacitor, or the value contradicts the DS | critical with netlist + DS; warning on PDF | DS power-supply / layout section, not a universal 0.1 µF + 10 µF rule |
| Capacitor voltage rating | Every capacitor, including coupling, bypass, and bulk parts | Rated voltage from the BOM or the schematic; the DC voltage across the two pins from the nets | Rated voltage is above the DC voltage across that capacitor | Rated voltage is below the DC voltage across it, or the rating is not printed and no datasheet was opened | critical when both voltages are known and the rating is lower; not verifiable when the rating is missing | Capacitor DS voltage rating |
| Inductor saturation | Buck, boost, or SEPIC | L, f, Vin, Vout from schematic; Isat from inductor BOM line | Isat ≥ calculated peak switch current (DC + ripple/2) | Isat < calculated peak | critical when the calculation inputs are all on the schematic or BOM | Inductor DS saturation-current spec |
| Adjustable setpoint | Regulator with an external feedback divider | Resistor values on the FB node; Vref and the DS equation | Computed Vout is within 2% of the schematic rail name, and < abs-max of every IC on that rail | Computed Vout is outside 2%, or above a cited abs-max | critical only when computed Vout exceeds a cited abs-max; otherwise warning | Regulator DS feedback equation and load IC absolute-maximum table |
| Reverse input | External DC jack, battery, or unprotected VBUS into silicon | Connector pin net traced to the first series element | A series MOSFET, ideal diode, or diode rated for the input blocks reverse current before any pin whose abs-max is 0 V reverse | The connector net reaches an IC pin with no series element, and that pin's abs-max is not rated for reverse | critical when pinout and abs-max are both cited | Connector pinout; IC absolute-maximum ratings |
| Sequencing | SoC, FPGA, or PMIC whose DS lists a required rail order | EN / PGOOD nets from the parser; DS sequence table | EN and PGOOD connections match the cited order and delay | A rail the DS requires later is hard-tied on, or an EN net is tied to the earlier rail | critical with netlist + DS table; not a finding if the DS states order does not matter | DS power-up sequence table |
| Enable default | Load switch, boost, or regulator whose EN must stay off before firmware | EN pin `pin_net` and the resistors on that net | EN is held in the DS off polarity by a resistor to a rail that exists before firmware runs | EN is the on polarity at reset, or floats | warning; critical if the on state drives current into a battery or exceeds a cited abs-max | DS EN pin description |

## 2. Clocks and buses

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Crystal load | Crystal or oscillator on an IC pin | C1, C2 values; crystal CL from BOM; MCU pin capacitance if the DS gives it | 2·CL ≈ C1 + C2 + Cstray, with Cstray stated (use 3 pF if the layout model is absent) and the result within ±2 pF of the crystal CL | No load caps on a crystal that requires them, or the computed CL is more than 2 pF off | warning | Crystal DS load capacitance; MCU oscillator section |
| I2C pull-up | SDA/SCL nets | `net_pins`; pull-up value and the rail it returns to | At least one pull-up to the IO rail, open-drain on every driver, value inside the range the DS or UM10204 allows for the speed | Net has no pull-up, or the pull-up rail is above a device's cited VIH/abs-max | critical with netlist when the pull-up is absent or the rail exceeds abs-max; warning on PDF | NXP UM10204; each device's I2C electrical table |
| Strap / boot pins | SoC boot or address strap | Each strap `pin_net` resolved to a rail or divider | The resolved level matches the boot or address table for the intended mode | The net is tied to the opposite level of the required mode | critical with netlist + boot table | DS strapping / boot table |
| CAN termination | CAN transceiver on this board | Resistor nets on CANH/CANL | 120 Ω at each end that is on this board | This board is an end node and has no 120 Ω | warning if the other end is off-board (`not verifiable` for that end); critical only when both ends are on this board and neither has 120 Ω | Transceiver DS; ISO 11898-2 |
| RS-485 termination | RS-485 transceiver | A/B resistor nets | Termination and fail-safe bias match the transceiver DS for the cable being the end | End node on this board missing the resistor the DS requires | warning; not verifiable for an off-board peer | Transceiver DS termination section |
| Unused CMOS input | Datasheet input pin with no function in this design | `missing_pins` against `lib_pins`, or `pin_net` for the tied net | Tied to a rail through the resistor or short the DS allows, or configured by a cited default | Input pin appears in no net | warning | DS pin description, unused-pin section |

## 3. Protection and external ports

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| External-port clamp | Connector pin that leaves the enclosure (USB, jack, header, antenna, SIM) | Connector pin `pin_net`; protection part on that net | A TVS, series ferrite plus clamp, or a port IC whose DS claims the IEC level, with clamp voltage < protected-pin abs-max and standoff > the normal signal | The net has no protection part and the attached IC DS does not claim the IEC level | warning when the product ESD level is unknown; critical when the cited abs-max is below the connector's hot-plug voltage | IEC 61000-4-2 for the level; TVS DS clamp table; IC abs-max |
| Unidirectional TVS polarity | Unidirectional TVS symbol | Symbol cathode/anode and the net names on each pin | Cathode faces the positive rail or signal being clamped | Cathode is on GND while the protected net is positive | warning | TVS DS pin configuration |
| Antenna DC and match | RF port or antenna net | Series/shunt parts between RF pin and antenna | A series element and a shunt-to-ground option exist, values are DNP or populated against a cited match, and no DC short from the RF pin to ground | RF pin is a direct copper short to ground, or a fixed match is claimed with no DS/network note and no measurement | critical for a DC short proven by netlist; otherwise not verifiable for "match is correct" | RF IC reference schematic; measurement only if the user supplied it |
| USB-C CC | USB-C receptacle | CC1 and CC2 `pin_net` separately | Each CC pin reaches the Rp, Rd, or Ra the role requires, and they are not shorted together | One CC floats, both share one resistor without the DS allowing it, or a source uses Rd | critical with netlist; warning on PDF | USB Type-C spec CC model; PD controller DS |
| Cable filter | USB, HDMI, Ethernet, or other data cable, once the private EMC table in `references/conditional-review.md` selects that cable | Series common-mode choke, ferrite, or RC at the connector; DNP counts | A populated filter or a DNP footprint is on the connector side of the PHY | The pair reaches the PHY with only a TVS, and there is no DNP footprint for a choke or ferrite | warning | PHY or connector reference schematic |
| Power-entry filter | DC jack, VBUS, or mains used as power, once the private EMC table selects CE or EFT | Pi-filter, common-mode choke, or ferrite before the board-side bulk capacitor | The part or a DNP footprint is the first series element after the connector | VBUS or the DC jack net goes straight to the regulator input capacitor with no series filter and no DNP footprint | warning | Regulator or connector reference schematic |
| Antenna filter exception | 50 Ω antenna net | Matching network only | The RF pin is not loaded by a common-mode choke unless the radio reference design shows one | A CM choke or ferrite is in series with the antenna without a cited reference design | warning | Radio reference schematic |

Battery, 4G burst, and motor-stall checks stay in `references/conditional-review.md`. Use those fail conditions instead of restating them here.

## 4. Low power (battery, portable, always-on)

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Standby budget | Battery or an explicit standby-life target | Cell capacity and a measured standby current, or a spreadsheet the user supplied | Measured standby × required hours ≤ usable cell energy between the cited charge and cutoff voltages | The budget uses only active current, or only sums datasheet typical Iq | not verifiable when no measurement is supplied; warning if a supplied budget misses an always-on block you can see | Cell DS discharge curve; regulator Iq spec |
| Gated domain back-drive | Load switch or FET that claims a domain is off | Off-state nets: pull-ups, TVS diodes, and bidirectional IO pins from the parser | No resistor, clamp diode, or IO pin connects the gated rail back to an always-on rail | A pull-up or diode on the gated rail returns to an always-on rail | warning; critical if that path charges a battery or forward-biases a GPIO | Load-switch DS; IO pin abs-max injection current |
| Always-on Iq | Regulator that stays enabled in ship or standby | EN net and the Iq line in the DS | The always-on regulator's cited Iq is in the standby budget, and unused regulators have EN in the off state | A switcher or LDO with milliamp Iq is left enabled on the always-on rail | warning | Regulator DS quiescent-current table |
| Ship / storage | Battery product | A switch, FET, or charger ship pin in the netlist | A ship or undervoltage path can disconnect the cell without a user button held | The cell stays connected through a path with no cutoff and no cited ship mode | warning | Charger or protector DS ship-mode section |

## 5. Safety, test, firmware

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Mains barrier | AC primary, transformer, or optocoupler between mains and secondary | Isolation component DS and the net names on each side | The barrier part's cited isolation rating matches the declared safety class, and primary nets do not share a net name with secondary | A primary net and a secondary net are the same net, or the barrier part's cited rating is below the declared mains | critical when the short or the rating gap is cited; creepage distance is not verifiable from a schematic | IEC 62368-1 insulation; barrier-part DS |
| Accessible voltage | A node marked accessible, or a connector the user can touch | Rail voltage annotation and the safety class the user named | Touchable nets stay inside the cited SELV/ES1 limit | A touchable connector pin is on a net annotated above that limit with no barrier | critical when the voltage annotation and the class are both in the files; otherwise not verifiable | IEC 62368-1 voltage limits for the named class |
| Programming header | Production firmware | SWD, JTAG, or UART nets | A header or test points reach the programming pins, and the pin order is cited | No net from the programming pins reaches a header or test point | warning | MCU DS debug pinout |
| Firmware-off safe state | Charger, PMIC, or boost the user says is configured in firmware | Default register or strap state from the DS, and EN nets | With no firmware, EN and default registers stay inside the safe ranges in the DS | The DS default enables charging, a boost, or a load that the hardware text says firmware must turn on | warning; critical if the default exceeds a cited battery or abs-max limit | DS power-on default / register reset table |

Layout spacing, copper weight, and creepage in millimetres are PCB evidence. On a schematic-only review those rows are `not verifiable`, not a pass.

## 6. Resistors and capacitor bias

Check every resistor that has a printed value, and every capacitor that sees a DC voltage. A value you cannot read is `not verifiable` for that reference. Do not pass the rest of the board as a substitute.

### E96 resistors

Compare the resistance to IEC 60063 E96. Divide by decades until the mantissa is in `[1.00, 10.00)`. It must equal one of these numbers, not a nearby E24 number. `2.2` is not `2.21`. `4.7` is not `4.75`.

`1.00 1.02 1.05 1.07 1.10 1.13 1.15 1.18 1.21 1.24 1.27 1.30 1.33 1.37 1.40 1.43 1.47 1.50 1.54 1.58 1.62 1.65 1.69 1.74 1.78 1.82 1.87 1.91 1.96 2.00 2.05 2.10 2.15 2.21 2.26 2.32 2.37 2.43 2.49 2.55 2.61 2.67 2.74 2.80 2.87 2.94 3.01 3.09 3.16 3.24 3.32 3.40 3.48 3.57 3.65 3.74 3.83 3.92 4.02 4.12 4.22 4.32 4.42 4.53 4.64 4.75 4.87 4.99 5.11 5.23 5.36 5.49 5.62 5.76 5.90 6.04 6.19 6.34 6.49 6.65 6.81 6.98 7.15 7.32 7.50 7.68 7.87 8.06 8.25 8.45 8.66 8.87 9.09 9.31 9.53 9.76`

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Resistor is E96 | Every resistor with a value, including DNP parts that print one | Schematic value, or the BOM resistance and tolerance when the BOM is in the review | Mantissa is in the E96 list above. A stated tolerance is ±1% or tighter. `0 Ω` is a jumper and is not scored | Mantissa is not in the list, or the stated tolerance is wider than ±1% | warning. One finding per off-grid value, naming every reference that uses it | IEC 60063 E96 |

A value that a cited IC equation requires exactly, and that is not on the list, is an explicit accept for that reference. Name the equation. Do not silently treat it as E96.

### Capacitor DC bias

The voltage-rating row in section 1 still applies to every capacitor. DC bias is a second check of the capacitance that remains at that voltage.

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Class II DC bias | X5R, X7R, X6S, X7S, Y5V, or any ceramic that is not C0G/NP0 | Rated voltage, dielectric, rail or pin-to-pin DC voltage, and the capacitor DC-bias curve | At the actual DC voltage, the curve still provides the capacitance the circuit or the IC datasheet requires | No bias curve was opened, or the remaining capacitance is below the required value. A rating under 2× the DC bias does not pass without that curve | warning. Critical only when the remaining capacitance contradicts a value the IC datasheet requires and both numbers are cited | Capacitor DS DC-bias curve |
| Class I bias | C0G or NP0 | Dielectric on the BOM or schematic | DC-bias loss is not a finding. The voltage-rating row still applies | Dielectric is unmarked, so the part was treated as Class II | not verifiable until the dielectric is known | Capacitor DS dielectric |
| Polarized derating | Electrolytic or tantalum with a DC voltage across it | Rated voltage and the DC bias | Tantalum DC bias ≤ 50% of rated voltage. Electrolytic DC bias ≤ 80% of rated voltage, and below the rating | Tantalum bias above half the rating, or electrolytic bias above 80% of the rating | warning; critical when bias exceeds the rated voltage | Capacitor DS voltage-derating section |

## 7. MCU and SoC minimum system

Trigger on every microcontroller and every SoC in the design. Open that part's datasheet minimum-system or hardware-design figure. Check every part on that figure for the features this design uses. An internal oscillator or an internal reset passes only when the figure or the clock/reset section says that option is valid and the pins are tied the way that option requires. If the figure was not opened, this coverage row is `not verifiable`. Do not mark it confirmed from the crystal row or the boot-strap row alone.

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Supply capacitors | Each VDD, VDDIO, VDDA, VDD_CORE, or VCAP pin the figure shows | `net_pins` of that pin and the capacitors on it | Value, count, and dielectric match the figure or the power-pin table | A listed supply pin has no capacitor, or the value contradicts the table | critical with netlist and the table; warning on PDF | DS power supply / minimum system |
| Reset | NRST, RESET, or nPOR on the figure | `pin_net` and the resistor, capacitor, or supervisor on that net | The net matches the figure, including a required pull-up or capacitor | The pin floats, or a part shown on the figure is absent | warning; critical when the datasheet says an open reset pin prevents boot and the netlist shows it open | DS reset / minimum system |
| Clock | Clock pins on the figure | Crystal, oscillator, or the internal-clock tie | Load capacitors match the crystal CL row in section 2, or the internal clock is selected and the pins are tied as that section requires | The boot source needs a crystal and the pins have none, or the load capacitors contradict the crystal | warning | DS oscillator section |
| Boot and debug | Strap pins and the programming pins the figure shows | Strap row in section 2, and the programming-header row in section 5 | Both rows pass for this part | Either row fails | The severity of the failed row | DS boot table; DS debug pinout |
| Figure parts | Any other part drawn on the minimum-system figure for a feature this design uses | That reference's net | The part is present at the value the figure prints | The figure shows it and the net does not | warning | DS minimum-system figure |
