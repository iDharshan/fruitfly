#!/usr/bin/env python3
"""
scripts/export_godot_connectome.py

Exports high-definition 3D morphological connectome data (Ellipsoid Body,
Protocerebral Bridge, Fan-Shaped Body, PFL3 comparator tracts, Antennal Lobes,
and Ventral Nerve Cord) from the Python neuroscience suite directly into
Godot-compatible JSON format.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import numpy as np

from toy.brain_cloud import BrainPointCloud


def export_connectome():
    output_dir = ROOT_DIR / "godot_game" / "assets" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "connectome_1920.json"

    print("==> Initializing 3D Drosophila Connectome Point Cloud...")
    cloud = BrainPointCloud(seed=42)

    nodes_data = []
    for idx, node in enumerate(cloud.nodes):
        pos = node["pos"]
        # Scale to Godot 3D units: ~1.0 unit bounding size centered at origin
        # Original points are approximately -80..80 nm/um
        scaled_pos = [
            float(pos[0] * 0.015),
            float(pos[2] * 0.015), # In Godot, Y is up, Z is depth
            float(-pos[1] * 0.015),
        ]
        region = node.get("region", "OTHER")
        base_rate = float(node.get("base_rate", 10.0))
        
        node_entry = {
            "id": idx,
            "x": scaled_pos[0],
            "y": scaled_pos[1],
            "z": scaled_pos[2],
            "region": region,
            "base_rate": base_rate,
        }
        
        if "wedge" in node:
            node_entry["wedge"] = int(node["wedge"])
        if "col" in node:
            node_entry["col"] = int(node["col"])
        if "channel" in node:
            node_entry["channel"] = int(node["channel"])
            
        nodes_data.append(node_entry)

    edges_data = []
    for edge in cloud.tract_edges:
        src, dst, tract_type = edge
        edges_data.append({
            "src": int(src),
            "dst": int(dst),
            "type": tract_type,
        })

    payload = {
        "metadata": {
            "version": "1.0.0",
            "total_nodes": len(nodes_data),
            "total_tract_edges": len(edges_data),
            "reference_space": "Godot 3D (Y-up, scaled x0.015)",
        },
        "nodes": nodes_data,
        "edges": edges_data,
    }

    print(f"==> Exporting {len(nodes_data)} nodes and {len(edges_data)} tract edges to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"==> Export complete! File size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    export_connectome()
