#!/usr/bin/env bash
# scripts/setup_godot_linux.sh
# Automated Godot 4.3+ Linux Engine Provisioning Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_DIR="${ROOT_DIR}/bin"
GODOT_BIN="${BIN_DIR}/godot4"
GODOT_VERSION="4.3-stable"
GODOT_ZIP="Godot_v${GODOT_VERSION}_linux.x86_64.zip"
GODOT_URL="https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}/${GODOT_ZIP}"

mkdir -p "${BIN_DIR}"

if [[ -x "${GODOT_BIN}" ]]; then
    echo "==> Existing Godot binary detected at: ${GODOT_BIN}"
    CURRENT_VER=$("${GODOT_BIN}" --headless --version 2>/dev/null || true)
    if [[ "${CURRENT_VER}" == *"4.3"* ]]; then
        echo "==> Verified Godot version: ${CURRENT_VER}"
        echo "==> Godot 4.3 is already provisioned and ready."
        exit 0
    else
        echo "==> Existing binary reported: '${CURRENT_VER}', re-provisioning Godot ${GODOT_VERSION}..."
    fi
fi

echo "==> Downloading Godot Engine ${GODOT_VERSION}..."
TMP_ZIP=$(mktemp /tmp/godot_zip.XXXXXX.zip)

curl -fSL "${GODOT_URL}" -o "${TMP_ZIP}"

echo "==> Unpacking to ${BIN_DIR}..."
unzip -q -o "${TMP_ZIP}" -d "${BIN_DIR}"
rm -f "${TMP_ZIP}"

# The unzipped binary is named Godot_v4.3-stable_linux.x86_64
EXTRACTED_BIN="${BIN_DIR}/Godot_v${GODOT_VERSION}_linux.x86_64"
if [[ -f "${EXTRACTED_BIN}" ]]; then
    mv -f "${EXTRACTED_BIN}" "${GODOT_BIN}"
fi

chmod +x "${GODOT_BIN}"

echo "==> Verifying Godot Engine headless run..."
VER_OUTPUT=$("${GODOT_BIN}" --headless --version)
echo "==> Success! Godot Engine installed: ${VER_OUTPUT}"
echo "==> Path: ${GODOT_BIN}"
