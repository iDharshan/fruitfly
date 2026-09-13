class_name FlyMeshGenerator
extends RefCounted

## Procedural Anatomical Drosophila 3D Mesh Generator
## Generates authentic, biologically proportioned Drosophila melanogaster anatomy
## using SurfaceTool with custom biological shaders.
##
## Anatomical features:
## - Slender golden mesothorax with dark dorsal vittae and posterior scutellum
## - Cephalic capsule with ruby compound eyes (hex ommatidia & dynamic pseudopupil)
## - Feathery sensory aristae (branched antenna rays) and ventral proboscis
## - Authentic cephalic and thoracic macrochaetae (curved chitin bristles)
## - 6-segmented abdominal spindle with male apical melanization
## - Articulated legs tucked in natural streamlined flight posture
## - Thin-film iridescent wings with Dipteran venation and WIP interference

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
	
	# Materials
	var thorax_mat := ShaderMaterial.new()
	thorax_mat.shader = cuticle_shader
	thorax_mat.set_shader_parameter("amber_base", Color(0.68, 0.49, 0.28))
	thorax_mat.set_shader_parameter("charcoal_stripe", Color(0.12, 0.08, 0.05))
	thorax_mat.set_shader_parameter("is_thorax", true)
	thorax_mat.set_shader_parameter("is_abdomen", false)
	
	var head_mat := ShaderMaterial.new()
	head_mat.shader = cuticle_shader
	head_mat.set_shader_parameter("amber_base", Color(0.65, 0.46, 0.26))
	head_mat.set_shader_parameter("charcoal_stripe", Color(0.14, 0.09, 0.06))
	head_mat.set_shader_parameter("is_thorax", false)
	head_mat.set_shader_parameter("is_abdomen", false)
	
	var abdomen_mat := ShaderMaterial.new()
	abdomen_mat.shader = cuticle_shader
	abdomen_mat.set_shader_parameter("amber_base", Color(0.70, 0.52, 0.30))
	abdomen_mat.set_shader_parameter("charcoal_stripe", Color(0.10, 0.07, 0.04))
	abdomen_mat.set_shader_parameter("pleural_pale", Color(0.84, 0.72, 0.52))
	abdomen_mat.set_shader_parameter("is_thorax", false)
	abdomen_mat.set_shader_parameter("is_abdomen", true)
	abdomen_mat.set_shader_parameter("stripe_frequency", 6.0)
	abdomen_mat.set_shader_parameter("stripe_sharpness", 2.8)
	
	var bristle_mat := StandardMaterial3D.new()
	bristle_mat.albedo_color = Color(0.08, 0.05, 0.03)
	bristle_mat.roughness = 0.35
	bristle_mat.specular_mode = StandardMaterial3D.SPECULAR_SCHLICK_GGX
	
	# -------------------------------------------------------------
	# 1. Thorax (Aerodynamic mesothorax + posterior scutellum)
	# -------------------------------------------------------------
	var thorax_mesh := _create_ellipsoid(Vector3(0.056, 0.054, 0.082), 24, 18)
	var thorax_inst := MeshInstance3D.new()
	thorax_inst.name = "Thorax"
	thorax_inst.mesh = thorax_mesh
	thorax_inst.material_override = thorax_mat
	root.add_child(thorax_inst)
	
	# Scutellum (shield-shaped posterior prominence)
	var scutellum_mesh := _create_ellipsoid(Vector3(0.032, 0.024, 0.030), 16, 12)
	var scutellum_inst := MeshInstance3D.new()
	scutellum_inst.name = "Scutellum"
	scutellum_inst.mesh = scutellum_mesh
	scutellum_inst.position = Vector3(0.0, 0.036, 0.065)
	scutellum_inst.rotation_degrees = Vector3(-18, 0, 0)
	scutellum_inst.material_override = thorax_mat
	root.add_child(scutellum_inst)
	
	# -------------------------------------------------------------
	# 2. Cephalic Capsule (Head, Proboscis, Antennae, Aristae)
	# -------------------------------------------------------------
	var head_mesh := _create_ellipsoid(Vector3(0.044, 0.040, 0.036), 20, 16)
	var head_inst := MeshInstance3D.new()
	head_inst.name = "Head"
	head_inst.mesh = head_mesh
	head_inst.position = Vector3(0.0, 0.010, -0.096)
	head_inst.material_override = head_mat
	root.add_child(head_inst)
	
	# Proboscis / Mouthparts (Ventral rostrum and bilobed labellum)
	var proboscis_mesh := _create_proboscis_mesh()
	var proboscis_inst := MeshInstance3D.new()
	proboscis_inst.name = "Proboscis"
	proboscis_inst.mesh = proboscis_mesh
	proboscis_inst.position = Vector3(0.0, -0.024, -0.098)
	proboscis_inst.material_override = head_mat
	root.add_child(proboscis_inst)
	
	# Bilateral Ruby Compound Eyes (Hexagonal ommatidia & pseudopupil)
	var eye_mesh := _create_ellipsoid(Vector3(0.032, 0.036, 0.030), 20, 16)
	var eye_mat := ShaderMaterial.new()
	eye_mat.shader = eye_shader
	eye_mat.set_shader_parameter("eye_ruby_core", Color(0.72, 0.02, 0.05))
	eye_mat.set_shader_parameter("eye_ruby_glow", Color(1.0, 0.28, 0.14))
	eye_mat.set_shader_parameter("pseudopupil_color", Color(0.08, 0.01, 0.02))
	eye_mat.set_shader_parameter("hex_scale", 95.0)
	eye_mat.set_shader_parameter("pseudopupil_size", 0.55)
	
	var left_eye := MeshInstance3D.new()
	left_eye.name = "LeftEye"
	left_eye.mesh = eye_mesh
	left_eye.position = Vector3(-0.034, 0.018, -0.106)
	left_eye.rotation_degrees = Vector3(-10, -25, -15)
	left_eye.material_override = eye_mat
	root.add_child(left_eye)
	
	var right_eye := MeshInstance3D.new()
	right_eye.name = "RightEye"
	right_eye.mesh = eye_mesh
	right_eye.position = Vector3(0.034, 0.018, -0.106)
	right_eye.rotation_degrees = Vector3(-10, 25, 15)
	right_eye.material_override = eye_mat
	root.add_child(right_eye)
	
	# Antennae & Feathery Aristae (Iconic Drosophila sensory apparatus)
	var antennae_mesh := _create_antennae_and_aristae_mesh()
	var antennae_inst := MeshInstance3D.new()
	antennae_inst.name = "Antennae"
	antennae_inst.mesh = antennae_mesh
	antennae_inst.position = Vector3(0.0, 0.016, -0.130)
	antennae_inst.material_override = bristle_mat
	root.add_child(antennae_inst)
	
	# Cephalic & Thoracic Macrochaetae (Dark curved chitin bristles)
	var bristles_mesh := _create_bristles_mesh()
	var bristles_inst := MeshInstance3D.new()
	bristles_inst.name = "Macrochaetae"
	bristles_inst.mesh = bristles_mesh
	bristles_inst.material_override = bristle_mat
	root.add_child(bristles_inst)
	
	# -------------------------------------------------------------
	# 3. Segmented Abdomen (6 Tergites with melanic stripes & male tip)
	# -------------------------------------------------------------
	var abdomen_mesh := _create_segmented_abdomen(0.046, 0.016, 0.28, 24, 20)
	var abdomen_inst := MeshInstance3D.new()
	abdomen_inst.name = "Abdomen"
	abdomen_inst.mesh = abdomen_mesh
	abdomen_inst.position = Vector3(0.0, -0.014, 0.135)
	abdomen_inst.rotation_degrees = Vector3(7, 0, 0)
	abdomen_inst.material_override = abdomen_mat
	root.add_child(abdomen_inst)
	
	# -------------------------------------------------------------
	# 4. Thin-film Wings with Drosophila Venation & WIPs
	# -------------------------------------------------------------
	var left_wing_root := Node3D.new()
	left_wing_root.name = "LeftWingRoot"
	left_wing_root.position = Vector3(-0.038, 0.038, -0.018)
	root.add_child(left_wing_root)
	
	var right_wing_root := Node3D.new()
	right_wing_root.name = "RightWingRoot"
	right_wing_root.position = Vector3(0.038, 0.038, -0.018)
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
	
	# -------------------------------------------------------------
	# 5. Vibrating Halteres (Gyroscopic balance organs)
	# -------------------------------------------------------------
	var left_haltere_root := Node3D.new()
	left_haltere_root.name = "LeftHaltereRoot"
	left_haltere_root.position = Vector3(-0.045, 0.015, 0.055)
	root.add_child(left_haltere_root)
	
	var right_haltere_root := Node3D.new()
	right_haltere_root.name = "RightHaltereRoot"
	right_haltere_root.position = Vector3(0.045, 0.015, 0.055)
	root.add_child(right_haltere_root)
	
	var haltere_mesh := _create_haltere_mesh()
	var haltere_mat := StandardMaterial3D.new()
	haltere_mat.albedo_color = Color(0.92, 0.89, 0.78)
	haltere_mat.roughness = 0.25
	haltere_mat.rim_enabled = true
	haltere_mat.rim = 0.5
	
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
	
	# -------------------------------------------------------------
	# 6. Articulated Flight Legs (Streamlined flight posture)
	# -------------------------------------------------------------
	var legs_mesh := _create_articulated_flight_legs()
	var legs_inst := MeshInstance3D.new()
	legs_inst.name = "Legs"
	legs_inst.mesh = legs_mesh
	legs_inst.material_override = bristle_mat
	root.add_child(legs_inst)
	
	return root

# =================================================================
# GEOMETRY GENERATION HELPERS
# =================================================================

## Helper: Creates a smooth UV-mapped ellipsoid with proper tangents
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

## Helper: Creates a segmented tapered abdomen with realistic lateral curvature
static func _create_segmented_abdomen(radius_start: float, radius_end: float, length: float, segments: int, rings: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	for i in range(rings + 1):
		var v: float = float(i) / float(rings)
		var z: float = (v - 0.5) * length
		
		# Spindle profile: wider in segments 2-4, tapering smoothly to posterior apex
		var profile: float = sin(v * PI * 0.88 + 0.12)
		var current_radius: float = lerp(radius_start, radius_end, v) * profile
		
		# Segmental grooves (6 visible tergites)
		var seg_wave: float = 1.0 - 0.06 * pow(sin(v * PI * 6.0), 2.0)
		current_radius *= seg_wave
		
		for j in range(segments + 1):
			var u: float = float(j) / float(segments)
			var theta: float = u * TAU
			
			var x: float = current_radius * cos(theta)
			var y: float = current_radius * sin(theta) * 0.78 # Dorsoventrally flattened
			
			var normal := Vector3(x, y * 1.25, 0.18).normalized()
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
	
	var span_steps := 16
	var chord_steps := 10
	var wing_span: float = 0.34
	var max_chord: float = 0.125
	var sign_x: float = 1.0 if is_right else -1.0
	
	for i in range(span_steps + 1):
		var u: float = float(i) / float(span_steps)
		var span_pos: float = u * wing_span * sign_x
		
		# Drosophila elliptical wing contour
		var chord: float = max_chord * sin(u * PI * 0.85 + 0.15) * (1.0 - u * 0.20)
		
		for j in range(chord_steps + 1):
			var v: float = float(j) / float(chord_steps)
			var chord_pos: float = (v - 0.28) * chord
			
			# Aerodynamic camber profile
			var camber: float = 0.007 * sin(v * PI) * (1.0 - u * 0.3)
			
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

## Helper: Creates a club-shaped haltere (gyroscopic balance organ)
static func _create_haltere_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	var length: float = 0.048
	var stalk_radius: float = 0.0035
	var bulb_radius: float = 0.011
	var segments := 10
	var rings := 8
	
	for i in range(rings + 1):
		var v: float = float(i) / float(rings)
		var y: float = v * length
		var r: float = stalk_radius if v < 0.68 else lerp(stalk_radius, bulb_radius, sin((v - 0.68) / 0.32 * PI * 0.5))
		
		for j in range(segments + 1):
			var u: float = float(j) / float(segments)
			var theta: float = u * TAU
			var x: float = r * cos(theta)
			var z: float = r * sin(theta)
			
			st.set_normal(Vector3(cos(theta), 0.2, sin(theta)).normalized())
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

## Helper: Creates folded ventral mouthparts (rostrum & labellum)
static func _create_proboscis_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Rostrum (basal cone)
	_append_cylinder_segment(st, Vector3(0, 0, 0), Vector3(0, -0.016, 0.008), 0.014, 0.010, 8)
	# Haustellum (middle shaft)
	_append_cylinder_segment(st, Vector3(0, -0.016, 0.008), Vector3(0, -0.026, 0.018), 0.010, 0.008, 8)
	# Bilobed labellum (fleshy oral disc)
	_append_cylinder_segment(st, Vector3(-0.007, -0.026, 0.018), Vector3(-0.009, -0.032, 0.022), 0.006, 0.004, 6)
	_append_cylinder_segment(st, Vector3(0.007, -0.026, 0.018), Vector3(0.009, -0.032, 0.022), 0.006, 0.004, 6)
	
	st.generate_tangents()
	return st.commit()

## Helper: Creates antennae and feathered aristae (hallmark of Drosophila)
static func _create_antennae_and_aristae_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	for side in [-1.0, 1.0]:
		var base := Vector3(side * 0.014, 0.0, 0.0)
		var funiculus := base + Vector3(side * 0.012, 0.006, -0.020)
		
		# Antennal segments 1-3 (scape, pedicel, bulbous funiculus)
		_append_cylinder_segment(st, base, funiculus, 0.005, 0.006, 6)
		
		# Arista main stem (slender shaft curving antero-laterally)
		var arista_mid := funiculus + Vector3(side * 0.022, 0.018, -0.024)
		var arista_tip := funiculus + Vector3(side * 0.038, 0.026, -0.042)
		_append_cylinder_segment(st, funiculus, arista_mid, 0.0025, 0.0016, 5)
		_append_cylinder_segment(st, arista_mid, arista_tip, 0.0016, 0.0008, 5)
		
		# 5 dorsal arista feather branches
		for k in range(5):
			var frac: float = float(k + 1) / 6.0
			var branch_root: Vector3 = funiculus.lerp(arista_tip, frac)
			var branch_tip: Vector3 = branch_root + Vector3(side * 0.006, 0.012 + frac * 0.004, -0.006)
			_append_cylinder_segment(st, branch_root, branch_tip, 0.0012, 0.0005, 4)
			
		# 3 ventral arista branches
		for k in range(3):
			var frac: float = float(k + 2) / 6.0
			var branch_root: Vector3 = funiculus.lerp(arista_tip, frac)
			var branch_tip: Vector3 = branch_root + Vector3(side * 0.005, -0.008, -0.004)
			_append_cylinder_segment(st, branch_root, branch_tip, 0.0012, 0.0005, 4)
			
		# Terminal bifurcation
		_append_cylinder_segment(st, arista_tip, arista_tip + Vector3(side * 0.006, 0.004, -0.006), 0.0008, 0.0003, 3)
		_append_cylinder_segment(st, arista_tip, arista_tip + Vector3(side * 0.004, -0.003, -0.006), 0.0008, 0.0003, 3)
	
	st.generate_tangents()
	return st.commit()

## Helper: Creates cephalic and thoracic macrochaetae (large curved chitin bristles)
static func _create_bristles_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Bristle definitions: [start_pt, dir, length, base_radius]
	var bristles := [
		# 4 Scutellar bristles (anterior and posterior pairs projecting backward from scutellum)
		[Vector3(-0.018, 0.046, 0.075), Vector3(-0.15, 0.40, 0.90).normalized(), 0.042, 0.0024],
		[Vector3(0.018, 0.046, 0.075), Vector3(0.15, 0.40, 0.90).normalized(), 0.042, 0.0024],
		[Vector3(-0.008, 0.042, 0.092), Vector3(-0.08, 0.30, 0.95).normalized(), 0.048, 0.0026],
		[Vector3(0.008, 0.042, 0.092), Vector3(0.08, 0.30, 0.95).normalized(), 0.048, 0.0026],
		
		# 4 Dorsocentral bristles on scutum
		[Vector3(-0.030, 0.052, 0.010), Vector3(-0.25, 0.85, 0.45).normalized(), 0.038, 0.0022],
		[Vector3(0.030, 0.052, 0.010), Vector3(0.25, 0.85, 0.45).normalized(), 0.038, 0.0022],
		[Vector3(-0.032, 0.050, 0.042), Vector3(-0.25, 0.80, 0.55).normalized(), 0.040, 0.0022],
		[Vector3(0.032, 0.050, 0.042), Vector3(0.25, 0.80, 0.55).normalized(), 0.040, 0.0022],
		
		# Cephalic: Ocellar bristles (top of head between eyes)
		[Vector3(-0.006, 0.048, -0.092), Vector3(-0.20, 0.90, -0.35).normalized(), 0.032, 0.0020],
		[Vector3(0.006, 0.048, -0.092), Vector3(0.20, 0.90, -0.35).normalized(), 0.032, 0.0020],
		
		# Cephalic: Vertical bristles (posterior margin of head)
		[Vector3(-0.024, 0.046, -0.082), Vector3(-0.40, 0.85, 0.35).normalized(), 0.036, 0.0022],
		[Vector3(0.024, 0.046, -0.082), Vector3(0.40, 0.85, 0.35).normalized(), 0.036, 0.0022],
	]
	
	for b in bristles:
		var p0: Vector3 = b[0]
		var dir: Vector3 = b[1]
		var blen: float = b[2]
		var r: float = b[3]
		var p_mid := p0 + dir * (blen * 0.55) + Vector3(0, 0.003, 0)
		var p_end := p0 + dir * blen
		_append_cylinder_segment(st, p0, p_mid, r, r * 0.55, 5)
		_append_cylinder_segment(st, p_mid, p_end, r * 0.55, 0.0004, 5)
	
	st.generate_tangents()
	return st.commit()

## Helper: Creates 6 articulated insect legs in authentic streamlined flight posture
static func _create_articulated_flight_legs() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	
	# Leg joints: [Coxa-root, Femur-knee, Tibia-joint, Tarsus-tip]
	# Flight posture:
	# - Front legs: flexed forward-ventrally under head
	# - Middle legs: tucked tightly against sides of thorax
	# - Rear legs: extended backward beneath abdomen
	var legs := [
		# 1. Front Left (Prothoracic)
		[Vector3(-0.026, -0.032, -0.042), Vector3(-0.048, -0.058, -0.075), Vector3(-0.036, -0.072, -0.052), Vector3(-0.022, -0.085, -0.032)],
		# 2. Front Right (Prothoracic)
		[Vector3(0.026, -0.032, -0.042), Vector3(0.048, -0.058, -0.075), Vector3(0.036, -0.072, -0.052), Vector3(0.022, -0.085, -0.032)],
		
		# 3. Middle Left (Mesothoracic)
		[Vector3(-0.032, -0.036, 0.005), Vector3(-0.058, -0.062, -0.008), Vector3(-0.050, -0.078, 0.032), Vector3(-0.038, -0.092, 0.068)],
		# 4. Middle Right (Mesothoracic)
		[Vector3(0.032, -0.036, 0.005), Vector3(0.058, -0.062, -0.008), Vector3(0.050, -0.078, 0.032), Vector3(0.038, -0.092, 0.068)],
		
		# 5. Rear Left (Metathoracic - extended backward along abdomen)
		[Vector3(-0.028, -0.032, 0.048), Vector3(-0.048, -0.052, 0.085), Vector3(-0.038, -0.065, 0.155), Vector3(-0.026, -0.072, 0.225)],
		# 6. Rear Right (Metathoracic - extended backward along abdomen)
		[Vector3(0.028, -0.032, 0.048), Vector3(0.048, -0.052, 0.085), Vector3(0.038, -0.065, 0.155), Vector3(0.026, -0.072, 0.225)],
	]
	
	for leg in legs:
		var p0: Vector3 = leg[0] # Coxa
		var p1: Vector3 = leg[1] # Femur
		var p2: Vector3 = leg[2] # Tibia
		var p3: Vector3 = leg[3] # Tarsus
		
		# Coxa-Femur segment (muscular upper leg)
		_append_cylinder_segment(st, p0, p1, 0.0055, 0.0042, 6)
		# Femur-Tibia segment (slender lower leg)
		_append_cylinder_segment(st, p1, p2, 0.0042, 0.0028, 6)
		# Tibia-Tarsus segment (flexible foot)
		_append_cylinder_segment(st, p2, p3, 0.0028, 0.0016, 5)
		# Tarsal claws (tiny hook at tip)
		var claw_tip := p3 + (p3 - p2).normalized() * 0.008 + Vector3(0, -0.003, 0)
		_append_cylinder_segment(st, p3, claw_tip, 0.0016, 0.0006, 4)
		
	st.generate_tangents()
	return st.commit()

## Helper: Appends a tapered cylinder segment with smoothed normal mapping
static func _append_cylinder_segment(st: SurfaceTool, start_pt: Vector3, end_pt: Vector3, r0: float, r1: float, sides: int) -> void:
	var dir := (end_pt - start_pt).normalized()
	if dir.length_squared() < 0.0001:
		return
	var up := Vector3.UP if abs(dir.y) < 0.9 else Vector3.RIGHT
	var side := dir.cross(up).normalized()
	up = side.cross(dir).normalized()
	
	for i in range(sides):
		var a0: float = float(i) / float(sides) * TAU
		var a1: float = float(i + 1) / float(sides) * TAU
		
		var v0_start := start_pt + (side * cos(a0) + up * sin(a0)) * r0
		var v1_start := start_pt + (side * cos(a1) + up * sin(a1)) * r0
		var v0_end := end_pt + (side * cos(a0) + up * sin(a0)) * r1
		var v1_end := end_pt + (side * cos(a1) + up * sin(a1)) * r1
		
		var n0 := (side * cos(a0) + up * sin(a0)).normalized()
		var n1 := (side * cos(a1) + up * sin(a1)).normalized()
		
		st.set_normal(n0)
		st.set_uv(Vector2(0, 0))
		st.add_vertex(v0_start)
		
		st.set_normal(n0)
		st.set_uv(Vector2(1, 0))
		st.add_vertex(v0_end)
		
		st.set_normal(n1)
		st.set_uv(Vector2(1, 1))
		st.add_vertex(v1_end)
		
		st.set_normal(n0)
		st.set_uv(Vector2(0, 0))
		st.add_vertex(v0_start)
		
		st.set_normal(n1)
		st.set_uv(Vector2(1, 1))
		st.add_vertex(v1_end)
		
		st.set_normal(n1)
		st.set_uv(Vector2(0, 1))
		st.add_vertex(v1_start)
