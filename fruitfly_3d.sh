#!/usr/bin/env bash
# fruitfly_3d.sh
# Production High-Performance Standalone Launcher for Drosophila 3D: Neuro-Flight
# Target Hardware: Ubuntu 24.04 LTS / NVIDIA GeForce RTX 4060 / Intel Core i7-12700H

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
GAME_BIN="${BUILD_DIR}/fruitfly_3d.x86_64"
GAME_PCK="${BUILD_DIR}/fruitfly_3d.pck"

# If binary is in same folder as script (e.g. when distributed inside build/)
if [[ ! -f "${GAME_BIN}" ]] && [[ -f "${SCRIPT_DIR}/fruitfly_3d.x86_64" ]]; then
    BUILD_DIR="${SCRIPT_DIR}"
    GAME_BIN="${SCRIPT_DIR}/fruitfly_3d.x86_64"
    GAME_PCK="${SCRIPT_DIR}/fruitfly_3d.pck"
fi

if [[ ! -x "${GAME_BIN}" ]] || [[ ! -f "${GAME_PCK}" ]]; then
    echo "ERROR: Standalone game executable or PCK missing in ${BUILD_DIR}."
    echo "Run ./scripts/run_headless_ci.sh or package build first."
    exit 1
fi

# 1. NVIDIA RTX 4060 GPU Offload Configuration
if command -v nvidia-smi >/dev/null 2>&1; then
    export __NV_PRIME_RENDER_OFFLOAD=1
    export __GLX_VENDOR_LIBRARY_NAME=nvidia
    if [[ -f "/usr/share/vulkan/icd.d/nvidia_icd.json" ]]; then
        export VK_DRIVER_FILES="/usr/share/vulkan/icd.d/nvidia_icd.json"
    fi
fi

# 2. Linux Wayland / X11 Compositor Bypass for High Refresh & Low Latency
export SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR=0

# 3. High Refresh Rate & Vulkan Forward+ Settings
export MESA_VK_WSI_PRESENT_MODE=immediate
export __GL_SYNC_TO_VBLANK=0

echo "===================================================================="
echo "       🪰 DROSOPHILA 3D: HIGH-FIDELITY NEURO-FLIGHT GAME 🪰"
echo "  Biological CANN Heading Compass & Biomechanical Flight Engine"
echo "  Renderer : Forward+ Clustered Vulkan | Target GPU: RTX 4060"
echo "===================================================================="

exec "${GAME_BIN}" --main-pack "${GAME_PCK}" "$@"
