# 🪰 Drosophila Autonomous Navigation: Biological PFL3 & Olfactory Steering Plan

## 1. Executive Summary & Circuit Neurobiology

In the adult fruit fly (*Drosophila melanogaster*), goal-directed navigation is driven by a specialized comparative circuit in the Central Complex (CX). While **E-PG** neurons maintain allocentric heading (the "compass needle") and **P-EN** neurons rotate that heading based on angular velocity (the "shifter"), goal-directed steering is computed downstream by **PFL3 neurons** (*Protocerebral Bridge – Fan-Shaped Body – Lateral Accessory Lobe*).

```text
                           [ FOOD PELLET ODOR PLUME ]
                                       │
                                       ▼
                       [ Odor Sensory Columns (FB) ]
                       (Receptive field: relative bearing Ψ)
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │   PFL3_L (12 nodes)   │             │   PFL3_R (12 nodes)   │
        │   Receives E-PG (PB)  │             │   Receives E-PG (PB)  │
        │   + Goal Vector (FB)  │             │   + Goal Vector (FB)  │
        └───────────┬───────────┘             └───────────┬───────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                       Δ PFL3 = (Σ PFL3_R - Σ PFL3_L)
                                       │
                                       ▼
                    [ Steering Angular Velocity (ω) ]
                                       │
             ┌─────────────────────────┴─────────────────────────┐
             │                                                   │
             ▼                                                   ▼
     [ P-EN_L Shifters ]                                 [ P-EN_R Shifters ]
     (Counter-Clockwise -45°)                            (Clockwise +45°)
             │                                                   │
             └─────────────────────────┬─────────────────────────┘
                                       │ (2.09x Driving Torque)
                                       ▼
                         [ E-PG Compass Bump Rotates ]
                                       │
                                       ▼
                      [ Fly Physical Body Steers in Arena ]
```

---

## 2. Operating Modes Division of Responsibility

| Parameter / Feature | **Manual Mode** *(Default)* | **Autonomous Mode** *(Toggle `M`)* |
| :--- | :--- | :--- |
| **Primary Steering Driver** | **Human User** (Arrow keys / WASD) | **Biological PFL3 Circuit** (Autopilot) |
| **P-EN Input Channel** | User key input directly drives $\omega$ | PFL3 activity differential drives $\omega = k \cdot (r_{\text{PFL3\_R}} - r_{\text{PFL3\_L}})$ |
| **Forward Throttle** | User `Up` / `Down` keys | Automatic modulation based on odor alignment & proximity |
| **Sensory Firing Display** | Active on HUD & 3D Brain (Passive monitoring) | Active on HUD & 3D Brain (Active steering driver) |
| **Sun Landmark** | Completely optional and OFF by default | Completely optional and OFF by default |
| **Food Pellet Interaction** | Fly eats pellet on contact $\to$ Respawn | Fly eats pellet on contact $\to$ Respawn |

---

## 3. Connectomic Specifications from NeuPrint (`hemibrain:v1.2.1`)

We queried Janelia's NeuPrint API and verified the biological circuit parameters:

1. **PFL3 Population Size:** Exactly **24 neurons** (12 in Left PB, 12 in Right PB):
   - Left PB instances: `PFL3(PB12c)_L1_C3` through `PFL3(PB12c)_L5_C7`
   - Right PB instances: `PFL3(PB12c)_R1_C2` through `PFL3(PB12c)_R5_C3`
2. **E-PG $\to$ PFL3 Synapses:** **123 directed connection pairs** with **1,569 total synaptic weight** connecting PB compass wedges into PFL3 dendritic branches.
3. **Anatomical Push-Pull Comparator:**
   - Left PFL3 neurons arborize in the Right LAL (controlling leftward steering turns).
   - Right PFL3 neurons arborize in the Left LAL (controlling rightward steering turns).
   - When the odor plume is to the left ($\Psi < 0$), left PFL3 activity dominates, injecting counter-clockwise turning torque into $P\text{-}EN_L$.

---

## 4. Step-by-Step Implementation Instructions

### Step 1: Connectomic Extraction Script (`scripts/extract_pfl3_connectome.py`)
- **Action:** Create a standalone offline extraction script interfacing with `neuprint-python`.
- **Outputs:**
  - `data/pfl3_neurons.json`: Body IDs, types, anatomical PB column assignments, and ROI volumes.
  - `data/epg_pfl3_weights.npz`: Complete $24 \times 48$ biological synaptic adjacency matrix $W_{\text{EP-PFL3}}$.
  - `data/pfl3_skeletons.json`: 3D node coordinates for rendering in the 3D whole-brain cloud.
- **Why Offline Caching:** The interactive simulation must run smoothly at 60–120 FPS without making blocking network API calls during the Pygame animation loop.

### Step 2: Biological Circuit Extension (`toy/circuit.py`)
- **Action:** Extend [`DualRingAttractor`](file:///home/rac/Projects/fruitfly/toy/circuit.py) to incorporate the 24 PFL3 decision neurons:
  1. Load or initialize biological synaptic matrix $W_{\text{EP-PFL3}}$ ($24 \times 48$).
  2. Model the Odor Sensory Input array $u_{\text{odor}}$ (16–24 elements spanning $[0, 2\pi)$ based on the fly's egocentric relative odor bearing $\Psi$).
  3. Integrate PFL3 firing rates via leaky integrator dynamics:
     $$\tau_{\text{PFL3}} \frac{dr_{\text{PFL3}}}{dt} = -r_{\text{PFL3}} + \phi\left(W_{\text{EP-PFL3}} r_{\text{EPG}} + W_{\text{FB-PFL3}} u_{\text{odor}}\right)$$
  4. Compute differential steering drive:
     $$\omega_{\text{auto}} = k_{\text{drive}} \cdot \left(\sum r_{\text{PFL3\_R}} - \sum r_{\text{PFL3\_L}}\right)$$
  5. Compute forward speed drive:
     $$v_{\text{auto}} = v_{\text{base}} \cdot \left(0.6 + 0.4 \cos(\Psi)\right) \cdot (0.4 + 0.6 \cdot \text{strength})$$
  6. Return `(omega_auto, target_v, pfl3_left_mean, pfl3_right_mean)`.

### Step 3: Event Loop & Autonomous Mode Integration (`run_toy.py`)
- **Action:** Update the main simulation loop:
  - In `MANUAL` mode:
    - Arrow keys / WASD control $\omega$ and acceleration as before.
    - PFL3 rates update passively for live telemetry and brain mesh glow.
  - In `AUTO` mode:
    - Keyboard steering is ignored.
    - `circuit.step_pfl3(odor_reading)` computes $\omega_{\text{auto}}$ and $v_{\text{auto}}$.
    - `circuit.step_frame(dt, omega=omega_auto)` drives the canonical E-PG/P-EN dual-ring CANN attractor.
    - Fly agent kinematic update uses decoded E-PG compass heading $\hat{\theta}$.

### Step 4: UI & Avionics Dashboard Enhancement (`toy/renderer.py`)
- **Action:**
  1. **Stats HUD:**
     - Add PFL3 decision activity row: `PFL3: L <rate> | R <rate>` with directional steering bias pointer.
     - Mode badge prominently toggles between `[MANUAL]` (Cyan) and `[AUTO]` (Emerald).
  2. **3D Brain Point Cloud ([`toy/brain_cloud.py`](file:///home/rac/Projects/fruitfly/toy/brain_cloud.py)):**
     - Add anatomical PFL3 nodes spanning the PB, Fan-Shaped Body, and Lateral Accessory Lobes.
     - Live 0–200 Hz firing rate glows reflect active decision making when chasing food plumes.

### Step 5: Unit Verification & Regression Testing (`tests/test_pfl3.py`)
- **Action:** Build automated unit tests:
  - Test 1: Validate $24 \times 48$ synaptic matrix alignment and stability.
  - Test 2: When odor is placed at Left ($-90^\circ$), verify Left PFL3 fires stronger and produces $\omega < 0$.
  - Test 3: When odor is placed at Right ($+90^\circ$), verify Right PFL3 fires stronger and produces $\omega > 0$.
  - Test 4: Verify 120-frame headless navigation test autonomously reaches and consumes the food pellet.

---

## 5. Summary of Deliverables

1. **`scripts/extract_pfl3_connectome.py`**: NeuPrint API extractor for 24 PFL3 neurons, synaptic weights, and skeletons.
2. **`data/pfl3_circuit.npz`**: Cached connectome data ensuring instant offline startup.
3. **Updated [`toy/circuit.py`](file:///home/rac/Projects/fruitfly/toy/circuit.py)**: PFL3 24-neuron comparator dynamics feeding into the 2.09× P-EN shifter loop.
4. **Updated [`run_toy.py`](file:///home/rac/Projects/fruitfly/run_toy.py)**: Seamless Manual ↔ Autonomous mode execution.
5. **Updated [`toy/renderer.py`](file:///home/rac/Projects/fruitfly/toy/renderer.py) & [`toy/brain_cloud.py`](file:///home/rac/Projects/fruitfly/toy/brain_cloud.py)**: Live PFL3 telemetry and 3D central complex activations.
6. **`tests/test_pfl3.py`**: Complete automated test verification.
