# EE Review

[简体中文](README.zh-CN.md)

An electronics engineering design-review skill for **schematics, netlists, and BOMs**. It produces an evidence-based HTML report and, when requested, a review deck.

**PCB layout review is out of scope.** Do not use this skill to grade `.kicad_pcb`, Gerber sets, or board geometry. Ask for schematic, netlist, or BOM evidence instead.

## Install

Copy the entire repository folder (including `SKILL.md`, `scripts/`, `references/`, and `assets/`) so the folder name stays `ee-review`, matching the `name` in `SKILL.md`. Prefer a symlink to the git checkout so updates apply without re-copying.

| Host | Destination |
| --- | --- |
| Codex | `~/.agents/skills/ee-review` |
| WorkBuddy / CodeBuddy | `~/.agents/skills/ee-review` (same user skills directory as Codex on this machine) |
| Cursor | `~/.cursor/skills/ee-review` |

Windows Codex / WorkBuddy destination: `%USERPROFILE%\.agents\skills\ee-review`.

After install:

1. Start a **new** agent session so the host rediscovers the skill.
2. Ask for a schematic/BOM review, for example: `Review this schematic and BOM using the ee-review skill.`
3. If an older `schematic-review` skill is also installed, remove or disable it; both fire on the same requests and will fight.

Do not install only `SKILL.md`. The review commands and checklists live under `scripts/` and `references/`.

## Runtime dependency matrix

| Dependency | Required? | Needed for |
| --- | --- | --- |
| Python 3.11+ (stdlib only for review scripts) | **Required** | Parsers, HTML report, PPT text fill, tests |
| Design inputs (schematic PDF / netlist / BOM) | **Required** | Any real review |
| KiCad 8+ / `kicad-cli` | Optional | Exporting KiCad `.kicad_sch` to `kicadxml`; cropping KiCad symbols. Not needed if an XML netlist is already supplied |
| Graphviz `dot` | Optional | System block diagram and power-tree PNG/SVG |
| Pillow (`requirements-pptx.txt`) | Optional | Drawing boxes/arrows on schematic or datasheet crops for the PPT |
| `uv` + `altium-monkey==2026.9.22` | Optional | Native Altium `.PrjPcb` connectivity; see [Altium parsing](references/altium-monkey.md) |
| Network to LCSC / Digi-Key / Mouser / Arrow / Avnet, or a dated export | Optional | Stock, price, lead time, lifecycle. Without it those rows stay `not verifiable` |
| PyYAML + Codex `quick_validate.py` | Optional (maintainers) | `python3 scripts/validate_skill.py` only. Prefer a venv: `python3 -m venv .venv && .venv/bin/pip install -r requirements-validation.txt` |
| PADS on Windows | Optional | Automated PADS schematic/netlist export; otherwise use the manual export guide |

**Everyday reviews do not need PyYAML.** System Python without PyYAML is fine for parsers, HTML, and PPT fill. Install PyYAML only when you run the maintainer validator.

CI is tested on Python 3.11. Local runs on newer CPython 3.x are fine for the stdlib scripts. PCB layout tools are not part of the review contract.

Version is the single-line [VERSION](VERSION) file; see [CHANGELOG.md](CHANGELOG.md). Current package: **0.3.0**.

## Verify

```bash
python3 tests/test_ee_review.py
python3 scripts/check_package_hygiene.py
```

With a venv that has PyYAML (and the Codex validator available) — **not required for day-to-day reviews**:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-validation.txt
.venv/bin/python scripts/validate_skill.py
```

Acceptance baseline (desensitized KiCad XML netlist + BOM + HTML/PPT):

```bash
python3 scripts/parse_kicad_netlist.py examples/acceptance-demo/demo_board.xml
python3 scripts/generate_report.py \
  examples/acceptance-demo/ee-review/review.json \
  examples/acceptance-demo/ee-review/DEMO_design_review_20261103.html
python3 scripts/generate_pptx.py \
  examples/acceptance-demo/ee-review/deck.json \
  -o examples/acceptance-demo/ee-review/DEMO_design_review_20261103.pptx
```

See [examples/acceptance-demo/README.md](examples/acceptance-demo/README.md).

### WorkBuddy / Codex install smoke

After linking or copying this folder to `~/.agents/skills/ee-review` (Windows:
`%USERPROFILE%\.agents\skills\ee-review`):

1. Confirm `~/.agents/skills/ee-review/SKILL.md` and `VERSION` are readable.
2. Quit and relaunch WorkBuddy (or start a **new** agent session) so skills rediscover.
3. Ask: `Review this schematic using the ee-review skill.` with a netlist or schematic attached.
4. Confirm the agent loads `ee-review` (not a stale `schematic-review`) and does not ask to install PyYAML for the review itself.

`scripts/smoke_workbuddy_install.sh` checks the install path structure; the host UI relaunch is still a one-time manual click.

## Sharing and licensing

This repository is suitable for access-controlled **internal** sharing. Give colleagues read access to the repository, or distribute a copy of the skill directory using the installation steps above.

See [LICENSE](LICENSE): proprietary / all rights reserved. Do not publish publicly or redistribute outside the organization until the rights holder grants a broader license and sets repository visibility. The bundled PPT template is desensitized for company name/logo traces; re-scan before any external drop.

## Legacy scripts (not part of review)

`scripts/convert_layout.py`, `pads_full_converter.py`, `pads_route_injector.py`,
`pads_common.py`, `pads_export_all.bas`, and `pads_export.bat` are **legacy /
not part of review**. New contributors should not run them during an ee-review
session. Layout conversion docs in `references/file-preparation-guide.md` are
offline helpers only.

## Scope

In scope: schematic / netlist electrical review, BOM and sourcing checks, architecture diagrams when required, and an optional review PPT.

Out of scope: PCB layout, stackup, routing geometry, Gerber visual review, and substituting this skill for simulation, lab measurement, EMC testing, certification, or a qualified safety assessment. Every conclusion must stay bounded by the provided design evidence and the cited device documentation or controlled standards.
