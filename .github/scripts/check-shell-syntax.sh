#!/usr/bin/env bash
set -euo pipefail

scripts=()
while IFS= read -r script; do
  scripts+=("${script}")
done < <(git ls-files '*.sh')

if [[ ${#scripts[@]} -eq 0 ]]; then
  echo "No shell scripts found."
  exit 0
fi

for script in "${scripts[@]}"; do
  echo "Checking ${script}"
  bash -n "${script}"
done

echo "Validated ${#scripts[@]} shell scripts."
