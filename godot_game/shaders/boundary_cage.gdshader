shader_type spatial;
render_mode blend_add, depth_draw_opaque, cull_disabled, unshaded;

// Boundary Cage / Grid Volume Shader
// Renders subtle luminous boundary lines for the 3D flight volume

uniform vec4 line_color : source_color = vec4(0.20, 0.22, 0.26, 0.45);
uniform float grid_spacing : float = 5.0;
uniform float line_width : float = 0.04;
uniform float proximity_fade : float = 30.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// Anti-aliased 3D plane lines
	vec2 uv_grid = abs(fract(world_pos.xy / grid_spacing - 0.5) - 0.5);
	vec2 d = fwidth(world_pos.xy / grid_spacing);
	vec2 aagrid = smoothstep(line_width + d * 1.5, line_width - d * 1.5, uv_grid);
	float edge = max(aagrid.x, aagrid.y);
	
	float cam_dist = length(CAMERA_POSITION_WORLD - world_pos);
	float alpha = clamp(1.0 - cam_dist / proximity_fade, 0.0, 1.0) * line_color.a * edge;
	
	ALBEDO = line_color.rgb;
	ALPHA = alpha;
}
