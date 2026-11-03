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

## Runtime requirements

The Python review scripts use the Python 3.11 standard library. The CI suite is tested on Python 3.11. Install additional tools only for workflows that need them:

| Workflow | Additional requirement |
| --- | --- |
| KiCad schematic netlist export / parsing | KiCad 8 or later, with `kicad-cli` available (also tried at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` on macOS) |
| System and power diagrams | Graphviz `dot` |
| Altium project connectivity parsing | `uv` and the pinned `altium-monkey==2026.9.22` package; see [Altium parsing](references/altium-monkey.md) |
| Schematic/image crops for review decks | Pillow: `python3 -m pip install -r requirements-pptx.txt` |
| Skill structure validation | PyYAML and the Codex `quick_validate.py`; run `python3 scripts/validate_skill.py` |
| PADS automated schematic/netlist export | PADS on Windows; otherwise follow the manual export guide |

Distributor availability and lifecycle checks require network access to the relevant distributor pages, or a dated user-provided export. Do not substitute remembered stock data.

## Verify

```bash
python3 tests/test_ee_review.py
```

In an environment with PyYAML and the Codex validator available:

```bash
python3 scripts/validate_skill.py
```

## Sharing and licensing

This repository is suitable for access-controlled **internal** sharing. Give colleagues read access to the repository, or distribute a copy of the skill directory using the installation steps above.

The repository does **not** currently grant an open-source license. Do not publish it publicly or redistribute it outside the organization until the rights holder has approved a license and repository visibility. Before any broader release, re-check the bundled PPT template and reference material for company-specific ownership or distribution restrictions.

## Scope

In scope: schematic / netlist electrical review, BOM and sourcing checks, architecture diagrams when required, and an optional review PPT.

Out of scope: PCB layout, stackup, routing geometry, Gerber visual review, and substituting this skill for simulation, lab measurement, EMC testing, certification, or a qualified safety assessment. Every conclusion must stay bounded by the provided design evidence and the cited device documentation or controlled standards.
