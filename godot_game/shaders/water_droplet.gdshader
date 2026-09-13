shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back;

uniform vec4 droplet_tint : source_color = vec4(0.90, 0.96, 1.0, 0.30);
uniform float roughness : hint_range(0.0, 1.0) = 0.03;
uniform float specular : hint_range(0.0, 1.0) = 0.98;

void fragment() {
    float cos_theta = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
    float fresnel = pow(1.0 - cos_theta, 3.5);
    
    // Optical chromatic dispersion fringe at glancing angles
    vec3 dispersion = vec3(
        pow(1.0 - cos_theta, 3.2),
        pow(1.0 - cos_theta, 3.5),
        pow(1.0 - cos_theta, 3.8)
    ) * 0.22;
    
    ALBEDO = droplet_tint.rgb + dispersion;
    ALPHA = mix(droplet_tint.a, 0.92, fresnel);
    ROUGHNESS = roughness;
    METALLIC = 0.02;
    SPECULAR = specular;
    CLEARCOAT = 1.0;
    CLEARCOAT_ROUGHNESS = 0.02;
    RIM = 0.55;
    RIM_TINT = 0.9;
}
