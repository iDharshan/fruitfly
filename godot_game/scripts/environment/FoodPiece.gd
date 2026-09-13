class_name FoodPiece
extends Area3D

## Volumetric 3D Floating Nutrient Food Source
## Vibrant, colorful floating nutrient orb designed to stand out strikingly
## in the minimalist dark-grid void environment.
## Features translucent chromatic fruit core, orbiting syrupy droplets,
## bioluminescent spore aura, and generous 3D aerial intercept trigger.

signal food_consumed(pos: Vector3)

@export var arena_bounds: Rect2 = Rect2(-30.0, -30.0, 60.0, 60.0)
@export var min_altitude: float = 3.5
@export var max_altitude: float = 26.0

var _core_mesh: MeshInstance3D
var _outer_mesh: MeshInstance3D
var _halo_light: OmniLight3D
var _droplets_node: Node3D
var _consume_particles: GPUParticles3D
var _ambient_spores: GPUParticles3D
var _pulse_time: float = 0.0
var _base_spawn_pos: Vector3

func _ready() -> void:
	collision_layer = 4
	collision_mask = 2 # Detect FlyAgent (layer 2)
	
	_base_spawn_pos = position
	_build_floating_fruit_visuals()
	_setup_consumption_fx()
	_setup_ambient_spores()
	body_entered.connect(_on_body_entered)

func _build_floating_fruit_visuals() -> void:
	# 1. Inner Radiant Chromatic Core
	var core_sphere := SphereMesh.new()
	core_sphere.radius = 0.22
	core_sphere.height = 0.44
	core_sphere.radial_segments = 24
	core_sphere.rings = 16
	
	_core_mesh = MeshInstance3D.new()
	_core_mesh.name = "RadiantCore"
	_core_mesh.mesh = core_sphere
	
	var core_mat := StandardMaterial3D.new()
	core_mat.albedo_color = Color(1.0, 0.45, 0.15, 1.0) # Vivid solar nectar orange
	core_mat.emission_enabled = true
	core_mat.emission = Color(1.0, 0.55, 0.10)
	core_mat.emission_energy_multiplier = 2.4
	core_mat.roughness = 0.15
	_core_mesh.material_override = core_mat
	add_child(_core_mesh)
	
	# 2. Outer Translucent Prismatic Rind / Nutrient Gel Shell
	var outer_sphere := SphereMesh.new()
	outer_sphere.radius = 0.32
	outer_sphere.height = 0.64
	outer_sphere.radial_segments = 24
	outer_sphere.rings = 16
	
	_outer_mesh = MeshInstance3D.new()
	_outer_mesh.name = "PrismaticShell"
	_outer_mesh.mesh = outer_sphere
	
	var shell_mat := StandardMaterial3D.new()
	shell_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	shell_mat.albedo_color = Color(0.20, 0.98, 0.60, 0.45) # Luminescent emerald/cyan gel
	shell_mat.emission_enabled = true
	shell_mat.emission = Color(0.15, 0.90, 0.55)
	shell_mat.emission_energy_multiplier = 0.9
	shell_mat.roughness = 0.08
	shell_mat.clearcoat_enabled = true
	shell_mat.clearcoat = 1.0
	shell_mat.clearcoat_roughness = 0.05
	shell_mat.rim_enabled = true
	shell_mat.rim = 1.0
	shell_mat.rim_tint = 0.8
	_outer_mesh.material_override = shell_mat
	add_child(_outer_mesh)
	
	# 3. Orbiting Sugar Syrup Globules
	_droplets_node = Node3D.new()
	_droplets_node.name = "OrbitingSyrup"
	add_child(_droplets_node)
	
	var drop_mat := StandardMaterial3D.new()
	drop_mat.albedo_color = Color(1.0, 0.88, 0.35, 0.9)
	drop_mat.roughness = 0.05
	drop_mat.emission_enabled = true
	drop_mat.emission = Color(1.0, 0.75, 0.2)
	drop_mat.emission_energy_multiplier = 1.2
	drop_mat.clearcoat_enabled = true
	drop_mat.clearcoat = 1.0
	
	for i in range(8):
		var angle: float = float(i) * TAU / 8.0
		var r: float = 0.48
		var drop := MeshInstance3D.new()
		var sm := SphereMesh.new()
		var drop_size: float = randf_range(0.04, 0.07)
		sm.radius = drop_size
		sm.height = drop_size * 2.0
		drop.mesh = sm
		drop.position = Vector3(r * cos(angle), sin(angle * 2.0) * 0.12, r * sin(angle))
		drop.material_override = drop_mat
		_droplets_node.add_child(drop)
	
	# 4. Bioluminescent Chromatic OmniLight
	_halo_light = OmniLight3D.new()
	_halo_light.name = "NutrientBeaconLight"
	_halo_light.light_color = Color(0.35, 1.0, 0.65)
	_halo_light.light_energy = 2.8
	_halo_light.omni_range = 14.0
	_halo_light.omni_attenuation = 1.2
	add_child(_halo_light)
	
	# 5. Generous 3D Aerial Intercept Trigger
	var col := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 1.2 # Generous 3D volume for high-speed intercept
	col.shape = sphere
	add_child(col)

func _setup_ambient_spores() -> void:
	_ambient_spores = GPUParticles3D.new()
	_ambient_spores.name = "AmbientSpores"
	_ambient_spores.amount = 40
	_ambient_spores.lifetime = 2.4
	_ambient_spores.preprocess = 1.0
	
	var p_mat := ParticleProcessMaterial.new()
	p_mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	p_mat.emission_sphere_radius = 0.75
	p_mat.gravity = Vector3(0.0, 0.05, 0.0)
	p_mat.initial_velocity_min = 0.05
	p_mat.initial_velocity_max = 0.20
	p_mat.scale_min = 0.03
	p_mat.scale_max = 0.08
	p_mat.color = Color(0.4, 1.0, 0.7, 0.75)
	_ambient_spores.process_material = p_mat
	
	var quad := QuadMesh.new()
	quad.size = Vector2(0.06, 0.06)
	var q_mat := StandardMaterial3D.new()
	q_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	q_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	q_mat.albedo_color = Color(0.4, 1.0, 0.7, 0.75)
	q_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	quad.material = q_mat
	_ambient_spores.draw_pass_1 = quad
	
	add_child(_ambient_spores)

func _setup_consumption_fx() -> void:
	_consume_particles = GPUParticles3D.new()
	_consume_particles.name = "ConsumeBurst"
	_consume_particles.emitting = false
	_consume_particles.one_shot = true
	_consume_particles.explosiveness = 0.9
	_consume_particles.amount = 48
	_consume_particles.lifetime = 0.85
	
	var p_mat := ParticleProcessMaterial.new()
	p_mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	p_mat.emission_sphere_radius = 0.35
	p_mat.direction = Vector3.UP
	p_mat.spread = 180.0 # Omnidirectional 3D blast
	p_mat.initial_velocity_min = 1.8
	p_mat.initial_velocity_max = 3.6
	p_mat.gravity = Vector3.ZERO
	p_mat.scale_min = 0.04
	p_mat.scale_max = 0.12
	p_mat.color = Color(0.3, 1.0, 0.6, 0.95)
	_consume_particles.process_material = p_mat
	
	var quad := QuadMesh.new()
	quad.size = Vector2(0.08, 0.08)
	var q_mat := StandardMaterial3D.new()
	q_mat.shading_mode = StandardMaterial3D.SHADING_MODE_UNSHADED
	q_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	q_mat.albedo_color = Color(0.3, 1.0, 0.6, 0.95)
	q_mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	quad.material = q_mat
	_consume_particles.draw_pass_1 = quad
	
	add_child(_consume_particles)

func _process(delta: float) -> void:
	_pulse_time += delta * 2.8
	
	# 3D Floating Bobbing Motion
	position.y = _base_spawn_pos.y + sin(_pulse_time) * 0.35
	position.x = _base_spawn_pos.x + cos(_pulse_time * 0.7) * 0.18
	position.z = _base_spawn_pos.z + sin(_pulse_time * 0.5) * 0.18
	
	# Orbiting droplets rotation
	if _droplets_node:
		_droplets_node.rotate_y(delta * 1.6)
		_droplets_node.rotate_x(delta * 0.4)
		
	# Pulsating light & core
	if _halo_light:
		_halo_light.light_energy = 2.4 + 0.8 * sin(_pulse_time * 1.5)
	if _core_mesh and _core_mesh.material_override:
		var mat = _core_mesh.material_override as StandardMaterial3D
		mat.emission_energy_multiplier = 2.2 + 0.8 * sin(_pulse_time * 1.5)

var _is_eating: bool = false

func _on_body_entered(body: Node3D) -> void:
	if body is FlyAgent and not _is_eating:
		_is_eating = true
		var consumed_pos := global_position
		print("Food consumed in 3D space at: ", consumed_pos)
		if _consume_particles:
			_consume_particles.restart()
			_consume_particles.emitting = true
		respawn()
		food_consumed.emit(global_position)
		# Brief cooldown to prevent double-triggering before fly leaves radius
		get_tree().create_timer(0.20).timeout.connect(func(): _is_eating = false)

func respawn() -> void:
	var rx: float = randf_range(arena_bounds.position.x + 6.0, arena_bounds.position.x + arena_bounds.size.x - 6.0)
	var rz: float = randf_range(arena_bounds.position.y + 6.0, arena_bounds.position.y + arena_bounds.size.y - 6.0)
	var ry: float = randf_range(min_altitude + 1.0, max_altitude - 2.0)
	
	_base_spawn_pos = Vector3(rx, ry, rz)
	position = _base_spawn_pos
	print("Food respawned in 3D volume at: ", position)
