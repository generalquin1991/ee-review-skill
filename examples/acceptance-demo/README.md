# Acceptance demo board

Desensitized sample used as the skill acceptance baseline. No customer name, project code, or real cell chemistry is claimed.

## Contents

| Path | Role |
| --- | --- |
| `demo_board.kicad_sch` | KiCad schematic source (visual companion) |
| `demo_board.xml` | **Authoritative** KiCad XML netlist for parser checks |
| `bom.csv` | BOM with placeholder cell MPN and real-format passives |
| `ee-review/` | Review outputs: power tree, `review.json`, HTML, PPT, empty `datasheets/` |

Intentional finding for the baseline: **R2 = 4.7 kΩ** is outside IEC 60063 E96 (recommend 4.75 kΩ). R1 = 10 kΩ is on-grid.

## Reproduce

From the skill root:

```bash
# Netlist sanity
python3 scripts/parse_kicad_netlist.py examples/acceptance-demo/demo_board.xml

# Power tree (optional Graphviz)
dot -Tpng -o examples/acceptance-demo/ee-review/demo_power_tree.png \
  examples/acceptance-demo/ee-review/demo_power_tree.dot

# HTML report
python3 scripts/generate_report.py \
  examples/acceptance-demo/ee-review/review.json \
  examples/acceptance-demo/ee-review/DEMO_design_review_20261103.html

# Review PPT
python3 scripts/generate_pptx.py \
  examples/acceptance-demo/ee-review/deck.json \
  -o examples/acceptance-demo/ee-review/DEMO_design_review_20261103.pptx
```

Optional: re-export the netlist from KiCad after editing the schematic.

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist \
  --format kicadxml \
  -o examples/acceptance-demo/demo_board.xml \
  examples/acceptance-demo/demo_board.kicad_sch
```

If a fresh export disagrees with the checked-in XML, keep the XML as the baseline until the schematic wiring is cleaned in KiCad. Parser-backed findings must quote the XML.

## What this baseline proves

- KiCad XML parses with `parse_kicad_netlist.py`
- BOM + schematic values drive an E96 finding on one slide
- Power-tree artifacts land under `ee-review/`
- HTML and PPT generate without customer identity
- Distributor stock stays `not verifiable` without a fetched page
- PCB layout review is not attempted
