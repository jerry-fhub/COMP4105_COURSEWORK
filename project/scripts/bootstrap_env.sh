#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
WORKSPACE_ROOT="$(cd "${PROJECT_ROOT}"/.. && pwd)"

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/mplconfig_dlcw}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/xdg_cache_dlcw}"

if [[ -f "${PROJECT_ROOT}/scripts/stage_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/scripts/stage_env.sh" >/dev/null
elif [[ -f "${WORKSPACE_ROOT}/stage_env.sh" ]]; then
  # Reuse the locally installed Stage runtime when it is available.
  # shellcheck disable=SC1091
  source "${WORKSPACE_ROOT}/stage_env.sh" >/dev/null
fi

mkdir -p "${MPLCONFIGDIR}" "${XDG_CACHE_HOME}"

echo "PROJECT_ROOT=${PROJECT_ROOT}"
echo "PYTHONPATH=${PYTHONPATH}"
echo "MPLCONFIGDIR=${MPLCONFIGDIR}"
echo "XDG_CACHE_HOME=${XDG_CACHE_HOME}"
if [[ -n "${STAGE_ROOT:-}" ]]; then
  echo "STAGE_ROOT=${STAGE_ROOT}"
fi
