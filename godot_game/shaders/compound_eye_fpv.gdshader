shader_type canvas_item;

// Drosophila Compound Eye Ommatidia & Chromatic Dispersion Filter
// Authentic insect first-person vision with hexagonal corneal faceting,
// peripheral chromatic aberration (red/cyan fringe), and corneal lens barrel vignette.

uniform float intensity : hint_range(0.0, 1.0) = 0.0;
uniform float hex_scale : hint_range(20.0, 250.0) = 110.0;
uniform float chromatic_aberration : hint_range(0.0, 0.05) = 0.008;
uniform float vignette_radius : hint_range(0.2, 1.5) = 0.95;
uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;

void fragment() {
	vec4 base_color = texture(screen_texture, SCREEN_UV);
	if (intensity > 0.001) {
		vec2 uv = SCREEN_UV;
	vec2 center = vec2(0.5, 0.5);
	vec2 offset_from_center = uv - center;
	float dist = length(offset_from_center);

	// Hexagonal ommatidia lenslet coordinate transformation
	float s = hex_scale;
	vec2 hex_grid = uv * vec2(s * 1.1547, s);
	vec2 hex_local = fract(hex_grid) - 0.5;
	float hex_dist = length(hex_local);

	// Subtle corneal lenslet curvature
	vec2 lens_uv = uv + hex_local * (0.0018 * intensity);

	// Chromatic dispersion radiating from center
	float chrom = chromatic_aberration * intensity * (0.6 + dist * 1.8);
	vec2 dir = normalize(offset_from_center + vec2(1e-5));

	float r_col = texture(screen_texture, lens_uv + dir * chrom).r;
	float g_col = texture(screen_texture, lens_uv).g;
	float b_col = texture(screen_texture, lens_uv - dir * chrom).b;
	vec3 col = vec3(r_col, g_col, b_col);

	// Subtle ommatidia hexagonal corneal seam lines
	float facet_rim = smoothstep(0.40, 0.48, hex_dist);
	col *= (1.0 - facet_rim * 0.18 * intensity);

	// Peripheral corneal vignette
	float vig = smoothstep(vignette_radius, vignette_radius - 0.55, dist);
	col *= mix(1.0, vig, 0.45 * intensity);

	// Organic ruby corneal sheen in extreme periphery
	vec3 ruby_sheen = vec3(1.08, 0.92, 0.94);
	col = mix(col, col * ruby_sheen, dist * 0.22 * intensity);

		COLOR = vec4(mix(base_color.rgb, col, intensity), 1.0);
	} else {
		COLOR = base_color;
	}
}
