"""
Target Image Generator for Fruitfly V2 Hybrid Painting.
Generates diverse visual patterns into data/targets/ for curriculum training & generalization:
  - Bauhaus Composition (primary color geometric shapes)
  - Drosophila Emblem (stylized fly silhouette)
  - Chromatic Flower (8-petal multi-color radial pattern)
  - Nested Rings (circular flight trajectories)
  - Pixel Heart (8-bit structured block pattern)
  - Yin-Yang Crescent (flowing curved boundaries)
  - Geometric Cross (sharp 90-degree intersections)
"""

import sys
import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def generate_all_targets(output_dir: Path = Path("data/targets")):
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating diverse training target images into {output_dir.resolve()}...")

    # Color definitions matching the 4 paint pots:
    # Pot 0 (Red): (230, 30, 30)
    # Pot 1 (Green): (30, 190, 40)
    # Pot 2 (Blue): (25, 60, 220)
    # Pot 3 (Yellow): (240, 210, 20)
    c_red = (230, 30, 30)
    c_green = (30, 190, 40)
    c_blue = (25, 60, 220)
    c_yellow = (240, 210, 20)
    c_white = (255, 255, 255)

    size = (256, 256)

    # 1. Bauhaus Composition (Red square, Blue circle, Yellow rectangle, Green triangle)
    img1 = Image.new("RGB", size, c_white)
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([40, 40, 110, 110], fill=c_red)
    draw1.ellipse([140, 40, 220, 120], fill=c_blue)
    draw1.rectangle([40, 140, 160, 180], fill=c_yellow)
    draw1.polygon([(180, 220), (225, 145), (135, 145)], fill=c_green)
    img1.save(output_dir / "01_bauhaus_composition.png")

    # 2. Drosophila Emblem (Stylized Fruit Fly with wings and abdomen)
    img2 = Image.new("RGB", size, c_white)
    draw2 = ImageDraw.Draw(img2)
    # Head and Thorax
    draw2.ellipse([116, 50, 140, 74], fill=c_red)  # Head
    draw2.ellipse([110, 78, 146, 128], fill=c_blue)  # Thorax
    draw2.ellipse([114, 130, 142, 215], fill=c_blue)  # Abdomen
    # Left & Right Wings
    draw2.ellipse([45, 80, 115, 175], fill=c_yellow)  # Left wing
    draw2.ellipse([141, 80, 211, 175], fill=c_yellow)  # Right wing
    # Compound eyes
    draw2.ellipse([112, 54, 124, 66], fill=c_red)
    draw2.ellipse([132, 54, 144, 66], fill=c_red)
    img2.save(output_dir / "02_fruitfly_emblem.png")

    # 3. Chromatic Flower (8 radial petals in alternating primary colors)
    img3 = Image.new("RGB", size, c_white)
    draw3 = ImageDraw.Draw(img3)
    cx, cy = 128, 128
    colors = [c_red, c_yellow, c_blue, c_green, c_red, c_yellow, c_blue, c_green]
    for idx, col in enumerate(colors):
        ang = idx * (2.0 * np.pi / 8.0)
        px = cx + int(50.0 * np.cos(ang))
        py = cy + int(50.0 * np.sin(ang))
        r = 24
        draw3.ellipse([px - r, py - r, px + r, py + r], fill=col)
    # Center disc
    draw3.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=c_yellow)
    img3.save(output_dir / "03_chromatic_flower.png")

    # 4. Nested Rings (Target concentric circles)
    img4 = Image.new("RGB", size, c_white)
    draw4 = ImageDraw.Draw(img4)
    draw4.ellipse([30, 30, 226, 226], fill=c_blue)
    draw4.ellipse([54, 54, 202, 202], fill=c_white)
    draw4.ellipse([78, 78, 178, 178], fill=c_red)
    draw4.ellipse([102, 102, 154, 154], fill=c_white)
    draw4.ellipse([114, 114, 142, 142], fill=c_yellow)
    img4.save(output_dir / "04_nested_rings.png")

    # 5. Pixel Art Heart (8-bit structured shape in Red)
    img5 = Image.new("RGB", size, c_white)
    draw5 = ImageDraw.Draw(img5)
    # 12x12 grid centered on canvas (block size 14px)
    heart_pattern = [
        "  ####  ####  ",
        " ############ ",
        " ############ ",
        " ############ ",
        "  ##########  ",
        "   ########   ",
        "    ######    ",
        "     ####     ",
        "      ##      ",
    ]
    bx0, by0 = 46, 68
    b_size = 14
    for r_idx, row in enumerate(heart_pattern):
        for c_idx, char in enumerate(row):
            if char == "#":
                x = bx0 + c_idx * b_size
                y = by0 + r_idx * b_size
                draw5.rectangle([x, y, x + b_size - 1, y + b_size - 1], fill=c_red)
    img5.save(output_dir / "05_pixel_heart.png")

    # 6. Yin-Yang Crescent (Curved split composition in Blue and Yellow)
    img6 = Image.new("RGB", size, c_white)
    draw6 = ImageDraw.Draw(img6)
    # Outer circle in Blue
    draw6.ellipse([48, 48, 208, 208], fill=c_blue)
    # Left crescent chord in Yellow
    draw6.pieslice([48, 48, 208, 208], start=90, end=270, fill=c_yellow)
    # Upper small circle in Yellow
    draw6.ellipse([88, 48, 168, 128], fill=c_yellow)
    # Lower small circle in Blue
    draw6.ellipse([88, 128, 168, 208], fill=c_blue)
    # Inner dots
    draw6.ellipse([120, 80, 136, 96], fill=c_blue)
    draw6.ellipse([120, 160, 136, 176], fill=c_yellow)
    img6.save(output_dir / "06_yin_yang_crescent.png")

    # 7. Geometric Cross & Diamond (Interlocking Red cross + Green accents)
    img7 = Image.new("RGB", size, c_white)
    draw7 = ImageDraw.Draw(img7)
    # Cross bars in Red
    draw7.rectangle([112, 45, 144, 211], fill=c_red)
    draw7.rectangle([45, 112, 211, 144], fill=c_red)
    # Corner diamonds in Green
    draw7.polygon([(78, 78), (92, 64), (106, 78), (92, 92)], fill=c_green)
    draw7.polygon([(164, 78), (178, 64), (192, 78), (178, 92)], fill=c_green)
    draw7.polygon([(78, 178), (92, 164), (106, 178), (92, 192)], fill=c_green)
    draw7.polygon([(164, 178), (178, 164), (192, 178), (178, 192)], fill=c_green)
    # Central disc in Yellow
    draw7.ellipse([116, 116, 140, 140], fill=c_yellow)
    img7.save(output_dir / "07_crossbar_emblem.png")

    # 8. Starry Spiral (Archimedean spiral vortex in Blue and Yellow)
    img8 = Image.new("RGB", size, c_white)
    draw8 = ImageDraw.Draw(img8)
    cx, cy = 128, 128
    theta_vals = np.linspace(0.5, 4.0 * np.pi, 250)
    for idx, t in enumerate(theta_vals):
        r = 7.5 * t
        px = cx + int(r * np.cos(t))
        py = cy + int(r * np.sin(t))
        col = c_blue if idx % 2 == 0 else c_yellow
        draw8.ellipse([px - 5, py - 5, px + 5, py + 5], fill=col)
    img8.save(output_dir / "08_starry_spiral.png")

    # 9. Circuit Microchip (Orthogonal bus tracks with pads in Green and Yellow)
    img9 = Image.new("RGB", size, c_white)
    draw9 = ImageDraw.Draw(img9)
    # Central chip in Green
    draw9.rectangle([96, 96, 160, 160], fill=c_green)
    draw9.rectangle([112, 112, 144, 144], fill=c_yellow)
    # North/South/East/West bus lines
    for offset in [-30, -10, 10, 30]:
        # Top tracks
        draw9.rectangle([128 + offset - 2, 40, 128 + offset + 2, 96], fill=c_green)
        draw9.ellipse([128 + offset - 5, 35, 128 + offset + 5, 45], fill=c_red)
        # Bottom tracks
        draw9.rectangle([128 + offset - 2, 160, 128 + offset + 2, 216], fill=c_green)
        draw9.ellipse([128 + offset - 5, 211, 128 + offset + 5, 221], fill=c_red)
        # Left tracks
        draw9.rectangle([40, 128 + offset - 2, 96, 128 + offset + 2], fill=c_green)
        draw9.ellipse([35, 128 + offset - 5, 45, 128 + offset + 5], fill=c_blue)
        # Right tracks
        draw9.rectangle([160, 128 + offset - 2, 216, 128 + offset + 2], fill=c_green)
        draw9.ellipse([211, 128 + offset - 5, 221, 128 + offset + 5], fill=c_blue)
    img9.save(output_dir / "09_circuit_microchip.png")

    # 10. Sunset Horizon (Horizontal multi-band landscape in Red, Yellow, Blue)
    img10 = Image.new("RGB", size, c_white)
    draw10 = ImageDraw.Draw(img10)
    # Sky bands
    draw10.rectangle([40, 40, 216, 85], fill=c_blue)
    draw10.rectangle([40, 85, 216, 125], fill=c_red)
    draw10.rectangle([40, 125, 216, 160], fill=c_yellow)
    # Sun semi-circle
    draw10.pieslice([98, 90, 158, 150], start=180, end=360, fill=c_red)
    # Ground terrain in Green
    draw10.rectangle([40, 160, 216, 216], fill=c_green)
    img10.save(output_dir / "10_sunset_horizon.png")

    generated_files = list(output_dir.glob("*.png"))
    print(f"Successfully generated {len(generated_files)} training targets:")
    for f in sorted(generated_files):
        print(f"  - {f.name}")


if __name__ == "__main__":
    generate_all_targets()
