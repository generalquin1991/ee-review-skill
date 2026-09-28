# Review contract

Every checklist row is a decision, not a reminder to look. Record it with all six fields. If a field cannot be filled from a file you opened in this review, the row is `not verifiable`.

| Field | What to write |
|---|---|
| Trigger | The feature, part, or net that makes this check apply. If the trigger is absent, status is `not applicable` and cite the file that shows the absence. |
| Evidence | The file, sheet, ref.pin, net, BOM line, or layout object the verdict uses. |
| Pass | The observable condition that closes the check. |
| Fail | The observable condition that opens a finding. |
| Severity | `critical`, `warning`, or `info`, already capped by the rules below. |
| Citation | Local datasheet PDF in `ee-review/datasheets/`, plus the document title, revision if the file shows one, and the table or section. "Per datasheet" with no file is not a citation. |

## Status vocabulary

Use only `confirmed`, `finding`, `not applicable`, or `not verifiable`.

- `confirmed` requires the evidence cell and the citation when the pass condition depends on a datasheet or standard.
- `finding` uses the same six fields. The recommendation states the change that would meet Pass.
- `not applicable` names the input that shows the trigger is absent. Do not infer it because a reference designator was unrecognized.
- `not verifiable` names the missing file. Do not emit a finding, and do not write `confirmed`.

Forbidden as a status, a finding title, or the whole evidence cell: "checked", "reviewed", "verified", "looks fine", "已检查", "已确认". A dimension with no proven fail and no proven pass is `not verifiable`, not a passing grade filler.

## Datasheets on disk

Before a row that depends on a datasheet, save that PDF under `<project>/ee-review/datasheets/`. Name the file from the manufacturer part number. If the user already supplied the PDF, copy it there and cite that copy. A browser page that was not saved is not the citation. If the PDF cannot be saved, the row is `not verifiable` and names the missing path. Stock and lifecycle stay on the distributor rule below; a datasheet PDF is not a stock quote.

## Review output folder

Every file this review writes goes in `<project>/ee-review/`, next to the schematic or netlist. That includes the `.dot` sources, the rendered `.svg` and `.png`, schematic and datasheet crops, `deck.json`, the HTML report, and the PPT. Datasheet PDFs go in `ee-review/datasheets/`. Leave the design sources where the user put them.

## PDF and connectivity

A connectivity claim says a pin is connected, unconnected, shorted, swapped, missing from a net, or pulled to a rail. It is `critical` only when the finding quotes a `TelNetlist` or `KicadNetlist` lookup (`pin_net`, `net_pins`, `component_pins`, or `missing_pins`) for that ref and pin.

A schematic PDF, screenshot, or prose description without that lookup cannot carry a Critical connectivity finding. The maximum severity is `warning`, and the evidence cell says `PDF-only; connection not proven`. If the sheet is unreadable, the row is `not verifiable`.

A value that is printed and readable (resistor value, regulator setpoint equation, capacitor voltage marking) can still be Critical when the citation shows that value exceeds an absolute maximum or a required setpoint. That is a value claim, not a connectivity claim.

## Distributor stock and lifecycle

This skill does not include a distributor client. Stock, price, lead time, MOQ, and lifecycle are `not verifiable` unless this review cites one of:

- a page fetched in this session, with URL, retrieval date, and the stock and lifecycle strings copied from that page, or
- a user-supplied distributor export or screenshot that shows the date, the manufacturer part number, and those strings.

Check order when a fetch or export exists: LCSC (szlcsc) first, then Digi-Key, Mouser, Arrow, Avnet. A miss at LCSC is not a finding by itself; name the next source that actually appears in the evidence and the price delta shown there.

Training data, memory, and "usually in stock" are not evidence. If the page does not load, write `not verifiable`. Do not invent a quantity, a lead time, or an NRND flag. An Obsolete or EOL finding is allowed only when the fetched page or the user export shows that status for the full MPN.

## Architecture diagrams

A multi-board design requires the system block diagram in `references/architecture-diagrams.md`. Do not ask to skip it. A battery product requires the power tree. The source-sag review in `references/schematic-review.md` applies to every shared upstream node, with or without a battery. For a single board that is not battery powered, draw the system block diagram or the power tree when the topology would change a finding. If you decide that diagram is not needed, ask the user before skipping it. The power tree of a non-battery multi-board design still follows that ask.

BOM-only, Gerber-only, or a PCB with neither schematic nor netlist: do not infer a block diagram from a parts list. Ask the user, and ask for a schematic or netlist if they want the drawing. After they confirm a skip, or when there is still nothing to draw from, the row is `not applicable`, evidence `no schematic or netlist in this review`.

If the diagram is needed and the file is missing, that row is `not verifiable` and Power Supply Design gets a warning that names the missing `.dot` path. Do not treat a verbal description as the diagram.

## Grade policy

Score each dimension from 100. Deduct 15 for each Critical, 5 for each Warning, 1 for each Info. Floor at 0.

Map the score to a letter:

| Score | Letter |
|---|---|
| 90–100 | S |
| 80–89 | A |
| 65–79 | B |
| 50–64 | C |
| < 50 | D |

Then apply one cap, to the dimension letter and to the overall letter:

- Any Critical finding in a dimension caps that dimension at C. A score already below 50 stays D.
- Any Critical finding in the review, or any dimension letter D, caps the overall letter at C. A weighted overall score already below 50 stays D.

S, A, and B therefore require zero Critical findings in that scope. One Critical is enough. There is no separate "three Criticals" rule.

Weighted overall score uses weight 1.5 for Power, Signal Integrity, Protection, Safety, and Low-Power on a battery, portable, or power-constrained design. Other dimensions use weight 1.0. Map that weighted score to a letter, then apply the cap. `scripts/generate_report.py` enforces the cap when it renders the HTML report.
