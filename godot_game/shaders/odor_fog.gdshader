shader_type fog;

uniform vec3 odor_color : source_color = vec3(0.28, 0.92, 0.48);
uniform vec3 odor_emission : source_color = vec3(0.04, 0.18, 0.08);
uniform float base_density : hint_range(0.0, 1.0) = 0.28;
uniform float turbulence_scale : hint_range(0.1, 10.0) = 3.0;

// Analytical 3D pseudo-noise for volumetric filament turbulence
float hash(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(vec3 x) {
    vec3 p = floor(x);
    vec3 f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash(p + vec3(0.0, 0.0, 0.0)), hash(p + vec3(1.0, 0.0, 0.0)), f.x),
                   mix(hash(p + vec3(0.0, 1.0, 0.0)), hash(p + vec3(1.0, 1.0, 0.0)), f.x), f.y),
               mix(mix(hash(p + vec3(0.0, 0.0, 1.0)), hash(p + vec3(1.0, 0.0, 1.0)), f.x),
                   mix(hash(p + vec3(0.0, 1.0, 1.0)), hash(p + vec3(1.0, 1.0, 1.0)), f.x), f.y), f.z);
}

void fog() {
    vec3 local_pos = OBJECT_POSITION;
    float dist = length(local_pos);
    float falloff = exp(-dist * dist * 1.5);
    
    // Filament turbulence drifting with time
    vec3 sample_coord = WORLD_POSITION * turbulence_scale + vec3(TIME * 0.12, TIME * 0.18, TIME * 0.08);
    float n = noise(sample_coord);
    float filament = smoothstep(0.25, 0.75, n);
    
    DENSITY = base_density * falloff * (0.35 + 0.65 * filament);
    ALBEDO = odor_color;
    EMISSION = odor_emission * (0.7 + 0.5 * filament);
}
