shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

// Minimalist Dark Grey Grid Shader
// Generates anti-aliased procedural grid lines with distance fade into deep void

uniform vec4 background_color : source_color = vec4(0.018, 0.018, 0.022, 1.0);
uniform vec4 minor_line_color : source_color = vec4(0.14, 0.15, 0.17, 1.0);
uniform vec4 major_line_color : source_color = vec4(0.26, 0.28, 0.32, 1.0);
uniform vec4 axis_x_color : source_color = vec4(0.45, 0.18, 0.20, 1.0);
uniform vec4 axis_z_color : source_color = vec4(0.18, 0.32, 0.48, 1.0);

uniform float minor_grid_size : hint_range(0.1, 10.0) = 1.0;
uniform float major_grid_mult : hint_range(2.0, 20.0) = 5.0;
uniform float line_thickness : hint_range(0.01, 0.2) = 0.025;
uniform float fade_start : hint_range(10.0, 200.0) = 45.0;
uniform float fade_end : hint_range(20.0, 400.0) = 120.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float get_grid(vec2 pos, float size, float thickness) {
	vec2 coord = pos / size;
	vec2 grid = abs(fract(coord - 0.5) - 0.5);
	vec2 d = fwidth(coord);
	vec2 aagrid = smoothstep(thickness + d * 1.5, thickness - d * 1.5, grid);
	return max(aagrid.x, aagrid.y);
}

void fragment() {
	vec2 p = world_pos.xz;
	
	// Distance fade to smooth horizon void
	float dist = length(p - CAMERA_POSITION_WORLD.xz);
	float fade = clamp(1.0 - (dist - fade_start) / max(fade_end - fade_start, 1.0), 0.0, 1.0);
	
	// Minor & Major grids
	float minor = get_grid(p, minor_grid_size, line_thickness);
	float major = get_grid(p, minor_grid_size * major_grid_mult, line_thickness * 1.4);
	
	// Subtle coordinate axes
	vec2 axis_dist = abs(p);
	vec2 d_axis = fwidth(p);
	float axis_x = smoothstep(0.03 + d_axis.y * 1.5, 0.03 - d_axis.y * 1.5, axis_dist.y);
	float axis_z = smoothstep(0.03 + d_axis.x * 1.5, 0.03 - d_axis.x * 1.5, axis_dist.x);
	
	vec4 col = background_color;
	col = mix(col, minor_line_color, minor * 0.7);
	col = mix(col, major_line_color, major);
	col = mix(col, axis_x_color, axis_x * 0.8);
	col = mix(col, axis_z_color, axis_z * 0.8);
	
	col = mix(background_color, col, fade);
	
	ALBEDO = col.rgb;
	ROUGHNESS = 0.92;
	METALLIC = 0.05;
	SPECULAR = 0.15;
}
