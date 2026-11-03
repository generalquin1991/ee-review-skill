# Changelog

All notable changes to this skill package are documented here. Version matches
the single-line `VERSION` file at the repository root.

## 0.3.0 — 2026-11-03

### Added

- `LICENSE` (proprietary / all rights reserved; internal sharing only until a
  broader grant exists)
- `VERSION` and this `CHANGELOG`
- Package-hygiene checks: PPT brand scan, acceptance demo smoke, VERSION sync
- Hardened PPT rule: conclusion text must match the crops on that finding

### Changed

- Slimmed `SKILL.md`; operational detail stays in `references/`
- Desensitized `assets/review-slide-template.pptx` (removed company name/logo traces)
- Clarified that PyYAML is maintainer/validation-only; everyday reviews need only
  the stdlib review scripts
- Marked layout conversion helpers as **legacy / not part of review**

### Notes

- PCB layout review remains out of scope (unchanged contract)
