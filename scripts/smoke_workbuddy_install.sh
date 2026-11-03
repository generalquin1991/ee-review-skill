#!/usr/bin/env bash
# Install-path smoke for Codex / WorkBuddy user skills.
# Does not drive the WorkBuddy GUI; after this passes, quit/relaunch the host
# once so it rediscovers skills, then ask for an ee-review of a schematic.
set -euo pipefail

SKILL_NAME="ee-review"
CANDIDATES=(
  "${HOME}/.agents/skills/${SKILL_NAME}"
  "${HOME}/.cursor/skills/${SKILL_NAME}"
)

found=""
for path in "${CANDIDATES[@]}"; do
  if [[ -e "${path}" ]]; then
    found="${path}"
    break
  fi
done

if [[ -z "${found}" ]]; then
  echo "[FAIL] ${SKILL_NAME} not installed under ~/.agents/skills or ~/.cursor/skills" >&2
  echo "Link or copy this repo so the folder name stays ${SKILL_NAME}." >&2
  exit 1
fi

for rel in SKILL.md VERSION LICENSE scripts/generate_report.py references/review-contract.md assets/review-slide-template.pptx; do
  if [[ ! -e "${found}/${rel}" ]]; then
    echo "[FAIL] missing ${found}/${rel}" >&2
    exit 1
  fi
done

version="$(tr -d '[:space:]' < "${found}/VERSION")"
echo "[OK] install path: ${found}"
echo "[OK] VERSION=${version}"
echo "[OK] next: quit/relaunch WorkBuddy (or open a new agent session), then ask for an ee-review."
if [[ -d "/Applications/WorkBuddy.app" ]]; then
  echo "[OK] WorkBuddy.app is present on this Mac"
else
  echo "[INFO] WorkBuddy.app not found under /Applications (skip GUI hint)"
fi
