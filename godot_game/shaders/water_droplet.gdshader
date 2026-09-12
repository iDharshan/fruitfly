shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back;

uniform vec4 droplet_tint : source_color = vec4(0.88, 0.96, 1.0, 0.35);
uniform float roughness : hint_range(0.0, 1.0) = 0.04;
uniform float specular : hint_range(0.0, 1.0) = 0.98;

void fragment() {
    float cos_theta = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
    float fresnel = pow(1.0 - cos_theta, 3.5);
    
    ALBEDO = droplet_tint.rgb;
    ALPHA = mix(droplet_tint.a, 0.88, fresnel);
    ROUGHNESS = roughness;
    METALLIC = 0.05;
    SPECULAR = specular;
    CLEARCOAT = 1.0;
    CLEARCOAT_ROUGHNESS = 0.02;
    RIM = 0.45;
    RIM_TINT = 0.8;
}
