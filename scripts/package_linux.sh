#!/usr/bin/env bash
# scripts/package_linux.sh
# Packages the standalone Linux release build for Drosophila 3D: Neuro-Flight

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_DIR="${ROOT_DIR}/bin"
GODOT_BIN="${BIN_DIR}/godot4"
PROJECT_DIR="${ROOT_DIR}/godot_game"
BUILD_DIR="${ROOT_DIR}/build"

echo "===================================================================="
echo "    PACKAGING STANDALONE LINUX BUILD: DROSOPHILA 3D"
echo "===================================================================="

if [[ ! -x "${GODOT_BIN}" ]]; then
    echo "==> Godot binary not found. Provisioning engine first..."
    "${ROOT_DIR}/scripts/setup_godot_linux.sh"
fi

mkdir -p "${BUILD_DIR}"

echo "==> Exporting game pack (PCK) using Linux/X11 preset..."
"${GODOT_BIN}" --headless --path "${PROJECT_DIR}" --export-pack "Linux/X11" "${BUILD_DIR}/fruitfly_3d.pck"

echo "==> Deploying standalone executable runner..."
cp -f "${GODOT_BIN}" "${BUILD_DIR}/fruitfly_3d.x86_64"
chmod +x "${BUILD_DIR}/fruitfly_3d.x86_64"

echo "==> Copying launcher script, desktop file, and icon..."
cp -f "${ROOT_DIR}/fruitfly_3d.sh" "${BUILD_DIR}/fruitfly_3d.sh"
chmod +x "${BUILD_DIR}/fruitfly_3d.sh"

cp -f "${ROOT_DIR}/Drosophila3D.desktop" "${BUILD_DIR}/Drosophila3D.desktop"
chmod +x "${BUILD_DIR}/Drosophila3D.desktop"

cp -f "${PROJECT_DIR}/icon.svg" "${BUILD_DIR}/fruitfly_icon.svg"

echo "===================================================================="
echo "    ✓ BUILD COMPLETED SUCCESSFULLY!"
echo "    Output Directory: ${BUILD_DIR}"
ls -lh "${BUILD_DIR}"
echo "===================================================================="
