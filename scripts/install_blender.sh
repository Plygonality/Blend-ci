#!/usr/bin/env bash
# Install one official Blender linux-x64 tarball and fail closed if it is missing.
#
# Exact download (the only URL this repo uses):
#   https://download.blender.org/release/Blender<major>/blender-<version>-linux-x64.tar.xz
#
# Exact cache directory (GitHub Actions key: blender-<version>-linux-x64):
#   ${BLEND_CI_CACHE:-$HOME/.cache/blend-ci}/blender-<version>/
#
# This is not a DCC GUI image. Do not use lscr.io/linuxserver/blender for CI:
# that container is a KasmVNC desktop. Headless cooks use the official tarball
# plus xvfb + mesa (see APT_PACKAGES in src/blend_ci/versions.py).
set -euo pipefail

CHANNEL="${1:-}"
if [[ -z "${CHANNEL}" ]]; then
  echo "usage: scripts/install_blender.sh <version>|lts|current" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${CHANNEL}"
if [[ "${CHANNEL}" == "lts" || "${CHANNEL}" == "current" ]]; then
  PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
  VERSION="$(python3 -c "from blend_ci.versions import resolve_channel; print(resolve_channel('${CHANNEL}'))")"
fi

MAJOR="${VERSION%.*}"
TARBALL="blender-${VERSION}-linux-x64.tar.xz"
URL="https://download.blender.org/release/Blender${MAJOR}/${TARBALL}"
CACHE="${BLEND_CI_CACHE:-${HOME}/.cache/blend-ci}"
PREFIX="${CACHE}/blender-${VERSION}"
BIN="${PREFIX}/blender"

if [[ -x "${BIN}" ]]; then
  echo "blend-ci: using cached ${BIN}"
  "${BIN}" --version | head -n 1
  echo "BLENDER=${BIN}"
  if [[ -n "${GITHUB_PATH:-}" ]]; then
    echo "${PREFIX}" >> "${GITHUB_PATH}"
  fi
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "BLENDER=${BIN}" >> "${GITHUB_ENV}"
  fi
  exit 0
fi

mkdir -p "${CACHE}"
TMP="${CACHE}/${TARBALL}"
echo "blend-ci: downloading ${URL}"
if ! curl -fL --retry 4 --retry-delay 4 -o "${TMP}" "${URL}"; then
  echo "blend-ci: failed to download ${URL}" >&2
  echo "blend-ci: fail closed — blender is missing on this runner." >&2
  exit 2
fi

rm -rf "${PREFIX}"
mkdir -p "${PREFIX}"
tar -xJf "${TMP}" -C "${PREFIX}" --strip-components=1
rm -f "${TMP}"

if [[ ! -x "${BIN}" ]]; then
  echo "blend-ci: ${BIN} missing after extract. Fail closed." >&2
  exit 2
fi

"${BIN}" --version | head -n 1
echo "BLENDER=${BIN}"
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "${PREFIX}" >> "${GITHUB_PATH}"
fi
if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "BLENDER=${BIN}" >> "${GITHUB_ENV}"
fi
