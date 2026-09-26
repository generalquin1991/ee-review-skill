# EE Review Optimizations Implementation Plan

> **For Codex:** Implement this plan task-by-task with focused verification after each change.

**Goal:** Improve conversion correctness, report safety, CLI behavior, and regression coverage for the EE review skill.

**Architecture:** Keep the current script-based workflow, but separate schematic conversion from PCB conversion, make export failures observable, centralize report escaping/slugging, and add standard-library tests for deterministic behavior. Defer the larger PADS parser deduplication until the shared API is covered by fixtures.

**Tech Stack:** Python 3.8+, standard library `argparse`, `html`, `json`, `unittest`; Markdown documentation.

---

### Task 1: Fix conversion type handling and export status

**Files:**
- Modify: `scripts/convert_layout.py`
- Modify: `references/file-preparation-guide.md`
- Modify: `SKILL.md`

Implement explicit schematic format handling, keep PCB exports on the PCB path, aggregate export return values, and make the CLI exit non-zero when requested artifacts fail.

### Task 2: Harden and generalize HTML report generation

**Files:**
- Modify: `scripts/generate_report.py`

Escape user-controlled text, generate safe dimension IDs, and make I2C topology titles/notes data-driven instead of project-specific.

### Task 3: Improve netlist CLI ergonomics

**Files:**
- Modify: `scripts/parse_netlist.py`

Use `argparse` for `--help`, validation, and consistent error reporting while preserving existing flag forms and library APIs.

### Task 4: Add regression tests and documentation checks

**Files:**
- Create: `tests/test_ee_review.py`

Cover format classification, failed export propagation, netlist continuation parsing, report escaping, and removal of project-specific topology defaults.

### Task 5: Verify and report remaining refactor opportunities

Run the standard-library test suite and targeted CLI help/dry-run checks. Document the remaining PADS parser duplication as a follow-up rather than risk an untested conversion rewrite.
