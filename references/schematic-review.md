# Schematic review checks

Apply `references/review-contract.md` to every row. The Pass and Fail columns are the verdict. If the Evidence file is not in the review, record `not verifiable` and do not open a finding. Severity in the table is the ceiling after the PDF connectivity rule: a connectivity fail on a PDF with no parser lookup is at most `warning`.

Citation means a document you opened. Copy the table or section id into the finding. A blank citation on a pass that depends on a datasheet makes the row `not verifiable`.

## 1. Power

| Check | Trigger | Evidence | Pass | Fail | Severity | Citation |
|---|---|---|---|---|---|---|
| Rail has a source | A named load rail (3V3, 1V8, AVDD, PVDD, VBAT, VBUS) | Power-tree `.dot` plus `net_pins` for that rail, or the PDF sheet if no netlist | Every IC power pin on that rail shares a net with a regulator output, a battery pin, or VBUS | A power pin's net has no source pin | critical with netlist; warning on PDF | Regulator or PMIC pin table |
| Current headroom | Regulator, load switch, or USB source feeding a known load | BOM current limit and a load list (datasheet typ/max, or measured) | Source Iout ≥ 1.3× the sum of maximum loads on that rail, including the stated peak | Sum of known maximum loads > source Iout | critical when both numbers are cited; otherwise not verifiable | Source DS output-current spec; load DS supply current |
| Required local capacitor | IC power, PLL, RF, REF, or ADC pin whose datasheet names a capacitor | `net_pins` of that pin, capacitor refs on the same net, values from schematic or BOM | The DS-required value and dielectric are on that net | The named pin's net has no capacitor, or the value contradicts the DS | critical with netlist + DS; warning on PDF | DS power-supply / layout section, not a universal 0.1 µF + 10 µF rule |
| MLCC voltage bias | Class II ceramic (X5R/X7R/Y5V) on a DC rail | Cap voltage rating and dielectric from BOM; rail voltage from schematic | Rated voltage ≥ 2× the DC bias, or the cap DS DC-bias curve still meets the required C at that bias | Rating < rail voltage, or class II rating < 2× bias and no bias curve is cited | critical if rating < rail; warning if only the 2× rule fails | Capacitor DS DC-bias curve |
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
