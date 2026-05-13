#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
WORKSPACE_ROOT="$(cd "${PROJECT_ROOT}"/.. && pwd)"

export STAGE_ROOT="${STAGE_ROOT:-${WORKSPACE_ROOT}/stage-install}"
export STAGE_DEPS_ROOT="${STAGE_DEPS_ROOT:-${WORKSPACE_ROOT}/stage-deps}"
export PATH="${STAGE_ROOT}/bin:${PATH}"
STAGE_LIBRARY_PATHS="${STAGE_ROOT}/lib:${STAGE_DEPS_ROOT}/lib"
export LD_LIBRARY_PATH="${STAGE_LIBRARY_PATHS}:${LD_LIBRARY_PATH:-}"
if [[ "$(uname -s)" == "Darwin" ]]; then
  export DYLD_LIBRARY_PATH="${STAGE_LIBRARY_PATHS}:${DYLD_LIBRARY_PATH:-}"
fi
export STAGEPATH="${STAGE_ROOT}/lib/Stage-4.3"

echo "STAGE_ROOT=${STAGE_ROOT}"
echo "STAGE_DEPS_ROOT=${STAGE_DEPS_ROOT}"
echo "STAGEPATH=${STAGEPATH}"
