# EE Review

[简体中文](README.zh-CN.md)

An electronics engineering design-review skill for schematics, PCB layouts, and BOMs. The skill produces an evidence-based HTML report and can produce a review deck when requested.

## Install for Codex

1. Clone or download this repository.
2. Copy the entire `ee-review` folder, including `SKILL.md`, `scripts/`, `references/`, and `assets/`, into the user skills directory as `~/.agents/skills/ee-review`.
3. Start a new Codex session so it discovers the skill.
4. Ask for an electronics design review, for example: "Review this schematic and BOM using the ee-review skill."

On Windows, use `%USERPROFILE%\.agents\skills\ee-review` as the destination. Keep the folder name `ee-review` aligned with the `name` in `SKILL.md`.

## Runtime requirements

The Python review scripts use the Python 3.11 standard library. The CI suite is tested on Python 3.11. Install additional tools only for workflows that need them:

| Workflow | Additional requirement |
| --- | --- |
| KiCad schematic parsing and PCB conversion | KiCad 8 or later, with `kicad-cli` available on `PATH` |
| System and power diagrams | Graphviz `dot` |
| Altium project connectivity parsing | `uv` and the pinned `altium-monkey==2026.9.22` package; see [Altium parsing](references/altium-monkey.md) |
| Schematic/image crops for review decks | Pillow: `python3 -m pip install -r requirements-pptx.txt` |
| Skill structure validation | PyYAML and the Codex `quick_validate.py`; run `python3 scripts/validate_skill.py` |
| PADS automated export | PADS Layout on Windows; otherwise follow the manual export guide |

Distributor availability and lifecycle checks require network access to the relevant distributor pages, or a dated user-provided export. Do not substitute remembered stock data.

## Verify

Run the automated tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the skill structure validator in a Codex environment with PyYAML installed:

```bash
python3 scripts/validate_skill.py
```

## Sharing and licensing

This repository is suitable for access-controlled internal sharing. Give colleagues read access to the repository, or distribute a copy of the skill directory using the installation steps above. The repository does not currently grant an open-source license. Do not publish it publicly or redistribute it outside the organization until the rights holder has approved a license and repository visibility. Review the bundled template and reference material for any company-specific ownership or distribution restrictions before external release.

## Scope

The skill supports engineering review; it does not replace simulation, laboratory measurements, EMC testing, certification, or a qualified safety assessment. Every conclusion must remain bounded by the provided design evidence and the cited device documentation or controlled standards.
