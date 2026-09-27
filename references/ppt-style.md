# Review PPT

Produce the deck only by calling the bundled commands. Do not assemble slides with a one-off script, edit slide XML by hand, or copy the template and patch it during a review. If a layout is missing, change the script in this skill, then re-run the command.

```bash
python3 scripts/crop_schematic.py <board.kicad_sch> --ref <refdes> -o crop.png
python3 scripts/crop_schematic.py --image <page.png> --box <left,top,right,bottom> -o crop.png --mark box
python3 scripts/generate_pptx.py deck.json -o <project code>_design_review_<YYYYMMDD>.pptx
```

`kicad-cli` is not always on `PATH`. The crop command also tries `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`. Netlists still go through `scripts/parse_kicad_netlist.py` or `scripts/parse_netlist.py`. Do not write a parser for this deck.

## Which conclusions become slides

A slide needs a concrete location (reference designator, net, or a datasheet table row) and one verdict sentence. That includes an explicit accept. `not verifiable`, a missing file, the coverage table, and S/A/B/C grades stay in the HTML report. They do not get a slide.

The deck body is the circuit, the number, and the verdict. Do not write why the review process included the item. Forbidden wording includes "according to the review rules", the skill name, the checklist, the coverage table, sign-off, and the grade labels Critical, Warning, Info, S, A, B, C, D. A proposed alternate part is not a slide until the user has confirmed that exact part.

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

Show the proposed cover values before writing `deck.json`. If the user changes one, use theirs.

## Slide copy

One finding per slide, in English, three to five sentences.

1. Eyebrow is the domain: `Schematic · <area>`, `BOM · <area>`, `PCB / layout`, or `DFM`.
2. Subtitle is the part or net and the parameter being judged: `<ref> — <parameter>`.
3. `problem` is one sentence stating the issue, or the accept, on a single line. At most 60 characters. The finding layout's placeholder does not wrap; a longer sentence is rejected.
4. Body states the circuit (part, value, net), then the calculation or the datasheet comparison, then one verdict.

Use only these verdict forms:

- `We recommend …` or `It is recommended to …`, followed by the part number or the value to use.
- `There are no issues with …` / `meets this requirement` / `it is deemed acceptable` when the cited numbers agree.
- `is assumed to be acceptable` when the delta is small and the reason is in the same sentence.
- `Note that …` for a behavior constraint.
- `Fix: …` when the defect and the change are both specific.
- `needs to be verified through testing` or `Please keep this in mind during <measurement>.`

Name the part and the parameter when citing a datasheet. Do not write "per the datasheet requirement" with no number.

Figures sit inside the template's existing picture frames. The command fits each picture to its own aspect ratio and centers it in that frame, so a tall crop is not stretched across the wide frame. Use one crop when one location carries the verdict: the schematic only around the parts named in the sentence, a datasheet table cropped to the cited rows with `--mark box`, or a PCB crop with `--mark arrow` and a short `--label`. Use two crops when the sentence depends on two places. A net that crosses boards gets one crop per board: the I2C pins on board A, and the pull-up that sits on board B. A sentence that cites both the schematic and a datasheet row gets both. Do not add a crop the sentence does not use. A slide has two frames; further crops continue on the next slide with the same eyebrow and subtitle. A conclusion with no picture leaves the frame out; do not insert a placeholder icon.

The text command keeps the template typeface and size. If the body does not fit, the command continues it on the next slide with the same eyebrow and subtitle. Do not shrink the type, and do not add a label that says the slide is a continuation.

## Where the picture comes from

KiCad schematic (`.kicad_sch`): export and crop with `scripts/crop_schematic.py`. Do not ask for a screenshot.

Already-supplied schematic PDF, datasheet PDF, or a saved web table: crop that file, then pass the PNG to `scripts/crop_schematic.py --image` when it needs a red box or arrow.

PADS or Altium schematic: if the existing importer and parsers do not yield a netlist, stop and ask for a netlist or a BOM, using `references/file-preparation-guide.md`. Do not write a parser in the review. If there is nothing to plot, ask for a schematic PDF and then crop that PDF. PCB files that `scripts/convert_layout.py` already accepts stay on that command.

Red lines are drawn only by `--mark` on `scripts/crop_schematic.py`.
