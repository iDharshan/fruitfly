# 🪰 Fruitfly V2: Hybrid Biological + Learned Painting Agent
## Comprehensive Architecture, First-Principles Design & Engineering Execution Plan

**Repository:** `iDharshan/fruitfly`  
**Author:** Antigravity Engineering (in collaboration with the Drosophila Connectomics & Hybrid RL Research Group)  
**Target Hardware:** Linux x86_64, NVIDIA RTX 4060 GPU, 16GB RAM  
**Software Stack:** Python 3.12 (`fly_env`), NumPy, SciPy, Pygame 2.6.1, Gymnasium 1.0+, Stable-Baselines3, PyTorch, Godot Engine 4.7+ (Embodiment Layer)  
**Target Date:** September 2026  

---

## Executive Summary: The Layered Hybrid Paradigm

The objective of **Fruitfly V2** is to build an artificial agent capable of painting target visual patterns onto an in-world canvas using a closed-loop embodiment. 

Rather than treating the problem as a monolithic deep reinforcement learning task (which reduces the fly's connectome to a decorative theme) or attempting an intractable whole-brain biophysical simulation (>50,000 optic lobe neurons and thousands of motor neurons), **Fruitfly V2 adopts a layered hybrid architecture**:

1. **Frozen Biological Core:** The existing connectomics-grounded Continuous Attractor Neural Network (CANN)—featuring 48 E-PG compass neurons, 48 P-EN angular velocity shifters ($2.09\times$ asymmetric feedback ratio), and 24 PFL3 steering comparators—remains mathematically frozen. It acts as the immutable physical compass and heading memory of the agent.
2. **Sensory Transduction Layer:** Pure biological interfaces simulate the transformation of external physical stimuli (visual light and chemical volatiles) into rate-coded neural activity (receptive-field visual projection neurons and antennal lobe olfactory glomeruli).
3. **Biological Premotor Bridge:** Descending Neurons (DNs) and Ventral Nerve Cord (VNC) premotor circuits translate high-level behavioral drives into stable motor primitives (forward cruise, banked turns, landing, takeoff, brush contact).
4. **Lean Learned Policy (PPO):** A compact Actor-Critic network (~256-256 hidden layers) sits atop the biological substrate. It does not replace the compass or steer raw motor neurons; instead, it observes the biological sensory-compass state alongside compact target-canvas error features, learning the **high-level behavioral strategy** (which color to seek, when to reload, where to apply paint) and outputting **residual steering and throttle biases**.

```
                           ┌───────────────────────────────┐
                           │      UPLOADED TARGET IMAGE    │
                           └───────────────┬───────────────┘
                                           │
                                    Target Encoder
                                           │
                           ┌───────────────▼───────────────┐
                           │ Compact Target Representation │
                           │  (16×16 RGB, edges, palette)  │
                           └───────┬───────────────┬───────┘
                                   │               │
       ┌───────────────────────────┘               └───────────────────────────┐
       ▼                                                                       ▼
┌──────────────┐                                                        ┌──────────────┐
│ Paint Pots   │                                                        │ Live Canvas  │
│ (RGBY Odors) │                                                        │  (Pigment)   │
└──────┬───────┘                                                        └──────┬───────┘
       │                                                                       │
       ▼                                                                       ▼
┌──────────────────────────────┐                        ┌──────────────────────────────┐
│  BIOLOGICAL SENSORY SYSTEM   │                        │      TASK STATE FEATURES     │
│ • Olfactory: ORN ➔ AL (Pots) │                        │ • Canvas vs Target Error     │
│ • Visual: VPN Receptive Field│                        │ • Pigment Volume & Color     │
└──────────────┬───────────────┘                        └──────────────┬───────────────┘
               │                                                       │
               ▼                                                       │
┌──────────────────────────────┐                                       │
│  FROZEN CANN COMPASS (CX)    │                                       │
│ • E-PG ⟷ P-EN Ring Attractor │                                       │
│ • Decoded Heading (sin, cos) │                                       │
│ • Bump Coherence & Torque    │                                       │
└──────────────┬───────────────┘                                       │
               │                                                       │
               └───────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │     SMALL LEARNED POLICY      │
                       │             (PPO)             │
                       │   "What color? Where next?"   │
                       │   Residual Heading Bias ±Δω   │
                       └───────────────┬───────────────┘
                                       │ High-level intent & bias
                                       ▼
                       ┌───────────────────────────────┐
                       │   DESCENDING / PREMOTOR (VNC) │
                       │ • DN Steering Modulation      │
                       │ • Motor Primitives (Flight)   │
                       │ • Pen Actuator (Contact & P)  │
                       └───────────────┬───────────────┘
                                       │ Physical Kinematics
                                       ▼
                       ┌───────────────────────────────┐
                       │      FLY AGENT + BRUSH        │
                       │    Navigates, Dips, Paints    │
                       └───────────────────────────────┘
```

---

## 1. First-Principles Audit of the Codebase & Critical Foundations

### 1.1 What We Have Today (and Why It Works)
A systematic inspection of the `fruitfly` repository reveals that the core biophysical and mathematical mechanics are already implemented, verified, and passing tests:
* [`toy/circuit.py`](file:///home/rac/Projects/fruitfly/toy/circuit.py): Contains the `DualRingAttractor` class modeling 48 E-PG wedges, 24 Left P-ENs, 24 Right P-ENs, and 24 PFL3 comparators. Synaptic matrices ($W_{ee}, W_{ep}, W_{pe}$) implement Gaussian topology with the verified $2.09\times$ feedback-to-feedforward ratio. The integration loop utilizes sub-stepping ($8 \times 2\text{ ms} = 16\text{ ms}$) with divisive normalization in the Ellipsoid Body (EB):
  $$\phi_e(u) = \frac{\max(0, u)^2}{1 + k_{\text{div}} \sum_j \max(0, u_j)^2}$$
* [`tests/test_circuit.py`](file:///home/rac/Projects/fruitfly/tests/test_circuit.py): Rigorously confirms attractor formation, stationary memory retention ($<0.01^\circ$ drift over 1 s), angular velocity integration for left/right turns ($>450^\circ$ unwrapped tracking), synaptic arc generation, and visual landmark cue anchoring ($0.00^\circ$ error).
* [`tests/test_pfl3.py`](file:///home/rac/Projects/fruitfly/tests/test_pfl3.py): Validates the biological steering comparator: neutral odor yields symmetric PFL3 activity ($\omega \approx 0$), while lateral odors drive asymmetric push-pull steering ($|\omega| \approx 2.8\text{ rad/s}$), enabling closed-loop autonomous foraging.
* [`toy/agent.py`](file:///home/rac/Projects/fruitfly/toy/agent.py) & [`toy/food.py`](file:///home/rac/Projects/fruitfly/toy/food.py): Provide 2D kinematics, toroidal boundaries, analytical continuous Gaussian odor plume fields, and gradient calculations.

### 1.2 First-Principles Critique: Questioning Assumptions & Traps

| Component | Common Naive Proposal | First-Principles Biological / RL Reality | Fruitfly V2 Resolution |
| :--- | :--- | :--- | :--- |
| **Vision** | Feed raw $256 \times 256$ RGB canvas directly into an RL MLP. | Input dimension is $196,608$. An MLP cannot learn spatial convolutions; a heavy CNN will tank simulation throughput from $2,000\text{ FPS}$ to $30\text{ FPS}$. MaleCNS does not connect arbitrary RGB pixels to central neurons. | Split into two pathways: (1) Receptive-field visual sensor for allocentric arena bearings; (2) Compact deterministic target/canvas error map ($16 \times 16 \times 3$ plus edge maps). |
| **CANN Integration** | Backpropagate through CANN or let RL optimize synaptic weights. | The experiment becomes "RL learned an artificial compass," destroying biological interpretability. | **Strictly freeze the CANN**. Synaptic matrices $W_{ee}, W_{ep}, W_{pe}$ are read-only buffers. Policy receives decoded heading, coherence, and internal activations. |
| **Motor System** | RL directly outputs continuous torque to dozens of individual motor neurons. | Biological Descending Neurons (DNs) do not control individual muscles; they trigger structured premotor circuits in the VNC. Pure low-level RL takes millions of steps just to discover how not to spin out. | Two-tier control: RL outputs strategic intent and a small steering bias $\Delta \omega$; the biological premotor layer translates this into smooth flight and brush contact. |
| **Action Space** | Complex hybrid continuous/discrete action spaces requiring bespoke algorithms. | Standard PPO in Stable-Baselines3 performs best on unified continuous boxes or clean multi-discrete spaces. | 10 Hz policy step controlling 120 Hz physics/CANN substeps. Actions are normalized continuous commands with thresholded state triggers. |
| **Reward Design** | $\text{Reward} = \text{Image Similarity}$ or $+1.0$ per paint collected. | Pure similarity is too sparse. Flat collection reward creates an infinite reward-hacking loop (collect, dump, collect forever). | Strictly potential-based progress reward: $R_t = \lambda_{\text{prog}} [S(\mathcal{C}_t, \mathcal{T}) - S(\mathcal{C}_{t-1}, \mathcal{T})]$. Sum of rewards is telescoping and mathematically bounded. |
| **Simulation Engine** | Run training inside Godot 3D engine. | Godot engine overhead limits headless stepping to $\sim 60\text{--}120\text{ FPS}$, making RL training take days. | **Pygame/Pure Python** is the authoritative high-speed training simulator ($>3,000\text{ FPS}$ headless). **Godot 4.7+** is the downstream 3D embodiment and visualization layer. |

---

## 2. Theoretical & Mathematical Formulations

### 2.1 Frozen Continuous Attractor Neural Network (CANN)
The central complex heading compass co-models the Ellipsoid Body (EB) and Protocerebral Bridge (PB):
* **E-PG (Compass Neurons):** $N_{\text{epg}} = 48$ neurons covering azimuthal space $\theta_i \in [0, 2\pi)$.
* **P-EN (Velocity Shifters):** $N_{\text{pen}} = 48$ ($24_L$ Left, $24_R$ Right), shifted by $\pm \pi/4$ ($45^\circ$).
* **Membrane Dynamics:**
  $$\tau_m \frac{dr_i}{dt} = -r_i + \phi(u_i)$$
  $$u_e = W_{ee} r_{\text{epg}} + 0.30 \left( W_{pe, L} r_{\text{pen}, L} + W_{pe, R} r_{\text{pen}, R} \right) + u_{\text{visual}} + \eta(t)$$
* **Population Vector Readout:**
  $$X = \sum_{i=1}^{N_{\text{epg}}} r_i \cos(\theta_i), \quad Y = \sum_{i=1}^{N_{\text{epg}}} r_i \sin(\theta_i)$$
  $$\hat{\theta} = \operatorname{atan2}(Y, X), \quad A = \sqrt{X^2 + Y^2}, \quad \text{Coherence } C = \frac{A}{\sum_i r_i + \epsilon}$$
* **Formal `CompassState` Dataclass:**
  To guarantee that RL cannot tamper with circuit dynamics, the CANN outputs an immutable snapshot:
  ```python
  @dataclass(frozen=True)
  class CompassState:
      heading: float           # Decoded azimuth theta in [-pi, pi)
      sin_heading: float       # sin(theta) (smooth cyclic representation)
      cos_heading: float       # cos(theta)
      coherence: float         # Bump quality in [0, 1]
      amplitude: float         # Vector sum amplitude
      torque: float            # Differential P-EN activation (Right - Left)
      epg_activity: np.ndarray # Shape (48,), normalized [0, 1]
      pen_left_mean: float     # Left shifter activity
      pen_right_mean: float    # Right shifter activity
      pfl3_bias: float         # Biological steering bias from PFL3 in [-1, 1]
  ```

### 2.2 Olfactory Chemical Sensing (Multi-Pot Odor Field)
There are $K$ paint pots ($K \ge 4$: Red, Green, Blue, Yellow) located at arena positions $\mathbf{p}_k = (x_k, y_k)$. Each pot emits a volatile chemical plume modeled as an independent radial Gaussian dispersion:
$$C_k(\mathbf{x}) = \exp\left( -\frac{\|\mathbf{x} - \mathbf{p}_k\|_{\text{torus}}^2}{2 \sigma_{\text{odor}}^2} \right)$$
The analytical spatial gradient for channel $k$ is:
$$\nabla C_k(\mathbf{x}) = \frac{\mathbf{p}_k - \mathbf{x}}{\sigma_{\text{odor}}^2} C_k(\mathbf{x}) = \begin{bmatrix} \partial C_k / \partial x \\ \partial C_k / \partial y \end{bmatrix}$$
The egocentric bearing to pot $k$ relative to the fly's compass heading $\hat{\theta}$ is:
$$\psi_k = \operatorname{wrap}\left( \operatorname{atan2}\left( \frac{\partial C_k}{\partial y}, \frac{\partial C_k}{\partial x} \right) - \hat{\theta} \right)$$
The biological Antennal Lobe (AL) projection neurons encode this as:
$$r_{\text{AL}, k} = \tanh(\beta_{\text{odor}} C_k(\mathbf{x}))$$

### 2.3 Physical Canvas & Pigment Accumulation Dynamics
The canvas represents an active surface $\mathcal{C}$ within the flight arena:
* **High-Resolution Visual Buffer:** $\mathcal{C}_{\text{vis}} \in \mathbb{R}^{256 \times 256 \times 4}$ (RGBA).
* **Low-Resolution Evaluation Grid:** $\mathcal{C}_{\text{eval}} \in \mathbb{R}^{32 \times 32 \times 3}$ (Normalized RGB) for fast reward calculation.
* **Fly Altitude & Brush Contact:** The fly possesses vertical altitude $z \in [0, z_{\text{max}}]$.
  * $z > z_{\text{contact}}$: Fly is airborne (cruising flight, no painting possible).
  * $z \le z_{\text{contact}}$: Brush makes physical contact with the surface.
* **Pigment Deposition:**
  When landed on the canvas ($z \le z_{\text{contact}}$) with pen down, brush pressure $P \in [0, 1]$, and pigment volume $V_{\text{pigment}} > 0$:
  $$\Delta V = \min\left(V_{\text{pigment}}, \kappa_{\text{flow}} \cdot P \cdot \Delta t\right)$$
  The pigment is deposited onto pixels $\mathbf{u} = (u_x, u_y)$ according to a 2D Gaussian footprint:
  $$G(\mathbf{u}; \mathbf{x}_{\text{pen}}, \sigma_{\text{brush}}) = \exp\left( -\frac{\|\mathbf{u} - \mathbf{x}_{\text{pen}}\|^2}{2 \sigma_{\text{brush}}^2} \right)$$
  $$\mathcal{C}(\mathbf{u}) \leftarrow \mathcal{C}(\mathbf{u}) + \left( \mathbf{c}_{\text{pigment}} - \mathcal{C}(\mathbf{u}) \right) \cdot \frac{\Delta V}{A_{\text{brush}}} G(\mathbf{u})$$
  $$V_{\text{pigment}} \leftarrow V_{\text{pigment}} - \Delta V$$

### 2.4 Target Representation & Preprocessing
When an image (PNG/JPEG) is loaded, it is processed into a structured target object $\mathcal{T}$:
1. Resized to $256 \times 256$ RGB (reference canvas scale).
2. Downsampled to $16 \times 16 \times 3$ RGB tensor ($768$ values).
3. Sobel edge-filtered to produce a $16 \times 16$ binary edge map ($256$ values).
4. Quantized into an $8$-bin color palette distribution ($24$ values).
5. Downsampled to $32 \times 32 \times 3$ for step-by-step evaluation.

```
Uploaded Image ──> Rescale 256x256 ──┬──> Eval Target (32x32x3) ──> Reward Engine
                                     └──> Policy Input (16x16 RGB + Edges + Palette)
```

---

## 3. Reinforcement Learning Architecture

### 3.1 Observation Space (`gym.spaces.Dict`)
The observation is structured into physically and biologically interpretable semantic sub-spaces, fully normalized to $[-1, 1]$ or $[0, 1]$:

```python
observation_space = gym.spaces.Dict({
    # Biological Compass State (from frozen CANN)
    "compass": gym.spaces.Box(
        low=np.array([-1.0, -1.0, 0.0, -1.0, -1.0], dtype=np.float32),
        high=np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32),
        dtype=np.float32,
        # [sin(theta), cos(theta), coherence, torque, pfl3_bias]
    ),
    
    # Sensory Arena Perception (Visual bearings & distances)
    "sensory": gym.spaces.Box(
        low=-1.0, high=1.0, shape=(8,), dtype=np.float32,
        # [canvas_bearing, canvas_dist_norm, pot_R_bearing, pot_G_bearing,
        #  pot_B_bearing, pot_Y_bearing, min_pot_dist, altitude_norm]
    ),
    
    # Olfactory Antennal Lobe Glomeruli Activations
    "odor": gym.spaces.Box(
        low=0.0, high=1.0, shape=(4,), dtype=np.float32,
        # [AL_concentration_R, AL_concentration_G, AL_concentration_B, AL_concentration_Y]
    ),
    
    # Internal Pigment Reservoir
    "pigment": gym.spaces.Box(
        low=0.0, high=1.0, shape=(5,), dtype=np.float32,
        # [volume_ratio, is_R, is_G, is_B, is_Y]
    ),
    
    # Pen & Kinematics State
    "kinematics": gym.spaces.Box(
        low=-1.0, high=1.0, shape=(4,), dtype=np.float32,
        # [velocity_norm, pen_down_flag, pen_pressure, altitude]
    ),
    
    # Compact Task Discrepancy (Target vs Current Canvas)
    "task": gym.spaces.Box(
        low=-1.0, high=1.0, shape=(16, 16, 3), dtype=np.float32,
        # (Target_16x16 - Canvas_16x16) difference tensor in normalized RGB
    ),
})
```

### 3.2 Action Space & Multi-Rate Temporal Hierarchy
* **Simulation Rate:** $120\text{ Hz}$ ($\Delta t = 8.33\text{ ms}$). CANN ODEs, biophysics, drag, and brush pigment deposition integrate at this rate.
* **RL Decision Rate:** $10\text{ Hz}$ ($\Delta t_{\text{macro}} = 100\text{ ms} = 12\text{ internal physics steps}$).
* **Action Specification:** Continuous Box $\mathbf{a} \in [-1, 1]^4$:
  1. $a_0 \in [-1, 1]$: **Heading Bias ($\Delta \omega$)**. Biases the biological steering:
     $$\omega_{\text{steer}} = \omega_{\text{bio}} + a_0 \cdot \omega_{\text{max\_bias}}$$
  2. $a_1 \in [-1, 1]$: **Forward Throttle ($v_{\text{target}}$)**. Mapped to $[v_{\text{min}}, v_{\text{max}}]$.
  3. $a_2 \in [-1, 1]$: **Altitude Command ($z_{\text{target}}$)**. $>0$ climbs to cruising flight; $\le 0$ commands descent and surface contact.
  4. $a_3 \in [-1, 1]$: **Brush Actuation ($P_{\text{pen}}$)**. $>0$ engages pen down with pressure $a_3$; $\le 0$ lifts pen up.

### 3.3 Anti-Hacking Potential-Based Reward Formulation
To prevent classic reward-hacking loops (e.g. infinite paint reloading without canvas strokes), the primary reward is **strictly potential-based progress**:

1. **Normalized Evaluation Similarity:**
   $$S_t = 1.0 - \frac{1}{3 \cdot 32 \cdot 32} \sum_{u=1}^{32} \sum_{v=1}^{32} \|\mathcal{C}_{\text{eval}, t}(u, v) - \mathcal{T}_{\text{eval}}(u, v)\|_1 \in [0, 1]$$
2. **Progress Reward:**
   $$R_{\text{progress}} = \lambda_{\text{prog}} \cdot \left( S_t - S_{t-1} \right)$$
   *Proof of Boundedness:* $\sum_{t=1}^T R_{\text{progress}} = \lambda_{\text{prog}} [S_T - S_0] \le \lambda_{\text{prog}}$. The agent cannot earn infinite reward by cycling.
3. **Action & Error Penalties:**
   $$R_{\text{spill}} = -\lambda_{\text{spill}} \quad \text{if pen is down while } \mathbf{x}_{\text{fly}} \notin \text{CanvasArea}$$
   $$R_{\text{energy}} = -\lambda_{\text{energy}} \cdot \left( \frac{v}{v_{\text{max}}} \right)^2 \Delta t_{\text{macro}}$$
4. **Terminal Completion Bonus:**
   $$R_{\text{terminal}} = +10.0 \quad \text{if } S_t \ge 0.90$$

---

## 4. Scientific Ablation Suite & Research Hypotheses

The core research question of this project is:
> *"Does a fixed biological navigation circuit (E-PG ⟷ P-EN CANN + PFL3) provide a beneficial inductive bias for learning a visuomotor task compared to standard end-to-end RL?"*

We define five rigorous experimental conditions to be executed with identical seeds and hyperparameters:

```text
Condition A: Scripted Rule-Based Baseline (Deterministic state machine, no learning)
Condition B: Pure RL Baseline (No CANN, raw egocentric delta heading to targets)
Condition C: Fruitfly V2 Hybrid (Frozen CANN + PFL3 + Learned PPO policy)
Condition D: Scrambled CANN Control (Randomly permuted synaptic matrices W_ee, W_pe)
Condition E: Direct Motor Control (RL outputs raw motor torques without VNC primitives)
```

### Metrics for Quantitative Evaluation:
* **Painting Fidelity:** Peak Signal-to-Noise Ratio (PSNR), Structural Similarity Index (SSIM), final pixel L1 accuracy.
* **Sample Efficiency:** Number of environment steps to reach $S_t \ge 0.70$.
* **Compass Coherence:** Mean bump coherence $C(t)$ during turning maneuvers.
* **Kinematic Efficiency:** Ratio of Euclidean path length to actual trajectory length ($\mathcal{L}_{\text{direct}} / \mathcal{L}_{\text{actual}}$).
* **Pigment Economy:** Ratio of pigment successfully deposited on canvas to total pigment consumed from pots.

---

## 5. Architectural Directory Layout

The repository will be structured cleanly to separate biological models, painting domain logic, reinforcement learning environments, and visualization:

```text
fruitfly/
├── biology/
│   ├── __init__.py
│   ├── interfaces.py       # CompassState, SensoryState, BrainOutput, BiologyConfig
│   ├── cann.py             # Frozen DualRingAttractor with immutable parameters
│   ├── olfactory.py        # Multi-channel odor dispersion, ORN & AL rate coding
│   ├── visual.py           # Virtual retina & visual projection neuron receptive fields
│   ├── descending.py       # Descending neuron command integration
│   └── motor.py            # VNC premotor circuits & flight/pen motor primitives
│
├── painting/
│   ├── __init__.py
│   ├── canvas.py           # 256x256 visual canvas + 32x32 evaluation buffer
│   ├── brush.py            # Altitude-aware pen mechanics & pigment reservoir
│   ├── paint_pot.py        # Multi-color paint pots with individual odor signatures
│   ├── target.py           # Target image processor (16x16, edges, palette)
│   ├── scripted_agent.py   # Deterministic non-learning baseline painter
│   └── world.py            # Canonical PaintingSimulation world state
│
├── rl/
│   ├── __init__.py
│   ├── env.py              # FruitFlyPaintEnv (Gymnasium Dict observation space)
│   ├── observations.py     # Observation normalization & tensor packaging
│   ├── actions.py          # Action translation & biological steering bias
│   ├── reward.py           # Telescoping potential-based reward calculator
│   ├── policy.py           # PPO Actor-Critic network architecture
│   ├── train.py            # SB3 training runner with VecNormalize & checkpoints
│   └── evaluate.py         # Evaluation harness across benchmark shapes
│
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py          # SSIM, PSNR, L1, bump coherence, trajectory efficiency
│   ├── ablations.py        # Runner for Conditions A, B, C, D, E
│   └── plots.py            # Matplotlib/Seaborn scientific publication figures
│
├── tests/
│   ├── test_circuit.py     # Existing CANN tests (preserved)
│   ├── test_agent.py       # Existing agent kinematics (preserved)
│   ├── test_food.py        # Existing food tests (preserved)
│   ├── test_pfl3.py        # Existing PFL3 tests (preserved)
│   ├── test_cann_freeze.py # Verifies CANN immutability & CompassState
│   ├── test_painting.py    # Canvas pigment deposition & brush contact tests
│   ├── test_sensors.py     # Multi-pot odor fields & visual sensors
│   ├── test_motor.py       # Descending & motor primitives verification
│   ├── test_scripted.py    # Scripted baseline completes painting task
│   ├── test_gym_env.py     # Gymnasium API compliance & check_env test
│   └── test_training.py    # Fast smoke test for PPO training step
│
├── run_toy.py              # Existing 2D interactive simulator (preserved)
├── run_painting.py         # V2 interactive 2D painting simulator & dashboard
└── fruitfly_3d.sh          # Godot 3D game launcher
```

---

## 6. Detailed Implementation Roadmap & Milestones

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       FRUITFLY V2 MILESTONE ROADMAP                        │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 0: Foundation & CANN API Freeze                                     │
│          ├── Create biology/interfaces.py and biology/cann.py             │
│          └── Verify CANN immutability and existing test regression        │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: 2D Painting Arena & Scripted Fly Baseline                         │
│          ├── Implement canvas.py, brush.py, paint_pot.py, target.py       │
│          └── EXIT CRITERION: Deterministic scripted fly paints target     │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Biological Sensory Interfaces                                     │
│          ├── Multi-channel odor dispersion & AL projection neurons        │
│          └── Visual receptive-field allocentric bearing encoding          │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Biological Motor Bridge & Descending Primitives                   │
│          ├── DN integration & VNC flight/contact primitives               │
│          └── Scripted agent navigates via motor primitives                │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Gymnasium Environment (`FruitFlyPaintEnv`)                        │
│          ├── Gymnasium reset(), step(), Dict spaces, check_env()          │
│          └── Headless benchmark (>3,000 steps/sec)                        │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 5: RL Training Pipeline & Progressive Curriculum                     │
│          ├── Stage 0: Navigation ➔ Stage 1: Odor Homing ➔                 │
│          │   Stage 2: Collection ➔ Stage 3: Stroke Execution              │
│          └── PPO training with VecNormalize and tensorboard logging        │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 6: Multi-Color Painting & Generalization                             │
│          ├── Procedural shape generator & multi-color logo painting       │
│          └── Evaluation on arbitrary uploaded images                      │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 7: Interactive Pygame Dashboard & Live Telemetry UI                  │
│          └── Cyberpunk split UI: Canvas + World + Live CANN Bump + Telemetry│
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 8: Godot 4.7+ 3D Embodiment & Dynamic Canvas Texture                 │
│          └── UDP/WebSocket state bridge to 3D macro flight arena          │
├────────────────────────────────────────────────────────────────────────────┤
│ Phase 9: Research Evaluation & Automated Scientific Ablations              │
│          └── Run Conditions A–E, log metrics, plot publication curves     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 0: Foundation & CANN API Freeze
* **Objective:** Encapsulate the proven continuous attractor dynamics behind an immutable interface so that downstream RL cannot alter biological parameters.
* **Key Tasks:**
  1. Define `CompassState` and `BiologyConfig` in `biology/interfaces.py`.
  2. Implement `biology/cann.py` wrapping `DualRingAttractor`, enforcing parameter freezing (`freeze_weights=True`) and computing SHA-256 parameter fingerprints.
  3. Create `tests/test_cann_freeze.py` to verify that repeated calls to `step()` do not mutate synaptic weights ($W_{ee}, W_{ep}, W_{pe}$) and that heading readout is identical to the verified `toy/circuit.py`.
* **Verification Test:**
  ```bash
  python tests/test_circuit.py
  python tests/test_cann_freeze.py
  ```

### Phase 1: 2D Painting Arena & Scripted Fly Baseline
* **Objective:** Implement the physical world mechanics (canvas, brush, pots, pigment) and prove the task is 100% solvable with a deterministic, non-learning controller before training any RL models.
* **Key Tasks:**
  1. Implement `painting/canvas.py`: $256 \times 256$ RGBA accumulation surface with Gaussian stamp stamping and $32 \times 32$ evaluation downsampling.
  2. Implement `painting/brush.py`: Altitude management ($z$), physical contact detection, pressure dynamics ($P$), and pigment reservoir depletion.
  3. Implement `painting/paint_pot.py`: Discrete pots (Red, Green, Blue, Yellow) with reload zones.
  4. Implement `painting/target.py`: Target processing (RGB, Sobel edges, color distribution).
  5. Implement `painting/scripted_agent.py`: A state machine that sequentially executes:
     $$\text{IDLE} \longrightarrow \text{SEEK\_POT} \longrightarrow \text{DIP\_RELOAD} \longrightarrow \text{SEEK\_CANVAS} \longrightarrow \text{EXECUTE\_STROKE} \longrightarrow \text{FINISH}$$
* **Exit Criterion:**
  The scripted agent completes a simple painting (e.g. Red square on canvas) achieving $S > 0.85$ without any reinforcement learning.
* **Verification Test:**
  ```bash
  python tests/test_painting.py
  python tests/test_scripted.py
  ```

### Phase 2: Biological Sensory Interfaces
* **Objective:** Connect the physical world to biological rate-coded sensory populations.
* **Key Tasks:**
  1. Implement `biology/olfactory.py`: Generates continuous multi-channel Gaussian odor plumes for all $K$ paint pots; simulates ORN firing rates and Antennal Lobe (AL) glomeruli outputs.
  2. Implement `biology/visual.py`: Computes allocentric bearing angles and retinotopic receptive field activations for landmarks, pots, and the canvas surface.
  3. Create `tests/test_sensors.py`: Tests that approaching Pot Red specifically elevates Glomerulus Red without crosstalk.
* **Verification Test:**
  ```bash
  python tests/test_sensors.py
  ```

### Phase 3: Biological Motor Bridge & Descending Primitives
* **Objective:** Implement descending neuron (DN) integration and VNC premotor primitives so that control commands represent biological behaviors rather than uncoordinated low-level torques.
* **Key Tasks:**
  1. Implement `biology/motor.py`: Defines motor primitives:
     * `CRUISE_FORWARD(v)`: Maintained wingbeat forward momentum.
     * `YAW_BIAS(\Delta \omega)`: Modulates left/right haltere-guided steering.
     * `SET_ALTITUDE(z)`: Vertical climb / descent.
     * `ENGAGE_BRUSH(P)`: Lowers pen and regulates surface pressure.
  2. Create `tests/test_motor.py`: Verifies smooth aerodynamic transitions, turn rate limits, and altitude clamping.
* **Verification Test:**
  ```bash
  python tests/test_motor.py
  ```

### Phase 4: Gymnasium Environment (`FruitFlyPaintEnv`)
* **Objective:** Expose the complete hybrid simulation as a standard Gymnasium environment compatible with modern reinforcement learning libraries (Stable-Baselines3).
* **Key Tasks:**
  1. Implement `rl/env.py`: Inherits from `gym.Env`, declaring the exact `Dict` observation space and 4D continuous action space.
  2. Implements `reset(seed=...)` and `step(action)` with multi-rate stepping (1 policy step = 12 physics steps).
  3. Implements potential-based progress reward in `rl/reward.py`.
  4. Run Stable-Baselines3's official environment checker: `from stable_baselines3.common.env_checker import check_env; check_env(env)`.
  5. Profile headless stepping throughput to ensure $>3,000\text{ steps/second}$ on the host CPU/GPU.
* **Verification Test:**
  ```bash
  python tests/test_gym_env.py
  ```

### Phase 5: RL Training Pipeline & Progressive Curriculum
* **Objective:** Train the small PPO policy across a staged behavioral curriculum.
* **Curriculum Progression:**
  * **Stage 0 (Pure Navigation):** Steer to a designated spatial beacon.
  * **Stage 1 (Odor Homing):** Steer toward a specific active paint pot guided by AL odor gradient.
  * **Stage 2 (Pigment Reload):** Land on the pot, hold contact for $300\text{ ms}$ to fill reservoir, and take off.
  * **Stage 3 (Canvas Delivery):** Fly from pot to the canvas surface and execute a landing.
  * **Stage 4 (Single-Color Painting):** Deposit pigment to cover a target monochrome shape (e.g. $8 \times 8$ pixel patch).
* **Key Tasks:**
  1. Implement `rl/train.py` using Stable-Baselines3 `PPO`, wrapping the environment in `VecNormalize` for automatic observation and reward scaling.
  2. Implement checkpointing and TensorBoard logging for reward, SSIM, bump coherence, and episode length.
* **Verification Test:**
  ```bash
  python tests/test_training.py --smoke-test
  ```

### Phase 6: Multi-Color Painting & Generalization
* **Objective:** Extend learned painting strategy to multi-color compositions and evaluate zero-shot transfer to unseen target patterns.
* **Key Tasks:**
  1. Procedural generation of 2-color and 4-color training targets (rectangles, discs, crossbars, letters).
  2. Policy training across randomized procedural targets.
  3. Benchmark generalization on a test set of unseen uploaded images (e.g. icons, geometric emblems).
  4. Measure SSIM and color distribution accuracy over 100 test episodes.

### Phase 7: Interactive Pygame Dashboard & Live Telemetry UI
* **Objective:** Provide a rich, real-time cyberpunk visualization dashboard for demonstration, debugging, and live interaction.
* **UI Features:**
  * **Left Panel (Arena & Canvas):** Live arena view displaying the fly agent, wake particles, multi-pot odor plumes, and real-time canvas pigment deposition alongside the target thumbnail.
  * **Right Panel (Biological & RL Telemetry):**
    * Live E-PG compass ring with active activity bump.
    * Left and Right P-EN shifter activity bars with dynamic torque indicator.
    * Antennal Lobe odor channels (R, G, B, Y).
    * Policy action output bars (residual steering $\Delta \omega$, throttle $v$, altitude $z$, pen pressure $P$).
    * Painting progress gauge ($S_t$), SSIM, and remaining pigment reservoir.
* **Entry Point:** `run_painting.py`

### Phase 8: Godot 4.7+ 3D Embodiment & Dynamic Canvas Texture
* **Objective:** Transfer the verified 2D hybrid simulation into the 3D Godot flight environment for photorealistic embodiment.
* **Key Tasks:**
  1. Set Godot project target baseline to Godot 4.7+ (Forward+ Vulkan Renderer).
  2. Create a high-throughput UDP/IPC telemetry bridge between the Python simulation and Godot.
  3. In Godot: Instantiate a 3D fruit fly model with animated wings and halteres, a physical paintbrush tool, 3D paint pot meshes, and a dynamic canvas mesh whose texture is updated in real time via pixel buffer streams.
  4. Verify that the trained policy executes smooth flight paths in 3D identical to the 2D training physics.

### Phase 9: Scientific Evaluation & Automated Ablation Benchmark
* **Objective:** Automatically execute all five ablation conditions and generate publication-ready comparative figures and tables.
* **Key Tasks:**
  1. Implement `evaluation/ablations.py` to train/evaluate Conditions A, B, C, D, and E across 10 random seeds.
  2. Implement `evaluation/plots.py` to produce:
     * Learning curves (Episode Reward vs Environment Steps).
     * Final SSIM boxplots across conditions.
     * Bump coherence stability during high-speed turns.
     * Trajectory tortuosity and energy consumption comparisons.
  3. Output summary Markdown report in `docs/ablation_results.md`.

---

## 7. Immediate Next Steps & Execution Order

To initiate V2 development cleanly and systematically without regressing current codebase functionality, execution begins with **Phase 0 & Phase 1**:

1. **Create Directory Skeletons:**
   Establish `biology/`, `painting/`, `rl/`, and `evaluation/` with proper `__init__.py` files.
2. **Implement `biology/interfaces.py` & `biology/cann.py`:**
   Freeze `DualRingAttractor`, provide the `CompassState` API, and create `tests/test_cann_freeze.py`.
3. **Implement Canvas & Brush Systems:**
   Build `painting/canvas.py`, `painting/brush.py`, `painting/paint_pot.py`, and `painting/target.py`.
4. **Implement Deterministic Scripted Baseline:**
   Build `painting/scripted_agent.py` and verify via `tests/test_scripted.py` that the fly can paint a simple target pattern purely with classical state-machine navigation before any RL training commences.
