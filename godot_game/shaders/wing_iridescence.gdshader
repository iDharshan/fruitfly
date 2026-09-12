shader_type spatial;
render_mode cull_disabled, blend_mix, depth_draw_always;

uniform sampler2D wing_vein_texture : hint_default_black;
uniform float wing_phase : hint_range(0.0, 6.28318) = 0.0;
uniform float flutter_amplitude : hint_range(0.0, 0.5) = 0.22;
uniform float flutter_frequency : hint_range(0.0, 250.0) = 200.0;
uniform bool is_left_wing = false;

void vertex() {
    // 200 Hz wing oscillation with spanwise twist
    float span_factor = clamp(abs(VERTEX.x) * 1.5, 0.0, 1.0);
    float stroke_phase = wing_phase;
    float flap_angle = sin(stroke_phase) * flutter_amplitude * span_factor;
    VERTEX.y += flap_angle;
    VERTEX.z += cos(stroke_phase * 0.5) * (flutter_amplitude * 0.4) * span_factor;
}

void fragment() {
    float cos_theta = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
    
    // Thin-film Newton rings / iridescent color fringe
    vec3 iridescent_tint = 0.5 + 0.5 * cos(6.28318 * (vec3(0.0, 0.33, 0.67) + (1.0 - cos_theta) * 2.2));
    
    // Vein pattern procedurally generated if no texture
    float vein_intensity = 0.0;
    // Marginal costa vein along UV.y near 0
    vein_intensity += smoothstep(0.06, 0.02, UV.y);
    // Longitudinal veins
    float v1 = 1.0 - smoothstep(0.0, 0.025, abs(UV.y - 0.22));
    float v2 = 1.0 - smoothstep(0.0, 0.025, abs(UV.y - 0.42));
    float v3 = 1.0 - smoothstep(0.0, 0.025, abs(UV.y - 0.65));
    float v4 = 1.0 - smoothstep(0.0, 0.025, abs(UV.y - 0.85));
    vein_intensity += max(max(v1, v2), max(v3, v4)) * smoothstep(0.0, 0.1, UV.x);
    
    ALBEDO = mix(vec3(0.90, 0.95, 1.0) * iridescent_tint, vec3(0.25, 0.16, 0.10), clamp(vein_intensity, 0.0, 0.9));
    ALPHA = mix(0.35, 0.92, clamp(vein_intensity, 0.0, 1.0));
    ROUGHNESS = 0.06;
    METALLIC = 0.12;
    SPECULAR = 0.90;
    CLEARCOAT = 1.0;
    CLEARCOAT_ROUGHNESS = 0.04;
}
