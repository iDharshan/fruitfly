shader_type spatial;

// High-Fidelity Drosophila melanogaster Compound Eye Shader
// Features:
// 1. Hexagonal ommatidial corneal facet lattice (~750-800 ommatidia)
// 2. Biological Pseudopupil: optical rhabdom absorption creates a dark
//    center that dynamically tracks the viewer's gaze
// 3. Deep ruby-red pteridine pigment core with radiant orange-amber Fresnel rim
// 4. Corneal clearcoat reflection with per-facet specular glint

uniform vec3 eye_ruby_core : source_color = vec3(0.72, 0.02, 0.05);
uniform vec3 eye_ruby_glow : source_color = vec3(1.0, 0.28, 0.14);
uniform vec3 pseudopupil_color : source_color = vec3(0.10, 0.01, 0.02);
uniform float hex_scale : hint_range(20.0, 300.0) = 95.0;
uniform float pseudopupil_size : hint_range(0.0, 1.0) = 0.55;

void fragment() {
    // Hexagonal lattice coordinates for corneal facets
    vec2 p = UV * hex_scale;
    vec2 r = vec2(p.x * 1.1547, p.y + p.x * 0.57735);
    vec2 f = fract(r);
    float hex_dist = length(f - 0.5);
    
    // Ommatidial facet dome curvature normal perturbation
    float facet_rim = smoothstep(0.40, 0.48, hex_dist);
    
    // View alignment: cos(theta) between surface normal and camera view
    float NdotV = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
    float fresnel = pow(1.0 - NdotV, 3.2);
    
    // Biological Pseudopupil:
    // When looking directly along the optical axis of the ommatidia, the deep
    // photoreceptor rhabdoms trap light, appearing as a dark tracking center.
    float gaze_alignment = pow(NdotV, 4.0);
    float pseudopupil_mask = smoothstep(1.0 - pseudopupil_size * 0.5, 1.0, gaze_alignment);
    
    // Base pigment color blending: ruby core to radiant Fresnel rim
    vec3 pigment_color = mix(eye_ruby_core, eye_ruby_glow, fresnel * 0.85);
    
    // Modulate by hexagonal corneal facet boundaries
    pigment_color *= (0.86 + 0.18 * facet_rim);
    
    // Apply pseudopupil absorption
    vec3 final_albedo = mix(pigment_color, pseudopupil_color, pseudopupil_mask * 0.78);
    
    ALBEDO = final_albedo;
    ROUGHNESS = mix(0.12, 0.28, facet_rim);
    SPECULAR = 0.90;
    METALLIC = 0.02;
    CLEARCOAT = 0.95;
    CLEARCOAT_ROUGHNESS = 0.08;
    
    // Biological bioluminescent / metabolic eye glow
    EMISSION = eye_ruby_core * (0.12 + 0.16 * fresnel) * (1.0 - pseudopupil_mask * 0.6);
    RIM = 0.65;
    RIM_TINT = 0.75;
}
