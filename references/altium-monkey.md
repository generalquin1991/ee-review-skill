# Altium Source Parsing with altium-monkey

Use this reference whenever an Altium `.PrjPcb` project or `.SchDoc` source is
included in an EE review. The goal is to obtain semantic, project-level net
connectivity from the source files before making any connected/unconnected
claim.

## Installation

Install the pinned package in an isolated temporary environment outside the
design directory and record the installed version in the review evidence. The
current skill pin is `2026.9.22`; update this pin deliberately after testing a
new parser release.

```bash
REVIEW_TMP="$(mktemp -d)"
uv venv "$REVIEW_TMP/altium-venv"
uv pip install --python "$REVIEW_TMP/altium-venv/bin/python" "altium-monkey==2026.9.22"
```

Do not modify the design files. The package is only a read-only parser for the
review workflow.

## Project-level parse

When a `.PrjPcb` file is available, always prefer the project path over parsing
individual sheets. This preserves sheet hierarchy and lets the parser compile
logical and flattened nets:

```python
from pathlib import Path
from altium_monkey import AltiumDesign

project = AltiumDesign.from_prjpcb(Path("RRMaxMain.PrjPcb"))
compiled = project.compile(force=True)

from importlib.metadata import version
import sys

print("python", sys.version)
print("altium-monkey", version("altium-monkey"))
print(compiled.summary)
for diagnostic in compiled.diagnostics:
    print(diagnostic)
```

The parse is eligible for Critical connectivity evidence only when all of these
conditions hold:

1. `compiled.summary.has_errors` is `False`.
2. `compiled.summary.has_warnings` is `False`, or every warning is explicitly
   adjudicated in the review and none indicates an incomplete or unsupported
   source document.
3. `compiled.summary.logical_document_count` matches the project schematic
   document inventory, and the compiled component inventory is non-empty.
4. The target reference and pin exist in the compiled component/pin inventory.

If any gate fails, preserve the diagnostics and keep connectivity at
`not verifiable` or a non-critical warning. Inspect `compiled.nets`; for each
relevant net quote its `name`, `scope`, and the exact `terminals` or `endpoints`
containing the reference designator and pin.

Example evidence query:

```python
refs = {"R6", "R7", "R20", "R21"}
for net in compiled.nets:
    terminals = [
        (t.designator, t.pin, t.pin_name, t.pin_type)
        for t in net.terminals
        if t.designator in refs
    ]
    if terminals:
        print(net.name, net.scope, terminals)
```

For a cross-sheet claim, use the `compiled_flat` net when present and confirm
the expected physical/logical source sheet in the net metadata. A local sheet
net or an inter-sheet link alone is not enough to claim final flattened
connectivity.

## Sheet-only limitations

`AltiumSchDoc(path)` is useful for listing components, pins, wires, power ports,
and graphic objects on one sheet. It is not a substitute for project compile:
without `.PrjPcb`, do not assert cross-sheet connectivity or a final net name
from object coordinates alone. Request an exported pin-level netlist or mark
the connection check `not verifiable`.

## Evidence and failure handling

- Never use PDF appearance, SVG geometry, raw OLE records, `strings`, or
  component coordinates as the primary proof of a connection.
- Never call a red cross-hatched graphic a No-Connect marker unless the native
  object model exposes an explicit No-Connect object at that pin.
- Record package version, Python version, project path, compile summary,
  document/component counts, diagnostics, net name, reference, and pin for every
  connectivity finding.
- If parsing fails or diagnostics indicate an incomplete project, preserve the
  diagnostic and downgrade the connectivity check to `not verifiable` or a
  non-critical warning. Do not write an ad-hoc parser for that review.

`altium-monkey` is an open-source parser, but it does not replace a final ERC
run in Altium Designer. Use its compiled net evidence to prove source
connectivity, then separately review electrical intent, component values,
datasheet requirements, and release consistency.
