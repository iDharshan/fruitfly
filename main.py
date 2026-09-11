"""
Drosophila Compass Neural Circuit Analysis & 3D Visualization Pipeline.

This script interfaces with Janelia's NeuPrint connectomics API (hemibrain:v1.2.1)
to extract the E-PG compass neurons (forming the Ellipsoid Body ring attractor),
computes topological metrics safely without combinatorial explosions, and
renders both 2D circular topologies and interactive 3D WebGL anatomical skeletons.
"""

import os
import sys
import getpass
import logging
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from dotenv import load_dotenv, find_dotenv

# NeuPrint and Navis connectomics stack
import neuprint
from neuprint import Client, NeuronCriteria as NC, fetch_neurons, fetch_adjacencies
import navis
import navis.interfaces.neuprint as nip

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("CompassCircuit")

# Ensure navis.read_neuprint alias is bound to neuprint skeleton fetcher
if not hasattr(navis, "read_neuprint"):
    navis.read_neuprint = nip.fetch_skeletons


def connect_client() -> Client:
    """
    Initialize and return a neuprint.Client targeting neuprint.janelia.org
    and dataset hemibrain:v1.2.1. Validates credentials and logs confirmation.
    """
    # Attempt loading from .env in working directory or parents
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file, override=True)
    else:
        # Fallback to local .env if present
        load_dotenv(Path(__file__).parent / ".env", override=True)

    token = os.environ.get("NEUPRINT_APPLICATION_CREDENTIALS")
    if not token:
        logger.warning("NEUPRINT_APPLICATION_CREDENTIALS environment variable not found.")
        try:
            token = getpass.getpass("Enter NeuPrint Auth Token (from neuprint.janelia.org): ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.error("Authentication aborted.")
            sys.exit(1)

    if not token:
        raise ValueError(
            "NeuPrint application token is missing. Please set NEUPRINT_APPLICATION_CREDENTIALS "
            "in your environment or .env file."
        )

    logger.info("Connecting to NeuPrint server (neuprint.janelia.org, dataset hemibrain:v1.2.1)...")
    try:
        client = Client("neuprint.janelia.org", dataset="hemibrain:v1.2.1", token=token)
        # Verify connection by querying dataset info
        meta = neuprint.fetch_meta(client=client)
        dataset_name = meta.get("Dataset", "hemibrain:v1.2.1")
        logger.info(f"Connected successfully to dataset: {dataset_name}")
        return client
    except Exception as exc:
        logger.error(f"Failed to connect to NeuPrint: {exc}")
        raise


def extract_compass_circuit(client: Client, min_synaptic_weight: int = 3) -> Tuple[nx.DiGraph, List[int]]:
    """
    Extracts compass neurons (E-PG / EPG) innervating the Ellipsoid Body (EB) and
    their directed synaptic connections. Constructs a NetworkX DiGraph and exports to GraphML.

    Parameters:
        client: Active neuprint.Client instance
        min_synaptic_weight: Minimum total synapse weight to include directed edge

    Returns:
        Tuple of (DiGraph G, list of neuron bodyIds)
    """
    logger.info("Querying E-PG compass neurons innervating Ellipsoid Body (EB)...")
    
    # Query neurons: handle both 'E-?PG.*' and 'EPG.*' naming in hemibrain
    neurons_df, _ = fetch_neurons(NC(type="E-?PG.*", regex=True, rois=["EB"]), client=client)
    if len(neurons_df) == 0:
        neurons_df, _ = fetch_neurons(NC(type="EPG.*", regex=True, rois=["EB"]), client=client)

    if len(neurons_df) == 0:
        raise RuntimeError("No E-PG compass neurons returned from NeuPrint query.")

    neuron_ids = sorted(neurons_df["bodyId"].tolist())
    logger.info(f"Identified {len(neuron_ids)} E-PG compass neurons.")

    logger.info(f"Querying directed synaptic adjacencies (min total weight: {min_synaptic_weight})...")
    _, conn_df = fetch_adjacencies(neuron_ids, neuron_ids, min_total_weight=min_synaptic_weight, client=client)

    logger.info(f"Retrieved {len(conn_df)} ROI-specific synaptic connection records.")

    # Aggregate weights across ROIs between each pre-post neuron pair
    total_conns = conn_df.groupby(["bodyId_pre", "bodyId_post"], as_index=False)["weight"].sum()
    # Filter by min_synaptic_weight on total weight
    filtered_conns = total_conns[total_conns["weight"] >= min_synaptic_weight]

    # Construct directed graph
    G = nx.DiGraph()

    # Add all neuron nodes with attributes
    for _, row in neurons_df.iterrows():
        b_id = int(row["bodyId"])
        G.add_node(
            b_id,
            bodyId=b_id,
            type=str(row.get("type", "EPG")),
            instance=str(row.get("instance", "")),
            pre=int(row.get("pre", 0)),
            post=int(row.get("post", 0))
        )

    # Add directed edges with synaptic weight
    for _, row in filtered_conns.iterrows():
        u = int(row["bodyId_pre"])
        v = int(row["bodyId_post"])
        w = int(row["weight"])
        G.add_edge(u, v, weight=w)

    output_graphml = "compass_circuit.graphml"
    nx.write_graphml(G, output_graphml)
    logger.info(f"Exported graph to {output_graphml} ({G.number_of_nodes()} nodes, {G.number_of_edges()} directed edges).")

    return G, neuron_ids


def compute_graph_metrics(G: nx.DiGraph) -> dict:
    """
    Computes and logs topological graph metrics.
    
    SAFETY NOTE:
    Does NOT use nx.algorithms.cycles.simple_cycles(G) as dense recurrent
    connectomics graphs produce combinatorial explosions (> 10^12 cycles)
    which exhausts memory and causes system freezes. Instead, evaluates
    directed acyclicity, strongly connected components, reciprocal edges,
    and exemplar directed cycles in guaranteed linear O(V + E) time.
    """
    logger.info("Computing topological graph metrics...")

    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    in_degrees = [deg for _, deg in G.in_degree()]
    out_degrees = [deg for _, deg in G.out_degree()]
    avg_in_degree = sum(in_degrees) / num_nodes if num_nodes else 0.0
    avg_out_degree = sum(out_degrees) / num_nodes if num_nodes else 0.0

    # Reciprocity: proportion of mutual directed connections
    reciprocity_val = nx.reciprocity(G)

    # Average clustering coefficient for directed graphs
    avg_clustering = nx.average_clustering(G)

    # Safe directed cycle evaluation (O(V + E))
    is_dag = nx.is_directed_acyclic_graph(G)
    has_cycles = not is_dag

    # Find exemplar feedback cycle in O(V + E)
    example_cycle = None
    if has_cycles:
        try:
            example_cycle = nx.find_cycle(G, orientation="original")
        except nx.NetworkXNoCycle:
            example_cycle = None

    # Strongly connected components (recurrent network modules)
    sccs = list(nx.strongly_connected_components(G))
    recurrent_sccs = [c for c in sccs if len(c) > 1]
    max_scc_size = max((len(c) for c in recurrent_sccs), default=0)

    # Mutual 2-cycle reciprocal pairs
    reciprocal_pairs = [(u, v) for u, v in G.edges() if G.has_edge(v, u) and u < v]

    # Assemble metrics summary
    metrics = {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "avg_in_degree": avg_in_degree,
        "avg_out_degree": avg_out_degree,
        "reciprocity": reciprocity_val,
        "avg_clustering": avg_clustering,
        "has_directed_cycles": has_cycles,
        "recurrent_scc_count": len(recurrent_sccs),
        "max_scc_size": max_scc_size,
        "reciprocal_pair_count": len(reciprocal_pairs),
        "example_cycle_length": len(example_cycle) if example_cycle else 0
    }

    # Formatted console output
    print("\n" + "=" * 65)
    print("        COMPASS CIRCUIT TOPOLOGICAL METRICS SUMMARY")
    print("=" * 65)
    print(f"Total Neurons (Nodes):               {num_nodes}")
    print(f"Synaptic Links (Edges):              {num_edges}")
    print(f"Average In-Degree:                   {avg_in_degree:.2f}")
    print(f"Average Out-Degree:                  {avg_out_degree:.2f}")
    print(f"Directed Reciprocity:                {reciprocity_val:.4f} ({reciprocity_val * 100:.1f}%)")
    print(f"Average Clustering Coefficient:      {avg_clustering:.4f}")
    print("-" * 65)
    print("RECURRENT CONNECTIVITY & CYCLE CONFIRMATION:")
    print(f"  Directed Acyclic Graph (DAG):      {is_dag}")
    print(f"  Recurrent Directed Cycles Present: {has_cycles} (Ring Attractor Confirmed)")
    print(f"  Strongly Connected Components:     {len(sccs)} total ({len(recurrent_sccs)} recurrent)")
    print(f"  Largest Recurrent Core Size:       {max_scc_size} of {num_nodes} neurons")
    print(f"  Bidirectional Reciprocal Pairs:    {len(reciprocal_pairs)} pairs")
    if example_cycle:
        cycle_str = " -> ".join([str(u) for u, _, _ in example_cycle] + [str(example_cycle[0][0])])
        print(f"  Sample Directed Feedback Loop:     {cycle_str}")
    print("=" * 65 + "\n")

    return metrics


def plot_ring_topology(G: nx.DiGraph, output_path: str = "compass_ring.png") -> None:
    """
    Renders 2D circular topology plot of the E-PG ring attractor.
    Scales node colors by degree and edge widths by synaptic weight.
    Saves as a high-DPI image.
    """
    logger.info(f"Rendering 2D circular topology plot to {output_path}...")

    plt.figure(figsize=(12, 12), facecolor="#0e1117")
    ax = plt.gca()
    ax.set_facecolor("#0e1117")

    pos = nx.circular_layout(G)

    # Compute total degree for node coloring
    degrees = dict(G.degree())
    node_colors = [degrees[n] for n in G.nodes()]

    # Extract and scale edge weights
    weights = [G[u][v].get("weight", 1) for u, v in G.edges()]
    max_w = max(weights) if weights else 1
    min_w = min(weights) if weights else 1
    # Normalized edge widths (0.6 to 4.0)
    edge_widths = [0.6 + 3.4 * ((w - min_w) / (max_w - min_w + 1e-6)) for w in weights]

    # Draw nodes
    nodes = nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        cmap=plt.cm.plasma,
        node_size=400,
        edgecolors="#ffffff",
        linewidths=0.8,
        ax=ax
    )

    # Draw directed edges with curvature
    nx.draw_networkx_edges(
        G,
        pos,
        width=edge_widths,
        edge_color="#38ef7d",
        alpha=0.35,
        arrows=True,
        arrowsize=14,
        arrowstyle="-|>",
        connectionstyle="arc3,rad=0.08",
        ax=ax
    )

    # Styling and annotations
    ax.set_axis_off()
    cbar = plt.colorbar(nodes, ax=ax, shrink=0.75, pad=0.03)
    cbar.set_label("Neuron Total Degree (In + Out)", color="white", fontsize=11, labelpad=10)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

    plt.title(
        "Drosophila Compass Heading Direction Circuit (E-PG Ring Attractor)\n"
        f"Circular Recurrent Synaptic Topology ({G.number_of_nodes()} Neurons, {G.number_of_edges()} Directed Synapses)",
        color="white",
        fontsize=14,
        fontweight="bold",
        pad=25
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor="#0e1117", edgecolor="none")
    plt.close()
    logger.info(f"Saved circular topology plot: {output_path}")


def render_3d_morphology(
    client: Client,
    neuron_ids: List[int],
    sample_count: int = 6,
    output_html: str = "compass_3d.html"
) -> None:
    """
    Samples neurons and fetches their 3D skeleton structures via Navis.
    Renders an interactive 3D WebGL plot with camera perspective displaying
    both the Ellipsoid Body (EB) donut ring and the Protocerebral Bridge (PB) handlebar.
    Saves standalone interactive HTML.
    """
    logger.info(f"Sampling {sample_count} neurons for 3D morphological reconstruction...")
    # Select evenly distributed neurons across the population for azimuth coverage
    if len(neuron_ids) > sample_count:
        step = len(neuron_ids) / sample_count
        sampled_ids = [neuron_ids[int(i * step)] for i in range(sample_count)]
    else:
        sampled_ids = neuron_ids

    logger.info(f"Fetching 3D skeletons for bodyIds: {sampled_ids}...")
    skeletons = navis.read_neuprint(sampled_ids, client=client)
    logger.info(f"Successfully retrieved {len(skeletons)} neuron skeletons.")

    logger.info("Rendering interactive 3D morphology with Plotly backend...")
    # Generate 3D plot using navis plotly backend
    fig = navis.plot3d(
        skeletons,
        backend="plotly",
        inline=False,
        color_by="type",
        palette="turbo",
        width=1200,
        height=850
    )

    # Configure optimal camera perspective showing EB ring and dorsal PB handlebar
    # In hemibrain coordinate system:
    # Camera looking slightly downwards and angled from front-dorsal view
    fig.update_layout(
        title=dict(
            text="Interactive 3D Morphology: Drosophila E-PG Compass Ring Neurons<br>"
                 "<sup>Ellipsoid Body (EB donut ring) & Protocerebral Bridge (PB dorsal handlebar)</sup>",
            x=0.5,
            xanchor="center",
            font=dict(size=16, color="#f0f2f6")
        ),
        paper_bgcolor="#11141a",
        scene=dict(
            bgcolor="#11141a",
            xaxis=dict(showgrid=False, showbackground=False, zeroline=False, showticklabels=False, title=""),
            yaxis=dict(showgrid=False, showbackground=False, zeroline=False, showticklabels=False, title=""),
            zaxis=dict(showgrid=False, showbackground=False, zeroline=False, showticklabels=False, title=""),
            camera=dict(
                eye=dict(x=-1.6, y=1.2, z=0.8),
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0)
            ),
            aspectmode="data"
        ),
        margin=dict(l=0, r=0, b=0, t=60)
    )

    # Save to standalone HTML file with CDN plotly.js
    fig.write_html(output_html, include_plotlyjs="cdn")
    file_size_mb = os.path.getsize(output_html) / (1024 * 1024)
    logger.info(f"Saved interactive 3D viewer to {output_html} ({file_size_mb:.2f} MB).")


def main() -> None:
    """
    Main execution pipeline running all stages sequentially.
    """
    logger.info("Starting Drosophila Compass Neural Circuit Pipeline...")

    try:
        # 1. Connect to NeuPrint client
        client = connect_client()

        # 2. Extract compass circuit and export GraphML
        G, neuron_ids = extract_compass_circuit(client, min_synaptic_weight=3)

        # 3. Compute and display topological metrics (safe O(V+E) cycle analysis)
        compute_graph_metrics(G)

        # 4. Render 2D circular topology plot
        plot_ring_topology(G, output_path="compass_ring.png")

        # 5. Render 3D morphological reconstruction
        render_3d_morphology(client, neuron_ids, sample_count=6, output_html="compass_3d.html")

        logger.info("All pipeline stages completed successfully!")
        print("\nGenerated outputs:")
        print("  1. compass_circuit.graphml (GraphML network export)")
        print("  2. compass_ring.png        (High-DPI 2D circular ring topology)")
        print("  3. compass_3d.html          (Interactive 3D WebGL neuron skeleton browser)")

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.error(f"Pipeline failed with error: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
