shader_type spatial;

uniform vec3 amber_base : source_color = vec3(0.85, 0.52, 0.20);
uniform vec3 charcoal_stripe : source_color = vec3(0.18, 0.12, 0.08);
uniform float stripe_frequency : hint_range(1.0, 20.0) = 6.0;
uniform float stripe_sharpness : hint_range(1.0, 10.0) = 4.0;
uniform float cuticle_roughness : hint_range(0.0, 1.0) = 0.38;

void fragment() {
    // Abdominal tergite banding along UV.y
    float band = sin(UV.y * 3.14159 * stripe_frequency);
    float stripe_mask = clamp(pow(clamp(band, 0.0, 1.0), stripe_sharpness) * 2.0, 0.0, 1.0);
    
    vec3 col = mix(amber_base, charcoal_stripe, stripe_mask);
    
    ALBEDO = col;
    ROUGHNESS = cuticle_roughness;
    METALLIC = 0.08;
    SPECULAR = 0.45;
    RIM = 0.35;
    RIM_TINT = 0.6;
}
