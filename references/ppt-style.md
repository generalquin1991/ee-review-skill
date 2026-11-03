# Review PPT

Produce the deck only by calling the bundled commands. Do not assemble slides with a one-off script, edit slide XML by hand, or copy the template and patch it during a review. If a layout is missing, change the script in this skill, then re-run the command.

```bash
python3 scripts/crop_schematic.py <board.kicad_sch> --ref <refdes> -o ee-review/<refdes>.png
python3 scripts/crop_schematic.py --image <page.png> --box <left,top,right,bottom> -o ee-review/<crop>.png --mark box
python3 scripts/generate_pptx.py ee-review/deck.json -o ee-review/<project code>_design_review_<YYYYMMDD>.pptx
```

`kicad-cli` is not always on `PATH`. The crop command also tries `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`. Netlists still go through `scripts/parse_kicad_netlist.py` or `scripts/parse_netlist.py`. Do not write a parser for this deck.

## Which conclusions become slides

A slide needs a concrete location (reference designator, net, or a datasheet table row) and one verdict sentence. That includes an explicit accept. `not verifiable`, a missing file, the coverage table, and S/A/B/C grades stay in the HTML report. They do not get a slide.

The deck body is the circuit, the number, and the verdict. Do not write why the review process included the item. Forbidden wording includes "according to the review rules", the skill name, the checklist, the coverage table, sign-off, and the grade labels Critical, Major, Minor, Okay, S, A, B, C, D. A proposed alternate part is not a slide until the user has confirmed that exact part.

Which EMC or safety phenomena apply is decided from the schematic and the PRD, when a PRD was provided, using `references/conditional-review.md`. That choice is not a slide and not a sentence. A missing USB, HDMI, or power-entry filter is a slide only as the part and the nets: populated, DNP footprint, or absent.

## Cover

The template cover keeps its background. Fill the fields from the current project. Do not reuse an identity stored from an older deck.

| Field | Where it comes from |
|---|---|
| `project_code` | Project directory name or the schematic title block. If neither exists, ask. Do not invent one. |
| `document_title` | `Design review report` unless the user names another document title. |
| `designer` | Title-block name. If it is absent, ask. Do not invent a person. |
| `reviewer` | The name the user gives for this review. If they have not, ask. |
| `review_date` | Today, `YYYYMMDD`. |

Before generating or modifying the deck, explicitly ask the user to confirm the `designer` and `reviewer` names that will appear on the cover. This is required even when those names can be read from the title block or an existing deck. Also show the proposed `project_code` and `review_date`; wait for confirmation before writing `deck.json` or the PPT. Use the user's exact names, never silently reuse an older deck's identity, and treat names already supplied in the current request as confirmation.

## Slide copy

One finding per slide, in English, three to five sentences.

1. Eyebrow is the domain: `Schematic · <area>`, `BOM · <area>`, or `DFM`. Do not use a PCB/layout eyebrow; layout review is out of scope.
2. Subtitle is the one existing line under the eyebrow. It is the one-sentence summary of the issue, or of the accept. At most 60 characters. That placeholder does not wrap, and there is no second line for the same sentence. A longer subtitle is rejected. Set `severity` to `critical`, `major`, `minor`, or `okay`. The command colors that line only: red, yellow, black, or green. Do not write the severity word in the sentence.
3. Body states the circuit (part, value, net), then the calculation or the datasheet comparison, then one verdict.

The E96 resistor finding is one slide. The body is one verdict sentence. The values are a table with columns Value, References, and Recommended, and `"single_page": true`. A list of several parts, values, or addresses is a table in the same way, not a paragraph of reference designators. Pass it as `"table": {"columns": [...], "rows": [[...]]}`.

The footprint pin check is its own slide, separate from other findings. The table lists every part whose pin table was opened, with columns Reference, MPN, Datasheet, and Result. Set `"single_page": true`. `okay` when every row matches. A disagreed pin still gets a boxed crop of that datasheet region. This is a symbol/library pin-map check, not a layout slide.

Use only these verdict forms:

- `We recommend …` or `It is recommended to …`, followed by the part number or the value to use.
- `There are no issues with …` / `meets this requirement` / `it is deemed acceptable` when the cited numbers agree.
- `is assumed to be acceptable` when the delta is small and the reason is in the same sentence.
- `Note that …` for a behavior constraint.
- `Fix: …` when the defect and the change are both specific.
- `needs to be verified through testing` or `Please keep this in mind during <measurement>.`

Name the part and the parameter when citing a datasheet. Do not write "per the datasheet requirement" with no number.

A number, equation, recommended range, pin function, or limit that the verdict takes from a datasheet is a crop of that region. Render the local PDF in `ee-review/datasheets/`, crop the equation, table rows, or figure, and box it with `--mark box`. A page number written in the sentence does not replace that crop. Keep the schematic crop when the sentence also uses the circuit. Two frames per slide; further regions continue with the same eyebrow and subtitle. An E96 equation exception is this case: the resistor table stays on one slide, and the formula crop is one of the pictures on that finding. `"single_page": true` keeps the body and the table from splitting; it still carries every datasheet crop the sentence uses.

Figures sit inside the template's existing picture frames. The command fits each picture to its own aspect ratio and centers it in that frame, so a tall crop is not stretched across the wide frame. Use one crop when one location carries the verdict: the schematic only around the parts named in the sentence, or a datasheet region with `--mark box`. Use two crops when the sentence depends on two places. A net that crosses boards gets one schematic crop per board: the I2C pins on board A, and the pull-up that sits on board B. Do not add a crop the sentence does not use. Do not crop PCB layout copper for a finding. A slide has two frames; further crops continue on the next slide with the same eyebrow and subtitle. A conclusion with no picture leaves the frame out; do not insert a placeholder icon.

## Figure must support the sentence

Before writing `deck.json` or accepting a generated slide, re-read the body and
open every crop for that finding.

1. Every reference, net, value, threshold, pin name, or path the body names must
   appear in at least one crop on that finding, **or** the crop must make the
   claimed absence visible (empty pad, missing series element, open net stub).
2. If the picture shows a part the sentence says is missing — or shows a
   different topology than the verdict — rewrite the sentence or recrop. Do not
   ship both.
3. A datasheet number, equation, recommended range, or pin function used in the
   verdict must be inside the boxed datasheet crop, not only in the prose.
4. Self-check: a reviewer who looks only at the pictures must be able to accept
   or reject the sentence without trusting unseen context. If they cannot, the
   slide fails this rule.

This is a hard gate for PPT findings, not a style preference. HTML-only rows
still follow the six-field contract; they do not get a contradictory slide.

The text command keeps the template typeface and size. If the body does not fit, the command continues it on the next slide with the same eyebrow and subtitle. Do not shrink the type, and do not add a label that says the slide is a continuation.

## Where the picture comes from

KiCad schematic (`.kicad_sch`): export and crop with `scripts/crop_schematic.py`. Do not ask for a screenshot.

Already-supplied schematic PDF, datasheet PDF, or a saved web table: copy the datasheet into `ee-review/datasheets/` first, crop that file, then pass the PNG to `scripts/crop_schematic.py --image` when it needs a red box or arrow. Write the crop into `ee-review/`.

PADS or Altium schematic: if the existing importer and parsers do not yield a netlist, stop and ask for a netlist or a BOM, using `references/file-preparation-guide.md`. Do not write a parser in the review. If there is nothing to plot, ask for a schematic PDF and then crop that PDF. Do not convert or crop PCB layout files for this deck.

Red lines are drawn only by `--mark` on `scripts/crop_schematic.py`.
