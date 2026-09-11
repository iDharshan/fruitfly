# Drosophila Compass Neural Circuit Analysis & 3D Interactive Viewer

An end-to-end Python connectomics pipeline that interfaces with Janelia's **NeuPrint API** (`hemibrain:v1.2.1`) to extract the fruit fly (*Drosophila melanogaster*) heading direction circuit (**E-PG compass neurons** forming the **Ellipsoid Body ring attractor**), computes graph topological metrics safely without combinatorial explosions, and renders both 2D circular topologies and interactive 3D WebGL anatomical neuron skeletons.

---

## 🧠 Biological & Computational Background

In the central complex of the fruit fly brain, **E-PG neurons** (*Ellipsoid body – Protocerebral bridge – Gall*) function as the insect's internal compass:
- **Donut-Shaped Ring Attractor (Ellipsoid Body - EB):** A localized bump of neural activity moves along the ring, tracking the fly's angular orientation ($0^\circ \text{ to } 360^\circ$) in real time.
- **Topographic Phase Shift (Protocerebral Bridge - PB):** Ascending axons map circular azimuth onto bilateral columns in the dorsal handlebar, enabling left/right angular velocity signals to steer and update the heading bump.
- **Continuous Attractor Architecture:** This circuit provides definitive physical proof of continuous attractor neural network (CANN) dynamics in biological hardware.

---

## ⚡ Safe Graph Topology & Cycle Detection

The E-PG circuit contains **50 neurons and 487 directed synapses** with **83.8% reciprocity** and a dense recurrent core spanning 48 neurons. 

> [!WARNING]
> **Avoid `nx.algorithms.cycles.simple_cycles(G)`:**  
> In a 50-node dense recurrent network of this density, the number of simple directed cycles exceeds $10^{12}$ (trillions). Attempting to enumerate all simple cycles causes immediate memory exhaustion, extreme swap thrashing, and complete OS freeze.

### $O(V + E)$ Linear-Time Verification:
This pipeline verifies recurrent ring attractor connectivity safely in milliseconds using:
1. **DAG Check (`nx.is_directed_acyclic_graph`):** Topologically confirms directed feedback cycles exist ($O(V + E)$).
2. **Strongly Connected Components (`nx.strongly_connected_components`):** Identifies recurrent modules ($O(V + E)$), proving 48 of 50 neurons participate in recurrent feedback loops.
3. **Directed Reciprocity (`nx.reciprocity`):** Measures mutual connection density ($83.8\%$).
4. **Exemplar Feedback Cycles (`nx.find_cycle`):** Isolates sample directed feedback loops in linear time.

---

## 📊 Circuit Topological Metrics

| Metric | Measured Value | Significance |
| :--- | :--- | :--- |
| **Total Neurons (Nodes)** | 50 | Full E-PG population innervating EB |
| **Directed Synaptic Links (Edges)** | 487 | Synaptic connections ($\ge 3$ weight) |
| **Average In / Out Degree** | 9.74 | High intra-population interconnectivity |
| **Directed Reciprocity** | 83.78% | Strong mutual feedback between neuron pairs |
| **Clustering Coefficient** | 0.6498 | High local clustering characteristic of attractors |
| **Recurrent Core Size** | 48 / 50 neurons | Global recurrent ring connectivity |
| **Bidirectional Pairs** | 204 pairs | Substrates for continuous bump propagation |

---

## 🚀 Getting Started

### 1. Prerequisites & Installation

```bash
# Clone the repository
git clone https://github.com/iDharshan/fruitfly.git
cd fruitfly

# Create and activate virtual environment
python3 -m venv fly_env
source fly_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. NeuPrint Credentials
Get an auth token from [neuprint.janelia.org](https://neuprint.janelia.org) (*Sign in $\to$ Account $\to$ Copy Token*).

Add it to a `.env` file in the project root:
```bash
echo 'NEUPRINT_APPLICATION_CREDENTIALS="your_token_here"' > .env
```
*(The `.env` file is gitignored to protect credentials).*

### 3. Run the Pipeline

```bash
python main.py
```

---

## 📁 Generated Outputs

1. **`compass_circuit.graphml`**: The raw directed graph serialized with neuron metadata (`bodyId`, `type`, `instance`, `pre`, `post`) and edge synaptic `weight` attributes.
2. **`compass_ring.png`**: High-resolution (300 DPI) circular topology graph visualization scaled by neuron degree and synaptic weight.
3. **`compass_3d.html`**: Interactive WebGL 3D morphological reconstruction of sampled E-PG neuron skeletons showing both the Ellipsoid Body donut ring and Protocerebral Bridge handlebar.

---

## 🖥️ Viewing the Interactive 3D Model

Open `compass_3d.html` directly in your browser:

```bash
# Linux
xdg-open compass_3d.html
# or
google-chrome compass_3d.html
# or
firefox compass_3d.html
```

- **Left-click + Drag:** Rotate 3D camera.
- **Scroll:** Zoom in / out.
- **Right-click + Drag:** Pan across the brain.
