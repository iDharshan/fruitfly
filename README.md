# 🪰 Drosophila Closed-Loop Compass Attractor Circuit (E-PG + P-EN)

<p align="center">
  <img src="https://img.shields.io/badge/Dataset-hemibrain%3Av1.2.1-blue.svg?style=for-the-badge&logo=dna" alt="Dataset">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/API-Janelia%20NeuPrint-orange.svg?style=for-the-badge" alt="NeuPrint">
  <img src="https://img.shields.io/badge/Morphology-Navis-blueviolet.svg?style=for-the-badge" alt="Navis">
  <img src="https://img.shields.io/badge/3D%20Viewer-Plotly%20WebGL-success.svg?style=for-the-badge&logo=plotly" alt="Plotly">
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License">
</p>

An end-to-end computational connectomics pipeline that interfaces with Janelia Research Campus's **NeuPrint API** (`hemibrain:v1.2.1`) to extract, analyze, and visualize the complete **closed-loop heading direction attractor circuit** of the fruit fly (*Drosophila melanogaster*).

The pipeline extracts and co-models both:
1. **E-PG Compass Neurons** (*Ellipsoid body – Protocerebral bridge – Gall*): The biological "compass needle" maintaining head direction azimuth ($\theta$).
2. **P-EN Shifter Neurons** (*Protocerebral bridge – Ellipsoid body – Noduli*, `PEN_a/PEN1` and `PEN_b/PEN2`): The motor angular velocity ($\dot{\theta}$) "shifter" neurons driving heading updates during rotational steering.

The system evaluates topological recurrence without combinatorial cycle explosions, characterizes four-block synaptic connectivity, and renders **2D dual-ring recurrent topologies** as well as **interactive 3D WebGL anatomical neuron skeletons**.

---

### 📸 Visual Gallery

| 2D Dual-Ring Recurrent Topology | Co-Rendered 3D Neuron Morphology |
| :---: | :---: |
| ![Dual Ring](compass_dual_ring.png) | ![Dual 3D](compass_dual_3d_preview.png) |
| *Concentric circular topology of 92 neurons (50 inner E-PG cyan, 42 outer P-EN magenta).* | *3D projection of matched E-PG (cyan) and P-EN (magenta) neurons across EB and PB.* |

> [!TIP]
> **Interactive 3D WebGL Viewer:** Open [`compass_dual_3d.html`](compass_dual_3d.html) directly in any web browser to rotate, zoom, and inspect full 3D morphology of both populations in real-time WebGL.

---

## 🧠 Scientific & Biological Background: The E-PG ⇄ P-EN Shifter Loop

In the central complex of *Drosophila*, internal heading direction is maintained as a localized bump of excitation within a continuous ring attractor network. During turns, this activity bump must shift around the ring to faithfully reflect physical head rotation. This is accomplished via an anatomically phase-shifted recurrent feedback loop between **E-PG** and **P-EN** neurons:

```
                  ┌────────────────────────────────────────────────────────┐
                  │       Protocerebral Bridge (PB Handlebar)              │
                  │       [L9] ... [L3] [L2] [L1] | [R1] [R2] [R3] ... [R9]│
                  └─────────▲───────────────────────────────────┬──────────┘
                            │ (Ascending E-PG Axons)            │ (P-EN Dendrites:
                            │                                   │  receives E-PG +
                            │                                   │  angular velocity)
                 ┌──────────┴──────────┐              ┌─────────▼──────────┐
                 │    E-PG Compass     │              │    P-EN Shifter    │
                 │   Needle (n=50)     │              │   Neurons (n=42)   │
                 └──────────▲──────────┘              └─────────┬──────────┘
                            │                                   │ (Phase-Shifted
                            │ (Local Recurrence)                │  Feedback: ±1 column)
                  ┌─────────┴───────────────────────────────────▼──────────┐
                  │              Ellipsoid Body (EB Donut Ring)            │
                  │   [Wedge 1] ──> [Wedge 2] ──> [Wedge 3] ... [Wedge 8]   │
                  │     ↺ Left Turn (PEN_L): CCW Shift (-45°) ↺            │
                  │     ↻ Right Turn (PEN_R): CW Shift (+45°) ↻            │
                  └────────────────────────────────────────────────────────┘
```

### Key Anatomical Principles:
1. **Compass Needle (E-PG):** Each E-PG neuron extends dendrites in an Ellipsoid Body wedge and sends axonal projections to a specific Protocerebral Bridge glomerulus (e.g., PB column L3 or R3), encoding current heading azimuth ($\theta$).
2. **Angular Velocity Modulation (P-EN):** P-EN neurons in the PB receive excitation from E-PGs as well as asymmetrical turn-rate signals from the lateral accessory lobes / noduli representing angular velocity ($\dot{\theta}$).
3. **Anatomical Phase Shift ($\pm 1$ PB Column / $\pm 45^\circ$ EB Offset):**
   - P-EN neurons originating in the **Left PB** project back to the EB shifted by **1 wedge counter-clockwise** ($\Delta \theta = -45^\circ$).
   - P-EN neurons originating in the **Right PB** project back to the EB shifted by **1 wedge clockwise** ($\Delta \theta = +45^\circ$).
4. **Closed-Loop Dynamic Steering:** When the fly rotates to the left, left-hemisphere P-EN neurons fire more vigorously, injecting phase-shifted feedback into the EB that pulls the activity bump leftward. Asymmetric motor input thus dynamically rotates the compass needle!
5. **Asymmetric Synaptic Weight Driving Force:** Feedback from P-EN to E-PG (**21,937 synapses**) is more than **2.09× stronger** than feedforward E-PG to P-EN excitation (**10,479 synapses**), ensuring strong driving torque to lock and translate the activity bump.

---

## ⚡ Safe Graph Topology & Cycle Analysis: $O(V + E)$ Linear Time

The full closed-loop attractor network consists of **92 neurons and 2,650 directed synaptic connections** (with total synaptic weight $\ge 3$).

> [!CAUTION]
> **CRITICAL SAFETY CONSTRAINT: Why `nx.algorithms.cycles.simple_cycles(G)` Freezes Systems:**  
> In dense recurrent connectomics graphs with ~90 nodes and >2,600 edges, enumerating elementary directed cycles via Johnson's algorithm encounters a factorial combinatorial explosion ($> 10^{14}$ cycles). Cycle enumeration will consume dozens of gigabytes of RAM in seconds, thrash swap space, and hard-freeze the operating system.

### Safe Linear-Time $O(V + E)$ Verification:
To verify recurrence with zero risk of memory exhaustion, this pipeline employs mathematically sound linear-time graph theory checks:
- **Directed Acyclic Graph Check (`nx.is_directed_acyclic_graph`):** Runs topological sort in $O(V + E)$ (~2 ms). Returns `False`, formally proving the existence of recurrent directed loops.
- **Strongly Connected Components (`nx.strongly_connected_components`):** Identifies recurrent modules in $O(V + E)$ (~2 ms). Proves that **all 92 of 92 neurons (100%)** form a single, unified recurrent core.
- **Directed Reciprocity (`nx.reciprocity`):** Computes bidirectional symmetry in $O(E)$ time, revealing an exceptional **85.43%** combined network reciprocity (and E-PG subnetwork reciprocity: **83.78%**), with **488** inter-population mutual pairs (79.41% inter-population reciprocity).
- **Exemplar Cycle Extraction (`nx.find_cycle`):** Isolates specific directed feedback loops (e.g., `387364605 ⇄ 387023620`) in linear time without exponential state-space traversal.

---

## 📊 Measured Network & Attractor Dynamics Metrics

### 1. Four-Block Functional Connectivity Breakdown

| Functional Block | Biological / Circuit Role | Directed Edges | Connection Density | Total Synapses | Mean Synapse Weight |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`E-PG -> E-PG`** | Local Compass Recurrent Excitation | `487` | `19.9%` | `7,706` | `15.82` |
| **`E-PG -> P-EN`** | Ascending Compass Signal to Motor Shifter | `548` | `26.1%` | `10,479` | `19.12` |
| **`P-EN -> E-PG`** | Phase-Shifted Angular Velocity Feedback | `681` | `32.4%` | `21,937` | `32.21` |
| **`P-EN -> P-EN`** | Lateral Shifter Coordination | `934` | `54.2%` | `11,252` | `12.05` |
| **Total Circuit** | **Closed-Loop Ring Attractor** | **`2,650`** | **`31.6%`** | **`51,374`** | **`19.39`** |

### 2. Recurrent Topology & Dynamical Indicators

| Metric | Single E-PG Circuit | Full E-PG + P-EN Attractor | Biological Interpretation |
| :--- | :---: | :---: | :--- |
| **Neuron Population (Nodes)** | `50` | `92` (50 E-PG + 42 P-EN) | Complete heading maintenance + steering system |
| **Directed Synaptic Edges** | `487` | `2,650` (weight $\ge 3$) | Full cross-population connectivity matrix |
| **Total Synapses** | `7,706` | `51,374` | Comprehensive synaptic substrate |
| **Average Degree (In / Out)** | `9.74` | `28.80` | Dense interconnectivity across columns and wedges |
| **Combined Reciprocity** | `83.78%` | `85.43%` | High bidirectional coupling reinforcing state stability |
| **Inter-Population Reciprocity** | — | `79.41%` (488 mutual pairs) | Tight feedback coupling between needle and shifters |
| **Unified Recurrent Core Size** | `48 / 50` (96.0%) | **`92 / 92` (100.0%)** | Unbroken closed-loop recurrent core across all neurons |
| **$\frac{\text{Feedback}}{\text{Feedforward}}$ Ratio** | — | **`2.09×`** ($21,937 / 10,479$) | Motor shifter feedback exerts dominant driving torque |

---

## 📂 Repository Structure

```text
fruitfly/
├── main.py                          # Modular end-to-end closed-loop attractor pipeline
├── requirements.txt                 # Python dependencies (neuprint-python, navis, networkx, etc.)
├── .gitignore                       # Excludes virtual environments, cache, and sensitive .env tokens
├── .env                             # NeuPrint credentials (gitignored)
├── README.md                        # Documentation, scientific theory, and metrics
│
├── compass_dual_ring.png            # High-DPI (300 DPI) 2D dual concentric ring topology
├── compass_dual_3d.html             # Standalone interactive 3D WebGL dual skeleton viewer
├── compass_dual_3d_preview.png     # High-DPI 2D projection preview of dual 3D skeletons
├── compass_epg_pen_circuit.graphml  # Full E-PG + P-EN directed graph export with metadata
│
├── compass_ring.png                 # (Legacy) 2D single-ring E-PG topology
├── compass_3d.html                  # (Legacy) Interactive 3D E-PG skeleton viewer
├── compass_3d_preview.png           # (Legacy) 2D preview of E-PG skeletons
└── compass_circuit.graphml          # (Legacy) E-PG directed graph export
```

---

## 🚀 Getting Started

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/iDharshan/fruitfly.git
cd fruitfly

# Create and activate virtual environment
python3 -m venv fly_env
source fly_env/bin/activate

# Install required packages
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Credentials

Obtain an access token from [neuprint.janelia.org](https://neuprint.janelia.org) (*Sign In $\to$ Account $\to$ Copy Token*).

Add your token to `.env` in the repository root (this file is excluded by `.gitignore`):

```bash
echo 'NEUPRINT_APPLICATION_CREDENTIALS="your_actual_token_here"' > .env
```

### 3. Execute Pipeline

Run the closed-loop attractor pipeline:

```bash
./fly_env/bin/python main.py
```

The pipeline automatically:
1. Connects to Janelia's NeuPrint server (`hemibrain:v1.2.1`).
2. Queries the 50 E-PG compass neurons and 42 P-EN shifter neurons (`PEN_a` & `PEN_b`).
3. Fetches directed synaptic adjacencies ($\ge 3$ weight) and exports `compass_epg_pen_circuit.graphml`.
4. Executes linear-time $O(V+E)$ dynamics analysis across all 4 connectivity blocks.
5. Renders the 2D concentric dual-ring topology (`compass_dual_ring.png`, 300 DPI).
6. Fetches 3D skeletons via Navis and compiles the interactive WebGL browser (`compass_dual_3d.html`) and projection preview (`compass_dual_3d_preview.png`).

---

## 🕹️ Inspecting the Interactive 3D Model

Open [`compass_dual_3d.html`](compass_dual_3d.html) in any modern browser:

```bash
# Linux
xdg-open compass_dual_3d.html
# or
google-chrome compass_dual_3d.html
# or
firefox compass_dual_3d.html
```

### Navigation Controls:
- **Left-Click + Drag:** Full 360° 3D orbital camera rotation.
- **Scroll Wheel:** Smooth zooming into individual dendritic arborizations in the EB and PB.
- **Right-Click + Drag:** Pan across the central brain coordinate space.

---

## 📚 References & Literature

- **E-PG and P-EN Ring Attractor Dynamics:**  
  Turner-Evans, D. et al. (2020). *The neuroanatomical ultrastructure and function of a heading direction circuit.* **Neuron**, 108(1), 145-163. [doi:10.1016/j.neuron.2020.08.006](https://doi.org/10.1016/j.neuron.2020.08.006).
- **Neural Mechanism for Heading Computation:**  
  Green, J. et al. (2017). *A neural circuit architecture for angular velocity integration in Drosophila.* **Nature**, 546(7656), 101-106. [doi:10.1038/nature22343](https://doi.org/10.1038/nature22343).
- **Connectomics of the Adult Drosophila Central Complex:**  
  Hulse, B.K. et al. (2021). *A connectome of the Drosophila central complex reveals network motifs suitable for flexible navigation and motor control.* **eLife**, 10:e66039. [doi:10.7554/eLife.66039](https://doi.org/10.7554/eLife.66039).
- **Janelia Hemibrain Connectome Dataset:**  
  Scheffer, L.K. et al. (2020). *A connectome and analysis of the adult Drosophila central brain.* **eLife**, 9:e57443. [doi:10.7554/eLife.57443](https://doi.org/10.7554/eLife.57443).
- **Navis Connectomics Framework:**  
  Bates, A.S. et al. (2020). *navis: Morphology and connectivity analysis of neuronal data.* [navis.readthedocs.io](https://navis.readthedocs.io/).
