class_name FlyMeshGenerator
extends RefCounted

## Procedural Anatomical Drosophila 3D Mesh Generator
## Generates realistic, biologically proportioned Drosophila melanogaster anatomy
## using SurfaceTool with custom biological shaders.

const WING_SHADER_PATH = "res://shaders/wing_iridescence.gdshader"
const EYE_SHADER_PATH = "res://shaders/compound_eye.gdshader"
const CUTICLE_SHADER_PATH = "res://shaders/chitin_cuticle.gdshader"

static func generate_fly() -> Node3D:
	var root := Node3D.new()
	root.name = "FlyModel"
	
	# Load Shaders
	var wing_shader: Shader = load(WING_SHADER_PATH)
	var eye_shader: Shader = load(EYE_SHADER_PATH)
	var cuticle_shader: Shader = load(CUTICLE_SHADER_PATH)
	
	# 1. Thorax & Head Mesh
	var thorax_head_mesh := _create_ellipsoid(Vector3(0.24, 0.22, 0.30), 20, 16)
	var thorax_inst := MeshInstance3D.new()
	thorax_inst.name = "Thorax"
	thorax_inst.mesh = thorax_head_mesh
	var thorax_mat := ShaderMaterial.new()
	thorax_mat.shader = cuticle_shader
	thorax_mat.set_shader_parameter("amber_base", Color(0.72, 0.42, 0.16))
	thorax_mat.set_shader_parameter("charcoal_stripe", Color(0.22, 0.14, 0.08))
	thorax_mat.set_shader_parameter("stripe_frequency", 3.0)
	thorax_inst.material_override = thorax_mat
	root.add_child(thorax_inst)
	
	# Head
	var head_mesh := _create_ellipsoid(Vector3(0.18, 0.16, 0.15), 18, 14)
	var head_inst := MeshInstance3D.new()
	head_inst.name = "Head"
	head_inst.mesh = head_mesh
	head_inst.position = Vector3(0.0, 0.04, -0.34)
	head_inst.material_override = thorax_mat
	root.add_child(head_inst)
	
	# 2. Ruby Compound Eyes (Left & Right)
	var eye_mesh := _create_ellipsoid(Vector3(0.12, 0.14, 0.12), 16, 14)
	var eye_mat := ShaderMaterial.new()
	eye_mat.shader = eye_shader
	eye_mat.set_shader_parameter("eye_ruby_core", Color(0.82, 0.03, 0.06))
	eye_mat.set_shader_parameter("eye_ruby_glow", Color(1.0, 0.28, 0.18))
	eye_mat.set_shader_parameter("hex_scale", 70.0)
	
	var left_eye := MeshInstance3D.new()
	left_eye.name = "LeftEye"
	left_eye.mesh = eye_mesh
	left_eye.position = Vector3(-0.13, 0.07, -0.36)
	left_eye.rotation_degrees = Vector3(-10, -25, -15)
	left_eye.material_override = eye_mat
	root.add_child(left_eye)
	
	var right_eye := MeshInstance3D.new()
	right_eye.name = "RightEye"
	right_eye.mesh = eye_mesh
	right_eye.position = Vector3(0.13, 0.07, -0.36)
	right_eye.rotation_degrees = Vector3(-10, 25, 15)
	right_eye.material_override = eye_mat
	root.add_child(right_eye)
	
	# 3. Segmented Abdomen (5 visible tergites)
	var abdomen_mesh := _create_tapered_capsule(0.22, 0.12, 0.55, 20, 16)
	var abdomen_inst := MeshInstance3D.new()
	abdomen_inst.name = "Abdomen"
	abdomen_inst.mesh = abdomen_mesh
	abdomen_inst.position = Vector3(0.0, -0.04, 0.45)
	abdomen_inst.rotation_degrees = Vector3(8, 0, 0)
	var abdomen_mat := ShaderMaterial.new()
	abdomen_mat.shader = cuticle_shader
	abdomen_mat.set_shader_parameter("amber_base", Color(0.86, 0.56, 0.22))
	abdomen_mat.set_shader_parameter("charcoal_stripe", Color(0.14, 0.09, 0.05))
	abdomen_mat.set_shader_parameter("stripe_frequency", 8.0)
	abdomen_mat.set_shader_parameter("stripe_sharpness", 5.0)
	abdomen_inst.material_override = abdomen_mat
	root.add_child(abdomen_inst)
	
	# 4. Thin-film Wings (Left & Right with roots for animation)
	var left_wing_root := Node3D.new()
	left_wing_root.name = "LeftWingRoot"
	left_wing_root.position = Vector3(-0.14, 0.14, -0.06)
	root.add_child(left_wing_root)
	
	var right_wing_root := Node3D.new()
	right_wing_root.name = "RightWingRoot"
	right_wing_root.position = Vector3(0.14, 0.14, -0.06)
	root.add_child(right_wing_root)
	
	var left_wing_mesh := _create_wing_mesh(false)
	var right_wing_mesh := _create_wing_mesh(true)
	
	var left_wing_mat := ShaderMaterial.new()
	left_wing_mat.shader = wing_shader
	left_wing_mat.set_shader_parameter("is_left_wing", true)
	
	var right_wing_mat := ShaderMaterial.new()
	right_wing_mat.shader = wing_shader
	right_wing_mat.set_shader_parameter("is_left_wing", false)
	
	var left_wing_inst := MeshInstance3D.new()
	left_wing_inst.name = "LeftWing"
	left_wing_inst.mesh = left_wing_mesh
	left_wing_inst.material_override = left_wing_mat
	left_wing_root.add_child(left_wing_inst)
	
	var right_wing_inst := MeshInstance3D.new()
	right_wing_inst.name = "RightWing"
	right_wing_inst.mesh = right_wing_mesh
	right_wing_inst.material_override = right_wing_mat
	right_wing_root.add_child(right_wing_inst)
	
	# 5. Vibrating Halteres (Gyroscopic balance organs posterior to wings)
	var left_haltere_root := Node3D.new()
	left_haltere_root.name = "LeftHaltereRoot"
	left_haltere_root.position = Vector3(-0.16, 0.05, 0.18)
	root.add_child(left_haltere_root)
	
	var right_haltere_root := Node3D.new()
	right_haltere_root.name = "RightHaltereRoot"
	right_haltere_root.position = Vector3(0.16, 0.05, 0.18)
	root.add_child(right_haltere_root)
	
	var haltere_mesh := _create_haltere_mesh()
	var haltere_mat := StandardMaterial3D.new()
	haltere_mat.albedo_color = Color(0.92, 0.88, 0.75)
	haltere_mat.roughness = 0.2
	
	var left_haltere_inst := MeshInstance3D.new()
	left_haltere_inst.name = "LeftHaltere"
	left_haltere_inst.mesh = haltere_mesh
	left_haltere_inst.rotation_degrees = Vector3(0, -60, -30)
	left_haltere_inst.material_override = haltere_mat
	left_haltere_root.add_child(left_haltere_inst)
	
	var right_haltere_inst := MeshInstance3D.new()
	right_haltere_inst.name = "RightHaltere"
	right_haltere_inst.mesh = haltere_mesh
	right_haltere_inst.rotation_degrees = Vector3(0, 60, 30)
	right_haltere_inst.material_override = haltere_mat
	right_haltere_root.add_child(right_haltere_inst)
	
	# 6. Articulated Legs (6 thoracic appendages)
	var legs_mesh := _create_legs_mesh()
	var legs_inst := MeshInstance3D.new()
	legs_inst.name = "Legs"
	legs_inst.mesh = legs_mesh
	var legs_mat := StandardMaterial3D.new()
	legs_mat.albedo_color = Color(0.35, 0.22, 0.12)
	legs_mat.roughness = 0.5
	legs_inst.material_override = legs_mat
	root.add_child(legs_inst)
	
	# 7. Bilateral Sensory Antennae
	var antennae_mesh := _create_antennae_mesh()
	var antennae_inst := MeshInstance3D.new()
	antennae_inst.name = "Antennae"
	antennae_inst.mesh = antennae_mesh
	antennae_inst.position = Vector3(0, 0.06, -0.46)
	antennae_inst.material_override = legs_mat
	root.add_child(antennae_inst)
	
	return root

## Helper: Creates a smooth UV-mapped ellipsoid
static func _create_ellipsoid(radii: Vector3, segments: int, rings: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	for i in range(rings + 1):
		var v: float = float(i) / float(rings)
		var phi: float = v * PI
		
		for j in range(segments + 1):
			var u: float = float(j) / float(segments)
			var theta: float = u * TAU
			
			var x: float = radii.x * sin(phi) * cos(theta)
			var y: float = radii.y * cos(phi)
			var z: float = radii.z * sin(phi) * sin(theta)
			
			var normal := Vector3(x / radii.x, y / radii.y, z / radii.z).normalized()
			st.set_normal(normal)
			st.set_uv(Vector2(u, v))
			st.add_vertex(Vector3(x, y, z))
	
	for i in range(rings):
		for j in range(segments):
			var first: int = i * (segments + 1) + j
			var second: int = first + segments + 1
			
			st.add_index(first)
			st.add_index(second)
			st.add_index(first + 1)
			
			st.add_index(second)
			st.add_index(second + 1)
			st.add_index(first + 1)
	
	st.generate_tangents()
	return st.commit()

## Helper: Creates a tapered segmented abdomen capsule
static func _create_tapered_capsule(radius_start: float, radius_end: float, length: float, segments: int, rings: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	for i in range(rings + 1):
		var v: float = float(i) / float(rings)
		var z: float = (v - 0.5) * length
		var current_radius: float = lerp(radius_start, radius_end, v) * sin(v * PI)
		
		for j in range(segments + 1):
			var u: float = float(j) / float(segments)
			var theta: float = u * TAU
			
			var x: float = current_radius * cos(theta)
			var y: float = current_radius * sin(theta) * 0.85 # slightly dorsoventrally flattened
			
			var normal := Vector3(x, y, 0.2).normalized()
			st.set_normal(normal)
			st.set_uv(Vector2(u, v))
			st.add_vertex(Vector3(x, y, z))
	
	for i in range(rings):
		for j in range(segments):
			var first: int = i * (segments + 1) + j
			var second: int = first + segments + 1
			
			st.add_index(first)
			st.add_index(second)
			st.add_index(first + 1)
			
			st.add_index(second)
			st.add_index(second + 1)
			st.add_index(first + 1)
	
	st.generate_tangents()
	return st.commit()

## Helper: Creates an aerodynamic, curved thin-film wing blade
static func _create_wing_mesh(is_right: bool) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var span_steps := 12
	var chord_steps := 8
	var wing_span: float = 0.95
	var max_chord: float = 0.42
	var sign_x: float = 1.0 if is_right else -1.0
	
	for i in range(span_steps + 1):
		var u: float = float(i) / float(span_steps) # 0.0 at root, 1.0 at wing tip
		var span_pos: float = u * wing_span * sign_x
		
		# Wing chord width contour (slender at root, broad at mid-wing, rounded at tip)
		var chord: float = max_chord * sin(u * PI * 0.9 + 0.1) * (1.0 - u * 0.25)
		
		for j in range(chord_steps + 1):
			var v: float = float(j) / float(chord_steps) # 0.0 at leading edge (Costa), 1.0 at trailing edge
			var chord_pos: float = (v - 0.25) * chord
			
			# Camber curvature (slight convex camber along chord)
			var camber: float = 0.02 * sin(v * PI)
			
			var vertex := Vector3(span_pos, camber, chord_pos)
			var normal := Vector3(0.0, 1.0, 0.0)
			
			st.set_normal(normal)
			st.set_uv(Vector2(u, v))
			st.add_vertex(vertex)
	
	for i in range(span_steps):
		for j in range(chord_steps):
			var first: int = i * (chord_steps + 1) + j
			var second: int = first + chord_steps + 1
			
			if is_right:
				st.add_index(first)
				st.add_index(second)
				st.add_index(first + 1)
				
				st.add_index(second)
				st.add_index(second + 1)
				st.add_index(first + 1)
			else:
				st.add_index(first)
				st.add_index(first + 1)
				st.add_index(second)
				
				st.add_index(second)
				st.add_index(first + 1)
				st.add_index(second + 1)
	
	st.generate_tangents()
	return st.commit()

## Helper: Creates a club-shaped haltere (stalk + bulb)
static func _create_haltere_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var length: float = 0.14
	var stalk_radius: float = 0.012
	var bulb_radius: float = 0.035
	var segments := 8
	var rings := 6
	
	for i in range(rings + 1):
		var v: float = float(i) / float(rings)
		var y: float = v * length
		var r: float = stalk_radius if v < 0.7 else lerp(stalk_radius, bulb_radius, (v - 0.7) / 0.3)
		
		for j in range(segments + 1):
			var u: float = float(j) / float(segments)
			var theta: float = u * TAU
			var x: float = r * cos(theta)
			var z: float = r * sin(theta)
			
			st.set_normal(Vector3(cos(theta), 0, sin(theta)))
			st.set_uv(Vector2(u, v))
			st.add_vertex(Vector3(x, y, z))
	
	for i in range(rings):
		for j in range(segments):
			var first: int = i * (segments + 1) + j
			var second: int = first + segments + 1
			st.add_index(first)
			st.add_index(second)
			st.add_index(first + 1)
			st.add_index(second)
			st.add_index(second + 1)
			st.add_index(first + 1)
			
	st.generate_tangents()
	return st.commit()

## Helper: Creates 6 articulated insect legs with coxa/femur/tibia bends
static func _create_legs_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Leg attachment roots on ventral thorax
	var leg_roots := [
		# Left legs (Front, Mid, Hind)
		Vector3(-0.12, -0.12, -0.16),
		Vector3(-0.15, -0.14, 0.0),
		Vector3(-0.12, -0.12, 0.16),
		# Right legs (Front, Mid, Hind)
		Vector3(0.12, -0.12, -0.16),
		Vector3(0.15, -0.14, 0.0),
		Vector3(0.12, -0.12, 0.16),
	]
	
	var leg_targets := [
		Vector3(-0.28, -0.32, -0.30),
		Vector3(-0.35, -0.34, 0.02),
		Vector3(-0.30, -0.32, 0.32),
		Vector3(0.28, -0.32, -0.30),
		Vector3(0.35, -0.34, 0.02),
		Vector3(0.30, -0.32, 0.32),
	]
	
	for k in range(leg_roots.size()):
		var p0: Vector3 = leg_roots[k]
		var p2: Vector3 = leg_targets[k]
		# Knee joint p1
		var p1: Vector3 = (p0 + p2) * 0.5 + Vector3(0.08 * sign(p0.x), 0.10, 0.0)
		_append_cylinder_segment(st, p0, p1, 0.020, 0.015, 6)
		_append_cylinder_segment(st, p1, p2, 0.015, 0.008, 6)
		
	st.generate_tangents()
	return st.commit()

## Helper: Creates bilateral antennae with sensory aristae
static func _create_antennae_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Left antenna
	_append_cylinder_segment(st, Vector3(-0.04, 0.0, 0.0), Vector3(-0.09, 0.05, -0.10), 0.012, 0.006, 5)
	# Right antenna
	_append_cylinder_segment(st, Vector3(0.04, 0.0, 0.0), Vector3(0.09, 0.05, -0.10), 0.012, 0.006, 5)
	
	st.generate_tangents()
	return st.commit()

## Helper: Appends a tapered cylinder segment between two points
static func _append_cylinder_segment(st: SurfaceTool, start_pt: Vector3, end_pt: Vector3, r0: float, r1: float, sides: int) -> void:
	var dir := (end_pt - start_pt).normalized()
	var up := Vector3.UP if abs(dir.y) < 0.9 else Vector3.RIGHT
	var side := dir.cross(up).normalized()
	up = side.cross(dir).normalized()
	
	var base_idx: int = 0
	# We use SurfaceTool without manually tracking indices if we build quads
	for i in range(sides):
		var a0: float = float(i) / float(sides) * TAU
		var a1: float = float(i + 1) / float(sides) * TAU
		
		var v0_start := start_pt + (side * cos(a0) + up * sin(a0)) * r0
		var v1_start := start_pt + (side * cos(a1) + up * sin(a1)) * r0
		var v0_end := end_pt + (side * cos(a0) + up * sin(a0)) * r1
		var v1_end := end_pt + (side * cos(a1) + up * sin(a1)) * r1
		
		var n0 := (side * cos(a0) + up * sin(a0)).normalized()
		var n1 := (side * cos(a1) + up * sin(a1)).normalized()
		
		# Triangle 1
		st.set_normal(n0)
		st.set_uv(Vector2(0, 0))
		st.add_vertex(v0_start)
		
		st.set_normal(n0)
		st.set_uv(Vector2(1, 0))
		st.add_vertex(v0_end)
		
		st.set_normal(n1)
		st.set_uv(Vector2(1, 1))
		st.add_vertex(v1_end)
		
		# Triangle 2
		st.set_normal(n0)
		st.set_uv(Vector2(0, 0))
		st.add_vertex(v0_start)
		
		st.set_normal(n1)
		st.set_uv(Vector2(1, 1))
		st.add_vertex(v1_end)
		
		st.set_normal(n1)
		st.set_uv(Vector2(0, 1))
		st.add_vertex(v1_start)
