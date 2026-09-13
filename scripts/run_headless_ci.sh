#!/usr/bin/env bash
# scripts/run_headless_ci.sh
# Full Automated Headless CI Test Runner for Drosophila 3D: Neuro-Flight
# Validates performance budgets, 240 frames of ODE stability, and zero leaks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
GODOT_BIN="${ROOT_DIR}/bin/godot4"
PROJECT_DIR="${ROOT_DIR}/godot_game"

if [[ ! -x "${GODOT_BIN}" ]]; then
    echo "ERROR: Godot engine binary not found at ${GODOT_BIN}"
    echo "Run scripts/setup_godot_linux.sh first."
    exit 1
fi

echo "===================================================================="
echo "    DROSOPHILA 3D: HIGH-FIDELITY NEURO-FLIGHT HEADLESS CI SUITE"
echo "===================================================================="
echo "Engine: $("${GODOT_BIN}" --version)"
echo "Project: ${PROJECT_DIR}"
echo "Date: $(date -u)"
echo "===================================================================="

run_test() {
    local test_name="$1"
    local script_path="$2"
    echo ""
    echo ">>> Running Test Suite: ${test_name} (${script_path})..."
    "${GODOT_BIN}" --headless --path "${PROJECT_DIR}" -s "${script_path}"
    echo ">>> [PASS] ${test_name} passed successfully."
}

# 1. Performance Profiling & Hardware Budget Benchmark
run_test "Phase 7 Performance & Hardware Budget Benchmark" "tests/test_performance_profile.gd"

# 2. 240-Frame Continuous Closed-Loop CI Stability Test
run_test "Phase 7 240-Frame Closed-Loop CI & Zero-Leak Test" "tests/test_headless_ci.gd"

# 3. Closed-Loop Chemotaxis & Anemotaxis Navigation
run_test "Phase 4 & 5 Closed-Loop Odor & Cast-and-Surge Navigation" "tests/test_closed_loop.gd"

# 4. Holographic Connectome HUD & Avionics Telemetry
run_test "Phase 6 Holographic Connectome HUD & Camera Director" "tests/test_hud_hologram.gd"

echo ""
echo "===================================================================="
echo "    ✓✓✓ ALL 4 CI TEST SUITES PASSED WITH 100% SUCCESS! ✓✓✓"
echo "===================================================================="
