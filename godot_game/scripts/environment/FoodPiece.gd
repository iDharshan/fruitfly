class_name FoodPiece
extends Area3D

## Decaying Fruit Food Source
## Represents decaying fruit slice with bioluminescent nutrient core.
## Detects fly feeding proximity, triggers consumption halo, and respawns.

signal food_consumed(pos: Vector3)

@export var arena_bounds: Rect2 = Rect2(-1.5, -1.5, 3.0, 3.0)

var _core_mesh: MeshInstance3D
var _halo_light: OmniLight3D
var _mold_mesh: MeshInstance3D
var _pulse_time: float = 0.0

func _ready() -> void:
	collision_layer = 4
	collision_mask = 2 # Detect FlyAgent (layer 2)
	
	_build_fruit_visuals()
	body_entered.connect(_on_body_entered)

func _build_fruit_visuals() -> void:
	# 1. Decaying Fruit Core (Translucent Amber Peach Flesh)
	var fruit_mesh := CylinderMesh.new()
	fruit_mesh.top_radius = 0.22
	fruit_mesh.bottom_radius = 0.26
	fruit_mesh.height = 0.12
	fruit_mesh.radial_segments = 16
	
	_core_mesh = MeshInstance3D.new()
	_core_mesh.name = "FruitFlesh"
	_core_mesh.mesh = fruit_mesh
	
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.95, 0.58, 0.22, 0.92)
	mat.roughness = 0.25
	mat.emission_enabled = true
	mat.emission = Color(0.85, 0.42, 0.12)
	mat.emission_energy_multiplier = 0.6
	mat.rim_enabled = true
	mat.rim = 0.6
	_core_mesh.material_override = mat
	add_child(_core_mesh)
	
	# 2. Syrupy Bioluminescent Halo Light
	_halo_light = OmniLight3D.new()
	_halo_light.name = "NutrientGlow"
	_halo_light.light_color = Color(0.4, 0.95, 0.5)
	_halo_light.light_energy = 1.2
	_halo_light.omni_range = 1.2
	_halo_light.omni_attenuation = 1.4
	add_child(_halo_light)
	
	# 3. Collision Shape
	var col := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.28
	col.shape = sphere
	add_child(col)

func _process(delta: float) -> void:
	_pulse_time += delta * 3.0
	if _halo_light:
		_halo_light.light_energy = 1.0 + 0.35 * sin(_pulse_time)
	if _core_mesh and _core_mesh.material_override:
		var mat = _core_mesh.material_override as StandardMaterial3D
		mat.emission_energy_multiplier = 0.5 + 0.25 * sin(_pulse_time)

func _on_body_entered(body: Node3D) -> void:
	if body is FlyAgent:
		print("Food consumed by Drosophila at: ", global_position)
		food_consumed.emit(global_position)
		respawn()

func respawn() -> void:
	var rx: float = randf_range(arena_bounds.position.x, arena_bounds.position.x + arena_bounds.size.x)
	var rz: float = randf_range(arena_bounds.position.y, arena_bounds.position.y + arena_bounds.size.y)
	position = Vector3(rx, 0.08, rz)
