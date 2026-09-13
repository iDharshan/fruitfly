class_name FoodPiece
extends Area3D

## Decaying Fruit Food Source (Macro Tabletop Centerpiece)
## Features translucent peach/banana pulp flesh, glistening sugar syrup droplets,
## fuzzy fungal mold spores (Botrytis/Penicillium), and bioluminescent consumption halos.

signal food_consumed(pos: Vector3)

@export var arena_bounds: Rect2 = Rect2(-1.5, -1.5, 3.0, 3.0)

var _flesh_mesh: MeshInstance3D
var _rind_mesh: MeshInstance3D
var _halo_light: OmniLight3D
var _mold_node: Node3D
var _droplets_node: Node3D
var _consume_particles: GPUParticles3D
var _pulse_time: float = 0.0

func _ready() -> void:
	collision_layer = 4
	collision_mask = 2 # Detect FlyAgent (layer 2)
	
	_build_fruit_visuals()
	_setup_consumption_fx()
	body_entered.connect(_on_body_entered)

func _build_fruit_visuals() -> void:
	# 1. Outer Rind (Peach skin / banana peel)
	var rind_mesh := CylinderMesh.new()
	rind_mesh.top_radius = 0.25
	rind_mesh.bottom_radius = 0.27
	rind_mesh.height = 0.14
	rind_mesh.radial_segments = 20
	
	_rind_mesh = MeshInstance3D.new()
	_rind_mesh.name = "FruitRind"
	_rind_mesh.mesh = rind_mesh
	var rind_mat := StandardMaterial3D.new()
	rind_mat.albedo_color = Color(0.85, 0.45, 0.18) # Peach skin orange-red
	rind_mat.roughness = 0.42
	_rind_mesh.material_override = rind_mat
	add_child(_rind_mesh)
	
	# 2. Decaying Fruit Pulp Flesh (Translucent Amber Core)
	var flesh_mesh := CylinderMesh.new()
	flesh_mesh.top_radius = 0.22
	flesh_mesh.bottom_radius = 0.24
	flesh_mesh.height = 0.15
	flesh_mesh.radial_segments = 20
	
	_flesh_mesh = MeshInstance3D.new()
	_flesh_mesh.name = "FruitFlesh"
	_flesh_mesh.mesh = flesh_mesh
	_flesh_mesh.position = Vector3(0, 0.01, 0)
	
	var flesh_mat := StandardMaterial3D.new()
	flesh_mat.albedo_color = Color(0.98, 0.68, 0.25, 0.94)
	flesh_mat.roughness = 0.18
	flesh_mat.emission_enabled = true
	flesh_mat.emission = Color(0.90, 0.48, 0.15)
	flesh_mat.emission_energy_multiplier = 0.65
	flesh_mat.clearcoat_enabled = true
	flesh_mat.clearcoat = 1.0
	flesh_mat.clearcoat_roughness = 0.08
	flesh_mat.rim_enabled = true
	flesh_mat.rim = 0.7
	flesh_mat.rim_tint = 0.8
	_flesh_mesh.material_override = flesh_mat
	add_child(_flesh_mesh)
	
	# 3. Glistening Syrupy Sugar Droplets along the rim
	_droplets_node = Node3D.new()
	_droplets_node.name = "SyrupDroplets"
	add_child(_droplets_node)
	
	var drop_mat := StandardMaterial3D.new()
	drop_mat.albedo_color = Color(0.98, 0.82, 0.45, 0.85)
	drop_mat.roughness = 0.04
	drop_mat.metallic = 0.05
	drop_mat.clearcoat_enabled = true
	drop_mat.clearcoat = 1.0
	drop_mat.clearcoat_roughness = 0.02
	
	for i in range(8):
		var angle: float = float(i) * TAU / 8.0 + randf_range(-0.15, 0.15)
		var rad: float = randf_range(0.16, 0.23)
		var drop := MeshInstance3D.new()
		var sm := SphereMesh.new()
		var r: float = randf_range(0.025, 0.045)
		sm.radius = r
		sm.height = r * 1.5
		drop.mesh = sm
		drop.position = Vector3(rad * cos(angle), 0.075, rad * sin(angle))
		drop.material_override = drop_mat
		_droplets_node.add_child(drop)
		
	# 4. Fungal Mold Spores (Microscopic Penicillium / Botrytis fluffy patches)
	_mold_node = Node3D.new()
	_mold_node.name = "FungalMold"
	add_child(_mold_node)
	
	var mold_mat := StandardMaterial3D.new()
	mold_mat.albedo_color = Color(0.82, 0.92, 0.88, 0.90) # Pale velvety greenish-white
	mold_mat.roughness = 0.95
	mold_mat.emission_enabled = true
	mold_mat.emission = Color(0.2, 0.5, 0.35)
	mold_mat.emission_energy_multiplier = 0.3
	
	for j in range(12):
		var mold_tuft := MeshInstance3D.new()
		var tm := SphereMesh.new()
		var tr: float = randf_range(0.015, 0.035)
		tm.radius = tr
		tm.height = tr * 1.6
		mold_tuft.mesh = tm
		mold_tuft.position = Vector3(
			randf_range(-0.10, 0.10) + 0.10,
			0.08 + randf_range(0.0, 0.025),
			randf_range(-0.10, 0.10) - 0.08
		)
		mold_tuft.material_override = mold_mat
		_mold_node.add_child(mold_tuft)
	
	# 5. Bioluminescent Nutrient Halo Light
	_halo_light = OmniLight3D.new()
	_halo_light.name = "NutrientGlow"
	_halo_light.light_color = Color(0.35, 0.96, 0.55)
	_halo_light.light_energy = 1.3
	_halo_light.omni_range = 1.4
	_halo_light.omni_attenuation = 1.3
	add_child(_halo_light)
	
	# 6. Physical Proximity Trigger Shape
	var col := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.30
	col.shape = sphere
	add_child(col)

func _setup_consumption_fx() -> void:
	_consume_particles = GPUParticles3D.new()
	_consume_particles.name = "ConsumeHaloParticles"
	_consume_particles.emitting = false
	_consume_particles.one_shot = true
	_consume_particles.explosiveness = 0.85
	_consume_particles.amount = 32
	_consume_particles.lifetime = 0.75
	
	var p_mat := ParticleProcessMaterial.new()
	p_mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	p_mat.emission_sphere_radius = 0.2
	p_mat.direction = Vector3.UP
	p_mat.spread = 75.0
	p_mat.initial_velocity_min = 0.6
	p_mat.initial_velocity_max = 1.4
	p_mat.gravity = Vector3(0.0, -0.4, 0.0)
	p_mat.scale_min = 0.03
	p_mat.scale_max = 0.08
	p_mat.color = Color(0.4, 1.0, 0.6, 0.8)
	_consume_particles.process_material = p_mat
	
	var quad := QuadMesh.new()
	quad.size = Vector2(0.06, 0.06)
	var q_mat := StandardMaterial3D.new()
	q_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	q_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	q_mat.albedo_color = Color(0.4, 1.0, 0.6, 0.8)
	q_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	quad.material = q_mat
	_consume_particles.draw_pass_1 = quad
	
	add_child(_consume_particles)

func _process(delta: float) -> void:
	_pulse_time += delta * 3.2
	if _halo_light:
		_halo_light.light_energy = 1.1 + 0.4 * sin(_pulse_time)
	if _flesh_mesh and _flesh_mesh.material_override:
		var mat = _flesh_mesh.material_override as StandardMaterial3D
		mat.emission_energy_multiplier = 0.6 + 0.3 * sin(_pulse_time)

func _on_body_entered(body: Node3D) -> void:
	if body is FlyAgent:
		print("Food consumed by Drosophila at: ", global_position)
		if _consume_particles:
			_consume_particles.restart()
			_consume_particles.emitting = true
		food_consumed.emit(global_position)
		respawn()

func respawn() -> void:
	var rx: float = randf_range(arena_bounds.position.x, arena_bounds.position.x + arena_bounds.size.x)
	var rz: float = randf_range(arena_bounds.position.y, arena_bounds.position.y + arena_bounds.size.y)
	position = Vector3(rx, 0.08, rz)
