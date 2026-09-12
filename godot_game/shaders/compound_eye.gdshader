shader_type spatial;

uniform vec3 eye_ruby_core : source_color = vec3(0.78, 0.03, 0.06);
uniform vec3 eye_ruby_glow : source_color = vec3(1.0, 0.25, 0.18);
uniform float hex_scale : hint_range(20.0, 300.0) = 80.0;

void fragment() {
    // Hexagonal grid calculation for individual corneal lenses (ommatidia)
    vec2 p = UV * hex_scale;
    vec2 r = vec2(p.x * 1.1547, p.y + p.x * 0.57735);
    vec2 f = fract(r);
    float hex_dist = length(f - 0.5);
    
    float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
    
    // Hex lens boundary shine
    float lens_lens = smoothstep(0.42, 0.48, hex_dist);
    
    ALBEDO = mix(eye_ruby_core, eye_ruby_glow, fresnel * 0.7) * (0.85 + 0.20 * lens_lens);
    ROUGHNESS = 0.10;
    SPECULAR = 0.95;
    EMISSION = eye_ruby_core * (0.15 + 0.1 * fresnel);
    RIM = 0.5;
    RIM_TINT = 0.8;
}
