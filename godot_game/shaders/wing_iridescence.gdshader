shader_type spatial;
render_mode cull_disabled, blend_mix, depth_draw_always;

// Ultra-High-Fidelity Drosophila melanogaster Thin-Film Wing Shader
// Features:
// 1. Authentic Dipteran wing venation: Costa, R1, R2+3, R4+5, M1+2, CuA, and
//    diagnostic transverse crossveins (r-m and dm-cu)
// 2. Structural Thin-Film Wing Interference Patterns (WIPs): multi-order
//    Newtonian interference displaying iridescent cyan, magenta, violet, and gold
// 3. Realistic chitin membrane transparency, micro-vein depth, and clearcoat sheen

uniform sampler2D wing_vein_texture : hint_default_black;
uniform float wing_phase : hint_range(0.0, 6.28318) = 0.0;
uniform float flutter_amplitude : hint_range(0.0, 0.5) = 0.22;
uniform float flutter_frequency : hint_range(0.0, 250.0) = 200.0;
uniform bool is_left_wing = false;

void vertex() {
    float span_factor = clamp(abs(VERTEX.x) * 2.5, 0.0, 1.0);
    float stroke_phase = wing_phase;
    // Aerodynamic wing camber and dynamic flapping deformation
    float flap_angle = sin(stroke_phase) * flutter_amplitude * span_factor;
    VERTEX.y += flap_angle;
    VERTEX.z += cos(stroke_phase * 0.5) * (flutter_amplitude * 0.35) * span_factor;
    // Subtle spanwise torsional twist during stroke
    VERTEX.y += sin(stroke_phase + 1.2) * (flutter_amplitude * 0.15) * (UV.y - 0.5) * span_factor;
}

void fragment() {
    float NdotV = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
    float cos_theta = NdotV;
    
    // -------------------------------------------------------------
    // 1. Authentic Drosophila Wing Venation Architecture
    // UV.x runs spanwise (0.0 at base to 1.0 at wing tip)
    // UV.y runs chordwise (0.0 at anterior Costa to 1.0 at posterior margin)
    // -------------------------------------------------------------
    float u = clamp(UV.x, 0.0, 1.0);
    float v = clamp(UV.y, 0.0, 1.0);
    
    float vein_intensity = 0.0;
    
    // A. Costa (Thickened anterior margin)
    float costa = 1.0 - smoothstep(0.01, 0.045, v);
    vein_intensity = max(vein_intensity, costa * 1.0);
    
    // B. Subcosta & R1 (Short anterior vein reaching margin around u ~ 0.35)
    float r1_curve = 0.05 + 0.06 * (u / 0.35);
    if (u < 0.40) {
        float r1 = 1.0 - smoothstep(0.0, 0.016, abs(v - r1_curve));
        vein_intensity = max(vein_intensity, r1 * 0.85);
    }
    
    // C. Radius 2+3 (R2+3: Long smooth curve running toward anterior apex)
    float r23_curve = 0.08 + 0.18 * pow(u, 0.85);
    float r23 = 1.0 - smoothstep(0.0, 0.016, abs(v - r23_curve));
    vein_intensity = max(vein_intensity, r23 * 0.90 * smoothstep(0.05, 0.15, u));
    
    // D. Radius 4+5 (R4+5: Central vein running directly to wing tip)
    float r45_curve = 0.14 + 0.30 * pow(u, 0.95);
    float r45 = 1.0 - smoothstep(0.0, 0.017, abs(v - r45_curve));
    vein_intensity = max(vein_intensity, r45 * 0.92 * smoothstep(0.04, 0.12, u));
    
    // E. Media 1+2 (M1+2: Major vein running to postero-apical margin)
    float m12_curve = 0.20 + 0.52 * pow(u, 1.05);
    float m12 = 1.0 - smoothstep(0.0, 0.018, abs(v - m12_curve));
    vein_intensity = max(vein_intensity, m12 * 0.88 * smoothstep(0.05, 0.15, u));
    
    // F. Anterior Crossvein (r-m): Diagnostic transverse bridge between R4+5 and M1+2
    // Located around u ~ 0.38
    if (u > 0.35 && u < 0.42 && v >= r45_curve - 0.02 && v <= m12_curve + 0.02) {
        float rm_x = 1.0 - smoothstep(0.0, 0.018, abs(u - 0.385));
        vein_intensity = max(vein_intensity, rm_x * 0.80);
    }
    
    // G. Posterior Crossvein (dm-cu): Diagnostic transverse bridge between M1+2 and CuA
    // Located around u ~ 0.68
    float cua_curve = 0.32 + 0.55 * pow(u, 1.2);
    if (u > 0.64 && u < 0.73 && v >= m12_curve - 0.02 && v <= cua_curve + 0.02) {
        float dmcu_x = 1.0 - smoothstep(0.0, 0.020, abs(u - 0.685));
        vein_intensity = max(vein_intensity, dmcu_x * 0.75);
    }
    
    // H. Cubitus A1 (CuA): Postero-basal vein
    if (u < 0.78) {
        float cua = 1.0 - smoothstep(0.0, 0.020, abs(v - cua_curve));
        vein_intensity = max(vein_intensity, cua * 0.78 * smoothstep(0.08, 0.20, u));
    }
    
    // I. Basal cell convergence
    if (u < 0.20) {
        float base_vein = 1.0 - smoothstep(0.0, 0.035, abs(v - 0.16));
        vein_intensity = max(vein_intensity, base_vein * 0.85);
    }
    
    // -------------------------------------------------------------
    // 2. Physical Structural Wing Interference Patterns (WIPs)
    // Membrane thickness variation (180nm to 380nm) creates iridescent
    // color shifts: violet, magenta, cyan, and gold fringes
    // -------------------------------------------------------------
    float optical_path = (u * 1.8 + v * 0.9 + (1.0 - cos_theta) * 2.2) * 6.28318;
    vec3 iridescent_wip = vec3(
        0.5 + 0.5 * cos(optical_path + 0.0),      // Red / Gold fringe
        0.5 + 0.5 * cos(optical_path + 2.094),    // Green / Cyan fringe
        0.5 + 0.5 * cos(optical_path + 4.188)     // Blue / Violet fringe
    );
    
    // Blend subtle iridescent sheen with high-clarity transparent membrane
    vec3 membrane_base = vec3(0.92, 0.95, 0.97);
    vec3 membrane_color = mix(membrane_base, iridescent_wip, 0.32);
    
    // Melanic sclerotized chitin vein color (amber-brown to dark sepia)
    vec3 vein_color = vec3(0.24, 0.17, 0.11);
    
    // -------------------------------------------------------------
    // 3. Final Surface Material Assignment
    // -------------------------------------------------------------
    float vein_clamp = clamp(vein_intensity, 0.0, 1.0);
    ALBEDO = mix(membrane_color, vein_color, vein_clamp * 0.85);
    ALPHA = mix(0.22, 0.80, vein_clamp);
    ROUGHNESS = mix(0.06, 0.30, vein_clamp);
    METALLIC = 0.03;
    SPECULAR = 0.88;
    CLEARCOAT = 0.95;
    CLEARCOAT_ROUGHNESS = 0.04;
    RIM = 0.40;
    RIM_TINT = 0.65;
}
