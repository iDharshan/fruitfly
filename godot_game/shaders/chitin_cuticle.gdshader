shader_type spatial;

// High-Fidelity Drosophila melanogaster Chitin Cuticle Shader
// Supports anatomical differentiation:
// - Thorax: Honey-amber scutum with longitudinal melanic vittae
// - Abdomen: Segmented tergite bands (T1-T6) with dark posterior bands and male apical melanization
// - Head & Appendages: Warm sclerotized chitin with natural subsurface scattering

uniform vec3 amber_base : source_color = vec3(0.68, 0.49, 0.28);
uniform vec3 charcoal_stripe : source_color = vec3(0.12, 0.08, 0.05);
uniform vec3 pleural_pale : source_color = vec3(0.82, 0.70, 0.50);
uniform float stripe_frequency : hint_range(1.0, 20.0) = 5.0;
uniform float stripe_sharpness : hint_range(1.0, 10.0) = 2.8;
uniform float cuticle_roughness : hint_range(0.0, 1.0) = 0.38;
uniform bool is_abdomen = false;
uniform bool is_thorax = false;

void fragment() {
    vec3 base_col = amber_base;
    float roughness_val = cuticle_roughness;
    
    if (is_abdomen) {
        // Abdominal tergites: 6 distinct segments along UV.y
        // Each tergite has an amber anterior half and a crisp melanic posterior band
        float seg_coord = UV.y * 6.0;
        float seg_frac = fract(seg_coord);
        
        // Posterior edge banding within each segment
        float band = smoothstep(0.40, 0.65, seg_frac);
        
        // Male Drosophila melanogaster apical melanization:
        // Posterior segments (UV.y > 0.65) are heavily melanized (almost solid dark)
        float apical_melanism = smoothstep(0.60, 0.90, UV.y) * 0.75;
        float total_melanin = clamp(max(band, apical_melanism), 0.0, 1.0);
        
        base_col = mix(amber_base, charcoal_stripe, total_melanin);
        
        // Lateral pale pleural membrane along UV.x edges
        float pleural_mask = 1.0 - smoothstep(0.05, 0.18, abs(UV.x - 0.5) * 2.0);
        base_col = mix(base_col, pleural_pale, (1.0 - pleural_mask) * 0.25);
        roughness_val = mix(0.32, 0.46, total_melanin);
        
    } else if (is_thorax) {
        // Mesothorax scutum: Longitudinal dorsal vittae (stripes along UV.x)
        float vitta_left = 1.0 - smoothstep(0.0, 0.06, abs(UV.x - 0.40));
        float vitta_right = 1.0 - smoothstep(0.0, 0.06, abs(UV.x - 0.60));
        float vitta_center = 1.0 - smoothstep(0.0, 0.04, abs(UV.x - 0.50)) * 0.5;
        float vittae = clamp(max(vitta_left, vitta_right) + vitta_center, 0.0, 1.0);
        
        base_col = mix(amber_base, charcoal_stripe, vittae * 0.55);
        roughness_val = 0.34;
        
    } else {
        // Head / limbs / proboscis: Warm uniform chitin with subtle gradient
        float vert_grad = smoothstep(0.0, 1.0, UV.y);
        base_col = mix(amber_base, charcoal_stripe * 1.2, vert_grad * 0.25);
    }
    
    // Micro-surface chitin texture
    float micro_tex = sin(UV.x * 120.0) * sin(UV.y * 120.0) * 0.02;
    base_col += vec3(micro_tex);
    
    ALBEDO = base_col;
    ROUGHNESS = roughness_val;
    METALLIC = 0.03;
    SPECULAR = 0.42;
    
    // Subsurface translucency (amber rim illumination)
    RIM = 0.52;
    RIM_TINT = 0.85;
    
    // Clearcoat natural insect wax layer
    CLEARCOAT = 0.35;
    CLEARCOAT_ROUGHNESS = 0.20;
}
