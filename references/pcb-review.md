# PCB layout review — out of scope

This skill does **not** review PCB layout.

Do not open stackup, impedance, return-path, copper-current, decoupling-distance, routing-quality, solder-mask, paste, via, courtyard, silk, or Gerber findings from a `.kicad_pcb`, Gerber set, or converted board file. Do not convert a layout only so you can invent those findings. Do not score a PCB layout dimension.

If the user asks for a layout review, say that PCB layout review is out of scope for this skill, and continue with schematic, netlist, and BOM work when those files are present.

Symbol-to-datasheet pin name and number checks live in `references/schematic-review.md`. Package-code matching against the BOM lives in `references/bom-review.md`. Those are not layout reviews.

Conversion helpers under `scripts/convert_layout.py` and the PADS injectors may remain in the repository for other workflows. They are marked **legacy / not part of review** and are not part of the review contract. Do not run them during an ee-review session.
